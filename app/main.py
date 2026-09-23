import asyncio
import json
import math
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, UploadFile, File, Request, Response, Depends
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import settings
from .db import init_db, execute, one, all_rows
from .auth import hash_password, verify_password, create_session, get_user, require_user
from .providers.factory import get_provider
from .movie import split_story, download, assemble

app = FastAPI(title="RedPits API", version="4.0.0")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/media", StaticFiles(directory=settings.storage_dir), name="media")

@app.on_event("startup")
def startup():
    init_db()

@app.get("/")
def index():
    return FileResponse("app/static/index.html")

@app.get("/auth")
def auth_page():
    return FileResponse("app/static/auth.html")

@app.get("/studio")
def studio_page(request: Request):
    if not get_user(request):
        return RedirectResponse("/auth", status_code=303)
    return FileResponse("app/static/studio.html")

class AuthRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=8, max_length=200)

@app.post("/api/auth/signup")
def signup(req: AuthRequest, response: Response):
    email = req.email.strip().lower()
    if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        raise HTTPException(400, "Enter a valid email address.")
    if one("SELECT id FROM users WHERE email=?", (email,)):
        raise HTTPException(409, "An account with that email already exists. Log in instead.")
    uid = uuid.uuid4().hex
    execute("INSERT INTO users(id,email,password_hash,created_at) VALUES(?,?,?,?)", (uid, email, hash_password(req.password), now()))
    token = create_session(uid)
    response.set_cookie("redpits_session", token, max_age=60*60*24*30, httponly=True, secure=settings.session_cookie_secure, samesite="lax", path="/")
    return {"ok": True, "user": {"id": uid, "email": email}}

@app.post("/api/auth/login")
def login(req: AuthRequest, response: Response):
    email = req.email.strip().lower()
    user = one("SELECT * FROM users WHERE email=?", (email,))
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password.")
    token = create_session(user["id"])
    response.set_cookie("redpits_session", token, max_age=60*60*24*30, httponly=True, secure=settings.session_cookie_secure, samesite="lax", path="/")
    return {"ok": True, "user": {"id": user["id"], "email": user["email"]}}

@app.post("/api/auth/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get("redpits_session")
    if token:
        execute("DELETE FROM sessions WHERE token=?", (token,))
    response.delete_cookie("redpits_session", path="/")
    return {"ok": True}

@app.get("/api/auth/me")
def me(request: Request):
    user = get_user(request)
    if not user:
        raise HTTPException(401, "Not logged in")
    return {"id": user["id"], "email": user["email"]}

class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=settings.max_prompt_length)
    mode: str = "video"
    duration: int = Field(default=6, ge=1, le=600)
    aspect_ratio: str = "16:9"
    image_url: str | None = None
    seed: int = 42
    steps: int = Field(default=4, ge=1, le=8)

class ProjectRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=settings.max_prompt_length)
    title: str | None = None
    mode: str = "video"
    output_url: str | None = None

def now():
    return datetime.now(timezone.utc).isoformat()

def new_job(kind, project_id=None, req=None, user_id=None):
    jid = uuid.uuid4().hex
    params = req.model_dump_json() if req else "{}"
    execute("INSERT INTO jobs(id,user_id,project_id,kind,status,progress,message,created_at,model,parameters) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (jid, user_id, project_id, kind, "queued", 0, "Queued", now(), "self-hosted-local", params))
    return jid

def set_job(jid, status=None, progress=None, message=None, output_url=None, error=None, started_at=None, completed_at=None):
    cur = one("SELECT * FROM jobs WHERE id=?", (jid,))
    if not cur:
        return
    execute("UPDATE jobs SET status=?,progress=?,message=?,output_url=?,error=?,started_at=?,completed_at=? WHERE id=?",
            (status or cur["status"], progress if progress is not None else cur["progress"],
             message if message is not None else cur["message"], output_url if output_url is not None else cur["output_url"],
             error if error is not None else cur["error"], started_at or cur["started_at"], completed_at or cur["completed_at"], jid))

async def run_generation(jid, req):
    started = now()
    try:
        set_job(jid, "processing", 5, "Connecting to the RedPits local GPU engine", started_at=started)
        provider = get_provider()
        if req.mode == "video":
            result = await provider.text_to_video(req.prompt, req.duration, req.aspect_ratio)
        elif req.mode == "image":
            result = await provider.text_to_image(req.prompt, req.aspect_ratio)
        elif req.mode == "sticker":
            result = await provider.text_to_sticker(req.prompt)
        elif req.mode == "image-to-video":
            if not req.image_url:
                raise ValueError("An image URL is required for image-to-video.")
            result = await provider.image_to_video(req.image_url, req.prompt, req.duration, req.aspect_ratio)
        elif req.mode == "audio":
            result = await provider.text_to_audio(req.prompt, req.duration)
        else:
            raise ValueError("Unsupported generation mode")
        set_job(jid, "succeeded", 100, "Generation complete", result.url, completed_at=now())
    except Exception as e:
        set_job(jid, "failed", 100, "Generation failed", error=str(e), completed_at=now())

async def run_movie(jid, req):
    try:
        provider = get_provider()
        scenes = split_story(req.prompt, settings.max_movie_scenes)
        if not scenes:
            raise ValueError("Your movie story is empty.")
        work = Path(settings.storage_dir) / "movies" / jid
        work.mkdir(parents=True, exist_ok=True)
        clips = []
        shot_seconds = max(1, settings.ai_max_video_seconds)
        shot_count = max(1, math.ceil(req.duration / shot_seconds))
        for i in range(shot_count):
            scene = scenes[i % len(scenes)]
            progress = int(i / shot_count * 90)
            set_job(jid, "processing", progress, f"Producing shot {i + 1} of {shot_count}")
            prompt = ("Create one short cinematic production shot for a longer film. Preserve character identity, "
                      "wardrobe, age, physical traits, props, locations, time of day and visual style across the "
                      "entire movie. Use natural motion, coherent camera movement, strong composition, and a clear "
                      "beginning-to-end action beat. Do not add captions, titles, logos or watermarks. "
                      f"This is shot {i + 1} of {shot_count}. {scene}")
            result = await provider.text_to_video(prompt, shot_seconds, req.aspect_ratio)
            clip = work / f"scene-{i + 1:04d}.mp4"
            if result.url.startswith("/media/"):
                local = Path(settings.storage_dir) / result.url.removeprefix("/media/")
                if not local.exists():
                    raise FileNotFoundError(f"Generated scene file was not found: {local}")
                clip.write_bytes(local.read_bytes())
            else:
                await download(result.url, clip)
            clips.append(clip)
        set_job(jid, "processing", 95, "Assembling the final movie")
        output = work / "redpits-movie.mp4"
        assemble(clips, output)
        set_job(jid, "succeeded", 100, f"Movie complete • {len(clips)} scenes", f"/media/movies/{jid}/redpits-movie.mp4", completed_at=now())
    except Exception as e:
        set_job(jid, "failed", 100, "Movie generation failed", error=str(e), completed_at=now())

@app.post("/api/upload")
async def upload_image(file: UploadFile = File(...), user=Depends(require_user)):
    allowed = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}
    if file.content_type not in allowed:
        raise HTTPException(400, "Only PNG, JPG and WebP images are supported.")
    data = await file.read()
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(413, "Image is too large. Maximum size is 15 MB.")
    name = f"references/{uuid.uuid4().hex}{allowed[file.content_type]}"
    path = Path(settings.storage_dir) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {"url": f"/media/{name}"}

async def ai_engine_ready():
    if settings.provider == "mock":
        return
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(8.0, connect=4.0)) as client:
            r = await client.get(f"{settings.ai_engine_url.rstrip('/')}/health", headers={"Authorization": f"Bearer {settings.ai_engine_token}"} if settings.ai_engine_token else {})
            if not r.is_success:
                raise RuntimeError(f"AI engine returned HTTP {r.status_code}.")
            data = r.json()
            if data.get("gpu_available") is False:
                raise RuntimeError("RedPits AI engine is online but no supported NVIDIA GPU is available.")
            if data.get("ready") is False:
                missing = ", ".join(data.get("readiness", {}).get("missing", []))
                raise RuntimeError("RedPits AI engine is not ready" + (f": {missing}" if missing else "."))
    except Exception as exc:
        raise HTTPException(503, f"RedPits AI engine is unavailable. Connect the self-hosted GPU engine at AI_ENGINE_URL before generating. ({exc})")

@app.post("/api/generate")
async def generate(req: GenerateRequest, user=Depends(require_user)):
    if req.mode == "audio":
        raise HTTPException(400, "Local audio generation is not enabled yet.")
    await ai_engine_ready()
    jid = new_job(req.mode, req=req, user_id=user["id"])
    asyncio.create_task(run_generation(jid, req))
    return {"job_id": jid}

@app.post("/api/movie")
async def movie(req: GenerateRequest, user=Depends(require_user)):
    await ai_engine_ready()
    if req.duration > settings.movie_max_duration:
        raise HTTPException(400, f"Movie generation is limited to {settings.movie_max_duration} seconds per job.")
    jid = new_job("movie", req=req, user_id=user["id"])
    asyncio.create_task(run_movie(jid, req))
    return {"job_id": jid}

@app.get("/api/jobs/{jid}")
def job(jid, request: Request):
    user = require_user(request)
    item = one("SELECT * FROM jobs WHERE id=? AND user_id=?", (jid, user["id"]))
    if not item:
        raise HTTPException(404, "Job not found")
    return item

@app.post("/api/projects")
def create_project(req: ProjectRequest, user=Depends(require_user)):
    pid = uuid.uuid4().hex
    execute("INSERT INTO projects(id,user_id,title,prompt,mode,output_url,created_at) VALUES(?,?,?,?,?,?,?)",
            (pid, user["id"], req.title or "Untitled project", req.prompt, req.mode, req.output_url, now()))
    return one("SELECT * FROM projects WHERE id=?", (pid,))

@app.get("/api/projects")
def projects(user=Depends(require_user)):
    return all_rows("SELECT * FROM projects WHERE user_id=? ORDER BY created_at DESC LIMIT 100", (user["id"],))

@app.delete("/api/projects/{pid}")
def delete_project(pid, request: Request):
    user = require_user(request)
    if not one("SELECT * FROM projects WHERE id=? AND user_id=?", (pid, user["id"])):
        raise HTTPException(404, "Project not found")
    execute("DELETE FROM projects WHERE id=? AND user_id=?", (pid, user["id"]))
    return {"ok": True}

@app.get("/api/health")
async def health():
    result = {"ok": True, "app": settings.app_name, "provider": "self-hosted", "configured_provider": settings.provider, "ai_engine_url": settings.ai_engine_url, "self_hosted": True}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{settings.ai_engine_url.rstrip('/')}/health", headers={"Authorization": f"Bearer {settings.ai_engine_token}"} if settings.ai_engine_token else {})
            result["ai_engine"] = r.json() if r.is_success else {"status": "unavailable", "http_status": r.status_code}
    except Exception as exc:
        result["ai_engine"] = {"status": "unavailable", "error": str(exc)}
    return result

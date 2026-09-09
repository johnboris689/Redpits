import asyncio
import math
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import settings
from .db import init_db, execute, one, all_rows
from .providers.factory import get_provider
from .movie import split_story, download, assemble

app = FastAPI(title="RedPits API", version="3.0.0")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/media", StaticFiles(directory=settings.storage_dir), name="media")

@app.on_event("startup")
def startup():
    init_db()

@app.get("/")
def index():
    return FileResponse("app/static/index.html")

class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=settings.max_prompt_length)
    mode: str = "video"
    duration: int = Field(default=6, ge=1, le=600)
    aspect_ratio: str = "16:9"
    image_url: str | None = None

class ProjectRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=settings.max_prompt_length)
    title: str | None = None
    mode: str = "video"
    output_url: str | None = None

def now():
    return datetime.now(timezone.utc).isoformat()

def new_job(kind, project_id=None):
    jid = uuid.uuid4().hex
    execute("INSERT INTO jobs(id,project_id,kind,status,progress,message,created_at) VALUES(?,?,?,?,?,?,?)",
            (jid, project_id, kind, "queued", 0, "Queued", now()))
    return jid

def set_job(jid, status=None, progress=None, message=None, output_url=None, error=None):
    cur = one("SELECT * FROM jobs WHERE id=?", (jid,))
    if not cur:
        return
    execute("UPDATE jobs SET status=?,progress=?,message=?,output_url=?,error=? WHERE id=?",
            (status or cur["status"], progress if progress is not None else cur["progress"],
             message if message is not None else cur["message"],
             output_url if output_url is not None else cur["output_url"],
             error if error is not None else cur["error"], jid))

async def run_generation(jid, req):
    try:
        set_job(jid, "processing", 5, "Connecting to the free AI provider")
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
        set_job(jid, "succeeded", 100, "Generation complete", result.url)
    except Exception as e:
        set_job(jid, "failed", 100, "Generation failed", error=str(e))

async def run_movie(jid, req):
    try:
        provider = get_provider()
        scenes = split_story(req.prompt, settings.max_movie_scenes)
        if not scenes:
            raise ValueError("Your movie story is empty.")
        work = Path(settings.storage_dir) / "movies" / jid
        work.mkdir(parents=True, exist_ok=True)
        clips = []
        shot_seconds = max(1, settings.hf_max_video_seconds)
        shot_count = max(1, math.ceil(req.duration / shot_seconds))
        for i in range(shot_count):
            scene = scenes[i % len(scenes)]
            progress = int(i / shot_count * 90)
            set_job(jid, "processing", progress, f"Producing shot {i + 1} of {shot_count}")
            prompt = (
                "Create one short cinematic production shot for a longer film. "
                "Preserve character identity, wardrobe, age, physical traits, props, "
                "locations, time of day and visual style across the entire movie. "
                "Use natural motion, coherent camera movement, strong composition, "
                "and a clear beginning-to-end action beat. Do not add captions, titles, "
                "logos or watermarks. This is shot " + str(i + 1) + " of " + str(shot_count) + ". " + scene
            )
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
        set_job(jid, "succeeded", 100, f"Movie complete • {len(clips)} scenes", f"/media/movies/{jid}/redpits-movie.mp4")
    except Exception as e:
        set_job(jid, "failed", 100, "Movie generation failed", error=str(e))

@app.post("/api/upload")
async def upload_image(file: UploadFile = File(...)):
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

@app.post("/api/generate")
async def generate(req: GenerateRequest):
    jid = new_job(req.mode)
    asyncio.create_task(run_generation(jid, req))
    return {"job_id": jid}

@app.post("/api/movie")
async def movie(req: GenerateRequest):
    if req.duration > settings.movie_max_duration:
        raise HTTPException(400, f"Free movie generation is limited to {settings.movie_max_duration} seconds per job.")
    jid = new_job("movie")
    asyncio.create_task(run_movie(jid, req))
    return {"job_id": jid}

@app.get("/api/jobs/{jid}")
def job(jid):
    item = one("SELECT * FROM jobs WHERE id=?", (jid,))
    if not item:
        raise HTTPException(404, "Job not found")
    return item

@app.post("/api/projects")
def create_project(req: ProjectRequest):
    pid = uuid.uuid4().hex
    execute("INSERT INTO projects(id,title,prompt,mode,output_url,created_at) VALUES(?,?,?,?,?,?)",
            (pid, req.title or "Untitled project", req.prompt, req.mode, req.output_url, now()))
    return one("SELECT * FROM projects WHERE id=?", (pid,))

@app.get("/api/projects")
def projects():
    return all_rows("SELECT * FROM projects ORDER BY created_at DESC LIMIT 100")

@app.delete("/api/projects/{pid}")
def delete_project(pid):
    if not one("SELECT * FROM projects WHERE id=?", (pid,)):
        raise HTTPException(404, "Project not found")
    execute("DELETE FROM projects WHERE id=?", (pid,))
    return {"ok": True}

@app.get("/api/health")
def health():
    return {
        "ok": True,
        "app": settings.app_name,
        "provider": settings.provider,
        "video_space": settings.hf_video_space if settings.provider == "huggingface" else None,
        "image_space": settings.hf_image_space if settings.provider == "huggingface" else None,
        "free_provider": settings.provider == "huggingface",
        "video_max_seconds": settings.hf_max_video_seconds if settings.provider == "huggingface" else None,
    }

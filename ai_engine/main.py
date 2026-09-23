
from pathlib import Path
import uuid

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .config import settings
from .security import require_token
from .hardware import inspect_hardware
from .service import create_job, public_job, jobs, models, readiness


app = FastAPI(title="RedPits Self-Hosted AI Engine", version="2.0.0")


class JobRequest(BaseModel):
    kind: str
    prompt: str = Field(min_length=1, max_length=settings.max_prompt_length)
    duration: int = Field(default=settings.default_video_seconds, ge=1, le=settings.max_video_seconds)
    aspect_ratio: str = "16:9"
    image_path: str | None = None
    seed: int = 42
    steps: int = Field(default=4, ge=1, le=8)


@app.get("/health")
def health(_=Depends(require_token)):
    hw = inspect_hardware()
    ready = readiness(hw)
    return {
        "status": "ok",
        **hw,
        "ready": ready["ready"],
        "readiness": ready,
        "queue_size": sum(1 for j in jobs.values() if j.status in ("queued", "processing")),
    }


@app.get("/models")
def get_models(_=Depends(require_token)):
    return models()


@app.post("/files")
async def upload_reference(file: UploadFile = File(...), _=Depends(require_token)):
    suffix = Path(file.filename or "reference.bin").suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise HTTPException(400, "Only PNG, JPG and WebP references are supported.")
    target = Path(settings.output_dir) / "inputs" / f"{uuid.uuid4().hex}{suffix}"
    target.parent.mkdir(parents=True, exist_ok=True)
    data = await file.read()
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(413, "Reference file is too large.")
    target.write_bytes(data)
    return {"path": str(target)}


@app.get("/outputs/{name}")
def output(name: str, _=Depends(require_token)):
    safe = Path(name).name
    if safe != name:
        raise HTTPException(400, "Invalid output name.")
    path = Path(settings.output_dir) / safe
    if not path.exists() or not path.is_file():
        raise HTTPException(404, "Output not found")
    return FileResponse(path)


@app.post("/jobs")
def create(req: JobRequest, _=Depends(require_token)):
    if req.kind == "audio":
        raise HTTPException(400, "Local audio generation is not enabled yet.")
    if req.kind not in {"video", "image", "image-to-video", "sticker"}:
        raise HTTPException(400, "Unsupported generation type.")
    return public_job(create_job(req.kind, req.model_dump()))


@app.get("/jobs/{job_id}")
def status(job_id: str, _=Depends(require_token)):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "AI job not found")
    return public_job(job)


@app.post("/jobs/{job_id}/cancel")
def cancel(job_id: str, _=Depends(require_token)):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "AI job not found")
    if job.task and not job.task.done():
        job.task.cancel()
        job.status, job.progress, job.message = "cancelled", 100, "Generation cancelled"
    return public_job(job)

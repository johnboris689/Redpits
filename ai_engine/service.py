import asyncio
import uuid
from pathlib import Path
from dataclasses import dataclass, field

from .config import settings
from .hardware import inspect_hardware, require_device
from .models.registry import REGISTRY
from .models.image.engine import generate as generate_image
from .models.video.engine import generate as generate_video
from .models.sticker import make_sticker

@dataclass
class Job:
    id: str
    kind: str
    payload: dict
    status: str = "queued"
    progress: int = 0
    message: str = "Queued"
    output: str | None = None
    error: str | None = None
    task: asyncio.Task | None = field(default=None, repr=False)

jobs: dict[str, Job] = {}
semaphore = asyncio.Semaphore(settings.max_concurrent_jobs)


def _aspect(size: tuple[int, int], ratio: str):
    if ratio == "9:16": return size[1], size[0]
    if ratio == "1:1": return min(size), min(size)
    if ratio == "4:5": return 512, 640
    return size[0], size[1]

async def _run(job: Job):
    async with semaphore:
        job.status, job.progress, job.message = "processing", 5, "Checking GPU and loading the local model…"
        try:
            device = require_device()
            p = job.payload
            kind = job.kind
            if kind == "image":
                w, h = _aspect((1024, 576), p.get("aspect_ratio", "16:9"))
                path = await asyncio.to_thread(generate_image, p["prompt"], Path(settings.output_dir), w, h, p.get("steps", 4), p.get("seed", 42), device, settings.image_model_id)
            elif kind in ("video", "image-to-video"):
                w, h = _aspect((576, 1024), p.get("aspect_ratio", "16:9"))
                seconds = min(int(p.get("duration", settings.default_video_seconds)), settings.max_video_seconds)
                image_path = Path(p["image_path"]) if p.get("image_path") else None
                path = await asyncio.to_thread(generate_video, p["prompt"], Path(settings.output_dir), w, h, seconds, settings.default_fps, p.get("seed", 42), device, image_path)
            elif kind == "sticker":
                # Generate a local image first, then remove its background locally.
                w, h = 1024, 1024
                image = await asyncio.to_thread(generate_image, p["prompt"] + ", isolated sticker subject, clean edges, centered", Path(settings.output_dir), w, h, 4, p.get("seed", 42), device, settings.image_model_id)
                path = await asyncio.to_thread(make_sticker, image, Path(settings.output_dir))
            else:
                raise RuntimeError(f"Unsupported AI job type: {kind}")
            job.status, job.progress, job.message, job.output = "succeeded", 100, "Generation complete", str(path)
        except Exception as exc:
            job.status, job.progress, job.message, job.error = "failed", 100, "Generation failed", str(exc)


def create_job(kind: str, payload: dict):
    jid = uuid.uuid4().hex
    job = Job(jid, kind, payload)
    jobs[jid] = job
    job.task = asyncio.create_task(_run(job))
    return job


def public_job(job: Job):
    return {
        "id": job.id, "kind": job.kind, "status": job.status,
        "progress": job.progress, "message": job.message,
        "output": job.output, "error": job.error,
    }

def readiness(hw=None):
    hw = hw or inspect_hardware()
    missing = []
    repo = Path(settings.ltx_repo_dir)
    if not (repo / "inference.py").exists():
        missing.append("LTX-Video repository")
    if not (repo / settings.ltx_pipeline_config).exists() and not Path(settings.ltx_pipeline_config).exists():
        missing.append("LTX pipeline configuration")
    setup_marker = Path(settings.model_dir) / ".redpits_setup_complete"
    if not setup_marker.exists():
        missing.append("local model setup (run `python -m ai_engine.setup`)")
    ready = bool(hw["gpu_available"]) and not missing
    return {
        "ready": ready,
        "gpu_required": True,
        "models_ready": not missing,
        "missing": missing,
    }


def models():
    hw = inspect_hardware()
    vram = hw["vram_gb"]
    return [{"id": k, "kind": v.kind, "min_vram_gb": v.min_vram_gb, "available": (vram >= v.min_vram_gb if hw["gpu_available"] else False), "description": v.description} for k,v in REGISTRY.items()]

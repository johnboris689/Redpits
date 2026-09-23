from pathlib import Path
import asyncio
import httpx

from .base import GenerationResult
from ..config import settings

class SelfHostedProvider:
    def __init__(self):
        self.base = settings.ai_engine_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {settings.ai_engine_token}"} if settings.ai_engine_token else {}

    async def _submit(self, kind, prompt, duration=6, aspect_ratio="16:9", image_url=None, seed=42, steps=4):
        image_path = None
        if image_url:
            if not image_url.startswith("/media/"):
                raise ValueError("Only images uploaded to RedPits can be used as generation references.")
            image_path = str(Path(settings.storage_dir) / image_url.removeprefix("/media/"))
            if not Path(image_path).exists():
                raise FileNotFoundError("Reference image is no longer available.")
            async with httpx.AsyncClient(timeout=httpx.Timeout(settings.ai_request_timeout, connect=15.0)) as client:
                with open(image_path, "rb") as f:
                    files = {"file": (Path(image_path).name, f, "application/octet-stream")}
                    r = await client.post(f"{self.base}/files", headers=self.headers, files=files)
                r.raise_for_status()
                image_path = r.json()["path"]
        payload = {"kind": kind, "prompt": prompt, "duration": duration, "aspect_ratio": aspect_ratio, "image_path": image_path, "seed": seed, "steps": steps}
        async with httpx.AsyncClient(timeout=httpx.Timeout(settings.ai_request_timeout, connect=15.0)) as client:
            r = await client.post(f"{self.base}/jobs", headers=self.headers, json=payload)
            r.raise_for_status()
            job = r.json()
            job_id = job["id"]
            deadline = asyncio.get_running_loop().time() + settings.ai_request_timeout
            while True:
                if asyncio.get_running_loop().time() > deadline:
                    raise TimeoutError("RedPits AI generation timed out while waiting for the GPU engine.")
                await asyncio.sleep(1.5)
                q = await client.get(f"{self.base}/jobs/{job_id}", headers=self.headers)
                q.raise_for_status()
                status = q.json()
                if status["status"] == "succeeded":
                    path = status["output"]
                    name = Path(path).name
                    # AI output is copied into the web app storage through a protected download endpoint.
                    media = await client.get(f"{self.base}/outputs/{name}", headers=self.headers)
                    media.raise_for_status()
                    local = Path(settings.storage_dir) / "generations" / name
                    local.parent.mkdir(parents=True, exist_ok=True)
                    local.write_bytes(media.content)
                    kind_out = "image" if kind in ("image", "sticker") else "video"
                    return GenerationResult(f"/media/generations/{name}", kind_out, {"ai_job_id": job_id})
                if status["status"] in ("failed", "cancelled"):
                    raise RuntimeError(status.get("error") or status.get("message") or "AI generation failed")

    async def text_to_video(self, prompt, duration, aspect_ratio):
        return await self._submit("video", prompt, min(duration, settings.ai_max_video_seconds), aspect_ratio)

    async def image_to_video(self, image_url, prompt, duration, aspect_ratio):
        return await self._submit("image-to-video", prompt, min(duration, settings.ai_max_video_seconds), aspect_ratio, image_url=image_url)

    async def text_to_image(self, prompt, aspect_ratio):
        return await self._submit("image", prompt, 1, aspect_ratio)

    async def text_to_sticker(self, prompt):
        return await self._submit("sticker", prompt, 1, "1:1")

    async def text_to_audio(self, prompt, duration):
        raise RuntimeError("Local audio generation is not enabled yet.")

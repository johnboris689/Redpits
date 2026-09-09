"""Free Hugging Face Spaces provider.

RedPits does not run a video model on Render. Render remains the web/API server,
while public Gradio Spaces provide the GPU inference. The provider discovers the
Space API at runtime so endpoint names can change without requiring a RedPits
release.
"""
from __future__ import annotations

import asyncio
import mimetypes
import shutil
import uuid
from pathlib import Path
from urllib.parse import urlparse

from gradio_client import Client, handle_file

from .base import Provider, GenerationResult
from ..config import settings


class HuggingFaceProvider(Provider):
    def __init__(self):
        if not settings.hf_video_space:
            raise RuntimeError("HF_VIDEO_SPACE is not configured.")
        self.video_space = settings.hf_video_space
        self.image_space = settings.hf_image_space or self.video_space
        self.token = settings.hf_token or None
        self._clients: dict[str, Client] = {}
        self._apis: dict[str, dict] = {}

    def _client(self, space: str) -> Client:
        if space not in self._clients:
            self._clients[space] = Client(space, token=self.token, verbose=False, download_files=str(Path(settings.storage_dir) / "hf-tmp"))
        return self._clients[space]

    def _api(self, space: str) -> dict:
        if space not in self._apis:
            self._apis[space] = self._client(space).view_api(print_info=False, return_format="dict")
        return self._apis[space]

    @staticmethod
    def _label(p: dict) -> str:
        return str(p.get("parameter_name") or p.get("label") or "").strip().lower().replace(" ", "_").replace("-", "_")

    @staticmethod
    def _component(p: dict) -> str:
        return str(p.get("component") or "").lower()

    @classmethod
    def _endpoint(cls, api: dict, want: str, with_image: bool = False):
        candidates = []
        for name, info in (api.get("named_endpoints") or {}).items():
            params = info.get("parameters") or []
            returns = info.get("returns") or []
            labels = [cls._label(p) for p in params]
            comps = [cls._component(p) for p in params]
            out = " ".join(str(r.get("label") or "").lower() + " " + str(r.get("component") or "").lower() for r in returns)
            has_prompt = any("prompt" in x for x in labels)
            has_video = "video" in out or "video" in name.lower()
            has_image = "image" in out or "image" in name.lower()
            has_file = any("image" in x or "file" in c for x, c in zip(labels, comps))
            score = 0
            low = name.lower()
            if want == "video" and has_video: score += 10
            if want == "image" and has_image and not has_video: score += 10
            if with_image and has_file: score += 8
            if has_prompt: score += 5
            if want == "video" and any(x in low for x in ("t2v", "text", "video", "generate")): score += 2
            if want == "image" and any(x in low for x in ("image", "generate", "text")): score += 2
            if score: candidates.append((score, name, info))
        if not candidates:
            raise RuntimeError(f"No compatible {want} endpoint was found in Hugging Face Space.")
        return sorted(candidates, reverse=True)[0][1:]

    @classmethod
    def _kwargs(cls, info: dict, prompt: str, duration: int, aspect_ratio: str, image_path: Path | None = None):
        result = {}
        width, height = settings.hf_width, settings.hf_height
        if aspect_ratio == "9:16": width, height = height, width
        elif aspect_ratio == "1:1": width = height = min(width, height)
        elif aspect_ratio == "4:5": width, height = 512, 640
        seconds = max(1, min(int(duration), settings.hf_max_video_seconds))
        fps = settings.hf_fps
        frames = 8 * round(seconds * fps / 8) + 1
        for p in info.get("parameters") or []:
            key = cls._label(p)
            if not key: continue
            default = p.get("parameter_default")
            required = not p.get("parameter_has_default", False)
            value = default
            if "prompt" in key: value = prompt
            elif "negative" in key: value = ""
            elif key in ("preset", "quality", "mode"): value = settings.hf_video_preset
            elif key in ("width", "image_width"): value = width
            elif key in ("height", "image_height"): value = height
            elif key in ("seconds", "duration", "length"): value = seconds
            elif key in ("frames", "num_frames"): value = frames
            elif key in ("fps", "frame_rate"): value = fps
            elif key in ("seed",): value = settings.hf_seed
            elif "random" in key and "seed" in key: value = True
            elif key in ("num_inference_steps", "steps"): value = settings.hf_steps
            elif key in ("camera_lora", "camera"): value = "none"
            elif "strength" in key: value = 0.0
            elif image_path is not None and ("image" in key or "input" in key or "source" in key) and str(p.get("component", "")).lower() in ("image", "file", "uploadbutton"):
                value = handle_file(str(image_path))
            if required and value is None:
                comp = str(p.get("component") or "").lower()
                if comp in ("checkbox",): value = False
                elif "number" in comp or comp in ("slider",): value = 0
                elif comp in ("dropdown", "radio"): value = ""
                elif "image" in comp or "file" in comp: value = handle_file(str(image_path)) if image_path else None
            if value is not None:
                result[key] = value
        return result

    @staticmethod
    def _copy_output(value, kind: str) -> str:
        candidates = value if isinstance(value, (list, tuple)) else [value]
        for item in candidates:
            path = None
            if isinstance(item, dict): path = item.get("path") or item.get("url")
            elif isinstance(item, str): path = item
            if not path: continue
            if path.startswith("http://") or path.startswith("https://"):
                # Gradio client normally downloads files for us; remote URLs are
                # intentionally returned unchanged if a Space chooses to expose one.
                return path
            p = Path(path)
            if p.exists():
                ext = p.suffix or (".mp4" if kind == "video" else ".png")
                out = Path(settings.storage_dir) / "generations" / f"{uuid.uuid4().hex}{ext}"
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(p, out)
                return f"/media/generations/{out.name}"
        raise RuntimeError("Hugging Face returned no downloadable media file.")

    def _predict(self, space: str, want: str, prompt: str, duration: int, aspect_ratio: str, image_path: Path | None = None):
        api = self._api(space)
        endpoint, info = self._endpoint(api, want, with_image=image_path is not None)
        kwargs = self._kwargs(info, prompt, duration, aspect_ratio, image_path)
        result = self._client(space).predict(api_name=endpoint, **kwargs)
        kind = "video" if want == "video" else "image"
        url = self._copy_output(result, kind)
        return url, {"provider": "huggingface", "space": space, "endpoint": endpoint}

    async def text_to_video(self, prompt, duration, aspect_ratio):
        url, meta = await asyncio.to_thread(self._predict, self.video_space, "video", prompt, duration, aspect_ratio)
        return GenerationResult(url, "video", meta)

    async def image_to_video(self, image_url, prompt, duration, aspect_ratio):
        if not image_url.startswith("/media/"):
            raise ValueError("The reference image must be uploaded through RedPits first.")
        image_path = Path(settings.storage_dir) / image_url.removeprefix("/media/")
        if not image_path.exists(): raise FileNotFoundError("Uploaded reference image was not found.")
        url, meta = await asyncio.to_thread(self._predict, self.video_space, "video", prompt, duration, aspect_ratio, image_path)
        return GenerationResult(url, "video", meta)

    async def text_to_image(self, prompt, aspect_ratio):
        url, meta = await asyncio.to_thread(self._predict, self.image_space, "image", prompt, 1, aspect_ratio)
        return GenerationResult(url, "image", meta)

    async def text_to_sticker(self, prompt):
        sticker_prompt = ("Create a premium digital sticker. Isolated single subject, clean empty background, "
                          "bold silhouette, crisp edges, polished lighting, sticker-ready composition, no frame, no watermark. " + prompt)
        return await self.text_to_image(sticker_prompt, "1:1")

    async def text_to_audio(self, prompt, duration):
        raise RuntimeError("Standalone audio is not enabled in the free RedPits provider. Use video generation with the provider's native audio when available.")

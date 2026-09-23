import asyncio
from pathlib import Path
from .base import Provider, GenerationResult
from ..config import settings

class MockProvider(Provider):
    async def _file(self, name, content):
        p = Path(settings.storage_dir) / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content)
        return f"/media/{name}"
    async def text_to_video(self, prompt, duration, aspect_ratio):
        await asyncio.sleep(.2); return GenerationResult(await self._file("mock-video.txt", prompt.encode()), "video", {"mock": True})
    async def image_to_video(self, image_url, prompt, duration, aspect_ratio):
        await asyncio.sleep(.2); return GenerationResult(await self._file("mock-image-video.txt", prompt.encode()), "video", {"mock": True})
    async def text_to_image(self, prompt, aspect_ratio):
        await asyncio.sleep(.2); return GenerationResult(await self._file("mock-image.txt", prompt.encode()), "image", {"mock": True})
    async def text_to_sticker(self, prompt):
        await asyncio.sleep(.2); return GenerationResult(await self._file("mock-sticker.txt", prompt.encode()), "sticker", {"mock": True})
    async def text_to_audio(self, prompt, duration):
        raise RuntimeError("Audio generation is not enabled in the free provider.")

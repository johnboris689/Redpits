from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class GenerationResult:
    url: str
    kind: str
    metadata: dict

class Provider(ABC):
    @abstractmethod
    async def text_to_video(self, prompt, duration, aspect_ratio): ...
    @abstractmethod
    async def image_to_video(self, image_url, prompt, duration, aspect_ratio): ...
    @abstractmethod
    async def text_to_image(self, prompt, aspect_ratio): ...
    @abstractmethod
    async def text_to_sticker(self, prompt): ...
    @abstractmethod
    async def text_to_audio(self, prompt, duration): ...

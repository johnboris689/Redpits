from .mock import MockProvider
from .huggingface import HuggingFaceProvider
from ..config import settings

def get_provider():
    if settings.provider == "mock": return MockProvider()
    if settings.provider in ("huggingface", "hf", "free"): return HuggingFaceProvider()
    raise RuntimeError(f"Unknown provider: {settings.provider}. Use PROVIDER=huggingface.")

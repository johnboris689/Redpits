import os
from dataclasses import dataclass
from dotenv import load_dotenv
load_dotenv()

@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "RedPits")
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    provider: str = os.getenv("PROVIDER", "huggingface").lower()
    storage_dir: str = os.getenv("STORAGE_DIR", "./storage")
    db_path: str = os.getenv("DB_PATH", "./storage/redpits.db")
    hf_video_space: str = os.getenv("HF_VIDEO_SPACE", "techfreakworm/LTX2.3-Studio")
    hf_image_space: str = os.getenv("HF_IMAGE_SPACE", "mrfakename/Z-Image-Turbo")
    hf_token: str = os.getenv("HF_TOKEN", "")
    hf_max_video_seconds: int = int(os.getenv("HF_MAX_VIDEO_SECONDS", "6"))
    hf_fps: int = int(os.getenv("HF_FPS", "24"))
    hf_width: int = int(os.getenv("HF_WIDTH", "576"))
    hf_height: int = int(os.getenv("HF_HEIGHT", "1024"))
    hf_steps: int = int(os.getenv("HF_STEPS", "8"))
    hf_seed: int = int(os.getenv("HF_SEED", "42"))
    hf_video_preset: str = os.getenv("HF_VIDEO_PRESET", "fast")
    max_movie_scenes: int = int(os.getenv("MAX_MOVIE_SCENES", "20"))
    max_prompt_length: int = int(os.getenv("MAX_PROMPT_LENGTH", "100000"))
    movie_max_duration: int = int(os.getenv("MOVIE_MAX_DURATION", "60"))

settings = Settings()
os.makedirs(settings.storage_dir, exist_ok=True)

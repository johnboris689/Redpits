import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "RedPits")
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    provider: str = os.getenv("PROVIDER", "self-hosted").strip().lower()
    storage_dir: str = os.getenv("STORAGE_DIR", "./storage")
    db_path: str = os.getenv("DB_PATH", "./storage/redpits.db")
    ai_engine_url: str = os.getenv("AI_ENGINE_URL", "http://127.0.0.1:8100")
    ai_engine_token: str = os.getenv("AI_ENGINE_TOKEN", "")
    ai_request_timeout: float = float(os.getenv("AI_REQUEST_TIMEOUT", "3600"))
    max_movie_scenes: int = int(os.getenv("MAX_MOVIE_SCENES", "20"))
    max_prompt_length: int = int(os.getenv("MAX_PROMPT_LENGTH", "100000"))
    movie_max_duration: int = int(os.getenv("MOVIE_MAX_DURATION", "60"))
    ai_max_video_seconds: int = int(os.getenv("AI_MAX_VIDEO_SECONDS", "6"))
    ai_fps: int = int(os.getenv("AI_DEFAULT_FPS", "24"))
    session_cookie_secure: bool = os.getenv("SESSION_COOKIE_SECURE", "true").lower() == "true"

settings = Settings()
os.makedirs(settings.storage_dir, exist_ok=True)

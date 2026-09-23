import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class AISettings:
    host: str = os.getenv("AI_HOST", "0.0.0.0")
    port: int = int(os.getenv("AI_PORT", "8100"))
    token: str = os.getenv("AI_ENGINE_TOKEN", "")
    device: str = os.getenv("AI_DEVICE", "cuda")
    model_dir: str = os.getenv("AI_MODEL_DIR", "./models")
    output_dir: str = os.getenv("AI_OUTPUT_DIR", "./outputs")
    max_concurrent_jobs: int = int(os.getenv("AI_MAX_CONCURRENT_JOBS", "1"))
    enable_cpu_fallback: bool = os.getenv("AI_ENABLE_CPU_FALLBACK", "false").lower() == "true"
    gpu_memory_target: float = float(os.getenv("AI_GPU_MEMORY_TARGET", "0"))
    image_model_id: str = os.getenv("IMAGE_MODEL_ID", "stabilityai/sdxl-turbo")
    ltx_repo_dir: str = os.getenv("LTX_REPO_DIR", "./models/LTX-Video")
    ltx_pipeline_config: str = os.getenv("LTX_PIPELINE_CONFIG", "configs/ltxv-2b-0.9.8-distilled.yaml")
    ltx_model_revision: str = os.getenv("LTX_MODEL_REVISION", "main")
    default_width: int = int(os.getenv("AI_DEFAULT_WIDTH", "576"))
    default_height: int = int(os.getenv("AI_DEFAULT_HEIGHT", "1024"))
    default_fps: int = int(os.getenv("AI_DEFAULT_FPS", "24"))
    default_video_seconds: int = int(os.getenv("AI_DEFAULT_VIDEO_SECONDS", "6"))
    max_video_seconds: int = int(os.getenv("AI_MAX_VIDEO_SECONDS", "6"))
    max_prompt_length: int = int(os.getenv("AI_MAX_PROMPT_LENGTH", "100000"))

settings = AISettings()
Path(settings.model_dir).mkdir(parents=True, exist_ok=True)
Path(settings.output_dir).mkdir(parents=True, exist_ok=True)

import os
import platform
import sys

from .config import settings


def inspect_hardware():
    info = {
        "gpu_available": False,
        "gpu_name": None,
        "vram_gb": 0.0,
        "cuda": False,
        "torch_version": None,
        "cuda_version": None,
        "python": platform.python_version(),
        "platform": platform.platform(),
    }
    try:
        import torch
        info["torch_version"] = torch.__version__
        info["cuda_version"] = torch.version.cuda
        info["cuda"] = bool(torch.cuda.is_available())
        info["gpu_available"] = info["cuda"]
        if info["cuda"]:
            idx = torch.cuda.current_device()
            info["gpu_name"] = torch.cuda.get_device_name(idx)
            info["vram_gb"] = round(torch.cuda.get_device_properties(idx).total_memory / (1024**3), 2)
    except Exception:
        pass
    return info


def require_device():
    hw = inspect_hardware()
    if hw["gpu_available"]:
        return "cuda"
    if settings.enable_cpu_fallback:
        return "cpu"
    raise RuntimeError("AI GPU engine is unavailable. A CUDA-capable NVIDIA GPU is required for production inference.")

from .config import settings

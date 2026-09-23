
import os
import subprocess
import sys
from pathlib import Path

from .config import settings

LTX_URL = "https://github.com/Lightricks/LTX-Video.git"


def run(cmd, cwd=None):
    print("$", " ".join(cmd))
    subprocess.check_call(cmd, cwd=cwd)


def main():
    model_root = Path(settings.model_dir).resolve()
    model_root.mkdir(parents=True, exist_ok=True)
    hf_cache = model_root / "hf-cache"
    hf_cache.mkdir(parents=True, exist_ok=True)

    os.environ.setdefault("HF_HOME", str(hf_cache))
    os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(hf_cache / "hub"))
    os.environ.setdefault("TRANSFORMERS_CACHE", str(hf_cache / "transformers"))

    repo = Path(settings.ltx_repo_dir).resolve()
    if not repo.exists():
        run(["git", "clone", "--depth", "1", LTX_URL, str(repo)])

    from .patch_ltx import main as patch_ltx
    patch_ltx()

    # Install the official local LTX inference package.
    run([sys.executable, "-m", "pip", "install", "-e", ".[inference]"], cwd=repo)

    import yaml
    from huggingface_hub import hf_hub_download, snapshot_download

    cfg = repo / settings.ltx_pipeline_config
    if not cfg.exists():
        raise FileNotFoundError(f"LTX pipeline config not found: {cfg}")

    with cfg.open("r", encoding="utf-8") as fh:
        ltx_cfg = yaml.safe_load(fh)

    for key in ("checkpoint_path", "spatial_upscaler_model_path"):
        filename = ltx_cfg.get(key)
        if filename:
            print("Preparing LTX asset:", filename)
            hf_hub_download(
                repo_id="Lightricks/LTX-Video",
                filename=filename,
                repo_type="model",
                cache_dir=str(hf_cache),
                local_dir=str(repo),
            )

    print("Preparing local image model cache:", settings.image_model_id)
    snapshot_download(
        repo_id=settings.image_model_id,
        cache_dir=str(hf_cache),
    )

    text_encoder = ltx_cfg.get("text_encoder_model_name_or_path")
    if text_encoder:
        print("Preparing LTX text encoder cache:", text_encoder)
        snapshot_download(
            repo_id=text_encoder,
            cache_dir=str(hf_cache),
        )

    marker = model_root / ".redpits_setup_complete"
    marker.write_text("ready\n", encoding="utf-8")
    print("RedPits local AI assets are ready.")


if __name__ == "__main__":
    main()

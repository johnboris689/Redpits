from pathlib import Path
import re

from .config import settings

ROOT = Path(settings.ltx_repo_dir)
INFERENCE = ROOT / "ltx_video" / "inference.py"
PIPELINE = ROOT / "ltx_video" / "pipelines" / "pipeline_ltx_video.py"


def replace_once(path: Path, pattern: str, replacement: str, flags=re.S):
    text = path.read_text(encoding="utf-8")
    if replacement in text:
        return False
    new, count = re.subn(pattern, replacement, text, count=1, flags=flags)
    if count != 1:
        raise RuntimeError(f"Expected LTX source block was not found in {path}")
    path.write_text(new, encoding="utf-8")
    return True


def main():
    if not INFERENCE.exists() or not PIPELINE.exists():
        raise SystemExit("LTX-Video source is not installed. Run setup after cloning LTX-Video.")

    changed = 0
    changed += replace_once(
        INFERENCE,
        r'    prompt_enhancement_words_threshold = pipeline_config\[\s*"prompt_enhancement_words_threshold"\s*\]\s*\n\s*prompt_word_count = len\(config\.prompt\.split\(\)\)\s*\n\s*enhance_prompt = \(.*?\n\s*if prompt_enhancement_words_threshold > 0 and not enhance_prompt:\s*\n\s*logger\.info\(.*?\n\s*\)\s*',
        '''    prompt_word_count = len(config.prompt.split())\n\n    # RedPits production/T4 patch: disable LTX prompt enhancement.\n    # The optional Florence-2 + LLM enhancer consumes several GB of VRAM.\n    enhance_prompt = False\n'''
    )
    changed += replace_once(
        INFERENCE,
        r'    text_encoder = text_encoder\\.to\\(device\\)',
        '''    # RedPits T4-safe patch: keep the large T5 text encoder on CPU.
    # The pipeline handles temporary CPU/GPU movement when offload_to_cpu is enabled.
    text_encoder = text_encoder.to("cpu")''',
    )
    changed += replace_once(
        INFERENCE,
        r'    pipeline = LTXVideoPipeline\(\*\*submodel_dict\)\s*\n\s*pipeline = pipeline\.to\(device\)\s*\n\s*return pipeline',
        '''    pipeline = LTXVideoPipeline(**submodel_dict)\n    # Keep the large T5 text encoder on CPU when CPU offloading is enabled.\n    # Calling pipeline.to(device) would move it to a 15 GB T4 and can OOM.\n    return pipeline'''
    )
    changed += replace_once(
        PIPELINE,
        r'        if self\.text_encoder is not None:\s*\n\s*self\.text_encoder = self\.text_encoder\.to\(self\._execution_device\)',
        '''        if self.text_encoder is not None and not offload_to_cpu:\n            self.text_encoder = self.text_encoder.to(self._execution_device)'''
    )
    print(f"LTX RedPits patch complete: {changed} change(s)")


if __name__ == "__main__":
    main()

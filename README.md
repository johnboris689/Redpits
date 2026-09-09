# RedPits — Free AI Video & Media Generator

RedPits is a self-hostable AI creative workspace for text-to-video, image-to-video, text-to-image, stickers and short movie assembly.

## Free architecture
Render hosts the FastAPI web app. AI inference is delegated to public Hugging Face Gradio Spaces running on ZeroGPU. The default path requires no Gemini/Veo, Replicate, OpenAI or OpenRouter billing.

Default Spaces:
- `techfreakworm/LTX2.3-Studio` — video and image-to-video
- `mrfakename/Z-Image-Turbo` — images and stickers

Hugging Face ZeroGPU has daily quotas and shared queues. Free therefore means **no payment required**, not unlimited GPU time.

## Quick start
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Install FFmpeg for movie assembly.

## Environment
```env
PROVIDER=huggingface
HF_VIDEO_SPACE=techfreakworm/LTX2.3-Studio
HF_IMAGE_SPACE=mrfakename/Z-Image-Turbo
HF_TOKEN=
```
Public Spaces work without a token. A free Hugging Face token can improve authenticated access and quota handling.

The free video path intentionally uses short clips (6 seconds by default) and caps a movie job at 60 seconds. This avoids promising workloads that cannot realistically fit a free ZeroGPU quota.

## No fake generation
`mock` remains available only for local UI testing. The default `huggingface` provider performs real inference through Gradio APIs and stores returned media in RedPits storage.

## Rights
Use media and likenesses you have permission to use. RedPits does not bypass provider safety systems or remove provider-owned watermarks.

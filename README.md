# RedPits — Self-Hosted AI Creative Studio

RedPits is a real AI creative web application designed around a **self-hosted GPU AI engine**. The web application and GPU inference service are separate so the same RedPits software can move from a free GPU test environment to rented GPU infrastructure and eventually to a physical NVIDIA GPU server.

## What is self-hosted

RedPits does not use Gemini, Veo, Replicate, Hugging Face Spaces, or another company's AI-generation API for production inference.

Open-source model weights may be downloaded during setup. Inference happens locally on the RedPits AI machine.

The first local engines are:

- **LTX-Video 2B distilled** for text-to-video and image-to-video.
- **SDXL Turbo** for local text-to-image.
- **Local background removal** for transparent sticker output.
- **FFmpeg** for movie assembly and media processing.

The LTX-Video project documents local inference and lists its 2B distilled model as the lighter model for lower VRAM environments. citeturn2search1turn2search2 SDXL Turbo is loaded locally through Diffusers; it is not called as a hosted inference API.

## Architecture

```text
User
  ↓
RedPits Web/API
  ↓
RedPits Job Queue
  ↓
Private AI Engine API
  ↓
NVIDIA GPU
  ├── Local video model
  ├── Local image model
  ├── Local sticker processing
  └── FFmpeg
  ↓
Local/Object Storage
```

## Services

### Web service

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### GPU AI service

```bash
uvicorn ai_engine.main:app --host 0.0.0.0 --port 8100
```

The AI service exposes authenticated internal endpoints for health, model discovery, uploads, jobs, cancellation and output retrieval.

## GPU setup

See:

- `SELF_HOSTED_AI.md`
- `GPU_SETUP.md`
- `MODEL_SETUP.md`
- `DEPLOYMENT.md`

The AI setup script installs the official LTX-Video local inference package. LTX's official repository documents `pip install -e .[inference]`, local `inference.py`, image conditioning, and the 2B distilled configuration. citeturn2search0turn2search1

## Free GPU testing

The code is provider-independent. A free GPU environment can be used only as the first compute host for testing. It is not treated as part of the RedPits application or as an AI API dependency.

If the free environment has no compatible NVIDIA GPU, RedPits reports that the AI GPU engine is unavailable instead of returning fake media.

## Moving to a paid or physical GPU

Change the AI engine host/configuration only. The web application and API contract remain the same.

```text
Free GPU test
     ↓
Rented GPU server
     ↓
Physical NVIDIA GPU server
```

## Important

Free GPU compute is not unlimited. The self-hosted architecture removes AI API billing/dependency, but the hardware used for inference still has a real compute cost unless you have access to free hardware.

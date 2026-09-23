# RedPits + Lightning AI GPU

RedPits uses Lightning as a compute host only. The generation models run locally on the Lightning GPU; RedPits does not call Gemini, Veo, Replicate, Hugging Face Spaces, or another hosted generation API.

## Architecture

```text
Render / RedPits Web
        |
        | HTTPS + Authorization: Bearer <AI_ENGINE_TOKEN>
        v
Lightning Studio GPU :8100
        |
        +-- LTX-Video 2B distilled (video / image-to-video)
        +-- SDXL Turbo (images)
        +-- rembg (stickers)
        +-- FFmpeg
```

## Lightning Studio

Create a GPU Studio and use a persistent Studio filesystem for the model cache.

From the RedPits root inside the Studio:

```bash
python -m pip install -r ai_engine/requirements.txt
export AI_ENGINE_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
export AI_AUTO_SETUP=true
python -m ai_engine.entrypoint
```

The first start can take a long time because it downloads local model assets. Do not stop the process during setup.

The AI service listens on port `8100`.

Use Lightning's **Ports** plugin to expose port `8100` with a public or authenticated URL. Keep `AI_ENGINE_TOKEN` secret. The browser must never receive this token.

## Render

Set these environment variables on the RedPits web service:

```text
PROVIDER=self-hosted
AI_ENGINE_URL=https://YOUR-LIGHTNING-PORT-URL
AI_ENGINE_TOKEN=THE-SAME-RANDOM-TOKEN
AI_REQUEST_TIMEOUT=3600
SESSION_COOKIE_SECURE=true
```

The web server sends the token only from the server side to the AI engine.

## Health check

With the engine exposed, the web service calls:

```text
GET /health
Authorization: Bearer <token>
```

The engine reports:

- GPU availability
- GPU name
- VRAM
- model/setup readiness
- queued jobs

RedPits refuses to create a generation job if the GPU engine is offline, has no NVIDIA GPU, or has not completed local model setup.

## Important

A Lightning API key is not the same thing as the RedPits AI engine token.

- Lightning credentials authenticate you to Lightning.
- `AI_ENGINE_TOKEN` authenticates RedPits to your own RedPits AI service.

Never put either secret into frontend JavaScript.

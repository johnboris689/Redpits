# RedPits Self-Hosted AI

## Goal

The AI engine is a separate service from the RedPits web application. The frontend never talks directly to the GPU service.

```text
Browser → RedPits API → AI job → private AI engine → GPU → output
```

The same AI engine can run on a free test GPU, a rented GPU server, or a physical NVIDIA machine.

## AI endpoints

- `GET /health`
- `GET /models`
- `POST /files`
- `POST /jobs`
- `GET /jobs/{job_id}`
- `POST /jobs/{job_id}/cancel`
- `GET /outputs/{name}`

All endpoints can require `Authorization: Bearer <AI_ENGINE_TOKEN>`.

## Generation types

- `video`: local text-to-video
- `image-to-video`: local image-conditioned video
- `image`: local text-to-image
- `sticker`: local image generation followed by local background removal

Audio is deliberately not exposed as a fake feature. It can be added later as another local model adapter.

## Model adapters

Model-specific code lives under `ai_engine/models/`. The registry makes it possible to replace a model without changing the web API.

# Model Setup

## Video — LTX-Video 2B distilled

RedPits uses the official LTX-Video local inference package and the `ltxv-2b-0.9.8-distilled.yaml` configuration by default. The official repository documents the same local inference mechanism and identifies the 2B distilled model as the lighter model. citeturn2search1turn2search2

The first inference downloads missing model assets and caches them locally. No hosted generation API is used.

To switch to a stronger local LTX model later, change:

```text
LTX_PIPELINE_CONFIG=configs/ltxv-13b-0.9.8-distilled.yaml
```

Only do this after confirming the GPU has enough VRAM.

## Image — SDXL Turbo

Default:

```text
IMAGE_MODEL_ID=stabilityai/sdxl-turbo
```

The model is loaded through Diffusers into the local GPU process. The model weights are cached locally.

## Sticker

Sticker generation creates an image locally and then runs local background removal to produce a transparent PNG. No image-removal API is called.

## Model storage

Set:

```text
AI_MODEL_DIR=/models
```

on a persistent disk so model weights are not re-downloaded when the GPU service restarts.

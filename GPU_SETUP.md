# GPU Setup

## Minimum practical starting point

The first RedPits test profile uses:

- NVIDIA GPU with CUDA
- 8 GB+ VRAM for the lightweight LTX-Video 2B path
- 16 GB+ is preferable for image generation and larger settings
- 16 GB+ system RAM recommended
- SSD storage for model weights and generated media

The official LTX-Video repository describes the 2B distilled model as the smaller, lower-VRAM option and the 13B models as higher-quality but more demanding. citeturn2search2turn2search1

## Check the GPU

```bash
nvidia-smi
```

Then:

```bash
python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NO CUDA GPU')"
```

## Install the local AI engine

From the RedPits root:

```bash
python -m pip install -r ai_engine/requirements.txt
python -m ai_engine.setup
```

The setup clones the official LTX-Video repository and installs its local inference package. Model weights are cached locally when inference first needs them.

## Start the AI service

```bash
uvicorn ai_engine.main:app --host 0.0.0.0 --port 8100
```

Then check:

```bash
curl http://127.0.0.1:8100/health
```

## No GPU

With `AI_ENABLE_CPU_FALLBACK=false`, generation fails clearly rather than pretending to generate media.

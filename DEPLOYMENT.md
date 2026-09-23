# Deployment

## Recommended separation

### Web

Run the RedPits web/API service on normal web infrastructure.

### GPU

Run `ai_engine` on GPU-capable infrastructure.

The web service needs:

```text
AI_ENGINE_URL=https://private-or-secured-ai-host:8100
AI_ENGINE_TOKEN=<same-secret-as-ai-server>
```

The browser never receives the token.

## Free GPU test

Use any free GPU environment that permits a persistent Python process/container for your own testing. Install the AI engine there and point `AI_ENGINE_URL` at its private or authenticated endpoint.

Do not hard-code the provider name in RedPits.

## Rented GPU

Move the same `ai_engine` directory and persistent model volume to a GPU VPS/server. Keep the same HTTP API and change only the web service's `AI_ENGINE_URL` and the shared token.

## Physical GPU

Install Linux, NVIDIA drivers, CUDA-compatible PyTorch, Docker/NVIDIA Container Toolkit, then run the same `ai_engine` container. Put the GPU machine behind a private network or VPN. Do not expose the raw inference service to the public internet unless it is strongly authenticated and rate-limited.

## Domain

A domain such as `redpits.com` can point to the web service. The domain is independent of the GPU host.

# RedPit — complete starter source

This repository combines the RedPit Flask backend with the redesigned responsive creator-studio onboarding UI.

## Run locally

Python 3.10+ is required. Install dependencies with `pip install -r requirements.txt`, then run `python app.py`.

## Deploy on Render

The included `render.yaml` defines the Flask web service. The app uses Gunicorn (`gunicorn app:app --workers 1 --threads 4 --timeout 120`). Set `REDPIT_SECRET` to a long random secret. Attach a persistent disk and configure the app's database/uploads/renders paths for durable user data before production use.

## Current capabilities and limitations

- Flask registration/login and SQLite-backed project/scene endpoints.
- Offline template-based script starter.
- FFmpeg-based vertical video rendering from uploaded images or generated text title cards, with uploaded audio/music when supplied.
- Redesigned RedPit onboarding interface.

The onboarding's social-account connection and scheduled-publishing screens are UI demonstrations, not live OAuth or publishing integrations. The offline script starter is not an AI language model. The renderer does not generate AI images or natural-sounding narration; FFmpeg must be installed on the host for MP4 rendering. The current onboarding form is not yet wired to save its settings as a series through the backend.

Before public production use, add CSRF protection, rate limiting, stronger session configuration, persistent storage, and validate uploads. Do not use the default Flask secret in production.


# RedPit — Self-hosted AI Video Studio

RedPit is a lightweight, self-hostable faceless-video production workspace. It includes account registration/login, project management, an offline script starter, scene editing, image/audio uploads, and MP4 rendering through FFmpeg.

## Important feature notes

- The script starter uses local templates. It is **not** a full AI language model.
- Voiceovers are uploaded audio files. Text-to-speech is not bundled into this first release.
- Scene visuals can be uploaded, or RedPit creates branded title cards.
- Video rendering requires FFmpeg installed on the machine running RedPit.
- Social publishing is manual: download the MP4 and upload it to your platform.
- No paid API keys are required. No external AI API is called.

## Run locally (Windows 10)

1. Install Python 3.10 or newer from https://www.python.org/downloads/ and enable **Add Python to PATH**.
2. Install FFmpeg from https://ffmpeg.org/download.html and add its `bin` folder to PATH.
3. Open Command Prompt in this project folder.
4. Run:

```bash
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
py app.py
```

5. Open http://127.0.0.1:5000

For low-RAM computers, close other applications before rendering. Use a small number of scenes and modest image file sizes.

## Run on Termux (Android)

Termux can run the web app for development/testing, though rendering on a phone may be slow.

```bash
pkg update
pkg install python git ffmpeg
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000 in your phone browser.

## Deploy on Render

This repo includes `render.yaml` and `Procfile` for a basic deployment. Connect your GitHub repository to Render and deploy the web service.

**Free-hosting limitations:** free web services may sleep, have limited CPU/RAM, and may use ephemeral storage. The SQLite database, uploads and rendered files in this starter are stored locally, so they may not persist across redeploys or instance restarts on hosts with ephemeral disks. For reliable long-term production, use a persistent disk or host RedPit on your own PC/server. A free public web host is not guaranteed to support FFmpeg rendering.

## Security before public production

- Set a long, random `REDPIT_SECRET` environment variable.
- Use HTTPS through your hosting provider.
- Add rate limiting, CSRF protection, password reset, email verification, backups, and persistent storage before opening public registration to strangers.
- Do not expose a development server directly to the public internet.

## GitHub

After creating your empty GitHub repository, from this project folder:

```bash
git init
git add .
git commit -m "Initial RedPit release"
git branch -M main
git remote add origin YOUR_GITHUB_REPOSITORY_URL
git push -u origin main
```

## Current release

This is a functional first foundation, not a claim of feature parity with commercial faceless-video platforms. The next releases can add local TTS, optional local LLM integration, subtitle timing, richer transitions, and publishing integrations without paid AI API keys.


import os
import subprocess
import sys

def main():
    auto = os.getenv("AI_AUTO_SETUP", "true").lower() == "true"
    marker = os.path.join(os.getenv("AI_MODEL_DIR", "./models"), ".redpits_setup_complete")
    if auto and not os.path.exists(marker):
        subprocess.check_call([sys.executable, "-m", "ai_engine.setup"])
    os.execvp(
        sys.executable,
        [sys.executable, "-m", "uvicorn", "ai_engine.main:app",
         "--host", os.getenv("AI_HOST", "0.0.0.0"),
         "--port", os.getenv("AI_PORT", "8100")],
    )

if __name__ == "__main__":
    main()

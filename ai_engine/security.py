from fastapi import Header, HTTPException
from .config import settings

def require_token(authorization: str | None = Header(default=None)):
    if not settings.token:
        return
    expected = f"Bearer {settings.token}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Invalid AI engine credentials.")

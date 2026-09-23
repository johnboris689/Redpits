import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, Request
from .db import execute, one

SESSION_DAYS = 30

def now():
    return datetime.now(timezone.utc).isoformat()

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return "scrypt$16384$8$1$" + base64.urlsafe_b64encode(salt).decode() + "$" + base64.urlsafe_b64encode(digest).decode()

def verify_password(password: str, stored: str) -> bool:
    try:
        _, n, r, p, salt_b64, digest_b64 = stored.split("$", 5)
        salt = base64.urlsafe_b64decode(salt_b64.encode())
        expected = base64.urlsafe_b64decode(digest_b64.encode())
        actual = hashlib.scrypt(password.encode(), salt=salt, n=int(n), r=int(r), p=int(p))
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False

def create_session(user_id: str) -> str:
    token = secrets.token_urlsafe(48)
    expires = (datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)).isoformat()
    execute("INSERT INTO sessions(token,user_id,created_at,expires_at) VALUES(?,?,?,?)", (token, user_id, now(), expires))
    return token

def get_user(request: Request):
    token = request.cookies.get("redpits_session")
    if not token:
        return None
    row = one("SELECT u.id,u.email,u.created_at,s.expires_at FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=?", (token,))
    if not row:
        return None
    try:
        if datetime.fromisoformat(row["expires_at"]) <= datetime.now(timezone.utc):
            execute("DELETE FROM sessions WHERE token=?", (token,))
            return None
    except Exception:
        return None
    return row

def require_user(request: Request):
    user = get_user(request)
    if not user:
        raise HTTPException(401, "Please log in or create an account before using the studio.")
    return user

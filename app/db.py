import sqlite3
from .config import settings

def conn():
    c = sqlite3.connect(settings.db_path)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with conn() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS projects(
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            prompt TEXT NOT NULL,
            mode TEXT NOT NULL,
            output_url TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS jobs(
            id TEXT PRIMARY KEY,
            project_id TEXT,
            kind TEXT NOT NULL,
            status TEXT NOT NULL,
            progress INTEGER NOT NULL DEFAULT 0,
            message TEXT NOT NULL DEFAULT '',
            output_url TEXT,
            error TEXT,
            created_at TEXT NOT NULL
        );
        """)
        cols = {r["name"] for r in db.execute("PRAGMA table_info(projects)").fetchall()}
        if "output_url" not in cols:
            db.execute("ALTER TABLE projects ADD COLUMN output_url TEXT")
        db.commit()

def execute(sql, args=()):
    with conn() as db:
        db.execute(sql, args); db.commit()

def one(sql, args=()):
    with conn() as db:
        r = db.execute(sql, args).fetchone(); return dict(r) if r else None

def all_rows(sql, args=()):
    with conn() as db:
        return [dict(r) for r in db.execute(sql, args).fetchall()]

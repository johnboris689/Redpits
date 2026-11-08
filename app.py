
import os, sqlite3, uuid, json, subprocess, shutil, re, math
from datetime import datetime
from functools import wraps
from pathlib import Path
from flask import Flask, request, jsonify, session, redirect, send_from_directory, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).resolve().parent
UPLOADS = BASE / "uploads"
RENDERS = BASE / "renders"
DB = BASE / "redpit.db"
for folder in (UPLOADS, RENDERS):
    folder.mkdir(exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("REDPIT_SECRET", "change-this-secret-before-public-deployment")
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            topic TEXT DEFAULT '',
            script TEXT DEFAULT '',
            voice_file TEXT DEFAULT '',
            music_file TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS scenes (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            title TEXT NOT NULL,
            narration TEXT DEFAULT '',
            image_file TEXT DEFAULT '',
            duration REAL DEFAULT 5,
            sort_order INTEGER DEFAULT 0,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        );
        """)
init_db()

def current_user():
    if not session.get("user_id"):
        return None
    with db() as con:
        return con.execute("SELECT id,email FROM users WHERE id=?", (session["user_id"],)).fetchone()

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            return jsonify({"error":"Please sign in first."}), 401
        return fn(*args, **kwargs)
    return wrapper

def project_for_user(project_id, user_id):
    with db() as con:
        return con.execute("SELECT * FROM projects WHERE id=? AND user_id=?", (project_id,user_id)).fetchone()

@app.get("/")
def home():
    return send_from_directory(BASE / "frontend-preview", "index.html")

@app.get("/assets/<path:filename>")
def frontend_assets(filename):
    return send_from_directory(BASE / "frontend-preview" / "assets", filename)

@app.get("/api/me")
def me():
    u = current_user()
    return jsonify({"user": dict(u) if u else None})

@app.post("/api/register")
def register():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return jsonify({"error":"Enter a valid email address."}), 400
    if len(password) < 8:
        return jsonify({"error":"Password must be at least 8 characters."}), 400
    try:
        with db() as con:
            cur = con.execute("INSERT INTO users(email,password,created_at) VALUES(?,?,?)",
                (email, generate_password_hash(password), datetime.utcnow().isoformat()))
            session["user_id"] = cur.lastrowid
        return jsonify({"ok":True})
    except sqlite3.IntegrityError:
        return jsonify({"error":"An account with that email already exists."}), 409

@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    with db() as con:
        u = con.execute("SELECT * FROM users WHERE email=?", ((data.get("email") or "").strip().lower(),)).fetchone()
    if not u or not check_password_hash(u["password"], data.get("password") or ""):
        return jsonify({"error":"Incorrect email or password."}), 401
    session["user_id"] = u["id"]
    return jsonify({"ok":True})

@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify({"ok":True})

@app.get("/api/projects")
@login_required
def list_projects():
    u = current_user()
    with db() as con:
        rows = con.execute("""
          SELECT p.*, (SELECT COUNT(*) FROM scenes s WHERE s.project_id=p.id) AS scene_count
          FROM projects p WHERE p.user_id=? ORDER BY p.created_at DESC
        """, (u["id"],)).fetchall()
    return jsonify([dict(r) for r in rows])

@app.post("/api/projects")
@login_required
def create_project():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "Untitled project").strip()[:100]
    topic = (data.get("topic") or "").strip()[:500]
    pid = uuid.uuid4().hex[:12]
    with db() as con:
        con.execute("INSERT INTO projects(id,user_id,title,topic,created_at) VALUES(?,?,?,?,?)",
                    (pid,current_user()["id"],title,topic,datetime.utcnow().isoformat()))
    return jsonify({"id":pid,"title":title})

@app.get("/api/projects/<pid>")
@login_required
def get_project(pid):
    p = project_for_user(pid,current_user()["id"])
    if not p: return jsonify({"error":"Project not found."}),404
    with db() as con:
        scenes = con.execute("SELECT * FROM scenes WHERE project_id=? ORDER BY sort_order", (pid,)).fetchall()
    return jsonify({"project":dict(p),"scenes":[dict(s) for s in scenes]})

@app.patch("/api/projects/<pid>")
@login_required
def update_project(pid):
    p = project_for_user(pid,current_user()["id"])
    if not p: return jsonify({"error":"Project not found."}),404
    data = request.get_json(silent=True) or {}
    with db() as con:
        con.execute("UPDATE projects SET title=?,topic=?,script=? WHERE id=?",
          ((data.get("title",p["title"]) or p["title"])[:100],
           data.get("topic",p["topic"]), data.get("script",p["script"]),pid))
    return jsonify({"ok":True})

@app.delete("/api/projects/<pid>")
@login_required
def delete_project(pid):
    p = project_for_user(pid,current_user()["id"])
    if not p: return jsonify({"error":"Project not found."}),404
    with db() as con:
        scenes = con.execute("SELECT image_file FROM scenes WHERE project_id=?", (pid,)).fetchall()
        for s in scenes:
            if s["image_file"]: (UPLOADS/s["image_file"]).unlink(missing_ok=True)
        con.execute("DELETE FROM scenes WHERE project_id=?", (pid,))
        con.execute("DELETE FROM projects WHERE id=?", (pid,))
    shutil.rmtree(RENDERS/pid, ignore_errors=True)
    return jsonify({"ok":True})

@app.post("/api/projects/<pid>/script")
@login_required
def make_script(pid):
    p = project_for_user(pid,current_user()["id"])
    if not p: return jsonify({"error":"Project not found."}),404
    data = request.get_json(silent=True) or {}
    topic = (data.get("topic") or p["topic"] or "A surprising idea").strip()
    style = data.get("style","educational")
    # Offline starter writer: deterministic templates, no external API or internet request.
    hooks = {
      "educational": "Have you ever wondered about {topic}? The answer may surprise you.",
      "story": "It started with one simple question: what if {topic} was not what we thought?",
      "mystery": "There is something fascinating about {topic} that most people overlook.",
      "motivational": "Your next breakthrough could begin when you understand {topic}."
    }
    body = (
      f"{hooks.get(style,hooks['educational']).format(topic=topic)}\n\n"
      f"First, let's break it down. {topic} connects to everyday life in more ways than most people realise. "
      "The key is to look beyond the obvious and pay attention to the small details.\n\n"
      "Here is the important part: start with one clear idea, test what you learn, and build on it. "
      "Simple steps repeated consistently can lead to meaningful results.\n\n"
      f"So the next time you think about {topic}, remember this: curiosity is where progress begins. "
      "Follow for more ideas, and save this video so you can revisit it."
    )
    with db() as con:
        con.execute("UPDATE projects SET topic=?,script=? WHERE id=?", (topic,body,pid))
    return jsonify({"script":body,"mode":"offline-template","notice":"This is an offline script starter, not a large-language-model response. You can edit it or connect a local model later."})

@app.post("/api/projects/<pid>/scenes")
@login_required
def add_scene(pid):
    p = project_for_user(pid,current_user()["id"])
    if not p: return jsonify({"error":"Project not found."}),404
    data = request.get_json(silent=True) or {}
    sid = uuid.uuid4().hex[:12]
    with db() as con:
        n = con.execute("SELECT COUNT(*) n FROM scenes WHERE project_id=?", (pid,)).fetchone()["n"]
        con.execute("INSERT INTO scenes(id,project_id,title,narration,duration,sort_order) VALUES(?,?,?,?,?,?)",
          (sid,pid,(data.get("title") or f"Scene {n+1}")[:100],data.get("narration",""),max(2,min(30,float(data.get("duration",5))),),n))
    return jsonify({"id":sid})

@app.patch("/api/scenes/<sid>")
@login_required
def update_scene(sid):
    with db() as con:
        row = con.execute("""SELECT s.*,p.user_id FROM scenes s JOIN projects p ON p.id=s.project_id
                             WHERE s.id=? AND p.user_id=?""",(sid,current_user()["id"])).fetchone()
        if not row: return jsonify({"error":"Scene not found."}),404
        d=request.get_json(silent=True) or {}
        con.execute("UPDATE scenes SET title=?,narration=?,duration=? WHERE id=?",
          ((d.get("title",row["title"]) or row["title"])[:100],d.get("narration",row["narration"]),
           max(2,min(30,float(d.get("duration",row["duration"])))),sid))
    return jsonify({"ok":True})

@app.delete("/api/scenes/<sid>")
@login_required
def delete_scene(sid):
    with db() as con:
        row=con.execute("""SELECT s.* FROM scenes s JOIN projects p ON p.id=s.project_id
                           WHERE s.id=? AND p.user_id=?""",(sid,current_user()["id"])).fetchone()
        if not row:return jsonify({"error":"Scene not found."}),404
        if row["image_file"]:(UPLOADS/row["image_file"]).unlink(missing_ok=True)
        con.execute("DELETE FROM scenes WHERE id=?",(sid,))
    return jsonify({"ok":True})

@app.post("/api/projects/<pid>/upload/<kind>")
@login_required
def upload_asset(pid,kind):
    p=project_for_user(pid,current_user()["id"])
    if not p:return jsonify({"error":"Project not found."}),404
    if kind not in ("voice","music"):return jsonify({"error":"Unsupported asset type."}),400
    f=request.files.get("file")
    if not f:return jsonify({"error":"Choose a file first."}),400
    ext=Path(secure_filename(f.filename)).suffix.lower()
    allowed={".mp3",".wav",".m4a",".ogg",".aac"}
    if ext not in allowed:return jsonify({"error":"Use MP3, WAV, M4A, OGG or AAC audio."}),400
    name=f"{pid}_{kind}_{uuid.uuid4().hex[:8]}{ext}"
    f.save(UPLOADS/name)
    col="voice_file" if kind=="voice" else "music_file"
    with db() as con:con.execute(f"UPDATE projects SET {col}=? WHERE id=?",(name,pid))
    return jsonify({"ok":True,"filename":name})

@app.post("/api/scenes/<sid>/image")
@login_required
def upload_scene_image(sid):
    with db() as con:
        row=con.execute("""SELECT s.* FROM scenes s JOIN projects p ON p.id=s.project_id
                           WHERE s.id=? AND p.user_id=?""",(sid,current_user()["id"])).fetchone()
        if not row:return jsonify({"error":"Scene not found."}),404
        f=request.files.get("file")
        if not f:return jsonify({"error":"Choose an image."}),400
        ext=Path(secure_filename(f.filename)).suffix.lower()
        if ext not in (".png",".jpg",".jpeg",".webp"):return jsonify({"error":"Use PNG, JPG or WEBP."}),400
        name=f"{sid}_{uuid.uuid4().hex[:8]}{ext}"
        f.save(UPLOADS/name)
        con.execute("UPDATE scenes SET image_file=? WHERE id=?",(name,sid))
    return jsonify({"ok":True,"filename":name})

def get_font(size, bold=False):
    candidates = [
      "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
      "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"
    ]
    for f in candidates:
        try:return ImageFont.truetype(f,size)
        except:pass
    return ImageFont.load_default()

def make_card(scene, out, index):
    w,h=1080,1920
    im=Image.new("RGB",(w,h),(12,12,18))
    px=im.load()
    for y in range(h):
        for x in range(w):
            glow=max(0,1-math.sqrt(((x-850)/900)**2+((y-250)/900)**2))
            px[x,y]=(int(12+65*glow),int(10+5*glow),int(18+12*glow))
    d=ImageDraw.Draw(im)
    d.rounded_rectangle((76,100,1004,1800),radius=44,outline=(100,35,48),width=3)
    d.text((110,140),"REDPIT  /  AI VIDEO STUDIO",font=get_font(32,True),fill=(255,75,95))
    d.text((110,260),f"SCENE {index+1:02d}",font=get_font(30,True),fill=(255,110,125))
    title=scene["title"]
    words=title.split()
    lines=[]; line=""
    for word in words:
        test=(line+" "+word).strip()
        if d.textbbox((0,0),test,font=get_font(76,True))[2] > 820 and line:
            lines.append(line);line=word
        else:line=test
    if line:lines.append(line)
    y=760
    for line in lines[:5]:
        d.text((110,y),line,font=get_font(76,True),fill=(250,248,250),stroke_width=1,stroke_fill=(40,20,30))
        y+=105
    narration=scene.get("narration","")
    d.text((110,1450),"WATCH • LEARN • CREATE",font=get_font(30,True),fill=(190,180,190))
    im.save(out,quality=92)

@app.post("/api/projects/<pid>/render")
@login_required
def render_video(pid):
    p=project_for_user(pid,current_user()["id"])
    if not p:return jsonify({"error":"Project not found."}),404
    ffmpeg=shutil.which("ffmpeg")
    if not ffmpeg:return jsonify({"error":"FFmpeg is not installed. Install FFmpeg and add it to PATH, then try again."}),400
    with db() as con:
        scenes=[dict(x) for x in con.execute("SELECT * FROM scenes WHERE project_id=? ORDER BY sort_order",(pid,)).fetchall()]
    if not scenes:return jsonify({"error":"Add at least one scene before rendering."}),400
    work=RENDERS/pid
    work.mkdir(parents=True,exist_ok=True)
    inputs=[]
    for i,s in enumerate(scenes):
        src=UPLOADS/s["image_file"] if s["image_file"] and (UPLOADS/s["image_file"]).exists() else None
        if src:
            img=Image.open(src).convert("RGB")
            # Fit and crop to vertical 9:16.
            target=Image.new("RGB",(1080,1920),(10,10,16))
            img.thumbnail((1080,1920))
            target.paste(img,((1080-img.width)//2,(1920-img.height)//2))
            card=work/f"scene_{i:03d}.jpg";target.save(card,quality=90)
        else:
            card=work/f"scene_{i:03d}.jpg";make_card(s,card,i)
        inputs.append((card,max(2,min(30,float(s["duration"] or 5)))))
    concat=work/"concat.txt"
    with open(concat,"w",encoding="utf-8") as f:
        for path,duration in inputs:
            f.write(f"file '{path.as_posix()}'\nduration {duration}\n")
        f.write(f"file '{inputs[-1][0].as_posix()}'\n")
    output=RENDERS/f"{pid}_redpit.mp4"
    cmd=[ffmpeg,"-y","-f","concat","-safe","0","-i",str(concat),"-r","30","-vf",
         "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
         "-c:v","libx264","-preset","ultrafast","-crf","25"]
    audio=UPLOADS/(p["voice_file"] or "")
    music=UPLOADS/(p["music_file"] or "")
    if audio.exists():
        cmd += ["-i",str(audio),"-map","0:v:0","-map","1:a:0","-shortest"]
    elif music.exists():
        cmd += ["-i",str(music),"-map","0:v:0","-map","1:a:0","-shortest"]
    else:
        cmd += ["-an"]
    cmd += ["-movflags","+faststart",str(output)]
    try:
        result=subprocess.run(cmd,capture_output=True,text=True,timeout=900)
        if result.returncode!=0:return jsonify({"error":"FFmpeg could not render this project: "+(result.stderr[-900:] or "Unknown error")}),500
    except subprocess.TimeoutExpired:
        return jsonify({"error":"Rendering took too long. Try shorter scenes or smaller images."}),500
    return jsonify({"ok":True,"url":f"/renders/{output.name}","filename":output.name})

@app.get("/uploads/<path:name>")
@login_required
def uploaded(name):
    return send_from_directory(UPLOADS,name)

@app.get("/renders/<path:name>")
@login_required
def rendered(name):
    return send_from_directory(RENDERS,name,as_attachment=True)

@app.get("/health")
def health():
    return jsonify({"status":"ok","app":"RedPit"})

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)),debug=False)

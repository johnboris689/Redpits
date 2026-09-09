import subprocess
from pathlib import Path
import httpx

def split_story(story, max_scenes):
    story = story.replace("\r", "").strip()
    if not story: return []
    raw_parts = [p.strip() for p in story.split("\n\n") if p.strip()]
    parts=[]
    for block in raw_parts:
        sentences=[s.strip() for s in block.replace("!", ".").replace("?", ".").split(".") if s.strip()]
        buf=[]; size=0
        for sentence in sentences:
            if size + len(sentence) > 900 and buf:
                parts.append(". ".join(buf).strip()+"."); buf=[]; size=0
            buf.append(sentence); size += len(sentence)+2
        if buf: parts.append(". ".join(buf).strip() + ("" if block.endswith((".","!","?")) else "."))
    return parts[:max_scenes]

async def download(url, target):
    async with httpx.AsyncClient(timeout=600, follow_redirects=True) as client:
        r=await client.get(url); r.raise_for_status(); target.write_bytes(r.content)

def assemble(paths, output):
    if not paths: raise RuntimeError("No scene clips were generated")
    list_file=output.parent/"concat.txt"; normalized=[]
    try:
        for i,p in enumerate(paths):
            n=output.parent/f"normalized-{i:03d}.mp4"
            subprocess.run(["ffmpeg","-y","-i",str(p),"-vf","scale=trunc(iw/2)*2:trunc(ih/2)*2","-r","30","-c:v","libx264","-preset","veryfast","-crf","20","-c:a","aac","-b:a","192k","-ar","48000","-ac","2",str(n)],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            normalized.append(n)
        with list_file.open("w",encoding="utf-8") as f:
            for p in normalized: f.write("file '"+str(p).replace("'","'\\''")+"'\n")
        subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(list_file),"-c","copy","-movflags","+faststart",str(output)],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    finally:
        list_file.unlink(missing_ok=True)
        for p in normalized: p.unlink(missing_ok=True)
    return output

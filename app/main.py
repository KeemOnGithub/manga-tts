from __future__ import annotations

import shutil
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import db
from .config import settings
from .services.qwen_tts import TTSUnavailable, create_voice
from .worker import start_worker, stop_worker


STATIC = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    db.init_db()
    start_worker()
    yield
    stop_worker()


app = FastAPI(title="PageTurn Audio", version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


class PassageEdit(BaseModel):
    text: str = Field(max_length=20000)
    speaker_id: str | None = None


class SpeakerEdit(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    voice_prompt: str = Field(default="", max_length=2048)


class PreviewRequest(BaseModel):
    preview_text: str = Field(default="Hello. This is a sample of my audiobook voice.", min_length=1, max_length=256)


def _project(project_id: str):
    with db.connect() as conn:
        row = conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Project not found")
    return dict(row)


@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/health")
def health():
    return {"status": "ok", "text_model_configured": bool(settings.text_api_key),
            "text_model": settings.text_model, "tts_model": settings.tts_model}


@app.get("/api/projects")
def list_projects():
    with db.connect() as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM projects ORDER BY updated_at DESC")]


@app.post("/api/projects/upload", status_code=202)
async def upload_pdf(file: UploadFile = File(...)):
    filename = Path(file.filename or "upload.pdf").name
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(415, "Upload a PDF file.")
    contents = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(contents) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"PDF exceeds the {settings.max_upload_mb} MB upload limit.")
    if not contents.startswith(b"%PDF-"):
        raise HTTPException(415, "The uploaded file does not appear to be a valid PDF.")
    project_id = db.new_id()
    project_dir = settings.data_dir / "projects" / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = project_dir / "source.pdf"
    pdf_path.write_bytes(contents)
    title = Path(filename).stem[:180] or "Untitled audiobook"
    with db.connect() as conn:
        conn.execute("INSERT INTO projects(id,title,source_name,status,created_at,updated_at) VALUES(?,?,?,'extracting',?,?)",
                     (project_id, title, filename, db.now(), db.now()))
        conn.execute("INSERT INTO artifacts(project_id,pdf_path) VALUES(?,?)", (project_id, str(pdf_path)))
    job_id = db.create_job(project_id, "extract")
    return {"project_id": project_id, "job_id": job_id}


@app.get("/api/projects/{project_id}")
def get_project(project_id: str):
    project = _project(project_id)
    with db.connect() as conn:
        passages = [dict(row) for row in conn.execute("SELECT * FROM passages WHERE project_id=? ORDER BY ordinal", (project_id,))]
        speakers = [dict(row) for row in conn.execute("SELECT id,name,voice_prompt,voice_id,CASE WHEN preview_path IS NULL THEN 0 ELSE 1 END AS has_preview,is_narrator FROM speakers WHERE project_id=? ORDER BY is_narrator DESC,name", (project_id,))]
        jobs = [dict(row) for row in conn.execute("SELECT id,kind,status,stage,progress,error,result,created_at FROM jobs WHERE project_id=? ORDER BY created_at DESC LIMIT 10", (project_id,))]
        artifact = conn.execute("SELECT mp3_path FROM artifacts WHERE project_id=?", (project_id,)).fetchone()
    for job in jobs:
        if job["result"]:
            import json
            job["result"] = json.loads(job["result"])
    project["passages"] = passages
    project["speakers"] = speakers
    project["jobs"] = jobs
    project["audio_url"] = f"/api/projects/{project_id}/audio" if artifact and artifact["mp3_path"] and Path(artifact["mp3_path"]).exists() else None
    return project


@app.post("/api/projects/{project_id}/analysis", status_code=202)
def start_analysis(project_id: str):
    _project(project_id)
    job_id = db.create_job(project_id, "analyze")
    return {"job_id": job_id}


@app.put("/api/projects/{project_id}/passages/{passage_id}")
def edit_passage(project_id: str, passage_id: str, edit: PassageEdit):
    _project(project_id)
    with db.connect() as conn:
        row = conn.execute("SELECT id FROM passages WHERE id=? AND project_id=?", (passage_id, project_id)).fetchone()
        if not row:
            raise HTTPException(404, "Passage not found")
        if edit.speaker_id and not conn.execute("SELECT 1 FROM speakers WHERE id=? AND project_id=?", (edit.speaker_id, project_id)).fetchone():
            raise HTTPException(400, "Speaker does not belong to this project.")
        conn.execute("UPDATE passages SET text=?,speaker_id=? WHERE id=?",
                     (edit.text, edit.speaker_id, passage_id))
        audio_rows = conn.execute("SELECT path FROM audio_segments WHERE passage_id=?", (passage_id,)).fetchall()
        conn.execute("DELETE FROM audio_segments WHERE passage_id=?", (passage_id,))
        conn.execute("UPDATE artifacts SET mp3_path=NULL WHERE project_id=?", (project_id,))
    for audio in audio_rows:
        Path(audio["path"]).unlink(missing_ok=True)
    return {"saved": True}


@app.patch("/api/projects/{project_id}/speakers/{speaker_id}")
def edit_speaker(project_id: str, speaker_id: str, edit: SpeakerEdit):
    _project(project_id)
    with db.connect() as conn:
        row = conn.execute("SELECT id,voice_prompt FROM speakers WHERE id=? AND project_id=?", (speaker_id, project_id)).fetchone()
        if not row:
            raise HTTPException(404, "Speaker not found")
        changed_voice = row["voice_prompt"] != edit.voice_prompt
        if changed_voice:
            voice = conn.execute("SELECT voice_id,preview_path FROM speakers WHERE id=?", (speaker_id,)).fetchone()
            paths = conn.execute("SELECT path FROM audio_segments WHERE passage_id IN (SELECT id FROM passages WHERE speaker_id=?)", (speaker_id,)).fetchall()
            conn.execute("UPDATE speakers SET name=?,voice_prompt=?,voice_id=NULL,preview_path=NULL WHERE id=?",
                         (edit.name.strip(), edit.voice_prompt.strip(), speaker_id))
            conn.execute("DELETE FROM audio_segments WHERE passage_id IN (SELECT id FROM passages WHERE speaker_id=?)", (speaker_id,))
            conn.execute("UPDATE artifacts SET mp3_path=NULL WHERE project_id=?", (project_id,))
        else:
            conn.execute("UPDATE speakers SET name=? WHERE id=?", (edit.name.strip(), speaker_id))
    if changed_voice:
        if voice["preview_path"]:
            Path(voice["preview_path"]).unlink(missing_ok=True)
        # A changed voice profile invalidates audio for this speaker.
        for item in paths:
            Path(item["path"]).unlink(missing_ok=True)
    return {"saved": True, "voice_needs_preview": changed_voice}


@app.post("/api/projects/{project_id}/speakers/{speaker_id}/preview", status_code=201)
def preview_speaker(project_id: str, speaker_id: str, request: PreviewRequest):
    _project(project_id)
    with db.connect() as conn:
        speaker = conn.execute("SELECT * FROM speakers WHERE id=? AND project_id=?", (speaker_id, project_id)).fetchone()
    if not speaker:
        raise HTTPException(404, "Speaker not found")
    try:
        voice_id, preview_bytes = create_voice(speaker["voice_prompt"], f"pt_{speaker_id[:12]}", request.preview_text)
    except TTSUnavailable as exc:
        raise HTTPException(502, str(exc)) from exc
    if not preview_bytes:
        raise HTTPException(502, "The voice was created, but the service did not return preview audio.")
    preview_path = settings.data_dir / "projects" / project_id / f"preview-{speaker_id}.wav"
    preview_path.write_bytes(preview_bytes)
    with db.connect() as conn:
        conn.execute("UPDATE speakers SET voice_id=?,preview_path=? WHERE id=?", (voice_id, str(preview_path), speaker_id))
    return {"voice_id": voice_id, "preview_url": f"/api/projects/{project_id}/speakers/{speaker_id}/preview"}


@app.get("/api/projects/{project_id}/speakers/{speaker_id}/preview")
def get_preview(project_id: str, speaker_id: str):
    _project(project_id)
    with db.connect() as conn:
        row = conn.execute("SELECT preview_path FROM speakers WHERE id=? AND project_id=?", (speaker_id, project_id)).fetchone()
    if not row or not row["preview_path"] or not Path(row["preview_path"]).exists():
        raise HTTPException(404, "No voice preview is available.")
    return FileResponse(row["preview_path"], media_type="audio/wav")


@app.post("/api/projects/{project_id}/audio", status_code=202)
def start_audio(project_id: str):
    _project(project_id)
    with db.connect() as conn:
        missing = conn.execute("""
            SELECT DISTINCT s.name FROM passages p LEFT JOIN speakers s ON s.id=p.speaker_id
            WHERE p.project_id=? AND (s.id IS NULL OR s.voice_id IS NULL OR s.voice_id='') LIMIT 1
        """, (project_id,)).fetchone()
    if missing:
        raise HTTPException(409, f"Create a voice preview for '{missing['name'] or 'an assigned speaker'}' before generating audio.")
    job_id = db.create_job(project_id, "audio")
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@app.get("/api/projects/{project_id}/audio")
def download_audio(project_id: str):
    _project(project_id)
    with db.connect() as conn:
        row = conn.execute("SELECT mp3_path FROM artifacts WHERE project_id=?", (project_id,)).fetchone()
    if not row or not row["mp3_path"] or not Path(row["mp3_path"]).exists():
        raise HTTPException(404, "Audiobook is not ready yet.")
    return FileResponse(row["mp3_path"], media_type="audio/mpeg", filename="audiobook.mp3")


@app.delete("/api/projects/{project_id}", status_code=204)
def delete_project(project_id: str):
    _project(project_id)
    project_dir = settings.data_dir / "projects" / project_id
    with db.connect() as conn:
        conn.execute("DELETE FROM projects WHERE id=?", (project_id,))
    shutil.rmtree(project_dir, ignore_errors=True)

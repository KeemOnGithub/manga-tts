from __future__ import annotations

import json
import shutil
import threading
import time
import wave
from pathlib import Path

from . import db
from .config import settings
from .services.audio import assemble_mp3
from .services.pdf import extract_pdf
from .services.qwen_tts import create_voice, synthesize
from .services.text_model import analyze_passages


_stop = threading.Event()
_thread: threading.Thread | None = None


def start_worker() -> None:
    global _thread
    db.recover_interrupted_jobs()
    if _thread is None or not _thread.is_alive():
        _stop.clear()
        _thread = threading.Thread(target=_run, name="audiobook-worker", daemon=True)
        _thread.start()


def stop_worker() -> None:
    _stop.set()
    if _thread and _thread.is_alive():
        _thread.join(timeout=3)


def _project_dir(project_id: str) -> Path:
    return settings.data_dir / "projects" / project_id


def _fail(job_id: str, message: str) -> None:
    db.update_job(job_id, status="failed", stage="Failed", error=message[:1200])
    job = db.get_job(job_id)
    if job:
        with db.connect() as conn:
            conn.execute("UPDATE projects SET status='error', updated_at=? WHERE id=?", (db.now(), job["project_id"]))


def _run() -> None:
    while not _stop.is_set():
        job = db.claim_queued_job()
        if job is None:
            _stop.wait(0.6)
            continue
        try:
            if job["kind"] == "extract":
                _extract(job)
            elif job["kind"] == "analyze":
                _analyze(job)
            elif job["kind"] == "audio":
                _audio(job)
            else:
                raise ValueError(f"Unknown job type: {job['kind']}")
        except Exception as exc:  # Persist worker errors for the UI.
            _fail(job["id"], str(exc))


def _extract(job: dict) -> None:
    project_id, job_id = job["project_id"], job["id"]
    db.update_job(job_id, stage="Extracting PDF text", progress=0.1)
    with db.connect() as conn:
        artifact = conn.execute("SELECT pdf_path FROM artifacts WHERE project_id=?", (project_id,)).fetchone()
    if not artifact:
        raise ValueError("Uploaded PDF was not found for this project.")
    page_count, blocks = extract_pdf(Path(artifact["pdf_path"]), settings.max_pdf_pages)
    with db.connect() as conn:
        conn.execute("DELETE FROM passages WHERE project_id=?", (project_id,))
        for index, (page, text) in enumerate(blocks):
            conn.execute("INSERT INTO passages(id,project_id,ordinal,page,source_text,text) VALUES(?,?,?,?,?,?)",
                         (db.new_id(), project_id, index, page, text, text))
        conn.execute("UPDATE projects SET page_count=?,status='ready',updated_at=? WHERE id=?",
                     (page_count, db.now(), project_id))
    db.update_job(job_id, status="completed", stage="Text extracted", progress=1,
                  result={"page_count": page_count, "passage_count": len(blocks)})


def _analyze(job: dict) -> None:
    project_id, job_id = job["project_id"], job["id"]
    with db.connect() as conn:
        passages = [dict(row) for row in conn.execute("SELECT id,text,page,ordinal FROM passages WHERE project_id=? ORDER BY ordinal", (project_id,))]
        old_speakers = [dict(row) for row in conn.execute("SELECT * FROM speakers WHERE project_id=?", (project_id,))]
    if not passages:
        raise ValueError("Extract text from the PDF before running speaker analysis.")
    speaker_map = {speaker["name"].casefold(): speaker for speaker in old_speakers}
    # Keep requests bounded while carrying known character identities between chunks.
    groups: list[list[dict]] = []
    current: list[dict] = []
    chars = 0
    for passage in passages:
        size = len(passage["text"])
        if current and (len(current) >= 24 or chars + size > 14000):
            groups.append(current)
            current, chars = [], 0
        current.append(passage)
        chars += size
    if current:
        groups.append(current)
    for chunk_index, group in enumerate(groups):
        db.update_job(job_id, stage=f"Analyzing text ({chunk_index + 1}/{len(groups)})", progress=chunk_index / len(groups))
        response = analyze_passages(group, list(speaker_map.values()))
        items = response.get("passages") if isinstance(response, dict) else None
        if not isinstance(items, list):
            raise ValueError("Text model returned an invalid response: expected a passages array.")
        source_ids = {item["id"] for item in group}
        parsed: dict[str, dict] = {}
        for item in items:
            if not isinstance(item, dict) or item.get("passage_id") not in source_ids:
                continue
            parsed[item["passage_id"]] = item
        for passage in group:
            answer = parsed.get(passage["id"], {})
            name = str(answer.get("speaker_name") or "Unknown").strip()[:100]
            confidence = answer.get("confidence")
            try:
                confidence = max(0, min(1, float(confidence))) if confidence is not None else None
            except (TypeError, ValueError):
                confidence = None
            key = name.casefold()
            if key not in speaker_map:
                is_narrator = int(key == "narrator")
                speaker_id = db.new_id()
                description = str(answer.get("voice_description") or "")[:2048]
                with db.connect() as conn:
                    conn.execute("INSERT INTO speakers(id,project_id,name,voice_prompt,is_narrator) VALUES(?,?,?,?,?)",
                                 (speaker_id, project_id, name, description, is_narrator))
                speaker_map[key] = {"id": speaker_id, "project_id": project_id, "name": name,
                                    "voice_prompt": description, "voice_id": None, "is_narrator": is_narrator}
            with db.connect() as conn:
                conn.execute("UPDATE passages SET speaker_id=?,confidence=? WHERE id=?",
                             (speaker_map[key]["id"], confidence, passage["id"]))
    with db.connect() as conn:
        conn.execute("UPDATE projects SET status='review',updated_at=? WHERE id=?", (db.now(), project_id))
    db.update_job(job_id, status="completed", stage="Speaker analysis ready for review", progress=1,
                  result={"speaker_count": len(speaker_map), "passage_count": len(passages)})


def _audio(job: dict) -> None:
    project_id, job_id = job["project_id"], job["id"]
    project_dir = _project_dir(project_id)
    audio_dir = project_dir / "segments"
    audio_dir.mkdir(parents=True, exist_ok=True)
    with db.connect() as conn:
        passages = [dict(row) for row in conn.execute("SELECT * FROM passages WHERE project_id=? ORDER BY ordinal", (project_id,))]
        speakers = {row["id"]: dict(row) for row in conn.execute("SELECT * FROM speakers WHERE project_id=?", (project_id,))}
        existing_rows = conn.execute("SELECT passage_id,path FROM audio_segments WHERE project_id=? ORDER BY created_at,path", (project_id,)).fetchall()
    existing: dict[str, list[str]] = {}
    for row in existing_rows:
        existing.setdefault(row["passage_id"], []).append(row["path"])
    if not passages:
        raise ValueError("There is no extracted text to synthesize.")
    audio_paths: list[Path] = []
    for index, passage in enumerate(passages):
        if not passage["text"].strip():
            continue
        speaker = speakers.get(passage["speaker_id"])
        if not speaker:
            raise ValueError("Assign a speaker to every passage before generating audio.")
        segment_paths = [Path(item) for item in existing.get(passage["id"], [])]
        if segment_paths and all(path.exists() for path in segment_paths):
            audio_paths.extend(segment_paths)
            continue
        # Keep each provider request comfortably below long-form request limits.
        remaining = passage["text"].strip()
        text_chunks: list[str] = []
        while len(remaining) > 1600:
            split_at = remaining.rfind(" ", 0, 1600)
            if split_at < 800:
                split_at = 1600
            text_chunks.append(remaining[:split_at].strip())
            remaining = remaining[split_at:].strip()
        if remaining:
            text_chunks.append(remaining)
        if segment_paths:
            with db.connect() as conn:
                conn.execute("DELETE FROM audio_segments WHERE passage_id=?", (passage["id"],))
            for old_path in segment_paths:
                old_path.unlink(missing_ok=True)
        for part_index, text_chunk in enumerate(text_chunks):
            path = audio_dir / f"{passage['id']}-part-{part_index:03d}.wav"
            if not path.exists():
                db.update_job(job_id, stage=f"Generating audio ({index + 1}/{len(passages)}, part {part_index + 1}/{len(text_chunks)})",
                              progress=(index + part_index / max(1, len(text_chunks))) / len(passages))
                voice_id = speaker.get("voice_id")
                if not voice_id:
                    raise ValueError(f"Create and preview a voice for '{speaker['name']}' before generating the audiobook.")
                audio, fmt = synthesize(text_chunk, voice_id)
                path = path.with_suffix("." + (fmt or "wav").lower().replace("mpeg", "mp3"))
                path.write_bytes(audio)
                with db.connect() as conn:
                    conn.execute("INSERT INTO audio_segments(id,project_id,passage_id,path,created_at) VALUES(?,?,?,?,?)",
                                 (db.new_id(), project_id, passage["id"], str(path), db.now()))
            audio_paths.append(path)
    db.update_job(job_id, stage="Assembling MP3", progress=0.95)
    output_path = project_dir / "audiobook.mp3"
    assemble_mp3(audio_paths, output_path)
    with db.connect() as conn:
        conn.execute("UPDATE artifacts SET mp3_path=? WHERE project_id=?", (str(output_path), project_id))
        conn.execute("UPDATE projects SET status='complete',updated_at=? WHERE id=?", (db.now(), project_id))
    db.update_job(job_id, status="completed", stage="Audiobook ready", progress=1,
                  result={"download_url": f"/api/projects/{project_id}/audio"})

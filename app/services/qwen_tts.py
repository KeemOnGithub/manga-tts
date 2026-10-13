from __future__ import annotations

import base64
import json
from pathlib import Path
from urllib.parse import urlparse

import requests

from ..config import settings


class TTSUnavailable(RuntimeError):
    pass


def _headers() -> dict[str, str]:
    if not settings.text_api_key:
        raise TTSUnavailable("DASHSCOPE_API_KEY is not configured. Add your Model Studio Singapore API key to .env.")
    return {"Authorization": f"Bearer {settings.text_api_key}", "Content-Type": "application/json"}


def create_voice(description: str, preferred_name: str, preview_text: str = "Hello. This is a sample of my audiobook voice.") -> tuple[str, bytes | None]:
    if not description.strip():
        raise TTSUnavailable("Add a voice description before creating a voice.")
    payload = {
        "model": "qwen-voice-design",
        "input": {
            "action": "create",
            "target_model": settings.tts_model,
            "preferred_name": preferred_name[:64],
            "voice_prompt": description[:2048],
            "preview_text": preview_text[:256],
            "language": settings.tts_language,
        },
        "parameters": {"sample_rate": 24000, "response_format": "wav"},
    }
    try:
        response = requests.post(f"{settings.tts_api_base.rstrip('/')}/services/audio/tts/customization",
                                 headers=_headers(), json=payload, timeout=(15, 180))
        response.raise_for_status()
        output = response.json().get("output", {})
        voice_id = output.get("voice")
        if not voice_id:
            raise TTSUnavailable("Voice Design response did not contain a voice ID.")
        preview = output.get("preview_audio", {}).get("data")
        return voice_id, base64.b64decode(preview) if preview else None
    except requests.RequestException as exc:
        detail = exc.response.text[:800] if exc.response is not None else str(exc)
        raise TTSUnavailable(f"Voice creation failed: {detail}") from exc


def synthesize(text: str, voice_id: str) -> tuple[bytes, str]:
    payload = {"model": settings.tts_model, "input": {"text": text, "voice": voice_id, "format": "wav", "sample_rate": 24000}}
    try:
        response = requests.post(f"{settings.tts_api_base.rstrip('/')}/services/audio/tts/SpeechSynthesizer",
                                 headers=_headers(), json=payload, timeout=(15, 180))
        response.raise_for_status()
        body = response.json()
        output = body.get("output", {})
        audio = output.get("audio") or output.get("audio_url")
        if isinstance(audio, dict):
            if audio.get("data"):
                return base64.b64decode(audio["data"]), audio.get("format", "wav")
            audio = audio.get("url")
        if isinstance(audio, str) and audio.startswith("data:"):
            return base64.b64decode(audio.split(",", 1)[1]), "wav"
        if isinstance(audio, str) and urlparse(audio).scheme == "https":
            fetched = requests.get(audio, timeout=(15, 180))
            fetched.raise_for_status()
            return fetched.content, Path(urlparse(audio).path).suffix.lstrip(".") or "wav"
        raise TTSUnavailable(f"TTS response did not contain downloadable audio: {json.dumps(body)[:700]}")
    except requests.RequestException as exc:
        detail = exc.response.text[:800] if exc.response is not None else str(exc)
        raise TTSUnavailable(f"Speech synthesis failed: {detail}") from exc

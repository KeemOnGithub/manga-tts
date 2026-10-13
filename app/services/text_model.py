from __future__ import annotations

import json

import requests

from ..config import settings


class ModelError(RuntimeError):
    pass


def analyze_passages(passages: list[dict], existing_speakers: list[dict]) -> dict:
    if not settings.text_api_key:
        raise ModelError("DASHSCOPE_API_KEY is not configured. Add your Model Studio Singapore API key to .env.")
    payload = {
        "model": settings.text_model,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": (
                "Analyze audiobook passages. Do not rewrite or omit source text. Return one JSON object with "
                "a passages array; each item must contain passage_id, speaker_name (use Narrator for narration "
                "or Unknown when uncertain), confidence from 0 to 1, and optional voice_description for a newly "
                "identified speaker. Keep speaker names stable. Voice descriptions must describe vocal qualities, "
                "not imitate a real person. Existing speaker names: " + ", ".join(s["name"] for s in existing_speakers)
            )},
            {"role": "user", "content": json.dumps({"passages": passages}, ensure_ascii=False)},
        ],
    }
    try:
        response = requests.post(
            f"{settings.text_api_base.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {settings.text_api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=(15, 180),
        )
        response.raise_for_status()
        raw = response.json()["choices"][0]["message"]["content"]
        if isinstance(raw, list):
            raw = "".join(part.get("text", "") for part in raw if isinstance(part, dict))
        return json.loads(raw)
    except (requests.RequestException, KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise ModelError(f"Text analysis failed: {exc}") from exc

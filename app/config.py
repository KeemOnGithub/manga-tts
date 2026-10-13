from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    data_dir: Path = Path(os.getenv("AUDIOBOOK_DATA_DIR", str(ROOT / "data")))
    database_path: Path = Path(os.getenv("AUDIOBOOK_DATABASE", str(ROOT / "data" / "audiobook.sqlite3")))
    text_api_key: str = os.getenv("DASHSCOPE_API_KEY", "")
    text_api_base: str = os.getenv("QWEN_TEXT_API_BASE", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1")
    text_model: str = os.getenv("QWEN_TEXT_MODEL", "qwen3.8-flash")
    tts_api_base: str = os.getenv("QWEN_TTS_API_BASE", "https://dashscope-intl.aliyuncs.com/api/v1")
    tts_model: str = os.getenv("QWEN_TTS_MODEL", "qwen3-tts-vd-2026-01-26")
    tts_language: str = os.getenv("QWEN_TTS_LANGUAGE", "en")
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "50"))
    max_pdf_pages: int = int(os.getenv("MAX_PDF_PAGES", "500"))


settings = Settings()

from __future__ import annotations

from pathlib import Path

import fitz


def extract_pdf(path: Path, page_limit: int) -> tuple[int, list[tuple[int, str]]]:
    document = fitz.open(path)
    if document.is_encrypted:
        raise ValueError("Password-protected PDFs are not supported yet.")
    if document.page_count > page_limit:
        raise ValueError(f"This PDF has {document.page_count} pages; the current limit is {page_limit}.")
    passages: list[tuple[int, str]] = []
    for page_index, page in enumerate(document, start=1):
        text = page.get_text("text", sort=True)
        blocks = [" ".join(line.strip() for line in block.splitlines() if line.strip())
                  for block in text.split("\n\n")]
        blocks = [block.strip() for block in blocks if block.strip()]
        if not blocks and not text.strip():
            try:
                import pytesseract
                from PIL import Image
                import io
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                blocks = [pytesseract.image_to_string(Image.open(io.BytesIO(pix.tobytes("png"))), lang="eng").strip()]
                blocks = [block for block in blocks if block]
            except ImportError:
                pass
            except Exception as exc:
                raise ValueError(f"OCR failed on page {page_index}: {exc}") from exc
        for block in blocks:
            remaining = block.strip()
            while len(remaining) > 1800:
                split_at = remaining.rfind(" ", 0, 1800)
                if split_at < 900:
                    split_at = 1800
                passages.append((page_index, remaining[:split_at].strip()))
                remaining = remaining[split_at:].strip()
            if remaining:
                passages.append((page_index, remaining))
    if not passages:
        raise ValueError("No text could be extracted. The PDF may be scanned; install/configure Tesseract OCR and try again.")
    return document.page_count, passages

"""Per-type processing for uploaded files.

Each helper takes raw bytes + filename, returns (file_type, extracted_text).
extracted_text is None for binary types (images, video — handled at chat
build-time by referencing the S3 URL instead).

Type detection is by extension. Magic-byte detection deliberately not used —
extension-based mapping is simpler and good enough for the current set of
supported types. The endpoint clamps total size before any processing.
"""
from __future__ import annotations

import io
import logging
import os
from typing import Optional

logger = logging.getLogger("jarvis.files")

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
PDF_EXTS = {".pdf"}
CSV_EXTS = {".csv"}
TEXT_EXTS = {".txt", ".md", ".markdown", ".log"}
VIDEO_EXTS = {".mp4", ".mov", ".webm", ".avi"}

MAX_BYTES = 20 * 1024 * 1024  # 20 MB hard cap


def detect_type(filename: str) -> str:
    """Return image/pdf/csv/text/video/unknown based on extension."""
    ext = os.path.splitext(filename or "")[1].lower()
    if ext in IMAGE_EXTS:
        return "image"
    if ext in PDF_EXTS:
        return "pdf"
    if ext in CSV_EXTS:
        return "csv"
    if ext in TEXT_EXTS:
        return "text"
    if ext in VIDEO_EXTS:
        return "video"
    return "unknown"


def extract_pdf(data: bytes) -> str:
    """Best-effort PDF text extraction via pypdf. Returns empty string on
    failure (scanned PDFs, encrypted, etc.)."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        out: list[str] = []
        for page in reader.pages[:50]:  # cap at 50 pages
            try:
                out.append(page.extract_text() or "")
            except Exception:
                continue
        return "\n\n".join(p for p in out if p).strip()
    except Exception:
        logger.exception("pdf extract failed")
        return ""


def extract_csv(data: bytes, max_rows: int = 100) -> str:
    """Parse a CSV and return a compact markdown table. Caps at max_rows."""
    try:
        import pandas as pd
        df = pd.read_csv(io.BytesIO(data), nrows=max_rows)
        return df.to_markdown(index=False)
    except Exception:
        logger.exception("csv parse failed")
        try:
            # plain-text fallback — show the first 4 KB
            return data[:4096].decode("utf-8", errors="replace")
        except Exception:
            return ""


def extract_text(data: bytes) -> str:
    try:
        return data.decode("utf-8", errors="replace")
    except Exception:
        return ""


def process(filename: str, data: bytes) -> tuple[str, Optional[str]]:
    """Dispatch to the right processor. Returns (file_type, extracted_text).
    extracted_text is None for binary file types (image/video)."""
    kind = detect_type(filename)
    if kind == "pdf":
        return kind, extract_pdf(data)
    if kind == "csv":
        return kind, extract_csv(data)
    if kind == "text":
        return kind, extract_text(data)
    if kind in ("image", "video", "unknown"):
        # No text extraction — content goes to the model via image_url at chat time.
        return kind, None
    return kind, None

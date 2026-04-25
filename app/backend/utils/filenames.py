"""Filename sanitization helpers."""

from __future__ import annotations

import re
from pathlib import Path

MAX_FILENAME_LENGTH = 180
RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
}


def sanitize_filename(value: str, fallback: str = "download") -> str:
    """Return a cross-platform-safe filename stem or filename."""

    cleaned = re.sub(r"[<>:\"/\\|?*\x00-\x1F]", "-", value).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = cleaned.strip(" .")
    if not cleaned:
        cleaned = fallback
    if cleaned.upper() in RESERVED_NAMES:
        cleaned = f"{cleaned}-file"
    return cleaned[:MAX_FILENAME_LENGTH]


def safe_join(base_directory: Path, filename: str) -> Path:
    """Join a filename to a base directory without allowing traversal."""

    base = base_directory.expanduser().resolve()
    raw_path = Path(filename)
    if raw_path.is_absolute() or ".." in raw_path.parts:
        raise ValueError("Output path escapes the configured output directory")
    candidate = (base / sanitize_filename(filename)).resolve()
    if base != candidate.parent and base not in candidate.parents:
        raise ValueError("Output path escapes the configured output directory")
    return candidate

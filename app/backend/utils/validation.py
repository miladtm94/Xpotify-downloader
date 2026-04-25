"""URL and source detection helpers."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Optional
from urllib.parse import unquote, urlparse

DIRECT_AUDIO_EXTENSIONS = {".mp3", ".m4a", ".flac", ".wav", ".ogg", ".opus"}
DIRECT_VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov"}
DIRECT_MEDIA_EXTENSIONS = DIRECT_AUDIO_EXTENSIONS | DIRECT_VIDEO_EXTENSIONS


def parse_http_url(url: str):
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return parsed


def is_spotify_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme == "spotify":
        return True
    return parsed.netloc.lower() == "open.spotify.com" and parsed.path


def get_url_extension(url: str) -> Optional[str]:
    parsed = urlparse(url)
    suffix = PurePosixPath(unquote(parsed.path)).suffix.lower()
    return suffix or None


def is_direct_media_url(url: str) -> bool:
    return parse_http_url(url) is not None and get_url_extension(url) in DIRECT_MEDIA_EXTENSIONS


def direct_media_type(url: str) -> str:
    extension = get_url_extension(url)
    if extension in DIRECT_AUDIO_EXTENSIONS:
        return "audio"
    if extension in DIRECT_VIDEO_EXTENSIONS:
        return "video"
    return "unknown"


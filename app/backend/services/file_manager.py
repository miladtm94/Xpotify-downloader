"""Filesystem helpers for downloads."""

from __future__ import annotations

from pathlib import Path

from app.backend.models.settings import AppSettings
from app.backend.utils.filenames import sanitize_filename


class FileManager:
    """Owns safe output path decisions."""

    def __init__(self, settings: AppSettings):
        self.settings = settings

    def output_directory(self, override: Path | None = None) -> Path:
        directory = (override or self.settings.output_directory).expanduser()
        directory.mkdir(parents=True, exist_ok=True)
        return directory.resolve()

    def available_path(
        self, filename: str, extension: str, output_directory: Path | None = None
    ) -> Path:
        directory = self.output_directory(output_directory)
        clean_stem = sanitize_filename(Path(filename).stem)
        clean_extension = extension.lower().lstrip(".")
        candidate = directory / f"{clean_stem}.{clean_extension}"
        counter = 2
        while candidate.exists():
            candidate = directory / f"{clean_stem} ({counter}).{clean_extension}"
            counter += 1
        return candidate


"""Filesystem helpers for downloads."""

from __future__ import annotations

from pathlib import Path

from app.backend.models.settings import AppSettings
from app.backend.utils.filenames import sanitize_filename


class FileManager:
    """Owns safe output path decisions."""

    def __init__(self, settings: AppSettings):
        self.settings = settings

    def output_directory(
        self,
        override: Path | None = None,
        subfolder: str | None = None,
    ) -> Path:
        base = override.expanduser() if override else self.settings.output_directory
        if override and not base.is_absolute():
            base = self.settings.output_directory / base
        directory = self._append_subfolder(base, subfolder)
        directory.mkdir(parents=True, exist_ok=True)
        return directory.resolve()

    def available_path(
        self,
        filename: str,
        extension: str,
        output_directory: Path | None = None,
        output_subfolder: str | None = None,
    ) -> Path:
        directory = self.output_directory(output_directory, output_subfolder)
        clean_stem = sanitize_filename(Path(filename).stem)
        clean_extension = extension.lower().lstrip(".")
        candidate = directory / f"{clean_stem}.{clean_extension}"
        counter = 2
        while candidate.exists():
            candidate = directory / f"{clean_stem} ({counter}).{clean_extension}"
            counter += 1
        return candidate

    def _append_subfolder(self, base: Path, subfolder: str | None) -> Path:
        if not subfolder:
            return base.expanduser()

        directory = base.expanduser()
        for part in Path(subfolder).parts:
            if part in {"", ".", ".."}:
                continue
            directory = directory / sanitize_filename(part)
        return directory

"""Provider for lawful public video platform URLs through yt-dlp."""

from __future__ import annotations

import asyncio
import json
import re
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse, urlunparse
from uuid import uuid4

from app.backend.models.download_job import DownloadJob
from app.backend.models.download_result import (
    DownloadResult,
    MediaMetadata,
    ProviderCapability,
    StructuredError,
    ValidationResult,
)
from app.backend.models.settings import AppSettings
from app.backend.providers.base import DownloadProvider, ProgressCallback, ProviderError
from app.backend.services.file_manager import FileManager

KNOWN_PLATFORM_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "youtu.be",
    "x.com",
    "twitter.com",
    "www.x.com",
    "www.twitter.com",
    "facebook.com",
    "www.facebook.com",
    "m.facebook.com",
    "mobile.facebook.com",
    "web.facebook.com",
    "fb.watch",
    "instagram.com",
    "www.instagram.com",
    "m.instagram.com",
    "vimeo.com",
    "www.vimeo.com",
    "tiktok.com",
    "www.tiktok.com",
}
KNOWN_PLATFORM_SUFFIXES = {
    ".youtube.com",
    ".x.com",
    ".twitter.com",
    ".facebook.com",
    ".instagram.com",
    ".vimeo.com",
    ".tiktok.com",
}
IGNORED_YT_DLP_EXTRACTORS = {"GenericIE", "KnownPiracyIE"}

QUALITY_FORMATS = {
    "best": "bestvideo+bestaudio/best",
    "high": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
    "medium": "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
    "low": "bestvideo[height<=480]+bestaudio/best[height<=480]/best",
}
QUICKTIME_QUALITY_FORMATS = {
    "best": (
        "bestvideo[ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a][acodec^=mp4a]/"
        "best[ext=mp4][vcodec^=avc1][acodec^=mp4a]/"
        "bestvideo+bestaudio/best"
    ),
    "high": (
        "bestvideo[ext=mp4][vcodec^=avc1][height<=1080]+"
        "bestaudio[ext=m4a][acodec^=mp4a]/"
        "best[ext=mp4][vcodec^=avc1][acodec^=mp4a][height<=1080]/"
        "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best"
    ),
    "medium": (
        "bestvideo[ext=mp4][vcodec^=avc1][height<=720]+"
        "bestaudio[ext=m4a][acodec^=mp4a]/"
        "best[ext=mp4][vcodec^=avc1][acodec^=mp4a][height<=720]/"
        "bestvideo[height<=720]+bestaudio/best[height<=720]/best"
    ),
    "low": (
        "bestvideo[ext=mp4][vcodec^=avc1][height<=480]+"
        "bestaudio[ext=m4a][acodec^=mp4a]/"
        "best[ext=mp4][vcodec^=avc1][acodec^=mp4a][height<=480]/"
        "bestvideo[height<=480]+bestaudio/best[height<=480]/best"
    ),
}
VIDEO_FORMATS = {"mp4", "webm", "mov"}
QUICKTIME_FORMATS = {"mp4", "mov"}
QUICKTIME_AUDIO_CODECS = {"aac", "mp3"}
QUICKTIME_PIXEL_FORMATS = {"yuv420p", "yuvj420p"}
VIDEO_QUALITY_LABELS = {
    2160: "2160p UHD",
    1440: "1440p QHD",
    1080: "1080p FHD",
    720: "720p HD",
    480: "480p SD",
    360: "360p",
    240: "240p",
    144: "144p",
}


class VideoProvider(DownloadProvider):
    """Downloads public, non-DRM platform videos when yt-dlp can access them."""

    name = "video_platform"
    display_name = "Public video platform"

    def __init__(self, settings: AppSettings):
        self.settings = settings
        self.file_manager = FileManager(settings)

    @property
    def capability(self) -> ProviderCapability:
        return ProviderCapability(
            name=self.name,
            display_name=self.display_name,
            source_types=[
                "YouTube video",
                "X/Twitter clip",
                "Facebook video or reel",
                "Instagram reel or clip",
                "Vimeo video",
                "TikTok video",
                "Other yt-dlp-supported public video page",
            ],
            supports_metadata=True,
            supports_progress=True,
            supported_formats=["mp4", "webm", "mov"],
            supported_qualities=["best", "high", "medium", "low"],
            limitations=[
                "Only public media that yt-dlp can access without credentials is supported.",
                "No cookies, DRM bypass, private content, login-gated media, "
                "or anti-bot circumvention.",
            ],
        )

    def can_handle(self, url: str) -> bool:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        return parsed.scheme in {"http", "https"} and (
            self._is_known_platform_host(host) or self._yt_dlp_extractor_for_url(url) is not None
        )

    def _is_known_platform_host(self, host: str) -> bool:
        return host in KNOWN_PLATFORM_HOSTS or any(
            host.endswith(suffix) for suffix in KNOWN_PLATFORM_SUFFIXES
        )

    async def validate(self, url: str) -> ValidationResult:
        if not self.can_handle(url):
            return ValidationResult(
                ok=False,
                provider=self.name,
                message="Unsupported video source.",
                error=StructuredError(
                    code="unsupported_source",
                    message="This source is not supported by the video provider.",
                ),
            )

        return ValidationResult(
            ok=True,
            provider=self.name,
            source_type="video",
            message=(
                f"{self._platform_name(url)} URL is supported when the media is public, "
                "accessible without login, and permitted."
            ),
            supported_formats=["mp4", "webm", "mov"],
            supported_qualities=["best", "high", "medium", "low"],
        )

    def _platform_name(self, url: str) -> str:
        host = urlparse(url).netloc.lower()
        if host == "youtu.be" or host.endswith("youtube.com"):
            return "YouTube"
        if host == "x.com" or host.endswith(".x.com"):
            return "X"
        if host == "twitter.com" or host.endswith(".twitter.com"):
            return "Twitter"
        if host == "fb.watch" or host == "facebook.com" or host.endswith(".facebook.com"):
            return "Facebook"
        if host == "instagram.com" or host.endswith(".instagram.com"):
            return "Instagram"
        if host == "vimeo.com" or host.endswith(".vimeo.com"):
            return "Vimeo"
        if host == "tiktok.com" or host.endswith(".tiktok.com"):
            return "TikTok"
        return "Public video page"

    @staticmethod
    @lru_cache(maxsize=2048)
    def _yt_dlp_extractor_for_url(url: str) -> str | None:
        try:
            from yt_dlp.extractor import gen_extractor_classes
        except Exception:  # pragma: no cover - defensive dependency guard
            return None

        for extractor in gen_extractor_classes():
            extractor_name = extractor.__name__
            if extractor_name in IGNORED_YT_DLP_EXTRACTORS:
                continue
            try:
                if extractor.suitable(url):
                    return extractor_name
            except Exception:
                continue
        return None

    async def get_metadata(self, url: str) -> MediaMetadata:
        return await asyncio.to_thread(self._get_metadata_sync, url)

    async def download(
        self, job: DownloadJob, progress_callback: ProgressCallback
    ) -> DownloadResult:
        return await asyncio.to_thread(self._download_sync, job, progress_callback)

    def _ydl_options(
        self,
        job: DownloadJob | None = None,
        output_template: str | None = None,
    ):
        quality = (job.options.quality if job else None) or self.settings.default_quality
        selected_format = self.settings.default_video_format
        if job and job.options.format and job.options.format in VIDEO_FORMATS:
            selected_format = job.options.format

        options = {
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "noplaylist": False,
            "ignoreerrors": False,
            "format": self._format_selector(quality, selected_format),
            "merge_output_format": selected_format,
            "restrictfilenames": False,
            "cookiefile": None,
            "retries": 3,
            "fragment_retries": 3,
        }
        if output_template is not None:
            options["outtmpl"] = output_template
        return options

    def _format_selector(self, quality: str, selected_format: str) -> str:
        height = self._quality_height(quality)
        if height is not None:
            return self._height_format_selector(height, selected_format)
        if selected_format in QUICKTIME_FORMATS:
            return QUICKTIME_QUALITY_FORMATS.get(quality, QUICKTIME_QUALITY_FORMATS["best"])
        return QUALITY_FORMATS.get(quality, QUALITY_FORMATS["best"])

    def _quality_height(self, quality: str) -> int | None:
        match = re.fullmatch(r"(\d{3,4})p", quality.lower())
        if match is None:
            return None
        return int(match.group(1))

    def _height_format_selector(self, height: int, selected_format: str) -> str:
        if selected_format in QUICKTIME_FORMATS:
            return (
                f"bestvideo[ext=mp4][vcodec^=avc1][height<={height}]+"
                "bestaudio[ext=m4a][acodec^=mp4a]/"
                f"best[ext=mp4][vcodec^=avc1][acodec^=mp4a][height<={height}]/"
                f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/best"
            )
        return f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/best"

    def _get_metadata_sync(self, url: str) -> MediaMetadata:
        try:
            from yt_dlp import YoutubeDL

            with YoutubeDL(self._ydl_options()) as ydl:
                info = ydl.extract_info(self._yt_dlp_url(url), download=False)

            if info is None:
                raise ProviderError(
                    "metadata_unavailable",
                    "yt-dlp could not read metadata for this URL.",
                )

            entries = info.get("entries") or []
            first_entry = next((entry for entry in entries if entry), None)
            source = first_entry or info
            available_qualities = self._available_video_qualities(source)
            return MediaMetadata(
                source_url=url,
                title=source.get("title") or info.get("title") or "Platform video",
                artist=source.get("uploader") or source.get("channel"),
                duration_seconds=self._duration_seconds(source.get("duration")),
                media_type="playlist" if entries else "video",
                thumbnail_url=source.get("thumbnail"),
                provider=self.name,
                raw={
                    "extractor": source.get("extractor_key") or info.get("extractor_key"),
                    "webpage_url": source.get("webpage_url") or info.get("webpage_url"),
                    "entry_count": len(entries),
                    "available_qualities": available_qualities,
                },
            )
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(
                "platform_metadata_failed",
                self._metadata_error_message(exc),
            ) from exc

    def _metadata_error_message(self, exc: Exception) -> str:
        message = str(exc)
        if "Unable to extract title" in message:
            return (
                "Could not read a downloadable video from this page. The site may "
                "have returned a homepage or blocked page, require browser session "
                "cookies, be geoblocked, be removed, or have changed its page format."
            )
        return f"Could not inspect this public video URL: {message}"

    def _duration_seconds(self, duration: object) -> int | None:
        if duration in (None, ""):
            return None
        try:
            return round(float(duration))
        except (TypeError, ValueError):
            return None

    def _yt_dlp_url(self, url: str) -> str:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        normalized_host = {
            "x.com": "twitter.com",
            "www.x.com": "twitter.com",
            "m.x.com": "twitter.com",
            "mobile.x.com": "twitter.com",
            "twitter.com": "twitter.com",
            "www.twitter.com": "twitter.com",
            "m.twitter.com": "twitter.com",
            "mobile.twitter.com": "twitter.com",
            "m.facebook.com": "www.facebook.com",
            "mobile.facebook.com": "www.facebook.com",
            "web.facebook.com": "www.facebook.com",
            "m.instagram.com": "www.instagram.com",
        }.get(host)
        if normalized_host is None:
            return url
        return urlunparse(parsed._replace(netloc=normalized_host))

    def _available_video_qualities(self, info: dict) -> list[dict[str, object]]:
        formats = info.get("formats") or []
        by_height: dict[int, dict[str, object]] = {}
        audio_size = self._best_audio_size(formats)

        for media_format in formats:
            if media_format.get("vcodec") in {None, "none"}:
                continue
            height = media_format.get("height")
            if not isinstance(height, int) or height <= 0:
                continue
            size = self._format_size(media_format)
            current = by_height.get(height)
            current_size = current.get("estimated_bytes", 0) if current else 0
            if current is None or size > int(current_size or 0):
                by_height[height] = {
                    "id": f"{height}p",
                    "label": VIDEO_QUALITY_LABELS.get(height, f"{height}p"),
                    "height": height,
                    "fps": media_format.get("fps"),
                    "extension": media_format.get("ext"),
                    "video_codec": media_format.get("vcodec"),
                    "estimated_bytes": size + audio_size if size else None,
                }

        qualities: list[dict[str, object]] = [
            {
                "id": "best",
                "label": "Best available",
                "detail": "Let yt-dlp pick the highest available compatible stream.",
            }
        ]
        for height in sorted(by_height, reverse=True):
            quality = by_height[height]
            detail_parts = []
            if quality.get("video_codec"):
                detail_parts.append(str(quality["video_codec"]).split(".")[0])
            if quality.get("fps"):
                detail_parts.append(f"{quality['fps']} fps")
            if quality.get("estimated_bytes"):
                detail_parts.append(f"~{self._format_bytes(int(quality['estimated_bytes']))}")
            if detail_parts:
                quality["detail"] = " | ".join(detail_parts)
            qualities.append(quality)
        return qualities

    def _best_audio_size(self, formats: list[dict]) -> int:
        return max(
            (
                self._format_size(media_format)
                for media_format in formats
                if media_format.get("acodec") not in {None, "none"}
                and media_format.get("vcodec") in {None, "none"}
            ),
            default=0,
        )

    def _format_size(self, media_format: dict) -> int:
        size = media_format.get("filesize") or media_format.get("filesize_approx") or 0
        return int(size) if isinstance(size, (int, float)) else 0

    def _format_bytes(self, size: int) -> str:
        if size >= 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024 * 1024):.1f} GB"
        if size >= 1024 * 1024:
            return f"{size / (1024 * 1024):.0f} MB"
        if size >= 1024:
            return f"{size / 1024:.0f} KB"
        return f"{size} B"

    def _download_sync(
        self, job: DownloadJob, progress_callback: ProgressCallback
    ) -> DownloadResult:
        try:
            from yt_dlp import YoutubeDL

            output_dir = self.file_manager.output_directory(
                job.options.output_directory,
                job.options.output_subfolder,
            )
            output_template = str(output_dir / "%(title).180B [%(id)s].%(ext)s")

            def hook(status):
                if status.get("status") == "downloading":
                    total = status.get("total_bytes") or status.get("total_bytes_estimate")
                    downloaded = status.get("downloaded_bytes") or 0
                    if total:
                        progress_callback(
                            int(downloaded / total * 95),
                            "Downloading platform video",
                        )
                    else:
                        progress_callback(max(job.progress, 5), "Downloading platform video")
                elif status.get("status") == "finished":
                    progress_callback(96, "Merging and post-processing")

            options = self._ydl_options(job, output_template)
            options["progress_hooks"] = [hook]

            with YoutubeDL(options) as ydl:
                info = ydl.extract_info(self._yt_dlp_url(job.url), download=True)

            entries = info.get("entries") if info else None
            downloaded_files = []
            if entries:
                for entry in entries:
                    if not entry:
                        continue
                    path = entry.get("requested_downloads", [{}])[0].get("filepath")
                    if path:
                        downloaded_files.append(Path(path))
            else:
                for download in (info or {}).get("requested_downloads", []):
                    path = download.get("filepath")
                    if path:
                        downloaded_files.append(Path(path))

            final_files = []
            for downloaded_file in downloaded_files:
                final_files.append(
                    self._ensure_quicktime_compatible(downloaded_file, progress_callback)
                )

            progress_callback(100, "Platform video download complete")
            return DownloadResult(
                job_id=job.id,
                success=True,
                file_path=final_files[0] if final_files else None,
                metadata=job.metadata,
            )
        except ProviderError as exc:
            return DownloadResult(
                job_id=job.id,
                success=False,
                metadata=job.metadata,
                error=exc.to_structured_error(),
            )
        except Exception as exc:
            return DownloadResult(
                job_id=job.id,
                success=False,
                metadata=job.metadata,
                error=StructuredError(
                    code="platform_download_failed",
                    message=f"Public video download failed: {exc}",
                ),
            )

    def _ensure_quicktime_compatible(
        self,
        path: Path,
        progress_callback: ProgressCallback,
    ) -> Path:
        if path.suffix.lower().lstrip(".") not in QUICKTIME_FORMATS:
            return path

        codecs = self._probe_codecs(path)
        if codecs["video"] is None:
            raise ProviderError(
                "video_stream_missing",
                "The downloaded file does not contain a video stream.",
            )

        if self._is_quicktime_compatible(codecs):
            return path

        progress_callback(98, "Optimizing video for QuickTime")
        return self._transcode_for_quicktime(
            path,
            progress_callback,
            codecs.get("duration"),
        )

    def _probe_codecs(self, path: Path) -> dict[str, str | None]:
        ffprobe = shutil.which("ffprobe")
        if ffprobe is None:
            raise ProviderError(
                "ffprobe_missing",
                "ffprobe is required to verify MP4/MOV compatibility.",
            )

        result = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-print_format",
                "json",
                "-show_streams",
                "-show_format",
                str(path),
            ],
            capture_output=True,
            check=True,
            text=True,
            timeout=30,
        )
        streams = json.loads(result.stdout).get("streams", [])
        video_stream = next(
            (stream for stream in streams if stream.get("codec_type") == "video"),
            {},
        )
        audio_stream = next(
            (stream for stream in streams if stream.get("codec_type") == "audio"),
            {},
        )
        duration = video_stream.get("duration") or json.loads(result.stdout).get("format", {}).get(
            "duration"
        )
        return {
            "video": video_stream.get("codec_name"),
            "audio": audio_stream.get("codec_name"),
            "pixel_format": video_stream.get("pix_fmt"),
            "duration": duration,
        }

    def _is_quicktime_compatible(self, codecs: dict[str, str | None]) -> bool:
        video_codec = codecs.get("video")
        audio_codec = codecs.get("audio")
        pixel_format = codecs.get("pixel_format")
        return (
            video_codec == "h264"
            and (audio_codec is None or audio_codec in QUICKTIME_AUDIO_CODECS)
            and (pixel_format is None or pixel_format in QUICKTIME_PIXEL_FORMATS)
        )

    def _transcode_for_quicktime(
        self,
        path: Path,
        progress_callback: ProgressCallback,
        duration: str | None,
    ) -> Path:
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg is None:
            raise ProviderError(
                "ffmpeg_missing",
                "ffmpeg is required to make this video QuickTime-compatible.",
            )

        temp_path = path.with_name(f"{path.stem}.quicktime-{uuid4().hex}{path.suffix}")
        try:
            command = [
                ffmpeg,
                "-y",
                "-v",
                "error",
                "-i",
                str(path),
                "-map",
                "0:v:0",
                "-map",
                "0:a:0?",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "22",
                "-pix_fmt",
                "yuv420p",
                "-tag:v",
                "avc1",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-movflags",
                "+faststart",
                "-progress",
                "pipe:1",
                "-nostats",
                str(temp_path),
            ]
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self._stream_ffmpeg_progress(process, progress_callback, duration)
            stderr = process.stderr.read() if process.stderr else ""
            return_code = process.wait()
            if return_code != 0:
                raise subprocess.CalledProcessError(
                    return_code,
                    command,
                    stderr=stderr,
                )
            path.unlink()
            temp_path.replace(path)
            return path
        except subprocess.CalledProcessError as exc:
            if temp_path.exists():
                temp_path.unlink()
            details = exc.stderr.strip() or str(exc)
            raise ProviderError(
                "quicktime_transcode_failed",
                f"Could not make the video QuickTime-compatible: {details}",
            ) from exc

    def _stream_ffmpeg_progress(
        self,
        process: subprocess.Popen[str],
        progress_callback: ProgressCallback,
        duration: str | None,
    ) -> None:
        try:
            total_seconds = float(duration or 0)
        except ValueError:
            total_seconds = 0

        if process.stdout is None:
            progress_callback(98, "Optimizing video for QuickTime")
            return

        for line in process.stdout:
            key, _, value = line.strip().partition("=")
            if key not in {"out_time_ms", "out_time_us"} or total_seconds <= 0:
                continue
            try:
                current_seconds = int(value) / 1_000_000
            except ValueError:
                continue
            percent = max(0, min(99, int(current_seconds / total_seconds * 100)))
            progress_callback(
                min(99, 96 + int(percent * 3 / 100)),
                f"Optimizing video for QuickTime ({percent}%)",
            )

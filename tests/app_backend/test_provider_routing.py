import pytest

from app.backend.models.settings import AppSettings
from app.backend.providers.direct_media_provider import DirectMediaProvider
from app.backend.providers.video_provider import VideoProvider
from app.backend.services.download_manager import DownloadManager


@pytest.mark.asyncio
async def test_direct_media_provider_validates_direct_audio_url():
    provider = DirectMediaProvider(AppSettings())
    result = await provider.validate("https://example.com/audio.mp3")
    assert result.ok is True
    assert result.provider == "direct_media"
    assert result.source_type == "audio"


@pytest.mark.asyncio
async def test_video_provider_accepts_public_platform_urls():
    provider = VideoProvider(AppSettings())
    result = await provider.validate("https://x.com/example/status/123")
    assert result.ok is True
    assert result.provider == "video_platform"
    assert result.source_type == "video"


@pytest.mark.asyncio
async def test_download_manager_routes_to_direct_provider():
    manager = DownloadManager(settings=AppSettings())
    result = await manager.validate_url("https://example.com/video.mp4")
    assert result.ok is True
    assert result.provider == "direct_media"


@pytest.mark.asyncio
async def test_download_manager_routes_to_platform_video_provider():
    manager = DownloadManager(settings=AppSettings())
    result = await manager.validate_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert result.ok is True
    assert result.provider == "video_platform"


@pytest.mark.asyncio
async def test_download_manager_returns_unsupported_for_unknown_url():
    manager = DownloadManager(settings=AppSettings())
    result = await manager.validate_url("notaurl")
    assert result.ok is False
    assert result.error is not None
    assert result.error.code == "unsupported_source"

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


@pytest.mark.parametrize(
    ("url", "platform"),
    [
        ("https://x.com/example/status/123", "X"),
        ("https://mobile.twitter.com/example/status/123", "Twitter"),
        ("https://www.facebook.com/watch/?v=123", "Facebook"),
        ("https://m.facebook.com/reel/123", "Facebook"),
        ("https://fb.watch/abc123", "Facebook"),
        ("https://www.instagram.com/reel/ABC123/", "Instagram"),
        ("https://m.instagram.com/p/ABC123/", "Instagram"),
    ],
)
@pytest.mark.asyncio
async def test_video_provider_accepts_social_clip_urls(url, platform):
    provider = VideoProvider(AppSettings())

    result = await provider.validate(url)

    assert result.ok is True
    assert result.provider == "video_platform"
    assert platform in result.message


@pytest.mark.parametrize(
    "url",
    [
        "https://www.xnxx.com/video-eckm91/your_mum_is_a_slut",
        "https://www.xvideos.com/video123456/example",
        "https://xvideos2.com/video123456/example",
        "https://www.xvideos.es/video123456/example",
        "https://www.pornhub.com/view_video.php?viewkey=abc123",
        "https://pornhub.net/view_video.php?viewkey=abc123",
        "https://www.thumbzilla.com/video/abc123",
        "https://beeg.com/123456",
        "https://www.beeg.com/video/123456",
    ],
)
@pytest.mark.asyncio
async def test_video_provider_accepts_other_ytdlp_supported_public_video_pages(url):
    provider = VideoProvider(AppSettings())

    result = await provider.validate(url)

    assert result.ok is True
    assert result.provider == "video_platform"
    assert "Public video page" in result.message


@pytest.mark.parametrize(
    "url",
    [
        "https://notfacebook.com/reel/123",
        "https://instagram.example.com/reel/123",
        "https://twitter.example.com/status/123",
        "https://notxvideos.com/video123",
        "https://xvideos.example.com/video123",
        "https://cineby.example/watch/123",
        "https://notpornhub.com/view_video.php?viewkey=abc123",
        "https://pornhub.example.com/view_video.php?viewkey=abc123",
        "https://sex.com/video/123",
    ],
)
def test_video_provider_rejects_lookalike_social_hosts(url):
    provider = VideoProvider(AppSettings())

    assert provider.can_handle(url) is False


@pytest.mark.parametrize(
    "url",
    [
        "https://sex.com/video/123",
        "https://www.cineby.sc/movie/1318447",
        "https://example.com/page",
    ],
)
def test_video_provider_rejects_urls_without_specific_ytdlp_extractors(url):
    provider = VideoProvider(AppSettings())

    assert provider.can_handle(url) is False


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


def test_video_provider_prefers_quicktime_codecs_for_mp4():
    provider = VideoProvider(AppSettings(default_video_format="mp4"))

    options = provider._ydl_options()

    assert "vcodec^=avc1" in options["format"]
    assert "acodec^=mp4a" in options["format"]
    assert options["merge_output_format"] == "mp4"


def test_video_provider_uses_exact_height_selector_for_video_quality():
    provider = VideoProvider(AppSettings(default_video_format="mp4"))
    job_options = {"quality": "1080p", "format": "mp4"}

    selector = provider._format_selector(job_options["quality"], job_options["format"])

    assert "height<=1080" in selector
    assert "vcodec^=avc1" in selector


def test_video_provider_keeps_generic_selector_for_webm():
    provider = VideoProvider(AppSettings(default_video_format="webm"))

    options = provider._ydl_options()

    assert "vcodec^=avc1" not in options["format"]
    assert options["merge_output_format"] == "webm"


def test_quicktime_codec_check_accepts_h264_aac_yuv420p():
    provider = VideoProvider(AppSettings())

    assert provider._is_quicktime_compatible(
        {"video": "h264", "audio": "aac", "pixel_format": "yuv420p"}
    )


def test_quicktime_codec_check_rejects_vp9_mp4():
    provider = VideoProvider(AppSettings())

    assert not provider._is_quicktime_compatible(
        {"video": "vp9", "audio": "aac", "pixel_format": "yuv420p"}
    )


def test_video_provider_builds_available_quality_options():
    provider = VideoProvider(AppSettings())

    qualities = provider._available_video_qualities(
        {
            "formats": [
                {"vcodec": "none", "acodec": "mp4a.40.2", "filesize": 1_000_000},
                {
                    "height": 720,
                    "fps": 30,
                    "ext": "mp4",
                    "vcodec": "avc1.64001F",
                    "filesize": 20_000_000,
                },
                {
                    "height": 1080,
                    "fps": 30,
                    "ext": "webm",
                    "vcodec": "vp9",
                    "filesize": 40_000_000,
                },
            ]
        }
    )

    assert [quality["id"] for quality in qualities] == ["best", "1080p", "720p"]
    assert qualities[1]["label"] == "1080p FHD"
    assert qualities[1]["estimated_bytes"] == 41_000_000


def test_video_provider_rounds_fractional_social_video_duration():
    provider = VideoProvider(AppSettings())

    assert provider._duration_seconds(174.962) == 175


def test_video_provider_explains_extractor_page_failures():
    provider = VideoProvider(AppSettings())

    message = provider._metadata_error_message(Exception("Unable to extract title"))

    assert "Could not read a downloadable video" in message
    assert "browser session cookies" in message


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (
            "https://x.com/i/status/2048172881947849084",
            "https://twitter.com/i/status/2048172881947849084",
        ),
        (
            "https://mobile.twitter.com/example/status/123",
            "https://twitter.com/example/status/123",
        ),
        (
            "https://m.facebook.com/reel/123",
            "https://www.facebook.com/reel/123",
        ),
        (
            "https://m.instagram.com/reel/ABC123/",
            "https://www.instagram.com/reel/ABC123/",
        ),
    ],
)
def test_video_provider_normalizes_social_urls_for_ytdlp(url, expected):
    provider = VideoProvider(AppSettings())

    assert provider._yt_dlp_url(url) == expected

import time

from app.backend.models.download_job import DownloadJob, DownloadOptions
from app.backend.models.download_result import MediaMetadata
from app.backend.models.settings import AppSettings
from app.backend.providers import spotdl_provider
from app.backend.providers.base import ProviderError
from app.backend.providers.spotdl_provider import SpotDLProvider
from spotdl.utils import metadata as metadata_utils


def test_spotdl_provider_translates_best_quality_to_auto_bitrate(tmp_path):
    provider = SpotDLProvider(AppSettings(output_directory=tmp_path))
    job = DownloadJob(
        url="https://open.spotify.com/track/2tUBqZG2AbRi7Q0BIrVrEj?si=23346445333d4bc0",
        options=DownloadOptions(format="mp3", quality="best"),
    )

    _, downloader_settings = provider._spotdl_settings(job)

    assert downloader_settings["bitrate"] == "auto"


def test_spotdl_provider_keeps_explicit_bitrate(tmp_path):
    provider = SpotDLProvider(AppSettings(output_directory=tmp_path))
    job = DownloadJob(
        url="https://open.spotify.com/track/2tUBqZG2AbRi7Q0BIrVrEj",
        options=DownloadOptions(format="mp3", quality="128k"),
    )

    _, downloader_settings = provider._spotdl_settings(job)

    assert downloader_settings["bitrate"] == "128k"


def test_spotdl_relative_output_folder_is_subfolder_of_library(tmp_path):
    provider = SpotDLProvider(AppSettings(output_directory=tmp_path / "library"))
    job = DownloadJob(
        url="https://open.spotify.com/playlist/37i9dQZF1E35jo0CrB6zS5",
        options=DownloadOptions(output_subfolder="Playlists/Daily Mix 2"),
    )

    _, downloader_settings = provider._spotdl_settings(job)

    assert downloader_settings["output"].startswith(
        str(tmp_path / "library" / "Playlists" / "Daily Mix 2")
    )


def test_spotdl_relative_output_override_stays_under_library(tmp_path):
    provider = SpotDLProvider(AppSettings(output_directory=tmp_path / "library"))
    job = DownloadJob(
        url="https://open.spotify.com/playlist/37i9dQZF1E35jo0CrB6zS5",
        options=DownloadOptions(output_directory="Daily Mix 2"),
    )

    _, downloader_settings = provider._spotdl_settings(job)

    assert downloader_settings["output"].startswith(
        str(tmp_path / "library" / "Daily Mix 2")
    )


def test_spotdl_provider_maps_spotify_rate_limit(tmp_path):
    provider = SpotDLProvider(AppSettings(output_directory=tmp_path))

    error = provider._rate_limit_error(Exception("HTTP status 429, retry-after: 86400"))

    assert error is not None
    assert error.code == "spotify_rate_limited"
    assert error.details["retry_after_seconds"] == 86400
    assert "client ID" not in error.message


def test_spotdl_playlist_uses_embed_before_spotdl_resolver(monkeypatch, tmp_path):
    provider = SpotDLProvider(AppSettings(output_directory=tmp_path))
    job = DownloadJob(
        url="https://open.spotify.com/playlist/37i9dQZF1E35jo0CrB6zS5",
        options=DownloadOptions(),
    )
    embed_song = provider._song_from_basic_metadata(
        url="https://open.spotify.com/track/1",
        title="Embed song",
        artist="Embed artist",
        list_name="Embed playlist",
        list_url=job.url,
        list_position=1,
        list_length=1,
    )
    messages = []

    monkeypatch.setattr(
        provider,
        "_songs_from_spotify_embed_collection",
        lambda *args, **kwargs: [embed_song],
    )
    monkeypatch.setattr(
        provider,
        "_try_spotdl_playlist_resolution",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("spotDL resolver should not be used after embed resolution")
        ),
    )
    monkeypatch.setattr(
        provider,
        "_download_songs_concurrently",
        lambda songs, settings, callback: ([tmp_path / "Embed song.mp3"], ""),
    )
    (tmp_path / "Embed song.mp3").write_bytes(b"ok")

    result = provider._download_sync(job, lambda progress, message: messages.append(message))

    assert result.success is True
    assert job.metadata is not None
    assert job.metadata.raw["track_count"] == 1
    assert "Read 1 tracks from Spotify's public playlist data" in messages


def test_spotdl_embed_playlist_page_builds_all_songs(monkeypatch, tmp_path):
    provider = SpotDLProvider(AppSettings(output_directory=tmp_path))

    class Response:
        status_code = 200
        text = """
        <html><body>
          <script id="__NEXT_DATA__" type="application/json">
            {
              "props": {
                "pageProps": {
                  "state": {
                    "data": {
                      "entity": {
                        "title": "Daily Mix 2",
                        "coverArt": {
                          "sources": [{"url": "https://example.com/cover.jpg"}]
                        },
                        "trackList": [
                          {
                            "uri": "spotify:track:4537oC0JfzmGXi3r3TyCCK",
                            "title": "Madad Rangi",
                            "subtitle": "Ebi",
                            "duration": 306333,
                            "entityType": "track"
                          },
                          {
                            "uri": "spotify:track:7dXQJlsVwPfBVHylTrMgIw",
                            "title": "Ey Yare Man",
                            "subtitle": "Anoushirvan Rohani,\\u00a0Molavi",
                            "duration": 228414,
                            "entityType": "track"
                          }
                        ]
                      }
                    }
                  }
                }
              }
            }
          </script>
        </body></html>
        """

    monkeypatch.setattr(spotdl_provider.requests, "get", lambda *args, **kwargs: Response())

    songs = provider._songs_from_spotify_embed_collection(
        "https://open.spotify.com/playlist/37i9dQZF1E35jo0CrB6zS5",
        None,
    )

    assert len(songs) == 2
    assert songs[0].name == "Madad Rangi"
    assert songs[0].artist == "Ebi"
    assert songs[0].list_length == 2
    assert songs[1].artists == ["Anoushirvan Rohani", "Molavi"]


def test_spotdl_embed_album_page_builds_all_songs(monkeypatch, tmp_path):
    provider = SpotDLProvider(AppSettings(output_directory=tmp_path))

    class Response:
        status_code = 200
        text = """
        <html><body>
          <script id="__NEXT_DATA__" type="application/json">
            {
              "props": {
                "pageProps": {
                  "state": {
                    "data": {
                      "entity": {
                        "type": "album",
                        "title": "Whitney",
                        "subtitle": "Whitney Houston",
                        "trackList": [
                          {
                            "uri": "spotify:track:2tUBqZG2AbRi7Q0BIrVrEj",
                            "title": "I Wanna Dance with Somebody (Who Loves Me)",
                            "subtitle": "Whitney Houston",
                            "duration": 292875,
                            "entityType": "track"
                          }
                        ]
                      }
                    }
                  }
                }
              }
            }
          </script>
        </body></html>
        """

    monkeypatch.setattr(spotdl_provider.requests, "get", lambda *args, **kwargs: Response())

    songs = provider._songs_from_spotify_embed_collection(
        "https://open.spotify.com/album/5Vdzprr5cOqXQo44eHeV7t",
        None,
    )

    assert len(songs) == 1
    assert songs[0].name == "I Wanna Dance with Somebody (Who Loves Me)"
    assert songs[0].album_name == "Whitney"
    assert songs[0].album_artist == "Whitney Houston"
    assert songs[0].album_type == "album"

    metadata = provider._metadata_from_songs(
        "https://open.spotify.com/album/5Vdzprr5cOqXQo44eHeV7t",
        songs,
    )

    assert metadata.media_type == "album"
    assert metadata.title == "Whitney"


def test_spotdl_playlist_does_not_download_partial_public_page(monkeypatch, tmp_path):
    provider = SpotDLProvider(AppSettings(output_directory=tmp_path))
    job = DownloadJob(
        url="https://open.spotify.com/playlist/37i9dQZF1E35jo0CrB6zS5",
        options=DownloadOptions(),
    )
    public_song = provider._song_from_basic_metadata(
        url="https://open.spotify.com/track/1",
        title="Public song",
        artist="Public artist",
        list_name="Partial playlist",
        list_url=job.url,
        list_position=1,
        list_length=2,
    )

    monkeypatch.setattr(
        provider,
        "_songs_from_spotify_embed_collection",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        provider,
        "_try_spotdl_playlist_resolution",
        lambda *args, **kwargs: ([], "rate limited"),
    )
    monkeypatch.setattr(
        provider,
        "_songs_from_public_playlist_page",
        lambda *args, **kwargs: [public_song],
    )
    monkeypatch.setattr(
        provider,
        "_download_songs_concurrently",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("partial playlist should not be downloaded")
        ),
    )

    try:
        provider._download_sync(job, lambda *_args: None)
    except ProviderError as exc:
        assert exc.code == "spotify_playlist_incomplete"
        assert "only 1 of 2" in exc.message
    else:
        raise AssertionError("Expected incomplete playlist failure")


def test_spotdl_metadata_preview_does_not_resolve_tracks(monkeypatch, tmp_path):
    provider = SpotDLProvider(AppSettings(output_directory=tmp_path))

    def fail_if_called(_job):
        raise AssertionError("spotDL search should happen during download, not metadata preview")

    class Response:
        status_code = 200

        def json(self):
            return {
                "title": "Preview title",
                "author_name": "Preview artist",
                "thumbnail_url": "https://example.com/cover.jpg",
                "provider_name": "Spotify",
                "type": "rich",
            }

    monkeypatch.setattr(provider, "_create_spotdl_client", fail_if_called)
    monkeypatch.setattr(spotdl_provider.requests, "get", lambda *args, **kwargs: Response())

    metadata = provider._get_oembed_metadata(
        "https://open.spotify.com/track/2tUBqZG2AbRi7Q0BIrVrEj"
    )

    assert metadata.title == "Preview title"
    assert metadata.artist == "Preview artist"
    assert metadata.thumbnail_url == "https://example.com/cover.jpg"


def test_spotdl_preview_reads_artist_from_public_page(monkeypatch, tmp_path):
    provider = SpotDLProvider(AppSettings(output_directory=tmp_path))

    class OembedResponse:
        status_code = 200

        def json(self):
            return {
                "title": "Hasrat",
                "thumbnail_url": "https://example.com/cover.jpg",
                "provider_name": "Spotify",
                "type": "rich",
            }

    class PageResponse:
        status_code = 200
        text = (
            '<meta property="og:title" content="Hasrat">'
            '<meta property="og:description" '
            'content="Mohammad Esfahani, Foad Hejazi · Hasrat · Song · 2002">'
            "<title>Hasrat - song and lyrics by Mohammad Esfahani, Foad Hejazi | Spotify</title>"
        )

    def fake_get(url, *args, **kwargs):
        if "oembed" in url:
            return OembedResponse()
        return PageResponse()

    monkeypatch.setattr(spotdl_provider.requests, "get", fake_get)

    metadata = provider._get_oembed_metadata(
        "https://open.spotify.com/track/4bLW9HioJ4Kc4JzgGbnzD7"
    )

    assert metadata.title == "Hasrat"
    assert metadata.artist == "Mohammad Esfahani, Foad Hejazi"


def test_spotdl_public_playlist_page_builds_downloadable_songs(monkeypatch, tmp_path):
    provider = SpotDLProvider(AppSettings(output_directory=tmp_path))

    class PageResponse:
        status_code = 200
        text = """
        <html>
          <head>
            <meta property="og:title" content="Daily Mix 2">
            <meta property="og:description" content="Playlist · Spotify · 50 items">
          </head>
          <body>
            <div data-testid="track-row" aria-label="Tansife Morghe Sahar">
              <img src="https://example.com/cover-1.jpg">
              <a href="/track/1MSRQklZLFqMghL2aZzH0M">Tansife Morghe Sahar</a>
              <a href="/artist/artist-1">Homayoun Shajarian</a>
            </div>
            <div data-testid="track-row" aria-label="Scent Of Hair">
              <img src="https://example.com/cover-2.jpg">
              <a href="/track/6i9hnmsEKDHJuFab5tzaIS">Scent Of Hair</a>
              <a href="/artist/artist-2">Alireza Ghorbani</a>
              <a href="/artist/artist-3">Hesam Naseri</a>
            </div>
          </body>
        </html>
        """

    monkeypatch.setattr(spotdl_provider.requests, "get", lambda *args, **kwargs: PageResponse())

    songs = provider._songs_from_public_playlist_page(
        "https://open.spotify.com/playlist/37i9dQZF1E35jo0CrB6zS5",
        MediaMetadata(
            source_url="https://open.spotify.com/playlist/37i9dQZF1E35jo0CrB6zS5",
            title="Fallback title",
            media_type="playlist",
        ),
    )

    assert len(songs) == 2
    assert songs[0].name == "Tansife Morghe Sahar"
    assert songs[0].artist == "Homayoun Shajarian"
    assert songs[0].list_name == "Daily Mix 2"
    assert songs[0].list_position == 1
    assert songs[0].list_length == 50
    assert songs[1].artists == ["Alireza Ghorbani", "Hesam Naseri"]

    metadata = provider._metadata_from_songs(
        "https://open.spotify.com/playlist/37i9dQZF1E35jo0CrB6zS5",
        songs,
    )

    assert metadata.media_type == "playlist"
    assert metadata.raw["spotify_id"] == "https://open.spotify.com/playlist/37i9dQZF1E35jo0CrB6zS5"
    assert metadata.raw["track_count"] == 2
    assert metadata.raw["list_length"] == 50


def test_spotdl_track_preview_builds_downloadable_song(tmp_path):
    provider = SpotDLProvider(AppSettings(output_directory=tmp_path))

    song = provider._song_from_preview_metadata(
        "https://open.spotify.com/track/4bLW9HioJ4Kc4JzgGbnzD7?si=75783514264144da",
        MediaMetadata(
            source_url="https://open.spotify.com/track/4bLW9HioJ4Kc4JzgGbnzD7",
            title="Preview title",
            artist="Preview artist",
            media_type="audio",
            thumbnail_url="https://example.com/cover.jpg",
        ),
    )

    assert song.name == "Preview title"
    assert song.artist == "Preview artist"
    assert song.artists == ["Preview artist"]
    assert song.song_id == "4bLW9HioJ4Kc4JzgGbnzD7"
    assert song.album_id == ""
    assert song.album_artist == "Preview artist"


def test_spotdl_resolution_timeout_fails_clearly(tmp_path):
    provider = SpotDLProvider(AppSettings(output_directory=tmp_path))

    try:
        provider._run_with_timeout(lambda: time.sleep(0.05), 0, "Timed out")
    except ProviderError as exc:
        assert exc.code == "spotify_resolution_timeout"
        assert exc.message == "Timed out"
    else:
        raise AssertionError("Expected provider timeout")


def test_spotdl_provider_errors_are_exposed(tmp_path):
    provider = SpotDLProvider(AppSettings(output_directory=tmp_path))

    class Downloader:
        errors = ["url - LookupError: No results found"]

    class Client:
        downloader = Downloader()

    assert (
        provider._provider_errors(Client())
        == "spotDL failed: url - LookupError: No results found"
    )


def test_spotdl_missing_reported_file_is_not_success(monkeypatch, tmp_path):
    provider = SpotDLProvider(AppSettings(output_directory=tmp_path))
    song = provider._song_from_preview_metadata(
        "https://open.spotify.com/track/5a2Mb0OPY17zkS8FnciQhg",
        MediaMetadata(
            source_url="https://open.spotify.com/track/5a2Mb0OPY17zkS8FnciQhg",
            title="Finally",
            artist="Swedish House Mafia, Alicia Keys",
            media_type="audio",
        ),
    )
    song.download_url = "https://music.youtube.com/watch?v=test"
    missing_path = tmp_path / "missing.mp3"

    class FakeDownloader:
        errors = []

        def __init__(self, settings):
            self.settings = settings

        def download_song(self, _song):
            return _song, missing_path

    monkeypatch.setattr("spotdl.download.downloader.Downloader", FakeDownloader)

    path, error, skipped = provider._download_single_song(song, {"threads": 4})

    assert path is None
    assert skipped is False
    assert str(missing_path) in error


def test_spotdl_existing_master_library_file_is_skipped(monkeypatch, tmp_path):
    provider = SpotDLProvider(AppSettings(output_directory=tmp_path))
    song = provider._song_from_preview_metadata(
        "https://open.spotify.com/track/5a2Mb0OPY17zkS8FnciQhg",
        MediaMetadata(
            source_url="https://open.spotify.com/track/5a2Mb0OPY17zkS8FnciQhg",
            title="Finally",
            artist="Swedish House Mafia, Alicia Keys",
            media_type="audio",
        ),
    )
    existing_path = tmp_path / "Swedish House Mafia - Finally.mp3"
    existing_path.write_bytes(b"existing")

    class FakeDownloader:
        def __init__(self, settings):
            raise AssertionError("Downloader should not start for a local duplicate")

    monkeypatch.setattr("spotdl.download.downloader.Downloader", FakeDownloader)
    monkeypatch.setattr(
        "spotdl.utils.search.get_song_from_file_metadata",
        lambda _path: None,
    )

    path, error, skipped = provider._download_single_song(
        song,
        {"format": "mp3", "threads": 4},
    )

    assert path == existing_path
    assert error == ""
    assert skipped is True


def test_spotdl_fallback_song_embeds_without_isrc(monkeypatch, tmp_path):
    provider = SpotDLProvider(AppSettings(output_directory=tmp_path))
    song = provider._song_from_preview_metadata(
        "https://open.spotify.com/track/5a2Mb0OPY17zkS8FnciQhg",
        MediaMetadata(
            source_url="https://open.spotify.com/track/5a2Mb0OPY17zkS8FnciQhg",
            title="Finally",
            artist="Swedish House Mafia, Alicia Keys",
            media_type="audio",
        ),
    )
    audio_path = tmp_path / "test.mp3"

    class EasyAudio(dict):
        def save(self, *args, **kwargs):
            return None

    class FullAudio(dict):
        def add(self, frame):
            self[frame.FrameID] = frame

        def save(self, *args, **kwargs):
            return None

    easy_audio = EasyAudio()
    full_audio = FullAudio()

    monkeypatch.setattr(metadata_utils, "File", lambda *args, **kwargs: easy_audio)
    monkeypatch.setattr(metadata_utils, "ID3", lambda *args, **kwargs: full_audio)

    metadata_utils.embed_metadata(audio_path, song, skip_album_art=True)

    assert "isrc" not in easy_audio

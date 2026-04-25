from app.backend.models.download_job import DownloadJob, DownloadOptions
from app.backend.models.settings import AppSettings
from app.backend.providers.spotdl_provider import SpotDLProvider


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


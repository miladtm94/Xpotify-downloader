import pytest
from pydantic import ValidationError

from app.backend.models.settings import AppSettings


def test_settings_normalize_output_directory():
    settings = AppSettings(output_directory="~/Downloads/Xpotify")
    assert str(settings.output_directory).endswith("Downloads/Xpotify")


def test_settings_reject_unsupported_audio_format():
    with pytest.raises(ValidationError):
        AppSettings(default_audio_format="exe")


def test_settings_reject_invalid_concurrency():
    with pytest.raises(ValidationError):
        AppSettings(max_concurrent_downloads=0)


from pathlib import Path

import pytest

from app.backend.utils.filenames import safe_join, sanitize_filename


def test_sanitize_filename_removes_unsafe_characters():
    assert sanitize_filename('bad:name/with*chars?.mp3') == "bad-name-with-chars-.mp3"


def test_sanitize_filename_handles_reserved_names():
    assert sanitize_filename("CON") == "CON-file"


def test_safe_join_blocks_path_traversal(tmp_path: Path):
    with pytest.raises(ValueError):
        safe_join(tmp_path, "../escape.mp3")


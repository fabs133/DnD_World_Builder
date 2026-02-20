import pytest
from pathlib import Path
from core.media_manager import MediaManager


@pytest.fixture
def workspace(tmp_path):
    ws = tmp_path / "test_scenario"
    ws.mkdir()
    return ws


@pytest.fixture
def manager(workspace):
    return MediaManager(workspace)


@pytest.fixture
def sample_image(tmp_path):
    img = tmp_path / "portrait.png"
    img.write_bytes(b"FAKE_PNG_DATA")
    return img


@pytest.fixture
def sample_audio(tmp_path):
    audio = tmp_path / "ambience.mp3"
    audio.write_bytes(b"FAKE_MP3_DATA")
    return audio


def test_import_image_creates_directory(manager, sample_image, workspace):
    result = manager.import_image(sample_image)
    assert result.startswith("media/images/")
    full_path = workspace / result
    assert full_path.exists()
    assert full_path.read_bytes() == b"FAKE_PNG_DATA"


def test_import_audio_creates_directory(manager, sample_audio, workspace):
    result = manager.import_audio(sample_audio)
    assert result.startswith("media/audio/")
    full_path = workspace / result
    assert full_path.exists()
    assert full_path.read_bytes() == b"FAKE_MP3_DATA"


def test_import_same_file_twice_no_duplicate(manager, sample_image, workspace):
    result1 = manager.import_image(sample_image)
    result2 = manager.import_image(sample_image)
    # Same content → same file, no collision suffix
    assert result1 == result2
    images_dir = workspace / "media" / "images"
    assert len(list(images_dir.iterdir())) == 1


def test_import_different_files_same_name(manager, workspace, tmp_path):
    # Create two files with the same name but different content
    dir1 = tmp_path / "dir1"
    dir1.mkdir()
    file1 = dir1 / "portrait.png"
    file1.write_bytes(b"IMAGE_A")

    dir2 = tmp_path / "dir2"
    dir2.mkdir()
    file2 = dir2 / "portrait.png"
    file2.write_bytes(b"IMAGE_B")

    result1 = manager.import_image(file1)
    result2 = manager.import_image(file2)
    # Different content, same name → collision handling
    assert result1 != result2
    images_dir = workspace / "media" / "images"
    assert len(list(images_dir.iterdir())) == 2


def test_resolve_path(manager, workspace):
    resolved = manager.resolve_path("media/images/test.png")
    assert resolved == workspace / "media" / "images" / "test.png"


def test_import_preserves_extension(manager, tmp_path, workspace):
    img = tmp_path / "dragon.jpg"
    img.write_bytes(b"JPG_DATA")
    result = manager.import_image(img)
    assert result.endswith(".jpg")

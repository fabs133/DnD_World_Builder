import json
import zipfile
from pathlib import Path

import pytest

from core.export_manager import ExportManager

@pytest.fixture
def dummy_map(tmp_path):
    def _make(meta=None):
        data = {}
        if meta is not None:
            data["meta"] = meta
        # write out as JSON
        p = tmp_path / "map.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        return p
    return _make

def test_export_creates_export_dir_and_zip(tmp_path, dummy_map):
    export_dir = tmp_path / "my_exports"
    em = ExportManager(export_dir=str(export_dir))
    # export_dir should be created
    assert export_dir.exists() and export_dir.is_dir()

    map_path = dummy_map()
    bundle_path = em.export_bundle(map_path)
    assert bundle_path.exists()
    assert bundle_path.suffix == ".zip"

def test_export_without_profile_or_media(tmp_path, dummy_map):
    em = ExportManager(export_dir=str(tmp_path / "exports"))
    map_path = dummy_map()
    bundle = em.export_bundle(map_path)

    with zipfile.ZipFile(bundle, 'r') as zf:
        names = set(zf.namelist())
        # only map.json + manifest.json
        assert names == {"map.json", "manifest.json"}

        manifest = json.loads(zf.read("manifest.json"))
        # default map_name = stem, author = Unknown
        assert manifest["map_name"] == "map"
        assert manifest["author"] == "Unknown"
        assert manifest["files"] == ["map.json"]

def test_export_with_meta(dummy_map, tmp_path):
    em = ExportManager(export_dir=str(tmp_path / "exports"))
    meta = {"map_name": "Dungeon", "author": "Gandalf"}
    map_path = dummy_map(meta=meta)
    bundle = em.export_bundle(map_path)

    with zipfile.ZipFile(bundle, 'r') as zf:
        manifest = json.loads(zf.read("manifest.json"))
        assert manifest["map_name"] == "Dungeon"
        assert manifest["author"] == "Gandalf"

def test_export_includes_profiles_and_media(tmp_path, dummy_map):
    em = ExportManager(export_dir=str(tmp_path / "exports"))
    map_path = dummy_map()

    # set up profile_dir with a nested file
    profile_dir = tmp_path / "profiles"
    file_a = profile_dir / "foo.json"
    file_a.parent.mkdir(parents=True)
    file_a.write_text("profile-data")

    # set up media_dir with a nested file
    media_dir = tmp_path / "media"
    file_b = media_dir / "images" / "bar.png"
    file_b.parent.mkdir(parents=True)
    file_b.write_bytes(b"\x00\x01\x02")

    bundle = em.export_bundle(map_path, profile_dir=profile_dir, media_dir=media_dir)

    with zipfile.ZipFile(bundle, 'r') as zf:
        names = set(zf.namelist())
        # should include:
        assert "map.json" in names
        assert "profiles/foo.json" in names
        assert "media/images/bar.png" in names
        assert "manifest.json" in names

        manifest = json.loads(zf.read("manifest.json"))
        # profiles/ and media/ markers
        assert "profiles/" in manifest["files"]
        assert "media/" in manifest["files"]

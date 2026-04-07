"""Tests for the asset manager panel."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from PyQt5.QtCore import Qt, QByteArray, QMimeData

from core.media_manager import MediaManager
from ui.panels.asset_manager_panel import AssetManagerPanel, ASSET_MIME_TYPE


@pytest.fixture
def workspace(tmp_path):
    """Create a temp workspace with a media directory."""
    images = tmp_path / "media" / "images"
    audio = tmp_path / "media" / "audio"
    images.mkdir(parents=True)
    audio.mkdir(parents=True)
    return tmp_path


@pytest.fixture
def panel(qtbot, workspace):
    """Create an AssetManagerPanel attached to a workspace."""
    p = AssetManagerPanel()
    qtbot.addWidget(p)
    p.set_workspace(workspace)
    return p


def _create_image(workspace, name="test.png"):
    path = workspace / "media" / "images" / name
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    return path


def _create_audio(workspace, name="test.wav"):
    path = workspace / "media" / "audio" / name
    path.write_bytes(b"RIFF" + b"\x00" * 100)
    return path


class TestAssetManagerPanel:
    def test_panel_creates(self, qtbot):
        p = AssetManagerPanel()
        qtbot.addWidget(p)
        assert p is not None

    def test_set_workspace_scans_media(self, qtbot, workspace):
        _create_image(workspace, "tavern.png")
        _create_audio(workspace, "ambience.wav")

        p = AssetManagerPanel()
        qtbot.addWidget(p)
        p.set_workspace(workspace)

        assert p._list.count() == 2

    def test_search_filters(self, qtbot, workspace):
        _create_image(workspace, "tavern_bg.png")
        _create_image(workspace, "forest_bg.png")

        p = AssetManagerPanel()
        qtbot.addWidget(p)
        p.set_workspace(workspace)

        assert p._list.count() == 2

        p._search.setText("tavern")
        visible = sum(1 for i in range(p._list.count()) if not p._list.item(i).isHidden())
        assert visible == 1

    def test_category_tabs_filter(self, qtbot, workspace):
        _create_image(workspace, "pic.png")
        _create_audio(workspace, "sound.wav")

        p = AssetManagerPanel()
        qtbot.addWidget(p)
        p.set_workspace(workspace)

        # All tab
        p._tabs.setCurrentIndex(p._TAB_ALL)
        visible = sum(1 for i in range(p._list.count()) if not p._list.item(i).isHidden())
        assert visible == 2

        # Images only
        p._tabs.setCurrentIndex(p._TAB_IMAGES)
        visible = sum(1 for i in range(p._list.count()) if not p._list.item(i).isHidden())
        assert visible == 1

        # Audio only
        p._tabs.setCurrentIndex(p._TAB_AUDIO)
        visible = sum(1 for i in range(p._list.count()) if not p._list.item(i).isHidden())
        assert visible == 1

    def test_refresh_rescans(self, panel, workspace):
        assert panel._list.count() == 0

        _create_image(workspace, "new.png")
        panel.refresh()

        assert panel._list.count() == 1

    def test_status_label_updates(self, qtbot, workspace):
        _create_image(workspace, "a.png")
        _create_image(workspace, "b.png")
        _create_audio(workspace, "c.wav")

        p = AssetManagerPanel()
        qtbot.addWidget(p)
        p.set_workspace(workspace)

        assert "3 assets" in p._status.text()
        assert "2 images" in p._status.text()
        assert "1 audio" in p._status.text()

    def test_empty_workspace(self, qtbot, workspace):
        p = AssetManagerPanel()
        qtbot.addWidget(p)
        p.set_workspace(workspace)

        assert p._list.count() == 0

    def test_no_workspace_import_returns_zero(self, qtbot):
        p = AssetManagerPanel()
        qtbot.addWidget(p)
        assert p.import_files() == 0


class TestMediaManagerListing:
    def test_list_images(self, workspace):
        _create_image(workspace, "a.png")
        _create_image(workspace, "b.jpg")
        mm = MediaManager(workspace)
        result = mm.list_images()
        assert len(result) == 2
        assert all("media/images/" in r for r in result)

    def test_list_audio(self, workspace):
        _create_audio(workspace, "a.wav")
        _create_audio(workspace, "b.mp3")
        mm = MediaManager(workspace)
        result = mm.list_audio()
        assert len(result) == 2
        assert all("media/audio/" in r for r in result)

    def test_list_images_empty(self, workspace):
        mm = MediaManager(workspace)
        assert mm.list_images() == []

    def test_list_ignores_unsupported_extensions(self, workspace):
        (workspace / "media" / "images" / "readme.txt").write_text("not an image")
        mm = MediaManager(workspace)
        assert mm.list_images() == []

    def test_list_nonexistent_dir(self, tmp_path):
        mm = MediaManager(tmp_path)
        assert mm.list_images() == []
        assert mm.list_audio() == []

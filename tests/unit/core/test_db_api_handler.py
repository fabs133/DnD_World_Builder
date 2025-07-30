import pytest
import json
import os
from pathlib import Path
from core.db_api_handler import LocalAPIHandler, APIError

@pytest.fixture
def handler():
    base_path = "tests/assets/rulebook_json"
    os.makedirs(base_path, exist_ok=True)
    return LocalAPIHandler(base_path)

def test_get_known_category(monkeypatch):
    def fake_load_file(self, category):
        assert category == "spells"
        return [{"name": "Fireball"}]

    monkeypatch.setattr(LocalAPIHandler, "_load_file", fake_load_file)

    h = LocalAPIHandler()
    data = h.get("spells")
    assert isinstance(data, list)
    assert data[0]["name"] == "Fireball"

def test_get_unknown_key_raises(handler):
    with pytest.raises(APIError):
        handler.get("nonexistent_key")

def test_get_raw_success(monkeypatch):
    sample_data = [{"index": "fireball", "name": "Fireball"}]

    def fake_load_file(self, category):
        assert category == "spells"
        return sample_data

    monkeypatch.setattr(LocalAPIHandler, "_load_file", fake_load_file)
    h = LocalAPIHandler()
    result = h.get_raw("/api/spells/fireball")
    assert result["name"] == "Fireball"

def test_get_raw_invalid_path(handler):
    with pytest.raises(APIError):
        handler.get_raw("/badpath")

def test_get_monster_and_spell(monkeypatch):
    def fake_get_raw(self, endpoint, params=None):
        if "ogre-king" in endpoint:
            return {"name": "Ogre King"}
        elif "magic-missile" in endpoint:
            return {"name": "Magic Missile"}
        return None

    monkeypatch.setattr(LocalAPIHandler, "get_raw", fake_get_raw)
    h = LocalAPIHandler()

    monster = h.get_monster("Ogre King")
    assert monster["name"] == "Ogre King"

    spell = h.get_spell("Magic Missile")
    assert spell["name"] == "Magic Missile"

def test_list_available_delegates(monkeypatch):
    monkeypatch.setattr(LocalAPIHandler, "_load_file", lambda self, cat: [{"name": "Elf"}])
    h = LocalAPIHandler()
    races = h.list_available("races")
    assert races[0]["name"] == "Elf"

def test_list_categories(tmp_path):
    # Create fake SRD files
    path = tmp_path / "rulebook_json"
    path.mkdir()
    (path / "5e-SRD-Spells.json").write_text("[]")
    (path / "5e-SRD-Monsters.json").write_text("[]")

    h = LocalAPIHandler(str(path))
    cats = h.list_categories()
    assert "spells" in cats
    assert "monsters" in cats

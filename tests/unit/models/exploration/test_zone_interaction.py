"""Tests for zone interaction logic."""

from models.exploration.zone_interaction import get_available_interactions, get_inspect_text


class FakeEntity:
    def __init__(self, name="Guard", entity_type="npc", hp=10, max_hp=10, tags=None):
        self.name = name
        self.entity_type = entity_type
        self.hp = hp
        self.max_hp = max_hp
        self.tags = tags or []
        self.locked = False


class TestGetInteractions:

    def test_npc_gets_talk_inspect(self):
        entity = FakeEntity(entity_type="npc")
        result = get_available_interactions(entity)
        ids = [r["id"] for r in result]
        assert "talk" in ids
        assert "inspect" in ids

    def test_merchant_gets_trade(self):
        entity = FakeEntity(entity_type="npc", tags=["merchant"])
        result = get_available_interactions(entity)
        ids = [r["id"] for r in result]
        assert "trade" in ids

    def test_object_gets_search(self):
        entity = FakeEntity(entity_type="object")
        result = get_available_interactions(entity)
        ids = [r["id"] for r in result]
        assert "search" in ids

    def test_container_gets_open(self):
        entity = FakeEntity(entity_type="object", tags=["container"])
        result = get_available_interactions(entity)
        ids = [r["id"] for r in result]
        assert "open" in ids

    def test_locked_gets_pick_lock(self):
        entity = FakeEntity(entity_type="object")
        entity.locked = True
        result = get_available_interactions(entity)
        ids = [r["id"] for r in result]
        assert "pick_lock" in ids

    def test_unconscious_no_talk(self):
        entity = FakeEntity(entity_type="npc", hp=0)
        result = get_available_interactions(entity)
        talk = next(r for r in result if r["id"] == "talk")
        assert talk["enabled"] is False

    def test_dm_sees_all_enabled(self):
        entity = FakeEntity(entity_type="npc", hp=0)
        result = get_available_interactions(entity, viewer_role="dm")
        talk = next(r for r in result if r["id"] == "talk")
        assert talk["enabled"] is True


class TestGetInspectText:

    def test_npc_text(self):
        entity = FakeEntity(name="Marta", entity_type="npc", hp=10, max_hp=10)
        text = get_inspect_text(entity)
        assert "Marta" in text
        assert "healthy" in text.lower()

    def test_wounded_text(self):
        entity = FakeEntity(name="Guard", entity_type="npc", hp=3, max_hp=10)
        text = get_inspect_text(entity)
        assert "wounded" in text.lower()

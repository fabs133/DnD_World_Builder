import pytest
from core.rulebook.entity_importer import EntityImporter
from core.rulebook.rulebook_entity import RulebookEntity

class DummyAPI:
    def __init__(self):
        self.called = False
        self.endpoint = None

    def get(self, path):
        self.called = True
        self.endpoint = path
        return [{"name": "Ogre"}]  # expects a list of dicts

    def get_raw(self, endpoint):
        self.called_with = endpoint
        # simulate a found monster
        if "ogre" in endpoint:
            return {
                'name': 'Ogre',
                'type': 'beast',
                'hit_points': 30,
                'armor_class': [{'value': 11}],
                'speed': {'walk': '30'},
                'strength': 19,
                'dexterity': 8,
                'constitution': 16,
                'intelligence': 5,
                'wisdom': 7,
                'charisma': 7,
                'proficiency_bonus': 2,
                'xp': 450,
                'challenge_rating': 2,
                'special_abilities': [{'name': 'Charge', 'desc': 'Rushes.'}],
                'actions': [{'name': 'Club', 'desc': 'Melee attack.'}]
            }
        return None

@pytest.fixture
def importer(monkeypatch):
    # patch EntityImporter.__init__ so no LocalAPIHandler is called
    monkeypatch.setattr(EntityImporter, "__init__", lambda self, api=None, base_path=None: None)
    imp = EntityImporter()
    imp.api = DummyAPI()
    imp.endpoint = "monsters"
    return imp

def test_list_all_uses_api(importer):
    result = importer.list_all()
    assert importer.api.called is True
    assert importer.api.endpoint == "monsters"
    assert isinstance(result, list)
    assert result[0]["name"] == "Ogre"

def test_parse_creates_rulebook_entity(monkeypatch):
    # patch init so it does not load LocalAPIHandler
    monkeypatch.setattr(EntityImporter, "__init__", lambda self, api=None, base_path=None: None)
    imp = EntityImporter()
    imp.api = DummyAPI()
    imp.endpoint = "monsters"
    raw = {
        'name': 'Trap',
        'type': 'object',
        'hit_points': 0,
        'armor_class': [],
        'speed': {},
        'strength': 0,
        'dexterity': 0,
        'constitution': 0,
        'intelligence': 0,
        'wisdom': 0,
        'charisma': 0,
        'special_abilities': [],
        'actions': []
    }
    entity = imp.parse(raw)
    assert isinstance(entity, RulebookEntity)
    assert entity.name == "Trap"

def test_get_by_name_returns_entity_when_found(importer):
    entity = importer.get_by_name("Ogre")
    assert isinstance(entity, RulebookEntity)
    assert entity.name == "Ogre"

def test_get_by_name_returns_none_when_not_found(monkeypatch):
    monkeypatch.setattr(EntityImporter, "__init__", lambda self, api=None, base_path=None: None)
    imp = EntityImporter()
    imp.api = DummyAPI()
    imp.endpoint = "monsters"
    # force get_raw to return None for unknown
    monkeypatch.setattr(imp.api, "get_raw", lambda endpoint: None)
    entity = imp.get_by_name("Unknown")
    assert entity is None

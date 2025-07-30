import pytest
from core.rulebook.spell_importer import SpellImporter
from core.rulebook.importer_base import BaseImporter
from core.rulebook.rulebook_spell import RulebookSpell

class DummyAPI:
    def __init__(self):
        self.last_endpoint = None
        self.return_value = {'results': []}
    def get(self, endpoint):
        self.last_endpoint = endpoint
        return self.return_value
    def get_raw(self, endpoint):
        self.last_endpoint = endpoint
        return {'name':'Shield','level':1,'school':{'name':'Abjuration'},'casting_time':'1 reaction','duration':'Instantaneous','range':'Self','damage':{},'desc':[], 'dc':None,'classes':[],'area_of_effect':None,'concentration':False,'higher_level':None,'material':None,'components':[]}



@pytest.fixture
def importer(monkeypatch):
    # Stub APIHandler inside BaseImporter
    monkeypatch.setattr('core.rulebook.importer_base.LocalAPIHandler', DummyAPI)
    # Instantiate SpellImporter (inherits BaseImporter)
    si = SpellImporter()
    # Replace internal api with DummyAPI instance for tracking
    si.api = DummyAPI()
    return si

def test_list_all_delegates_to_api(importer):
    # Prepare dummy response
    importer.api.return_value = {'results': [{'name': 'Fireball'}]}
    res = importer.list_all()
    assert importer.api.last_endpoint == 'spells'
    assert res == {'results': [{'name': 'Fireball'}]}

def test_get_by_name_returns_rulebookspell(importer, monkeypatch):
    # Fake raw data
    raw = {'name':'Shield','level':1,'school':{'name':'Abjuration'},'casting_time':'1 reaction','duration':'Instantaneous','range':'Self','damage':{},'desc':[], 'dc':None,'classes':[],'area_of_effect':None,'concentration':False,'higher_level':None,'material':None,'components':[]}
    # Stub get_raw to return raw
    monkeypatch.setattr(importer, 'get_raw', lambda category, name: raw)
    # Spy on from_api without causing recursion
    original = RulebookSpell.from_api
    called = {}
    def fake_from_api(data):
        called['data'] = data
        return original(data)
    monkeypatch.setattr(RulebookSpell, 'from_api', fake_from_api)

    spell = importer.get_by_name('Shield')
    assert called['data'] == raw
    assert isinstance(spell, RulebookSpell)

@pytest.mark.parametrize("raw_input", [
    {'dummy':'data'},
])
def test_parse_wraps_from_api(raw_input, importer, monkeypatch):
    # Spy on from_api without parsing raw data
    caught = {}
    # Create a dummy RulebookSpell to return
    dummy_spell = RulebookSpell(
        name="X", level=0, school="", casting_time="", duration="", range_=""
    )
    def fake_from_api(data):
        caught['data'] = data
        return dummy_spell
    monkeypatch.setattr(RulebookSpell, 'from_api', classmethod(lambda cls, data: fake_from_api(data)))

    obj = importer.parse(raw_input)
    assert caught['data'] is raw_input
    # parse returns our dummy instance
    assert obj is dummy_spell

import pytest
from core.rulebook.importer_base import BaseImporter

class DummyAPI:
    def __init__(self):
        self.called_with = None
    def get(self, endpoint):
        self.called_with = endpoint
        return {'data': 123}
    def get_raw(self, endpoint):
        self.called_with = endpoint
        return {'data': 123}

@pytest.fixture
def importer(monkeypatch):
    # Stub out the underlying APIHandler with DummyAPI
    monkeypatch.setattr('core.rulebook.importer_base.LocalAPIHandler', DummyAPI)
    return BaseImporter()

@pytest.mark.parametrize("name,expected", [
    ("SimpleName", "simplename"),
    ("Name With Spaces", "name-with-spaces"),
    ("  Trim  ", "trim"),
    ("Special!@#Chars$$", "specialchars"),
    ("Multiple   spaces", "multiple-spaces"),
    ("Mixed_CASE-Name", "mixed_case-name"),
])
def test_slugify(name, expected, importer):
    assert importer.slugify(name) == expected


def test_get_raw_calls_api_and_returns(monkeypatch, importer):
    # Replace importer.api with DummyAPI instance
    importer.api = DummyAPI()
    result = importer.get_raw('category', 'Some Name')
    # slugify('Some Name') -> 'some-name'
    assert importer.api.called_with == '/api/category/some-name'
    assert result == {'data': 123}


def test_get_raw_empty_slug(monkeypatch, importer):
    importer.api = DummyAPI()
    # name with only invalid chars becomes empty slug
    result = importer.get_raw('cat', '!!!')
    # slugify('!!!') -> ''
    assert importer.api.called_with == '/api/cat/'  # trailing slash
    assert result == {'data': 123}

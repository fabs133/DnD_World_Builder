"""Tests for shareable rule packs — serialization, validation, ZIP roundtrip."""

import json
import pytest
import tempfile
from pathlib import Path

from domain.specs.pack import (
    RulePack, PackAuthor, PackCategory, PackDependency,
    PackStats, PackValidator, ValidationResult, CompatibilityLevel,
)


def _make_pack(**overrides):
    defaults = dict(
        pack_id="test_pack",
        name="Test Pack",
        version="1.0.0",
        description="A test pack",
        category=PackCategory.HOMEBREW,
        author=PackAuthor(name="Test Author"),
        masks=[{"mask_id": "m1", "components": [{"rule_id": "r1"}]}],
        rulesets=[{"ruleset_id": "rs1", "name": "TestRuleset"}],
    )
    defaults.update(overrides)
    return RulePack(**defaults)


# ── Serialization ───────────────────────────────────────────────────


class TestSerialization:

    def test_to_dict_has_required_keys(self):
        pack = _make_pack()
        d = pack.to_dict()
        assert d["pack_id"] == "test_pack"
        assert d["name"] == "Test Pack"
        assert d["version"] == "1.0.0"

    def test_from_dict_roundtrip(self):
        pack = _make_pack()
        d = pack.to_dict()
        restored = RulePack.from_dict(d)
        assert restored.pack_id == pack.pack_id
        assert restored.name == pack.name
        assert restored.version == pack.version
        assert len(restored.masks) == len(pack.masks)
        assert len(restored.rulesets) == len(pack.rulesets)

    def test_to_json_valid(self):
        pack = _make_pack()
        j = pack.to_json()
        parsed = json.loads(j)
        assert parsed["pack_id"] == "test_pack"

    def test_from_json_roundtrip(self):
        pack = _make_pack()
        j = pack.to_json()
        restored = RulePack.from_json(j)
        assert restored.name == pack.name

    def test_empty_pack(self):
        pack = _make_pack(masks=[], rulesets=[])
        d = pack.to_dict()
        restored = RulePack.from_dict(d)
        assert len(restored.masks) == 0
        assert len(restored.rulesets) == 0

    def test_content_hash_deterministic(self):
        pack = _make_pack()
        h1 = pack.content_hash
        h2 = pack.content_hash
        assert h1 == h2

    def test_content_hash_changes_with_content(self):
        p1 = _make_pack(masks=[{"mask_id": "a", "components": []}])
        p2 = _make_pack(masks=[{"mask_id": "b", "components": []}])
        assert p1.content_hash != p2.content_hash

    def test_full_id(self):
        pack = _make_pack()
        assert pack.full_id == "test_pack@1.0.0"


# ── File I/O ────────────────────────────────────────────────────────


class TestFileIO:

    def test_save_and_load(self, tmp_path):
        pack = _make_pack()
        path = tmp_path / "test_pack.json"
        pack.save(path)
        loaded = RulePack.load(path)
        assert loaded.name == pack.name

    def test_zip_export_and_import(self, tmp_path):
        pack = _make_pack(long_description="# Readme\nTest content")
        zip_path = pack.export_zip(tmp_path / "test_pack")
        assert zip_path.exists()
        imported = RulePack.import_zip(zip_path)
        assert imported.pack_id == pack.pack_id
        assert imported.name == pack.name
        assert len(imported.masks) == len(pack.masks)
        assert len(imported.rulesets) == len(pack.rulesets)


# ── Validation ──────────────────────────────────────────────────────


class TestValidation:

    def _make_validator(self):
        from unittest.mock import MagicMock
        registry = MagicMock()
        registry.get.return_value = MagicMock()  # All rule_ids "exist"
        return PackValidator(registry, app_version="1.0.0")

    def test_valid_pack_passes(self):
        v = self._make_validator()
        pack = _make_pack()
        result = v.validate(pack)
        assert result.valid is True

    def test_missing_pack_id(self):
        v = self._make_validator()
        pack = _make_pack(pack_id="")
        result = v.validate(pack)
        assert result.valid is False
        assert any("Pack ID" in e for e in result.errors)

    def test_missing_name(self):
        v = self._make_validator()
        pack = _make_pack(name="")
        result = v.validate(pack)
        assert result.valid is False

    def test_missing_version(self):
        v = self._make_validator()
        pack = _make_pack(version="")
        result = v.validate(pack)
        assert result.valid is False

    def test_invalid_version_format(self):
        v = self._make_validator()
        pack = _make_pack(version="abc")
        result = v.validate(pack)
        assert result.valid is False
        assert any("version format" in e for e in result.errors)

    def test_compatibility_full(self):
        v = self._make_validator()
        pack = _make_pack(min_app_version="1.0.0")
        result = v.validate(pack)
        assert result.compatibility == CompatibilityLevel.FULL

    def test_compatibility_partial(self):
        v = PackValidator(
            registry=self._make_validator().registry, app_version="0.9.0")
        pack = _make_pack(min_app_version="1.0.0")
        result = v.validate(pack)
        assert result.compatibility == CompatibilityLevel.PARTIAL

    def test_security_check_rejects_eval(self):
        v = self._make_validator()
        pack = _make_pack(description="eval(malicious)")
        result = v.validate(pack)
        assert result.valid is False
        assert any("Suspicious" in e for e in result.errors)

    def test_security_check_rejects_import(self):
        v = self._make_validator()
        pack = _make_pack(description="__import__('os')")
        result = v.validate(pack)
        assert result.valid is False


# ── Data classes ────────────────────────────────────────────────────


class TestDataClasses:

    def test_pack_author_roundtrip(self):
        author = PackAuthor(name="Test", email="t@t.com", github="test")
        d = author.to_dict()
        restored = PackAuthor.from_dict(d)
        assert restored.name == "Test"
        assert restored.github == "test"

    def test_pack_dependency_roundtrip(self):
        dep = PackDependency(pack_id="other", min_version="2.0.0")
        d = dep.to_dict()
        restored = PackDependency.from_dict(d)
        assert restored.pack_id == "other"

    def test_pack_stats_roundtrip(self):
        stats = PackStats(downloads=100, stars=5)
        d = stats.to_dict()
        restored = PackStats.from_dict(d)
        assert restored.downloads == 100

    def test_pack_category_values(self):
        assert len(PackCategory) >= 5
        assert PackCategory.HOMEBREW.value == "homebrew"

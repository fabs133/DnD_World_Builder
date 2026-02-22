"""
Rule Pack - Shareable Collections of Rules

A Rule Pack is a distributable bundle containing:
- Custom rule masks
- Preset rulesets
- Metadata (author, version, compatibility)
- Documentation

Rule Packs can be:
- Exported to JSON/ZIP for sharing
- Published to a community repository
- Imported and validated before use
- Versioned with compatibility tracking

Example packs:
- "Classic Dungeon Traps" - 20 trap templates
- "Naval Combat Rules" - Ship movement and combat
- "Stealth & Infiltration" - Detection and sneaking rules
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from enum import Enum
from datetime import datetime
from pathlib import Path
import json
import hashlib
import zipfile
import tempfile
import shutil


class PackCategory(Enum):
    """Categories for rule packs."""
    TRAPS = "traps"
    COMBAT = "combat"
    EXPLORATION = "exploration"
    SOCIAL = "social"
    MAGIC = "magic"
    ENVIRONMENTAL = "environmental"
    VARIANT_RULES = "variant_rules"
    HOMEBREW = "homebrew"
    CAMPAIGN_SPECIFIC = "campaign_specific"
    UTILITY = "utility"


class CompatibilityLevel(Enum):
    """How compatible a pack is with the current version."""
    FULL = "full"           # Fully compatible
    PARTIAL = "partial"     # Some features may not work
    INCOMPATIBLE = "incompatible"  # Cannot be loaded
    UNKNOWN = "unknown"     # Not yet checked


@dataclass
class PackAuthor:
    """Author information for a rule pack."""
    name: str
    email: str = ""
    url: str = ""
    github: str = ""
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "email": self.email,
            "url": self.url,
            "github": self.github,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PackAuthor:
        return cls(**data)


@dataclass
class PackDependency:
    """Dependency on another rule pack."""
    pack_id: str
    min_version: str = "1.0.0"
    optional: bool = False
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "pack_id": self.pack_id,
            "min_version": self.min_version,
            "optional": self.optional,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PackDependency:
        return cls(**data)


@dataclass
class PackStats:
    """Usage statistics for a rule pack."""
    downloads: int = 0
    stars: int = 0
    forks: int = 0
    last_updated: str = ""
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "downloads": self.downloads,
            "stars": self.stars,
            "forks": self.forks,
            "last_updated": self.last_updated,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PackStats:
        return cls(**data)


@dataclass
class RulePack:
    """
    A shareable collection of rules.
    
    This is the unit of distribution for community rules.
    """
    # Identity
    pack_id: str
    name: str
    version: str
    
    # Metadata
    description: str = ""
    long_description: str = ""  # Markdown supported
    category: PackCategory = PackCategory.HOMEBREW
    tags: list[str] = field(default_factory=list)
    
    # Author info
    author: PackAuthor = field(default_factory=lambda: PackAuthor("Anonymous"))
    contributors: list[PackAuthor] = field(default_factory=list)
    license: str = "CC-BY-4.0"  # Default to Creative Commons
    
    # Content
    masks: list[dict[str, Any]] = field(default_factory=list)  # Serialized RuleMasks
    rulesets: list[dict[str, Any]] = field(default_factory=list)  # Serialized Rulesets
    
    # Dependencies
    dependencies: list[PackDependency] = field(default_factory=list)
    min_app_version: str = "1.0.0"  # Minimum DnD World Builder version
    
    # Stats (populated by repository)
    stats: PackStats = field(default_factory=PackStats)
    
    # Repository info
    repository_url: str = ""
    homepage_url: str = ""
    issues_url: str = ""
    
    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def add_mask(self, mask: "RuleMask"):
        """Add a rule mask to the pack."""
        self.masks.append(mask.to_dict())
    
    def add_ruleset(self, ruleset: "Ruleset"):
        """Add a ruleset to the pack."""
        self.rulesets.append(ruleset.to_dict())
    
    def get_masks(self) -> list["RuleMask"]:
        """Get all masks as RuleMask objects."""
        from domain.specs.builder import RuleMask
        return [RuleMask.from_dict(m) for m in self.masks]
    
    def get_rulesets(self) -> list["Ruleset"]:
        """Get all rulesets as Ruleset objects."""
        from domain.specs.ruleset import Ruleset
        return [Ruleset.from_dict(r) for r in self.rulesets]
    
    @property
    def content_hash(self) -> str:
        """Generate hash of pack contents for integrity checking."""
        content = json.dumps({
            "masks": self.masks,
            "rulesets": self.rulesets,
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    @property
    def full_id(self) -> str:
        """Full identifier including version."""
        return f"{self.pack_id}@{self.version}"
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "pack_id": self.pack_id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "long_description": self.long_description,
            "category": self.category.value,
            "tags": self.tags,
            "author": self.author.to_dict(),
            "contributors": [c.to_dict() for c in self.contributors],
            "license": self.license,
            "masks": self.masks,
            "rulesets": self.rulesets,
            "dependencies": [d.to_dict() for d in self.dependencies],
            "min_app_version": self.min_app_version,
            "stats": self.stats.to_dict(),
            "repository_url": self.repository_url,
            "homepage_url": self.homepage_url,
            "issues_url": self.issues_url,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "content_hash": self.content_hash,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RulePack:
        """Deserialize from dictionary."""
        return cls(
            pack_id=data["pack_id"],
            name=data["name"],
            version=data["version"],
            description=data.get("description", ""),
            long_description=data.get("long_description", ""),
            category=PackCategory(data.get("category", "homebrew")),
            tags=data.get("tags", []),
            author=PackAuthor.from_dict(data.get("author", {"name": "Anonymous"})),
            contributors=[PackAuthor.from_dict(c) for c in data.get("contributors", [])],
            license=data.get("license", "CC-BY-4.0"),
            masks=data.get("masks", []),
            rulesets=data.get("rulesets", []),
            dependencies=[PackDependency.from_dict(d) for d in data.get("dependencies", [])],
            min_app_version=data.get("min_app_version", "1.0.0"),
            stats=PackStats.from_dict(data.get("stats", {})),
            repository_url=data.get("repository_url", ""),
            homepage_url=data.get("homepage_url", ""),
            issues_url=data.get("issues_url", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )
    
    def to_json(self, indent: int = 2) -> str:
        """Export as JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
    
    @classmethod
    def from_json(cls, json_str: str) -> RulePack:
        """Import from JSON string."""
        return cls.from_dict(json.loads(json_str))
    
    def save(self, path: str | Path):
        """Save pack to JSON file."""
        path = Path(path)
        path.write_text(self.to_json())
    
    @classmethod
    def load(cls, path: str | Path) -> RulePack:
        """Load pack from JSON file."""
        path = Path(path)
        return cls.from_json(path.read_text())
    
    def export_zip(self, output_path: str | Path) -> Path:
        """
        Export pack as a ZIP archive.
        
        Structure:
        pack.zip/
        ├── manifest.json      # Pack metadata
        ├── masks/             # Individual mask files
        │   ├── trap_pit.json
        │   └── trap_dart.json
        ├── rulesets/          # Individual ruleset files
        │   └── dungeon.json
        └── README.md          # Long description
        """
        output_path = Path(output_path)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # Create manifest (metadata without content)
            manifest = self.to_dict()
            manifest.pop("masks", None)
            manifest.pop("rulesets", None)
            manifest["mask_count"] = len(self.masks)
            manifest["ruleset_count"] = len(self.rulesets)
            
            (tmpdir / "manifest.json").write_text(
                json.dumps(manifest, indent=2)
            )
            
            # Write masks
            masks_dir = tmpdir / "masks"
            masks_dir.mkdir()
            for mask in self.masks:
                mask_file = masks_dir / f"{mask['mask_id']}.json"
                mask_file.write_text(json.dumps(mask, indent=2))
            
            # Write rulesets
            rulesets_dir = tmpdir / "rulesets"
            rulesets_dir.mkdir()
            for ruleset in self.rulesets:
                rs_file = rulesets_dir / f"{ruleset['ruleset_id']}.json"
                rs_file.write_text(json.dumps(ruleset, indent=2))
            
            # Write README
            if self.long_description:
                (tmpdir / "README.md").write_text(self.long_description)
            
            # Create ZIP
            zip_path = output_path.with_suffix(".zip")
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for file in tmpdir.rglob("*"):
                    if file.is_file():
                        zf.write(file, file.relative_to(tmpdir))
            
            return zip_path
    
    @classmethod
    def import_zip(cls, zip_path: str | Path) -> RulePack:
        """Import pack from ZIP archive."""
        zip_path = Path(zip_path)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # Extract
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(tmpdir)
            
            # Load manifest
            manifest = json.loads((tmpdir / "manifest.json").read_text())
            
            # Load masks
            masks = []
            masks_dir = tmpdir / "masks"
            if masks_dir.exists():
                for mask_file in masks_dir.glob("*.json"):
                    masks.append(json.loads(mask_file.read_text()))
            
            # Load rulesets
            rulesets = []
            rulesets_dir = tmpdir / "rulesets"
            if rulesets_dir.exists():
                for rs_file in rulesets_dir.glob("*.json"):
                    rulesets.append(json.loads(rs_file.read_text()))
            
            # Load README
            readme_path = tmpdir / "README.md"
            if readme_path.exists():
                manifest["long_description"] = readme_path.read_text()
            
            # Reconstruct pack
            manifest["masks"] = masks
            manifest["rulesets"] = rulesets
            
            return cls.from_dict(manifest)


# ─────────────────────────────────────────────────────────────────────────────
# Pack Validation
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ValidationResult:
    """Result of validating a rule pack."""
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    compatibility: CompatibilityLevel = CompatibilityLevel.UNKNOWN
    
    def add_error(self, msg: str):
        self.errors.append(msg)
        self.valid = False
    
    def add_warning(self, msg: str):
        self.warnings.append(msg)


class PackValidator:
    """
    Validates rule packs before import.
    
    Checks:
    - Schema validity
    - Rule references exist
    - No malicious content
    - Version compatibility
    """
    
    def __init__(self, registry: "RuleRegistry", app_version: str = "1.0.0"):
        self.registry = registry
        self.app_version = app_version
    
    def validate(self, pack: RulePack) -> ValidationResult:
        """Validate a rule pack."""
        result = ValidationResult(valid=True)
        
        # Check required fields
        if not pack.pack_id:
            result.add_error("Pack ID is required")
        if not pack.name:
            result.add_error("Pack name is required")
        if not pack.version:
            result.add_error("Pack version is required")
        
        # Validate version format
        if not self._is_valid_version(pack.version):
            result.add_error(f"Invalid version format: {pack.version}")
        
        # Check app version compatibility
        if not self._is_compatible_version(pack.min_app_version, self.app_version):
            result.add_warning(
                f"Pack requires app version {pack.min_app_version}, "
                f"you have {self.app_version}"
            )
            result.compatibility = CompatibilityLevel.PARTIAL
        else:
            result.compatibility = CompatibilityLevel.FULL
        
        # Validate masks
        for i, mask_data in enumerate(pack.masks):
            self._validate_mask(mask_data, i, result)
        
        # Validate rulesets
        for i, ruleset_data in enumerate(pack.rulesets):
            self._validate_ruleset(ruleset_data, i, result)
        
        # Check for suspicious content
        self._check_security(pack, result)
        
        return result
    
    def _validate_mask(self, mask_data: dict, index: int, result: ValidationResult):
        """Validate a single mask."""
        if "mask_id" not in mask_data:
            result.add_error(f"Mask {index}: missing mask_id")
        if "components" not in mask_data:
            result.add_error(f"Mask {index}: missing components")
            return
        
        # Check component rule references
        for j, comp in enumerate(mask_data.get("components", [])):
            rule_id = comp.get("rule_id")
            if not rule_id:
                result.add_error(f"Mask {index}, component {j}: missing rule_id")
            elif not self.registry.get(rule_id):
                result.add_warning(
                    f"Mask {index}, component {j}: unknown rule '{rule_id}'"
                )
    
    def _validate_ruleset(self, ruleset_data: dict, index: int, result: ValidationResult):
        """Validate a single ruleset."""
        if "ruleset_id" not in ruleset_data:
            result.add_error(f"Ruleset {index}: missing ruleset_id")
        if "name" not in ruleset_data:
            result.add_error(f"Ruleset {index}: missing name")
    
    def _check_security(self, pack: RulePack, result: ValidationResult):
        """Check for potentially malicious content."""
        # Check for suspicious patterns in serialized data
        pack_json = pack.to_json()
        
        suspicious_patterns = [
            "__import__",
            "eval(",
            "exec(",
            "compile(",
            "subprocess",
            "os.system",
            "<script",
        ]
        
        for pattern in suspicious_patterns:
            if pattern in pack_json:
                result.add_error(f"Suspicious content detected: {pattern}")
    
    def _is_valid_version(self, version: str) -> bool:
        """Check if version string is valid semver."""
        parts = version.split(".")
        if len(parts) != 3:
            return False
        try:
            for part in parts:
                int(part)
            return True
        except ValueError:
            return False
    
    def _is_compatible_version(self, required: str, current: str) -> bool:
        """Check if current version meets requirement."""
        try:
            req_parts = [int(p) for p in required.split(".")]
            cur_parts = [int(p) for p in current.split(".")]
            return cur_parts >= req_parts
        except ValueError:
            return False


# ─────────────────────────────────────────────────────────────────────────────
# Pack Manager
# ─────────────────────────────────────────────────────────────────────────────

class PackManager:
    """
    Manages installed rule packs.
    
    Handles:
    - Installing/uninstalling packs
    - Loading installed packs
    - Checking for updates
    """
    
    def __init__(self, packs_dir: str | Path, registry: "RuleRegistry"):
        self.packs_dir = Path(packs_dir)
        self.packs_dir.mkdir(parents=True, exist_ok=True)
        self.registry = registry
        self.validator = PackValidator(registry)
        self._installed: dict[str, RulePack] = {}
        self._load_installed()
    
    def _load_installed(self):
        """Load all installed packs."""
        for pack_file in self.packs_dir.glob("*/manifest.json"):
            try:
                pack_dir = pack_file.parent
                pack = self._load_pack_from_dir(pack_dir)
                self._installed[pack.pack_id] = pack
            except Exception as e:
                print(f"Failed to load pack from {pack_file}: {e}")
    
    def _load_pack_from_dir(self, pack_dir: Path) -> RulePack:
        """Load a pack from an installed directory."""
        manifest = json.loads((pack_dir / "manifest.json").read_text())
        
        # Load masks
        masks = []
        masks_dir = pack_dir / "masks"
        if masks_dir.exists():
            for mask_file in masks_dir.glob("*.json"):
                masks.append(json.loads(mask_file.read_text()))
        
        # Load rulesets
        rulesets = []
        rulesets_dir = pack_dir / "rulesets"
        if rulesets_dir.exists():
            for rs_file in rulesets_dir.glob("*.json"):
                rulesets.append(json.loads(rs_file.read_text()))
        
        manifest["masks"] = masks
        manifest["rulesets"] = rulesets
        
        return RulePack.from_dict(manifest)
    
    def install(self, pack: RulePack, force: bool = False) -> ValidationResult:
        """
        Install a rule pack.
        
        Args:
            pack: The pack to install
            force: Skip validation if True
        
        Returns:
            ValidationResult
        """
        # Validate first
        if not force:
            result = self.validator.validate(pack)
            if not result.valid:
                return result
        else:
            result = ValidationResult(valid=True)
        
        # Check for existing installation
        if pack.pack_id in self._installed:
            existing = self._installed[pack.pack_id]
            if existing.version >= pack.version and not force:
                result.add_warning(
                    f"Pack {pack.pack_id} v{existing.version} already installed"
                )
                return result
        
        # Install to packs directory
        pack_dir = self.packs_dir / pack.pack_id
        if pack_dir.exists():
            shutil.rmtree(pack_dir)
        pack_dir.mkdir()
        
        # Write manifest
        manifest = pack.to_dict()
        manifest.pop("masks", None)
        manifest.pop("rulesets", None)
        (pack_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
        
        # Write masks
        masks_dir = pack_dir / "masks"
        masks_dir.mkdir()
        for mask in pack.masks:
            (masks_dir / f"{mask['mask_id']}.json").write_text(
                json.dumps(mask, indent=2)
            )
        
        # Write rulesets
        rulesets_dir = pack_dir / "rulesets"
        rulesets_dir.mkdir()
        for ruleset in pack.rulesets:
            (rulesets_dir / f"{ruleset['ruleset_id']}.json").write_text(
                json.dumps(ruleset, indent=2)
            )
        
        # Update internal state
        self._installed[pack.pack_id] = pack
        
        return result
    
    def uninstall(self, pack_id: str) -> bool:
        """Uninstall a pack."""
        if pack_id not in self._installed:
            return False
        
        pack_dir = self.packs_dir / pack_id
        if pack_dir.exists():
            shutil.rmtree(pack_dir)
        
        del self._installed[pack_id]
        return True
    
    def get(self, pack_id: str) -> RulePack | None:
        """Get an installed pack."""
        return self._installed.get(pack_id)
    
    def get_all(self) -> list[RulePack]:
        """Get all installed packs."""
        return list(self._installed.values())
    
    def is_installed(self, pack_id: str) -> bool:
        """Check if a pack is installed."""
        return pack_id in self._installed
    
    def install_from_zip(self, zip_path: str | Path) -> ValidationResult:
        """Install from a ZIP file."""
        pack = RulePack.import_zip(zip_path)
        return self.install(pack)
    
    def install_from_url(self, url: str) -> ValidationResult:
        """Download and install from URL."""
        import urllib.request
        
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            urllib.request.urlretrieve(url, tmp.name)
            result = self.install_from_zip(tmp.name)
            Path(tmp.name).unlink()
            return result

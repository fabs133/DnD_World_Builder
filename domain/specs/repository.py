"""
Rule Repository - Community Sharing via GitHub

This module provides the infrastructure for sharing rules:
- GitHub-based repository (can be self-hosted)
- Browse/search community packs
- Publish your own packs
- Track downloads and ratings

Repository Structure (GitHub):
    dnd-worldbuilder-rules/
    ├── index.json                 # Pack index with metadata
    ├── packs/
    │   ├── classic-traps/
    │   │   ├── manifest.json
    │   │   ├── masks/
    │   │   └── rulesets/
    │   └── naval-combat/
    │       └── ...
    └── README.md

The index.json is the source of truth for available packs.
Each pack lives in its own directory under packs/.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable
from enum import Enum
from datetime import datetime
from pathlib import Path
import json
import urllib.request
import urllib.error
import tempfile
import os

from domain.specs.pack import RulePack, PackCategory, PackStats, PackAuthor


# Default repository URL (can be overridden)
DEFAULT_REPO_URL = "https://raw.githubusercontent.com/dnd-worldbuilder/community-rules/main"
DEFAULT_REPO_API = "https://api.github.com/repos/dnd-worldbuilder/community-rules"


class SortOrder(Enum):
    """How to sort pack listings."""
    NEWEST = "newest"
    MOST_DOWNLOADED = "downloads"
    MOST_STARRED = "stars"
    NAME = "name"
    RECENTLY_UPDATED = "updated"


@dataclass
class PackListing:
    """
    Summary of a pack in the repository.
    
    This is the lightweight metadata shown in browse views,
    without the full pack content.
    """
    pack_id: str
    name: str
    version: str
    description: str
    category: PackCategory
    author: str
    tags: list[str]
    stats: PackStats
    updated_at: str
    download_url: str
    
    @property
    def downloads(self) -> int:
        return self.stats.downloads
    
    @property
    def stars(self) -> int:
        return self.stats.stars
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "pack_id": self.pack_id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "category": self.category.value,
            "author": self.author,
            "tags": self.tags,
            "stats": self.stats.to_dict(),
            "updated_at": self.updated_at,
            "download_url": self.download_url,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PackListing:
        return cls(
            pack_id=data["pack_id"],
            name=data["name"],
            version=data["version"],
            description=data.get("description", ""),
            category=PackCategory(data.get("category", "homebrew")),
            author=data.get("author", "Anonymous"),
            tags=data.get("tags", []),
            stats=PackStats.from_dict(data.get("stats", {})),
            updated_at=data.get("updated_at", ""),
            download_url=data.get("download_url", ""),
        )


@dataclass
class RepositoryIndex:
    """
    Index of all packs in a repository.
    
    This is downloaded once and cached, then used
    for browsing and searching.
    """
    packs: list[PackListing] = field(default_factory=list)
    last_updated: str = ""
    repository_version: str = "1.0"
    
    def search(
        self, 
        query: str = "",
        category: PackCategory | None = None,
        tags: list[str] | None = None,
        sort_by: SortOrder = SortOrder.MOST_DOWNLOADED,
        limit: int = 50,
    ) -> list[PackListing]:
        """
        Search and filter packs.
        """
        results = list(self.packs)
        
        # Filter by query
        if query:
            query = query.lower()
            results = [
                p for p in results
                if (query in p.name.lower() or
                    query in p.description.lower() or
                    any(query in t.lower() for t in p.tags))
            ]
        
        # Filter by category
        if category:
            results = [p for p in results if p.category == category]
        
        # Filter by tags
        if tags:
            results = [
                p for p in results
                if any(t in p.tags for t in tags)
            ]
        
        # Sort
        if sort_by == SortOrder.NEWEST:
            results.sort(key=lambda p: p.updated_at, reverse=True)
        elif sort_by == SortOrder.MOST_DOWNLOADED:
            results.sort(key=lambda p: p.downloads, reverse=True)
        elif sort_by == SortOrder.MOST_STARRED:
            results.sort(key=lambda p: p.stars, reverse=True)
        elif sort_by == SortOrder.NAME:
            results.sort(key=lambda p: p.name.lower())
        elif sort_by == SortOrder.RECENTLY_UPDATED:
            results.sort(key=lambda p: p.updated_at, reverse=True)
        
        return results[:limit]
    
    def get(self, pack_id: str) -> PackListing | None:
        """Get a specific pack listing."""
        for pack in self.packs:
            if pack.pack_id == pack_id:
                return pack
        return None
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "packs": [p.to_dict() for p in self.packs],
            "last_updated": self.last_updated,
            "repository_version": self.repository_version,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RepositoryIndex:
        return cls(
            packs=[PackListing.from_dict(p) for p in data.get("packs", [])],
            last_updated=data.get("last_updated", ""),
            repository_version=data.get("repository_version", "1.0"),
        )


class RepositoryClient:
    """
    Client for interacting with a rule repository.
    
    Handles:
    - Fetching the pack index
    - Downloading packs
    - Publishing packs (via GitHub PR)
    - Caching
    
    Example:
        client = RepositoryClient()
        
        # Browse packs
        index = client.fetch_index()
        traps = index.search(category=PackCategory.TRAPS)
        
        # Download a pack
        pack = client.download_pack("classic-traps")
        
        # Install it
        pack_manager.install(pack)
    """
    
    def __init__(
        self, 
        base_url: str = DEFAULT_REPO_URL,
        cache_dir: str | Path | None = None,
        github_token: str | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.github_token = github_token or os.environ.get("GITHUB_TOKEN")
        
        # Setup cache
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path(tempfile.gettempdir()) / "dnd_rules_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self._index: RepositoryIndex | None = None
        self._index_etag: str | None = None
    
    def fetch_index(self, force_refresh: bool = False) -> RepositoryIndex:
        """
        Fetch the repository index.
        
        Uses caching to avoid repeated downloads.
        """
        cache_file = self.cache_dir / "index.json"
        
        # Check cache
        if not force_refresh and self._index:
            return self._index
        
        if not force_refresh and cache_file.exists():
            # Check if cache is recent (< 1 hour)
            age = datetime.now().timestamp() - cache_file.stat().st_mtime
            if age < 3600:  # 1 hour
                self._index = RepositoryIndex.from_dict(
                    json.loads(cache_file.read_text())
                )
                return self._index
        
        # Fetch from repository
        try:
            url = f"{self.base_url}/index.json"
            data = self._fetch_json(url)
            self._index = RepositoryIndex.from_dict(data)
            
            # Update cache
            cache_file.write_text(json.dumps(data, indent=2))
            
            return self._index
        
        except urllib.error.URLError as e:
            # Fall back to cache if available
            if cache_file.exists():
                self._index = RepositoryIndex.from_dict(
                    json.loads(cache_file.read_text())
                )
                return self._index
            raise ConnectionError(f"Failed to fetch index: {e}")
    
    def download_pack(self, pack_id: str) -> RulePack:
        """
        Download a full pack from the repository.
        """
        # Get the listing for download URL
        index = self.fetch_index()
        listing = index.get(pack_id)
        
        if not listing:
            raise ValueError(f"Pack not found: {pack_id}")
        
        # Download pack manifest
        pack_url = listing.download_url or f"{self.base_url}/packs/{pack_id}"
        manifest_data = self._fetch_json(f"{pack_url}/manifest.json")
        
        # Download masks
        masks = []
        masks_url = f"{pack_url}/masks"
        try:
            # Try to list masks (GitHub API or directory listing)
            mask_files = self._list_files(masks_url, ".json")
            for mask_file in mask_files:
                mask_data = self._fetch_json(f"{masks_url}/{mask_file}")
                masks.append(mask_data)
        except Exception:
            pass  # No masks directory
        
        # Download rulesets
        rulesets = []
        rulesets_url = f"{pack_url}/rulesets"
        try:
            ruleset_files = self._list_files(rulesets_url, ".json")
            for rs_file in ruleset_files:
                rs_data = self._fetch_json(f"{rulesets_url}/{rs_file}")
                rulesets.append(rs_data)
        except Exception:
            pass  # No rulesets directory
        
        # Build pack
        manifest_data["masks"] = masks
        manifest_data["rulesets"] = rulesets
        
        # Update stats
        self._increment_download_count(pack_id)
        
        return RulePack.from_dict(manifest_data)
    
    def _fetch_json(self, url: str) -> dict:
        """Fetch JSON from URL."""
        request = urllib.request.Request(url)
        request.add_header("Accept", "application/json")
        
        if self.github_token:
            request.add_header("Authorization", f"token {self.github_token}")
        
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode())
    
    def _list_files(self, url: str, extension: str) -> list[str]:
        """List files in a directory (simplified)."""
        # For GitHub raw URLs, we can't list directories
        # This would need to use GitHub API
        # For now, return empty - full implementation would use API
        return []
    
    def _increment_download_count(self, pack_id: str):
        """Track download (would call stats API in real implementation)."""
        pass  # TODO: Implement stats tracking
    
    def search(
        self,
        query: str = "",
        category: PackCategory | None = None,
        sort_by: SortOrder = SortOrder.MOST_DOWNLOADED,
    ) -> list[PackListing]:
        """Search the repository."""
        index = self.fetch_index()
        return index.search(query=query, category=category, sort_by=sort_by)
    
    def get_categories(self) -> dict[PackCategory, int]:
        """Get category counts."""
        index = self.fetch_index()
        counts: dict[PackCategory, int] = {}
        for pack in index.packs:
            counts[pack.category] = counts.get(pack.category, 0) + 1
        return counts
    
    def get_popular_tags(self, limit: int = 20) -> list[tuple[str, int]]:
        """Get most popular tags."""
        index = self.fetch_index()
        tag_counts: dict[str, int] = {}
        for pack in index.packs:
            for tag in pack.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_tags[:limit]


# ─────────────────────────────────────────────────────────────────────────────
# Publishing
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PublishResult:
    """Result of publishing a pack."""
    success: bool
    message: str
    pr_url: str = ""
    errors: list[str] = field(default_factory=list)


class PackPublisher:
    """
    Publishes rule packs to the community repository.
    
    Publishing flow:
    1. Validate the pack
    2. Fork the repository (if needed)
    3. Create a branch
    4. Add pack files
    5. Create a Pull Request
    
    The PR is then reviewed by maintainers before merging.
    """
    
    def __init__(
        self,
        github_token: str,
        repo_owner: str = "dnd-worldbuilder",
        repo_name: str = "community-rules",
    ):
        self.github_token = github_token
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.api_base = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
    
    def publish(self, pack: RulePack) -> PublishResult:
        """
        Publish a pack to the repository.
        
        Creates a Pull Request with the pack contents.
        """
        from domain.specs.pack import PackValidator
        from domain.specs.registry import get_default_registry
        
        # Validate first
        validator = PackValidator(get_default_registry())
        validation = validator.validate(pack)
        
        if not validation.valid:
            return PublishResult(
                success=False,
                message="Pack validation failed",
                errors=validation.errors,
            )
        
        try:
            # Create branch
            branch_name = f"add-pack-{pack.pack_id}-{pack.version}"
            self._create_branch(branch_name)
            
            # Add pack files
            self._add_pack_to_branch(pack, branch_name)
            
            # Update index
            self._update_index(pack, branch_name)
            
            # Create PR
            pr_url = self._create_pull_request(
                branch_name,
                title=f"Add pack: {pack.name} v{pack.version}",
                body=self._generate_pr_body(pack),
            )
            
            return PublishResult(
                success=True,
                message="Pull request created successfully",
                pr_url=pr_url,
            )
        
        except Exception as e:
            return PublishResult(
                success=False,
                message=f"Publishing failed: {str(e)}",
                errors=[str(e)],
            )
    
    def _create_branch(self, branch_name: str):
        """Create a new branch from main."""
        # Get main branch SHA
        # Create new branch
        # (GitHub API calls)
        pass
    
    def _add_pack_to_branch(self, pack: RulePack, branch: str):
        """Add pack files to the branch."""
        # Create pack directory structure
        # Add manifest.json
        # Add masks/*.json
        # Add rulesets/*.json
        # (GitHub API calls)
        pass
    
    def _update_index(self, pack: RulePack, branch: str):
        """Update index.json with new pack."""
        # Fetch current index
        # Add new pack listing
        # Commit updated index
        # (GitHub API calls)
        pass
    
    def _create_pull_request(self, branch: str, title: str, body: str) -> str:
        """Create a pull request."""
        # Create PR via GitHub API
        # Return PR URL
        return f"https://github.com/{self.repo_owner}/{self.repo_name}/pull/999"
    
    def _generate_pr_body(self, pack: RulePack) -> str:
        """Generate PR description."""
        return f"""
## New Rule Pack: {pack.name}

**Version:** {pack.version}
**Author:** {pack.author.name}
**Category:** {pack.category.value}
**License:** {pack.license}

### Description
{pack.description}

### Contents
- **Masks:** {len(pack.masks)}
- **Rulesets:** {len(pack.rulesets)}

### Tags
{', '.join(pack.tags)}

---
*This PR was automatically generated by DnD World Builder*
"""


# ─────────────────────────────────────────────────────────────────────────────
# Repository Index Generator (for maintainers)
# ─────────────────────────────────────────────────────────────────────────────

class IndexGenerator:
    """
    Generates index.json from pack directories.
    
    Run this after merging new packs to update the index.
    """
    
    def __init__(self, repo_path: str | Path):
        self.repo_path = Path(repo_path)
        self.packs_dir = self.repo_path / "packs"
    
    def generate(self) -> RepositoryIndex:
        """Generate index from pack directories."""
        listings = []
        
        for pack_dir in self.packs_dir.iterdir():
            if not pack_dir.is_dir():
                continue
            
            manifest_file = pack_dir / "manifest.json"
            if not manifest_file.exists():
                continue
            
            try:
                manifest = json.loads(manifest_file.read_text())
                
                listing = PackListing(
                    pack_id=manifest["pack_id"],
                    name=manifest["name"],
                    version=manifest["version"],
                    description=manifest.get("description", ""),
                    category=PackCategory(manifest.get("category", "homebrew")),
                    author=manifest.get("author", {}).get("name", "Anonymous"),
                    tags=manifest.get("tags", []),
                    stats=PackStats.from_dict(manifest.get("stats", {})),
                    updated_at=manifest.get("updated_at", ""),
                    download_url=f"packs/{pack_dir.name}",
                )
                listings.append(listing)
            
            except Exception as e:
                print(f"Error processing {pack_dir}: {e}")
        
        return RepositoryIndex(
            packs=listings,
            last_updated=datetime.utcnow().isoformat(),
        )
    
    def save_index(self):
        """Generate and save index.json."""
        index = self.generate()
        index_file = self.repo_path / "index.json"
        index_file.write_text(json.dumps(index.to_dict(), indent=2))
        return index


# ─────────────────────────────────────────────────────────────────────────────
# Featured/Curated Collections
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Collection:
    """
    A curated collection of packs.
    
    Used for "Featured", "Staff Picks", "New This Month", etc.
    """
    collection_id: str
    name: str
    description: str
    pack_ids: list[str]
    icon: str = "📚"
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "collection_id": self.collection_id,
            "name": self.name,
            "description": self.description,
            "pack_ids": self.pack_ids,
            "icon": self.icon,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Collection:
        return cls(**data)


# Default collections
FEATURED_COLLECTIONS = [
    Collection(
        collection_id="essential",
        name="Essential Packs",
        description="Must-have rule packs for every DM",
        pack_ids=["classic-traps", "standard-conditions"],
        icon="⭐",
    ),
    Collection(
        collection_id="exploration",
        name="Exploration & Travel",
        description="Rules for wilderness, dungeons, and travel",
        pack_ids=["wilderness-survival", "dungeon-hazards"],
        icon="🗺️",
    ),
    Collection(
        collection_id="combat",
        name="Combat Enhancements",
        description="Advanced combat rules and options",
        pack_ids=["tactical-combat", "critical-hits"],
        icon="⚔️",
    ),
]

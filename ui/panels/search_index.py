"""Global search index for all entities, objects, and labeled tiles.

Pure Python — no Qt dependency. Scans scene items to build a flat
searchable list that the QuickSearchPanel filters in real time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


_ENTITY_CATEGORIES = {
    "player": "entity", "enemy": "entity", "npc": "entity",
    "ally": "entity", "companion": "entity", "monster": "entity",
    "hostile": "entity",
}


@dataclass
class SearchResultItem:
    """One searchable item in the index."""
    name: str
    category: str              # "entity", "object", "tile"
    subcategory: str           # "enemy", "npc", "player", etc.
    tile_id: str
    tile_position: tuple[int, int]
    tile_label: str | None
    entity_type_str: str       # raw entity_type for display
    source_entity: Any = None  # GameEntity reference
    source_tile_item: Any = None  # SquareTileItem reference (for navigation)
    search_text: str = ""      # pre-built lowercase text for matching


class SearchIndex:
    """Builds and queries a flat index of all searchable items in the scene."""

    def __init__(self):
        self._items: list[SearchResultItem] = []

    @property
    def items(self) -> list[SearchResultItem]:
        return self._items

    def build(self, scene_items) -> None:
        """Scan all tile items in the scene and build the index.

        :param scene_items: Iterable of QGraphicsItems from the scene.
        """
        self._items.clear()

        for item in scene_items:
            tile_data = getattr(item, "tile_data", None)
            if tile_data is None:
                continue

            tile_id = getattr(tile_data, "tile_id", "")
            position = getattr(tile_data, "position", (0, 0))
            if isinstance(position, list):
                position = tuple(position)
            label = getattr(tile_data, "user_label", None)
            note = getattr(tile_data, "note", None)

            # Index entities on this tile
            entities = getattr(tile_data, "entities", [])
            for ent in entities:
                if isinstance(ent, dict):
                    name = ent.get("name", "?")
                    etype = str(ent.get("entity_type", "")).lower()
                else:
                    name = getattr(ent, "name", "?")
                    etype = str(getattr(ent, "entity_type", "")).lower()

                category = _ENTITY_CATEGORIES.get(etype, "object")
                search_parts = [name.lower(), etype, str(position)]
                if label:
                    search_parts.append(label.lower())

                self._items.append(SearchResultItem(
                    name=name,
                    category=category,
                    subcategory=etype,
                    tile_id=tile_id,
                    tile_position=position,
                    tile_label=label,
                    entity_type_str=etype,
                    source_entity=ent,
                    source_tile_item=item,
                    search_text=" ".join(search_parts),
                ))

            # Index the tile itself if it has a label or note
            if label or note:
                search_parts = []
                if label:
                    search_parts.append(label.lower())
                if note:
                    search_parts.append(note.lower())
                search_parts.append(str(position))

                # Determine tile subcategory from tags
                tags = getattr(tile_data, "tags", [])
                tag_strs = [str(t).lower() for t in tags]
                if "trap_zone" in tag_strs:
                    subcat = "trap"
                elif "start_zone" in tag_strs:
                    subcat = "spawn"
                else:
                    subcat = "location"

                self._items.append(SearchResultItem(
                    name=label or "(noted tile)",
                    category="tile",
                    subcategory=subcat,
                    tile_id=tile_id,
                    tile_position=position,
                    tile_label=label,
                    entity_type_str=subcat,
                    source_tile_item=item,
                    search_text=" ".join(search_parts),
                ))

    def search(
        self,
        query: str,
        categories: set[str] | None = None,
        subcategories: set[str] | None = None,
    ) -> list[SearchResultItem]:
        """Filter index by query text and optional category/subcategory sets."""
        q = query.strip().lower()
        results = []
        for item in self._items:
            if categories and item.category not in categories:
                continue
            if subcategories and item.subcategory not in subcategories:
                continue
            if q and q not in item.search_text:
                continue
            results.append(item)
        return results

    def count_by_type(self, entity_type: str) -> int:
        """Count entities matching a type string (case-insensitive)."""
        t = entity_type.lower()
        return sum(1 for i in self._items if i.subcategory == t)

    def total(self) -> int:
        return len(self._items)

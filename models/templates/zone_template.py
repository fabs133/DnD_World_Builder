from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

@dataclass
class ZoneTemplate:
    template_id: str
    name: str
    zones_data: list[dict[str, Any]]   # list of TileZone.to_dict() format
    tags: list[str] = field(default_factory=list)
    description: str = ""
    is_builtin: bool = False

    def to_zones_dicts(self) -> list[dict]:
        return deepcopy(self.zones_data)

    def to_dict(self) -> dict:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "zones_data": self.zones_data,
            "tags": self.tags,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ZoneTemplate:
        return cls(
            template_id=data["template_id"],
            name=data["name"],
            zones_data=data["zones_data"],
            tags=data.get("tags", []),
            description=data.get("description", ""),
            is_builtin=data.get("is_builtin", False),
        )

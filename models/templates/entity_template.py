from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

@dataclass
class EntityTemplate:
    template_id: str
    name: str
    category: str         # "npc", "enemy", "object"
    entity_data: dict[str, Any]   # GameEntity.to_dict() format
    tags: list[str] = field(default_factory=list)
    description: str = ""
    is_builtin: bool = False

    def to_entity_dict(self) -> dict:
        return deepcopy(self.entity_data)

    def to_dict(self) -> dict:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "category": self.category,
            "entity_data": self.entity_data,
            "tags": self.tags,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> EntityTemplate:
        return cls(
            template_id=data["template_id"],
            name=data["name"],
            category=data["category"],
            entity_data=data["entity_data"],
            tags=data.get("tags", []),
            description=data.get("description", ""),
            is_builtin=data.get("is_builtin", False),
        )

    @classmethod
    def from_entity(cls, entity, template_id: str, tags=None, description="") -> EntityTemplate:
        data = entity.to_dict() if hasattr(entity, "to_dict") else dict(entity)
        return cls(
            template_id=template_id,
            name=data.get("name", template_id),
            category=data.get("entity_type", "npc"),
            entity_data=data,
            tags=tags or [],
            description=description,
        )

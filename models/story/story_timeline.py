"""Story timeline data model for tracking scenes and narrative progression."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SceneEntry:
    """A single scene in the story timeline."""

    scene_id: str
    title: str
    description: str = ""
    tile_ids: list[str] = field(default_factory=list)
    notes: str = ""
    status: str = "planned"  # planned | active | completed | skipped
    order: int = 0
    act: str = ""

    def to_dict(self) -> dict:
        return {
            "scene_id": self.scene_id,
            "title": self.title,
            "description": self.description,
            "tile_ids": list(self.tile_ids),
            "notes": self.notes,
            "status": self.status,
            "order": self.order,
            "act": self.act,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SceneEntry:
        return cls(
            scene_id=data["scene_id"],
            title=data["title"],
            description=data.get("description", ""),
            tile_ids=data.get("tile_ids", []),
            notes=data.get("notes", ""),
            status=data.get("status", "planned"),
            order=data.get("order", 0),
            act=data.get("act", ""),
        )


@dataclass
class StoryTimeline:
    """Ordered collection of scenes forming a story arc."""

    scenes: list[SceneEntry] = field(default_factory=list)

    # -- mutation ----------------------------------------------------------

    def add_scene(self, title: str, tile_ids: list[str] | None = None, act: str = "") -> SceneEntry:
        """Create and append a new scene, returning it."""
        scene = SceneEntry(
            scene_id=uuid.uuid4().hex[:12],
            title=title,
            tile_ids=tile_ids if tile_ids is not None else [],
            order=len(self.scenes),
            act=act,
        )
        self.scenes.append(scene)
        return scene

    def remove_scene(self, scene_id: str) -> None:
        """Remove a scene by its id and renumber remaining orders."""
        self.scenes = [s for s in self.scenes if s.scene_id != scene_id]
        for idx, scene in enumerate(self.scenes):
            scene.order = idx

    def reorder(self, scene_id: str, new_index: int) -> None:
        """Move a scene to *new_index* and renumber all orders."""
        scene = self._find(scene_id)
        self.scenes.remove(scene)
        self.scenes.insert(new_index, scene)
        for idx, s in enumerate(self.scenes):
            s.order = idx

    # -- status helpers ----------------------------------------------------

    def get_active(self) -> SceneEntry | None:
        """Return the currently active scene, or None."""
        for scene in self.scenes:
            if scene.status == "active":
                return scene
        return None

    def mark_active(self, scene_id: str) -> None:
        """Set *scene_id* to active; demote any other active scene to planned."""
        for scene in self.scenes:
            if scene.status == "active":
                scene.status = "planned"
        target = self._find(scene_id)
        target.status = "active"

    def mark_completed(self, scene_id: str) -> None:
        """Set *scene_id* status to completed."""
        target = self._find(scene_id)
        target.status = "completed"

    # -- serialization -----------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "scenes": [s.to_dict() for s in self.scenes],
        }

    @classmethod
    def from_dict(cls, data: dict) -> StoryTimeline:
        scenes = [SceneEntry.from_dict(d) for d in data.get("scenes", [])]
        return cls(scenes=scenes)

    def save(self, path: Path) -> None:
        """Write the timeline to a JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> StoryTimeline:
        """Read a timeline from a JSON file."""
        path = Path(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_dict(data)

    # -- internal ----------------------------------------------------------

    def _find(self, scene_id: str) -> SceneEntry:
        for scene in self.scenes:
            if scene.scene_id == scene_id:
                return scene
        raise KeyError(f"Scene not found: {scene_id}")

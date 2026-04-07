"""Tests for the StoryTimeline data model."""

import json
from pathlib import Path

from models.story.story_timeline import SceneEntry, StoryTimeline


class TestSceneEntrySerialization:

    def test_scene_entry_serialization(self):
        """Roundtrip to_dict / from_dict preserves all fields."""
        scene = SceneEntry(
            scene_id="abc123",
            title="Ambush at the Bridge",
            description="Bandits block the road.",
            tile_ids=["tile_01", "tile_02"],
            notes="Play dramatic music.",
            status="active",
            order=3,
            act="Act II",
        )
        data = scene.to_dict()
        restored = SceneEntry.from_dict(data)

        assert restored.scene_id == scene.scene_id
        assert restored.title == scene.title
        assert restored.description == scene.description
        assert restored.tile_ids == scene.tile_ids
        assert restored.notes == scene.notes
        assert restored.status == scene.status
        assert restored.order == scene.order
        assert restored.act == scene.act


class TestStoryTimeline:

    def test_timeline_add_scene(self):
        """Adding 3 scenes assigns orders 0, 1, 2."""
        tl = StoryTimeline()
        s0 = tl.add_scene("Intro")
        s1 = tl.add_scene("Rising Action")
        s2 = tl.add_scene("Climax")

        assert len(tl.scenes) == 3
        assert s0.order == 0
        assert s1.order == 1
        assert s2.order == 2
        # Each scene_id should be a 12-char hex string
        for s in tl.scenes:
            assert len(s.scene_id) == 12

    def test_timeline_remove_scene(self):
        """Removing the middle scene re-numbers the rest."""
        tl = StoryTimeline()
        s0 = tl.add_scene("A")
        s1 = tl.add_scene("B")
        s2 = tl.add_scene("C")

        tl.remove_scene(s1.scene_id)

        assert len(tl.scenes) == 2
        assert tl.scenes[0].scene_id == s0.scene_id
        assert tl.scenes[1].scene_id == s2.scene_id
        assert tl.scenes[0].order == 0
        assert tl.scenes[1].order == 1

    def test_timeline_reorder(self):
        """Moving scene from index 2 to 0 shifts others down."""
        tl = StoryTimeline()
        s0 = tl.add_scene("A")
        s1 = tl.add_scene("B")
        s2 = tl.add_scene("C")

        tl.reorder(s2.scene_id, 0)

        assert tl.scenes[0].scene_id == s2.scene_id
        assert tl.scenes[1].scene_id == s0.scene_id
        assert tl.scenes[2].scene_id == s1.scene_id
        for idx, scene in enumerate(tl.scenes):
            assert scene.order == idx

    def test_mark_active(self):
        """Only one scene can be active at a time."""
        tl = StoryTimeline()
        s0 = tl.add_scene("A")
        s1 = tl.add_scene("B")
        s2 = tl.add_scene("C")

        tl.mark_active(s0.scene_id)
        assert tl.get_active().scene_id == s0.scene_id

        tl.mark_active(s2.scene_id)
        assert tl.get_active().scene_id == s2.scene_id
        # Previous active should be demoted to planned
        assert s0.status == "planned"
        assert s2.status == "active"

    def test_mark_completed(self):
        """Marking a scene completed changes its status."""
        tl = StoryTimeline()
        s0 = tl.add_scene("A")
        tl.mark_active(s0.scene_id)
        tl.mark_completed(s0.scene_id)

        assert s0.status == "completed"
        assert tl.get_active() is None

    def test_save_and_load(self, tmp_path: Path):
        """Save to a temp file, load back, and verify data integrity."""
        tl = StoryTimeline()
        s0 = tl.add_scene("Intro", tile_ids=["t1"], act="Act I")
        s1 = tl.add_scene("Battle", tile_ids=["t2", "t3"], act="Act II")
        tl.mark_active(s1.scene_id)

        filepath = tmp_path / "timeline.json"
        tl.save(filepath)

        # Verify the file is valid JSON
        raw = json.loads(filepath.read_text(encoding="utf-8"))
        assert "scenes" in raw
        assert len(raw["scenes"]) == 2

        loaded = StoryTimeline.load(filepath)
        assert len(loaded.scenes) == 2
        assert loaded.scenes[0].title == "Intro"
        assert loaded.scenes[0].tile_ids == ["t1"]
        assert loaded.scenes[0].act == "Act I"
        assert loaded.scenes[1].title == "Battle"
        assert loaded.scenes[1].status == "active"
        assert loaded.get_active().scene_id == s1.scene_id

    def test_get_active_none(self):
        """Empty timeline returns None for get_active."""
        tl = StoryTimeline()
        assert tl.get_active() is None

    def test_add_scene_with_tile_ids(self):
        """tile_ids passed to add_scene are stored on the SceneEntry."""
        tl = StoryTimeline()
        scene = tl.add_scene("Tavern", tile_ids=["tavern_floor", "tavern_bar"])

        assert scene.tile_ids == ["tavern_floor", "tavern_bar"]
        assert tl.scenes[0].tile_ids == ["tavern_floor", "tavern_bar"]

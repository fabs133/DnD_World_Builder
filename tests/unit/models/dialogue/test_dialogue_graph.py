"""Tests for the dialogue graph system."""

import pytest

from models.dialogue.dialogue_graph import (
    DialogueCondition,
    DialogueGraph,
    DialogueNode,
    DialogueOption,
    EMOTION_PRESETS,
)


# ── Fixtures ─────────────────────────────────────────────────────────

def _simple_graph() -> DialogueGraph:
    """A minimal valid graph: greeting -> lore -> farewell."""
    return DialogueGraph(
        entry_node="greeting_0",
        nodes={
            "greeting_0": DialogueNode(
                node_id="greeting_0",
                text="Hello there!",
                emotion="friendly",
                options=[
                    DialogueOption(text="Tell me more.", next_node="lore_0"),
                    DialogueOption(text="Goodbye.", next_node="farewell_0"),
                ],
            ),
            "lore_0": DialogueNode(
                node_id="lore_0",
                text="This place has a long history.",
                options=[
                    DialogueOption(text="Interesting.", next_node="greeting_0"),
                    DialogueOption(text="Goodbye.", next_node="farewell_0"),
                ],
            ),
            "farewell_0": DialogueNode(
                node_id="farewell_0",
                text="Safe travels!",
                is_terminal=True,
            ),
        },
    )


def _conditional_graph() -> DialogueGraph:
    """Graph with flag-based conditions."""
    return DialogueGraph(
        entry_node="greeting_0",
        nodes={
            "greeting_0": DialogueNode(
                node_id="greeting_0",
                text="Welcome back.",
                options=[
                    DialogueOption(
                        text="I dealt with the wolves.",
                        next_node="quest_done",
                        conditions=[DialogueCondition("wolves_killed", True)],
                        set_flags={"wolves_rewarded": True},
                    ),
                    DialogueOption(
                        text="About those wolves...",
                        next_node="quest_offer",
                        conditions=[DialogueCondition("wolves_killed", False)],
                    ),
                    DialogueOption(text="Bye.", next_node="farewell_0"),
                ],
            ),
            "quest_offer": DialogueNode(
                node_id="quest_offer",
                text="Wolves plague the north road. Handle them?",
                emotion="commanding",
                set_flags={"quest_offered": True},
                options=[
                    DialogueOption(text="I'll do it.", next_node="farewell_0",
                                   set_flags={"quest_accepted": True}),
                    DialogueOption(text="Not now.", next_node="greeting_0"),
                ],
            ),
            "quest_done": DialogueNode(
                node_id="quest_done",
                text="Excellent work! Here's your reward.",
                emotion="excited",
                options=[
                    DialogueOption(text="Thanks.", next_node="farewell_0"),
                ],
            ),
            "farewell_0": DialogueNode(
                node_id="farewell_0",
                text="Good luck.",
                is_terminal=True,
            ),
        },
    )


# ── DialogueCondition ────────────────────────────────────────────────

class TestDialogueCondition:

    def test_evaluate_flag_set(self):
        c = DialogueCondition("quest_done", True)
        assert c.evaluate({"quest_done": True})
        assert not c.evaluate({"quest_done": False})
        assert not c.evaluate({})  # missing = False

    def test_evaluate_flag_not_set(self):
        c = DialogueCondition("quest_done", False)
        assert c.evaluate({})  # missing = False, expected False → True
        assert c.evaluate({"quest_done": False})
        assert not c.evaluate({"quest_done": True})

    def test_roundtrip(self):
        c = DialogueCondition("has_key", False)
        d = c.to_dict()
        c2 = DialogueCondition.from_dict(d)
        assert c2.flag == "has_key"
        assert c2.expected is False

    def test_default_expected_true(self):
        c = DialogueCondition.from_dict({"flag": "x"})
        assert c.expected is True


# ── DialogueOption ───────────────────────────────────────────────────

class TestDialogueOption:

    def test_available_no_conditions(self):
        o = DialogueOption(text="Hi", next_node="n1")
        assert o.is_available({})

    def test_available_with_conditions(self):
        o = DialogueOption(
            text="Report success",
            next_node="done",
            conditions=[
                DialogueCondition("quest_accepted", True),
                DialogueCondition("quest_failed", False),
            ],
        )
        assert o.is_available({"quest_accepted": True})
        assert not o.is_available({"quest_accepted": False})
        assert not o.is_available({"quest_accepted": True, "quest_failed": True})

    def test_roundtrip(self):
        o = DialogueOption(
            text="Do it", next_node="n2",
            conditions=[DialogueCondition("flag_a")],
            set_flags={"accepted": True},
            priority=5,
        )
        d = o.to_dict()
        o2 = DialogueOption.from_dict(d)
        assert o2.text == "Do it"
        assert o2.next_node == "n2"
        assert len(o2.conditions) == 1
        assert o2.set_flags == {"accepted": True}
        assert o2.priority == 5

    def test_minimal_dict(self):
        o = DialogueOption(text="Hi", next_node="n1")
        d = o.to_dict()
        assert "conditions" not in d
        assert "set_flags" not in d
        assert "priority" not in d


# ── DialogueNode ─────────────────────────────────────────────────────

class TestDialogueNode:

    def test_voice_params_no_emotion(self):
        n = DialogueNode(node_id="n", text="Hello")
        assert n.get_voice_params() == {}

    def test_voice_params_emotion(self):
        n = DialogueNode(node_id="n", text="Watch out!", emotion="fearful")
        params = n.get_voice_params()
        assert params["exaggeration"] == 0.7
        assert params["speed_factor"] == 1.1

    def test_voice_params_override(self):
        n = DialogueNode(
            node_id="n", text="RAGE!", emotion="angry",
            voice_overrides={"exaggeration": 0.99},
        )
        params = n.get_voice_params()
        assert params["exaggeration"] == 0.99  # override wins
        assert params["speed_factor"] == 0.9   # from angry preset

    def test_roundtrip(self):
        n = DialogueNode(
            node_id="q1", text="Got a quest?",
            set_flags={"seen_quest": True},
            category="quest", emotion="friendly",
            voice_overrides={"speed_factor": 1.1},
            options=[DialogueOption(text="Sure", next_node="q2")],
        )
        d = n.to_dict()
        n2 = DialogueNode.from_dict(d)
        assert n2.node_id == "q1"
        assert n2.emotion == "friendly"
        assert n2.voice_overrides == {"speed_factor": 1.1}
        assert len(n2.options) == 1

    def test_terminal_minimal_dict(self):
        n = DialogueNode(node_id="end", text="Bye.", is_terminal=True)
        d = n.to_dict()
        assert d["is_terminal"] is True
        assert "options" not in d
        assert "emotion" not in d


# ── DialogueGraph ────────────────────────────────────────────────────

class TestDialogueGraph:

    def test_get_node(self):
        g = _simple_graph()
        assert g.get_node("greeting_0") is not None
        assert g.get_node("nonexistent") is None

    def test_all_texts(self):
        g = _simple_graph()
        texts = g.all_texts()
        ids = [t[0] for t in texts]
        assert "greeting_0" in ids
        assert "lore_0" in ids
        assert "farewell_0" in ids

    def test_roundtrip(self):
        g = _simple_graph()
        d = g.to_dict()
        g2 = DialogueGraph.from_dict(d)
        assert g2.entry_node == "greeting_0"
        assert len(g2.nodes) == 3
        assert g2.get_node("lore_0").text == "This place has a long history."

    def test_validate_valid(self):
        g = _simple_graph()
        assert g.validate() == []

    def test_validate_missing_entry(self):
        g = DialogueGraph(entry_node="missing", nodes={})
        errors = g.validate()
        assert any("not found" in e for e in errors)

    def test_validate_dangling_ref(self):
        g = DialogueGraph(
            entry_node="n1",
            nodes={"n1": DialogueNode(
                node_id="n1", text="Hi",
                options=[DialogueOption(text="Go", next_node="missing")])},
        )
        errors = g.validate()
        assert any("unknown node" in e for e in errors)

    def test_validate_dead_end(self):
        g = DialogueGraph(
            entry_node="n1",
            nodes={"n1": DialogueNode(node_id="n1", text="Hi")},
        )
        errors = g.validate()
        assert any("dead end" in e for e in errors)

    def test_validate_unreachable(self):
        g = DialogueGraph(
            entry_node="n1",
            nodes={
                "n1": DialogueNode(
                    node_id="n1", text="Hi", is_terminal=True),
                "orphan": DialogueNode(
                    node_id="orphan", text="Nobody reaches me",
                    is_terminal=True),
            },
        )
        errors = g.validate()
        assert any("unreachable" in e for e in errors)

    def test_validate_unknown_emotion(self):
        g = DialogueGraph(
            entry_node="n1",
            nodes={"n1": DialogueNode(
                node_id="n1", text="Hi", emotion="nonexistent",
                is_terminal=True)},
        )
        errors = g.validate()
        assert any("unknown emotion" in e for e in errors)


# ── Backward compatibility ───────────────────────────────────────────

class TestFromDialogueLines:

    def test_converts_basic(self):
        lines = {
            "greeting": ["Hello!"],
            "lore": ["The castle is old.", "Very old indeed."],
            "farewell": ["Goodbye."],
        }
        g = DialogueGraph.from_dialogue_lines(lines)
        errors = g.validate()
        assert errors == [], f"Conversion produced invalid graph: {errors}"

    def test_entry_is_greeting(self):
        lines = {"greeting": ["Hi!"], "farewell": ["Bye."]}
        g = DialogueGraph.from_dialogue_lines(lines)
        assert g.entry_node == "greeting_0"
        assert g.get_node("greeting_0").text == "Hi!"

    def test_hub_has_category_options(self):
        lines = {
            "greeting": ["Hi!"],
            "lore": ["History here."],
            "quest": ["Got a job."],
            "farewell": ["Bye."],
        }
        g = DialogueGraph.from_dialogue_lines(lines)
        hub = g.get_node("hub")
        option_targets = {o.next_node for o in hub.options}
        assert "lore_0" in option_targets
        assert "quest_0" in option_targets
        assert "farewell_0" in option_targets

    def test_category_chain(self):
        lines = {
            "greeting": ["Hi!"],
            "lore": ["Part 1.", "Part 2.", "Part 3."],
            "farewell": ["Bye."],
        }
        g = DialogueGraph.from_dialogue_lines(lines)
        # lore_0 -> lore_1 -> lore_2 -> hub
        n0 = g.get_node("lore_0")
        assert any(o.next_node == "lore_1" for o in n0.options)
        n1 = g.get_node("lore_1")
        assert any(o.next_node == "lore_2" for o in n1.options)
        n2 = g.get_node("lore_2")
        assert any(o.next_node == "hub" for o in n2.options)

    def test_farewell_is_terminal(self):
        lines = {"greeting": ["Hi!"], "farewell": ["Bye.", "Later."]}
        g = DialogueGraph.from_dialogue_lines(lines)
        assert g.get_node("farewell_0").is_terminal

    def test_empty_category_skipped(self):
        lines = {"greeting": ["Hi!"], "lore": [], "farewell": ["Bye."]}
        g = DialogueGraph.from_dialogue_lines(lines)
        hub = g.get_node("hub")
        assert not any(o.next_node == "lore_0" for o in hub.options)


# ── Conditional graph ────────────────────────────────────────────────

class TestConditionalGraph:

    def test_options_filtered_by_flags(self):
        g = _conditional_graph()
        node = g.get_node("greeting_0")

        # No wolves killed → only quest_offer and bye visible
        flags: dict[str, bool] = {}
        available = [o for o in node.options if o.is_available(flags)]
        targets = {o.next_node for o in available}
        assert "quest_offer" in targets
        assert "quest_done" not in targets

        # Wolves killed → quest_done visible, quest_offer hidden
        flags = {"wolves_killed": True}
        available = [o for o in node.options if o.is_available(flags)]
        targets = {o.next_node for o in available}
        assert "quest_done" in targets
        assert "quest_offer" not in targets

    def test_flags_set_on_option(self):
        g = _conditional_graph()
        node = g.get_node("greeting_0")
        opt = [o for o in node.options if o.next_node == "quest_done"][0]
        assert opt.set_flags == {"wolves_rewarded": True}

    def test_flags_set_on_node(self):
        g = _conditional_graph()
        node = g.get_node("quest_offer")
        assert node.set_flags == {"quest_offered": True}

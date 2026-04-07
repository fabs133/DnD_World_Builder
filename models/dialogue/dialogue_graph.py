"""Branching dialogue graph for NPC conversations.

A directed graph of :class:`DialogueNode` objects connected by
:class:`DialogueOption` player responses.  Supports flag-based
conditions, per-node emotion/voice overrides, and auto-conversion
from the legacy flat ``dialogue_lines`` format.

Usage::

    graph = DialogueGraph.from_dict(entity_data["dialogue_graph"])
    node = graph.get_node(graph.entry_node)
    available = [o for o in node.options if o.is_available(flags)]
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ── Emotion presets for voice generation ─────────────────────────────

EMOTION_PRESETS: Dict[str, Dict[str, float]] = {
    "neutral":    {"exaggeration": 0.3, "speed_factor": 1.0, "temperature": 0.8},
    "friendly":   {"exaggeration": 0.5, "speed_factor": 1.05, "temperature": 0.85},
    "angry":      {"exaggeration": 0.85, "speed_factor": 0.9, "temperature": 0.9},
    "sad":        {"exaggeration": 0.6, "speed_factor": 0.85, "temperature": 0.7},
    "fearful":    {"exaggeration": 0.7, "speed_factor": 1.1, "temperature": 0.95},
    "excited":    {"exaggeration": 0.8, "speed_factor": 1.15, "temperature": 0.9},
    "whispering": {"exaggeration": 0.2, "speed_factor": 0.8, "temperature": 0.6},
    "commanding": {"exaggeration": 0.7, "speed_factor": 0.9, "cfg_weight": 0.3},
    "pleading":   {"exaggeration": 0.75, "speed_factor": 0.95, "temperature": 0.85},
}

# Labels shown to the player for old-style category choices
_CHOICE_LABELS = {
    "lore": "Tell me about this place.",
    "quest": "Do you have any work for me?",
    "trade": "What do you have for sale?",
    "combat": "I'm looking for a fight.",
    "search": "Let me take a closer look.",
}


# ── Data classes ─────────────────────────────────────────────────────

@dataclass
class DialogueCondition:
    """A simple flag-based condition.

    Evaluates to True when ``flags[flag] == expected``.
    Missing flags default to False.
    """

    flag: str
    expected: bool = True

    def evaluate(self, flags: Dict[str, bool]) -> bool:
        return flags.get(self.flag, False) == self.expected

    def to_dict(self) -> dict:
        d: dict = {"flag": self.flag}
        if not self.expected:
            d["expected"] = False
        return d

    @classmethod
    def from_dict(cls, data: dict) -> DialogueCondition:
        return cls(
            flag=data["flag"],
            expected=data.get("expected", True),
        )


@dataclass
class DialogueOption:
    """A player response that links to the next dialogue node.

    :param text: What the player says.
    :param next_node: ID of the target :class:`DialogueNode`.
    :param conditions: All must pass for the option to be shown.
    :param set_flags: Flags set when this option is chosen.
    :param priority: Higher values shown first (for ordering).
    """

    text: str
    next_node: str
    conditions: List[DialogueCondition] = field(default_factory=list)
    set_flags: Dict[str, bool] = field(default_factory=dict)
    priority: int = 0

    def is_available(self, flags: Dict[str, bool]) -> bool:
        """True if all conditions pass."""
        return all(c.evaluate(flags) for c in self.conditions)

    def to_dict(self) -> dict:
        d: dict = {"text": self.text, "next_node": self.next_node}
        if self.conditions:
            d["conditions"] = [c.to_dict() for c in self.conditions]
        if self.set_flags:
            d["set_flags"] = self.set_flags
        if self.priority:
            d["priority"] = self.priority
        return d

    @classmethod
    def from_dict(cls, data: dict) -> DialogueOption:
        return cls(
            text=data["text"],
            next_node=data["next_node"],
            conditions=[DialogueCondition.from_dict(c)
                        for c in data.get("conditions", [])],
            set_flags=data.get("set_flags", {}),
            priority=data.get("priority", 0),
        )


@dataclass
class DialogueNode:
    """One beat of an NPC conversation.

    :param node_id: Stable ID (also used as voice manifest key).
    :param text: NPC's spoken line.
    :param options: Player response choices.
    :param set_flags: Flags set when this node is entered.
    :param is_terminal: If True, conversation ends after this node.
    :param category: Voice generation grouping hint.
    :param emotion: Emotion preset name (see :data:`EMOTION_PRESETS`).
    :param voice_overrides: Explicit per-node TTS parameter overrides.
    """

    node_id: str
    text: str
    options: List[DialogueOption] = field(default_factory=list)
    set_flags: Dict[str, bool] = field(default_factory=dict)
    is_terminal: bool = False
    category: str = ""
    emotion: str = ""
    voice_overrides: Dict[str, float] = field(default_factory=dict)

    def get_voice_params(self) -> Dict[str, float]:
        """Merge emotion preset + explicit overrides into voice params.

        Returns a dict of parameter overrides to apply on top of
        the entity's base voice profile.
        """
        params: Dict[str, float] = {}
        if self.emotion and self.emotion in EMOTION_PRESETS:
            params.update(EMOTION_PRESETS[self.emotion])
        params.update(self.voice_overrides)
        return params

    def to_dict(self) -> dict:
        d: dict = {"node_id": self.node_id, "text": self.text}
        if self.options:
            d["options"] = [o.to_dict() for o in self.options]
        if self.set_flags:
            d["set_flags"] = self.set_flags
        if self.is_terminal:
            d["is_terminal"] = True
        if self.category:
            d["category"] = self.category
        if self.emotion:
            d["emotion"] = self.emotion
        if self.voice_overrides:
            d["voice_overrides"] = self.voice_overrides
        return d

    @classmethod
    def from_dict(cls, data: dict) -> DialogueNode:
        return cls(
            node_id=data["node_id"],
            text=data["text"],
            options=[DialogueOption.from_dict(o)
                     for o in data.get("options", [])],
            set_flags=data.get("set_flags", {}),
            is_terminal=data.get("is_terminal", False),
            category=data.get("category", ""),
            emotion=data.get("emotion", ""),
            voice_overrides=data.get("voice_overrides", {}),
        )


@dataclass
class DialogueGraph:
    """Complete branching conversation tree for one NPC.

    :param entry_node: ID of the first node.
    :param nodes: All nodes keyed by ``node_id``.
    """

    entry_node: str
    nodes: Dict[str, DialogueNode] = field(default_factory=dict)

    def get_node(self, node_id: str) -> Optional[DialogueNode]:
        return self.nodes.get(node_id)

    def all_texts(self) -> List[Tuple[str, str]]:
        """Return ``(node_id, text)`` for every node — used by voice generation."""
        return [(nid, n.text) for nid, n in self.nodes.items()]

    # ── Serialization ────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "entry_node": self.entry_node,
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> DialogueGraph:
        nodes = {}
        for nid, ndata in data.get("nodes", {}).items():
            if "node_id" not in ndata:
                ndata["node_id"] = nid
            nodes[nid] = DialogueNode.from_dict(ndata)
        return cls(
            entry_node=data["entry_node"],
            nodes=nodes,
        )

    # ── Backward compatibility ───────────────────────────────────

    @classmethod
    def from_dialogue_lines(
        cls,
        dialogue_lines: Dict[str, List[str]],
    ) -> DialogueGraph:
        """Auto-convert the old flat category format to a hub-and-spoke graph.

        Produces identical behavior to the legacy system: a greeting hub
        with spokes to each category's line chain.
        """
        nodes: Dict[str, DialogueNode] = {}
        hub_options: List[DialogueOption] = []

        for category, lines in dialogue_lines.items():
            if category in ("farewell", "greeting"):
                continue
            if not lines:
                continue

            label = _CHOICE_LABELS.get(category, category.replace("_", " ").title())

            for i, text in enumerate(lines):
                node_id = f"{category}_{i}"
                # Chain to next line or back to hub
                opts: List[DialogueOption] = []
                if i + 1 < len(lines):
                    opts.append(DialogueOption(
                        text="Tell me more.", next_node=f"{category}_{i + 1}"))
                opts.append(DialogueOption(
                    text="Let's talk about something else.", next_node="hub"))
                nodes[node_id] = DialogueNode(
                    node_id=node_id, text=text, category=category,
                    options=opts, emotion="friendly" if i == 0 else "",
                )

            # Hub option to enter this category
            hub_options.append(DialogueOption(text=label, next_node=f"{category}_0"))

        # Farewell terminal — merge all farewells into one node
        farewells = dialogue_lines.get("farewell", ["Farewell, traveler."])
        farewell_text = farewells[0] if farewells else "Farewell, traveler."
        nodes["farewell_0"] = DialogueNode(
            node_id="farewell_0", text=farewell_text,
            category="farewell", is_terminal=True)
        hub_options.append(DialogueOption(text="Goodbye.", next_node="farewell_0"))

        # Greeting as entry — use first greeting only
        greetings = dialogue_lines.get("greeting", ["Greetings, traveler."])
        greeting_text = greetings[0] if greetings else "Greetings, traveler."
        entry_id = "greeting_0"
        nodes[entry_id] = DialogueNode(
            node_id=entry_id, text=greeting_text, category="greeting",
            emotion="friendly", options=list(hub_options),
        )

        # Hub node (return point) — same options as greeting
        nodes["hub"] = DialogueNode(
            node_id="hub", text="What else would you like to know?",
            category="greeting", options=list(hub_options),
        )

        return cls(entry_node=entry_id, nodes=nodes)

    # ── Validation ───────────────────────────────────────────────

    def validate(self) -> List[str]:
        """Return a list of validation errors (empty = valid)."""
        errors: List[str] = []

        if self.entry_node not in self.nodes:
            errors.append(f"Entry node '{self.entry_node}' not found")
            return errors

        for nid, node in self.nodes.items():
            if not node.text.strip():
                errors.append(f"Node '{nid}' has empty text")
            if node.is_terminal and node.options:
                errors.append(
                    f"Terminal node '{nid}' has options (they will be ignored)")
            if not node.is_terminal and not node.options:
                errors.append(
                    f"Node '{nid}' is not terminal but has no options (dead end)")
            for opt in node.options:
                if opt.next_node not in self.nodes:
                    errors.append(
                        f"Node '{nid}' option -> unknown node '{opt.next_node}'")
            if node.emotion and node.emotion not in EMOTION_PRESETS:
                errors.append(
                    f"Node '{nid}' has unknown emotion '{node.emotion}'")

        # Reachability (BFS from entry)
        visited: set[str] = set()
        queue: deque[str] = deque([self.entry_node])
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            node = self.nodes.get(current)
            if node:
                for opt in node.options:
                    if opt.next_node not in visited:
                        queue.append(opt.next_node)

        for nid in set(self.nodes.keys()) - visited:
            errors.append(f"Node '{nid}' is unreachable from entry node")

        return errors

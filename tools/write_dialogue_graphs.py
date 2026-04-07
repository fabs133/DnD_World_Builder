#!/usr/bin/env python3
"""Write branching dialogue graphs for key NPCs and save to map.json."""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def brenna_graph():
    return {
        "entry_node": "greeting_0",
        "nodes": {
            "greeting_0": {
                "node_id": "greeting_0",
                "text": "Well now, fresh faces! Sit down before you fall down.",
                "category": "greeting", "emotion": "friendly",
                "options": [
                    {"text": "What is this place?", "next_node": "lore_0"},
                    {"text": "We're looking for work.", "next_node": "quest_0"},
                    {"text": "What can you tell us about the roads ahead?", "next_node": "quest_1"},
                    {"text": "Just passing through. Goodbye.", "next_node": "farewell_0"},
                ],
            },
            "lore_0": {
                "node_id": "lore_0",
                "text": "Used to be a proper kingdom here. The Crown held it all together.",
                "category": "lore", "emotion": "sad",
                "set_flags": {"heard_kingdom_history": True},
                "options": [
                    {"text": "What happened?", "next_node": "lore_1"},
                    {"text": "Let's talk about something else.", "next_node": "hub"},
                ],
            },
            "lore_1": {
                "node_id": "lore_1",
                "text": "Then that fool Morvain found the artifact. Or it found him. Hard to say which.",
                "category": "lore", "emotion": "sad",
                "set_flags": {"heard_about_morvain": True},
                "options": [
                    {"text": "Tell me more about the blight.", "next_node": "lore_2"},
                    {"text": "Who is this Dark Sovereign?", "next_node": "lore_4",
                     "conditions": [{"flag": "heard_about_blight"}]},
                    {"text": "Let's talk about something else.", "next_node": "hub"},
                ],
            },
            "lore_2": {
                "node_id": "lore_2",
                "text": "The blight started slow. Bad harvests. Animals going wrong. Then the land itself started changing.",
                "category": "lore", "emotion": "fearful",
                "set_flags": {"heard_about_blight": True},
                "options": [
                    {"text": "How bad is it now?", "next_node": "lore_3"},
                    {"text": "Let's talk about something else.", "next_node": "hub"},
                ],
            },
            "lore_3": {
                "node_id": "lore_3",
                "text": "We get refugees from every direction now. Each one tells a worse story than the last.",
                "category": "lore", "emotion": "sad",
                "options": [
                    {"text": "Who's behind all this?", "next_node": "lore_4"},
                    {"text": "Let's talk about something else.", "next_node": "hub"},
                ],
            },
            "lore_4": {
                "node_id": "lore_4",
                "text": "There's a man in the citadel at the center of it all. Calls himself the Dark Sovereign.",
                "category": "lore", "emotion": "fearful",
                "set_flags": {"heard_about_sovereign": True},
                "options": [
                    {"text": "What about the guild master?", "next_node": "lore_5",
                     "conditions": [{"flag": "heard_about_morvain"}]},
                    {"text": "We'll stop him.", "next_node": "quest_brave"},
                    {"text": "Let's talk about something else.", "next_node": "hub"},
                ],
            },
            "lore_5": {
                "node_id": "lore_5",
                "text": "Torven \u2014 that's the guild master \u2014 he's been funneling resources to Morvain for months. Nobody knows why.",
                "category": "lore", "emotion": "angry",
                "set_flags": {"heard_about_torven": True},
                "options": [
                    {"text": "Sounds like we need to pay him a visit.", "next_node": "hub"},
                    {"text": "Let's talk about something else.", "next_node": "hub"},
                ],
            },
            "quest_0": {
                "node_id": "quest_0",
                "text": "You look like the fighting type. Good. We need that.",
                "category": "quest", "emotion": "friendly",
                "options": [
                    {"text": "Where should we start?", "next_node": "quest_1"},
                    {"text": "Tell us about the dangers.", "next_node": "quest_2"},
                    {"text": "Let's talk about something else.", "next_node": "hub"},
                ],
            },
            "quest_1": {
                "node_id": "quest_1",
                "text": "Three roads lead out of Millhaven. North into the forest, east to the swamp, and west up the pass.",
                "category": "quest", "emotion": "neutral",
                "set_flags": {"heard_three_roads": True},
                "options": [
                    {"text": "What's to the north?", "next_node": "quest_2"},
                    {"text": "Any advice before we head out?", "next_node": "quest_3"},
                    {"text": "Let's talk about something else.", "next_node": "hub"},
                ],
            },
            "quest_2": {
                "node_id": "quest_2",
                "text": "Nobody's come back from the north in weeks. Whatever's up there, it's getting worse.",
                "category": "quest", "emotion": "fearful",
                "options": [
                    {"text": "Any advice before we head out?", "next_node": "quest_3"},
                    {"text": "We'll handle it.", "next_node": "quest_brave"},
                    {"text": "Let's talk about something else.", "next_node": "hub"},
                ],
            },
            "quest_3": {
                "node_id": "quest_3",
                "text": "If you're heading out, talk to Durin about gear. And say a prayer at Sister Maren's chapel. Can't hurt.",
                "category": "quest", "emotion": "friendly",
                "set_flags": {"heard_durin_tip": True, "heard_maren_tip": True},
                "options": [
                    {"text": "We'll do that. Thanks.", "next_node": "hub"},
                    {"text": "Time to go. Goodbye.", "next_node": "farewell_0"},
                ],
            },
            "quest_brave": {
                "node_id": "quest_brave",
                "text": "Ale's warm, stew's hot, and the roof doesn't leak. Much. You'll need a proper send-off.",
                "category": "greeting", "emotion": "friendly",
                "options": [
                    {"text": "Anything else we should know?", "next_node": "quest_3"},
                    {"text": "Goodbye for now.", "next_node": "farewell_0"},
                ],
            },
            "hub": {
                "node_id": "hub",
                "text": "What else do you want to know?",
                "category": "greeting", "emotion": "friendly",
                "options": [
                    {"text": "Tell me about this place.", "next_node": "lore_0"},
                    {"text": "We're looking for work.", "next_node": "quest_0"},
                    {"text": "What about the roads ahead?", "next_node": "quest_1"},
                    {"text": "Goodbye.", "next_node": "farewell_0"},
                ],
            },
            "farewell_0": {
                "node_id": "farewell_0",
                "text": "Don't die out there. I hate wasting good ale on memorials.",
                "category": "farewell", "emotion": "friendly",
                "is_terminal": True,
            },
        },
    }


def gerrik_graph():
    return {
        "entry_node": "greeting_0",
        "nodes": {
            "greeting_0": {
                "node_id": "greeting_0",
                "text": "Eh? More strangers. Town's full of 'em these days.",
                "category": "greeting", "emotion": "neutral",
                "options": [
                    {"text": "You seem like you've been here a while.", "next_node": "lore_0"},
                    {"text": "Tell me about the man who caused all this.", "next_node": "lore_1",
                     "conditions": [{"flag": "heard_about_morvain"}]},
                    {"text": "We need directions to the citadel.", "next_node": "lore_5",
                     "conditions": [{"flag": "heard_three_roads"}]},
                    {"text": "Sorry to bother you.", "next_node": "farewell_0"},
                ],
            },
            "lore_0": {
                "node_id": "lore_0",
                "text": "I remember when you could walk to the citadel in a day. Pleasant road, wildflowers.",
                "category": "lore", "emotion": "sad",
                "options": [
                    {"text": "What changed?", "next_node": "lore_1"},
                    {"text": "Let's talk about something else.", "next_node": "hub"},
                ],
            },
            "lore_1": {
                "node_id": "lore_1",
                "text": "Morvain wasn't always mad, you know. He was the king's castellan. Good man. Then he found that crown.",
                "category": "lore", "emotion": "sad",
                "set_flags": {"heard_about_crown": True},
                "options": [
                    {"text": "What happened next?", "next_node": "lore_2"},
                    {"text": "Let's talk about something else.", "next_node": "hub"},
                ],
            },
            "lore_2": {
                "node_id": "lore_2",
                "text": "First sign was the animals. Wolves with bark growing through their fur. Spiders big as dogs.",
                "category": "lore", "emotion": "fearful",
                "options": [
                    {"text": "What about the Crossing?", "next_node": "lore_3"},
                    {"text": "Is anyone mapping the blight?", "next_node": "lore_4"},
                    {"text": "Let's talk about something else.", "next_node": "hub"},
                ],
            },
            "lore_3": {
                "node_id": "lore_3",
                "text": "The Crossing used to be a bridge over the Ashwater. Now the whole riverbed is black.",
                "category": "lore", "emotion": "sad",
                "set_flags": {"heard_about_crossing": True},
                "options": [
                    {"text": "Anyone who might help us navigate?", "next_node": "lore_4"},
                    {"text": "How do we reach the citadel?", "next_node": "lore_5"},
                    {"text": "Let's talk about something else.", "next_node": "hub"},
                ],
            },
            "lore_4": {
                "node_id": "lore_4",
                "text": "There's a hermit up on the mountain pass. Harlen. He was the king's cartographer. Might still have maps.",
                "category": "lore", "emotion": "neutral",
                "set_flags": {"heard_about_harlen": True},
                "options": [
                    {"text": "How do we reach the citadel?", "next_node": "lore_5"},
                    {"text": "Thanks, old timer.", "next_node": "farewell_0"},
                ],
            },
            "lore_5": {
                "node_id": "lore_5",
                "text": "If you're going to the citadel, go through the Crossing. It's the only direct route. Everything else is a longer way around.",
                "category": "lore", "emotion": "commanding",
                "set_flags": {"heard_citadel_route": True},
                "options": [
                    {"text": "We'll find a way.", "next_node": "farewell_1"},
                    {"text": "Any other advice?", "next_node": "hub"},
                ],
            },
            "hub": {
                "node_id": "hub",
                "text": "You've got that look. The hero look. I've seen it before.",
                "category": "greeting", "emotion": "neutral",
                "options": [
                    {"text": "Tell me about the old days.", "next_node": "lore_0"},
                    {"text": "What do you know about Morvain?", "next_node": "lore_1"},
                    {"text": "How do we get to the citadel?", "next_node": "lore_5"},
                    {"text": "Goodbye.", "next_node": "farewell_0"},
                ],
            },
            "farewell_0": {
                "node_id": "farewell_0",
                "text": "I'll be here. Not like I've got anywhere else to go.",
                "category": "farewell", "emotion": "sad",
                "is_terminal": True,
            },
            "farewell_1": {
                "node_id": "farewell_1",
                "text": "Watch for the green glow. When you see that, you're in the thick of it.",
                "category": "farewell", "emotion": "fearful",
                "is_terminal": True,
            },
        },
    }


def durin_graph():
    return {
        "entry_node": "greeting_0",
        "nodes": {
            "greeting_0": {
                "node_id": "greeting_0",
                "text": "Speak up or move on. I've got orders to fill.",
                "category": "greeting", "emotion": "angry",
                "options": [
                    {"text": "We need weapons.", "next_node": "trade_0"},
                    {"text": "We heard you might have a job for us.", "next_node": "quest_0",
                     "conditions": [{"flag": "heard_durin_tip"}]},
                    {"text": "Tell us about the blight's effect on metalwork.", "next_node": "lore_1",
                     "conditions": [{"flag": "heard_about_blight"}]},
                    {"text": "What can you tell us about the situation?", "next_node": "lore_0"},
                    {"text": "Never mind.", "next_node": "farewell_0"},
                ],
            },
            "trade_0": {
                "node_id": "trade_0",
                "text": "What do you need? I've got swords, shields, and stubbornness. All three are sturdy.",
                "category": "trade", "emotion": "neutral",
                "options": [
                    {"text": "Got anything special?", "next_node": "quest_0"},
                    {"text": "Just browsing.", "next_node": "hub"},
                ],
            },
            "quest_0": {
                "node_id": "quest_0",
                "text": "My steel's good, but it won't cut through the blight.",
                "category": "quest", "emotion": "angry",
                "options": [
                    {"text": "What would?", "next_node": "quest_1"},
                    {"text": "Let's talk about something else.", "next_node": "hub"},
                ],
            },
            "quest_1": {
                "node_id": "quest_1",
                "text": "There's an old forge in the crystal caves to the east. Dwarven make. Real dwarven make.",
                "category": "quest", "emotion": "excited",
                "set_flags": {"heard_star_iron_quest": True},
                "options": [
                    {"text": "What do you need from there?", "next_node": "quest_2"},
                    {"text": "What's in the caves?", "next_node": "quest_3"},
                ],
            },
            "quest_2": {
                "node_id": "quest_2",
                "text": "Bring me star-iron from that forge and I'll make you something that'll actually hurt whatever's in that citadel.",
                "category": "quest", "emotion": "commanding",
                "set_flags": {"star_iron_quest_offered": True},
                "options": [
                    {"text": "We'll get it.", "next_node": "quest_accept",
                     "set_flags": {"star_iron_quest_accepted": True}},
                    {"text": "What's in the caves?", "next_node": "quest_3"},
                    {"text": "We'll think about it.", "next_node": "hub"},
                ],
            },
            "quest_3": {
                "node_id": "quest_3",
                "text": "Fair warning \u2014 the caves are crawling with things that used to be rocks.",
                "category": "quest", "emotion": "fearful",
                "options": [
                    {"text": "We'll handle it. Deal.", "next_node": "quest_accept",
                     "set_flags": {"star_iron_quest_accepted": True}},
                    {"text": "We need to prepare first.", "next_node": "hub"},
                ],
            },
            "quest_accept": {
                "node_id": "quest_accept",
                "text": "Another batch of would-be heroes, eh? At least you're armed.",
                "category": "greeting", "emotion": "friendly",
                "options": [
                    {"text": "Goodbye.", "next_node": "farewell_1"},
                ],
            },
            "lore_0": {
                "node_id": "lore_0",
                "text": "I've been sharpening blades for soldiers, guards, adventurers. None of them come back for a second sharpening.",
                "category": "lore", "emotion": "sad",
                "options": [
                    {"text": "The metal's been affected too?", "next_node": "lore_1"},
                    {"text": "Let's talk about something else.", "next_node": "hub"},
                ],
            },
            "lore_1": {
                "node_id": "lore_1",
                "text": "The metal's been acting strange. Blades rust overnight. Iron weeps in the forge.",
                "category": "lore", "emotion": "fearful",
                "options": [
                    {"text": "What's causing it?", "next_node": "lore_2"},
                    {"text": "Let's talk about something else.", "next_node": "hub"},
                ],
            },
            "lore_2": {
                "node_id": "lore_2",
                "text": "Whatever that artifact is doing, it's poisoning everything. Even the earth.",
                "category": "lore", "emotion": "angry",
                "set_flags": {"heard_earth_poisoned": True},
                "options": [
                    {"text": "Is there anything that resists it?", "next_node": "quest_0"},
                    {"text": "Let's talk about something else.", "next_node": "hub"},
                ],
            },
            "hub": {
                "node_id": "hub",
                "text": "Speak up or move on. I've got orders to fill.",
                "category": "greeting", "emotion": "angry",
                "options": [
                    {"text": "Show me your wares.", "next_node": "trade_0"},
                    {"text": "About that forge in the caves...", "next_node": "quest_1",
                     "conditions": [{"flag": "heard_star_iron_quest"}]},
                    {"text": "Tell us about the blight.", "next_node": "lore_0"},
                    {"text": "Goodbye.", "next_node": "farewell_0"},
                ],
            },
            "farewell_0": {
                "node_id": "farewell_0",
                "text": "Keep your blade dry and your shield up.",
                "category": "farewell", "emotion": "neutral",
                "is_terminal": True,
            },
            "farewell_1": {
                "node_id": "farewell_1",
                "text": "Don't come back dead. I've got your order to finish.",
                "category": "farewell", "emotion": "friendly",
                "is_terminal": True,
            },
        },
    }


def main():
    from models.dialogue.dialogue_graph import DialogueGraph

    graphs = {
        "Brenna the Barkeep": brenna_graph(),
        "Old Gerrik": gerrik_graph(),
        "Durin the Smith": durin_graph(),
    }

    # Validate
    all_valid = True
    for name, gdata in graphs.items():
        g = DialogueGraph.from_dict(gdata)
        errors = g.validate()
        if errors:
            print(f"FAIL {name}:")
            for e in errors:
                print(f"  - {e}")
            all_valid = False
        else:
            emotes = sum(1 for n in g.nodes.values() if n.emotion)
            flags = set()
            for n in g.nodes.values():
                flags.update(n.set_flags.keys())
                for o in n.options:
                    flags.update(o.set_flags.keys())
                    for c in o.conditions:
                        flags.add(c.flag)
            print(f"OK   {name}: {len(g.nodes)} nodes, {emotes} with emotion, {len(flags)} flags")

    if not all_valid:
        print("\nFix errors before saving!")
        return

    # Save to map.json
    map_path = Path("workspace/shattered_realms/map.json")
    data = json.loads(map_path.read_text(encoding="utf-8"))

    saved = 0
    for tile in data["tiles"]:
        for e in tile.get("entities", []):
            name = e.get("name", "")
            if name in graphs:
                e["dialogue_graph"] = graphs[name]
                saved += 1
                print(f"  Saved graph for {name}")

    map_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n{saved} graphs saved to map.json")


if __name__ == "__main__":
    main()

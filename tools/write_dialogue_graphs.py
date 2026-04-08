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


def thessa_graph():
    return {
        "entry_node": "greeting_0",
        "nodes": {
            "greeting_0": {
                "node_id": "greeting_0",
                "text": "State your business. We don't get travelers anymore \u2014 just refugees and fools.",
                "category": "greeting", "emotion": "commanding",
                "options": [
                    {"text": "What's the situation here?", "next_node": "lore_0"},
                    {"text": "We heard you lost a patrol.", "next_node": "quest_0"},
                    {"text": "We're armed and ready to help.", "next_node": "greeting_armed"},
                    {"text": "Just passing through.", "next_node": "farewell_0"},
                ],
            },
            "greeting_armed": {
                "node_id": "greeting_armed",
                "text": "You're armed. Good. We could use armed.",
                "category": "greeting", "emotion": "neutral",
                "options": [
                    {"text": "What's the situation?", "next_node": "lore_0"},
                    {"text": "Do you have work for us?", "next_node": "quest_0"},
                    {"text": "We'll be on our way.", "next_node": "farewell_0"},
                ],
            },
            "lore_0": {
                "node_id": "lore_0",
                "text": "I've got twelve guards left. Twelve, for a town of three hundred.",
                "category": "lore", "emotion": "angry",
                "set_flags": {"heard_guard_shortage": True},
                "options": [
                    {"text": "What's been attacking?", "next_node": "lore_1"},
                    {"text": "That's dire.", "next_node": "hub"},
                ],
            },
            "lore_1": {
                "node_id": "lore_1",
                "text": "Things come out of the dark now. Twisted things. We lost two guards last week.",
                "category": "lore", "emotion": "fearful",
                "options": [
                    {"text": "Is there no help coming?", "next_node": "lore_2"},
                    {"text": "Let's talk about something else.", "next_node": "hub"},
                ],
            },
            "lore_2": {
                "node_id": "lore_2",
                "text": "The kingdom's gone. There's no reinforcements coming. This is it.",
                "category": "lore", "emotion": "sad",
                "options": [
                    {"text": "We'll help.", "next_node": "quest_0"},
                    {"text": "Let's talk about something else.", "next_node": "hub"},
                ],
            },
            "quest_0": {
                "node_id": "quest_0",
                "text": "I sent a patrol into the swamp three days ago. Five soldiers. None returned.",
                "category": "quest", "emotion": "sad",
                "set_flags": {"patrol_quest_offered": True},
                "options": [
                    {"text": "Tell us more.", "next_node": "quest_1"},
                    {"text": "Let's talk about something else.", "next_node": "hub"},
                ],
            },
            "quest_1": {
                "node_id": "quest_1",
                "text": "I can't spare anyone else. But if you're heading that way...",
                "category": "quest", "emotion": "neutral",
                "options": [
                    {"text": "What do you need?", "next_node": "quest_2"},
                ],
            },
            "quest_2": {
                "node_id": "quest_2",
                "text": "Find my soldiers. If they're alive, bring them back. If not... bring back their insignias. Their families deserve to know.",
                "category": "quest", "emotion": "pleading",
                "options": [
                    {"text": "We'll find them.", "next_node": "quest_accept",
                     "set_flags": {"patrol_quest_accepted": True}},
                    {"text": "The swamp sounds dangerous. What should we expect?", "next_node": "quest_3"},
                    {"text": "We need to prepare first.", "next_node": "hub"},
                ],
            },
            "quest_3": {
                "node_id": "quest_3",
                "text": "The swamp's always been bad. Now it's worse. The dead don't stay down, and the water itself will try to pull you under. Stick to solid ground where you can find it.",
                "category": "quest", "emotion": "commanding",
                "set_flags": {"heard_swamp_dangers": True},
                "options": [
                    {"text": "We'll handle it.", "next_node": "quest_accept",
                     "set_flags": {"patrol_quest_accepted": True}},
                    {"text": "We need more time.", "next_node": "hub"},
                ],
            },
            "quest_accept": {
                "node_id": "quest_accept",
                "text": "Good. Their names are Holt, Vance, Asha, Bren, and Torma. Remember those names.",
                "category": "quest", "emotion": "neutral",
                "options": [
                    {"text": "We won't forget.", "next_node": "farewell_1"},
                ],
            },
            "hub": {
                "node_id": "hub",
                "text": "Anything else?",
                "category": "greeting", "emotion": "commanding",
                "options": [
                    {"text": "Tell me about the town defenses.", "next_node": "lore_0"},
                    {"text": "About the patrol...", "next_node": "quest_0",
                     "conditions": [{"flag": "patrol_quest_accepted", "expected": False}]},
                    {"text": "Goodbye.", "next_node": "farewell_0"},
                ],
            },
            "farewell_0": {
                "node_id": "farewell_0",
                "text": "Stay sharp out there. And if you see my patrol... do right by them.",
                "category": "farewell", "emotion": "neutral",
                "is_terminal": True,
            },
            "farewell_1": {
                "node_id": "farewell_1",
                "text": "Bring them home, soldier. That's an order.",
                "category": "farewell", "emotion": "commanding",
                "is_terminal": True,
            },
        },
    }


def harlen_graph():
    return {
        "entry_node": "greeting_0",
        "nodes": {
            "greeting_0": {
                "node_id": "greeting_0",
                "text": "Visitors! Actual visitors! Come in, come in \u2014 mind the maps, they're drying.",
                "category": "greeting", "emotion": "excited",
                "options": [
                    {"text": "Gerrik sent us.", "next_node": "greeting_referred",
                     "conditions": [{"flag": "heard_about_harlen"}]},
                    {"text": "We need information.", "next_node": "hub"},
                    {"text": "Interesting place you have here.", "next_node": "lore_0"},
                    {"text": "Goodbye.", "next_node": "farewell_0"},
                ],
            },
            "greeting_referred": {
                "node_id": "greeting_referred",
                "text": "Gerrik! Old Gerrik's still alive? Ha! I owe that man a bottle of wine. Well, what do you need? Maps? Routes? I've got it all.",
                "category": "greeting", "emotion": "excited",
                "options": [
                    {"text": "We need routes to the citadel.", "next_node": "lore_3"},
                    {"text": "Tell us about the blight pattern.", "next_node": "quest_0"},
                    {"text": "Let's start from the beginning.", "next_node": "lore_0"},
                ],
            },
            "lore_0": {
                "node_id": "lore_0",
                "text": "I was the king's cartographer. I mapped every road, every ruin, every forgotten path.",
                "category": "lore", "emotion": "friendly",
                "options": [
                    {"text": "What happened?", "next_node": "lore_1"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "lore_1": {
                "node_id": "lore_1",
                "text": "When the Shattering happened, I came up here. Best vantage point in the realm.",
                "category": "lore", "emotion": "sad",
                "options": [
                    {"text": "What have you seen?", "next_node": "lore_2"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "lore_2": {
                "node_id": "lore_2",
                "text": "The blight follows a pattern. It's not random. Someone \u2014 or something \u2014 is directing it.",
                "category": "lore", "emotion": "fearful",
                "options": [
                    {"text": "A pattern?", "next_node": "quest_0"},
                    {"text": "What about the citadel approaches?", "next_node": "lore_3"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "quest_0": {
                "node_id": "quest_0",
                "text": "I've mapped the blight's spread from up here. It's accelerating. Look \u2014 the corruption radiates from the citadel in a spiral. Not a circle. A spiral.",
                "category": "quest", "emotion": "excited",
                "set_flags": {"heard_ley_lines": True},
                "options": [
                    {"text": "What does that mean?", "next_node": "quest_1"},
                ],
            },
            "quest_1": {
                "node_id": "quest_1",
                "text": "That means it's following the old ley lines. The kingdom was built on them.",
                "category": "quest", "emotion": "excited",
                "options": [
                    {"text": "Can we use that?", "next_node": "quest_2"},
                ],
            },
            "quest_2": {
                "node_id": "quest_2",
                "text": "I need you to check something. At the summit, there's a standing stone. A ley line marker. If the stone is corrupted, the ley line is too. If it's intact... there might be a way to disrupt the spiral.",
                "category": "quest", "emotion": "commanding",
                "set_flags": {"ley_line_quest_offered": True},
                "options": [
                    {"text": "We'll check it.", "next_node": "quest_accept",
                     "set_flags": {"ley_line_quest_accepted": True}},
                    {"text": "What about the citadel?", "next_node": "lore_3"},
                    {"text": "We need time.", "next_node": "hub"},
                ],
            },
            "quest_accept": {
                "node_id": "quest_accept",
                "text": "Excellent! Take notes on what you see \u2014 color of the stone, any cracks, whether it hums. Details matter. They always matter.",
                "category": "quest", "emotion": "excited",
                "options": [
                    {"text": "What about citadel routes?", "next_node": "lore_3"},
                    {"text": "We'll report back.", "next_node": "farewell_1"},
                ],
            },
            "lore_3": {
                "node_id": "lore_3",
                "text": "The citadel has four approaches. The Crossing is direct but heavily guarded.",
                "category": "lore", "emotion": "neutral",
                "set_flags": {"heard_citadel_approaches": True},
                "options": [
                    {"text": "Other routes?", "next_node": "lore_4"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "lore_4": {
                "node_id": "lore_4",
                "text": "Through the forest is longer. Through the sands is dangerous. But through the pass above the Crossing... that's the route nobody watches.",
                "category": "lore", "emotion": "whispering",
                "set_flags": {"heard_secret_pass": True},
                "options": [
                    {"text": "What about Morvain himself?", "next_node": "lore_5"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "lore_5": {
                "node_id": "lore_5",
                "text": "Morvain was brilliant before the Crown took him. A tactician. If any of that mind remains, the citadel will be trapped.",
                "category": "lore", "emotion": "fearful",
                "set_flags": {"heard_morvain_tactician": True},
                "options": [
                    {"text": "We'll be careful.", "next_node": "farewell_1"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "hub": {
                "node_id": "hub",
                "text": "I've been expecting someone. Well, hoping. The expecting part is new. What else do you need?",
                "category": "greeting", "emotion": "friendly",
                "options": [
                    {"text": "The blight pattern.", "next_node": "quest_0",
                     "conditions": [{"flag": "heard_ley_lines", "expected": False}]},
                    {"text": "Citadel approaches.", "next_node": "lore_3"},
                    {"text": "Tell me about yourself.", "next_node": "lore_0"},
                    {"text": "Goodbye.", "next_node": "farewell_0"},
                ],
            },
            "farewell_0": {
                "node_id": "farewell_0",
                "text": "Take this map. It's not complete, but it's better than nothing.",
                "category": "farewell", "emotion": "friendly",
                "is_terminal": True,
            },
            "farewell_1": {
                "node_id": "farewell_1",
                "text": "If you reach the citadel... well, I'll watch from up here. And I'll update the map accordingly.",
                "category": "farewell", "emotion": "sad",
                "is_terminal": True,
            },
        },
    }


def sigrid_graph():
    return {
        "entry_node": "greeting_0",
        "nodes": {
            "greeting_0": {
                "node_id": "greeting_0",
                "text": "You're either very brave or very lost. Either way, warm yourself by the fire.",
                "category": "greeting", "emotion": "neutral",
                "options": [
                    {"text": "Who are you?", "next_node": "lore_sigrid"},
                    {"text": "What happened here?", "next_node": "lore_0"},
                    {"text": "We're looking for dawn lotus.", "next_node": "lore_lotus",
                     "conditions": [{"flag": "heard_maren_tip"}]},
                    {"text": "Goodbye.", "next_node": "farewell_0"},
                ],
            },
            "lore_sigrid": {
                "node_id": "lore_sigrid",
                "text": "I am Sigrid. Last of the Frostborn warband. The ice took the rest.",
                "category": "lore", "emotion": "sad",
                "options": [
                    {"text": "What brought you here?", "next_node": "quest_0"},
                    {"text": "What happened to your warband?", "next_node": "lore_1"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "lore_0": {
                "node_id": "lore_0",
                "text": "This winter isn't natural. It started the same time as the blight everywhere else.",
                "category": "lore", "emotion": "angry",
                "options": [
                    {"text": "The wraiths?", "next_node": "lore_1"},
                    {"text": "What's causing it?", "next_node": "quest_0"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "lore_1": {
                "node_id": "lore_1",
                "text": "The wraiths are people. Travelers, soldiers, my own warriors. The cold takes you and your spirit stays, frozen in the moment of death.",
                "category": "lore", "emotion": "sad",
                "options": [
                    {"text": "Can they be saved?", "next_node": "lore_1b"},
                    {"text": "What's under the lake?", "next_node": "quest_0"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "lore_1b": {
                "node_id": "lore_1b",
                "text": "Saved? No. Not saved. But they can be given rest. A clean death is all I can offer them now. It's more than they have.",
                "category": "lore", "emotion": "sad",
                "options": [
                    {"text": "Tell me about the lake.", "next_node": "quest_0"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "quest_0": {
                "node_id": "quest_0",
                "text": "My warband came to find the source of the winter. We found it. Under the lake. Something sleeps beneath the ice. Old. Powerful. The cold radiates from it.",
                "category": "quest", "emotion": "commanding",
                "set_flags": {"heard_frost_wyrm": True},
                "options": [
                    {"text": "What is it?", "next_node": "quest_1"},
                    {"text": "Can we stop it?", "next_node": "quest_2"},
                ],
            },
            "quest_1": {
                "node_id": "quest_1",
                "text": "Under the lake there's a creature \u2014 a frost wyrm, I think. Bound by the Crown's power. Kill it or free it, I don't care. Just stop this endless winter.",
                "category": "quest", "emotion": "angry",
                "set_flags": {"wyrm_quest_offered": True},
                "options": [
                    {"text": "We'll help.", "next_node": "quest_accept",
                     "set_flags": {"wyrm_quest_accepted": True, "sigrid_companion": True}},
                    {"text": "What's between us and it?", "next_node": "quest_2"},
                    {"text": "We need time.", "next_node": "hub"},
                ],
            },
            "quest_2": {
                "node_id": "quest_2",
                "text": "I can't fight it alone. But if you help me reach the lake's heart... there are wraiths between here and there. They were my warriors once. I'll fight beside you. I owe them a clean death.",
                "category": "quest", "emotion": "pleading",
                "set_flags": {"wyrm_quest_offered": True},
                "options": [
                    {"text": "You have our blades.", "next_node": "quest_accept",
                     "set_flags": {"wyrm_quest_accepted": True, "sigrid_companion": True}},
                    {"text": "We need to prepare.", "next_node": "hub"},
                ],
            },
            "quest_accept": {
                "node_id": "quest_accept",
                "text": "Then we fight together. I won't promise you warmth or comfort. But I will promise you my axe and my shield until this is done.",
                "category": "quest", "emotion": "commanding",
                "options": [
                    {"text": "Tell me about the dawn lotus.", "next_node": "lore_lotus",
                     "conditions": [{"flag": "heard_maren_tip"}]},
                    {"text": "Let's move.", "next_node": "farewell_1"},
                ],
            },
            "lore_lotus": {
                "node_id": "lore_lotus",
                "text": "The dawn lotus flowers by the lake shore \u2014 they're protected by the wyrm's magic. Sacred, maybe. Take them if you need them.",
                "category": "lore", "emotion": "neutral",
                "set_flags": {"heard_dawn_lotus_location": True},
                "options": [
                    {"text": "Good to know.", "next_node": "hub"},
                    {"text": "We're ready to move.", "next_node": "farewell_1"},
                ],
            },
            "hub": {
                "node_id": "hub",
                "text": "The cold is patient. We shouldn't be. What do you need?",
                "category": "greeting", "emotion": "neutral",
                "options": [
                    {"text": "The frost wyrm.", "next_node": "quest_0",
                     "conditions": [{"flag": "heard_frost_wyrm", "expected": False}]},
                    {"text": "The wraiths.", "next_node": "lore_1"},
                    {"text": "Dawn lotus.", "next_node": "lore_lotus",
                     "conditions": [{"flag": "heard_maren_tip"}]},
                    {"text": "Let's go.", "next_node": "farewell_1",
                     "conditions": [{"flag": "wyrm_quest_accepted"}]},
                    {"text": "Goodbye.", "next_node": "farewell_0"},
                ],
            },
            "farewell_0": {
                "node_id": "farewell_0",
                "text": "Rest. Eat. We move at first light \u2014 such as it is.",
                "category": "farewell", "emotion": "neutral",
                "is_terminal": True,
            },
            "farewell_1": {
                "node_id": "farewell_1",
                "text": "Stay close. Stay warm. And if a wraith speaks your name, don't answer.",
                "category": "farewell", "emotion": "fearful",
                "is_terminal": True,
            },
        },
    }


def zahara_graph():
    return {
        "entry_node": "greeting_0",
        "nodes": {
            "greeting_0": {
                "node_id": "greeting_0",
                "text": "You survived the Glass Fields. That earns you water and shade.",
                "category": "greeting", "emotion": "friendly",
                "options": [
                    {"text": "Tell us about this place.", "next_node": "lore_0"},
                    {"text": "We need to reach the citadel.", "next_node": "quest_0"},
                    {"text": "What do you have for trade?", "next_node": "trade_0"},
                    {"text": "Thank you. Goodbye.", "next_node": "farewell_0"},
                ],
            },
            "lore_0": {
                "node_id": "lore_0",
                "text": "This was grassland once. My grandmother remembers green fields, cattle, rain.",
                "category": "lore", "emotion": "sad",
                "set_flags": {"heard_sandwalker_history": True},
                "options": [
                    {"text": "What happened?", "next_node": "lore_1"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "lore_1": {
                "node_id": "lore_1",
                "text": "The heat came in a single day. A wave of fire from the citadel. Everything burned.",
                "category": "lore", "emotion": "angry",
                "options": [
                    {"text": "How did you survive?", "next_node": "lore_2"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "lore_2": {
                "node_id": "lore_2",
                "text": "We adapted. The Sandwalkers always adapt. But this... this we cannot outlast.",
                "category": "lore", "emotion": "sad",
                "options": [
                    {"text": "The standing stones?", "next_node": "lore_3"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "lore_3": {
                "node_id": "lore_3",
                "text": "The standing stones at this oasis are older than the kingdom. They protect us. Without them, even this water would boil.",
                "category": "lore", "emotion": "neutral",
                "set_flags": {"heard_oasis_stones": True},
                "options": [
                    {"text": "Interesting.", "next_node": "hub"},
                    {"text": "We need to move on.", "next_node": "farewell_0"},
                ],
            },
            "quest_0": {
                "node_id": "quest_0",
                "text": "Emberlord Azrak guards the eastern approach to the citadel. He was not always a monster. Once, he was a guardian spirit of the earth. The Crown corrupted him. Turned the guardian into a weapon.",
                "category": "quest", "emotion": "sad",
                "options": [
                    {"text": "Is there a way past him?", "next_node": "quest_1"},
                    {"text": "Can he be saved?", "next_node": "quest_1b"},
                ],
            },
            "quest_1": {
                "node_id": "quest_1",
                "text": "To reach the citadel from here, you must go through him. There is no other path. But I know his weakness.",
                "category": "quest", "emotion": "commanding",
                "options": [
                    {"text": "Tell us.", "next_node": "quest_2"},
                ],
            },
            "quest_1b": {
                "node_id": "quest_1b",
                "text": "The spirit within is long gone. What remains is rage and fire, shaped by the Crown's will. You cannot reason with a wildfire.",
                "category": "quest", "emotion": "sad",
                "options": [
                    {"text": "Then how do we fight him?", "next_node": "quest_2"},
                ],
            },
            "quest_2": {
                "node_id": "quest_2",
                "text": "The obsidian platform he stands on \u2014 it channels the Crown's power to him. Destroy the platform's anchor stones first. Without them, he is just fire. Still dangerous, but mortal.",
                "category": "quest", "emotion": "commanding",
                "set_flags": {"heard_emberlord_weakness": True, "heard_anchor_stones": True},
                "options": [
                    {"text": "How many anchor stones?", "next_node": "quest_3"},
                    {"text": "We'll do it.", "next_node": "farewell_1"},
                ],
            },
            "quest_3": {
                "node_id": "quest_3",
                "text": "Four stones, one at each corner of the platform. They glow green \u2014 you cannot miss them. But he will protect them. Strike fast, and do not stand still. Fire follows movement it can predict.",
                "category": "quest", "emotion": "whispering",
                "options": [
                    {"text": "Thank you.", "next_node": "farewell_1"},
                    {"text": "Anything else?", "next_node": "hub"},
                ],
            },
            "trade_0": {
                "node_id": "trade_0",
                "text": "Desert spices, waterskins, and fire resistance salve. You'll want all three.",
                "category": "trade", "emotion": "friendly",
                "options": [
                    {"text": "Good to know.", "next_node": "hub"},
                    {"text": "We need to go.", "next_node": "farewell_0"},
                ],
            },
            "hub": {
                "node_id": "hub",
                "text": "The Sandwalkers welcome those the desert does not swallow. What else do you need?",
                "category": "greeting", "emotion": "friendly",
                "options": [
                    {"text": "The Emberlord.", "next_node": "quest_0"},
                    {"text": "This place.", "next_node": "lore_0"},
                    {"text": "Trading.", "next_node": "trade_0"},
                    {"text": "Goodbye.", "next_node": "farewell_0"},
                ],
            },
            "farewell_0": {
                "node_id": "farewell_0",
                "text": "May the wind be at your back and the sand beneath your feet be cool.",
                "category": "farewell", "emotion": "friendly",
                "is_terminal": True,
            },
            "farewell_1": {
                "node_id": "farewell_1",
                "text": "If you kill the Emberlord... come back. I want to see green again.",
                "category": "farewell", "emotion": "pleading",
                "is_terminal": True,
            },
        },
    }


def king_aldric_graph():
    return {
        "entry_node": "greeting_0",
        "nodes": {
            "greeting_0": {
                "node_id": "greeting_0",
                "text": "At last... someone with the strength to listen.",
                "category": "greeting", "emotion": "whispering",
                "options": [
                    {"text": "Who are you?", "next_node": "lore_identity"},
                    {"text": "We know about the Crown.", "next_node": "quest_0",
                     "conditions": [{"flag": "heard_about_crown"}]},
                    {"text": "What is this place?", "next_node": "lore_chapel"},
                    {"text": "We should go.", "next_node": "farewell_0"},
                ],
            },
            "lore_identity": {
                "node_id": "lore_identity",
                "text": "I am \u2014 was \u2014 Aldric. Third of my name. This was my castle. My kingdom.",
                "category": "lore", "emotion": "sad",
                "options": [
                    {"text": "What happened to you?", "next_node": "lore_0"},
                    {"text": "Tell us about the Crown.", "next_node": "lore_1"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "lore_chapel": {
                "node_id": "lore_chapel",
                "text": "This was the war chapel of my ancestors. The wards carved into these walls predate even my bloodline. They held against the Crown's corruption. Even Morvain cannot reach in here.",
                "category": "lore", "emotion": "neutral",
                "options": [
                    {"text": "Tell us about yourself.", "next_node": "lore_identity"},
                    {"text": "Tell us about the Crown.", "next_node": "lore_1"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "lore_0": {
                "node_id": "lore_0",
                "text": "My ancestors sealed the Crown in the deepest vault for good reason.",
                "category": "lore", "emotion": "commanding",
                "options": [
                    {"text": "Why?", "next_node": "lore_1"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "lore_1": {
                "node_id": "lore_1",
                "text": "It is not evil. Not exactly. It is a mirror that shows you the worst version of yourself \u2014 and makes it real.",
                "category": "lore", "emotion": "fearful",
                "set_flags": {"heard_crown_nature": True},
                "options": [
                    {"text": "What about Morvain?", "next_node": "lore_2"},
                    {"text": "How do we destroy it?", "next_node": "quest_0"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "lore_2": {
                "node_id": "lore_2",
                "text": "Morvain was my most trusted advisor. Loyal, brilliant, dedicated.",
                "category": "lore", "emotion": "sad",
                "options": [
                    {"text": "What changed?", "next_node": "lore_3"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "lore_3": {
                "node_id": "lore_3",
                "text": "The Crown showed him a version of himself with power. With control. With everything he secretly wanted. He couldn't resist. Nobody can, not for long. That's why it must be broken.",
                "category": "lore", "emotion": "pleading",
                "set_flags": {"heard_morvain_truth": True},
                "options": [
                    {"text": "How do we break it?", "next_node": "quest_0"},
                    {"text": "What happens after?", "next_node": "lore_4"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "lore_4": {
                "node_id": "lore_4",
                "text": "When the Crown breaks, the blight will recede. The dead will rest. The ice will thaw.",
                "category": "lore", "emotion": "excited",
                "options": [
                    {"text": "And Morvain?", "next_node": "lore_5"},
                    {"text": "How do we break it?", "next_node": "quest_0"},
                ],
            },
            "lore_5": {
                "node_id": "lore_5",
                "text": "And Morvain... Morvain will remember what he was. That may be the cruelest part.",
                "category": "lore", "emotion": "sad",
                "options": [
                    {"text": "Tell us how.", "next_node": "quest_0"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "quest_0": {
                "node_id": "quest_0",
                "text": "The Crown of Fractures cannot be destroyed by sword or spell alone.",
                "category": "quest", "emotion": "commanding",
                "options": [
                    {"text": "Then how?", "next_node": "quest_1"},
                ],
            },
            "quest_1": {
                "node_id": "quest_1",
                "text": "It must be removed from Morvain's brow while he lives. Only then, when it has no host...",
                "category": "quest", "emotion": "whispering",
                "options": [
                    {"text": "Go on.", "next_node": "quest_2"},
                ],
            },
            "quest_2": {
                "node_id": "quest_2",
                "text": "Strike it against the throne. The throne is bonded to the bloodline. My bloodline. The impact will shatter the Crown. And the blight... will end.",
                "category": "quest", "emotion": "commanding",
                "set_flags": {"crown_destruction_method": True, "heard_throne_bloodline": True},
                "options": [
                    {"text": "How do we get it off him?", "next_node": "quest_3"},
                    {"text": "We understand.", "next_node": "farewell_1"},
                ],
            },
            "quest_3": {
                "node_id": "quest_3",
                "text": "But Morvain will fight to keep it. The Crown won't let him surrender. You must weaken him until the Crown's grip falters. Look for the moment of doubt in his eyes.",
                "category": "quest", "emotion": "pleading",
                "options": [
                    {"text": "We'll find that moment.", "next_node": "farewell_1"},
                    {"text": "Is there anything else?", "next_node": "quest_4"},
                ],
            },
            "quest_4": {
                "node_id": "quest_4",
                "text": "The sword in the alcove. It was mine in life. It still carries the blessing of my bloodline. Against the Crown's servants, it will burn true. Take it.",
                "category": "quest", "emotion": "commanding",
                "options": [
                    {"text": "Thank you, your majesty.", "next_node": "farewell_1"},
                ],
            },
            "hub": {
                "node_id": "hub",
                "text": "Time grows short. The Crown feeds on delay. What else must you know?",
                "category": "greeting", "emotion": "commanding",
                "options": [
                    {"text": "The Crown's nature.", "next_node": "lore_1"},
                    {"text": "Morvain.", "next_node": "lore_2"},
                    {"text": "How to destroy it.", "next_node": "quest_0"},
                    {"text": "We're ready.", "next_node": "farewell_1"},
                ],
            },
            "farewell_0": {
                "node_id": "farewell_0",
                "text": "I cannot leave this chapel. The wards hold me here as much as they protect you.",
                "category": "farewell", "emotion": "sad",
                "is_terminal": True,
            },
            "farewell_1": {
                "node_id": "farewell_1",
                "text": "End this. Not for me \u2014 for him. For everyone the Crown has consumed.",
                "category": "farewell", "emotion": "pleading",
                "is_terminal": True,
            },
        },
    }


def elara_graph():
    return {
        "entry_node": "greeting_0",
        "nodes": {
            "greeting_0": {
                "node_id": "greeting_0",
                "text": "The forest whispers of your coming. Not all of it is pleased.",
                "category": "greeting", "emotion": "neutral",
                "options": [
                    {"text": "Who are you?", "next_node": "lore_self"},
                    {"text": "What's happening to the forest?", "next_node": "lore_0"},
                    {"text": "We need potions.", "next_node": "quest_0"},
                    {"text": "Goodbye.", "next_node": "farewell_0"},
                ],
            },
            "lore_self": {
                "node_id": "lore_self",
                "text": "I am Elara. Herbalist, once. Now more of a... guardian, I suppose. Someone has to tend what's left.",
                "category": "lore", "emotion": "sad",
                "options": [
                    {"text": "What's left?", "next_node": "lore_0"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "lore_0": {
                "node_id": "lore_0",
                "text": "The blight started two seasons ago. First the animals changed.",
                "category": "lore", "emotion": "sad",
                "set_flags": {"heard_forest_corruption": True},
                "options": [
                    {"text": "Changed how?", "next_node": "lore_1"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "lore_1": {
                "node_id": "lore_1",
                "text": "Then the trees. Now even the river tastes wrong.",
                "category": "lore", "emotion": "fearful",
                "options": [
                    {"text": "Is there hope?", "next_node": "lore_2"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "lore_2": {
                "node_id": "lore_2",
                "text": "An old druid circle lies deeper in. If the wards still hold...",
                "category": "lore", "emotion": "whispering",
                "set_flags": {"heard_druid_circle": True},
                "options": [
                    {"text": "What would the circle do?", "next_node": "lore_3"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "lore_3": {
                "node_id": "lore_3",
                "text": "The druids anchored their magic to the oldest trees. If even one of those trees still stands uncorrupted, the circle might be reactivated. It could push the blight back from this part of the forest.",
                "category": "lore", "emotion": "excited",
                "options": [
                    {"text": "We could try.", "next_node": "hub"},
                    {"text": "Tell us about the potion.", "next_node": "quest_0"},
                ],
            },
            "lore_4": {
                "node_id": "lore_4",
                "text": "The spiders have grown. Not just bigger \u2014 smarter. They weave their webs across the moonpetal groves now, as if they know the flowers are valuable. Perhaps they do. The blight gives things a terrible cunning.",
                "category": "lore", "emotion": "fearful",
                "options": [
                    {"text": "We'll be careful.", "next_node": "hub"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "quest_0": {
                "node_id": "quest_0",
                "text": "I can brew a potion to resist the Crown's corruption.",
                "category": "quest", "emotion": "friendly",
                "options": [
                    {"text": "What do you need?", "next_node": "quest_1"},
                ],
            },
            "quest_1": {
                "node_id": "quest_1",
                "text": "But I need moonpetal blossoms. They only grow near the spider nests.",
                "category": "quest", "emotion": "fearful",
                "set_flags": {"moonpetal_quest_offered": True},
                "options": [
                    {"text": "We'll get them.", "next_node": "quest_accept",
                     "set_flags": {"moonpetal_quest_accepted": True}},
                    {"text": "Tell us about the spiders.", "next_node": "lore_4"},
                    {"text": "We need time.", "next_node": "hub"},
                ],
            },
            "quest_accept": {
                "node_id": "quest_accept",
                "text": "Bring me three, and I'll arm you against whatever waits at the heart.",
                "category": "quest", "emotion": "friendly",
                "options": [
                    {"text": "We're on it.", "next_node": "farewell_1"},
                    {"text": "Anything else?", "next_node": "hub"},
                ],
            },
            "hub": {
                "node_id": "hub",
                "text": "You carry no blight. That's... rare, these days. What else can I help with?",
                "category": "greeting", "emotion": "friendly",
                "options": [
                    {"text": "The forest.", "next_node": "lore_0"},
                    {"text": "The corruption potion.", "next_node": "quest_0",
                     "conditions": [{"flag": "moonpetal_quest_offered", "expected": False}]},
                    {"text": "The druid circle.", "next_node": "lore_2",
                     "conditions": [{"flag": "heard_druid_circle", "expected": False}]},
                    {"text": "The spiders.", "next_node": "lore_4"},
                    {"text": "Goodbye.", "next_node": "farewell_0"},
                ],
            },
            "farewell_0": {
                "node_id": "farewell_0",
                "text": "Step carefully. The forest remembers where you walk.",
                "category": "farewell", "emotion": "whispering",
                "is_terminal": True,
            },
            "farewell_1": {
                "node_id": "farewell_1",
                "text": "The moonpetals glow brightest at night. Look for the silver light between the webs. And... come back alive. The forest needs more friends.",
                "category": "farewell", "emotion": "sad",
                "is_terminal": True,
            },
        },
    }


def nessa_graph():
    return {
        "entry_node": "greeting_0",
        "nodes": {
            "greeting_0": {
                "node_id": "greeting_0",
                "text": "Heh. The swamp let you through. It doesn't do that for everyone.",
                "category": "greeting", "emotion": "friendly",
                "options": [
                    {"text": "We're looking for lost soldiers.", "next_node": "lore_soldiers",
                     "conditions": [{"flag": "patrol_quest_accepted"}]},
                    {"text": "What is this place?", "next_node": "lore_0"},
                    {"text": "We need your help.", "next_node": "quest_0"},
                    {"text": "What do you have for sale?", "next_node": "trade_0"},
                    {"text": "Goodbye.", "next_node": "farewell_0"},
                ],
            },
            "lore_0": {
                "node_id": "lore_0",
                "text": "Oh, the blight. Yes, I've watched it spread. Fascinating, really, in a horrible sort of way.",
                "category": "lore", "emotion": "friendly",
                "set_flags": {"heard_swamp_undead": True},
                "options": [
                    {"text": "How bad is it?", "next_node": "lore_1"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "lore_1": {
                "node_id": "lore_1",
                "text": "The swamp was always a bit... alive. But this is different. The water itself is infected.",
                "category": "lore", "emotion": "neutral",
                "options": [
                    {"text": "The dead?", "next_node": "lore_2"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "lore_2": {
                "node_id": "lore_2",
                "text": "The Sovereign's power comes from the Crown. Break the Crown, break the spell. Simple. Not easy, but simple.",
                "category": "lore", "emotion": "whispering",
                "options": [
                    {"text": "The bone mound?", "next_node": "lore_3"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "lore_3": {
                "node_id": "lore_3",
                "text": "There's something under the bone mound that predates the blight. Something older. Best not to wake it all the way.",
                "category": "lore", "emotion": "fearful",
                "set_flags": {"heard_bone_mound_ancient": True},
                "options": [
                    {"text": "What is it?", "next_node": "lore_3b"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "lore_3b": {
                "node_id": "lore_3b",
                "text": "I don't name things that might hear me. Let's just say the mound was a grave before the kingdom existed, and what's buried there didn't die willingly. The skull is all I need. Don't dig deeper.",
                "category": "lore", "emotion": "whispering",
                "options": [
                    {"text": "Understood.", "next_node": "hub"},
                    {"text": "About that skull...", "next_node": "quest_0"},
                ],
            },
            "lore_soldiers": {
                "node_id": "lore_soldiers",
                "text": "Your lost soldiers are at the drowned camp. Some of them, anyway. The rest are... walking around.",
                "category": "lore", "emotion": "neutral",
                "set_flags": {"heard_soldier_fate": True},
                "options": [
                    {"text": "Walking around?", "next_node": "lore_soldiers_2"},
                    {"text": "Can you help them?", "next_node": "quest_0"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "lore_soldiers_2": {
                "node_id": "lore_soldiers_2",
                "text": "Three are dead. True dead. You'll find insignias on the bodies. The other two? The swamp took them differently. They wander the hollow, not alive, not dead. My tincture could quiet them. Give them peace.",
                "category": "lore", "emotion": "sad",
                "options": [
                    {"text": "What do you need for the tincture?", "next_node": "quest_0"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "quest_0": {
                "node_id": "quest_0",
                "text": "The dead walk because the blight won't let them sleep. Rude, isn't it? I can brew something to quiet them. But I need a bone from that mound. A specific bone.",
                "category": "quest", "emotion": "friendly",
                "set_flags": {"bone_quest_offered": True},
                "options": [
                    {"text": "What bone?", "next_node": "quest_1"},
                ],
            },
            "quest_1": {
                "node_id": "quest_1",
                "text": "The skull of whatever's buried at the bottom. Bring it, and I'll give you something that keeps the dead... polite.",
                "category": "quest", "emotion": "friendly",
                "options": [
                    {"text": "Sounds dangerous.", "next_node": "quest_2"},
                    {"text": "We'll do it.", "next_node": "quest_accept",
                     "set_flags": {"bone_quest_accepted": True}},
                    {"text": "We need time.", "next_node": "hub"},
                ],
            },
            "quest_2": {
                "node_id": "quest_2",
                "text": "Don't worry, it's probably only mostly cursed.",
                "category": "quest", "emotion": "friendly",
                "options": [
                    {"text": "Reassuring. We'll do it.", "next_node": "quest_accept",
                     "set_flags": {"bone_quest_accepted": True}},
                    {"text": "We'll think about it.", "next_node": "hub"},
                ],
            },
            "quest_accept": {
                "node_id": "quest_accept",
                "text": "Brave and foolish. My favorite combination. When you reach the mound, the lurkers will smell you first. Kill them quick \u2014 they call more if you dawdle.",
                "category": "quest", "emotion": "excited",
                "options": [
                    {"text": "Any other advice?", "next_node": "trade_0"},
                    {"text": "We're going.", "next_node": "farewell_1"},
                ],
            },
            "trade_0": {
                "node_id": "trade_0",
                "text": "Potions, charms, and questionable advice. All reasonably priced.",
                "category": "trade", "emotion": "friendly",
                "options": [
                    {"text": "Good to know.", "next_node": "hub"},
                    {"text": "Goodbye.", "next_node": "farewell_0"},
                ],
            },
            "hub": {
                "node_id": "hub",
                "text": "I knew you were coming. The leeches told me. They tell me everything. What else?",
                "category": "greeting", "emotion": "friendly",
                "options": [
                    {"text": "The lost soldiers.", "next_node": "lore_soldiers",
                     "conditions": [{"flag": "patrol_quest_accepted"},
                                    {"flag": "heard_soldier_fate", "expected": False}]},
                    {"text": "The blight.", "next_node": "lore_0"},
                    {"text": "The bone mound quest.", "next_node": "quest_0",
                     "conditions": [{"flag": "bone_quest_offered", "expected": False}]},
                    {"text": "Trading.", "next_node": "trade_0"},
                    {"text": "Goodbye.", "next_node": "farewell_0"},
                ],
            },
            "farewell_0": {
                "node_id": "farewell_0",
                "text": "Try not to drown. The paperwork is terrible.",
                "category": "farewell", "emotion": "friendly",
                "is_terminal": True,
            },
            "farewell_1": {
                "node_id": "farewell_1",
                "text": "If the wisps follow you, don't follow them back. That's free advice. You're welcome.",
                "category": "farewell", "emotion": "friendly",
                "is_terminal": True,
            },
        },
    }


def maren_graph():
    return {
        "entry_node": "greeting_0",
        "nodes": {
            "greeting_0": {
                "node_id": "greeting_0",
                "text": "Come in, child. The Dawn's light still reaches here, even if it struggles.",
                "category": "greeting", "emotion": "friendly",
                "options": [
                    {"text": "Brenna sent us.", "next_node": "greeting_referred",
                     "conditions": [{"flag": "heard_maren_tip"}]},
                    {"text": "Are you a healer?", "next_node": "lore_self"},
                    {"text": "What can you tell us?", "next_node": "lore_0"},
                    {"text": "We need blessings.", "next_node": "quest_0"},
                    {"text": "Goodbye.", "next_node": "farewell_0"},
                ],
            },
            "greeting_referred": {
                "node_id": "greeting_referred",
                "text": "Brenna watches over the body, I watch over the spirit. Between us, we keep Millhaven standing. You're hurt. Or you will be soon. Either way, sit.",
                "category": "greeting", "emotion": "friendly",
                "options": [
                    {"text": "Tell us about the wards.", "next_node": "quest_0"},
                    {"text": "What's happening?", "next_node": "lore_0"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "lore_self": {
                "node_id": "lore_self",
                "text": "I am Sister Maren, keeper of this chapel and the last ward of the five. For what that's still worth.",
                "category": "lore", "emotion": "sad",
                "options": [
                    {"text": "The last ward?", "next_node": "lore_3"},
                    {"text": "What happened?", "next_node": "lore_0"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "lore_0": {
                "node_id": "lore_0",
                "text": "The Shattering wasn't just the land breaking. The veil between this world and the next grew thin.",
                "category": "lore", "emotion": "fearful",
                "set_flags": {"heard_veil_thinning": True},
                "options": [
                    {"text": "The dead walk?", "next_node": "lore_1"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "lore_1": {
                "node_id": "lore_1",
                "text": "The dead don't rest easy near the swamp. I've heard the reports. Corpses walking.",
                "category": "lore", "emotion": "sad",
                "options": [
                    {"text": "What caused all this?", "next_node": "lore_2"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "lore_2": {
                "node_id": "lore_2",
                "text": "Whatever Morvain found in that citadel, it predates the kingdom. Predates the gods, maybe.",
                "category": "lore", "emotion": "whispering",
                "options": [
                    {"text": "The wards?", "next_node": "lore_3"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "lore_3": {
                "node_id": "lore_3",
                "text": "There were five wards protecting the realm. Four have fallen. This chapel holds the last.",
                "category": "lore", "emotion": "sad",
                "set_flags": {"heard_five_wards": True, "heard_last_ward": True},
                "options": [
                    {"text": "Can they be restored?", "next_node": "quest_0"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "quest_0": {
                "node_id": "quest_0",
                "text": "The wards on this chapel are failing. Every week they grow dimmer. I need dawn lotus flowers. They grow in the frozen wastes to the northeast.",
                "category": "quest", "emotion": "pleading",
                "set_flags": {"dawn_lotus_quest_offered": True},
                "options": [
                    {"text": "We know where to find them.", "next_node": "quest_accept_informed",
                     "conditions": [{"flag": "heard_dawn_lotus_location"}]},
                    {"text": "Tell us more.", "next_node": "quest_1"},
                    {"text": "We'll think about it.", "next_node": "hub"},
                ],
            },
            "quest_1": {
                "node_id": "quest_1",
                "text": "The ice preserves them perfectly, but the cold preserves other things too. Bring me dawn lotus and I can restore the wards \u2014 and bless your weapons against the blight.",
                "category": "quest", "emotion": "commanding",
                "options": [
                    {"text": "We'll do it.", "next_node": "quest_accept",
                     "set_flags": {"dawn_lotus_quest_accepted": True}},
                    {"text": "We need to prepare.", "next_node": "hub"},
                ],
            },
            "quest_accept": {
                "node_id": "quest_accept",
                "text": "Thank you, child. The dawn lotus glows golden even under ice. Look near water. And dress warmly \u2014 the cold there is not natural.",
                "category": "quest", "emotion": "friendly",
                "options": [
                    {"text": "We'll return.", "next_node": "farewell_1"},
                    {"text": "Anything else?", "next_node": "hub"},
                ],
            },
            "quest_accept_informed": {
                "node_id": "quest_accept_informed",
                "text": "You know of the lotus already? Then the Dawn guides your path. Bring them quickly \u2014 the wards grow weaker by the day.",
                "category": "quest", "emotion": "excited",
                "set_flags": {"dawn_lotus_quest_accepted": True},
                "options": [
                    {"text": "We won't delay.", "next_node": "farewell_1"},
                    {"text": "Anything else?", "next_node": "hub"},
                ],
            },
            "hub": {
                "node_id": "hub",
                "text": "What else weighs on your spirit?",
                "category": "greeting", "emotion": "friendly",
                "options": [
                    {"text": "The wards.", "next_node": "quest_0",
                     "conditions": [{"flag": "dawn_lotus_quest_offered", "expected": False}]},
                    {"text": "The Shattering.", "next_node": "lore_0"},
                    {"text": "The last ward.", "next_node": "lore_3"},
                    {"text": "Goodbye.", "next_node": "farewell_0"},
                ],
            },
            "farewell_0": {
                "node_id": "farewell_0",
                "text": "Dawn comes. It always comes. Remember that when the dark closes in.",
                "category": "farewell", "emotion": "friendly",
                "is_terminal": True,
            },
            "farewell_1": {
                "node_id": "farewell_1",
                "text": "The light goes with you, whether you feel it or not.",
                "category": "farewell", "emotion": "friendly",
                "is_terminal": True,
            },
        },
    }


def kael_graph():
    return {
        "entry_node": "greeting_0",
        "nodes": {
            "greeting_0": {
                "node_id": "greeting_0",
                "text": "Don't \u2014 don't attack! I'm not with them anymore!",
                "category": "greeting", "emotion": "fearful",
                "options": [
                    {"text": "Who are you?", "next_node": "lore_self"},
                    {"text": "We know about Torven.", "next_node": "lore_torven",
                     "conditions": [{"flag": "heard_about_torven"}]},
                    {"text": "What's inside?", "next_node": "quest_0"},
                    {"text": "Step aside.", "next_node": "farewell_0"},
                ],
            },
            "lore_self": {
                "node_id": "lore_self",
                "text": "Thank the gods, living people. Real, breathing, living people. I was guild muscle. Torven's men. We brought supplies to the citadel for months.",
                "category": "lore", "emotion": "fearful",
                "options": [
                    {"text": "Why did you leave?", "next_node": "lore_0"},
                    {"text": "What's inside?", "next_node": "quest_0"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "lore_0": {
                "node_id": "lore_0",
                "text": "But what's in there... it's not natural. Morvain isn't a man anymore. He's... something else.",
                "category": "lore", "emotion": "fearful",
                "options": [
                    {"text": "What do you mean?", "next_node": "lore_1"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "lore_1": {
                "node_id": "lore_1",
                "text": "Morvain talks to the Crown. I've heard him. Late at night, whispering to it like it's alive. Maybe it is.",
                "category": "lore", "emotion": "whispering",
                "options": [
                    {"text": "The fallen knights?", "next_node": "lore_2"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "lore_2": {
                "node_id": "lore_2",
                "text": "The fallen knights? They were Ashenmere's royal guard. Good men. The Crown took them.",
                "category": "lore", "emotion": "sad",
                "options": [
                    {"text": "Were there other deserters?", "next_node": "lore_3"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "lore_3": {
                "node_id": "lore_3",
                "text": "There were others like me. Soldiers who realized what we were part of. Most didn't make it out.",
                "category": "lore", "emotion": "sad",
                "options": [
                    {"text": "Tell us about the layout.", "next_node": "quest_0"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "lore_torven": {
                "node_id": "lore_torven",
                "text": "Torven \u2014 that's the guild master \u2014 he's been feeding resources to Morvain. Money, soldiers, materials. Nobody knows why. Fear, probably. Or promises. The Crown can show you things. Things you want to see.",
                "category": "lore", "emotion": "fearful",
                "set_flags": {"heard_torven_detail": True},
                "options": [
                    {"text": "What's inside the citadel?", "next_node": "quest_0"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "quest_0": {
                "node_id": "quest_0",
                "text": "The main hall is patrolled by fallen knights. They never stop. Never rest.",
                "category": "quest", "emotion": "fearful",
                "set_flags": {"heard_citadel_layout": True},
                "options": [
                    {"text": "Is there another way?", "next_node": "quest_1"},
                ],
            },
            "quest_1": {
                "node_id": "quest_1",
                "text": "But the side corridor \u2014 the trapped corridor \u2014 it's dangerous, but the traps are mechanical. Avoidable.",
                "category": "quest", "emotion": "neutral",
                "set_flags": {"heard_trapped_corridor": True},
                "options": [
                    {"text": "What's past the traps?", "next_node": "quest_2"},
                ],
            },
            "quest_2": {
                "node_id": "quest_2",
                "text": "Past that, there's a war chapel. The old wards still hold there. You can rest safely.",
                "category": "quest", "emotion": "friendly",
                "set_flags": {"heard_war_chapel_safe": True},
                "options": [
                    {"text": "And beyond?", "next_node": "quest_3"},
                ],
            },
            "quest_3": {
                "node_id": "quest_3",
                "text": "The throne room is beyond the chapel. That's where Morvain waits. With the Crown. One more thing. The Crown \u2014 I don't think destroying Morvain is enough. You have to break the Crown itself.",
                "category": "quest", "emotion": "commanding",
                "set_flags": {"heard_crown_must_break": True},
                "options": [
                    {"text": "How do we break it?", "next_node": "quest_4"},
                    {"text": "We'll figure it out.", "next_node": "farewell_1"},
                ],
            },
            "quest_4": {
                "node_id": "quest_4",
                "text": "I don't know. I just know that others tried to kill him and failed. The Crown healed him. It won't let its host die easily. Find another way.",
                "category": "quest", "emotion": "pleading",
                "options": [
                    {"text": "We'll find a way.", "next_node": "farewell_1"},
                    {"text": "Anything else?", "next_node": "hub"},
                ],
            },
            "hub": {
                "node_id": "hub",
                "text": "I've told you what I know. Anything else?",
                "category": "greeting", "emotion": "fearful",
                "options": [
                    {"text": "The citadel layout.", "next_node": "quest_0",
                     "conditions": [{"flag": "heard_citadel_layout", "expected": False}]},
                    {"text": "Torven.", "next_node": "lore_torven",
                     "conditions": [{"flag": "heard_about_torven"}]},
                    {"text": "The fallen knights.", "next_node": "lore_2"},
                    {"text": "Goodbye.", "next_node": "farewell_0"},
                ],
            },
            "farewell_0": {
                "node_id": "farewell_0",
                "text": "I'm going south. Far south. Don't follow me.",
                "category": "farewell", "emotion": "fearful",
                "is_terminal": True,
            },
            "farewell_1": {
                "node_id": "farewell_1",
                "text": "Good luck. You'll need it. And... I'm sorry. For my part in this.",
                "category": "farewell", "emotion": "sad",
                "is_terminal": True,
            },
        },
    }


def brokk_graph():
    return {
        "entry_node": "greeting_0",
        "nodes": {
            "greeting_0": {
                "node_id": "greeting_0",
                "text": "Oh thank the stone! I've been trapped here for... days? Weeks? Time's strange underground.",
                "category": "greeting", "emotion": "excited",
                "options": [
                    {"text": "Durin sent us for star-iron.", "next_node": "quest_durin",
                     "conditions": [{"flag": "star_iron_quest_accepted"}]},
                    {"text": "What happened?", "next_node": "lore_self"},
                    {"text": "What's in these caves?", "next_node": "lore_0"},
                    {"text": "Stay safe.", "next_node": "farewell_0"},
                ],
            },
            "lore_self": {
                "node_id": "lore_self",
                "text": "Mind the rocks, the whole section's unstable. I was looking for the old dwarven forge when the cave-in hit.",
                "category": "lore", "emotion": "fearful",
                "options": [
                    {"text": "The forge?", "next_node": "quest_0"},
                    {"text": "The caves?", "next_node": "lore_0"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "lore_0": {
                "node_id": "lore_0",
                "text": "The crystals weren't always this color. They used to be blue. Clear. Beautiful.",
                "category": "lore", "emotion": "sad",
                "set_flags": {"heard_crystal_corruption": True},
                "options": [
                    {"text": "What changed?", "next_node": "lore_1"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "lore_1": {
                "node_id": "lore_1",
                "text": "Then that green started creeping in. The hum changed. Lower. Angrier.",
                "category": "lore", "emotion": "fearful",
                "options": [
                    {"text": "Is there a source?", "next_node": "lore_2"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "lore_2": {
                "node_id": "lore_2",
                "text": "There's a chamber at the very bottom with a crystal the size of a house. Pulsing. Like a heart.",
                "category": "lore", "emotion": "whispering",
                "set_flags": {"heard_crystal_relay": True},
                "options": [
                    {"text": "What is it?", "next_node": "lore_3"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "lore_3": {
                "node_id": "lore_3",
                "text": "I think it's connected to whatever's happening up top. A relay, channeling power from the center. If you could destroy that crystal... might weaken the corruption for miles around.",
                "category": "lore", "emotion": "commanding",
                "options": [
                    {"text": "We might try.", "next_node": "hub"},
                    {"text": "The forge?", "next_node": "quest_0"},
                ],
            },
            "quest_0": {
                "node_id": "quest_0",
                "text": "The forge! The old dwarven forge is deeper in. I was looking for it when the cave-in hit.",
                "category": "quest", "emotion": "excited",
                "options": [
                    {"text": "What's guarding it?", "next_node": "quest_1"},
                    {"text": "Directions?", "next_node": "quest_2"},
                ],
            },
            "quest_1": {
                "node_id": "quest_1",
                "text": "There are things guarding it now. Golems, but wrong. The crystals grew through them.",
                "category": "quest", "emotion": "fearful",
                "options": [
                    {"text": "How do we get past?", "next_node": "quest_2"},
                ],
            },
            "quest_2": {
                "node_id": "quest_2",
                "text": "Past the gallery, keep left. The forge is behind a door with a hammer sigil.",
                "category": "quest", "emotion": "neutral",
                "set_flags": {"heard_forge_directions": True},
                "options": [
                    {"text": "Is the star-iron there?", "next_node": "quest_3"},
                    {"text": "We'll find it.", "next_node": "farewell_1"},
                ],
            },
            "quest_3": {
                "node_id": "quest_3",
                "text": "The star-iron's in there \u2014 I'm sure of it. My grandfather told me about this place.",
                "category": "quest", "emotion": "excited",
                "options": [
                    {"text": "We'll get it.", "next_node": "farewell_1"},
                    {"text": "Something else.", "next_node": "hub"},
                ],
            },
            "quest_durin": {
                "node_id": "quest_durin",
                "text": "Durin! You know Durin? Ha! That stubborn old goat is still hammering away? Good. The star-iron is real \u2014 I've seen the shimmer through the cracks in the forge door. Past the gallery, keep left. Hammer sigil on the door. Can't miss it.",
                "category": "quest", "emotion": "excited",
                "set_flags": {"heard_forge_directions": True},
                "options": [
                    {"text": "What about the golems?", "next_node": "quest_1"},
                    {"text": "The green crystal?", "next_node": "lore_2"},
                    {"text": "We'll handle it.", "next_node": "farewell_1"},
                ],
            },
            "hub": {
                "node_id": "hub",
                "text": "I'll wait here. Not going deeper without an army. Or at least a stiff drink. What else?",
                "category": "greeting", "emotion": "neutral",
                "options": [
                    {"text": "The forge.", "next_node": "quest_0",
                     "conditions": [{"flag": "heard_forge_directions", "expected": False}]},
                    {"text": "The crystals.", "next_node": "lore_0"},
                    {"text": "The big crystal.", "next_node": "lore_2",
                     "conditions": [{"flag": "heard_crystal_relay", "expected": False}]},
                    {"text": "Goodbye.", "next_node": "farewell_0"},
                ],
            },
            "farewell_0": {
                "node_id": "farewell_0",
                "text": "I'll wait here. Not going deeper without an army. Or at least a stiff drink.",
                "category": "farewell", "emotion": "neutral",
                "is_terminal": True,
            },
            "farewell_1": {
                "node_id": "farewell_1",
                "text": "If you find the forge, bring me back a souvenir. Preferably not cursed.",
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
        "Captain Thessa": thessa_graph(),
        "Harlen the Cartographer": harlen_graph(),
        "Sigrid Frostborn": sigrid_graph(),
        "Zahara of the Sand": zahara_graph(),
        "Ghost of King Aldric": king_aldric_graph(),
        "Elara the Herbalist": elara_graph(),
        "Nessa the Witch": nessa_graph(),
        "Sister Maren": maren_graph(),
        "Deserter Kael": kael_graph(),
        "Brokk the Miner": brokk_graph(),
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

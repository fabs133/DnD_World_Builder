"""Side event registry — 100 events with 300+ variants for empty tile population."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SideEventVariant:
    name: str
    narrative: str
    skill_check: Optional[dict] = None
    success_text: Optional[str] = None
    reward: Optional[dict] = None
    fail_text: Optional[str] = None
    choices: Optional[tuple[dict, ...]] = None
    fail_consequences: Optional[dict] = None
    success_consequences: Optional[dict] = None


@dataclass(frozen=True)
class SideEvent:
    event_id: int
    name: str
    category: str
    terrain_allow: tuple[str, ...]
    terrain_deny: tuple[str, ...]
    variants: tuple[SideEventVariant, ...]


def _e(eid, name, cat, allow, deny, variants):
    return SideEvent(eid, name, cat, tuple(allow), tuple(deny),
                     tuple(SideEventVariant(**v) for v in variants))


# ── Terrain shorthand ──────────────────────────────────────────────
_ALL = ()
_NO_WATER_WALL = ("WATER", "WALL")
_LAND_ONLY = ("GRASS", "FLOOR", "SAND", "SWAMP")
_INDOOR = ("FLOOR",)
_OUTDOOR = ("GRASS", "SAND", "SWAMP", "MOUNTAIN")

# ═══════════════════════════════════════════════════════════════════
#  EXPLORATION & DISCOVERY  (1–15)
# ═══════════════════════════════════════════════════════════════════

_EVENTS = [
    _e(1, "Strange Fungus", "exploration", _ALL, _NO_WATER_WALL, [
        {"name": "Glowing Sporecaps",
         "narrative": "Clusters of pale mushrooms cling to the damp ground, each cap pulsing with a soft blue-green glow. The air smells of wet earth and something faintly sweet.",
         "skill_check": {"skill": "Nature", "dc": 10},
         "success_text": "You recognize sporecaps — harmless, but their glow intensifies near corrupted soil. These are dimmer than usual. The blight hasn't fully reached here yet."},
        {"name": "Withered Moldpatch",
         "narrative": "A patch of grey-brown mold spreads across the ground in a perfect circle. Everything within the ring is dead — grass, insects, even the soil looks ashen."},
        {"name": "Pulsing Mycelium Cluster",
         "narrative": "Thick white threads of mycelium weave through the soil, visibly pulsing in a slow rhythm. When you step closer, the pulsing quickens as if aware of your presence.",
         "skill_check": {"skill": "Nature", "dc": 12},
         "success_text": "The mycelium is reacting to vibration, not intelligence. Still, its reach is enormous — this network could span miles underground."},
        {"name": "Toxic Bloom",
         "narrative": "Vivid purple flowers have burst from a crack in the earth, their petals glistening with an oily sheen. A faint haze hangs around them. Beautiful, but your eyes water just looking at them."},
    ]),

    _e(2, "Collapsed Passage", "exploration", _ALL, ("WATER",), [
        {"name": "Rubble-Choked Tunnel",
         "narrative": "A tunnel entrance has been buried under a cascade of broken stone. Fresh scratch marks on the rubble suggest something tried to dig through from the other side — recently.",
         "skill_check": {"skill": "Perception", "dc": 12},
         "success_text": "Between the rocks, you spot a glint of metal. Someone left a blade wedged in the collapse — perhaps a marker, or a last desperate act."},
        {"name": "Cracked Archway",
         "narrative": "A stone archway stands alone, its keystone split cleanly in two. Beyond it, the path continues normally — but the arch itself radiates a faint unease, as if it once held something back."},
        {"name": "Caved-In Mineshaft",
         "narrative": "Rotting timber frames jut from the hillside around a dark opening choked with earth. A weathered sign reads 'SHAFT 7 — CONDEMNED.' The wood is newer than the mine."},
    ]),

    _e(3, "Abandoned Campsite", "exploration", _ALL, _NO_WATER_WALL, [
        {"name": "Cold Fire Pit",
         "narrative": "A ring of stones surrounds grey ashes. Whoever camped here left in a hurry — a half-eaten meal sits on a flat rock, and a bedroll lies unrolled but empty.",
         "skill_check": {"skill": "Survival", "dc": 10},
         "success_text": "The ashes are three days old. The tracks lead northeast, then stop abruptly — as if the person simply ceased to exist."},
        {"name": "Ransacked Bedrolls",
         "narrative": "Someone tore through this camp like a storm. Bedrolls are slashed open, packs emptied and scattered. Whatever they were looking for, the searchers were thorough — and angry."},
        {"name": "Hastily Buried Cache",
         "narrative": "A patch of freshly turned earth catches your eye. Someone buried something here and covered it with leaves. The work was sloppy — done in a panic.",
         "skill_check": {"skill": "Investigation", "dc": 11},
         "success_text": "You uncover a waxed leather pouch containing a handful of coins and a folded note: 'If I don't come back, send these to Millhaven.'",
         "reward": {"type": "loot", "name": "Buried coin pouch", "gold_value": 8}},
    ]),

    _e(4, "Mysterious Footprints", "exploration", _ALL, _NO_WATER_WALL, [
        {"name": "Clawed Tracks in Mud",
         "narrative": "Deep claw marks score the soft ground — three toes, each ending in a curved gouge. The stride is impossibly long. Whatever made these was moving fast.",
         "skill_check": {"skill": "Survival", "dc": 13},
         "success_text": "The gait pattern is wrong for any natural beast. The creature was limping on its right side, and the claw marks grow deeper as the trail continues — it was accelerating despite injury."},
        {"name": "Barefoot Trail",
         "narrative": "A line of barefoot prints wanders erratically across the ground, sometimes circling, sometimes stopping for long pauses. They end at a perfectly normal patch of earth with no sign of departure."},
        {"name": "Massive Boot Imprints",
         "narrative": "Enormous boot prints — twice the size of any human foot — press deep into the earth. They march in a perfectly straight line, each step exactly the same distance apart, like a machine."},
        {"name": "Drag Marks",
         "narrative": "Two parallel furrows cut through the dirt, flanked by scuffed footprints. Something heavy was dragged through here. A dark stain marks the point where the trail begins."},
    ]),

    _e(5, "Ancient Carving", "exploration", _ALL, ("WATER",), [
        {"name": "Faded Wall Runes",
         "narrative": "Carved into a rock face, barely visible under centuries of weathering, a line of angular runes catches the light. You can't read them, but the shapes feel deliberate — a message, not decoration.",
         "skill_check": {"skill": "Arcana", "dc": 13},
         "success_text": "The runes are in Old Ashenmere script. They read: 'Beyond this point, the Crown's eye watches.' A ward boundary, long since failed."},
        {"name": "Scratched Warning Glyph",
         "narrative": "Someone scratched a crude symbol into the stone at eye level — a circle with a jagged line through it. Below it, three words in Common: 'DO NOT DIG.'"},
        {"name": "Dwarven Clan Seal",
         "narrative": "A perfectly preserved dwarven clan seal is carved into the bedrock — a hammer crossing a mountain peak. The craftsmanship is extraordinary, untouched by the decay around it."},
    ]),

    _e(6, "Hidden Alcove", "exploration", _ALL, _NO_WATER_WALL, [
        {"name": "Cobwebbed Niche",
         "narrative": "Behind a curtain of old cobwebs, a small niche is cut into the wall. Inside: a clay cup, a dried flower, and a child's wooden toy. An offering, or a memorial.",
         "skill_check": {"skill": "Investigation", "dc": 10},
         "success_text": "The toy is carved in a style common to Millhaven. Someone from town came here to mourn — the flower is dawn lily, placed at graves."},
        {"name": "Moss-Curtained Hollow",
         "narrative": "A hanging curtain of moss conceals a shallow hollow just large enough for a person to sit in. The stone inside is worn smooth — someone used this as a hiding spot, and often."},
        {"name": "Bricked-Over Recess",
         "narrative": "A section of wall has been bricked over with mismatched stones, clearly newer than the surrounding structure. Something was sealed behind it. The mortar is crumbling."},
    ]),

    _e(7, "Unstable Ground", "exploration", _ALL, ("WATER", "WALL"), [
        {"name": "Crumbling Ledge",
         "narrative": "The ground ahead narrows to a crumbling ledge. Loose stones tumble into darkness below with each step. The path is passable, but demands careful footing."},
        {"name": "Sinking Mud",
         "narrative": "The earth here has a soft, yielding quality. Your boots sink an inch with each step, and the suction resists when you pull free. Not quicksand — not yet — but the ground is saturated and treacherous."},
        {"name": "Cracked Flagstones",
         "narrative": "The stone floor is webbed with cracks, some wide enough to peer through. Below, you glimpse empty darkness and feel a draft of cold air rising through the gaps."},
    ]),

    _e(8, "Echoing Chamber", "exploration", _ALL, ("WATER",), [
        {"name": "Whispering Gallery",
         "narrative": "The acoustics here are strange. Your breathing echoes back to you from every direction, layered and distorted. For a moment, you could swear the echoes are saying words you didn't speak.",
         "skill_check": {"skill": "Perception", "dc": 14},
         "success_text": "It's not your echo. Someone — or something — is whispering from deeper in. The words are too faint to make out, but the cadence sounds like a prayer."},
        {"name": "Droning Resonance Hall",
         "narrative": "A low, constant drone fills this space — not a sound you hear so much as feel in your chest. The walls vibrate faintly. The resonance makes it hard to think clearly."},
        {"name": "Silent Void Pocket",
         "narrative": "Sound dies here. Your footsteps, your breathing, even the clink of your gear — all swallowed by an unnatural silence. The effect ends abruptly at an invisible boundary."},
    ]),

    _e(9, "Old Battlefield", "exploration", _ALL, _NO_WATER_WALL, [
        {"name": "Rusted Weapons in Dirt",
         "narrative": "Broken blades and spearheads jut from the earth like iron weeds. The soil is darker here, stained by old blood. Whatever battle was fought, neither side cleaned up.",
         "skill_check": {"skill": "History", "dc": 12},
         "success_text": "The weapon styles are mixed — kingdom regulars and something older. This predates the Shattering. A border skirmish, perhaps, from the last century."},
        {"name": "Shattered Shield Wall",
         "narrative": "A line of broken shields lies half-buried in the dirt, still roughly in formation. The soldiers who held them are gone, but the shields tell the story — they were overwhelmed from behind."},
        {"name": "Bleached Bone Field",
         "narrative": "Bones lie scattered across the ground, bleached white by sun and rain. Most are animal — but not all. A skull grins up from the grass, missing its jaw."},
    ]),

    _e(10, "Peculiar Weather", "exploration", _OUTDOOR, (), [
        {"name": "Localized Fog Bank",
         "narrative": "A wall of thick fog hangs in the air ahead, its edges razor-sharp. Beyond the boundary, visibility drops to arm's length. The fog doesn't drift or dissipate — it just sits there, waiting."},
        {"name": "Sudden Temperature Drop",
         "narrative": "The air turns cold between one step and the next. Your breath fogs. Frost crystals form on your gear. Then, three steps later, the warmth returns as if nothing happened."},
        {"name": "Unnatural Stillness",
         "narrative": "Not a blade of grass moves. Not a leaf rustles. The air itself feels frozen in place — not cold, but utterly, perfectly still. Even your movement feels like pushing through something resistant."},
        {"name": "Static Charge in the Air",
         "narrative": "Your hair stands on end. Metal gear buzzes faintly. A sharp ozone smell fills the air, and tiny sparks crackle between your fingers when you flex your hand."},
    ]),

    _e(11, "Overgrown Ruin", "exploration", _OUTDOOR, ("WATER",), [
        {"name": "Vine-Strangled Pillar",
         "narrative": "A stone pillar rises from the undergrowth, wrapped so tightly in vines that the stone itself is cracking under the pressure. Whatever building this supported is long gone."},
        {"name": "Root-Split Foundation",
         "narrative": "The outline of a foundation is still visible — straight edges and right angles beneath the weeds. Tree roots have split the stones apart over centuries, reclaiming the space for the wild."},
        {"name": "Moss-Blanketed Altar",
         "narrative": "A flat stone slab sits on a low platform, every surface carpeted in thick green moss. The shape is unmistakable — an altar. To what god, only the moss knows now."},
    ]),

    _e(12, "Mineral Vein", "exploration", ("MOUNTAIN", "FLOOR"), (), [
        {"name": "Quartz Seam",
         "narrative": "A vein of white quartz cuts through the rock face, catching the light and throwing prismatic reflections. The crystals are clear and sharp — untouched by the corruption."},
        {"name": "Iron-Streaked Rock",
         "narrative": "Rust-red streaks run through the stone here, marking a rich iron deposit. The rock crumbles easily where the iron has oxidized. A miner's dream, if anyone was left to mine it."},
        {"name": "Glittering Unknown Ore",
         "narrative": "An unfamiliar metal glints in the rock — too dark for silver, too bright for iron. It catches the light with an almost oily sheen that shifts between green and purple.",
         "skill_check": {"skill": "Nature", "dc": 14},
         "success_text": "You've never seen this ore naturally — it might be star-iron in its raw form, or something the corruption has transmuted from common iron."},
    ]),

    _e(13, "Underground Stream", "exploration", ("FLOOR", "MOUNTAIN", "SWAMP"), (), [
        {"name": "Trickling Rivulet",
         "narrative": "A thin stream of water runs along a natural channel in the rock, barely wider than your hand. The water is clear and cold — remarkably clean given the state of things above."},
        {"name": "Flooded Corridor",
         "narrative": "Ankle-deep water covers the floor here, still and dark. Ripples spread from your steps and take far too long to settle. The water is warmer than it should be."},
        {"name": "Frozen Waterfall",
         "narrative": "A cascade of ice clings to the rock face — a waterfall frozen mid-flow. The ice is perfectly clear, and deep within it, you can see air bubbles trapped in strange spiral patterns."},
    ]),

    _e(14, "Forgotten Shrine", "exploration", _ALL, _NO_WATER_WALL, [
        {"name": "Cracked Idol",
         "narrative": "A small stone idol sits in a carved niche, its face split by a deep crack. Despite the damage, fresh wildflowers have been placed at its feet — someone still tends this shrine.",
         "skill_check": {"skill": "Religion", "dc": 11},
         "success_text": "The idol represents Aelindra, goddess of safe passage. The flowers are a traveler's prayer — placed by someone hoping to survive their journey."},
        {"name": "Offering Bowl with Old Coins",
         "narrative": "A shallow stone bowl holds a handful of tarnished coins and a few withered berries. The coins are from at least three different eras. This shrine has been receiving offerings for centuries.",
         "reward": {"type": "loot", "name": "Shrine offerings", "gold_value": 3}},
        {"name": "Defaced Holy Symbol",
         "narrative": "A holy symbol has been carved into the rock — then violently scratched out, the stone gouged deep by something sharp. Whoever defaced it was thorough, but the outline is still visible."},
    ]),

    _e(15, "Skylight", "exploration", ("FLOOR", "MOUNTAIN"), (), [
        {"name": "Shaft of Natural Light",
         "narrative": "A beam of daylight pierces the darkness from a crack far above, illuminating a small circle on the floor. Dust motes drift lazily through the light. It feels sacred."},
        {"name": "Rain-Dripping Fissure",
         "narrative": "Water drips steadily from a narrow fissure in the ceiling, pooling in a natural basin below. The rhythmic dripping is the only sound — peaceful, almost meditative."},
        {"name": "Moonlit Opening",
         "narrative": "A gap in the roof opens to the sky. Pale light filters down, painting the walls in silver. Vines have crept in through the opening, hanging like green curtains."},
    ]),

    # ═══════════════════════════════════════════════════════════════
    #  NPC ENCOUNTERS  (16–30)
    # ═══════════════════════════════════════════════════════════════

    _e(16, "Lost Traveler", "npc", _LAND_ONLY, ("WATER", "WALL", "MOUNTAIN"), [
        {"name": "Wounded Pilgrim",
         "narrative": "A figure in a torn travelling cloak sits propped against a rock, clutching a bloodied arm. They look up with desperate eyes. 'Please... I was on the road to the chapel when they came.'"},
        {"name": "Confused Scholar",
         "narrative": "A bespectacled woman paces in a tight circle, muttering and consulting a crumpled map that's clearly upside-down. 'This can't be right. The landmarks don't match anything anymore.'"},
        {"name": "Panicked Messenger",
         "narrative": "A young runner stumbles into view, gasping for breath. 'The bridge — the bridge is gone! I have to warn —' They stop, look around wildly, and seem to forget what they were saying."},
    ]),

    _e(17, "Wandering Merchant", "npc", _LAND_ONLY, ("WATER", "WALL", "MOUNTAIN"), [
        {"name": "Trinket Peddler",
         "narrative": "A hunched figure with an enormous pack grins through missing teeth. 'Charms! Baubles! Genuine lucky tokens, guaranteed to work or your money back!' The tokens look like painted rocks."},
        {"name": "Potion Hawker",
         "narrative": "A woman with a belt of clinking vials waves you over. 'Healing potions, stamina draughts, and one mystery flask I found in a ruin. Discount on the mystery one — I'm afraid to open it.'"},
        {"name": "Black-Market Fence",
         "narrative": "A figure in dark clothes leans against a tree, arms crossed. 'Looking to buy? Sell? I don't ask where things come from, and neither should you.'"},
    ]),

    _e(18, "Territorial Hermit", "npc", _ALL, _NO_WATER_WALL, [
        {"name": "Cave-Dwelling Recluse",
         "narrative": "A ragged figure emerges from the shadows, brandishing a gnarled staff. 'This is MY territory! I was here first! The blight, the Crown, none of it matters HERE!' They seem more frightened than threatening."},
        {"name": "Mad Prophet",
         "narrative": "A wild-eyed man in tattered robes points at you. 'You! You're in the spiral! Can't you feel it turning? The Crown sees ALL of us turning, turning, turning...' He trails off, muttering."},
        {"name": "Exiled Noble",
         "narrative": "A figure in stained but once-fine clothing regards you with haughty disdain. 'You may pass. I suppose even these lands must suffer visitors. Don't touch anything. Especially not the rocks — I've organized them.'"},
    ]),

    _e(19, "Ghost Echo", "npc", _ALL, ("WATER",), [
        {"name": "Sobbing Specter",
         "narrative": "A translucent figure kneels on the ground, shoulders heaving with silent sobs. When you approach, it looks up with empty eyes and mouths words you cannot hear. Then it fades like morning mist."},
        {"name": "Repeating Phantom Soldier",
         "narrative": "A ghostly soldier marches past in an endless patrol, armor rattling silently. Every thirty seconds, it loops back to the same starting point and begins again. It doesn't seem to know you're here."},
        {"name": "Lingering Death Memory",
         "narrative": "For a heartbeat, you see it — a figure falling, a blade flash, a spray of something dark. Then it's gone. Just an afterimage burned into this place by violence."},
    ]),

    _e(20, "Rival Adventurers", "npc", _LAND_ONLY, ("WATER", "WALL", "MOUNTAIN"), [
        {"name": "Competing Treasure Hunters",
         "narrative": "A trio of armed figures eye you suspiciously over a half-unrolled map. 'We were here first,' their leader says flatly. 'Whatever's in these parts, we've got first claim.'"},
        {"name": "Hostile Sellswords",
         "narrative": "Three mercenaries block the path, hands on weapons. 'Toll road,' the biggest one says. 'Ten gold to pass, or find another way.' Their smiles don't reach their eyes."},
        {"name": "Friendly But Wary Party",
         "narrative": "A group of adventurers waves cautiously. 'Good to see living faces,' their scout calls. 'Watch your step ahead — we found pit traps. And something was following us. We lost it. Maybe.'"},
    ]),

    _e(21, "Wounded Creature", "npc", _ALL, _NO_WATER_WALL, [
        {"name": "Limping Dire Wolf",
         "narrative": "A massive wolf lies panting in the undergrowth, one leg twisted at a wrong angle. It watches you with intelligent, pain-filled eyes but makes no move to attack. A rusted trap is clamped around its paw.",
         "choices": (
             {"label": "Free the wolf", "text": "You pry the trap open. The wolf yelps, then licks your hand once before limping into the undergrowth. As you continue, you notice it following at a distance — watching over you.",
              "consequences": {"flags": {"freed_wolf": True}}},
             {"label": "Put it out of its misery", "text": "A quick, clean strike. The wolf's eyes close peacefully. It was suffering. This was mercy."},
             {"label": "Leave it", "text": "Nature is cruel, and you can't save everything. The wolf watches you go with those intelligent eyes."},
         )},
        {"name": "Poisoned Giant Spider",
         "narrative": "An enormous spider curls against a rock, its legs twitching feebly. Green ichor oozes from a wound on its abdomen. Even dying, it's unsettling — but also pitiable.",
         "choices": (
             {"label": "Examine the wound", "text": "The poison is alchemical — not natural. Someone did this deliberately. The spider's silk glands are intact and valuable.",
              "reward": {"type": "loot", "name": "Spider silk glands", "gold_value": 8}},
             {"label": "Move on", "text": "A dying spider is still a spider. You give it wide berth and continue."},
         )},
        {"name": "Chained Beast",
         "narrative": "Heavy chains anchor a creature to an iron stake driven into the ground. The creature — something between a hound and a lizard — has worn the ground bare in a circle around its tether. Its water bowl is empty.",
         "choices": (
             {"label": "Free the creature", "text": "You break the chain. The creature shakes itself, sniffs your hand, and bounds away into the wild. Free at last."},
             {"label": "Give it water", "text": "You fill the bowl from your waterskin. The creature drinks desperately, then looks at you with something like gratitude. You can't free it — the chains are too strong. But at least it won't die thirsty."},
             {"label": "Leave it", "text": "Someone chained it for a reason. Best not to interfere with things you don't understand."},
         )},
    ]),

    _e(22, "Child in Danger", "npc", _LAND_ONLY, ("WATER", "WALL", "MOUNTAIN"), [
        {"name": "Lost Orphan",
         "narrative": "A small child sits in the dirt, knees pulled to chest, eyes red from crying. 'I can't find the road back. Everything looks wrong now. The trees moved.' They look up hopefully. 'Are you here to help?'",
         "choices": (
             {"label": "Help them find the road", "text": "You take the child's hand and guide them to the nearest safe path. 'Go straight until you reach the crossroads, then turn toward the smoke — that's Millhaven.' The child nods bravely and runs.",
              "consequences": {"flags": {"helped_child": True}}},
             {"label": "Give them food and directions", "text": "You hand over a ration pack and point toward Millhaven. The child clutches the food and nods. 'Thank you, mister.' Small legs carry them away with renewed purpose."},
         )},
        {"name": "Kidnapped Village Kid",
         "narrative": "Muffled sounds come from behind a locked door. A child's voice: 'Hello? Is someone there? Please — the bad men left but they locked the door and I can't get out!'",
         "choices": (
             {"label": "Break down the door", "text": "The lock is old and gives way with effort. A terrified child rushes out and clings to your leg. 'The bad men went toward the swamp. There were three of them.' Useful intelligence, from the smallest source.",
              "consequences": {"flags": {"helped_child": True}}},
             {"label": "Pick the lock", "text": "You work the mechanism carefully. The door swings open to reveal a small, brave face. 'I knew someone would come,' the child says firmly, as if they'd never doubted."},
         )},
        {"name": "Feral Urchin",
         "narrative": "Quick movement in the corner of your eye — a small figure, barefoot and filthy, watching you from the shadows. When you look directly, they bolt. But they left something behind: a crude drawing of a house.",
         "choices": (
             {"label": "Leave food where they were hiding", "text": "You place a ration pack where the urchin was crouching and step back. After a minute, a small hand darts out, snatches it, and disappears. A start."},
             {"label": "Examine the drawing", "text": "The drawing shows a house with people inside — stick figures with smiles. A family, maybe. One the urchin lost, or one they dream of having.",
              "reward": {"type": "info", "text": "The drawing shows a building that might be a specific house in Millhaven — possibly the urchin's former home."}},
         )},
    ]),

    _e(23, "Patrolling Guard", "npc", _ALL, ("WATER",), [
        {"name": "Corrupt Watchman",
         "narrative": "A guard in dented armor leans against a post, picking his teeth. 'Nothing to see here,' he says without looking up. 'Move along. Unless you've got coin — then maybe I saw something interesting.'"},
        {"name": "Diligent Sentry",
         "narrative": "A lone guard snaps to attention as you approach. 'Halt! State your —' She pauses, deflates. 'Actually, I don't even know who I'm guarding for anymore. The captain's gone. Everyone's gone.'"},
        {"name": "Undead Patrol",
         "narrative": "Two skeletal figures in rusted armor march in lockstep, empty eye sockets staring ahead. They follow a patrol route that no longer makes sense — through collapsed walls, over rubble. They don't notice you."},
    ]),

    _e(24, "Trapped Prisoner", "npc", _ALL, _NO_WATER_WALL, [
        {"name": "Caged Merchant",
         "narrative": "A wooden cage hangs from a tree branch, its occupant a disheveled merchant. 'Bandits! Three days ago! They took my wagon and left me here as a JOKE!' He rattles the bars furiously."},
        {"name": "Bound Cultist",
         "narrative": "A robed figure sits bound to a post, surprisingly calm. 'Ah, visitors. My former brethren left me here when I questioned the ritual. I can tell you things. Useful things. If you cut these ropes.'"},
        {"name": "Imprisoned Fey",
         "narrative": "An iron cage glows faintly where a small, luminous creature presses against the bars. Its wings flutter weakly. 'Cold iron burns,' it whispers. 'Free me and I'll owe you a favor. We always pay our debts.'"},
    ]),

    _e(25, "Bard's Performance", "npc", _LAND_ONLY, ("WATER", "WALL", "MOUNTAIN"), [
        {"name": "Eerie Lullaby in the Dark",
         "narrative": "A soft voice drifts from somewhere ahead, singing a lullaby in an unfamiliar language. The melody is beautiful but wrong — the intervals don't resolve, leaving you tense and expectant. The singer is nowhere to be seen."},
        {"name": "Campfire Ballad",
         "narrative": "A lone bard sits by a small fire, strumming a battered lute. 'The Ballad of the Shattered Crown,' he announces to no audience. 'Verse forty-seven. Nobody's heard the whole thing. I haven't finished writing it.'"},
        {"name": "Coded Song",
         "narrative": "A woman hums while working on something you can't see. The melody is simple, repetitive — until you notice the pattern. Three long notes, three short, three long. A distress signal, hidden in a tune.",
         "skill_check": {"skill": "Insight", "dc": 13},
         "success_text": "The song is a cipher. The intervals correspond to letters: 'VAULT BENEATH MILL.' Someone is trying to pass information without being overheard."},
    ]),

    _e(26, "Arguing NPCs", "npc", _LAND_ONLY, ("WATER", "WALL", "MOUNTAIN"), [
        {"name": "Feuding Siblings",
         "narrative": "Two people who look remarkably alike are screaming at each other. 'Father's sword goes to ME!' 'You can't even LIFT it!' They notice you and both turn. 'YOU. Settle this.'"},
        {"name": "Contract Dispute",
         "narrative": "A merchant and a hired guard face off, a crumpled contract between them. 'You said ESCORT, not COMBAT!' the guard shouts. 'Same thing in these lands!' the merchant fires back."},
        {"name": "Blame Over a Dead Companion",
         "narrative": "Two survivors huddle near a covered body, voices raw. 'You said the path was clear.' 'I said I THOUGHT it was clear.' Grief and guilt twist their faces in equal measure."},
    ]),

    _e(27, "Fleeing Refugee", "npc", _LAND_ONLY, ("WATER", "WALL", "MOUNTAIN"), [
        {"name": "Burned-Out Farmer",
         "narrative": "A man pushes a wheelbarrow containing everything he owns — which isn't much. 'Don't go that way,' he says without stopping. 'The fields are burning. Everything's burning. Nothing to go back to.'"},
        {"name": "Escaped Slave",
         "narrative": "A woman with raw wrists stumbles past, barely registering your presence. She moves with desperate urgency, glancing over her shoulder every few steps. The marks on her arms speak for themselves."},
        {"name": "Deserting Soldier",
         "narrative": "A soldier in mismatched armor hurries by, helmet under one arm. 'Don't try to stop me. I've seen what's coming. The line won't hold. Run if you're smart.' He doesn't wait for a response."},
    ]),

    _e(28, "Suspicious Stranger", "npc", _ALL, _NO_WATER_WALL, [
        {"name": "Cloaked Figure at Crossroads",
         "narrative": "A figure in a deep hood stands perfectly still at the intersection, facing you. They don't speak, don't move, don't even seem to breathe. When you blink, they're facing a different direction.",
         "skill_check": {"skill": "Insight", "dc": 14},
         "success_text": "Something about their posture is wrong — the proportions are off. Whatever is under that cloak isn't quite human-shaped."},
        {"name": "Too-Friendly Innkeeper",
         "narrative": "'Come in, come in! Rest your feet! Everything's on the house!' The jovial man gestures at an empty ruin with no roof and no walls. He seems genuinely to believe he's running a tavern."},
        {"name": "Silent Observer",
         "narrative": "Someone is watching from behind a low wall — you catch a flicker of movement, a glint of reflected light. When you investigate, you find only a warm patch on the stone where they sat."},
    ]),

    _e(29, "Animal Companion", "npc", _OUTDOOR, ("WATER",), [
        {"name": "Loyal Stray Dog",
         "narrative": "A scruffy dog with mismatched ears trots up, tail wagging hopefully. It's thin but alert, and it nudges your hand with a cold nose. Around its neck, a frayed collar reads 'BISCUIT.'"},
        {"name": "Wounded Hawk",
         "narrative": "A hawk perches on a low branch, one wing hanging at an odd angle. It watches you with fierce intelligence, clicking its beak. There's something tied to its leg — a tiny scroll case."},
        {"name": "Curious Fox Kit",
         "narrative": "A small red fox sits in the middle of the path, head tilted, watching you with open curiosity. It doesn't flee when you approach — instead it yips once, turns, and trots a few steps before looking back expectantly."},
    ]),

    _e(30, "Dying NPC", "npc", _ALL, _NO_WATER_WALL, [
        {"name": "Last Words of a Knight",
         "narrative": "A knight in battered plate slumps against a wall, hand pressed to a wound that's clearly fatal. 'Tell... tell the captain the south road is lost. The dead hold it now.' A final breath rattles out."},
        {"name": "Poisoned Spy with Intel",
         "narrative": "A figure in dark clothes lies curled on the ground, skin an unhealthy grey. 'Torven... the guild... shipment at the old mill...' They press a crumpled paper into your hand before going still.",
         "reward": {"type": "info", "text": "The note contains delivery schedules for supplies sent to the citadel — dates, quantities, and a route through the southern pass."},
         "success_consequences": {"flags": {"has_spy_intel": True}}},
        {"name": "Cursed Villager Begging for Help",
         "narrative": "A villager lies writhing, dark veins spreading visibly across their skin. 'It touched me — the green light — please, you have to cut it out before it reaches my heart!' Their eyes are wild with pain and terror."},
    ]),

    # ═══════════════════════════════════════════════════════════════
    #  ENVIRONMENTAL HAZARDS  (31–45)
    # ═══════════════════════════════════════════════════════════════

    _e(31, "Poison Gas", "hazard", _ALL, ("WALL",), [
        {"name": "Sulfurous Vent",
         "narrative": "A crack in the ground hisses with yellow-green gas that smells of rotten eggs. The vegetation around the vent is dead and blackened. Breathing here stings your lungs.",
         "skill_check": {"skill": "Constitution", "dc": 12},
         "success_text": "You hold your breath and push through the fumes without inhaling.",
         "fail_text": "The gas burns your lungs. You stumble clear, coughing and retching.",
         "fail_consequences": {"damage": "1d4", "damage_type": "poison"}},
        {"name": "Spore Cloud",
         "narrative": "A thick cloud of green-grey spores hangs in the air, barely moving. The mushrooms responsible are enormous — waist-high and bulging. Disturbing them would be unwise.",
         "skill_check": {"skill": "Constitution", "dc": 11},
         "success_text": "You skirt the cloud carefully, holding a cloth over your face.",
         "fail_text": "You inhale a lungful of spores. Your vision swims and your stomach lurches.",
         "fail_consequences": {"damage": "1d4", "damage_type": "poison", "condition": "poisoned"}},
        {"name": "Alchemical Leak",
         "narrative": "Broken glass crunches underfoot near an overturned cart. Acrid fumes rise from a spreading pool of mixed chemicals. Whatever the alchemist was transporting, it wasn't meant to combine.",
         "skill_check": {"skill": "Dexterity", "dc": 12},
         "success_text": "You step clear before the chemicals splash. Among the wreckage, a single intact vial remains.",
         "fail_text": "The chemicals splash your boots. The burn is immediate and unpleasant.",
         "fail_consequences": {"damage": "1d6", "damage_type": "acid"}},
    ]),

    _e(32, "Pit Trap", "hazard", _ALL, ("WATER", "WALL"), [
        {"name": "Spike-Lined Pit",
         "narrative": "The ground gives way underfoot — only your reflexes save you from a pit lined with sharpened stakes. Someone went to considerable effort to build this. The stakes are freshly sharpened.",
         "skill_check": {"skill": "Perception", "dc": 13},
         "success_text": "You spot the telltale signs just in time — a slight depression in the ground and disturbed soil. The trap can be safely skirted.",
         "fail_text": "You step on the false floor. The fall is short but the stakes are sharp.",
         "fail_consequences": {"damage": "1d6", "damage_type": "piercing"}},
        {"name": "Illusory Floor",
         "narrative": "The floor ahead looks solid — flagstones, dust, cracks. But a tossed pebble passes right through the surface and clatters somewhere far below. A glamour, hiding a deep shaft.",
         "skill_check": {"skill": "Investigation", "dc": 13},
         "success_text": "You test the ground ahead and find the illusion. A narrow real ledge runs along the wall.",
         "fail_text": "You step onto nothing. The fall is terrifying, though you catch yourself on a ledge.",
         "fail_consequences": {"damage": "1d8", "damage_type": "bludgeoning"}},
        {"name": "Collapsing Sinkhole",
         "narrative": "A circular depression in the ground is slowly widening, dirt crumbling inward at the edges. The center has already collapsed into darkness. The ground groans ominously when you step close.",
         "skill_check": {"skill": "Dexterity", "dc": 12},
         "success_text": "You leap back as the edge crumbles. Safe, but that was close.",
         "fail_text": "The ground gives way under you. You slide into the pit before catching the rim.",
         "fail_consequences": {"damage": "1d6", "damage_type": "bludgeoning"}},
    ]),

    _e(33, "Falling Debris", "hazard", _ALL, ("WATER",), [
        {"name": "Loose Stalactites",
         "narrative": "The ceiling is thick with stalactites, many cracked at their bases. A few have already fallen, shattering on the floor below. Moving through here feels like walking through a minefield — but above you.",
         "skill_check": {"skill": "Dexterity", "dc": 12},
         "success_text": "You weave through the danger zone. Nothing falls.",
         "fail_text": "A stalactite cracks loose and clips your shoulder.",
         "fail_consequences": {"damage": "1d6", "damage_type": "bludgeoning"}},
        {"name": "Crumbling Ceiling",
         "narrative": "Dust and small stones rain down with every vibration. The ceiling beams — where they still exist — are rotted through. Speak softly here, and step lightly.",
         "skill_check": {"skill": "Dexterity", "dc": 11},
         "success_text": "You move through quickly and quietly. The ceiling holds.",
         "fail_text": "A beam cracks and debris rains down on you.",
         "fail_consequences": {"damage": "1d4", "damage_type": "bludgeoning"}},
        {"name": "Tumbling Boulders",
         "narrative": "The hillside above is a jumble of loose rock, barely held in place by gravity and habit. A strong wind or a careless step could bring tonnes of stone cascading down.",
         "skill_check": {"skill": "Dexterity", "dc": 13},
         "success_text": "You pick your way through without disturbing anything.",
         "fail_text": "A stone shifts under your foot, triggering a small cascade. One catches your leg.",
         "fail_consequences": {"damage": "1d8", "damage_type": "bludgeoning"}},
    ]),

    _e(34, "Magical Anomaly", "hazard", _ALL, (), [
        {"name": "Wild Magic Surge Zone",
         "narrative": "The air crackles with uncontrolled magical energy. Colors shift without light sources. Small objects float briefly before dropping. Your skin tingles as stray magic discharges around you.",
         "skill_check": {"skill": "Arcana", "dc": 13},
         "success_text": "You recognize the discharge pattern and time your passage between surges.",
         "fail_text": "A wild surge catches you. Energy crackles through your body.",
         "fail_consequences": {"damage": "1d6", "damage_type": "force"}},
        {"name": "Gravity Reversal Pocket",
         "narrative": "A section of ground is littered with debris that's fallen... upward. Pebbles hover at chest height. Dust drifts toward the sky. Stepping into the zone would be an interesting mistake.",
         "skill_check": {"skill": "Arcana", "dc": 12},
         "success_text": "You map the pocket's boundary and walk around it safely.",
         "fail_text": "You drift upward, then crash back down when the effect sputters.",
         "fail_consequences": {"damage": "1d6", "damage_type": "bludgeoning"}},
        {"name": "Time-Stutter Field",
         "narrative": "A bird hangs frozen mid-flight above you. Raindrops hover in place. Then everything snaps forward in a burst of motion before freezing again. Time itself hiccups here.",
         "skill_check": {"skill": "Arcana", "dc": 14},
         "success_text": "The ley line beneath this spot is damaged — magical energy is leaking through a fracture in the weave. It's not dangerous yet, but the fracture is growing.",
         "fail_text": "You're caught in a time-stutter. A few seconds pass for you, but your body aches as if hours have gone by.",
         "fail_consequences": {"damage": "1d4", "damage_type": "force", "condition": "exhausted"}},
        {"name": "Anti-Magic Dead Zone",
         "narrative": "Your magical equipment goes quiet. Enchantments dim. The air feels flat and dead, scrubbed of any arcane resonance. Whatever happened here burned the magic out completely.",
         "skill_check": {"skill": "Arcana", "dc": 11},
         "success_text": "You identify the dead zone's boundary. Your enchantments resume once you step clear.",
         "fail_text": "You linger too long. Something vital flickers in your gear."},
    ]),

    _e(35, "Extreme Temperature", "hazard", _ALL, ("WALL",), [
        {"name": "Scorching Steam Vent",
         "narrative": "A jet of superheated steam erupts from a crack in the ground at irregular intervals. The rocks around it are stained white with mineral deposits. The heat is blistering.",
         "skill_check": {"skill": "Dexterity", "dc": 12},
         "success_text": "You time the eruption pattern and dash through between blasts.",
         "fail_text": "Steam scalds your exposed skin.",
         "fail_consequences": {"damage": "1d6", "damage_type": "fire"}},
        {"name": "Freezing Draft",
         "narrative": "An inexplicable wave of arctic cold flows through this area like an invisible river. Frost forms on your armor and your breath hangs in the air, even as the surrounding area remains temperate.",
         "skill_check": {"skill": "Constitution", "dc": 11},
         "success_text": "You push through quickly. The cold stings but does no lasting harm.",
         "fail_text": "The cold bites deep. Your fingers go numb and your joints stiffen.",
         "fail_consequences": {"damage": "1d4", "damage_type": "cold"}},
        {"name": "Radiant Heat Bloom",
         "narrative": "The ground radiates heat — not from any visible source, but from deep below. The stones are warm to the touch and the air shimmers. It would be pleasant if it weren't so unsettling.",
         "skill_check": {"skill": "Constitution", "dc": 10},
         "success_text": "The warmth is manageable. You pass through quickly.",
         "fail_text": "The heat saps your energy more than expected.",
         "fail_consequences": {"damage": "1d4", "damage_type": "fire"}},
    ]),

    _e(36, "Swarm", "hazard", _ALL, _NO_WATER_WALL, [
        {"name": "Rat Swarm",
         "narrative": "A carpet of grey-brown fur flows across the ground — hundreds of rats, moving with eerie coordination. They part around your feet without touching you, but the sound of their claws on stone is deeply unpleasant.",
         "skill_check": {"skill": "Dexterity", "dc": 11},
         "success_text": "You stamp and shout. The rats scatter, flowing around you harmlessly.",
         "fail_text": "Several rats bite your ankles before the swarm passes.",
         "fail_consequences": {"damage": "1d4", "damage_type": "piercing"}},
        {"name": "Beetle Carpet",
         "narrative": "The floor is alive with shiny black beetles, their shells clicking as they crawl over each other in a seething mass. They avoid the light, pulling back from your torch like a living shadow.",
         "skill_check": {"skill": "Nature", "dc": 10},
         "success_text": "You raise your light source. The beetles retreat, clearing a path.",
         "fail_text": "You step into the mass. The beetles crawl up your legs, biting."},
        {"name": "Bat Cloud",
         "narrative": "With a rush of leathery wings, a storm of bats erupts from above. They swirl around you in a screaming vortex before streaming away into the dark. The silence afterward feels deafening.",
         "skill_check": {"skill": "Dexterity", "dc": 11},
         "success_text": "You duck and cover. The bats stream past without touching you.",
         "fail_text": "Claws and wings batter your face. Superficial cuts, but startling.",
         "fail_consequences": {"damage": "1d4", "damage_type": "slashing"}},
        {"name": "Centipede Tide",
         "narrative": "Finger-long centipedes pour from a crack in the wall in a chittering stream. They flow across the floor in a living river, then vanish into another crack. The whole event takes thirty seconds. It feels like an hour.",
         "skill_check": {"skill": "Constitution", "dc": 11},
         "success_text": "You freeze and let them pass. Not one touches you.",
         "fail_text": "Several centipedes climb your legs and sting before you can brush them off.",
         "fail_consequences": {"damage": "1d4", "damage_type": "poison"}},
    ]),

    _e(37, "Quicksand", "hazard", ("SAND", "SWAMP"), (), [
        {"name": "Dry Sand Trap",
         "narrative": "The sand here is treacherously fine and deep. Your boot sinks to the ankle before finding purchase. Struggling only makes it worse. The trick is slow, deliberate movement.",
         "skill_check": {"skill": "Athletics", "dc": 12},
         "success_text": "Slow, steady pulls free your legs. You find solid ground.",
         "fail_text": "You sink to your knees before thrashing free, exhausted.",
         "fail_consequences": {"damage": "1d4", "damage_type": "bludgeoning"}},
        {"name": "Bog Sinkhole",
         "narrative": "What looks like solid ground is actually a thin crust over deep, sucking mud. A branch thrust into the surface disappears to its full length without hitting bottom.",
         "skill_check": {"skill": "Perception", "dc": 12},
         "success_text": "You test the ground with a stick and find the solid path around.",
         "fail_text": "The crust breaks. You plunge waist-deep before grabbing a root.",
         "fail_consequences": {"damage": "1d6", "damage_type": "bludgeoning"}},
        {"name": "Loose Gravel Slide",
         "narrative": "The slope is covered in loose gravel that shifts underfoot like a living thing. Every step sends cascades of small stones rattling downhill. Climbing this would be a battle against gravity.",
         "skill_check": {"skill": "Athletics", "dc": 12},
         "success_text": "You find the stable stones and pick your way across.",
         "fail_text": "The gravel gives way. You slide ten feet, scraping hands and knees.",
         "fail_consequences": {"damage": "1d4", "damage_type": "bludgeoning"}},
    ]),

    _e(38, "Flooding", "hazard", ("FLOOR", "SWAMP"), (), [
        {"name": "Rising Water Level",
         "narrative": "Water is seeping in from somewhere — under the walls, through the floor, rising slowly but steadily. It's at ankle depth now. The source is unclear, but the direction is only up.",
         "skill_check": {"skill": "Athletics", "dc": 11},
         "success_text": "You wade through quickly before the level rises further.",
         "fail_text": "The current is stronger than it looks. You're knocked off balance and swallow water.",
         "fail_consequences": {"damage": "1d4", "damage_type": "bludgeoning"}},
        {"name": "Burst Dam Trickle",
         "narrative": "A thin stream of water spurts from a crack in the wall with surprising force. The stone around the crack is already eroding. This trickle will be a flood before long.",
         "skill_check": {"skill": "Dexterity", "dc": 11},
         "success_text": "You pass the weak point before it gives way.",
         "fail_text": "The wall bursts as you pass. Cold water slams into you.",
         "fail_consequences": {"damage": "1d6", "damage_type": "bludgeoning"}},
        {"name": "Tide Pool Surge",
         "narrative": "A pool in the corner of the room surges periodically, water level rising and falling in a rhythm that matches no natural tide. Each surge brings more water in than it takes back out.",
         "skill_check": {"skill": "Perception", "dc": 10},
         "success_text": "You time the surges and pass between them.",
         "fail_text": "A surge catches you mid-stride. The cold water soaks you through."},
    ]),

    _e(39, "Web-Choked Area", "hazard", _ALL, _NO_WATER_WALL, [
        {"name": "Thick Spider Silk",
         "narrative": "Gossamer threads fill the space between walls, ceiling to floor. The silk is incredibly strong — tugging on it sends vibrations running in every direction. Something, somewhere, just felt that.",
         "skill_check": {"skill": "Dexterity", "dc": 12},
         "success_text": "You slip between the threads without touching a single one.",
         "fail_text": "You brush a thread. The web vibrates. Something stirs in the darkness above.",
         "fail_consequences": {"condition": "restrained"}},
        {"name": "Sticky Fungal Threads",
         "narrative": "Pale, sticky threads hang from every surface like fibrous curtains. They cling to skin and gear, leaving a faintly luminescent residue. The threads connect to bloated fungal bodies overhead.",
         "skill_check": {"skill": "Dexterity", "dc": 11},
         "success_text": "You weave through without touching the threads.",
         "fail_text": "The threads stick to your armor, slowing you and leaving a burning residue.",
         "fail_consequences": {"damage": "1d4", "damage_type": "acid"}},
        {"name": "Enchanted Binding Webs",
         "narrative": "These webs glow with a faint arcane light. Where they touch stone, the stone is smooth and warm. They were spun deliberately, in geometric patterns — not by an animal, but by something that understands magic.",
         "skill_check": {"skill": "Arcana", "dc": 13},
         "success_text": "You find the pattern's gap — an intentional opening in the design.",
         "fail_text": "The webs tighten around you. Arcane energy crackles painfully.",
         "fail_consequences": {"damage": "1d6", "damage_type": "force"}},
    ]),

    _e(40, "Unstable Magic Item", "hazard", _ALL, _NO_WATER_WALL, [
        {"name": "Leaking Wand",
         "narrative": "A wand lies on the ground, its tip dripping sparks of blue-white energy. Each spark scorches the ground where it lands. The wand hums with barely contained power — pick it up at your own risk.",
         "skill_check": {"skill": "Arcana", "dc": 13},
         "success_text": "You carefully stabilize the wand's output. It's drained but safe to carry.",
         "fail_text": "The wand discharges as you reach for it. Energy sears your hand.",
         "fail_consequences": {"damage": "1d8", "damage_type": "force"}},
        {"name": "Cracked Staff Sparking",
         "narrative": "A broken staff crackles with arcs of electricity, the fracture exposing a core of raw magical crystal. The air smells of ozone and burned wood. Even approaching it makes your teeth ache.",
         "skill_check": {"skill": "Arcana", "dc": 13},
         "success_text": "You extract the crystal core safely. It pulses with contained energy.",
         "fail_text": "An arc of electricity leaps from the staff to your armor.",
         "fail_consequences": {"damage": "1d8", "damage_type": "lightning"}},
        {"name": "Overcharged Runestone",
         "narrative": "A flat stone etched with glowing runes sits on a pedestal, vibrating hard enough to rattle against the surface. The runes are so bright they leave afterimages. This thing is about to blow — or has been on the verge for centuries.",
         "skill_check": {"skill": "Arcana", "dc": 14},
         "success_text": "You trace a grounding rune in the air. The vibration slows and stabilizes.",
         "fail_text": "The runestone detonates. A shockwave of raw magic throws you backward.",
         "fail_consequences": {"damage": "2d6", "damage_type": "force"}},
    ]),

    _e(41, "Rockslide", "hazard", ("MOUNTAIN", "FLOOR"), (), [
        {"name": "Triggered Avalanche",
         "narrative": "Loose stones shift underfoot, and a low rumble builds from above. Small rocks bounce past you, heralds of something larger. The path is passable — quickly.",
         "skill_check": {"skill": "Dexterity", "dc": 13},
         "success_text": "You sprint through. Boulders crash behind you, blocking the path.",
         "fail_text": "A rock catches your back. You're knocked flat but manage to crawl clear.",
         "fail_consequences": {"damage": "1d8", "damage_type": "bludgeoning"}},
        {"name": "Slow Gravel Cascade",
         "narrative": "A steady stream of gravel pours down the slope like sand through an hourglass. It's been going for a while — the pile at the bottom is enormous. The source seems inexhaustible.",
         "skill_check": {"skill": "Dexterity", "dc": 11},
         "success_text": "You time your crossing between cascades.",
         "fail_text": "Gravel peppers you like hail. Minor cuts, major annoyance.",
         "fail_consequences": {"damage": "1d4", "damage_type": "bludgeoning"}},
        {"name": "Explosive Shale Collapse",
         "narrative": "A section of the cliff face has sheared away, leaving a fresh scar of raw rock. Boulders the size of wagons litter the path. The collapse was recent — dust still hangs in the air.",
         "skill_check": {"skill": "Perception", "dc": 12},
         "success_text": "You spot the unstable section and route around it.",
         "fail_text": "Another section gives way. Sharp shale fragments cut deep.",
         "fail_consequences": {"damage": "1d8", "damage_type": "slashing"}},
    ]),

    _e(42, "Carnivorous Plant", "hazard", ("GRASS", "SWAMP"), (), [
        {"name": "Snapping Vine",
         "narrative": "A thick green vine lies across the path, seemingly harmless. When a beetle walks across it, the vine snaps closed like a jaw, crushing the insect. It relaxes slowly, waiting for the next victim.",
         "skill_check": {"skill": "Nature", "dc": 12},
         "success_text": "You recognize the trigger mechanism and step over the vine carefully.",
         "fail_text": "The vine snaps around your ankle. Thorns puncture your boot.",
         "fail_consequences": {"damage": "1d4", "damage_type": "piercing"}},
        {"name": "Luring Blossom",
         "narrative": "An impossibly beautiful flower blooms here, its petals shifting through colors you can't quite name. A sweet scent pulls at you like a physical force. Scattered around its base: bones of small animals.",
         "skill_check": {"skill": "Wisdom", "dc": 13},
         "success_text": "You resist the compulsion and keep your distance.",
         "fail_text": "You reach for the flower. A hidden tendril lashes your arm.",
         "fail_consequences": {"damage": "1d6", "damage_type": "poison", "condition": "poisoned"}},
        {"name": "Acid-Dripping Pitcher",
         "narrative": "Enormous pitcher plants — shoulder-height — line the path, their open mouths glistening with viscous fluid. The acid inside has dissolved things far larger than insects. A boot sole floats in one.",
         "skill_check": {"skill": "Dexterity", "dc": 12},
         "success_text": "You navigate past the pitchers without incident.",
         "fail_text": "A pitcher tilts as you brush past. Acid splashes your arm.",
         "fail_consequences": {"damage": "1d6", "damage_type": "acid"}},
    ]),

    _e(43, "Cursed Ground", "hazard", _ALL, _NO_WATER_WALL, [
        {"name": "Necrotic Soil",
         "narrative": "The earth here is black and wet without rain. Nothing grows. Nothing decays either — fallen leaves lie perfectly preserved on the dead soil, their colors impossibly vivid against the black.",
         "skill_check": {"skill": "Wisdom", "dc": 12},
         "success_text": "You feel the wrongness and skirt the area entirely.",
         "fail_text": "The necrotic energy seeps through your boots, chilling your bones.",
         "fail_consequences": {"damage": "1d4", "damage_type": "necrotic"}},
        {"name": "Unhallowed Earth",
         "narrative": "A chill emanates from the ground itself. Grass withers at the boundary, creating a perfect circle of bare earth. Standing in it makes your stomach turn and your vision swim at the edges.",
         "skill_check": {"skill": "Constitution", "dc": 13},
         "success_text": "You hold your nerve and pass through quickly.",
         "fail_text": "Dread washes over you. Your strength falters.",
         "fail_consequences": {"damage": "1d4", "damage_type": "necrotic", "condition": "frightened"}},
        {"name": "Blighted Root Network",
         "narrative": "Thick, dark roots push through the surface, pulsing faintly with green light. They form a web across the ground, and where they touch other plants, those plants wither and blacken. The corruption spreading in real time.",
         "skill_check": {"skill": "Nature", "dc": 12},
         "success_text": "You find gaps in the root network and step carefully through.",
         "fail_text": "A root wraps around your ankle. Corruption burns where it touches.",
         "fail_consequences": {"damage": "1d6", "damage_type": "necrotic"}},
    ]),

    _e(44, "Lightning Hazard", "hazard", _ALL, (), [
        {"name": "Charged Crystal Formation",
         "narrative": "A cluster of crystals crackles with static electricity. Blue-white arcs jump between the largest stones, leaving the air thick with ozone. Your hair stands on end from ten feet away.",
         "skill_check": {"skill": "Dexterity", "dc": 13},
         "success_text": "You time the discharges and dash through between arcs.",
         "fail_text": "An arc catches you. Every muscle seizes for an agonizing instant.",
         "fail_consequences": {"damage": "1d8", "damage_type": "lightning"}},
        {"name": "Storm-Conductor Pillar",
         "narrative": "A tall metal rod — clearly artificial — rises from the ground, its tip blackened by repeated lightning strikes. The ground around it is fused to glass. During storms, this must be spectacular. And lethal.",
         "skill_check": {"skill": "Perception", "dc": 12},
         "success_text": "You stay low and away from the pillar. The charge builds but doesn't strike.",
         "fail_text": "You get too close. A discharge jumps from the pillar to your armor.",
         "fail_consequences": {"damage": "1d8", "damage_type": "lightning"}},
        {"name": "Arc-Jumping Puddles",
         "narrative": "Standing water fills shallow depressions in the floor. Every few seconds, an electrical arc jumps from puddle to puddle in a crackling chain. Stepping in one would complete a very unfortunate circuit.",
         "skill_check": {"skill": "Dexterity", "dc": 12},
         "success_text": "You hop between dry spots, avoiding every puddle.",
         "fail_text": "Your foot splashes into a charged puddle. The shock jolts through you.",
         "fail_consequences": {"damage": "1d6", "damage_type": "lightning"}},
    ]),

    _e(45, "Miasma", "hazard", _ALL, ("WALL",), [
        {"name": "Hallucinogenic Mist",
         "narrative": "A low, pinkish fog clings to the ground. Within it, shadows move that don't correspond to anything real. Spending too long here would be unwise — the shapes are becoming more convincing.",
         "skill_check": {"skill": "Wisdom", "dc": 12},
         "success_text": "You recognize the signs of enchanted fog — a failed ward leaking residual illusion magic. Holding your breath and moving quickly is the safest approach.",
         "fail_text": "The hallucinations take hold. You stumble, disoriented.",
         "fail_consequences": {"damage": "1d4", "damage_type": "psychic", "condition": "frightened"}},
        {"name": "Exhaustion Fog",
         "narrative": "A grey mist saps your energy like a physical weight. Each step takes more effort than the last. Your eyelids droop. The temptation to just sit down and rest is overwhelming.",
         "skill_check": {"skill": "Constitution", "dc": 12},
         "success_text": "You grit your teeth and push through. The fog thins behind you.",
         "fail_text": "The fog drains you. Your limbs feel like lead.",
         "fail_consequences": {"condition": "exhausted"}},
        {"name": "Memory-Draining Haze",
         "narrative": "A translucent haze shimmers in the air. You walk through it and — what were you doing? You're standing in an unfamiliar spot with no memory of walking here. Your gear is untouched, but minutes are missing.",
         "skill_check": {"skill": "Wisdom", "dc": 13},
         "success_text": "You hold a clear thought in your mind and walk through. The haze tries to pull it away but fails.",
         "fail_text": "Minutes vanish. You feel weakened, as though something was taken from you.",
         "fail_consequences": {"damage": "1d4", "damage_type": "psychic"}},
    ]),

    # ═══════════════════════════════════════════════════════════════
    #  LOOT & TREASURE  (46–60)
    # ═══════════════════════════════════════════════════════════════

    _e(46, "Coin Stash", "loot", _ALL, _NO_WATER_WALL, [
        {"name": "Scattered Coppers",
         "narrative": "A handful of copper coins lies scattered across the ground, as if tossed from a torn purse. Most are tarnished beyond recognition, but a few still catch the light.",
         "reward": {"type": "loot", "name": "Scattered coppers", "gold_value": 2}},
        {"name": "Pouch of Silver",
         "narrative": "Tucked under a loose stone, a small leather pouch clinks promisingly. Inside: a dozen silver coins, still bright. Someone hid this and never came back for it.",
         "skill_check": {"skill": "Investigation", "dc": 10},
         "success_text": "The pouch has an embossed guild mark — Torven's trade guild. This was someone's emergency fund.",
         "reward": {"type": "loot", "name": "Silver pouch", "gold_value": 12}},
        {"name": "Single Gold Piece in a Skull",
         "narrative": "A bleached skull sits on a flat rock, almost decoratively. Inside the cranium, a single gold coin gleams. Whether offering or dark humor, someone placed it there deliberately.",
         "reward": {"type": "loot", "name": "Skull's gold piece", "gold_value": 1}},
    ]),

    _e(47, "Old Weapon", "loot", _ALL, _NO_WATER_WALL, [
        {"name": "Notched Longsword",
         "narrative": "A longsword lies half-buried in the dirt, its edge notched from heavy use. The hilt wrapping is rotted, but the blade itself is surprisingly sound. Someone fought hard with this."},
        {"name": "Rusted Crossbow",
         "narrative": "A crossbow leans against a rock, its string long since snapped. Rust has claimed most of the mechanism, but the stock is carved with a name: 'HOLT.' A soldier's weapon, personalized."},
        {"name": "Cracked Warhammer",
         "narrative": "A massive warhammer with a cracked head rests across two stones like a monument. The crack runs clean through the striking face — whatever it hit last was harder than dwarven steel."},
    ]),

    _e(48, "Potion Remains", "loot", _ALL, _NO_WATER_WALL, [
        {"name": "Half-Full Healing Vial",
         "narrative": "A small glass vial, miraculously unbroken, holds a thimbleful of red liquid. It smells faintly of cherries and warm metal. A healing potion — barely enough for a sip, but a sip might be enough.",
         "reward": {"type": "loot", "name": "Healing vial remnant", "gold_value": 5}},
        {"name": "Unlabeled Flask",
         "narrative": "A stoppered flask of murky blue liquid sits on a flat rock, almost as if someone left it there intentionally. No label, no markings. The liquid swirls on its own when tilted."},
        {"name": "Shattered Bottle",
         "narrative": "Glass shards and a dried stain mark where a potion bottle met an unfortunate end. The residue has crystallized into tiny amber beads that still faintly glow.",
         "skill_check": {"skill": "Arcana", "dc": 11},
         "success_text": "The residue is concentrated haste potion — expensive stuff. Whoever dropped this lost a small fortune."},
    ]),

    _e(49, "Scroll Fragment", "loot", _ALL, _NO_WATER_WALL, [
        {"name": "Torn Spell Scroll",
         "narrative": "A scrap of parchment covered in arcane notation flutters against a rock, pinned by a stone. The spell is incomplete — torn in half — but what remains suggests something powerful.",
         "skill_check": {"skill": "Arcana", "dc": 12},
         "success_text": "It's half of a protection ward — specifically designed to resist the Crown's influence. The other half could be invaluable."},
        {"name": "Partial Map",
         "narrative": "A fragment of a hand-drawn map shows tunnels, chambers, and notations in a cramped hand. 'LEFT AT SIGIL DOOR' is underlined twice. The rest is torn away.",
         "reward": {"type": "info", "text": "The map fragment shows a passage through the crystal caves that bypasses the main gallery."}},
        {"name": "Coded Letter",
         "narrative": "A water-stained letter in cipher. The code is simple — every third letter spells the real message — but the contents are alarming.",
         "skill_check": {"skill": "Investigation", "dc": 11},
         "success_text": "Decoded, the letter reads: 'Supply route compromised. Switch to the pass. Do not trust the merchant in Millhaven.'"},
    ]),

    _e(50, "Gemstone", "loot", _ALL, _NO_WATER_WALL, [
        {"name": "Rough Amethyst",
         "narrative": "A chunk of raw amethyst lies in the dirt, its purple crystal faces winking in the light. Uncut but genuine — worth something to the right buyer.",
         "reward": {"type": "loot", "name": "Rough amethyst", "gold_value": 10}},
        {"name": "Chipped Ruby",
         "narrative": "A ruby the size of a thumbnail, chipped on one side but still deep red and beautiful. It was set in something once — the mounting left small marks in the stone.",
         "reward": {"type": "loot", "name": "Chipped ruby", "gold_value": 15}},
        {"name": "Uncut Sapphire",
         "narrative": "Wedged in a rock crevice, a sapphire catches the light with a deep blue fire. It takes some effort to pry loose, but the stone is flawless — a rare find in troubled times.",
         "skill_check": {"skill": "Perception", "dc": 12},
         "success_text": "You notice the sapphire first, catching its glint from a distance.",
         "reward": {"type": "loot", "name": "Uncut sapphire", "gold_value": 25}},
    ]),

    _e(51, "Mundane Supplies", "loot", _ALL, _NO_WATER_WALL, [
        {"name": "Rope and Pitons",
         "narrative": "A coil of hemp rope and a pouch of iron pitons lie abandoned beside the path. The rope is sturdy, the pitons sharp. A climber's kit, left behind by someone who no longer needed to climb."},
        {"name": "Rations (stale but edible)",
         "narrative": "A canvas sack contains hard biscuits, dried meat, and a wax-sealed jar of preserves. Stale, but edible. In these times, even bad food is a find.",
         "reward": {"type": "loot", "name": "Travel rations", "gold_value": 2}},
        {"name": "Flint and Steel Kit",
         "narrative": "A small leather case holds a flint, a steel striker, and a bundle of dry tinder — the basics of fire-starting, carefully prepared. The case is engraved with a soldier's regiment number."},
    ]),

    _e(52, "Trinket", "loot", _ALL, _NO_WATER_WALL, [
        {"name": "Bone Dice Set",
         "narrative": "A pair of dice carved from yellowed bone, each face marked with pips of inlaid copper. They feel heavier than they should, and they always seem to land on the same number."},
        {"name": "Tarnished Locket",
         "narrative": "A silver locket, green with tarnish, hangs from a broken chain. Inside: a miniature portrait of a woman and a lock of dark hair. Someone loved, someone lost.",
         "reward": {"type": "loot", "name": "Silver locket", "gold_value": 5}},
        {"name": "Wooden Holy Symbol",
         "narrative": "A hand-carved holy symbol on a leather cord — simple craftsmanship, but the wood is worn smooth by years of worried fingers. Someone prayed with this. A lot."},
        {"name": "Glass Eye",
         "narrative": "A glass eye stares up from the dirt, startlingly lifelike. It's blue-green, with incredible detail in the iris. It seems to follow you as you move. It doesn't. Probably."},
    ]),

    _e(53, "Journal Entry", "loot", _ALL, _NO_WATER_WALL, [
        {"name": "Explorer's Last Page",
         "narrative": "A single journal page, torn out and weighted with a stone. The handwriting deteriorates from neat to frantic: '...the green light is closer. Can hear it now. Like singing, but wrong. I'm going to —' It ends mid-sentence.",
         "reward": {"type": "info", "text": "The explorer's notes mention a safe path along the western ridge that avoids the heaviest corruption zones."}},
        {"name": "Madman's Scrawl",
         "narrative": "Pages covered in overlapping text, written in circles and spirals rather than lines. Most is gibberish, but phrases repeat: 'THE CROWN SEES' and 'COUNT THE SPIRALS' appear dozens of times."},
        {"name": "Love Letter Never Sent",
         "narrative": "A carefully folded letter, sealed but never delivered. The handwriting is beautiful: 'My dearest, when this is over and the roads are safe again, I will find you. I swear it on every star.' It's unsigned."},
    ]),

    _e(54, "Locked Chest", "loot", _ALL, _NO_WATER_WALL, [
        {"name": "Iron-Bound Box",
         "narrative": "A small iron-bound box sits in a corner, its lock rusted shut. The box is heavy for its size, and something shifts inside when you tilt it. Could be treasure. Could be trouble.",
         "skill_check": {"skill": "Dexterity", "dc": 13},
         "success_text": "The lock yields to patient work. Inside: a handful of coins and a ring set with a tiny red stone.",
         "reward": {"type": "loot", "name": "Locked box contents", "gold_value": 18}},
        {"name": "Mimic Suspect",
         "narrative": "A treasure chest sits in the open, lid slightly ajar, gold glinting inside. It's almost too perfect. You've heard the stories. You eye it from a safe distance. It doesn't move. Yet."},
        {"name": "Trapped Jewelry Case",
         "narrative": "An ornate jewelry case sits on a stone shelf. A thin wire runs from the clasp to... something behind the shelf. The trap is crude but potentially unpleasant.",
         "skill_check": {"skill": "Dexterity", "dc": 12},
         "success_text": "You disarm the trap — a spring-loaded needle coated in something unpleasant. The case contains a silver brooch shaped like a crescent moon.",
         "reward": {"type": "loot", "name": "Silver crescent brooch", "gold_value": 15}},
    ]),

    _e(55, "Crafting Material", "loot", _ALL, _NO_WATER_WALL, [
        {"name": "Monster Hide",
         "narrative": "A thick, scaled hide has been stretched on a frame and left to dry. The scales are iridescent — beautiful and tough. Whoever prepared this knew their leatherwork, but never came back to collect it."},
        {"name": "Enchanting Dust",
         "narrative": "A sealed glass jar contains fine, shimmering dust that shifts color when the jar is tilted. Enchanting reagent — rare and valuable, even in small quantities.",
         "reward": {"type": "loot", "name": "Enchanting dust", "gold_value": 20}},
        {"name": "Alchemical Reagent",
         "narrative": "Glass bottles in a leather carry-case hold carefully separated liquids and powders. Labels in an alchemist's shorthand identify them as reagents for healing potions. Essential supplies in these times.",
         "reward": {"type": "loot", "name": "Alchemical reagents", "gold_value": 12}},
    ]),

    _e(56, "Armor Piece", "loot", _ALL, _NO_WATER_WALL, [
        {"name": "Dented Shield",
         "narrative": "A kite shield lies face-down, its surface dented by repeated blows. Flipping it reveals a heraldic device — a crown above crossed swords. The old kingdom's sigil. The shield still holds."},
        {"name": "Single Gauntlet",
         "narrative": "An articulated steel gauntlet lies on the ground, fingers curled as if still gripping something. The craftsmanship is excellent. The matching gauntlet — and its owner — are nowhere to be seen."},
        {"name": "Torn Chainmail Shirt",
         "narrative": "A chainmail shirt has been violently torn — something with enormous strength ripped it apart like paper. Scattered rings litter the ground around it. The blood has dried to black."},
    ]),

    _e(57, "Thieves' Tools", "loot", _ALL, _NO_WATER_WALL, [
        {"name": "Bent Lockpicks",
         "narrative": "A leather roll of lockpicks — most bent or broken, victims of locks that won. Two remain usable. Professional grade, delicate work. Their owner was skilled, if not always successful."},
        {"name": "Grappling Hook",
         "narrative": "A three-pronged iron grappling hook with a length of silk rope still attached. Light, strong, and well-maintained. Expensive kit for someone who needed to climb things that didn't want to be climbed."},
        {"name": "Smoke Pellets",
         "narrative": "A small pouch of clay pellets, each about the size of a marble. One broke in the bag, leaving a faint grey residue and a chemical smell. Throwing these hard would create a thick smoke screen."},
    ]),

    _e(58, "Religious Relic", "loot", _ALL, _NO_WATER_WALL, [
        {"name": "Saint's Finger Bone",
         "narrative": "A small bone — a finger — rests in a velvet-lined box. A brass plaque reads: 'Of Saint Emeric, Who Walked Into the Dark.' The bone is warm to the touch, warmer than it should be.",
         "skill_check": {"skill": "Religion", "dc": 12},
         "success_text": "Saint Emeric was a protector of travelers. His relics are said to ward against undead. In the Shattered Realms, this is more than a curiosity."},
        {"name": "Blessed Water Flask",
         "narrative": "A glass flask etched with holy symbols contains water that sparkles with an inner light. Blessed water — effective against undead and corruption. A rare commodity.",
         "reward": {"type": "loot", "name": "Blessed water flask", "gold_value": 8}},
        {"name": "Heretic's Brand",
         "narrative": "An iron brand, the handle wrapped in leather, the business end shaped into a blasphemous symbol — a holy sign inverted. It was used to mark people. The leather is still warm from a human grip."},
    ]),

    _e(59, "Musical Instrument", "loot", _ALL, _NO_WATER_WALL, [
        {"name": "Broken Lute",
         "narrative": "A lute with two snapped strings lies in its open case. The body is intact — rosewood, beautifully made. A skilled luthier could restore it. Inside the case, sheet music for 'The Fall of Ashenmere.'"},
        {"name": "Bone Flute",
         "narrative": "A small flute carved from a single bone — too large to be animal, too smooth to be natural. When wind passes over its holes, it produces a note that makes your chest ache."},
        {"name": "War Drum (cracked)",
         "narrative": "A massive drum lies on its side, the hide head cracked but not broken. Tribal markings cover the body — nothing you recognize. Striking it might carry sound for miles. Or attract attention."},
    ]),

    _e(60, "Curious Device", "loot", _ALL, _NO_WATER_WALL, [
        {"name": "Clockwork Mechanism",
         "narrative": "A palm-sized device of interlocking gears and tiny springs, still ticking softly. You can't tell what it does — but it's been running for a very long time without winding.",
         "skill_check": {"skill": "Investigation", "dc": 13},
         "success_text": "The device is counting something. Each tick advances a tiny dial. Whatever it's measuring, it's been going for approximately 200 years."},
        {"name": "Crystal Tuning Fork",
         "narrative": "A tuning fork carved from a single crystal hums faintly when held. Striking it against stone produces a note that makes nearby magical items pulse in response."},
        {"name": "Folding Spyglass",
         "narrative": "A brass spyglass that collapses to pocket size, lenses still clear after what must be decades of neglect. Looking through it, distant objects snap into sharp focus. Scratched inside the rim: 'PROPERTY OF HARLEN.'",
         "reward": {"type": "info", "text": "The spyglass belonged to Harlen the Cartographer. He may want it back."}},
    ]),

    # ═══════════════════════════════════════════════════════════════
    #  ATMOSPHERE & FLAVOR  (61–75)
    # ═══════════════════════════════════════════════════════════════

    _e(61, "Strange Sound", "atmosphere", _ALL, (), [
        {"name": "Distant Drumming",
         "narrative": "A rhythmic thumping reaches you from somewhere far away — deep, steady, like a giant heartbeat. It pulses through the ground as much as the air. It doesn't stop."},
        {"name": "Scratching Behind the Wall",
         "narrative": "A persistent scratching comes from behind the nearest wall — not frantic, but methodical. Whatever is doing it has been at it for a while. Occasionally it pauses, as if listening."},
        {"name": "Low Chanting",
         "narrative": "Voices rise and fall in unison, chanting in a language you don't recognize. The sound seems to come from everywhere and nowhere. When you hold your breath to listen, it stops. Resume breathing, and it returns."},
        {"name": "Metallic Grinding",
         "narrative": "A harsh, grinding sound of metal on metal echoes through the area. It comes in irregular bursts — like machinery struggling to work. Something mechanical is operating nearby, badly."},
    ]),

    _e(62, "Temperature Shift", "atmosphere", _ALL, (), [
        {"name": "Sudden Warmth",
         "narrative": "A wave of warmth washes over you — not heat, but comfort. Like stepping into a room with a fireplace. It lasts a few seconds, then fades, leaving you feeling strangely homesick."},
        {"name": "Bone-Deep Chill",
         "narrative": "Cold lances through you — not from outside, but from within, as if your bones are conducting frost. It passes in a moment, but the memory of it lingers. Something cold is near."},
        {"name": "Humid Wave",
         "narrative": "The air turns thick and tropical, moisture beading on every surface. Breathing feels like drinking warm water. The humidity passes as suddenly as it arrived, leaving everything damp."},
    ]),

    _e(63, "Unusual Smell", "atmosphere", _ALL, (), [
        {"name": "Fresh Bread",
         "narrative": "The unmistakable smell of fresh-baked bread drifts through the air. Your mouth waters. There is no bakery here. There is no one here. The smell is warm, comforting, and impossible."},
        {"name": "Rotting Flesh",
         "narrative": "A sweet, gagging stench hits you like a wall. Something dead, and not recently. The smell intensifies, then fades — as if the source passed through on some invisible current."},
        {"name": "Ozone After Lightning",
         "narrative": "The sharp, clean smell of ozone fills the air — the same scent that follows a lightning strike. But the sky is clear and nothing has burned. The air itself crackles faintly."},
        {"name": "Perfume",
         "narrative": "A waft of expensive perfume — jasmine and sandalwood — drifts past on air that shouldn't carry such a scent. It's gone as quickly as it came, leaving only the question of who wore it, and when."},
    ]),

    _e(64, "Light Source", "atmosphere", _ALL, (), [
        {"name": "Flickering Torchlight Ahead",
         "narrative": "A faint, flickering light dances in the distance — warm and orange, like a torch. It doesn't move closer or retreat. When you reach where it should be, there's nothing. The light is now behind you."},
        {"name": "Bioluminescent Moss",
         "narrative": "Patches of moss glow with a soft blue-green light, painting the ground in an underwater palette. The light pulses gently, brightening and dimming in a rhythm that almost matches your heartbeat."},
        {"name": "Floating Candle Flame",
         "narrative": "A single flame hangs in the air at eye level — no candle, no wick, no source. It burns steadily, casting real shadows. Passing your hand through it feels cool, like mist."},
    ]),

    _e(65, "Animal Behavior", "atmosphere", _OUTDOOR, (), [
        {"name": "Birds Going Silent",
         "narrative": "The constant background chatter of birds cuts off mid-note. Every bird, all at once, falls silent. The quiet is oppressive and wrong. After thirty heartbeats, the noise returns as if nothing happened."},
        {"name": "Insects Swarming Away",
         "narrative": "A cloud of insects lifts from the ground and streams away in a tight formation — not scattered, but organized, like a flock of birds. They're fleeing something. You can't see what."},
        {"name": "Rats Fleeing in One Direction",
         "narrative": "A stream of rats pours across your path, all running the same direction with single-minded urgency. They ignore you completely. Whatever they're running from commands more attention than a human."},
    ]),

    _e(66, "Eerie Feeling", "atmosphere", _ALL, (), [
        {"name": "Being Watched",
         "narrative": "The hair on the back of your neck stands up. You are being watched — you're certain of it. But every shadow is empty, every corner bare. The feeling doesn't fade when you move on."},
        {"name": "Deja Vu",
         "narrative": "You've been here before. You're certain of it — the same crack in the wall, the same loose stone. But you haven't. This is new ground. The certainty erodes, leaving only unease."},
        {"name": "Sudden Dread",
         "narrative": "A wave of formless dread crashes over you — no cause, no trigger, just pure animal fear. Your hands shake. Your breath comes fast. Then it's gone, as suddenly as it arrived, leaving only confusion."},
        {"name": "Unnatural Calm",
         "narrative": "A profound sense of peace settles over you. Every worry dissolves. Every tension releases. It feels wonderful — and deeply wrong. This calm is not yours. Something is projecting it."},
    ]),

    _e(67, "Weather Change", "atmosphere", _OUTDOOR, (), [
        {"name": "Wind Picks Up",
         "narrative": "A gust of wind sweeps through, building from nothing to a howl in seconds. It carries dust, leaves, and a sound that might be distant screaming — or might just be the wind."},
        {"name": "Rain Starts",
         "narrative": "A single drop, then another, then a downpour. The rain is warm and smells of copper. It passes in minutes, leaving everything glistening. The ground steams slightly where the water soaks in."},
        {"name": "Clouds Part Revealing Stars",
         "narrative": "The overcast sky breaks open above you, revealing a circle of stars. For a moment, the constellations look wrong — shifted, as if the sky itself has moved. Then the clouds close, and you doubt what you saw."},
    ]),

    _e(68, "Ground Tremor", "atmosphere", _ALL, (), [
        {"name": "Faint Vibration",
         "narrative": "The ground hums beneath your feet — not a tremor, but a vibration, steady and rhythmic. Like an enormous engine turning somewhere deep below. It goes on and on."},
        {"name": "Single Hard Jolt",
         "narrative": "The earth lurches — one sharp jolt that rattles your teeth and sends loose objects tumbling. Then silence. No aftershocks. Just one brutal reminder that the ground is not as stable as it looks."},
        {"name": "Rolling Quake",
         "narrative": "A low rumble builds, and the ground rolls like an ocean wave — a slow, nauseating undulation that lasts twenty seconds. Dust rains from above. Then stillness, except for settling debris."},
    ]),

    _e(69, "Water Feature", "atmosphere", ("FLOOR", "SWAMP", "MOUNTAIN"), (), [
        {"name": "Dripping Condensation",
         "narrative": "Water drips from the ceiling in a steady rhythm, each drop catching the light as it falls. The drip has worn a smooth groove in the stone floor — centuries of patient erosion."},
        {"name": "Still Reflecting Pool",
         "narrative": "A natural pool of water lies perfectly still, its surface a flawless mirror. Your reflection looks back at you — but moves a half-second too late, as if watching from just beyond the surface."},
        {"name": "Bubbling Spring",
         "narrative": "A small spring bubbles up from between stones, the water crystal clear and cold. The bubbles rise in patterns — spirals and circles that seem too regular to be natural."},
    ]),

    _e(70, "Vegetation Shift", "atmosphere", _OUTDOOR, (), [
        {"name": "Lush Patch in Barren Area",
         "narrative": "In the middle of dead, blighted ground, a patch of impossibly green grass grows in a perfect circle. Wildflowers bloom at its center. Nothing else for a hundred yards is alive."},
        {"name": "Dead Zone in Green Forest",
         "narrative": "A pocket of death in otherwise healthy forest — trees standing but leafless, bark grey and peeling, the ground bare. The boundary is sharp, like a wall. Life on one side, death on the other."},
        {"name": "Single Blooming Flower",
         "narrative": "A single flower blooms from a crack in the stone — bright red, perfect, impossible. No soil, no water source, no light. Yet here it grows, defiant and absurdly beautiful."},
    ]),

    _e(71, "Graffiti", "atmosphere", _ALL, ("WATER",), [
        {"name": "TURN BACK Scrawled in Charcoal",
         "narrative": "Two words scrawled on the wall in rough charcoal: TURN BACK. The letters are large and frantic, the charcoal smeared as if written in a hurry. Below, in smaller letters: 'it follows.'"},
        {"name": "Tallied Days on the Wall",
         "narrative": "Scratched into the stone, row after row of tally marks. You count over three hundred. Someone was trapped here for nearly a year, marking each day. The marks stop abruptly."},
        {"name": "Crude Map Scratched into Stone",
         "narrative": "Someone carved a rough map into the wall with a blade. Chambers, tunnels, dead ends — all marked with X's. One chamber is circled with the word 'SAFE.' Another reads 'NO.'"},
    ]),

    _e(72, "Insect Activity", "atmosphere", _ALL, ("WATER",), [
        {"name": "Firefly Cluster",
         "narrative": "A constellation of fireflies drifts through the air, blinking in synchronization. Their light is cool green — not the warm yellow of normal fireflies. They move with purpose, like a procession."},
        {"name": "Column of Ants",
         "narrative": "An endless column of ants marches in a perfectly straight line, carrying fragments of something green and luminescent. They emerge from one crack and disappear into another, tireless and focused."},
        {"name": "Moth Spiral Around Nothing",
         "narrative": "A dozen moths orbit a point in empty air, spiraling tighter and tighter around something invisible. Their wingbeats are silent. Occasionally one touches the invisible center and falls, motionless."},
    ]),

    _e(73, "Shadow Play", "atmosphere", _ALL, (), [
        {"name": "Moving Shadows Without Source",
         "narrative": "Shadows slide across the wall — the silhouettes of people walking — but the space is empty. The shadows move naturally, casting from some invisible crowd that passed through here once, and never truly left."},
        {"name": "Shadow Arrives Before Its Caster",
         "narrative": "Your shadow falls wrong. It moves a heartbeat ahead of you, reaching for things before you do, turning corners before you decide to. Looking directly at it, it snaps back to normal. Look away, and it creeps forward again."},
        {"name": "Frozen Shadow on the Wall",
         "narrative": "A human shadow is burned into the wall — arms raised, mouth open, frozen in a scream. No body, no source. Just a permanent silhouette of someone's worst moment, seared into stone by some terrible force."},
    ]),

    _e(74, "Residual Magic", "atmosphere", _ALL, (), [
        {"name": "Faint Aura",
         "narrative": "A faint shimmer hangs in the air — barely visible, like heat haze in a cold place. Magic was worked here, and its echo lingers. The shimmer is strongest near the ground, near something buried.",
         "skill_check": {"skill": "Arcana", "dc": 11},
         "success_text": "The residual aura is protective — a ward, long since expired. Whatever it was guarding is no longer protected."},
        {"name": "Arcane Scorch Marks",
         "narrative": "Black, glassy scorch marks radiate outward from a central point — the aftermath of a powerful spell. The stone is vitrified where the blast hit. This was not a gentle working."},
        {"name": "Lingering Enchantment Hum",
         "narrative": "A low hum permeates the area, felt in the teeth more than heard. Something here was enchanted, powerfully and permanently. The enchantment has faded, but its vibration continues — a ghost of magic."},
    ]),

    _e(75, "Structural Oddity", "atmosphere", _ALL, ("WATER",), [
        {"name": "Door to Nowhere",
         "narrative": "A perfectly ordinary door stands in a solid wall — handle, hinges, frame, all intact. Opening it reveals more wall. Solid stone, flush with the frame. A door that leads absolutely nowhere."},
        {"name": "Staircase That Loops",
         "narrative": "A stone staircase descends twelve steps and arrives back at its own beginning. You can walk it endlessly and never go anywhere. The illusion — if that's what it is — is flawless."},
        {"name": "Room Slightly Too Large Inside",
         "narrative": "This space is wrong. From outside, it should be a small alcove. Inside, it stretches too far. The back wall is twenty feet from the entrance, but the building it's in is only ten feet deep. The math doesn't work."},
    ]),

    # ═══════════════════════════════════════════════════════════════
    #  SOCIAL & MORAL DILEMMAS  (76–85)
    # ═══════════════════════════════════════════════════════════════

    _e(76, "Plea for Help", "social", _LAND_ONLY, ("WATER", "WALL"), [
        {"name": "Trapped Miner",
         "narrative": "A muffled voice from behind a rockfall: 'Is someone there? I can hear you! Please — my leg's pinned and the air's getting thin!' Loose stones shift above the blockage.",
         "choices": (
             {"label": "Clear the rubble", "text": "You heave stones aside until you reach the miner — bruised and grateful. 'Thank you! The caves aren't safe, but there's a supply cache deeper in. Take what you need.'",
              "reward": {"type": "info", "text": "The miner mentions a supply cache deeper in the caves."}},
             {"label": "Call out encouragement", "text": "You shout instructions through the gap. The miner manages to free their leg and crawl out, shaken but alive. They nod in thanks before limping away."},
             {"label": "Move on", "text": "The voice calls after you, growing fainter. You tell yourself someone else will come. The silence that follows says otherwise."},
         )},
        {"name": "Drowning Stranger",
         "narrative": "Thrashing in a flooded pit, a figure gasps for air. 'Help! I can't — the current —' They go under, surface, go under again. The water is dark and of unknown depth.",
         "choices": (
             {"label": "Jump in and help", "text": "You plunge into the water. It's freezing and deeper than it looked, but you grab the stranger and haul them to solid ground. They cough up water and clutch your arm. 'I owe you my life.'"},
             {"label": "Throw a rope", "text": "You toss a length of rope. The stranger catches it on the second try, and you pull them to safety. Slower, but you stay dry."},
             {"label": "Move on", "text": "The thrashing grows weaker as you walk away. You don't look back."},
         )},
        {"name": "Voice Behind a Sealed Door",
         "narrative": "A heavy door, barred from the outside. From behind it, a voice: 'Let me out. I've been here for days. Please.' A pause. 'I'm not one of them. I promise.' Another pause. 'I was a teacher.'",
         "choices": (
             {"label": "Open the door", "text": "You lift the bar. A thin, blinking figure stumbles out — a middle-aged woman in torn clothes. She weeps with relief. 'Thank you. I can tell you things about what's happening here.'",
              "reward": {"type": "info", "text": "The freed teacher describes patrol patterns she observed through a crack in the door."}},
             {"label": "Ask questions first", "text": "You interrogate through the door. The answers are consistent, desperate, human. But you leave the bar in place. Trust is expensive these days."},
             {"label": "Move on", "text": "The voice follows you: 'Please! Don't leave me here!' It echoes long after you've turned the corner."},
         )},
    ]),

    _e(77, "Moral Choice", "social", _LAND_ONLY, ("WATER", "WALL"), [
        {"name": "Mercy or Justice for a Thief",
         "narrative": "A young man kneels before you, hands tied, guarded by a grim-faced farmer. 'He stole my last sack of grain,' the farmer says. 'In the old days, the magistrate handled this. Now there's no magistrate.' The thief stares at the ground.",
         "choices": (
             {"label": "Show mercy", "text": "You cut the thief's bonds. 'Everyone's hungry,' you say. The farmer scowls but doesn't argue. The thief scrambles away without a word — but leaves something behind. A silver ring, dropped in haste.",
              "reward": {"type": "loot", "name": "Silver ring", "gold_value": 5}},
             {"label": "Side with the farmer", "text": "You help the farmer secure the thief for the next patrol — if one ever comes. Justice served, if imperfect. The farmer offers you a share of his remaining grain in thanks."},
             {"label": "Walk away", "text": "You leave them to sort it out. Behind you, voices rise — then fall silent. You don't know how it ended. Perhaps that's for the best."},
         )},
        {"name": "Share Rations with Strangers",
         "narrative": "A family huddles by the road — two adults, three children, all thin and hollow-eyed. They don't beg. They just look at you with the quiet acceptance of people who've stopped hoping.",
         "choices": (
             {"label": "Share your food", "text": "You hand over what you can spare. The children's eyes go wide. The mother mouths 'thank you' but can't speak. Small kindnesses in dark times.",
              "consequences": {"flags": {"helped_refugees": True}}},
             {"label": "Give directions to Millhaven", "text": "You can't feed them, but you can point them toward safety. 'Millhaven still stands. Ask for Brenna at the tavern.' Hope returns to their faces — faint, but real.",
              "consequences": {"flags": {"helped_refugees": True}}},
             {"label": "Move on", "text": "You pass by. The children watch you go with those hollow eyes. You walk faster."},
         )},
        {"name": "Destroy a Dangerous Artifact or Keep It",
         "narrative": "A crystal sphere pulses with green energy on a stone plinth. A note beside it reads: 'DO NOT TOUCH — amplifies Crown's power.' But the power could be turned against the Crown. Maybe.",
         "choices": (
             {"label": "Destroy it", "text": "You bring your weapon down hard. The sphere shatters with a sound like a scream, and the green energy dissipates. The air feels cleaner. One less tool for the Sovereign.",
              "reward": {"type": "info", "text": "Destroying the relay weakens the Crown's influence in this area."}},
             {"label": "Leave it alone", "text": "You step back. The note was clear enough, and you're not sure you understand what you'd be wielding. Better to leave it for someone who does."},
         )},
    ]),

    _e(78, "Faction Tension", "social", _LAND_ONLY, ("WATER", "WALL"), [
        {"name": "Guard vs. Smuggler Standoff",
         "narrative": "A town guard and a hooded figure face off over a crate of supplies. 'These are for the people!' the guard insists. 'These are for whoever can pay,' the smuggler replies coolly. Both look at you for support.",
         "choices": (
             {"label": "Side with the guard", "text": "You back the guard. The smuggler spits, drops the crate, and vanishes into the shadows. The guard nods gratefully. 'There's medicine in here. People need it.'",
              "reward": {"type": "info", "text": "The guard mentions a supply route that might still be open through the southern pass."}},
             {"label": "Side with the smuggler", "text": "Free market wins. The guard storms off. The smuggler grins. 'Smart choice. For that, I'll tell you something useful — there's a weapons cache north of here.'",
              "reward": {"type": "info", "text": "The smuggler reveals the location of a hidden weapons cache."}},
             {"label": "Walk away", "text": "Not your fight. They're still arguing as you leave."},
         )},
        {"name": "Clerics Arguing Over Jurisdiction",
         "narrative": "Two clerics in different vestments argue over a crossroads shrine. 'This shrine is consecrated to Aelindra!' 'It was Korvain's first! The inscription is clear!' Neither is willing to yield.",
         "choices": (
             {"label": "Mediate", "text": "You suggest they share the shrine — one god per side. They stare at you, then at each other. 'That's... actually reasonable,' one admits. They shake hands, reluctantly."},
             {"label": "Walk away", "text": "Holy disputes are above your pay grade. Their voices fade behind you."},
         )},
        {"name": "Two Merchants Claiming Same Goods",
         "narrative": "A wagon sits between two merchants, both claiming ownership. 'I paid Torven for this shipment!' 'And I paid Torven for the SAME shipment! The man sold it twice!' The wagon's contents could feed a village.",
         "choices": (
             {"label": "Split the goods", "text": "You suggest they divide the shipment. Half a wagon each. Neither is happy, but both walk away with something. 'Torven will answer for this,' one mutters."},
             {"label": "Suggest they confront Torven together", "text": "You point out the real villain: Torven, who took both their money. United in anger, they march off together to find the guild master.",
              "reward": {"type": "info", "text": "Both merchants confirm Torven has been double-dealing supplies meant for the resistance."}},
             {"label": "Walk away", "text": "Let them fight over scraps while the world burns. You have bigger problems."},
         )},
    ]),

    _e(79, "Deception", "social", _ALL, _NO_WATER_WALL, [
        {"name": "Fake Distress Signal",
         "narrative": "Smoke rises from beyond the next hill — the universal signal for help. But the fire, when you reach it, is carefully tended and unattended. A lure. You notice movement in the treeline too late to pretend you didn't come.",
         "skill_check": {"skill": "Insight", "dc": 13},
         "success_text": "The setup is classic bandit bait. The movement in the trees is deliberate — they want to be seen, to herd you toward the real trap. Circling wide would avoid it entirely."},
        {"name": "Illusory Treasure",
         "narrative": "Gold coins scatter the floor, gleaming in the light. Piles of them, more wealth than you've ever seen. But the coins have no weight when you pick them up. Your hand passes through the pile. All illusion."},
        {"name": "Shapeshifter Posing as Ally",
         "narrative": "A familiar face approaches — someone you've met before, waving and smiling. But something is off. The details are perfect, yet the mannerisms are wrong. The smile doesn't quite match the eyes.",
         "skill_check": {"skill": "Insight", "dc": 15},
         "success_text": "The impersonation is good but not perfect. The real person had a scar on their left hand. This one doesn't. Whatever this creature is, it's working from description, not direct observation."},
    ]),

    _e(80, "Sacrifice Required", "social", _ALL, _NO_WATER_WALL, [
        {"name": "Blood Price for a Door",
         "narrative": "A sealed door bears an inscription: 'The price of passage is freely given.' Below it, a shallow basin stained dark with old blood. The mechanism is clear — the door opens for a blood offering.",
         "choices": (
             {"label": "Pay the price", "text": "You draw a blade across your palm. Blood drips into the basin, and the door grinds open. The wound stings, but the path is clear."},
             {"label": "Find another way", "text": "You're not bleeding for a door. There must be another route. There always is."},
         )},
        {"name": "Trade a Memory for Passage",
         "narrative": "A translucent figure blocks the path, palm raised. 'A memory,' it whispers. 'Your happiest one. Give it freely and pass. Refuse, and find another way.' Its expression is neither kind nor cruel.",
         "choices": (
             {"label": "Give a memory", "text": "You close your eyes and think of... something. It slips away even as you offer it. The figure nods and fades. The path is open. You feel lighter. And emptier."},
             {"label": "Refuse", "text": "'My memories are mine.' The figure inclines its head, almost respectfully, and vanishes. The path remains blocked. You'll find another way."},
         )},
        {"name": "Leave an Item Behind to Proceed",
         "narrative": "A narrow passage, barely wide enough to squeeze through, has a shelf carved into the wall. On it, tokens left by previous travelers — rings, coins, a child's toy. An unwritten rule: leave something to pass safely.",
         "choices": (
             {"label": "Leave a token", "text": "You add a coin to the shelf. It feels right — a small tribute to those who came before. The passage beyond is clear and safe."},
             {"label": "Take the passage without offering", "text": "You push through without leaving anything. Nothing happens. But the air feels colder on the other side, and the shadows seem to lean closer."},
         )},
    ]),

    _e(81, "Oath or Promise", "social", _ALL, _NO_WATER_WALL, [
        {"name": "Swear to a Dying Knight",
         "narrative": "A knight in her final moments grips your arm with failing strength. 'Promise me — my sword to my daughter in Millhaven. Hanna. She's seven.' The sword is magnificent. The knight is sincere. And dying.",
         "choices": (
             {"label": "Swear the oath", "text": "You take the sword and swear. The knight's grip relaxes, and a faint smile crosses her face before the light leaves her eyes. You have a promise to keep.",
              "reward": {"type": "info", "text": "You now carry a promise to deliver a knight's sword to her daughter Hanna in Millhaven."}},
             {"label": "Comfort without promising", "text": "You hold her hand and speak gentle words, but make no oath you can't keep. She passes with fear in her eyes. The sword remains."},
         )},
        {"name": "Promise a Ghost Vengeance",
         "narrative": "A spirit materializes, pointing toward the citadel with trembling fury. 'He killed me. He killed all of us. PROMISE ME you will make him answer for it.' The ghost's rage is palpable, electric.",
         "choices": (
             {"label": "Swear vengeance", "text": "You swear it. The ghost's fury softens to something almost like gratitude before it fades. The temperature normalizes. A promise made to the dead carries weight."},
             {"label": "Acknowledge without swearing", "text": "'I hear you,' you say carefully. 'But I make no oaths I might not keep.' The ghost's expression twists — hurt, then resignation — before it dissolves."},
         )},
        {"name": "Vow to a Fey in Exchange for Aid",
         "narrative": "'I can show you a safe path,' the small figure offers, eyes glittering. 'All I ask is a promise. One small favor, later, of my choosing.' Fey bargains are never small. But the path ahead is dangerous.",
         "choices": (
             {"label": "Accept the bargain", "text": "You agree. The fey grins — too wide, too many teeth — and points the way. The path is indeed safer. What the favor will cost remains to be seen.",
              "reward": {"type": "info", "text": "You've made a bargain with a fey creature. The favor will be called in eventually."},
              "consequences": {"flags": {"freed_fey": True}}},
             {"label": "Decline", "text": "'I'll find my own way.' The fey shrugs, unconcerned. 'They always say that. I'll be here when you change your mind.' It vanishes with a giggle."},
         )},
    ]),

    _e(82, "Betrayal Reveal", "social", _ALL, _NO_WATER_WALL, [
        {"name": "Ally's Hidden Agenda",
         "narrative": "Documents scattered on a desk tell an uncomfortable story — detailed reports about your movements, your strengths, your plans. Written by someone who's been watching you. The handwriting is familiar.",
         "choices": (
             {"label": "Take the documents", "text": "You gather every page. This changes things. Someone you trusted has been reporting on you. But now you know — and that's an advantage.",
              "reward": {"type": "info", "text": "Intelligence reports about your party, written by someone with inside access. The handwriting might be identifiable."}},
             {"label": "Leave them", "text": "You leave the documents undisturbed. Better to let the spy think they're still undetected. For now."},
         )},
        {"name": "Planted Evidence Against Party",
         "narrative": "A wanted poster nailed to a post bears crude but recognizable sketches of your party. 'WANTED: For crimes against the Sovereign. Bring to the citadel ALIVE.' The reward is disturbingly generous.",
         "choices": (
             {"label": "Tear it down", "text": "You rip the poster from the post and shred it. But if there's one, there are more. The Sovereign knows you're coming."},
             {"label": "Study it for clues", "text": "You examine the poster carefully. The paper is citadel-issue, the ink fresh. Someone posted this within the last day. They're close.",
              "reward": {"type": "info", "text": "The wanted poster was posted recently — the Sovereign's agents are active in this area."}},
         )},
        {"name": "Double-Agent Exposed",
         "narrative": "Two identical messages, left carelessly side by side. One reports to the resistance. The other reports the same information to the citadel. The same author, playing both sides.",
         "choices": (
             {"label": "Take both messages", "text": "Proof of treachery. This double-agent has been feeding both sides — and the resistance needs to know.",
              "reward": {"type": "info", "text": "Evidence of a double-agent operating between the resistance and the citadel."}},
             {"label": "Leave them", "text": "You leave the messages. Picking sides in a spy game is dangerous when you don't know all the players."},
         )},
    ]),

    _e(83, "Cultural Misunderstanding", "social", _LAND_ONLY, ("WATER", "WALL"), [
        {"name": "Offended Local Custom",
         "narrative": "A group of locals recoils as you pass. 'The left hand!' one hisses. 'They gestured with the LEFT HAND!' Apparently, this is a grave insult here. You have no idea what you did.",
         "choices": (
             {"label": "Apologize", "text": "You bow your head and apologize with both hands raised, palms forward. The tension eases. An elder nods and waves you on. Crisis averted."},
             {"label": "Keep walking", "text": "You keep moving. Their customs aren't your problem. The muttering behind you follows for a while, then fades."},
         )},
        {"name": "Sacred Ground Trespassed",
         "narrative": "Stone markers ring a clearing, and the moment you step between them, a horn sounds. An angry voice calls out in a dialect you barely understand. The gist is clear: you weren't supposed to be here.",
         "choices": (
             {"label": "Back away respectfully", "text": "You raise your hands and step back beyond the markers. The horn stops. The voice softens. A figure emerges and points you toward a path that goes around."},
             {"label": "Stand your ground", "text": "You don't move. The voice gets louder, but no one appears. After a tense minute, silence falls. You proceed, but the feeling of unwelcome eyes never quite fades."},
         )},
        {"name": "Gift Interpreted as Insult",
         "narrative": "Offering water to a parched-looking traveler earns you a furious glare. 'You think I cannot provide for myself?' They knock the waterskin away. In this culture, apparently, unsolicited charity is a challenge.",
         "choices": (
             {"label": "Explain your intention", "text": "You explain that where you come from, sharing water is a sign of friendship. The traveler's expression softens. 'Then I accept your friendship, outsider. But next time, ask first.'"},
             {"label": "Pick up your waterskin and leave", "text": "You retrieve your waterskin without a word. Some lessons cost nothing but pride."},
         )},
    ]),

    _e(84, "Competing Objectives", "social", _ALL, _NO_WATER_WALL, [
        {"name": "Rescue vs. Pursue the Villain",
         "narrative": "A wounded survivor points two directions. 'The creature went that way. But my companions — three of them — are trapped the other way. The ceiling could come down any minute.' Time for one, not both.",
         "choices": (
             {"label": "Save the trapped companions", "text": "You rush toward the trapped survivors. The rubble is unstable but you manage to clear a path. Three terrified faces emerge from the dust. The creature escapes — but lives are saved."},
             {"label": "Pursue the creature", "text": "You sprint after the creature. Behind you, stones grind and settle. You tell yourself the trapped survivors had time. The creature's trail leads deeper into the dark."},
         )},
        {"name": "Save the Bridge or Save the Hostage",
         "narrative": "A figure is tied to the bridge support as fire licks at the ropes. Cutting them free saves a life but collapses the only crossing for miles. The fire spreads either way.",
         "choices": (
             {"label": "Save the hostage", "text": "You cut the ropes. The figure falls free as the bridge groans and collapses behind you. One life saved. One crossing lost. The river below rages."},
             {"label": "Try to extinguish the fire", "text": "You beat at the flames with your cloak. The fire slows, the bridge holds — barely. The hostage struggles free on their own, singed but alive. Luck was on your side."},
         )},
        {"name": "Rest Now or Push Through",
         "narrative": "Your body screams for rest — every muscle aches, every step is effort. But ahead, you can hear sounds of distress. Someone needs help NOW. Your exhaustion versus their emergency.",
         "choices": (
             {"label": "Push through", "text": "You force your legs to move. Every step is agony, but you reach the source of the cries — a traveler pinned under a fallen beam. Together, you lift it free. Heroes don't rest."},
             {"label": "Rest first", "text": "You sit. Just for a moment. The cries continue, then grow fainter. When you finally move, the trail has gone cold. Sometimes the body wins."},
         )},
    ]),

    _e(85, "Information Trade", "social", _ALL, _NO_WATER_WALL, [
        {"name": "Spy Offering Secrets for Gold",
         "narrative": "A figure in the shadows beckons. 'I know things. Patrol routes. Supply caches. The Sovereign's weaknesses. All yours — for a price.' Their smile is oily, but their information might be genuine.",
         "choices": (
             {"label": "Pay for information", "text": "You hand over coins. The spy whispers quickly: routes, schedules, a name. You can't verify any of it yet, but the details are specific enough to be useful.",
              "reward": {"type": "info", "text": "The spy reveals that the citadel's southern approach has fewer patrols between midnight and dawn."}},
             {"label": "Decline", "text": "'Keep your secrets.' The spy shrugs and melts back into shadow. 'Your loss. I'll find another buyer.'"},
         )},
        {"name": "Riddling Oracle",
         "narrative": "A blind woman sits cross-legged on the ground, head tilted as if listening to something you can't hear. 'Ask a question,' she says. 'I'll answer in riddles, because the truth is too sharp to say plainly.'",
         "choices": (
             {"label": "Ask about the Crown", "text": "'The Crown,' she muses. 'What breaks when you strike it against its own throne? What dies when it remembers what it was?' She smiles. 'You already know the answer. You just haven't believed it yet.'",
              "reward": {"type": "info", "text": "The oracle's riddle hints at how to destroy the Crown — striking it against the throne while its host remembers."}},
             {"label": "Ask about the path ahead", "text": "'The shortest path is the most watched. The longest is the safest. The one nobody takes is the one you should.' She tilts her head. 'But that's not really a riddle, is it?'"},
         )},
        {"name": "Talking Skull with Conditions",
         "narrative": "A human skull sits on a pedestal, eye sockets glowing faintly. 'I know what you seek,' it says in a dry, papery voice. 'I'll tell you. But first, you must answer MY question. What is the sound of one hand clapping?'",
         "choices": (
             {"label": "Clap with one hand", "text": "You snap your fingers. The skull stares for a long moment, then erupts in dry, rattling laughter. 'Acceptable! Very well — the ward chapel in the citadel still holds. Rest there. The Crown cannot reach inside.'",
              "reward": {"type": "info", "text": "The skull confirms the war chapel in the citadel is a safe haven, protected by ancient wards."}},
             {"label": "Refuse to play games", "text": "'I don't have time for riddles.' The skull's glow dims. 'Pity. Everyone's always in such a rush to die.' It falls silent and refuses to speak again."},
         )},
    ]),

    # ═══════════════════════════════════════════════════════════════
    #  COMBAT TRIGGERS  (86–95)
    # ═══════════════════════════════════════════════════════════════

    _e(86, "Ambush", "combat_hint", _ALL, _NO_WATER_WALL, [
        {"name": "Goblin Drop Attack",
         "narrative": "Something moves in the branches above — small, quick, multiple somethings. The glint of crude weapons. An ambush, spotted just in time. They haven't realized you've noticed.",
         "skill_check": {"skill": "Perception", "dc": 12},
         "success_text": "You count four — two in the trees, two behind the rocks. They're waiting for you to pass underneath. Knowing their positions gives you the advantage."},
        {"name": "Bandit Roadblock",
         "narrative": "A fallen tree blocks the path — too cleanly cut to be natural. Movement in the brush on both sides. 'Toll road,' a voice calls. 'Everything you've got, and you walk away. Fair deal, considering.'"},
        {"name": "Undead Rising from the Ground",
         "narrative": "The soil shifts. A hand breaks the surface — grey, decayed, grasping. Then another. The dead are climbing out of the earth, slow but relentless, drawn by the warmth of living blood."},
    ]),

    _e(87, "Territorial Beast", "combat_hint", _ALL, _NO_WATER_WALL, [
        {"name": "Owlbear Den",
         "narrative": "A musky, animal stench fills the air. Bones litter the ground — cracked and sucked clean. This is a den. From the darkness ahead, a deep, rattling hoot echoes. The owner is home.",
         "skill_check": {"skill": "Nature", "dc": 12},
         "success_text": "Owlbear territory markers — claw marks on trees, scent markings. The den is thirty feet ahead. Backing away slowly and quietly is your best option."},
        {"name": "Displacer Beast Hunting Ground",
         "narrative": "The prey animals are gone. Not hidden — gone. And the silence has a watchful quality. Then you see it: a shimmer in the air, like heat haze, moving against the wind. Something is hunting here. Something invisible."},
        {"name": "Giant Spider Lair",
         "narrative": "Silk threads glitter between the trees, forming a canopy of death. Wrapped bundles hang at intervals — some animal-sized, some disturbingly human-shaped. The webs vibrate with distant movement."},
    ]),

    _e(88, "Animated Object", "combat_hint", _ALL, _NO_WATER_WALL, [
        {"name": "Living Armor",
         "narrative": "A suit of plate armor stands in an alcove, posed as decoration. As you pass, the helmet turns to follow you. A gauntlet clenches. Steel screams against steel as it steps off its pedestal."},
        {"name": "Possessed Furniture",
         "narrative": "The chair moves. Not falls — moves. It drags itself across the floor on its own legs, positioning between you and the door. The table follows. The room is rearranging itself, and not in your favor."},
        {"name": "Dancing Swords",
         "narrative": "Three swords hang on a wall rack, gleaming. As you approach, the first lifts from its hooks and hangs in the air, point toward you. The second follows. Then the third. They wait, hovering, patient."},
    ]),

    _e(89, "Patrol Encounter", "combat_hint", _ALL, _NO_WATER_WALL, [
        {"name": "Orc Scouts",
         "narrative": "Heavy bootprints in the mud, still filling with water. Fresh. A guttural voice carries on the wind — commands in a harsh language. A scouting party, moving parallel to your path."},
        {"name": "Drow Reconnaissance",
         "narrative": "You almost miss them — dark figures moving with liquid grace through the shadows. Their white hair catches the light for just a moment before they vanish. They definitely saw you first."},
        {"name": "Hobgoblin Regulars",
         "narrative": "The rhythmic stamp of boots in formation echoes ahead. A squad of hobgoblins marches in disciplined ranks, weapons at the ready. Their officer scans the terrain with practiced efficiency."},
    ]),

    _e(90, "Summoning Gone Wrong", "combat_hint", _ALL, _NO_WATER_WALL, [
        {"name": "Loose Imp",
         "narrative": "A small, cackling creature darts between cover, leaving tiny scorch marks wherever it touches. Nearby, a scorched summoning circle tells the story — someone called this thing up and lost control."},
        {"name": "Unbound Elemental",
         "narrative": "A vortex of wind and debris spins in place, moaning like a living thing. The remnants of binding runes glow on the floor around it, broken. The elemental is free, confused, and angry."},
        {"name": "Failed Golem (erratic)",
         "narrative": "A stone construct lurches in a circle, one arm swinging wildly. Its rune-inscribed forehead flickers — the animation spell is corrupted. It's not hostile, exactly. It's broken. And strong enough to crush stone walls."},
    ]),

    _e(91, "Trap + Creature Combo", "combat_hint", _ALL, _NO_WATER_WALL, [
        {"name": "Pit Opens Into Monster Pen",
         "narrative": "The floor ahead is suspiciously clean — no dust, no debris. The stones are slightly different in color. Below, something growls. This isn't just a pit trap. It's a pit trap over a cage."},
        {"name": "Alarm Triggers Reinforcements",
         "narrative": "A tripwire stretches across the corridor at ankle height, connected to a brass bell. Simple, effective, and clearly maintained. Whatever patrol it summons won't be far.",
         "skill_check": {"skill": "Perception", "dc": 11},
         "success_text": "You spot the wire before touching it. Stepping over it carefully, you can proceed without alerting whatever comes when the bell rings."},
        {"name": "Net Trap + Archer Ambush",
         "narrative": "A large net is rigged above the path, its release mechanism hidden in the branches. From a vantage point beyond the net, arrow slits have been carved into the rock. A kill box, waiting to be sprung."},
    ]),

    _e(92, "Duel Challenge", "combat_hint", _ALL, _NO_WATER_WALL, [
        {"name": "Honor-Bound Knight",
         "narrative": "A knight in polished armor stands at the center of a cleared area, sword planted point-first in the ground. 'None shall pass without meeting my blade. One against one. To first blood or yield.' Their eyes are calm and certain."},
        {"name": "Drunk Brawler",
         "narrative": "A massive figure sways on their feet, fists the size of hams. 'YOU,' they slur, pointing. 'You look like you think you're tough. Let's find out.' They crack their knuckles with genuine menace."},
        {"name": "Dueling Ghost",
         "narrative": "A spectral figure salutes with a rapier, executing a textbook fencer's bow. 'I died with a challenge unanswered,' it says calmly. 'Grant me this, and I will find peace. Refuse, and I will remain. Forever.'"},
    ]),

    _e(93, "Corruption Manifestation", "combat_hint", _ALL, _NO_WATER_WALL, [
        {"name": "Shadow Spawn",
         "narrative": "The shadows in the corner are too dark. They don't thin at the edges. And they're moving — slowly, like oil, sliding across the floor toward you. Where they touch the light, it dims."},
        {"name": "Blighted Treant",
         "narrative": "What you thought was a dead tree unfolds. Branches crack and reshape into arms. The trunk splits into a mockery of a face — bark eyes glowing sickly green. The blight has animated the forest itself."},
        {"name": "Ooze from Cursed Well",
         "narrative": "A well in the ground bubbles with thick, dark liquid that moves against gravity — climbing the stones, reaching for the rim. It's not water. It's not alive. But it wants out."},
    ]),

    _e(94, "Pest Infestation", "combat_hint", _ALL, _NO_WATER_WALL, [
        {"name": "Kobold Warrens",
         "narrative": "Small tunnels riddle the walls — too small for humans, perfect for kobolds. Tiny eyes glint in the darkness. High-pitched chatter echoes from multiple directions. You're surrounded, but they seem more curious than hostile."},
        {"name": "Stirge Nest",
         "narrative": "Leathery wings flutter in the dark above. Dozens of mosquito-like creatures cling to the ceiling, proboscises twitching. Stirges — blood drinkers. They haven't noticed you yet. Moving quietly would be wise."},
        {"name": "Myconid Cluster",
         "narrative": "Mushroom-like creatures stand in a loose circle, swaying gently. Spores drift between them in a visible cloud. They seem peaceful — communicating, perhaps. Disturbing them would release a massive spore burst."},
    ]),

    _e(95, "Boss Foreshadow", "combat_hint", _ALL, _NO_WATER_WALL, [
        {"name": "Minion Fleeing Toward Boss",
         "narrative": "A terrified creature stumbles past you, running full tilt in the direction of the citadel. 'The master will protect me! The master will —' It doesn't even register your presence. Whatever scared it is behind you."},
        {"name": "Warning Totems",
         "narrative": "Crude totems line both sides of the path — skulls on stakes, bloody rags, bone chimes. The message is clear: you are approaching something's territory, and it wants you to know the cost of trespass."},
        {"name": "Fresh Kill Left as Message",
         "narrative": "A large animal lies eviscerated in the path — not eaten, just killed and opened. Displayed. The cuts are deliberate, almost surgical. This isn't predation. It's a warning. 'I can do this. To anything.'"},
    ]),

    # ═══════════════════════════════════════════════════════════════
    #  MISCELLANEOUS & WEIRD  (96–100)
    # ═══════════════════════════════════════════════════════════════

    _e(96, "Time Anomaly", "weird", _ALL, (), [
        {"name": "Campfire Still Warm",
         "narrative": "A campfire crackles cheerfully, flames dancing. But the logs are stone, fossilized mid-burn. The fire is warm and gives light. The fire has been burning for a hundred years, consuming nothing.",
         "skill_check": {"skill": "Arcana", "dc": 13},
         "success_text": "A temporal loop — a moment preserved in amber time. The fire will never go out because for it, no time passes. Someone froze this moment, deliberately, as a beacon or a memorial."},
        {"name": "Aging Flowers in Seconds",
         "narrative": "A flower pushes through the soil, blooms, wilts, and crumbles to dust — all in the space of ten heartbeats. Another sprouts in its place and begins the same accelerated life cycle."},
        {"name": "Reversed Footprints",
         "narrative": "Footprints in the dust walk backward — heel landing first, toe pushing off last. They lead from a dead end to the entrance, as if someone walked into this space by walking out of it."},
        {"name": "Echo of Future Conversation",
         "narrative": "Voices reach you — your own voices, talking about things that haven't happened yet. 'We should never have opened that door,' one says. 'At least we saved the —' Static drowns the rest."},
    ]),

    _e(97, "Planar Bleed", "weird", _ALL, (), [
        {"name": "Feywild Color Saturation",
         "narrative": "Colors intensify to the point of pain. Green becomes emerald fire. Blue becomes the depth of oceans. Everything is hyperreal, oversaturated, too beautiful. The Feywild is leaking through."},
        {"name": "Shadowfell Greyscale Patch",
         "narrative": "Color drains from the world in a defined area — everything turns to shades of grey. Your skin, your clothes, the ground. Joy dulls. Hope dims. The Shadowfell touches this place."},
        {"name": "Elemental Plane Leak",
         "narrative": "A crack in reality hisses with raw elemental energy — heat, cold, or wind pouring through from somewhere else entirely. The edges of the crack shimmer with impossible colors. It's growing."},
    ]),

    _e(98, "Dream Fragment", "weird", _ALL, (), [
        {"name": "Walking Into Someone Else's Nightmare",
         "narrative": "The world flickers. For a moment, you're somewhere else — a burning village, screaming faces, smoke in your lungs. Then you're back. Your heart pounds. That wasn't your memory. Whose was it?"},
        {"name": "Shared Vision of a Past Event",
         "narrative": "Reality peels back. You see this place as it was — bright, busy, alive. People walk through you like ghosts. A child laughs. A merchant argues over prices. Then it's gone, and the ruin returns."},
        {"name": "Prophetic Flash",
         "narrative": "A flash of light, and for one heartbeat you see the future: a crown shattering, a throne cracking, green light dying. Hope — raw and almost painful. Then the vision fades, leaving only its impression."},
    ]),

    _e(99, "Paradox Object", "weird", _ALL, (), [
        {"name": "Key That Unlocks Itself",
         "narrative": "A key lies on the ground next to a small locked box. The key fits the box. Inside the box is the same key. The one in your hand vanishes. Open the box again: the key is inside. Always."},
        {"name": "Book That Writes What You Say",
         "narrative": "An open book on a pedestal, its pages blank. When you speak, words appear — YOUR words, transcribed in perfect calligraphy. The book records everything. It's already filled several pages with your breathing."},
        {"name": "Mirror Showing a Different Room",
         "narrative": "A tall mirror stands against nothing, reflecting a room that doesn't exist — a warm study with a fire, bookshelves, a chair. A figure sits in the chair, reading. They look up. They wave at you."},
        {"name": "Compass Pointing at the Holder",
         "narrative": "A brass compass lies on the ground. When you pick it up, the needle swings... to point at you. Turn any direction — it follows. Set it down, walk away, look back: still pointing at you."},
    ]),

    _e(100, "The Nothing", "weird", _ALL, (), [
        {"name": "Tile of Absolute Silence",
         "narrative": "Sound ceases. Not fades — ceases. Your footsteps, your heartbeat, your thoughts all go silent. The world becomes a painting. You move through it like a ghost through a dream."},
        {"name": "Void Spot",
         "narrative": "A patch of... nothing. Not darkness — the absence of anything. Your eyes slide off it. Your mind refuses to process it. It's there, a hole in reality the size of a dinner plate, and it is deeply, fundamentally wrong."},
        {"name": "Space That Feels Skipped Over",
         "narrative": "You step forward and you're ten feet ahead of where you should be. The space between simply didn't happen. Looking back, the ground you 'crossed' is undisturbed. You didn't walk through it. You skipped it, like a scratch on a record."},
    ]),
]

# Build the lookup dict
SIDE_EVENTS: dict[int, SideEvent] = {ev.event_id: ev for ev in _EVENTS}


def get_event(event_id: int) -> SideEvent | None:
    return SIDE_EVENTS.get(event_id)


def is_terrain_compatible(event: SideEvent, terrain: str) -> bool:
    terrain = terrain.upper()
    if terrain in event.terrain_deny:
        return False
    if event.terrain_allow and terrain not in event.terrain_allow:
        return False
    return True


# ── Interaction system ─────────────────────────────────────────────

SKILL_TO_ABILITY: dict[str, str] = {
    "Perception": "Wisdom",
    "Nature": "Wisdom",
    "Survival": "Wisdom",
    "Insight": "Wisdom",
    "Arcana": "Intelligence",
    "History": "Intelligence",
    "Investigation": "Intelligence",
    "Religion": "Intelligence",
    "Athletics": "Strength",
    "Acrobatics": "Dexterity",
    "Stealth": "Dexterity",
    "Wisdom": "Wisdom",
    "Dexterity": "Dexterity",
    "Constitution": "Constitution",
}


def get_interaction_type(event: SideEvent, variant: SideEventVariant) -> str:
    """Resolve the interaction primitive for a variant.

    Returns one of: "choice", "salvage", "skill_check", "examine".
    """
    if variant.choices:
        return "choice"
    if variant.skill_check and variant.reward:
        return "salvage"
    if variant.skill_check:
        return "skill_check"
    return "examine"

from enum import Enum
from random import Random
from typing import Iterable, Dict, Any, Set

LOBBY_NPCS = ["Codex", "Merlin", "Hintmaster", "Janitor", "Diamond Dealer"]
EXTRA_MODES = {
    "base": ["No Beat", "Double Tempo", "Low Percent"],
    "amplified": ["Phasing", "Randomizer", "Mystery", "Hard", "No Return"],
}

class DLC(Enum):
    BASE = "base"
    AMPLIFIED = "amplified"
    SYNCHRONY = "synchrony"
    MIKU = "miku"
    SHOVEL_KNIGHT = "shovel knight"

def normalize_dlc(dlc: Iterable[str]) -> set[DLC]:
    return {DLC(d.lower()) for d in dlc}


def assign_caged_npcs(random: Random, dlc: Set[str]) -> Dict[str, Dict[str, Any]]:
    zones = [1, 2, 3, 4, 5] if "Amplified" in dlc else [1, 2, 3, 4]
    levels = [1, 2, 3]

    # Distribute zones as evenly as possible
    npc_zones = [zones[i % len(zones)] for i in range(len(LOBBY_NPCS))]
    random.shuffle(npc_zones)

    # Random levels
    npc_levels = [random.choice(levels) for _ in LOBBY_NPCS]

    # Ensure each unlockType is used at least once
    unlock_types = ["Shop", "Dig", "Glass"]
    remaining = len(LOBBY_NPCS) - len(unlock_types)

    # Fill remaining with weighted random choices
    weighted_choices = random.choices(
        ["Shop", "Dig", "Glass"],
        weights=[0.6, 0.3, 0.1],
        k=remaining
    )

    # Combine guaranteed + random
    all_unlocks = unlock_types + weighted_choices
    random.shuffle(all_unlocks)

    # Adjust levels so Glass is only on 2 or 3
    adjusted_levels = []
    for level, unlock in zip(npc_levels, all_unlocks):
        if unlock == "Glass" and level == 1:
            level = random.choice([2, 3])
        adjusted_levels.append(level)

    return {
        npc: {
            "zone": zone,
            "level": level,
            "unlockType": unlock_type
        }
        for npc, zone, level, unlock_type in zip(LOBBY_NPCS, npc_zones, adjusted_levels, all_unlocks)
    }

character_requirements = {
    "Melody": {"Golden Lute"},
    "Aria": {"Potion", "Nazar Charm"},
    "Dorian": {"Boots of Leaping", "Dorian's Plate Armor"},
    "Eli": {"Eli's Hand"},
    "Monk": {"Blood Shovel"},
    "Bolt": {"Spear"},
    "Dove": {"Flower", "Ring of Peace"},
    "Nocturna": {"Cutlass", "Transform Spell"},
    "Mary": {"Spear", "Cookies", "Nazar Charm"},
    "Tempo": {"Blood Material", "Compass"},
    "Klarinetta": {"Zweihander", "Shiny Armor", "Nazar Charm"},
    "Chaunter": {"Lantern"},
    "Suzu": {"Lance of Courage"},
    "Hatsune Miku": {"Leek", "Virtual Armor"},
    "Shovel Knight": {"Shovel Blade"}
}

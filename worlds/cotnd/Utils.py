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
    zones = [1, 2, 3, 4, 5] if "amplified" in dlc else [1, 2, 3, 4]
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
    "Hatsune Miku": {"Leek", "Virtual Armor", "Sing Spell"},
    "Shovel Knight": {"Shovel Blade"}
}

trap_name_to_value = {
    "144p Trap": "144p Trap",
    "Aaa Trap": "Aaa Trap",
    "Animal Trap": "Animal Trap",
    "Animal Bonus Trap": None,
    "Army Trap": "Armadillo Trap",
    "Bald Trap": "Bald Trap",
    "Banana Peel Trap": "Slip Trap",
    "Banana Trap": "Slip Trap",
    "Banner Trap": None,
    "Bee Trap": None,
    "Blue Balls Curse": "Instant Death Trap",
    "Bomb": "Bomb Trap",
    "Bomb Trap": "Bomb Trap",
    "Bonk Trap": "Bonk Trap",
    "Breakout Trap": None,
    "Bubble Trap": "Freeze Trap",
    "Bullet Time Trap": "Freeze Trap",
    "Burn Trap": "Burn Trap",
    "Buyon Trap": "Beetle Trap",
    "Camera Rotate Trap": "Camera Trap",
    "Chaos Trap": "Chaos Trap",
    "Chaos Control Trap": "Freeze Trap",
    "Chart Modifier Trap": "Tempo Trap",
    "Chaser Trap": "Haunted Shopkeeper Trap",
    "Clear Image Trap": None,
    "Confound Trap": "Confusion Trap",
    "Confuse Trap": "Confusion Trap",
    "Confusion Trap": "Confusion Trap",
    "Control Ball Trap": None,
    "Controller Drift Trap": None,
    "Cursed Ball Trap": None,
    "Cutscene Trap": "Cutscene Trap",
    "Damage Trap": "Damage Trap",
    "Deisometric Trap": "Isometric Trap",
    "Depletion Trap": "Disarm Trap",
    "Disable A Trap": "Disable Trap",
    "Disable B Trap": "Disable Trap",
    "Disable C Up Trap": "Disable Trap",
    "Disable Tag Trap": "Disable Trap",
    "Disable Z Trap": "Disable Trap",
    "Disarm Trap": "Disarm Trap",
    "Double Damage": "Double Damage Trap",
    "Dry Trap": "Disarm Trap",
    "Eject Ability": "Disarm Trap",
    "Electrocution Trap": None,
    "Empty Item Box Trap": "Disarm Trap",
    "Enemy Ball Trap": None,
    "Energy Drain Trap": "Disarm Trap",
    "Expensive Stocks": "Cursed Trap",
    "Explosion Trap": "Bomb Trap",
    "Exposition Trap": "Exposition Trap",
    "Extreme Chaos Mode": None,
    "Fake Transition": "Fake Transition Trap",
    "Fast Trap": "Fast Trap",
    "Fear Trap": None,
    "Fire Trap": "Burn Trap",
    "Fish Eye Trap": None,
    "Fishing Trap": None,
    "Fishin' Boo Trap": None,
    "Flip Horizontal Trap": "Flip Horizontal Trap",
    "Flip Trap": "Flip Horizontal Trap",
    "Flip Vertical Trap": "Flip Vertical Trap",
    "Frame Slime Trap": "Frame Slime Trap",
    "Freeze Trap": "Freeze Trap",
    "Frog Trap": None,
    "Frost Trap": "Freeze Trap",
    "Frozen Trap": "Freeze Trap",
    "Fuzzy Trap": None,
    "Gadget Shuffle Trap": "Transmute Trap",
    "Gas Trap": "Confusion Trap",
    "Get Out Trap": "Timer Trap",
    "Ghost": "Haunted Shopkeeper Trap",
    "Ghost Chat": None,
    "Gooey Bag": "Slime Player Trap",
    "Gravity Trap": "Ice Floor Trap",
    "Help Trap": "Help Trap",
    "Hey! Trap": None,
    "Hiccup Trap": "Hiccup Trap",
    "Home Trap": "Home Trap",
    "Honey Trap": "Tar Trap",
    "Ice Floor Trap": "Ice Floor Trap",
    "Ice Trap": "Freeze Trap",
    "Icy Hot Pants Trap": None,
    "Input Sequence Trap": None,
    "Instant Crystal Trap": None,
    "Instant Death Trap": "Instant Death Trap",
    "Invert Colors Trap": None,
    "Inverted Mouse Trap": "Confusion Trap",
    "Invisiball Trap": None,
    "Invisible Trap": "Invisible Trap",
    "Invisibility Trap": "Invisible Trap",
    "Iron Boots Trap": "Slow Trap",
    "Items to Bombs": "Bomb Trap",
    "Jump Trap": "Jump Trap",
    "Jumping Jacks Trap": "Jump Trap",
    "Laughter Trap": "Laughter Trap",
    "Light Up Path Trap": None,
    "Literature Trap": "Exposition Trap",
    "Mana Drain Trap": "Disarm Trap",
    "Market Crash Trap": "Market Crash Trap",
    "Math Quiz Trap": None,
    "Meteor Trap": "Meteor Trap",
    "Metronome Trap": "Timer Trap",
    "Mirror Trap": "Flip Horizontal Trap",
    "Monkey Mash Trap": "Monkey Trap",
    "My Turn! Trap": "My Turn Trap",
    "Ninja Trap": None,
    "No Guarding": "Commando Trap",
    "No Petals": "Satiated Trap",
    "No Revivals": "No Revivals Trap",
    "No Stocks": None,
    "No Vac Trap": "Disable Trap",
    "Number Sequence Trap": None,
    "Nut Trap": None,
    "OmoTrap": "Help Trap",
    "One Hit KO": "One Hit Trap",
    "Paper Trap": "Paper Trap",
    "Paralyze Trap": None,
    "Paralysis Trap": None,
    "Person Trap": "Person Trap",
    "Phone Trap": "Help Trap",
    "Pie Trap": "Slip Trap",
    "Pinball Trap": None,
    "Pixelate Trap": None,
    "Pixellation Trap": None,
    "Poison Mushroom": "Shrink Trap",
    "Poison Trap": None,
    "Pokemon Count Trap": None,
    "Pokemon Trivia Trap": None,
    "Police Trap": None,
    "PONG Challenge": None,
    "Pong Trap": None,
    "Posession Trap": None,
    "PowerPoint Trap": "Slow Trap",
    "Push Trap": "Leaping Trap",
    "Radiation Trap": None,
    "Rail Trap": "Ice Floor Trap",
    "Ranch Trap": "Home Trap",
    "Random Status Trap": None,
    "Resistance Trap": "Timer Trap",
    "Reversal Trap": "Confusion Trap",
    "Reverse Controls Trap": "Confusion Trap",
    "Reverse Trap": "Confusion Trap",
    "Rockfall Trap": "Earth Trap",
    "Sandstorm Trap": "Earth Trap",
    "Screen Flip Trap": "Flip Horizontal Trap",
    "Shake Trap": "Shake Trap",
    "Sleep Trap": None,
    "Slip Trap": "Slip Trap",
    "Slime Player Trap": "Slime Player Trap",
    "Slow Trap": "Slow Trap",
    "Slowness Trap": "Slow Trap",
    "Snake Trap": None,
    "Spam Trap": "My Turn Trap",
    "Spike Ball Trap": None,
    "Spooky Time": "Skeleton Trap",
    "Spotlight Trap": "Spotlight Trap",
    "Spring Trap": None,
    "Squash Trap": "Bonk Trap",
    "Sticky Floor Trap": "Tar Trap",
    "Sticky Hands Trap": "Sticky Hands Trap",
    "Stun Trap": "Confusion Trap",
    "SvC Effect": None,
    "Swap Trap": "Swap Trap",
    "Tarr Trap": "Tar Trap",
    "Teleport Trap": "Teleport Trap",
    "Text Trap": "Help Trap",
    "Thwimp Trap": None,
    "Time Limit": "Timer Trap",
    "Time Warp Trap": "Timer Trap",
    "Timer Trap": "Timer Trap",
    "Tiny Trap": "Shrink Trap",
    "Tip Trap": "Help Trap",
    "TNT Barrel Trap": "Bomb Trap",
    "TNT Trap": "Bomb Trap",
    "Tool Swap Trap": "Transmute Trap",
    "Trivia Trap": None,
    "Tutorial Trap": "Tutorial Trap",
    "Underwater Trap": None,
    "Undo Trap": "Undo Trap",
    "UNO Challenge": None,
    "W I D E Trap": "W I D E Trap",
    "Whirlpool Trap": None,
    "Whoops! Trap": "Disarm Trap",
    "Zoom In Trap": "Zoom In Trap",
    "Zoom Out Trap": "Zoom Out Trap",
    "Zoom Trap": "Zoom In Trap",
}

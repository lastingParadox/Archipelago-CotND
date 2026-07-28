import json
import pkgutil
import re
from enum import Enum
from random import Random
from typing import Iterable, Dict, Any, Set

# Minimum AP Redux mod version this apworld will accept a connection from.
# Kept in archipelago.json (next to world_version)
_archipelago_metadata: dict = json.loads(
    pkgutil.get_data(__name__, "archipelago.json") or b"{}"
)
MIN_MOD_VERSION: str = _archipelago_metadata.get("minimum_mod_version", "0.0.0")


def parse_version(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", version or ""))


def version_at_least(actual: str, minimum: str) -> bool:
    if actual == "":
        return False
    return parse_version(actual) >= parse_version(minimum)


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
    "Hatsune Miku": {"Spring Onion", "Virtual Armor", "Sing Spell"},
    "Shovel Knight": {"Shovel Blade"}
}

# Maps incoming TrapLink trap names to a CotND trap handler.
# Values are one of:
#   None                        - recognised but unimplemented; silently dropped
#   "HandlerId"                 - queued in the mod under that TrapHandler ID
#   ("HandlerId", {args})       - queued with handler-specific args,
#                                 e.g. ("SummonTrap", {"variant": "Beetle"})
# Handler IDs that belong to a pool item respect that item's trap_weights entry;
# TrapLink-only handlers respect the traplink_excluded_traps option instead.
trap_name_to_value = {
    "144p Trap": "144pTrap",
    "Aaa Trap": "AaaTrap",
    "Animal Trap": "AnimalTrap",
    "Animal Bonus Trap": None,
    "Army Trap": ("SummonTrap", {"variant": "Armadillo"}),
    "Bald Trap": "BaldTrap",
    "Banana Peel Trap": "SlipTrap",
    "Banana Trap": "SlipTrap",
    "Banner Trap": None,
    "Bee Trap": None,
    "Blue Balls Curse": "InstantDeathTrap",
    "Bomb": "BombTrap",
    "Bomb Trap": "BombTrap",
    "Bonk Trap": "BonkTrap",
    "Breakout Trap": None,
    "Bubble Trap": ("FreezeTrap", {"variant": "Ice"}),
    "Bullet Time Trap": ("FreezeTrap", {"variant": "Ice"}),
    "Burn Trap": "BurnTrap",
    "Buyon Trap": ("SummonTrap", {"variant": "Beetle"}),
    "Camera Rotate Trap": ("CameraTrap", {"variant": "Rotate"}),
    "Camera Trap": "CameraTrap",
    "Chaos Trap": "ChaosTrap",
    "Chaos Control Trap": ("FreezeTrap", {"variant": "Ice"}),
    "Chart Modifier Trap": "TempoTrap",
    "Chaser Trap": "HauntedShopkeeperTrap",
    "Clear Image Trap": None,
    "Confound Trap": "ConfusionTrap",
    "Confuse Trap": "ConfusionTrap",
    "Confusion Trap": "ConfusionTrap",
    "Control Ball Trap": None,
    "Controller Drift Trap": None,
    "Cursed Ball Trap": None,
    "Cursed Trap": "CursedTrap",
    "Cutscene Trap": "CutsceneTrap",
    "Dad Trap": "DadTrap",
    "Damage Trap": "DamageTrap",
    "Dead Ringer Trap": "DeadRingerTrap",
    "Deisometric Trap": "IsometricTrap",
    "Depletion Trap": "DisarmTrap",
    "Disable A Trap": "DisableTrap",
    "Disable B Trap": "DisableTrap",
    "Disable C Up Trap": "DisableTrap",
    "Disable Tag Trap": "DisableTrap",
    "Disable Z Trap": "DisableTrap",
    "Disarm Trap": "DisarmTrap",
    "Double Damage": "DoubleDamageTrap",
    "Double Damage Trap": "DoubleDamageTrap",
    "Dry Trap": "DisarmTrap",
    "Earth Trap": "EarthTrap",
    "Eject Ability": "DisarmTrap",
    "Electrocution Trap": None,
    "Empty Item Box Trap": "DisarmTrap",
    "Enemy Ball Trap": None,
    "Energy Drain Trap": "DisarmTrap",
    "Expensive Stocks": "CursedTrap",
    "Explosion Trap": "BombTrap",
    "Exposition Trap": "ExpositionTrap",
    "Extreme Chaos Mode": None,
    "Fake Transition": "FakeTransitionTrap",
    "Fast Trap": ("TempoTrap", {"variant": "Fast"}),
    "Fear Trap": None,
    "Fire Trap": "BurnTrap",
    "Fish Eye Trap": None,
    "Fishing Trap": None,
    "Fishin' Boo Trap": None,
    "Flip Horizontal Trap": ("CameraTrap", {"variant": "FlipHorizontal"}),
    "Flip Trap": ("CameraTrap", {"variant": "FlipHorizontal"}),
    "Flip Vertical Trap": ("CameraTrap", {"variant": "FlipVertical"}),
    "Frame Slime Trap": "FrameSlimeTrap",
    "Freeze Trap": ("FreezeTrap", {"variant": "Ice"}),
    "Frog Trap": None,
    "Frost Trap": ("FreezeTrap", {"variant": "Ice"}),
    "Frozen Trap": ("FreezeTrap", {"variant": "Ice"}),
    "Fuzzy Trap": None,
    "Gadget Shuffle Trap": "TransmuteTrap",
    "Gas Trap": "ConfusionTrap",
    "Get Out Trap": "TimerTrap",
    "Ghost": "HauntedShopkeeperTrap",
    "Ghost Chat": None,
    "Gold Scatter Trap": "GoldScatterTrap",
    "Gooey Bag": "SlimePlayerTrap",
    "Gravity Trap": "IceFloorTrap",
    "Haunted Shopkeeper Trap": "HauntedShopkeeperTrap",
    "Help Trap": "HelpTrap",
    "Hey! Trap": None,
    "Hiccup Trap": "HiccupTrap",
    "Home Trap": "HomeTrap",
    "Honey Trap": "TarTrap",
    "Hot Coals Trap": "BurnTrap",
    "Ice Floor Trap": "IceFloorTrap",
    "Ice Trap": ("FreezeTrap", {"variant": "Ice"}),
    "Icy Hot Pants Trap": None,
    "Input Sequence Trap": None,
    "Instant Crystal Trap": None,
    "Instant Death Trap": "InstantDeathTrap",
    "Invert Colors Trap": None,
    "Inverted Mouse Trap": "ConfusionTrap",
    "Invisiball Trap": None,
    "Invisible Trap": "InvisibleTrap",
    "Invisibility Trap": "InvisibleTrap",
    "Iron Boots Trap": ("TempoTrap", {"variant": "Slow"}),
    "Isometric Trap": "IsometricTrap",
    "Items to Bombs": "BombTrap",
    "Jump Trap": "JumpTrap",
    "Jumping Jacks Trap": "JumpTrap",
    "Laughter Trap": "LaughterTrap",
    "Leaping Trap": "LeapingTrap",
    "Light Up Path Trap": None,
    "Literature Trap": "ExpositionTrap",
    "Mana Drain Trap": "DisarmTrap",
    "Market Crash Trap": "MarketCrashTrap",
    "Math Quiz Trap": None,
    "Meteor Trap": "MeteorTrap",
    "Metronome Trap": "TimerTrap",
    "Mirror Trap": ("CameraTrap", {"variant": "FlipHorizontal"}),
    "Monkey Mash Trap": "MonkeyTrap",
    "Monkey Trap": "MonkeyTrap",
    "My Turn! Trap": "MyTurnTrap",
    "Ninja Trap": None,
    "No Guarding": "CommandoTrap",
    "No Petals": "SatiatedTrap",
    "No Return Trap": "NoReturnTrap",
    "No Revivals": "NoRevivalsTrap",
    "No Stocks": None,
    "No Vac Trap": "DisableTrap",
    "Number Sequence Trap": None,
    "Nut Trap": None,
    "OmoTrap": "HelpTrap",
    "One Hit KO": "OneHitTrap",
    "One Hit Trap": "OneHitTrap",
    "Paper Trap": "PaperTrap",
    "Paralyze Trap": None,
    "Paralysis Trap": None,
    "Person Trap": ("SummonTrap", {"variant": "Person"}),
    "Phone Trap": "HelpTrap",
    "Pie Trap": "SlipTrap",
    "Pinball Trap": None,
    "Pixelate Trap": None,
    "Pixellation Trap": None,
    "Poison Mushroom": "ShrinkTrap",
    "Poison Trap": None,
    "Pokemon Count Trap": None,
    "Pokemon Trivia Trap": None,
    "Police Trap": None,
    "PONG Challenge": None,
    "Pong Trap": None,
    "Posession Trap": None,
    "PowerPoint Trap": ("TempoTrap", {"variant": "Slow"}),
    "Push Trap": "LeapingTrap",
    "Radiation Trap": None,
    "Rail Trap": "IceFloorTrap",
    "Ranch Trap": "HomeTrap",
    "Random Status Trap": None,
    "Resistance Trap": "TimerTrap",
    "Reversal Trap": "ConfusionTrap",
    "Reverse Controls Trap": "ConfusionTrap",
    "Reverse Trap": "ConfusionTrap",
    "Rockfall Trap": "EarthTrap",
    "Sandstorm Trap": "EarthTrap",
    "Screen Flip Trap": ("CameraTrap", {"variant": "FlipHorizontal"}),
    "Shake Trap": "ShakeTrap",
    "Shrink Trap": "ShrinkTrap",
    "Sleep Trap": None,
    "Slip Trap": "SlipTrap",
    "Slime Player Trap": "SlimePlayerTrap",
    "Slow Trap": ("TempoTrap", {"variant": "Slow"}),
    "Slowness Trap": ("TempoTrap", {"variant": "Slow"}),
    "Snake Trap": None,
    "Spam Trap": "MyTurnTrap",
    "Spike Ball Trap": None,
    "Spooky Time": ("SummonTrap", {"variant": "Skeleton"}),
    "Spotlight Trap": "SpotlightTrap",
    "Spring Trap": None,
    "Squash Trap": "BonkTrap",
    "Sticky Floor Trap": "TarTrap",
    "Sticky Hands Trap": "StickyHandsTrap",
    "Stone Trap": ("FreezeTrap", {"variant": "Stone"}),
    "Stun Trap": "ConfusionTrap",
    "Summon Trap": "SummonTrap",
    "SvC Effect": None,
    "Swap Trap": "SwapTrap",
    "Tar Trap": "TarTrap",
    "Tarr Trap": "TarTrap",
    "Teleport Trap": "TeleportTrap",
    "Tempo Trap": "TempoTrap",
    "Text Trap": "HelpTrap",
    "Thwimp Trap": None,
    "Time Limit": "TimerTrap",
    "Time Warp Trap": "TimerTrap",
    "Timer Trap": "TimerTrap",
    "Tiny Trap": "ShrinkTrap",
    "Tip Trap": "HelpTrap",
    "TNT Barrel Trap": "BombTrap",
    "TNT Trap": "BombTrap",
    "Tool Swap Trap": "TransmuteTrap",
    "Transmute Trap": "TransmuteTrap",
    "Trivia Trap": None,
    "Tutorial Trap": "TutorialTrap",
    "Underwater Trap": None,
    "Undo Trap": "UndoTrap",
    "UNO Challenge": None,
    "Vintage Trap": None,
    "W I D E Trap": "WideTrap",
    "Weather Cloudy Trap": None,
    "Weather Rainy Trap": None,
    "Weather Stormy Trap": None,
    "Weather Sunny Trap": None,
    "Well Done Trap": None,
    "Whirlpool Trap": None,
    "Whoops! Trap": "DisarmTrap",
    "Zoom In Trap": ("CameraTrap", {"variant": "ZoomIn"}),
    "Zoom Out Trap": ("CameraTrap", {"variant": "ZoomOut"}),
    "Zoom Trap": ("CameraTrap", {"variant": "ZoomIn"}),
}

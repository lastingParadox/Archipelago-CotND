import math
from collections import defaultdict
from copy import copy
from dataclasses import dataclass
from enum import Enum, auto
from random import Random
from typing import Final, Set, Tuple

from BaseClasses import Item, ItemClassification
from worlds.cotnd.Utils import DLC, normalize_dlc, character_requirements


class CotNDItem(Item):
    game: str = "Crypt of the NecroDancer"


class ItemType(Enum):
    CHARACTER = auto()
    ARMOR = auto()
    HEAD = auto()
    FEET = auto()
    TORCH = auto()
    SHOVEL = auto()
    RING = auto()
    WEAPON = auto()
    SHIELD = auto()
    SPELL = auto()
    SCROLL = auto()
    ACTION = auto()
    MATERIAL = auto()
    MISC = auto()
    UPGRADE = auto()
    FILLER = auto()
    MODE = auto()
    NPC = auto()
    TRAP = auto()


PLURALS: dict[ItemType, str] = {
    ItemType.CHARACTER: "Characters",
    ItemType.ARMOR: "Armors",
    ItemType.HEAD: "Heads",
    ItemType.FEET: "Feet",
    ItemType.TORCH: "Torches",
    ItemType.SHOVEL: "Shovels",
    ItemType.RING: "Rings",
    ItemType.WEAPON: "Weapons",
    ItemType.SHIELD: "Shields",
    ItemType.SPELL: "Spells",
    ItemType.SCROLL: "Scrolls",
    ItemType.ACTION: "Actions",
    ItemType.MATERIAL: "Materials",
    ItemType.MISC: "Misc",
    ItemType.UPGRADE: "Upgrades",
    ItemType.MODE: "Modes",
    ItemType.NPC: "NPCs",
}


class DefaultType(Enum):
    ALWAYS = auto()
    MATERIAL = auto()
    UNIQUE = auto()
    POSSIBLE = auto()
    NEVER = auto()


@dataclass(slots=True)
class RawCotNDItemData:
    name: str
    classification: ItemClassification
    type: ItemType
    cotnd_id: str
    dlc: DLC
    default: DefaultType


@dataclass(slots=True)
class CotNDItemData(RawCotNDItemData):
    code: int


characters: list[RawCotNDItemData] = [
    RawCotNDItemData("Cadence", ItemClassification.progression, ItemType.CHARACTER, "Cadence", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Melody", ItemClassification.progression, ItemType.CHARACTER, "Melody", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Aria", ItemClassification.progression, ItemType.CHARACTER, "Aria", DLC.BASE, DefaultType.NEVER),
    RawCotNDItemData("Dorian", ItemClassification.progression, ItemType.CHARACTER, "Dorian", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Eli", ItemClassification.progression, ItemType.CHARACTER, "Eli", DLC.BASE, DefaultType.NEVER),
    RawCotNDItemData("Monk", ItemClassification.progression, ItemType.CHARACTER, "Monk", DLC.BASE, DefaultType.NEVER),
    RawCotNDItemData("Dove", ItemClassification.progression, ItemType.CHARACTER, "Dove", DLC.BASE, DefaultType.NEVER),
    RawCotNDItemData("Coda", ItemClassification.progression, ItemType.CHARACTER, "Coda", DLC.BASE, DefaultType.NEVER),
    RawCotNDItemData("Bolt", ItemClassification.progression, ItemType.CHARACTER, "Bolt", DLC.BASE, DefaultType.NEVER),
    RawCotNDItemData("Bard", ItemClassification.progression, ItemType.CHARACTER, "Bard", DLC.BASE, DefaultType.NEVER),
    RawCotNDItemData("Nocturna", ItemClassification.progression, ItemType.CHARACTER, "Nocturna", DLC.AMPLIFIED,
                     DefaultType.NEVER),
    RawCotNDItemData("Diamond", ItemClassification.progression, ItemType.CHARACTER, "Diamond", DLC.AMPLIFIED,
                     DefaultType.NEVER),
    RawCotNDItemData("Mary", ItemClassification.progression, ItemType.CHARACTER, "Mary", DLC.AMPLIFIED,
                     DefaultType.NEVER),
    RawCotNDItemData("Tempo", ItemClassification.progression, ItemType.CHARACTER, "Tempo", DLC.AMPLIFIED,
                     DefaultType.NEVER),
    RawCotNDItemData("Reaper", ItemClassification.progression, ItemType.CHARACTER, "Reaper", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Klarinetta", ItemClassification.progression, ItemType.CHARACTER, "Sync_Klarinetta",
                     DLC.SYNCHRONY, DefaultType.NEVER),
    RawCotNDItemData("Chaunter", ItemClassification.progression, ItemType.CHARACTER, "Sync_Chaunter", DLC.SYNCHRONY,
                     DefaultType.NEVER),
    RawCotNDItemData("Suzu", ItemClassification.progression, ItemType.CHARACTER, "Sync_Suzu", DLC.SYNCHRONY,
                     DefaultType.NEVER),
    RawCotNDItemData("Hatsune Miku", ItemClassification.progression, ItemType.CHARACTER, "Coldsteel_Coldsteel",
                     DLC.MIKU, DefaultType.NEVER),
    RawCotNDItemData("Shovel Knight", ItemClassification.progression, ItemType.CHARACTER, "Goldman_Goldman",
                     DLC.SHOVEL_KNIGHT, DefaultType.NEVER),
]

armors: list[RawCotNDItemData] = [
    RawCotNDItemData("Leather Armor", ItemClassification.useful, ItemType.ARMOR, "ArmorLeather", DLC.BASE,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Chainmail", ItemClassification.useful, ItemType.ARMOR, "ArmorChainmail", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Plate Armor", ItemClassification.useful, ItemType.ARMOR, "ArmorPlatemail", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Heavy Plate", ItemClassification.useful, ItemType.ARMOR, "ArmorHeavyplate", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Obsidian Armor", ItemClassification.useful, ItemType.ARMOR, "ArmorObsidian", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Glass Armor", ItemClassification.useful, ItemType.ARMOR, "ArmorGlass", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Heavy Glass Armor", ItemClassification.useful, ItemType.ARMOR, "ArmorHeavyglass", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Quartz Armor", ItemClassification.useful, ItemType.ARMOR, "ArmorQuartz", DLC.AMPLIFIED,
                     DefaultType.NEVER),
    RawCotNDItemData("Karate Gi", ItemClassification.useful, ItemType.ARMOR, "ArmorGi", DLC.AMPLIFIED,
                     DefaultType.NEVER),
    RawCotNDItemData("Dorian's Plate Armor", ItemClassification.useful, ItemType.ARMOR, "ArmorPlatemailDorian",
                     DLC.BASE, DefaultType.UNIQUE),
    RawCotNDItemData("Shiny Armor", ItemClassification.useful, ItemType.ARMOR, "Sync_ArmorPlatemailShiny",
                     DLC.SYNCHRONY, DefaultType.UNIQUE),
    RawCotNDItemData("Virtual Armor", ItemClassification.useful, ItemType.ARMOR, "Coldsteel_ArmorVirtual", DLC.MIKU,
                     DefaultType.UNIQUE)
]

heads: list[RawCotNDItemData] = [
    RawCotNDItemData("Miner's Cap", ItemClassification.useful, ItemType.HEAD, "HeadMinersCap", DLC.BASE,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Monocle", ItemClassification.useful, ItemType.HEAD, "HeadMonocle", DLC.BASE,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Circlet of Telepathy", ItemClassification.useful, ItemType.HEAD, "HeadCircletTelepathy",
                     DLC.BASE, DefaultType.POSSIBLE),
    RawCotNDItemData("Helm", ItemClassification.useful, ItemType.HEAD, "HeadHelm", DLC.BASE, DefaultType.NEVER),
    RawCotNDItemData("Crown of Thorns", ItemClassification.useful, ItemType.HEAD, "HeadCrownOfThorns", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Crown of Teleportation", ItemClassification.useful, ItemType.HEAD, "HeadCrownOfTeleportation",
                     DLC.BASE, DefaultType.POSSIBLE),
    RawCotNDItemData("Glass Jaw", ItemClassification.useful, ItemType.HEAD, "HeadGlassJaw", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Blast Helm", ItemClassification.useful, ItemType.HEAD, "HeadBlastHelm", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Sunglasses", ItemClassification.useful, ItemType.HEAD, "HeadSunglasses", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Spiked Ears", ItemClassification.useful, ItemType.HEAD, "HeadSpikedEars", DLC.AMPLIFIED,
                     DefaultType.NEVER),
]

feet: list[RawCotNDItemData] = [
    RawCotNDItemData("Ballet Shoes", ItemClassification.useful, ItemType.FEET, "FeetBalletShoes", DLC.BASE,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Winged Boots", ItemClassification.useful, ItemType.FEET, "FeetBootsWinged", DLC.BASE,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Explorers Boots", ItemClassification.useful, ItemType.FEET, "FeetBootsExplorers", DLC.BASE,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Lead Boots", ItemClassification.useful, ItemType.FEET, "FeetBootsLead", DLC.BASE,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Glass Slippers", ItemClassification.useful, ItemType.FEET, "FeetGlassSlippers", DLC.AMPLIFIED,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Hargreaves", ItemClassification.useful, ItemType.FEET, "FeetGreaves", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Boots of Strength", ItemClassification.useful, ItemType.FEET, "FeetBootsStrength", DLC.BASE,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Boots of Pain", ItemClassification.useful, ItemType.FEET, "FeetBootsPain", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Boots of Leaping", ItemClassification.useful, ItemType.FEET, "FeetBootsLeaping", DLC.BASE,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Boots of Lunging", ItemClassification.useful, ItemType.FEET, "FeetBootsLunging", DLC.BASE,
                     DefaultType.POSSIBLE),
]

torches: list[RawCotNDItemData] = [
    RawCotNDItemData("Torch", ItemClassification.useful, ItemType.TORCH, "Torch1", DLC.BASE, DefaultType.POSSIBLE),
    RawCotNDItemData("Bright Torch", ItemClassification.useful, ItemType.TORCH, "Torch2", DLC.BASE, DefaultType.NEVER),
    RawCotNDItemData("Luminous Torch", ItemClassification.useful, ItemType.TORCH, "Torch3", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Obsidian Torch", ItemClassification.useful, ItemType.TORCH, "TorchObsidian", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Glass Torch", ItemClassification.useful, ItemType.TORCH, "TorchGlass", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Infernal Torch", ItemClassification.useful, ItemType.TORCH, "TorchInfernal", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Torch of Foresight", ItemClassification.useful, ItemType.TORCH, "TorchForesight", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Torch of Walls", ItemClassification.useful, ItemType.TORCH, "TorchWalls", DLC.AMPLIFIED,
                     DefaultType.NEVER),
    RawCotNDItemData("Torch of Strength", ItemClassification.useful, ItemType.TORCH, "TorchStrength", DLC.AMPLIFIED,
                     DefaultType.NEVER),
]

shovels: list[RawCotNDItemData] = [
    RawCotNDItemData("Shovel", ItemClassification.useful, ItemType.SHOVEL, "ShovelBasic", DLC.BASE, DefaultType.ALWAYS),
    RawCotNDItemData("Titanium Shovel", ItemClassification.useful, ItemType.SHOVEL, "ShovelTitanium", DLC.BASE,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Crystal Shovel", ItemClassification.useful, ItemType.SHOVEL, "ShovelCrystal", DLC.BASE,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Obsidian Shovel", ItemClassification.useful, ItemType.SHOVEL, "ShovelObsidian", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Glass Shovel", ItemClassification.useful, ItemType.SHOVEL, "ShovelGlass", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Blood Shovel", ItemClassification.useful, ItemType.SHOVEL, "ShovelBlood", DLC.BASE,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Pickaxe", ItemClassification.useful, ItemType.SHOVEL, "Pickaxe", DLC.BASE, DefaultType.NEVER),
    RawCotNDItemData("Shovel of Courage", ItemClassification.useful, ItemType.SHOVEL, "ShovelCourage",
                     DLC.AMPLIFIED,
                     DefaultType.NEVER),
    RawCotNDItemData("Shovel of Strength", ItemClassification.useful, ItemType.SHOVEL, "ShovelStrength",
                     DLC.AMPLIFIED,
                     DefaultType.NEVER),
    RawCotNDItemData("Battle Shovel", ItemClassification.useful, ItemType.SHOVEL, "ShovelBattle", DLC.AMPLIFIED,
                     DefaultType.NEVER),
    RawCotNDItemData("Shovel Blade", ItemClassification.useful, ItemType.SHOVEL, "Goldman_ShovelPogo",
                     DLC.SHOVEL_KNIGHT, DefaultType.UNIQUE)
]

rings: list[RawCotNDItemData] = [
    RawCotNDItemData("Ring of Charisma", ItemClassification.useful, ItemType.RING, "RingCharisma", DLC.BASE,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Ring of Gold", ItemClassification.useful, ItemType.RING, "RingGold", DLC.BASE, DefaultType.NEVER),
    RawCotNDItemData("Ring of Luck", ItemClassification.useful, ItemType.RING, "RingLuck", DLC.BASE, DefaultType.NEVER),
    RawCotNDItemData("Ring of Mana", ItemClassification.useful, ItemType.RING, "RingMana", DLC.BASE, DefaultType.NEVER),
    RawCotNDItemData("Ring of Might", ItemClassification.useful, ItemType.RING, "RingMight", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Ring of Protection", ItemClassification.useful, ItemType.RING, "RingProtection", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Ring of Regeneration", ItemClassification.useful, ItemType.RING, "RingRegeneration", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Ring of Shielding", ItemClassification.useful, ItemType.RING, "RingShielding", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Ring of War", ItemClassification.useful, ItemType.RING, "RingWar", DLC.BASE, DefaultType.NEVER),
    RawCotNDItemData("Ring of Courage", ItemClassification.useful, ItemType.RING, "RingCourage", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Ring of Peace", ItemClassification.useful, ItemType.RING, "RingPeace", DLC.BASE,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Ring of Shadows", ItemClassification.useful, ItemType.RING, "RingShadows", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Ring of Becoming", ItemClassification.useful, ItemType.RING, "RingBecoming", DLC.BASE,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Ring of Phasing", ItemClassification.useful, ItemType.RING, "RingPhasing", DLC.BASE,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Ring of Frost", ItemClassification.useful, ItemType.RING, "RingFrost", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Ring of Piercing", ItemClassification.useful, ItemType.RING, "RingPiercing", DLC.AMPLIFIED,
                     DefaultType.NEVER),
    RawCotNDItemData("Ring of Pain", ItemClassification.useful, ItemType.RING, "RingPain", DLC.AMPLIFIED,
                     DefaultType.NEVER),
]

weapons: list[RawCotNDItemData] = [
    RawCotNDItemData("Dagger", ItemClassification.useful, ItemType.WEAPON, "WeaponDagger", DLC.BASE,
                     DefaultType.ALWAYS),
    RawCotNDItemData("Jeweled Dagger", ItemClassification.useful, ItemType.WEAPON, "WeaponDaggerJeweled", DLC.BASE,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Electric Dagger", ItemClassification.useful, ItemType.WEAPON, "WeaponDaggerElectric",
                     DLC.BASE,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Phasing Dagger", ItemClassification.useful, ItemType.WEAPON, "WeaponDaggerPhasing", DLC.BASE,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Frost Dagger", ItemClassification.useful, ItemType.WEAPON, "WeaponDaggerFrost", DLC.BASE,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Broadsword", ItemClassification.useful, ItemType.WEAPON, "WeaponBroadsword", DLC.BASE,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Longsword", ItemClassification.useful, ItemType.WEAPON, "WeaponLongsword", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Spear", ItemClassification.useful, ItemType.WEAPON, "WeaponSpear", DLC.BASE,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Trident", ItemClassification.useful, ItemType.WEAPON, "Sync_WeaponTrident", DLC.SYNCHRONY,
                     DefaultType.NEVER),
    RawCotNDItemData("Bow", ItemClassification.useful, ItemType.WEAPON, "WeaponBow", DLC.BASE, DefaultType.POSSIBLE),
    RawCotNDItemData("Staff", ItemClassification.useful, ItemType.WEAPON, "WeaponStaff", DLC.AMPLIFIED,
                     DefaultType.NEVER),
    RawCotNDItemData("Whip", ItemClassification.useful, ItemType.WEAPON, "WeaponWhip", DLC.BASE, DefaultType.NEVER),
    RawCotNDItemData("Harp", ItemClassification.useful, ItemType.WEAPON, "WeaponHarp", DLC.AMPLIFIED,
                     DefaultType.NEVER),
    RawCotNDItemData("Warhammer", ItemClassification.useful, ItemType.WEAPON, "WeaponWarhammer", DLC.AMPLIFIED,
                     DefaultType.NEVER),
    RawCotNDItemData("Cutlass", ItemClassification.useful, ItemType.WEAPON, "WeaponCutlass", DLC.AMPLIFIED,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Rapier", ItemClassification.useful, ItemType.WEAPON, "WeaponRapier", DLC.BASE, DefaultType.NEVER),
    RawCotNDItemData("Cat o' Nine Tails", ItemClassification.useful, ItemType.WEAPON, "WeaponCat", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Axe", ItemClassification.useful, ItemType.WEAPON, "WeaponAxe", DLC.AMPLIFIED, DefaultType.NEVER),
    RawCotNDItemData("Crossbow", ItemClassification.useful, ItemType.WEAPON, "WeaponCrossbow", DLC.BASE,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Blunderbuss", ItemClassification.useful, ItemType.WEAPON, "WeaponBlunderbuss", DLC.BASE,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Rifle", ItemClassification.useful, ItemType.WEAPON, "WeaponRifle", DLC.BASE, DefaultType.NEVER),
    RawCotNDItemData("Golden Lute", ItemClassification.useful, ItemType.WEAPON, "WeaponGoldenLute", DLC.BASE,
                     DefaultType.UNIQUE),
    RawCotNDItemData("Eli's Hand", ItemClassification.useful, ItemType.WEAPON, "WeaponEli", DLC.BASE,
                     DefaultType.UNIQUE),
    RawCotNDItemData("Flower", ItemClassification.useful, ItemType.WEAPON, "WeaponFlower", DLC.BASE,
                     DefaultType.UNIQUE),
    RawCotNDItemData("Zweihander", ItemClassification.useful, ItemType.WEAPON, "Sync_WeaponReallyBigSword",
                     DLC.SYNCHRONY, DefaultType.UNIQUE),
    RawCotNDItemData("Lantern", ItemClassification.useful, ItemType.WEAPON, "Sync_WeaponLantern", DLC.SYNCHRONY,
                     DefaultType.UNIQUE),
    RawCotNDItemData("Lance of Courage", ItemClassification.useful, ItemType.WEAPON, "Sync_WeaponLance", DLC.SYNCHRONY,
                     DefaultType.UNIQUE),
    RawCotNDItemData("Leek", ItemClassification.useful, ItemType.WEAPON, "Coldsteel_WeaponLeek", DLC.MIKU,
                     DefaultType.UNIQUE)
]

shields: list[RawCotNDItemData] = [
    RawCotNDItemData("Wooden Shield", ItemClassification.useful, ItemType.SHIELD, "Sync_ShieldWooden",
                     DLC.SYNCHRONY,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Titanium Shield", ItemClassification.useful, ItemType.SHIELD, "Sync_ShieldTitanium",
                     DLC.SYNCHRONY, DefaultType.NEVER),
    RawCotNDItemData("Heavy Shield", ItemClassification.useful, ItemType.SHIELD, "Sync_ShieldHeavy", DLC.SYNCHRONY,
                     DefaultType.NEVER),
    RawCotNDItemData("Obsidian Shield", ItemClassification.useful, ItemType.SHIELD, "Sync_ShieldObsidian",
                     DLC.SYNCHRONY, DefaultType.NEVER),
    RawCotNDItemData("Shield of Strength", ItemClassification.useful, ItemType.SHIELD, "Sync_ShieldStrength",
                     DLC.SYNCHRONY, DefaultType.POSSIBLE),
    RawCotNDItemData("Reflective Shield", ItemClassification.useful, ItemType.SHIELD, "Sync_ShieldReflective",
                     DLC.SYNCHRONY, DefaultType.NEVER),
    RawCotNDItemData("Shield of Shove", ItemClassification.useful, ItemType.SHIELD, "Sync_ShieldShove",
                     DLC.SYNCHRONY,
                     DefaultType.POSSIBLE),
]

spells: list[RawCotNDItemData] = [
    RawCotNDItemData("Fireball Spell", ItemClassification.useful, ItemType.SPELL, "SpellFireball", DLC.BASE,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Freeze Spell", ItemClassification.useful, ItemType.SPELL, "SpellFreezeEnemies", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Heal Spell", ItemClassification.useful, ItemType.SPELL, "SpellHeal", DLC.BASE, DefaultType.NEVER),
    RawCotNDItemData("Bomb Spell", ItemClassification.useful, ItemType.SPELL, "SpellBomb", DLC.BASE, DefaultType.NEVER),
    RawCotNDItemData("Shield Spell", ItemClassification.useful, ItemType.SPELL, "SpellShield", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Transmute Spell", ItemClassification.useful, ItemType.SPELL, "SpellTransmute", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Earth Spell", ItemClassification.useful, ItemType.SPELL, "SpellEarth", DLC.AMPLIFIED,
                     DefaultType.NEVER),
    RawCotNDItemData("Pulse Spell", ItemClassification.useful, ItemType.SPELL, "SpellPulse", DLC.AMPLIFIED,
                     DefaultType.NEVER),
    RawCotNDItemData("Berserk Spell", ItemClassification.useful, ItemType.SPELL, "Sync_SpellBerzerk", DLC.SYNCHRONY,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Dash Spell", ItemClassification.useful, ItemType.SPELL, "Sync_SpellDash", DLC.SYNCHRONY,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Charm Spell", ItemClassification.useful, ItemType.SPELL, "Sync_SpellCharm", DLC.SYNCHRONY,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Transform Spell", ItemClassification.useful, ItemType.SPELL, "SpellTransform", DLC.AMPLIFIED,
                     DefaultType.UNIQUE)
]

scrolls: list[RawCotNDItemData] = [
    RawCotNDItemData("Fireball Scroll", ItemClassification.useful, ItemType.SCROLL, "ScrollFireball", DLC.BASE,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Freeze Scroll", ItemClassification.useful, ItemType.SCROLL, "ScrollFreezeEnemies", DLC.BASE,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Shield Scroll", ItemClassification.useful, ItemType.SCROLL, "ScrollShield", DLC.BASE,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Transmute Scroll", ItemClassification.useful, ItemType.SCROLL, "ScrollTransmute", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Pulse Scroll", ItemClassification.useful, ItemType.SCROLL, "ScrollPulse", DLC.BASE,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Berzerk Scroll", ItemClassification.useful, ItemType.SCROLL, "Sync_ScrollBerzerk", DLC.SYNCHRONY,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Earthquake Scroll", ItemClassification.useful, ItemType.SCROLL, "ScrollEarthquake", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Enchant Weapon Scroll", ItemClassification.useful, ItemType.SCROLL, "ScrollEnchantWeapon",
                     DLC.BASE, DefaultType.NEVER),
    RawCotNDItemData("Fear Scroll", ItemClassification.useful, ItemType.SCROLL, "ScrollFear", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Scroll of Need", ItemClassification.useful, ItemType.SCROLL, "ScrollNeed", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Riches Scroll", ItemClassification.useful, ItemType.SCROLL, "ScrollRiches", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Fireball Tome", ItemClassification.useful, ItemType.SCROLL, "TomeFireball", DLC.AMPLIFIED,
                     DefaultType.NEVER),
    RawCotNDItemData("Freeze Tome", ItemClassification.useful, ItemType.SCROLL, "TomeFreeze", DLC.AMPLIFIED,
                     DefaultType.NEVER),
    RawCotNDItemData("Shield Tome", ItemClassification.useful, ItemType.SCROLL, "TomeShield", DLC.AMPLIFIED,
                     DefaultType.NEVER),
    RawCotNDItemData("Transmute Tome", ItemClassification.useful, ItemType.SCROLL, "TomeTransmute", DLC.AMPLIFIED,
                     DefaultType.NEVER),
    RawCotNDItemData("Pulse Tome", ItemClassification.useful, ItemType.SCROLL, "TomePulse", DLC.AMPLIFIED,
                     DefaultType.NEVER),
    RawCotNDItemData("Earth Tome", ItemClassification.useful, ItemType.SCROLL, "TomeEarth", DLC.AMPLIFIED,
                     DefaultType.NEVER),
]

actions: list[RawCotNDItemData] = [
    RawCotNDItemData("Apple", ItemClassification.useful, ItemType.ACTION, "Food1", DLC.BASE, DefaultType.ALWAYS),
    RawCotNDItemData("Cheese", ItemClassification.useful, ItemType.ACTION, "Food2", DLC.BASE, DefaultType.NEVER),
    RawCotNDItemData("Drumstick", ItemClassification.useful, ItemType.ACTION, "Food3", DLC.BASE, DefaultType.NEVER),
    RawCotNDItemData("Ham", ItemClassification.useful, ItemType.ACTION, "Food4", DLC.BASE, DefaultType.NEVER),
    RawCotNDItemData("Carrot", ItemClassification.useful, ItemType.ACTION, "FoodCarrot", DLC.AMPLIFIED,
                     DefaultType.NEVER),
    RawCotNDItemData("Cookies", ItemClassification.useful, ItemType.ACTION, "FoodCookies", DLC.AMPLIFIED,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Dove Familiar", ItemClassification.useful, ItemType.ACTION, "FamiliarDove", DLC.AMPLIFIED,
                     DefaultType.NEVER),
    RawCotNDItemData("Ice Spirit Familiar", ItemClassification.useful, ItemType.ACTION, "FamiliarIceSpirit",
                     DLC.AMPLIFIED, DefaultType.NEVER),
    RawCotNDItemData("Shopkeeper Familiar", ItemClassification.useful, ItemType.ACTION, "FamiliarShopkeeper",
                     DLC.AMPLIFIED, DefaultType.NEVER),
    RawCotNDItemData("Rat Familiar", ItemClassification.useful, ItemType.ACTION, "FamiliarRat", DLC.AMPLIFIED,
                     DefaultType.NEVER),
    RawCotNDItemData("War Drum", ItemClassification.useful, ItemType.ACTION, "WarDrum", DLC.AMPLIFIED,
                     DefaultType.NEVER),
    RawCotNDItemData("Blood Drum", ItemClassification.useful, ItemType.ACTION, "BloodDrum", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Heart Transplant", ItemClassification.useful, ItemType.ACTION, "HeartTransplant", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Holy Water", ItemClassification.useful, ItemType.ACTION, "HolyWater", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Cursed Potion", ItemClassification.useful, ItemType.ACTION, "CursedPotion", DLC.AMPLIFIED,
                     DefaultType.NEVER),
    RawCotNDItemData("Throwing Stars", ItemClassification.useful, ItemType.ACTION, "ThrowingStars", DLC.AMPLIFIED,
                     DefaultType.NEVER),
]

materials: list[RawCotNDItemData] = [
    RawCotNDItemData("Gold Material", ItemClassification.useful, ItemType.MATERIAL, "AP_MaterialGold", DLC.BASE,
                     DefaultType.MATERIAL),
    RawCotNDItemData("Glass Material", ItemClassification.useful, ItemType.MATERIAL, "AP_MaterialGlass", DLC.BASE,
                     DefaultType.MATERIAL),
    RawCotNDItemData("Blood Material", ItemClassification.useful, ItemType.MATERIAL, "AP_MaterialBlood", DLC.BASE,
                     DefaultType.MATERIAL),
    RawCotNDItemData("Obsidian Material", ItemClassification.useful, ItemType.MATERIAL, "AP_MaterialObsidian",
                     DLC.BASE, DefaultType.MATERIAL),
    RawCotNDItemData("Onyx Material", ItemClassification.useful, ItemType.MATERIAL, "AP_MaterialOnyx",
                     DLC.SYNCHRONY,
                     DefaultType.MATERIAL),
    RawCotNDItemData("Titanium Material", ItemClassification.useful, ItemType.MATERIAL, "AP_MaterialTitanium",
                     DLC.BASE, DefaultType.MATERIAL),
]

misc: list[RawCotNDItemData] = [
    RawCotNDItemData("Strength Charm", ItemClassification.useful, ItemType.MISC, "CharmStrength", DLC.BASE,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Risk Charm", ItemClassification.useful, ItemType.MISC, "CharmRisk", DLC.BASE,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Protection Charm", ItemClassification.useful, ItemType.MISC, "CharmProtection", DLC.BASE,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Nazar Charm", ItemClassification.useful, ItemType.MISC, "CharmNazar", DLC.BASE,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Gluttony Charm", ItemClassification.useful, ItemType.MISC, "CharmGluttony", DLC.BASE,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Frost Charm", ItemClassification.useful, ItemType.MISC, "CharmFrost", DLC.BASE,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Bomb Charm", ItemClassification.useful, ItemType.MISC, "CharmBomb", DLC.AMPLIFIED,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Grenade Charm", ItemClassification.useful, ItemType.MISC, "CharmGrenade", DLC.AMPLIFIED,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Throwing Charm", ItemClassification.useful, ItemType.MISC, "Sync_CharmThrowing",
                     DLC.SYNCHRONY,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Holster", ItemClassification.useful, ItemType.MISC, "Holster", DLC.BASE, DefaultType.NEVER),
    RawCotNDItemData("Backpack", ItemClassification.useful, ItemType.MISC, "HudBackpack", DLC.BASE,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Pack of Holding", ItemClassification.useful, ItemType.MISC, "BagHolding", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Map", ItemClassification.useful, ItemType.MISC, "MiscMap", DLC.BASE, DefaultType.POSSIBLE),
    RawCotNDItemData("Compass", ItemClassification.useful, ItemType.MISC, "MiscCompass", DLC.BASE,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Coupon", ItemClassification.useful, ItemType.MISC, "MiscCoupon", DLC.BASE, DefaultType.POSSIBLE),
    RawCotNDItemData("Monkey's Paw", ItemClassification.useful, ItemType.MISC, "MiscMonkeyPaw", DLC.AMPLIFIED,
                     DefaultType.POSSIBLE),
    RawCotNDItemData("Potion", ItemClassification.useful, ItemType.MISC, "MiscPotion", DLC.BASE,
                     DefaultType.POSSIBLE)
]

modes: list[RawCotNDItemData] = [
    RawCotNDItemData("No Return Mode", ItemClassification.progression, ItemType.MODE, "APNoReturnMode",
                     DLC.AMPLIFIED, DefaultType.NEVER),
    RawCotNDItemData("Hard Mode", ItemClassification.progression, ItemType.MODE, "APHardMode", DLC.AMPLIFIED,
                     DefaultType.NEVER),
    RawCotNDItemData("Phasing Mode", ItemClassification.progression, ItemType.MODE, "APPhasingMode", DLC.AMPLIFIED,
                     DefaultType.NEVER),
    RawCotNDItemData("Randomizer Mode", ItemClassification.progression, ItemType.MODE, "APRandomizerMode",
                     DLC.AMPLIFIED, DefaultType.NEVER),
    RawCotNDItemData("Mystery Mode", ItemClassification.progression, ItemType.MODE, "APMysteryMode", DLC.AMPLIFIED,
                     DefaultType.NEVER),
    RawCotNDItemData("No Beat Mode", ItemClassification.progression, ItemType.MODE, "APNoBeatMode", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Double Tempo Mode", ItemClassification.progression, ItemType.MODE, "APDoubleTempoMode",
                     DLC.BASE, DefaultType.NEVER),
    RawCotNDItemData("Low Percent Mode", ItemClassification.progression, ItemType.MODE, "APLowPercentMode",
                     DLC.BASE, DefaultType.NEVER),
]

npcs: list[RawCotNDItemData] = [
    RawCotNDItemData("Codex", ItemClassification.progression, ItemType.NPC, "Trainer", DLC.BASE, DefaultType.NEVER),
    RawCotNDItemData("Merlin", ItemClassification.progression, ItemType.NPC, "Merlin", DLC.BASE, DefaultType.NEVER),
    RawCotNDItemData("Hintmaster", ItemClassification.useful, ItemType.NPC, "Bossmaster", DLC.BASE, DefaultType.NEVER),
    RawCotNDItemData("Janitor", ItemClassification.useful, ItemType.NPC, "Janitor", DLC.BASE, DefaultType.NEVER),
    RawCotNDItemData("Diamond Dealer", ItemClassification.useful, ItemType.NPC, "Diamonddealer", DLC.BASE,
                     DefaultType.NEVER),
]

upgrades: list[RawCotNDItemData] = [
    RawCotNDItemData("Permanent Health Upgrade", ItemClassification.useful, ItemType.UPGRADE, "PermHeart2",
                     DLC.BASE, DefaultType.NEVER),
    RawCotNDItemData("Shop Stock Unlock", ItemClassification.progression, ItemType.UPGRADE, "APShopStock", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Zone 1 Access", ItemClassification.progression, ItemType.UPGRADE, "APZone1Access", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Zone 2 Access", ItemClassification.progression, ItemType.UPGRADE, "APZone2Access", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Zone 3 Access", ItemClassification.progression, ItemType.UPGRADE, "APZone3Access", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Zone 4 Access", ItemClassification.progression, ItemType.UPGRADE, "APZone4Access", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Zone 5 Access", ItemClassification.progression, ItemType.UPGRADE, "APZone5Access", DLC.AMPLIFIED,
                     DefaultType.NEVER),
    RawCotNDItemData("Progressive Zone Access", ItemClassification.progression, ItemType.UPGRADE, "APProgressiveZoneAccess",
                     DLC.BASE, DefaultType.NEVER),
    RawCotNDItemData("Character Room Key", ItemClassification.progression, ItemType.UPGRADE, "APCharRoomKey", DLC.BASE,
                     DefaultType.NEVER),
]

filler: list[RawCotNDItemData] = [
    RawCotNDItemData("Instant Gold (50)", ItemClassification.filler, ItemType.FILLER, "APInstantGold", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Instant Gold (200)", ItemClassification.filler, ItemType.FILLER, "APInstantGold2", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("1 Diamond", ItemClassification.filler, ItemType.FILLER, "APDiamond1", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("2 Diamonds", ItemClassification.filler, ItemType.FILLER, "APDiamond2", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("3 Diamonds", ItemClassification.filler, ItemType.FILLER, "APDiamond3", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("4 Diamonds", ItemClassification.filler, ItemType.FILLER, "APDiamond4", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Full Heal", ItemClassification.filler, ItemType.FILLER, "APFullHeal", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Camera Trap", ItemClassification.trap, ItemType.TRAP, "CameraTrap", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Confusion Trap", ItemClassification.trap, ItemType.TRAP, "ConfusionTrap", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Dad Trap", ItemClassification.trap, ItemType.TRAP, "DadTrap", DLC.BASE, DefaultType.NEVER),
    RawCotNDItemData("Dead Ringer Trap", ItemClassification.trap, ItemType.TRAP, "DeadRingerTrap", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Gold Scatter Trap", ItemClassification.trap, ItemType.TRAP, "GoldScatterTrap", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Haunted Shopkeeper Trap", ItemClassification.trap, ItemType.TRAP, "HauntedShopkeeperTrap",
                     DLC.BASE, DefaultType.NEVER),
    RawCotNDItemData("Monkey Trap", ItemClassification.trap, ItemType.TRAP, "MonkeyTrap", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("No Return Trap", ItemClassification.trap, ItemType.TRAP, "NoReturnTrap", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Skeleton Trap", ItemClassification.trap, ItemType.TRAP, "SkeletonTrap", DLC.BASE,
                     DefaultType.NEVER),
    RawCotNDItemData("Tempo Trap", ItemClassification.trap, ItemType.TRAP, "TempoTrap", DLC.BASE, DefaultType.NEVER),
]

ITEM_SOURCES: tuple[list[RawCotNDItemData], ...] = (
    characters,
    armors,
    heads,
    feet,
    torches,
    shovels,
    rings,
    weapons,
    shields,
    spells,
    scrolls,
    actions,
    materials,
    misc,
    modes,
    npcs,
    upgrades,
    filler
)

BASE_ITEM_CODE: Final = 247_080


def load_all_items() -> list[CotNDItemData]:
    loaded: list[CotNDItemData] = []
    seen_names: set[str] = set()
    seen_ids: set[str] = set()

    index = 0

    for source in ITEM_SOURCES:
        for item in source:
            if item.name in seen_names:
                raise ValueError(f"Duplicate item name: {item.name}")
            if item.cotnd_id in seen_ids:
                raise ValueError(f"Duplicate cotnd_id: {item.cotnd_id}")

            seen_names.add(item.name)
            seen_ids.add(item.cotnd_id)

            loaded.append(
                CotNDItemData(
                    name=item.name,
                    classification=item.classification,
                    type=item.type,
                    cotnd_id=item.cotnd_id,
                    dlc=item.dlc,
                    default=item.default,
                    code=BASE_ITEM_CODE + index,
                )
            )
            index += 1

    return loaded


ALL_ITEMS = load_all_items()
ITEMS_BY_NAME = {i.name: i for i in ALL_ITEMS}
ITEMS_BY_CODE = {i.code: i for i in ALL_ITEMS}


def item_from_name(name: str):
    return ITEMS_BY_NAME[name]


def item_from_code(code: int):
    return ITEMS_BY_CODE[code]


def get_shop_stock_unlocks(items: list[CotNDItemData], index: int):
    for _ in range(index - 1):
        items.append(ITEMS_BY_NAME["Shop Stock Unlock"])

    return items


def build_master_world_items(
        character_blacklist: Set[str] = None,
        dlc: Set[str] = None,
        game_modes: Set[str] = None,
        include_unique_items: bool = False,
        character_unlocks: str = "item_only"
) -> Tuple[list[CotNDItemData], dict[str, CotNDItemData], dict[int, CotNDItemData]]:
    if character_blacklist is None:
        character_blacklist = {}
    if dlc is None:
        dlc = {}
    if game_modes is None:
        game_modes = []
    dlc_enums = normalize_dlc(dlc)
    result: list[CotNDItemData] = []

    items_list = [copy(item) for item in ALL_ITEMS]

    for item in items_list:
        # Amplified phasing rule
        if item.name == "Ring of Phasing" and DLC.AMPLIFIED in dlc_enums:
            continue

        # Character blacklist
        if item.name in character_blacklist:
            continue

        # DLC filtering
        if item.dlc is not DLC.BASE and item.dlc not in dlc_enums:
            continue

        # Game modes
        if item.type is ItemType.MODE:
            if item.name.removesuffix(" Mode") not in game_modes:
                continue

        if item.default is DefaultType.UNIQUE and not include_unique_items:
            continue

        result.append(item)

        # Permanent Health Upgrade duplication
        # TODO: Move out to manual addition
        if item.name == "Permanent Health Upgrade":
            result.extend([item, item])

        # Change item classification for required items
        if character_unlocks != "item_only":
            required_items = {
                item_name
                for requirements in character_requirements.values()
                for item_name in requirements
            }

            for unlock_item in result:
                if unlock_item.name in required_items:
                    unlock_item.classification = ItemClassification.progression

    item_from_name_map = {item.name: item for item in result}
    item_from_code_map = {item.code: item for item in result}

    return result, item_from_name_map, item_from_code_map


# Items managed outside the standard population pipeline and added conditionally
AP_SYSTEM_ITEMS: frozenset[str] = frozenset({
    "Shop Stock Unlock",
    "Zone 1 Access",
    "Zone 2 Access",
    "Zone 3 Access",
    "Zone 4 Access",
    "Zone 5 Access",
    "Progressive Zone Access",
    "Character Room Key",
})


def filter_population_list(item_list: list[CotNDItemData]):
    filtered_list = []

    for item in item_list:
        # Exclude filler/trap items
        if item.type is ItemType.FILLER or item.type is ItemType.TRAP:
            continue

        # Exclude items that are added to the pool conditionally based on options
        if item.name in AP_SYSTEM_ITEMS:
            continue

        filtered_list.append(item)

    return filtered_list


def get_starting_pool(
    random: Random,
    items_list: list[CotNDItemData],
    starting_inventory: int,
    include_materials: bool
):
    starting_pool: list[CotNDItemData] = []

    for item in items_list:
        if item.type in (ItemType.CHARACTER, ItemType.MODE, ItemType.NPC):
            continue

        if item.default is DefaultType.NEVER:
            continue

        if not include_materials and item.type is ItemType.MATERIAL:
            continue

        starting_pool.append(item)

    always_items = [item for item in starting_pool if item.default is DefaultType.ALWAYS]
    optional_items = [item for item in starting_pool if item.default is not DefaultType.ALWAYS]

    pct = max(0, min(100, starting_inventory))

    target_count = math.ceil(len(starting_pool) * pct / 100)

    target_count = max(target_count, len(always_items))

    remaining = target_count - len(always_items)

    if remaining <= 0 or not optional_items:
        return always_items

    return always_items + random.sample(
        optional_items,
        min(remaining, len(optional_items))
    )


def get_filler_items(world, quantity: int):
    if quantity <= 0: return []

    filler_list = [i for i in ALL_ITEMS if i.type in (ItemType.FILLER, ItemType.TRAP)]
    non_traps = [i for i in filler_list if i.type is not ItemType.TRAP]
    traps = [i for i in filler_list if i.type is ItemType.TRAP]

    trap_percentage = world.options.trap_percentage.value / 100
    trap_weights = world.options.trap_weights.value

    if not sum(trap_weights.values()):
        trap_percentage = 0.0

    filler_percentage = 1.0 - trap_percentage

    weights: dict[str, float] = {}

    if non_traps:
        scale = filler_percentage / len(non_traps)
        for item in non_traps:
            weights[item.name] = scale

    if trap_percentage > 0 and traps:
        scale = trap_percentage / sum(trap_weights.values())
        for name, value in trap_weights.items():
            weights[name] = value * scale

    chosen_names = world.random.choices(list(weights.keys()), list(weights.values()), k=quantity)
    return [ITEMS_BY_NAME[name] for name in chosen_names]


def get_npc_items():
    npc_list = []

    for item in ALL_ITEMS:
        if item.type is ItemType.NPC:
            npc_list.append(item)

    return npc_list


def make_item_groups() -> dict[str, set[str]]:
    groups: dict[str, set[str]] = defaultdict(set)

    for item in ALL_ITEMS:
        if item.type not in PLURALS:
            continue
        group_name = PLURALS[item.type]
        groups[group_name].add(item.name)

    return dict(groups)


all_items = ALL_ITEMS.copy()
item_name_groups = make_item_groups()

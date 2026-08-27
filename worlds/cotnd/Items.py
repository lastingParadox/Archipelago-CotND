from __future__ import annotations

from collections import defaultdict
from copy import copy
import json
import math
import pkgutil
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Final

from BaseClasses import Item, ItemClassification
from worlds.cotnd.Locations import grow_locations, shop_rows
from worlds.cotnd.Utils import (CHARACTER_ITEM_REQUIREMENTS, DLC, max_zone, owned_dlc,
                                    shrine_has_valid_character)

if TYPE_CHECKING:
    from . import CotNDWorld

BASE_ITEM_CODE: Final = 247_080
DATA_RESOURCE: Final = "data/items.json"

class CotNDItem(Item):
    game: str = "Crypt of the NecroDancer"

# Item dataclass definitions

class ItemType(StrEnum):
    CHARACTER = "character"
    WEAPON    = "weapon"
    SHOVEL    = "shovel"
    TORCH     = "torch"
    ARMOR     = "armor"
    RING      = "ring"
    FOOTWEAR  = "footwear"
    HEADWEAR  = "headwear"
    SHIELD    = "shield"
    SPELL     = "spell"
    SCROLL    = "scroll"
    ACTION    = "action"
    MISC      = "misc"
    MATERIAL  = "material"
    NPC       = "npc"
    UPGRADE   = "upgrade"
    KEY       = "key"
    BUFF      = "buff"
    MODE      = "mode"
    SHRINE    = "shrine"
    FILLER    = "filler"
    TRAP      = "trap"

PLURALS: dict[ItemType, str] = {
    ItemType.CHARACTER: "Characters",
    ItemType.ARMOR: "Armors",
    ItemType.HEADWEAR: "Headwear",
    ItemType.FOOTWEAR: "Footwear",
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
    ItemType.BUFF: "Buffs",
    ItemType.SHRINE: "Shrines",
}

class InventoryType(StrEnum):
    ALWAYS = "always"
    MATERIAL = "material"
    UNIQUE = "unique"
    POSSIBLE = "possible"
    NEVER = "never"


@dataclass(slots=True)
class CotNDItemData:
    name: str
    classification: ItemClassification
    type: ItemType
    cotnd_id: str
    dlc: DLC
    inventory_type: InventoryType
    excluded_dlc: DLC = DLC.NONE
    code: int = 0

    def available_with(self, owned_dlc: DLC) -> bool:
        owned = owned_dlc | DLC.BASE
        return self.dlc in owned and not (self.excluded_dlc & owned)

# Loading in the Items from the JSON

@dataclass(slots=True)
class CotNDItemPool:
    items: list[CotNDItemData]
    _by_name: dict[str, CotNDItemData]
    _by_cotnd_id: dict[str, CotNDItemData]
    _by_code: dict[int, CotNDItemData]

    def __init__(self, items: list[CotNDItemData]):
        self.items = items

        self._by_name = {}
        self._by_cotnd_id = {}
        self._by_code = {}

        for code, item in enumerate(self.items):
            if item.name in self._by_name:
                raise ValueError(f"Duplicate item name: {item.name}")
            if item.cotnd_id in self._by_cotnd_id:
                raise ValueError(f"Duplicate cotnd_id: {item.cotnd_id}")

            item.code = code + BASE_ITEM_CODE

            self._by_name[item.name] = item
            self._by_cotnd_id[item.cotnd_id] = item
            self._by_code[item.code] = item

    def get_item_name_to_id(self) -> dict[str, int]:
        return {item.name: item.code for item in self.items}

    def get_item_name_to_item(self) -> dict[str, CotNDItemData]:
        return {item.name: item for item in self.items}

    def get_by_name(self, name: str) -> CotNDItemData:
        return self._by_name[name]

    def get_by_cotnd_id(self, cotnd_id: str) -> CotNDItemData:
        return self._by_cotnd_id[cotnd_id]

    def get_by_code(self, code: int) -> CotNDItemData:
        return self._by_code[code]


def parse_item(entry: dict[str, Any]) -> CotNDItemData:
    return CotNDItemData(
        name=entry["name"],
        classification=ItemClassification[entry["classification"]],
        type=ItemType(entry["type"]),
        cotnd_id=entry["cotnd_id"],
        dlc=DLC.parse(entry["dlc"]),
        inventory_type=InventoryType(entry["inventory_type"]),
        excluded_dlc=DLC.parse(entry.get("excluded_dlc", ())),
    )


def load_items(resource: str = DATA_RESOURCE) -> list[CotNDItemData]:
    data = pkgutil.get_data(__name__, resource)

    if data is None:
        raise FileNotFoundError(f"{resource}: missing from the cotnd world package")

    entries = json.loads(data.decode("utf-8"))

    if not isinstance(entries, list):
        raise ValueError(f"{resource}: expected a list of items, got {type(entries).__name__}")

    return [parse_item(entry) for entry in entries]


def load_item_pool(resource: str = DATA_RESOURCE) -> CotNDItemPool:
    return CotNDItemPool(load_items(resource))

# Master item pool for reference in World, Client, etc.

ALL_ITEMS = load_item_pool()
ITEM_NAME_TO_ID = ALL_ITEMS.get_item_name_to_id()
FILLER_ITEM_NAMES: Final = [item.name for item in ALL_ITEMS.items if item.type is ItemType.FILLER]
CHARACTER_NAMES: Final = [item.name for item in ALL_ITEMS.items if item.type is ItemType.CHARACTER]

# The mod's item-room category ids
ROOM_CATEGORIES: dict[ItemType, str] = {
    ItemType.CHARACTER: "character",
    ItemType.ARMOR: "armor",
    ItemType.HEADWEAR: "head",
    ItemType.FOOTWEAR: "feet",
    ItemType.TORCH: "torch",
    ItemType.SHOVEL: "shovel",
    ItemType.RING: "ring",
    ItemType.WEAPON: "weapon",
    ItemType.SHIELD: "shield",
    ItemType.SPELL: "spell",
    ItemType.SCROLL: "scroll",
    ItemType.ACTION: "action",
    ItemType.MATERIAL: "material",
    ItemType.MISC: "misc",
    ItemType.UPGRADE: "upgrade",
    ItemType.MODE: "mode",
    ItemType.NPC: "npc",
    ItemType.BUFF: "buff",
    ItemType.SHRINE: "shrine",
}

TRAP_ITEMS_BY_COTND_ID = {item.cotnd_id: item for item in ALL_ITEMS.items if item.type is ItemType.TRAP}

def item_from_code(code: int) -> CotNDItemData:
    return ALL_ITEMS.get_by_code(code)

# Item filtering functions

def zone_access_key_items(world: CotNDWorld, dlc: DLC) -> list[CotNDItemData]:
    zones = max_zone(dlc)

    if world.options.zone_access_keys == "separate":
        return [copy(ALL_ITEMS.get_by_name(f"Zone {zone} Access")) for zone in range(1, zones + 1)]

    progressive = ALL_ITEMS.get_by_name("Progressive Zone Access")
    return [copy(progressive) for _ in range(zones - 1)]

def character_requirement_ids(world: CotNDWorld) -> dict[str, dict[str, list[str]]]:
    #Each character's gating items as CotND entity ids, split by whether they are unique.
    dlc = owned_dlc(world)
    requirements: dict[str, dict[str, list[str]]] = {}

    for character, names in CHARACTER_ITEM_REQUIREMENTS.items():
        character_data = ALL_ITEMS.get_by_name(character)
        if not character_data.available_with(dlc):
            continue

        entry: dict[str, list[str]] = {"normal": [], "unique": []}

        for name in sorted(names):
            item = ALL_ITEMS.get_by_name(name)
            if not item.available_with(dlc):
                continue
            kind = "unique" if item.inventory_type is InventoryType.UNIQUE else "normal"
            entry[kind].append(item.cotnd_id)

        if entry["normal"] or entry["unique"]:
            requirements[character_data.cotnd_id] = entry

    return requirements

# Item pool population

def character_unlocks_change_classifications(itempool: list[CotNDItemData], characters: set[str]) -> list[CotNDItemData]:
    required_items = {
        item_name
        for character, requirements in CHARACTER_ITEM_REQUIREMENTS.items() if character in characters
        for item_name in requirements
    }

    for item in itempool:
        if item.name in required_items:
            item.classification = ItemClassification.progression

    return itempool

def populate_item_pool(world: CotNDWorld) -> list[CotNDItemData]:
    itempool: list[CotNDItemData] = []
    dlc = owned_dlc(world)
    blacklist = set(world.options.character_blacklist.value)

    # Initial Item filtering
    for item in ALL_ITEMS.items:
        # Filler item filtering
        if item.type is ItemType.FILLER:
            continue

        # Zone Access keys are stocked by mode below, not taken from the master pool
        if item.type is ItemType.KEY:
            continue

        # A trap weighted 0 is opted out of the multiworld, not just out of the filler roll
        if item.type is ItemType.TRAP and world.options.trap_weights.get(item.name, 0) == 0:
            continue

        # DLC filtering
        if not item.available_with(dlc):
            continue

        # Character blacklist
        if item.type is ItemType.CHARACTER and item.name in blacklist:
            continue

        # NPC unlocks locked to their own cage are placed by Locations, not shuffled
        if item.type is ItemType.NPC and not world.options.lobby_npc_items:
            continue

        # Game Mode filtering
        if item.type is ItemType.MODE:
            if item.name.removesuffix(" Mode") not in world.options.included_extra_modes:
                continue

        # Unique items filtering
        if item.inventory_type is InventoryType.UNIQUE and not world.options.include_unique_items:
            continue

        # Permanent Health Upgrade Duplication
        if item.name == "Permanent Health Upgrade":
            # Distinct copies, so later passes can treat every pool entry as its own item.
            itempool.extend(copy(item) for _ in range(world.options.permanent_health_upgrades))
            continue

        # Shop Stock unlocks: reaching row N costs N-1 restocks, so the first row is free
        if item.name == "Shop Restock":
            itempool.extend(copy(item) for _ in range(max(shop_rows(world, dlc) - 1, 0)))
            continue

        # Golden Lute Shards only exist for the goal that counts them, and validation has
        # already raised the pool count to at least what the goal asks for.
        if item.name == "Golden Lute Shard":
            if world.options.goal == "golden_lute_shards":
                itempool.extend(copy(item) for _ in range(world.options.lute_shards_in_pool.value))
            continue

        # Progressive Potions Duplication
        if item.name == "Progressive Potions":
            itempool.extend(copy(item) for _ in range(3))
            continue

        # Progressive Coin Multiplier Duplication: one copy per stacking coin upgrade
        if item.name == "Progressive Coin Multiplier":
            itempool.extend(copy(item) for _ in range(2))
            continue

        itempool.append(item)

    itempool += zone_access_key_items(world, dlc)

    characters = {item.name for item in itempool if item.type is ItemType.CHARACTER}

    # Item Classification Modifications
    if world.options.character_unlocks != "item_only":
        itempool = character_unlocks_change_classifications(itempool, characters)

    # Shrine Item Extractions
    itempool = [item for item in itempool
                if item.type is not ItemType.SHRINE or shrine_has_valid_character(item.name, characters)]

    return itempool

def item_room_entries(itempool: list[CotNDItemData]) -> list[dict[str, str]]:
    """The mod's item room: every item this slot can receive, deduped, in pool order."""
    seen: set[str] = set()
    room: list[dict[str, str]] = []

    for item in itempool:
        if item.type not in ROOM_CATEGORIES or item.cotnd_id in seen:
            continue

        seen.add(item.cotnd_id)
        room.append({"id": item.cotnd_id, "category": ROOM_CATEGORIES[item.type]})

    return room

def convert_cotnd_to_multiworld(world: CotNDWorld, itempool: list[CotNDItemData]) -> list[Item]:
    return [world.create_item(item.name) for item in itempool]

# CotNDWorld functionality: Precollection

def granted_by_disabled_feature(world: CotNDWorld, item: CotNDItemData) -> bool:
    options = world.options

    if item.type is ItemType.MATERIAL:
        return not options.include_materials
    if item.type is ItemType.SHRINE:
        return not options.include_shrine_checks
    if item.type is ItemType.BUFF:
        return not options.buff_items
    if item.name == "Character Room Key":
        return not options.lock_character_room

    return False

def granted_zone_access_keys(world: CotNDWorld, itempool: list[CotNDItemData]) -> list[CotNDItemData]:
    mode = world.options.zone_access_keys

    if mode == "disabled":
        return [item for item in itempool if item.type is ItemType.KEY]

    # Validation has already clamped this to a zone the enabled DLC actually has.
    zone = world.options.starting_zone.value

    if mode == "separate":
        return [item for item in itempool if item.name == f"Zone {zone} Access"]

    progressive = [item for item in itempool if item.name == "Progressive Zone Access"]
    return progressive[:max(0, zone - 1)]

def starting_inventory_items(world: CotNDWorld, itempool: list[CotNDItemData]) -> list[CotNDItemData]:
    candidates = [item for item in itempool if item.inventory_type in (InventoryType.ALWAYS, InventoryType.POSSIBLE)]

    always = [item for item in candidates if item.inventory_type is InventoryType.ALWAYS]
    optional = [item for item in candidates if item.inventory_type is not InventoryType.ALWAYS]

    # The mandatory items are a floor, so 0% still leaves a Shovel and a Dagger in hand.
    target = max(math.ceil(len(candidates) * world.options.starting_inventory / 100), len(always))
    wanted = target - len(always)

    if wanted <= 0 or not optional:
        return always

    return always + world.random.sample(optional, min(wanted, len(optional)))

def precollect_multiworld_items(world: CotNDWorld, itempool: list[CotNDItemData]) -> list[CotNDItemData]:
    granted: dict[int, CotNDItemData] = {}

    # Validation has already replaced an unavailable pick with one that is in the pool.
    starting_character = world.options.starting_character.current_option_name

    requirements: set[str] = set()
    if world.options.character_unlocks != "item_only":
        requirements = CHARACTER_ITEM_REQUIREMENTS.get(starting_character, set())

    for item in itempool:
        if (granted_by_disabled_feature(world, item)
                or item.name == starting_character
                or item.name in requirements):
            granted[id(item)] = item

    for item in granted_zone_access_keys(world, itempool):
        granted[id(item)] = item

    remaining = [item for item in itempool if id(item) not in granted]
    for item in starting_inventory_items(world, remaining):
        granted[id(item)] = item

    for item in granted.values():
        world.push_precollected(world.create_item(item.name))

    return [item for item in itempool if id(item) not in granted]

# CotNDWorld functionality: Item Creation

def create_multiworld_items(world: CotNDWorld) -> None:
    pool = populate_item_pool(world)

    # Before precollection, so the room still lists what the player starts with.
    world.item_room = item_room_entries(pool)

    # Raw itempool for precollection parsing
    raw_itempool = precollect_multiworld_items(world, pool)
    itempool = convert_cotnd_to_multiworld(world, raw_itempool)

    number_of_unfilled_locations = len(world.multiworld.get_unfilled_locations(world.player))

    # If the pool outgrew the locations, open more shop and zone item rows to hold it.
    # Growth reports the restocks its new shop rows sit behind.
    added_restocks = grow_locations(world, len(itempool) - number_of_unfilled_locations)
    itempool += [world.create_item("Shop Restock") for _ in range(added_restocks)]

    number_of_items = len(itempool)
    number_of_unfilled_locations = len(world.multiworld.get_unfilled_locations(world.player))
    needed_number_of_filler_items = number_of_unfilled_locations - number_of_items

    # Only reachable once the shop has hit its 225-slot ceiling.
    if needed_number_of_filler_items < 0:
        raise ValueError(
            f"CotND (player {world.player}) built {number_of_items} items for "
            f"{number_of_unfilled_locations} locations. Reduce the item pool or raise shop_rows."
        )

    itempool += [world.create_filler() for _ in range(needed_number_of_filler_items)]

    world.multiworld.itempool += itempool
    
def filler_item_names(world: CotNDWorld) -> list[str]:
    """The filler this slot can actually receive, given the DLC it owns."""
    dlc = owned_dlc(world)

    return [
        name for name in FILLER_ITEM_NAMES
        if ALL_ITEMS.get_by_name(name).available_with(dlc)
    ]

def available_trap_weights(world: CotNDWorld) -> dict[str, int]:
    dlc = owned_dlc(world)

    return {
        name: weight for name, weight in world.options.trap_weights.items()
        if ALL_ITEMS.get_by_name(name).available_with(dlc)
    }

def get_random_filler_item_name(world: CotNDWorld) -> str:
    trap_weights = available_trap_weights(world)
    total_trap_weight = sum(trap_weights.values())

    trap_percentage = world.options.trap_percentage / 100 if total_trap_weight else 0.0

    names = filler_item_names(world)
    weights = [(1.0 - trap_percentage) / len(names)] * len(names)

    if trap_percentage:
        scale = trap_percentage / total_trap_weight
        names += trap_weights.keys()
        weights += [weight * scale for weight in trap_weights.values()]

    return world.random.choices(names, weights)[0]

# Item Groups

ITEM_ALIASES: dict[str, str] = {
    "Leek": "Spring Onion",  # Spring Onion was formerly named "Leek"
}

def make_item_groups() -> dict[str, set[str]]:
    groups: dict[str, set[str]] = defaultdict(set)

    for item in ALL_ITEMS.items:
        if item.type not in PLURALS:
            continue
        group_name = PLURALS[item.type]
        groups[group_name].add(item.name)

    for alias, target in ITEM_ALIASES.items():
        if target in ALL_ITEMS.get_item_name_to_item():
            groups[alias].add(target)

    return dict(groups)

ITEM_NAME_GROUPS = make_item_groups()

from __future__ import annotations

import json
import math
import pkgutil
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, Final, Optional

from BaseClasses import Location
from worlds.cotnd.Regions import CRYPT_REGION, LOBBY_REGION, zone_region
from worlds.cotnd.Utils import DLC, max_zone, owned_dlc, shrine_has_valid_character

if TYPE_CHECKING:
    from . import CotNDWorld

BASE_LOCATION_CODE: Final = 742_080
DATA_RESOURCE: Final = "data/locations.json"

SHOP_ROW_SIZE: Final = 9
BASE_SHOP_SLOTS: Final = 69
AMPLIFIED_SHOP_SLOTS: Final = 29
SYNCHRONY_SHOP_SLOTS: Final = 4
SHOPKEEPER_COUNT = 3

# 225 shop locations exist in the data; the shop can never grow past them.
TOTAL_SHOP_ROWS: Final = 25

# 125 zone item locations exist in the data: index 1-25 across five zones.
TOTAL_ZONE_ITEM_ROWS: Final = 25

class CotNDLocation(Location):
    game: str = "Crypt of the NecroDancer"

class LocationType(Enum):
    FLOOR          = auto()
    ZONE           = auto()
    UNIQUE_BOSS    = auto()
    ALL_ZONES      = auto()
    EXTRA_MODE     = auto()
    SHOP           = auto()
    TUTORIAL       = auto()
    NPC            = auto()
    SHRINE         = auto()
    ZONE_ITEM       = auto()
    FLAWLESS_CHEST = auto()
    EVENT          = auto()

PLURALS: dict[LocationType, str] = {
    LocationType.FLOOR: "Floors",
    LocationType.ZONE: "Zones",
    LocationType.UNIQUE_BOSS: "Story Bosses",
    LocationType.ALL_ZONES: "All Zones Completions",
    LocationType.EXTRA_MODE: "Extra Modes Completions",
    LocationType.SHOP: "Shop Slots",
    LocationType.TUTORIAL: "Codex Rooms",
    LocationType.NPC: "Caged NPCs",
    LocationType.SHRINE: "Shrines",
    LocationType.ZONE_ITEM: "Zone Items",
    LocationType.FLAWLESS_CHEST: "Flawless Chests",
}

@dataclass(slots=True)
class CotNDLocationData:
    name: str
    type: LocationType
    character: Optional[str]
    dlc: DLC
    zone: Optional[int]
    floor: Optional[int] = None
    index: Optional[int] = None
    goal: Optional[str] = None
    excluded_dlc: DLC = DLC.NONE
    code: Optional[int] = None

    def available_with(self, owned_dlc: DLC) -> bool:
        owned = owned_dlc | DLC.BASE
        return self.dlc in owned and not (self.excluded_dlc & owned)

@dataclass(slots=True)
class CotNDLocationPool:
    locations: list[CotNDLocationData]
    _by_name: dict[str, CotNDLocationData]
    _by_code: dict[int, CotNDLocationData]

    def __init__(self, locations: list[CotNDLocationData]):
        self.locations = locations

        self._by_name = {}
        self._by_code = {}

        next_code = BASE_LOCATION_CODE

        for location in self.locations:
            if location.name in self._by_name:
                raise ValueError(f"Duplicate location name: {location.name}")

            self._by_name[location.name] = location

            if location.type is LocationType.EVENT:
                location.code = None
                continue

            location.code = next_code
            self._by_code[location.code] = location
            next_code += 1

    def get_location_name_to_id(self) -> dict[str, int]:
        return {location.name: location.code for location in self.locations if location.code is not None}

    def get_location_name_to_location(self) -> dict[str, CotNDLocationData]:
        return {location.name: location for location in self.locations}

    def get_by_name(self, name: str) -> CotNDLocationData:
        return self._by_name[name]

    def get_by_code(self, code: int) -> CotNDLocationData:
        return self._by_code[code]


def parse_location(entry: dict[str, Any]) -> CotNDLocationData:
    return CotNDLocationData(
        name=entry["name"],
        type=LocationType[entry["type"].upper()],
        character=entry.get("character"),
        dlc=DLC.parse(entry["dlc"]),
        zone=entry.get("zone"),
        floor=entry.get("floor"),
        index=entry.get("index"),
        goal=entry.get("goal"),
        excluded_dlc=DLC.parse(entry.get("excluded_dlc", ())),
    )


def load_locations(resource: str = DATA_RESOURCE) -> list[CotNDLocationData]:
    data = pkgutil.get_data(__name__, resource)

    if data is None:
        raise FileNotFoundError(f"{resource}: missing from the cotnd world package")

    entries = json.loads(data.decode("utf-8"))

    if not isinstance(entries, list):
        raise ValueError(f"{resource}: expected a list of locations, got {type(entries).__name__}")

    return [parse_location(entry) for entry in entries]


def load_location_pool(resource: str = DATA_RESOURCE) -> CotNDLocationPool:
    return CotNDLocationPool(load_locations(resource))

# Master location pool for reference in World, Client, etc.

ALL_LOCATIONS = load_location_pool()
LOCATION_NAME_TO_ID = ALL_LOCATIONS.get_location_name_to_id()

# The bosses each story character must beat, and the zone they are fought in.
STORY_BOSSES: Final[dict[str, tuple[tuple[str, int], ...]]] = {
    "Cadence": (("Dead Ringer", 4), ("NecroDancer", 4)),
    "Melody": (("NecroDancer", 4),),
    "Aria": (("Golden Lute", 1),),
    "Nocturna": (("Frankensteinway", 5), ("The Conductor", 5)),
}

def story_boss_keys(dlc: DLC) -> list[tuple[str, str]]:
    return [(character, boss)
            for character, bosses in STORY_BOSSES.items()
            if character != "Nocturna" or DLC.AMPLIFIED in dlc
            for boss, _zone in bosses]

def location_from_name(name: str) -> CotNDLocationData:
    return ALL_LOCATIONS.get_by_name(name)

def location_from_code(code: int) -> CotNDLocationData:
    return ALL_LOCATIONS.get_by_code(code)

# Location pool population

# Which floors carry a check, keyed by the zone_progress_checks option.
ZONE_PROGRESS_FLOORS: Final[dict[int, tuple[int, ...]]] = {
    1: (),
    2: (2,),
    3: (1, 3),
    4: (1, 2, 3),
}

# Exactly one victory event survives, chosen by the victory_trigger option.
VICTORY_TRIGGER_LOCATIONS: Final[dict[str, str]] = {
    "disabled": "Goal Completion",
    "ensemble": "Ensemble Completion",
    "boss_rush": "Boss Rush Completion",
    "expensive_purchase": "Expensive Purchase Completion",
}

def shop_rows(world: CotNDWorld, dlc: DLC) -> int:
    if (chosen := world.options.shop_rows.value) >= 0:
        return chosen

    slots = BASE_SHOP_SLOTS
    if DLC.AMPLIFIED in dlc:
        slots += AMPLIFIED_SHOP_SLOTS
    if DLC.SYNCHRONY in dlc:
        slots += SYNCHRONY_SHOP_SLOTS

    return math.ceil(slots / SHOP_ROW_SIZE)

def add_rows(world: CotNDWorld, location_type: LocationType, current: int, added: int,
             dlc: DLC) -> None:
    # Opens rows current+1 through current+added of one indexed location type
    create_regular_locations(world, [location for location in ALL_LOCATIONS.locations
                                     if location.type is location_type
                                     and location.index is not None
                                     and current < location.index <= current + added
                                     and location.available_with(dlc)], {})

def grow_locations(world: CotNDWorld, shortfall: int) -> int:
    # Open more locations until the item pool fits, and report the Shop Restocks owed.
    if shortfall <= 0:
        return 0

    dlc = owned_dlc(world)
    zone_row = max_zone(dlc)

    shop_start = shop_rows(world, dlc)
    zone_start = world.options.items_per_zone.value
    shop_added = zone_added = restocks = 0

    prefer_shop = True
    zone_excluded = zone_start == 0

    while shortfall > 0:
        zone_room = not zone_excluded and zone_start + zone_added < TOTAL_ZONE_ITEM_ROWS
        # Only honor shop_rows = 0 while the zones can still absorb the shortfall.
        shop_room = (shop_start + shop_added < TOTAL_SHOP_ROWS
                     and (world.options.shop_rows.value != 0 or not zone_room))

        if not (shop_room or zone_room):
            break

        if shop_room and (prefer_shop or not zone_room):
            shop_added += 1
            # The first row is free; every row after it is gated behind one more restock
            gated = shop_start + shop_added > 1
            restocks += 1 if gated else 0
            shortfall -= SHOP_ROW_SIZE - (1 if gated else 0)
        else:
            zone_added += 1
            shortfall -= zone_row

        prefer_shop = not prefer_shop

    if shop_added:
        add_rows(world, LocationType.SHOP, shop_start, shop_added, dlc)
    if zone_added:
        add_rows(world, LocationType.ZONE_ITEM, zone_start, zone_added, dlc)

    return restocks

def available_character_names(dlc: DLC, blacklist: set[str]) -> set[str]:
    """Characters whose locations survive the DLC filter and the blacklist."""
    return {location.character for location in ALL_LOCATIONS.locations
            if location.character is not None
            and location.character not in blacklist
            and location.available_with(dlc)}

def populate_location_pool(world: CotNDWorld) -> list[CotNDLocationData]:
    locations: list[CotNDLocationData] = []
    options = world.options
    dlc = owned_dlc(world)
    blacklist = set(options.character_blacklist.value)

    goal = options.goal.current_key
    kept_floors = ZONE_PROGRESS_FLOORS[options.zone_progress_checks.value]
    victory_location = VICTORY_TRIGGER_LOCATIONS[options.victory_trigger.current_key]
    characters = available_character_names(dlc, blacklist)

    rows = shop_rows(world, dlc)

    for location in ALL_LOCATIONS.locations:
        # Shop rows come straight from the option; the restock items follow from them.
        if location.type is LocationType.SHOP:
            if location.index is not None and location.index > rows:
                continue
            locations.append(location)
            continue

        # DLC filtering
        if not location.available_with(dlc):
            continue

        # Character blacklist
        if location.character is not None and location.character in blacklist:
            continue

        # Each goal keeps only the completions it scores, and one victory trigger.
        if location.goal is not None and location.goal != goal:
            continue

        if location.type is LocationType.EVENT and location.character is None:
            if location.name != victory_location:
                continue

        # Floors are kept per the spacing table; the zone clear is always a check.
        if location.type is LocationType.FLOOR and location.floor not in kept_floors:
            continue

        # Codex rooms
        if location.type is LocationType.TUTORIAL and not options.include_codex_checks:
            continue

        # Shrines a surviving character can still activate
        if location.type is LocationType.SHRINE:
            if not options.include_shrine_checks:
                continue
            if not shrine_has_valid_character(location.name, characters):
                continue

        # Zone items, trimmed from the generated maximum down to this slot's option.
        # Zero of them is how a slot turns item checks off.
        if location.type is LocationType.ZONE_ITEM:
            if location.index is not None and location.index > options.items_per_zone.value:
                continue

        # Flawless chests
        if location.type is LocationType.FLAWLESS_CHEST and not options.include_flawless_chest_checks:
            continue

        # Extra modes
        if location.type is LocationType.EXTRA_MODE:
            if location.name.removesuffix(" Mode") not in options.included_extra_modes:
                continue

        locations.append(location)

    return locations

# Location creation

LOBBY_TYPES: Final = frozenset({LocationType.SHOP, LocationType.TUTORIAL})
GOAL_EVENT_ITEM: Final = "Complete"
VICTORY_EVENT_ITEM: Final = "Victory"
CAGED_PREFIX: Final = "Caged "

def region_for(location: CotNDLocationData, npc_zones: dict[str, int]) -> str:
    if location.type in LOBBY_TYPES:
        return LOBBY_REGION

    # A cage sits in whichever zone generation scattered it to, so region membership is needed
    if location.type is LocationType.NPC:
        return zone_region(npc_zones[location.name.removeprefix(CAGED_PREFIX)])

    if location.zone is not None:
        return zone_region(location.zone, location.character)

    return CRYPT_REGION

def prefill_npc_placements(world: CotNDWorld, locations: list[CotNDLocationData]) -> None:
    if world.options.lobby_npc_items:
        return

    for location in locations:
        if location.type is not LocationType.NPC:
            continue

        npc = location.name.removeprefix(CAGED_PREFIX)
        world.get_location(location.name).place_locked_item(world.create_item(npc))

def create_all_locations(world: CotNDWorld) -> None:
    locations = populate_location_pool(world)
    npc_zones = {npc: info["zone"] for npc, info in world.caged_npcs.items()}

    create_regular_locations(world, locations, npc_zones)
    create_events(world, locations, npc_zones)
    prefill_npc_placements(world, locations)

def create_regular_locations(world: CotNDWorld, locations: list[CotNDLocationData],
                             npc_zones: dict[str, int]) -> None:
    by_region: dict[str, dict[str, Optional[int]]] = defaultdict(dict)

    for location in locations:
        if location.type is LocationType.EVENT:
            continue
        by_region[region_for(location, npc_zones)][location.name] = location.code

    for region_name, region_locations in by_region.items():
        world.get_region(region_name).add_locations(region_locations, CotNDLocation)

def create_events(world: CotNDWorld, locations: list[CotNDLocationData],
                  npc_zones: dict[str, int]) -> None:
    for location in locations:
        if location.type is not LocationType.EVENT:
            continue

        if location.character is None:
            item_name = VICTORY_EVENT_ITEM
        elif location.goal == "story":
            item_name = location.name
        else:
            item_name = GOAL_EVENT_ITEM

        region = world.get_region(region_for(location, npc_zones))
        region.add_event(location.name, item_name, location_type=CotNDLocation, item_type=world.item_class)

# Location groups

def make_location_groups() -> dict[str, set[str]]:
    groups: dict[str, set[str]] = defaultdict(set)

    for location in ALL_LOCATIONS.locations:
        if location.type not in PLURALS:
            continue
        groups[PLURALS[location.type]].add(location.name)

    return dict(groups)

LOCATION_NAME_GROUPS = make_location_groups()

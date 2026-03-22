import math
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum, auto
from typing import Set, Optional

from BaseClasses import Location
from worlds.cotnd.Characters import get_available_characters
from worlds.cotnd.Items import CotNDItemData
from worlds.cotnd.Utils import LOBBY_NPCS, normalize_dlc, DLC, EXTRA_MODES

BASE_CODE = 742_080
BASE_SHOP_COUNT = 69
AMP_SHOP_COUNT = 29
SYNC_SHOP_COUNT = 4
# 225 shop locations should provide an ample barrier for edge case options (e.g., 1 character, no codex locations, no per_level checks, goal = zones)
TOTAL_SHOP_LOCATIONS = 225
SHOPKEEPER_COUNT = 3
SHOP_LOCATION_RANGE = {"start": BASE_CODE, "end": BASE_CODE + TOTAL_SHOP_LOCATIONS}


class CotNDLocation(Location):
    game: str = "Crypt of the NecroDancer"


class LocationType(Enum):
    FLOOR = auto()
    ZONE = auto()
    BOSS = auto()
    UNIQUE_BOSS = auto()
    ALL_ZONES = auto()
    EXTRA_MODE = auto()
    SHOP = auto()
    TUTORIAL = auto()
    NPC = auto()
    ALL_ZONES_EVENT = auto()
    ZONES_EVENT = auto()


PLURALS: dict[LocationType, str] = {
    LocationType.FLOOR: "Floors",
    LocationType.ZONE: "Zones",
    LocationType.BOSS: "Zone Bosses",
    LocationType.UNIQUE_BOSS: "Story Bosses",
    LocationType.ALL_ZONES: "All Zones Completions",
    LocationType.EXTRA_MODE: "Extra Modes Completions",
    LocationType.SHOP: "Shop Slots",
    LocationType.TUTORIAL: "Codex Rooms",
    LocationType.NPC: "Caged NPCs"
}


@dataclass(frozen=True, slots=True)
class RawCotNDLocationData:
    name: str
    type: LocationType
    character: Optional[str]
    dlc: DLC
    zone: Optional[int]


@dataclass(frozen=True, slots=True)
class CotNDLocationData(RawCotNDLocationData):
    code: int | None


def generate_shop_locations(num: int) -> list[RawCotNDLocationData]:
    shopkeepers = ["Hephaestus", "Merlin", "Dungeon Master"]

    directions = ["Center", "Left", "Right"]

    locations: list[RawCotNDLocationData] = []
    round_index = 1

    while len(locations) < num:
        for direction in directions:
            for shopkeeper in shopkeepers:
                if len(locations) >= num:
                    return locations

                locations.append(
                    RawCotNDLocationData(f"{shopkeeper} - {direction} Shop Item {round_index}", LocationType.SHOP, None,
                                         DLC.BASE, None)
                )

        round_index += 1

    return locations


def generate_codex_locations():
    codex_locs = [
        RawCotNDLocationData("Dragon Lore", LocationType.TUTORIAL, None, DLC.BASE, None),
        RawCotNDLocationData("Trap Lore", LocationType.TUTORIAL, None, DLC.BASE, None),
        RawCotNDLocationData("Bomb Lore", LocationType.TUTORIAL, None, DLC.BASE, None),
        RawCotNDLocationData("How to Get Away with Murder", LocationType.TUTORIAL, None, DLC.BASE, None)
    ]

    return codex_locs


def generate_npc_locations():
    return [RawCotNDLocationData(f"Caged {npc}", LocationType.NPC, None, DLC.BASE, None) for npc in LOBBY_NPCS]


def generate_zone_clear_locations(characters: list[CotNDItemData]):
    zone_count = 5

    zone_locations: list[RawCotNDLocationData] = []

    for char in characters:
        char_name = char.name
        dlc = char.dlc
        for zone in range(1, zone_count + 1):
            zone_locations.extend(
                [RawCotNDLocationData(f"{char_name} - Zone {zone} - Floor {floor}", LocationType.FLOOR, char_name,
                                      dlc, zone) for floor in
                 range(1, 4)]
            )

            if not char_name == "Dove":
                zone_locations.append(
                    RawCotNDLocationData(f"{char_name} - Zone {zone} - Boss", LocationType.BOSS, char_name, dlc, zone))
            zone_locations.append(
                RawCotNDLocationData(f"{char_name} - Zone {zone}", LocationType.ZONE, char_name, dlc, zone))

            if zone == 4:
                if char_name == "Cadence":
                    zone_locations.append(
                        RawCotNDLocationData(f"{char_name} - Dead Ringer", LocationType.UNIQUE_BOSS, char_name, dlc,
                                             zone))
                    zone_locations.append(
                        RawCotNDLocationData(f"{char_name} - NecroDancer", LocationType.UNIQUE_BOSS, char_name, dlc,
                                             zone))
                elif char_name == "Melody":
                    zone_locations.append(
                        RawCotNDLocationData(f"{char_name} - NecroDancer", LocationType.UNIQUE_BOSS, char_name, dlc,
                                             zone))
            elif zone == 5 and char_name == "Nocturna":
                zone_locations.append(
                    RawCotNDLocationData(f"{char_name} - Frankensteinway", LocationType.UNIQUE_BOSS, char_name, dlc,
                                         zone))
                zone_locations.append(
                    RawCotNDLocationData(f"{char_name} - The Conductor", LocationType.UNIQUE_BOSS, char_name, dlc,
                                         zone))
            elif zone == 1 and char_name == "Aria":
                zone_locations.append(
                    RawCotNDLocationData(f"{char_name} - Dead Ringer", LocationType.UNIQUE_BOSS, char_name, dlc, zone))
                zone_locations.append(
                    RawCotNDLocationData(f"{char_name} - Golden Lute", LocationType.UNIQUE_BOSS, char_name, dlc, zone))

    zone_locations.extend(
        [RawCotNDLocationData(f"{char.name} - All Zones", LocationType.ALL_ZONES, char.name, char.dlc, None) for char in
         characters])

    return zone_locations


def generate_extra_mode_locations(characters: list[CotNDItemData]):
    locations: list[RawCotNDLocationData] = []

    for mode_dlc, modes in EXTRA_MODES.items():
        dlc_enum = DLC(mode_dlc)

        for char in characters:
            char_name = char.name

            for mode in modes:
                locations.append(
                    RawCotNDLocationData(f"{char_name} - {mode}", LocationType.EXTRA_MODE, char_name, dlc_enum, None))

    return locations


def generate_event_locations(characters: list[CotNDItemData]):
    all_zones: list[RawCotNDLocationData] = []
    zones: list[RawCotNDLocationData] = []
    for char in characters:
        all_zones.append(
            RawCotNDLocationData(f"{char.name} - Beat All Zones", LocationType.ALL_ZONES_EVENT, char.name, char.dlc,
                                 None))
        for zone in range(1, 6):
            zones.append(
                RawCotNDLocationData(f"{char.name} - Beat Zone {zone}", LocationType.ZONES_EVENT, char.name, char.dlc,
                                     zone))

    return all_zones + zones


def load_all_locations():
    characters = get_available_characters(None, {"Synchrony", "Amplified", "Miku", "Shovel Knight"})

    shop_locs = generate_shop_locations(TOTAL_SHOP_LOCATIONS)
    npc_locations = generate_npc_locations()
    codex_locs = generate_codex_locations()
    zone_locs = generate_zone_clear_locations(characters)
    extra_mode_locs = generate_extra_mode_locations(characters)
    event_locs = generate_event_locations(characters)

    all_locs = shop_locs + npc_locations + codex_locs + zone_locs + extra_mode_locs + event_locs
    loaded: list[CotNDLocationData] = []
    seen_names: Set[str] = set()

    index = 0

    for loc in all_locs:
        if loc.name in seen_names:
            raise ValueError(f"Duplicate location name: {loc.name}")

        seen_names.add(loc.name)

        loaded.append(
            CotNDLocationData(
                name=loc.name,
                type=loc.type,
                code=BASE_CODE + index if loc.type not in (
                    LocationType.ALL_ZONES_EVENT, LocationType.ZONES_EVENT) else None,
                character=loc.character,
                dlc=loc.dlc,
                zone=loc.zone
            )
        )
        index += 1

    return loaded


ALL_LOCATIONS = load_all_locations()
LOCATIONS_BY_NAME = {l.name: l for l in ALL_LOCATIONS}
LOCATIONS_BY_CODE = {l.code: l for l in ALL_LOCATIONS}


def location_from_name(name: str):
    return LOCATIONS_BY_NAME[name]


def location_from_code(code: int):
    return LOCATIONS_BY_CODE[code]


def get_locations_list(item_list: list[CotNDItemData], dlc: Set[str], character_blacklist: Set[str], goal: int,
                       extra_modes: Set[str], codex_checks: bool, per_level: bool):
    dlc_enums = normalize_dlc(dlc)
    location_list = []

    for location in ALL_LOCATIONS:
        # We'll calculate shops locations afterward
        if location.type is LocationType.SHOP:
            continue

        # Remove all locations associated with disabled dlc
        if location.dlc is not DLC.BASE and location.dlc not in dlc_enums:
            continue

        # Remove all zone 5 locations if Amplified isn't enabled
        if location.zone == 5 and DLC.AMPLIFIED not in dlc_enums:
            continue

        # Remove blacklisted characters
        if location.character is not None and location.character in character_blacklist:
            continue

        # Remove All Zones checks if the goal is just zones
        if goal == 1 and (location.type is LocationType.ALL_ZONES or location.type is LocationType.ALL_ZONES_EVENT):
            continue
        # Remove Zone events if the goal is All Zones
        elif goal == 0 and location.type is LocationType.ZONES_EVENT:
            continue

        # Remove zone complete checks
        if per_level:
            if location.type is LocationType.ZONE:
                continue
        # Remove per-level checks
        elif location.type is LocationType.FLOOR or location.type is LocationType.BOSS:
            continue

        # Remove checks not in extra_modes
        if location.type is LocationType.EXTRA_MODE:
            _, mode = location.name.split(" - ", 1)
            if mode not in extra_modes:
                continue

        # Remove tutorial checks if disabled
        if not codex_checks and location.type is LocationType.TUTORIAL:
            continue

        location_list.append(location)

    # How many locations are still needed for items
    missing_locations = len(item_list) - len(location_list)

    # Minimum shop count based on enabled DLCs
    min_shop_count = BASE_SHOP_COUNT

    if DLC.AMPLIFIED in dlc_enums:
        min_shop_count += AMP_SHOP_COUNT

    if DLC.SYNCHRONY in dlc_enums:
        min_shop_count += SYNC_SHOP_COUNT

    # Final number of shop locations to include
    shop_needed = max(min_shop_count, missing_locations)

    # Inflate shop locations until unlock items fit
    while True:
        required_unlocks = max(math.ceil(shop_needed / (SHOPKEEPER_COUNT * 3)) - 1, 0)
        free_locations = (len(location_list) + shop_needed) - len(item_list)

        if free_locations >= required_unlocks or shop_needed > TOTAL_SHOP_LOCATIONS:
            break

        shop_needed += 1

    if shop_needed > TOTAL_SHOP_LOCATIONS:
        raise ValueError("Shop Items needed exceed Shop Location count! Please inform the APWorld creator!")

    # Pull shop locations in deterministic order, preserving codes
    shop_locations = [loc for loc in ALL_LOCATIONS if loc.type is LocationType.SHOP][:shop_needed]

    location_list.extend(shop_locations)

    return location_list


def get_last_shop_item_row(locations: list[CotNDLocationData]) -> int:
    max_index = 0

    for loc in locations:
        if loc.type is not LocationType.SHOP:
            continue

        try:
            index = int(loc.name.rsplit(" Shop Item ", 1)[1])
            max_index = max(max_index, index)
        except (IndexError, ValueError):
            continue

    return max_index


def make_location_groups() -> dict[str, set[str]]:
    groups: dict[str, set[str]] = defaultdict(set)

    for location in ALL_LOCATIONS:
        if location.type not in PLURALS:
            continue
        group_name = PLURALS[location.type]
        groups[group_name].add(location.name)

    return dict(groups)


all_locations = ALL_LOCATIONS.copy()
location_name_groups = make_location_groups()

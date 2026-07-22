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
    VICTORY_EVENT = auto()


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
    required_dlcs: frozenset[DLC]
    zone: Optional[int]


@dataclass(frozen=True, slots=True)
class CotNDLocationData(RawCotNDLocationData):
    code: int | None


def _required_dlcs(*dlcs: DLC) -> frozenset[DLC]:
    """Build the set of DLCs required for a location, excluding BASE (always available)."""
    return frozenset(d for d in dlcs if d != DLC.BASE)


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
                                         frozenset(), None)
                )

        round_index += 1

    return locations


def generate_codex_locations():
    codex_locs = [
        RawCotNDLocationData("Dragon Lore", LocationType.TUTORIAL, None, frozenset(), None),
        RawCotNDLocationData("Trap Lore", LocationType.TUTORIAL, None, frozenset(), None),
        RawCotNDLocationData("Bomb Lore", LocationType.TUTORIAL, None, frozenset(), None),
        RawCotNDLocationData("How to Get Away with Murder", LocationType.TUTORIAL, None, frozenset(), None)
    ]

    return codex_locs


def generate_npc_locations():
    return [RawCotNDLocationData(f"Caged {npc}", LocationType.NPC, None, frozenset(), None) for npc in LOBBY_NPCS]


def generate_zone_clear_locations(characters: list[CotNDItemData]):
    zone_count = 5

    zone_locations: list[RawCotNDLocationData] = []

    for char in characters:
        char_name = char.name
        for zone in range(1, zone_count + 1):
            # Zone 5 only exists in Amplified; all zone-5 locations require it regardless of character.
            required = _required_dlcs(char.dlc, DLC.AMPLIFIED) if zone == 5 else _required_dlcs(char.dlc)
            zone_locations.extend(
                [RawCotNDLocationData(f"{char_name} - Zone {zone} - Floor {floor}", LocationType.FLOOR, char_name,
                                      required, zone) for floor in
                 range(1, 4)]
            )

            if not char_name == "Dove":
                zone_locations.append(
                    RawCotNDLocationData(f"{char_name} - Zone {zone} - Boss", LocationType.BOSS, char_name, required, zone))
            zone_locations.append(
                RawCotNDLocationData(f"{char_name} - Zone {zone}", LocationType.ZONE, char_name, required, zone))

            if zone == 4:
                if char_name == "Cadence":
                    zone_locations.append(
                        RawCotNDLocationData(f"{char_name} - Dead Ringer", LocationType.UNIQUE_BOSS, char_name, required,
                                             zone))
                    zone_locations.append(
                        RawCotNDLocationData(f"{char_name} - NecroDancer", LocationType.UNIQUE_BOSS, char_name, required,
                                             zone))
                elif char_name == "Melody":
                    zone_locations.append(
                        RawCotNDLocationData(f"{char_name} - NecroDancer", LocationType.UNIQUE_BOSS, char_name, required,
                                             zone))
            elif zone == 5 and char_name == "Nocturna":
                zone_locations.append(
                    RawCotNDLocationData(f"{char_name} - Frankensteinway", LocationType.UNIQUE_BOSS, char_name, required,
                                         zone))
                zone_locations.append(
                    RawCotNDLocationData(f"{char_name} - The Conductor", LocationType.UNIQUE_BOSS, char_name, required,
                                         zone))
            elif zone == 1 and char_name == "Aria":
                zone_locations.append(
                    RawCotNDLocationData(f"{char_name} - Golden Lute", LocationType.UNIQUE_BOSS, char_name, required, zone))

    zone_locations.extend(
        [RawCotNDLocationData(f"{char.name} - All Zones", LocationType.ALL_ZONES, char.name, _required_dlcs(char.dlc), None) for char in
         characters])

    return zone_locations


def generate_extra_mode_locations():
    locations: list[RawCotNDLocationData] = []

    for mode_dlc, modes in EXTRA_MODES.items():
        dlc_enum = DLC(mode_dlc)
        required = _required_dlcs(dlc_enum)

        for mode in modes:
            locations.append(
                RawCotNDLocationData(f"{mode} Mode", LocationType.EXTRA_MODE, None, required, None))

    return locations


def generate_event_locations(characters: list[CotNDItemData]):
    all_zones: list[RawCotNDLocationData] = []
    zones: list[RawCotNDLocationData] = []
    for char in characters:
        all_zones.append(
            RawCotNDLocationData(f"{char.name} - Beat All Zones", LocationType.ALL_ZONES_EVENT, char.name,
                                 _required_dlcs(char.dlc), None))
        for zone in range(1, 6):
            required = _required_dlcs(char.dlc, DLC.AMPLIFIED) if zone == 5 else _required_dlcs(char.dlc)
            zones.append(
                RawCotNDLocationData(f"{char.name} - Beat Zone {zone}", LocationType.ZONES_EVENT, char.name, required,
                                     zone))

    victory = [
        RawCotNDLocationData("Goal Completion", LocationType.VICTORY_EVENT, None, frozenset(), None),
        RawCotNDLocationData("Ensemble Completion", LocationType.VICTORY_EVENT, None, frozenset(), None),
        RawCotNDLocationData("Boss Rush Completion", LocationType.VICTORY_EVENT, None, frozenset(), None),
        RawCotNDLocationData("Expensive Purchase Completion", LocationType.VICTORY_EVENT, None, frozenset(), None),
    ]
    return all_zones + zones + victory


def load_all_locations():
    characters = get_available_characters(None, {"Synchrony", "Amplified", "Miku", "Shovel Knight"})

    shop_locs = generate_shop_locations(TOTAL_SHOP_LOCATIONS)
    npc_locations = generate_npc_locations()
    codex_locs = generate_codex_locations()
    zone_locs = generate_zone_clear_locations(characters)
    extra_mode_locs = generate_extra_mode_locations()
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
                    LocationType.ALL_ZONES_EVENT, LocationType.ZONES_EVENT, LocationType.VICTORY_EVENT) else None,
                character=loc.character,
                required_dlcs=loc.required_dlcs,
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


# VictoryTrigger option key -> the VICTORY_EVENT location that hosts the "Victory"
# event. Every trigger (including Disabled) has one so completion is uniformly
# Has("Victory") and the playthrough always ends on a Victory. The trigger only
# changes the mod's in-game catalyst, not AP logic. Keyed by option key (not
# number) so reordering the option stays safe.
VICTORY_TRIGGER_LOCATIONS: dict[str, str] = {
    "disabled": "Goal Completion",
    "ensemble": "Ensemble Completion",
    "boss_rush": "Boss Rush Completion",
    "expensive_purchase": "Expensive Purchase Completion",
}


def get_locations_list(item_list: list[CotNDItemData], dlc: Set[str], character_blacklist: Set[str], goal: int,
                       extra_modes: Set[str], codex_checks: bool, per_level: bool, victory_trigger: str = "Ensemble"):
    dlc_enums = normalize_dlc(dlc)
    location_list = []

    for location in ALL_LOCATIONS:
        # We'll calculate shops locations afterward
        if location.type is LocationType.SHOP:
            continue

        # Remove all locations whose required DLCs are not all enabled
        if not location.required_dlcs.issubset(dlc_enums):
            continue

        # Remove blacklisted characters
        if location.character is not None and location.character in character_blacklist:
            continue

        # Remove All Zones checks if the goal is not All Zones
        if goal in (1, 2) and (location.type is LocationType.ALL_ZONES or location.type is LocationType.ALL_ZONES_EVENT):
            continue
        # Remove Zone events if the goal is All Zones or Golden Lute Shards
        elif goal in (0, 2) and location.type is LocationType.ZONES_EVENT:
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
            if location.name.removesuffix(" Mode") not in extra_modes:
                continue

        # Remove tutorial checks if disabled
        if not codex_checks and location.type is LocationType.TUTORIAL:
            continue

        if location.type is LocationType.VICTORY_EVENT:
            if location.name != VICTORY_TRIGGER_LOCATIONS.get(victory_trigger):
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

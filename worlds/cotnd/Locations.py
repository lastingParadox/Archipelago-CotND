from typing import Dict, List, TypedDict, Tuple
from BaseClasses import Location
from .Options import CotNDOptions, all_game_modes
from .Characters import base_chars, amplified_chars, synchrony_chars, miku_chars

base_code = 742_080
shop_location_range = {"start": 742_187, "end": 742_289}


class CotNDLocation(Location):
    game: str = "Crypt of the NecroDancer"


class LocationDict(TypedDict):
    name: str
    code: int


zone_clear = {
    "location_text": {
        "single_zone": "Zone",
        "all_zones": "All Zones"
    },
    "location_zones": {
        "base": 4,
        "amplified": 1,
        "synchrony": 0,
        "miku": 0
    },
    "location_chars": {
        "base": base_chars,
        "amplified": amplified_chars,
        "synchrony": synchrony_chars,
        "miku": miku_chars
    }
}

hephaestus = {
    "location_text": {
        "left": "Hephaestus - Left Shop Item",
        "center": "Hephaestus - Center Shop Item",
        "right": "Hephaestus - Right Shop Item"
    },
    "location_amounts": {
        "base": {
            "left": 11,
            "center": 19,
            "right": 8
        },
        "amplified": {
            "left": 3,
            "center": 13,
            "right": 4
        },
        "synchrony": {
            "left": 3,
            "center": 0,
            "right": 1
        }
    }
}

merlin = {
    "location_text": {
        "left": "Merlin - Left Shop Item",
        "center": "Merlin - Center Shop Item",
        "right": "Merlin - Right Shop Item"
    },
    "location_amounts": {
        "base": {
            "left": 5,
            "center": 11,
            "right": 7
        },
        "amplified": {
            "left": 0,
            "center": 3,
            "right": 6
        },
        "synchrony": {
            "left": 0,
            "center": 0,
            "right": 0
        }
    }
}

# Dungeon Master locations are base game
dungeon_master_locations = (
        [f"Dungeon Master - Left Shop Item {i}" for i in range(1, 4)]
        + [f"Dungeon Master - Center Shop Item {i}" for i in range(1, 3)]
        + [f"Dungeon Master - Right Shop Item {i}" for i in range(1, 4)]
)


def build_location_dicts(locations: List[str], starting_code: int = base_code) -> List[LocationDict]:
    return [{"name": name, "code": starting_code + i} for i, name in enumerate(locations)]


def get_shop_locations(dlcs: List[str]) -> List[str]:
    shop_locations = dungeon_master_locations.copy()

    hephaestus_locations = hephaestus["location_amounts"]["base"].copy()
    merlin_locations = merlin["location_amounts"]["base"].copy()

    if "Amplified" in dlcs:
        for key in hephaestus_locations:
            hephaestus_locations[key] += hephaestus["location_amounts"]["amplified"].get(key, 0)
            merlin_locations[key] += merlin["location_amounts"]["amplified"].get(key, 0)

    if "Synchrony" in dlcs:
        for key in hephaestus_locations:
            hephaestus_locations[key] += hephaestus["location_amounts"]["synchrony"].get(key, 0)
            merlin_locations[key] += merlin["location_amounts"]["synchrony"].get(key, 0)

    for direction, amount in hephaestus_locations.items():
        shop_locations += [f"{hephaestus['location_text'][direction]} {i}" for i in range(1, amount + 1)]

    for direction, amount in merlin_locations.items():
        shop_locations += [f"{merlin['location_text'][direction]} {i}" for i in range(1, amount + 1)]

    return shop_locations

def get_shop_slot_lengths(dlcs: List[str]) -> Dict[str, int]:
    slot_lengths = {}

    for npc, npc_data in [("Hephaestus", hephaestus), ("Merlin", merlin)]:
        total_counts = npc_data["location_amounts"]["base"].copy()

        if "Amplified" in dlcs:
            for key in total_counts:
                total_counts[key] += npc_data["location_amounts"]["amplified"].get(key, 0)

        if "Synchrony" in dlcs:
            for key in total_counts:
                total_counts[key] += npc_data["location_amounts"]["synchrony"].get(key, 0)

        for direction, count in total_counts.items():
            slot_key = f"{npc} - {direction.title()}"
            slot_lengths[slot_key] = count

    # Add Dungeon Master (fixed 3-2-3)
    slot_lengths["Dungeon Master - Left"] = 3
    slot_lengths["Dungeon Master - Center"] = 2
    slot_lengths["Dungeon Master - Right"] = 3

    return slot_lengths


def get_shop_locations_numbers(dlcs: List[str]):
    hephaestus_locations = hephaestus["location_amounts"]["base"].copy()
    merlin_locations = merlin["location_amounts"]["base"].copy()

    if "Amplified" in dlcs:
        for key in hephaestus_locations:
            hephaestus_locations[key] += hephaestus["location_amounts"]["amplified"].get(key, 0)
            merlin_locations[key] += merlin["location_amounts"]["amplified"].get(key, 0)

    if "Synchrony" in dlcs:
        for key in hephaestus_locations:
            hephaestus_locations[key] += hephaestus["location_amounts"]["synchrony"].get(key, 0)
            merlin_locations[key] += merlin["location_amounts"]["synchrony"].get(key, 0)

    return {
        "hephaestus_locations": hephaestus_locations,
        "merlin_locations": merlin_locations,
        "dungeon_master_locations": {
            "left": 3,
            "center": 2,
            "right": 4
        }
    }


def get_zone_clear_locations(dlcs: List[str]) -> Tuple[List[str], List[str]]:
    zone_clear_locations = []
    all_zones_clear_locations = []

    characters = zone_clear["location_chars"]["base"].copy()
    zone_amount = zone_clear["location_zones"]["base"]

    if "Amplified" in dlcs:
        characters += zone_clear["location_chars"]["amplified"]
        zone_amount += zone_clear["location_zones"]["amplified"]
    if "Synchrony" in dlcs:
        characters += zone_clear["location_chars"]["synchrony"]
        zone_amount += zone_clear["location_zones"]["synchrony"]
    if "Miku" in dlcs:
        characters += zone_clear["location_chars"]["miku"]
        zone_amount += zone_clear["location_zones"]["miku"]

    for character in characters:
        zone_clear_locations += [f"{character} - {zone_clear['location_text']['single_zone']} {zone}" for zone in
                                 range(1, zone_amount + 1)]
        all_zones_clear_locations += [f"{character} - {zone_clear['location_text']['all_zones']}"]

    return zone_clear_locations, all_zones_clear_locations

def get_extra_mode_clear_locations(dlcs: List[str], modes: List[str]) -> List[str]:
    extra_mode_clear_locations = []

    characters = zone_clear["location_chars"]["base"].copy()

    if "Amplified" in dlcs:
        characters += zone_clear["location_chars"]["amplified"]
    if "Synchrony" in dlcs:
        characters += zone_clear["location_chars"]["synchrony"]
    if "Miku" in dlcs:
        characters += zone_clear["location_chars"]["miku"]


    for character in characters:
        for mode in modes:
            extra_mode_clear_locations += [f"{character} - {mode} Mode"]

    return extra_mode_clear_locations

def get_all_locations() -> List[LocationDict]:
    zone_locations, all_zone_locations = get_zone_clear_locations(["Amplified", "Synchrony", "Miku"])
    extra_mode_locations = get_extra_mode_clear_locations(["Amplified", "Synchrony", "Miku"], all_game_modes)
    shop_locations = get_shop_locations(["Amplified", "Synchrony"])
    return build_location_dicts(zone_locations + all_zone_locations + shop_locations + extra_mode_locations)


def get_available_locations(dlcs: List[str], extra_modes: List[str] = None) -> List[LocationDict]:
    if extra_modes is None:
        extra_modes = []
    zone_locations, all_zone_locations = get_zone_clear_locations(dlcs)
    extra_mode_locations = get_extra_mode_clear_locations(dlcs, extra_modes)
    shop_locations = get_shop_locations(dlcs)

    raw_locations = zone_locations + all_zone_locations + shop_locations + extra_mode_locations
    return [all_locations[location_name] for location_name in raw_locations]


def get_regions_to_locations(options: CotNDOptions) -> Dict[str, List[LocationDict]]:
    locations = get_available_locations(options.dlc.value, options.included_extra_modes.value)

    zone_locations = [loc for loc in locations if "Zone" in loc["name"] or "Mode" in loc["name"]]
    shop_locations = [loc for loc in locations if "Zone" not in loc["name"] and "Mode" not in loc["name"]]

    return {
        "Menu": shop_locations,
        "Crypt": zone_locations,
    }


def from_id(location_id: int) -> LocationDict:
    matching = [item for item in all_locations.values() if item['code'] == location_id]
    if len(matching) == 0:
        raise ValueError(f"No item data for item id '{location_id}'")
    assert len(matching) < 2, f"Multiple item data with id '{location_id}. Please report."
    return matching[0]


all_locations = {
    location["name"]: location for location in get_all_locations()
}

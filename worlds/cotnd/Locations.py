from typing import Dict, List, TypedDict
from BaseClasses import Location
from .Characters import base_chars, amplified_chars, synchrony_chars, miku_chars

base_code = 742_080
shop_location_range = {"start": 742_080, "end": 742_182}


class CotNDLocation(Location):
    game: str = "Crypt of the NecroDancer"


class LocationDict(TypedDict):
    name: str
    code: int


DLCS = ["amplified", "synchrony", "miku"]

ZONE_CLEAR_CHARS = {
    "base": base_chars,
    "amplified": amplified_chars,
    "synchrony": synchrony_chars,
    "miku": miku_chars
}

HEPHAESTUS = {
    "name": "Hephaestus",
    "location_amounts": {
        "base": {"left": 11, "center": 19, "right": 8},
        "amplified": {"left": 3, "center": 13, "right": 4},
        "synchrony": {"left": 3, "center": 0, "right": 1}
    }
}

MERLIN = {
    "name": "Merlin",
    "location_amounts": {
        "base": {"left": 5, "center": 11, "right": 7},
        "amplified": {"left": 0, "center": 3, "right": 6},
        "synchrony": {"left": 0, "center": 0, "right": 0}
    }
}

DUNGEON_MASTER = {
    "name": "Dungeon Master",
    "location_amounts": {
        "base": {"left": 3, "center": 2, "right": 3},
        "amplified": {"left": 0, "center": 0, "right": 0},
        "synchrony": {"left": 0, "center": 0, "right": 0}
    }
}


# ==============================
# Helpers
# ==============================

def normalize_dlcs(dlcs: List[str]) -> List[str]:
    """Normalize DLC names to lowercase."""
    return [d.lower() for d in dlcs]


def apply_dlc_amounts(dlcs: List[str], amounts: Dict[str, Dict[str, int]]) -> Dict[str, int]:
    """Return totals after applying DLC-specific overrides."""
    total = amounts["base"].copy()
    for dlc in dlcs:
        if dlc in amounts:
            for key, value in amounts[dlc].items():
                total[key] = total.get(key, 0) + value
    return total


def get_characters_for_dlcs(dlcs: List[str], blacklist: List[str] | None = None) -> list[str]:
    """Return all available characters for given DLCs, minus blacklist."""
    chars: List[str] = ZONE_CLEAR_CHARS["base"].copy()
    for dlc in DLCS:
        if dlc in dlcs:
            chars += ZONE_CLEAR_CHARS[dlc]
    if blacklist:
        chars = [c for c in chars if c not in blacklist]
    return chars


def build_location_dicts(zone_locations: List[str]) -> List[LocationDict]:
    """Convert location names to dicts with placeholder codes."""
    return [{"name": loc, "code": i} for i, loc in enumerate(zone_locations, start=base_code)]


# ==============================
# Zone Clear Locations
# ==============================

def get_zone_clear_locations(dlcs: List[str], blacklist: List[str] | None = None) -> tuple[list[str], list[str]]:
    """Return (zone_clear, all_zone_clear) locations."""
    dlcs = normalize_dlcs(dlcs)
    chars = get_characters_for_dlcs(dlcs, blacklist)

    zone_locations = [f"{char} - Zone {zone}" for char in chars for zone in range(1, 6 if "amplified" in dlcs else 5)]
    all_zone_locations = [f"{char} - All Zones" for char in chars]

    return zone_locations, all_zone_locations


# ==============================
# Event Locations
# ==============================

def get_event_locations(dlcs: List[str], blacklist: List[str] | None = None, goals: List[int] | None = None) -> List[str]:
    if goals is None:
        goals = [0, 1]

    dlcs = normalize_dlcs(dlcs)
    chars = get_characters_for_dlcs(dlcs, blacklist)

    all_zone_events = [f"{char} - Beat All Zones" for char in chars]
    zone_events = [f"{char} - Beat Zone {zone}" for char in chars for zone in range(1, 6 if "amplified" in dlcs else 5)]

    event_locations = []
    if 0 in goals: event_locations += all_zone_events
    if 1 in goals: event_locations += zone_events

    return event_locations

# ==============================
# Extra Mode Clear Locations
# ==============================

EXTRA_MODES = {
    "base": ["No Beat", "Double Tempo", "Low Percent"],
    "amplified": ["Phasing", "Randomizer", "Mystery", "Hard", "No Return"],
}


def get_extra_mode_clear_locations(dlcs: List[str], blacklist: List[str] | None = None,
                                   modes: List[str] | None = None) -> List[str]:
    """Return extra mode clear locations for allowed modes."""
    dlcs = normalize_dlcs(dlcs)
    chars = get_characters_for_dlcs(dlcs, blacklist)

    available_modes = []
    for dlc, dlc_modes in EXTRA_MODES.items():
        if dlc == "base" or dlc in dlcs:
            available_modes += dlc_modes

    if modes:
        available_modes = [m for m in available_modes if m in modes]
    else:
        return []

    return [f"{char} - {mode}" for char in chars for mode in available_modes]


# ==============================
# Lobby NPC Locations
# ==============================

LOBBY_NPCS = ["Beastmaster", "Merlin", "Bossmaster", "Weaponmaster", "Diamond Dealer"]


def get_lobby_npc_locations():
    return [f"Caged {npc}" for npc in LOBBY_NPCS]


# ==============================
# Shop Locations
# ==============================

def get_shop_locations(dlcs: List[str]) -> List[str]:
    """Return all shop location names based on DLCs."""
    dlcs = normalize_dlcs(dlcs)
    shop_locations = []

    heph_totals = apply_dlc_amounts(dlcs, HEPHAESTUS["location_amounts"])
    merlin_totals = apply_dlc_amounts(dlcs, MERLIN["location_amounts"])
    dm_totals = apply_dlc_amounts(dlcs, DUNGEON_MASTER["location_amounts"])

    for direction, amount in heph_totals.items():
        shop_locations += [f"{HEPHAESTUS['name']} - {direction.title()} Shop Item {i}" for i in range(1, amount + 1)]
    for direction, amount in merlin_totals.items():
        shop_locations += [f"{MERLIN['name']} - {direction.title()} Shop Item {i}" for i in range(1, amount + 1)]
    for direction, amount in dm_totals.items():
        shop_locations += [f"{DUNGEON_MASTER['name']} - {direction.title()} Shop Item {i}" for i in
                           range(1, amount + 1)]

    return shop_locations


def get_shop_slot_lengths(dlcs: List[str]) -> Dict[str, int]:
    """Return counts of slots for each shop NPC and direction."""
    dlcs = normalize_dlcs(dlcs)
    slot_lengths = {}

    heph_totals = apply_dlc_amounts(dlcs, HEPHAESTUS["location_amounts"])
    merlin_totals = apply_dlc_amounts(dlcs, MERLIN["location_amounts"])
    dm_totals = apply_dlc_amounts(dlcs, DUNGEON_MASTER["location_amounts"])

    for direction, amount in heph_totals.items():
        slot_lengths[f"{HEPHAESTUS['name']} - {direction.title()}"] = amount
    for direction, amount in merlin_totals.items():
        slot_lengths[f"{MERLIN['name']} - {direction.title()}"] = amount
    for direction, amount in dm_totals.items():
        slot_lengths[f"{DUNGEON_MASTER['name']} - {direction.title()}"] = amount

    return slot_lengths


# ==============================
# All Locations (full list)
# ==============================

def get_all_locations() -> List[LocationDict]:
    """Return all possible locations across all DLCs, modes, shops, lobby NPCs."""
    all_dlcs = DLCS[:]  # ["base", "amplified", "synchrony", "miku"]

    # Zone clears
    zone_locs, all_zone_locs = get_zone_clear_locations(all_dlcs)
    event_locs = get_event_locations(all_dlcs)
    extra_modes = get_extra_mode_clear_locations(all_dlcs, [], EXTRA_MODES["base"] + EXTRA_MODES["amplified"])
    shops = get_shop_locations(all_dlcs)
    lobby_npcs = get_lobby_npc_locations()

    return build_location_dicts(shops + zone_locs + all_zone_locs + event_locs + extra_modes + lobby_npcs)


all_locations = {
    location["name"]: location for location in get_all_locations()
}


def from_id(location_id: int) -> LocationDict:
    matching = [item for item in all_locations.values() if item['code'] == location_id]
    if len(matching) == 0:
        raise ValueError(f"No item data for item id '{location_id}'")
    assert len(matching) < 2, f"Multiple item data with id '{location_id}. Please report."
    return matching[0]


# ==============================
# Available Locations (per world/options)
# ==============================

def get_available_locations(
        dlcs: List[str],
        blacklist: List[str] | None = None,
        goals: List[int] | None = None,
        modes: List[str] | None = None,
        include_lobby_npcs: bool = True
) -> List[LocationDict]:
    """Return only available locations based on params (dlcs, blacklist, modes, lobby NPCs)."""
    dlcs = normalize_dlcs(dlcs)

    # Zone clears
    zone_locs, all_zone_locs = get_zone_clear_locations(dlcs, blacklist)

    # Event Locations
    event_locs = get_event_locations(dlcs, blacklist, goals)

    # Extra modes
    extra_modes = get_extra_mode_clear_locations(dlcs, blacklist, modes)

    # Shops
    shops = get_shop_locations(dlcs)

    # Lobby NPCs
    lobby_npcs = get_lobby_npc_locations() if include_lobby_npcs else []

    names = shops + zone_locs + (all_zone_locs if "All Zones" in goals else []) + event_locs + extra_modes + lobby_npcs

    return [all_locations[location_name] for location_name in names]

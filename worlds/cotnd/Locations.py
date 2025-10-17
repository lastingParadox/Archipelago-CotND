from typing import Dict, List, TypedDict
from BaseClasses import Location
from .Characters import base_chars, amplified_chars, synchrony_chars, miku_chars

base_code = 742_080
shop_location_range = {"start": 742_080, "end": 742_186}


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

def get_zone_clear_locations(dlcs: List[str], blacklist: List[str] | None = None, per_level = True) -> tuple[list[str], list[str]]:
    """Return (zone_clear, all_zone_clear) locations.

        If per_level is True, expands each zone into individual levels (1-1, 1-2, 1-3, Boss).
        Otherwise, just uses "Zone X".
        Handles special boss cases for specific characters.
        """
    dlcs = normalize_dlcs(dlcs)
    chars = get_characters_for_dlcs(dlcs, blacklist)
    amplified = "amplified" in dlcs

    zone_locations: list[str] = []

    for char in chars:
        if per_level:
            for zone in range(1, (6 if amplified else 5)):
                # Add standard levels
                zone_locations.extend([f"{char} - Zone {zone} - Floor {level}" for level in range(1, 4)])

                # Handle boss
                boss_label = f"Zone {zone} - Boss"
                if char == "Dove":
                    # Dove has no final boss
                    continue
                if zone == (4 if not amplified else 5):
                    # Final boss zone → handle special cases
                    if char == "Cadence":
                        zone_locations.append(f"{char} - Dead Ringer")
                        zone_locations.append(f"{char} - NecroDancer")
                        continue
                    elif char == "Melody":
                        zone_locations.append(f"{char} - NecroDancer")
                        continue
                    elif char == "Nocturna":
                        zone_locations.append(f"{char} - Frankensteinway")
                        zone_locations.append(f"{char} - The Conductor")
                        continue
                elif zone == 1 and char == "Aria":
                    zone_locations.append(f"{char} - Golden Lute")
                    continue
                # Default boss
                zone_locations.append(f"{char} - {boss_label}")
        else:
            # Simple Zone X clear
            for zone in range(1, (6 if amplified else 5)):
                zone_locations.append(f"{char} - Zone {zone}")

    # Add All Zones clears
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

LOBBY_NPCS = ["Codex", "Merlin", "Hintmaster", "Janitor", "Diamond Dealer"]


def get_lobby_npc_locations():
    codex_locs = ["Dragon Lore", "Trap Lore", "Bomb Lore", "How to Get Away with Murder"]
    caged_list = [f"Caged {npc}" for npc in LOBBY_NPCS]

    return codex_locs + caged_list


# ==============================
# Shop Locations
# ==============================

def _get_normalized_distribution(dlcs: List[str]) -> Dict[str, int]:
    """Compute normalized slot distribution across all shopkeepers and directions (9 total slots),
       rotating extra slots across shopkeepers. Priority per shopkeeper: center > left > right."""

    dlcs = normalize_dlcs(dlcs)
    shopkeepers = [HEPHAESTUS, MERLIN, DUNGEON_MASTER]

    # Apply DLC totals
    totals = {s["name"]: apply_dlc_amounts(dlcs, s["location_amounts"]) for s in shopkeepers}

    # Total across ALL shopkeepers
    grand_total = sum(sum(slots.values()) for slots in totals.values())

    # Normalize across 9 slots (3 shopkeepers × 3 directions)
    base = grand_total // 9
    remainder = grand_total % 9

    # Start with everyone getting base
    distribution = {f"{s['name']} - {d}": base for s in shopkeepers for d in ["center", "left", "right"]}

    # Build rotated priority order: center first for each shopkeeper in rotation, then left, then right
    directions = ["center", "left", "right"]
    priority_order = []

    # For each direction, rotate shopkeepers
    for direction in directions:
        for i in range(len(shopkeepers)):
            shopkeeper = shopkeepers[i % len(shopkeepers)]["name"]
            priority_order.append(f"{shopkeeper} - {direction}")

    # Hand out leftover slots in rotated order
    for i in range(remainder):
        distribution[priority_order[i % len(priority_order)]] += 1

    return distribution


def get_shop_locations(dlcs: List[str]) -> List[str]:
    """Return all shop location names with normalized slot distribution."""
    distribution = _get_normalized_distribution(dlcs)

    shop_locations = []
    for slot_key, count in distribution.items():
        shopkeeper, direction = slot_key.split(" - ")
        for i in range(1, count + 1):
            shop_locations.append(f"{shopkeeper} - {direction.title()} Shop Item {i}")

    return shop_locations


def get_shop_slot_lengths(dlcs: List[str]) -> Dict[str, int]:
    """Return normalized slot counts for each shop NPC and direction."""
    return _get_normalized_distribution(dlcs)

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

    return build_location_dicts(shops + lobby_npcs + zone_locs + all_zone_locs + event_locs + extra_modes)


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
        include_lobby_npcs: bool = True,
        per_level: bool = True,
) -> List[LocationDict]:
    """Return only available locations based on params (dlcs, blacklist, modes, lobby NPCs)."""
    dlcs = normalize_dlcs(dlcs)

    # Zone clears
    zone_locs, all_zone_locs = get_zone_clear_locations(dlcs, blacklist, per_level)

    # Event Locations
    event_locs = get_event_locations(dlcs, blacklist, goals)

    # Extra modes
    extra_modes = get_extra_mode_clear_locations(dlcs, blacklist, modes)

    # Shops
    shops = get_shop_locations(dlcs)

    # Lobby NPCs
    lobby_npcs = get_lobby_npc_locations() if include_lobby_npcs else []

    names = shops + lobby_npcs + zone_locs + (all_zone_locs if 0 in goals else []) + event_locs + extra_modes

    return [all_locations[location_name] for location_name in names]

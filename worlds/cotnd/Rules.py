from typing import List
from BaseClasses import LocationProgressType, MultiWorld
from worlds.generic.Rules import set_rule

from .Characters import base_chars, amplified_chars, synchrony_chars
from .Locations import (
    all_zones_clear_locations,
    dungeon_master_locations,
    hephaestus_locations,
    merlin_locations,
    zone_clear_locations,
)


def set_rules(world: MultiWorld, player: int, available_chars: List[str]):

    clear_locations = zone_clear_locations + all_zones_clear_locations
    lobby_locations = hephaestus_locations + merlin_locations + dungeon_master_locations

    all_chars = base_chars + amplified_chars + synchrony_chars

    zone_clear_locations_by_character = [
        [location for location in clear_locations if location.startswith(f"{char}")]
        for char in all_chars
    ]

    for char, character_locations in zip(all_chars, zone_clear_locations_by_character):
        for location in character_locations:
            loc = world.get_location(location, player)
            set_rule(
                loc,
                lambda state: state.has(char, player),
            )
            if char not in available_chars:
                loc.progress_type = LocationProgressType.EXCLUDED

    for location in lobby_locations:
        set_rule(world.get_location(location, player), lambda state: True)

    world.completion_condition[player] = (
        lambda state: state.has(f"Complete", player, 8)
    )

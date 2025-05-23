from typing import List
from BaseClasses import LocationProgressType, MultiWorld
from worlds.generic.Rules import set_rule

from .Characters import base_chars, amplified_chars, synchrony_chars


def set_rules(world: MultiWorld, player: int, locations: List[str], available_chars: List[str], dlcs: List[str], all_zones_goal_clear: int):

    all_chars = base_chars

    if "Amplified" in dlcs:
        all_chars += amplified_chars
    if "Synchrony" in dlcs:
        all_chars += synchrony_chars

    zone_clear_locations_by_character = [
        [location for location in locations if location.startswith(f"{char}")]
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

    lobby_locations = [location for location in locations if location.startswith("Hephaestus") or location.startswith("Merlin") or location.startswith("Dungeon Master")]

    for location in lobby_locations:
        set_rule(world.get_location(location, player), lambda state: True)

    world.completion_condition[player] = (
        lambda state: state.has(f"Complete", player, all_zones_goal_clear)
    )

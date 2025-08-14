import re
from typing import List, Dict
from BaseClasses import LocationProgressType, MultiWorld
from worlds.generic.Rules import set_rule, add_rule

from .Characters import base_chars, amplified_chars, synchrony_chars, miku_chars
from .Locations import get_shop_slot_lengths
from .Options import all_chars


def set_soft_shop_rules(world: MultiWorld, player: int, locations: List[str], slot_lengths: Dict[str, int], chars: List[str]):
    shop_pattern = re.compile(r"^(Hephaestus|Merlin|Dungeon Master) - (Left|Center|Right) Shop Item (\d+)$")

    for location in locations:
        match = shop_pattern.match(location)
        if not match:
            continue

        npc, slot, index_str = match.groups()
        index = int(index_str)
        slot_key = f"{npc} - {slot}"
        total_in_slot = slot_lengths.get(slot_key, 1)

        loc = world.get_location(location, player)

        if index == 1:
            set_rule(loc, lambda state: True)
            continue

        depth_ratio = index / total_in_slot
        required_chars = max(1, int(depth_ratio * max(len(chars), 6)))  # Adjust 6 for pacing at most

        set_rule(
            loc,
            lambda state, req=required_chars: sum(
                1 for c in chars if state.has(c, player)
            ) >= req
        )

def set_rules(world: MultiWorld, player: int, locations: List[str], available_chars: List[str], dlcs: List[str],
              all_zones_goal_clear: int):
    all_chars = base_chars[:]

    if "Amplified" in dlcs:
        all_chars += amplified_chars
    if "Synchrony" in dlcs:
        all_chars += synchrony_chars
    if "Miku" in dlcs:
        all_chars += miku_chars

    zone_clear_locations_by_character = [
        [location for location in locations if location.startswith(f"{char}")]
        for char in all_chars
    ]

    for char, character_locations in zip(all_chars, zone_clear_locations_by_character):
        for location in character_locations:
            loc = world.get_location(location, player)

            # Extract mode if present (e.g., "Melody - No Return Mode")
            mode = None
            if " - " in location:
                _, mode_name = location.split(" - ", 1)
                if mode_name.endswith(" Mode"):
                    mode = mode_name

            if mode:
                set_rule(
                    loc,
                    lambda state, c=char, m=mode: state.has(c, player) and state.has(m, player)
                )
            else:
                set_rule(
                    loc,
                    lambda state, c=char: state.has(c, player)
                )

            if char not in available_chars:
                loc.progress_type = LocationProgressType.EXCLUDED

    lobby_locations = [
        location for location in locations if location.startswith(("Hephaestus", "Merlin", "Dungeon Master"))
    ]

    set_soft_shop_rules(world, player, lobby_locations, get_shop_slot_lengths(dlcs), available_chars)

    world.completion_condition[player] = (
        lambda state: state.has("Complete", player, all_zones_goal_clear)
    )
import re
from typing import List, Dict
from BaseClasses import LocationProgressType, MultiWorld
from worlds.generic.Rules import set_rule, add_rule

from .Characters import base_chars, amplified_chars, synchrony_chars, miku_chars
from .Locations import get_shop_slot_lengths


def set_soft_shop_rules(world: MultiWorld, player: int, locations: List[str], slot_lengths: Dict[str, int], chars: List[str]):
    shop_pattern = re.compile(r"^(Hephaestus|Merlin|Dungeon Master) - (Left|Center|Right) Shop Item (\d+)$")

    for location in locations:
        match = shop_pattern.match(location)
        if not match:
            continue

        npc, slot, index_str = match.groups()
        index = int(index_str)

        loc = world.get_location(location, player)

        # Shared global unlock count:
        # Item 1 requires 1 Shop Stock Unlock,
        # Item 2 requires 2 Shop Stock Unlocks, etc.

        if index == 1:
            # First row is free
            continue
        else:
            # Row N requires (N-1) unlocks
            set_rule(
                loc,
                lambda state, req=(index - 1): state.has("Shop Stock Unlock", player, req)
            )

def set_rules(world: MultiWorld, player: int, locations: List[str], available_chars: List[str], dlcs: List[str],
              goal_clear_req: int, locked_lobby_npcs: bool, codex_enabled: bool):
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

    if locked_lobby_npcs:
        merlin_locations = [
            location for location in lobby_locations if location.startswith("Merlin")
        ]

        for location in merlin_locations:
            add_rule(world.get_location(location, player), lambda state: state.has("Merlin", player))

        codex_locations = ["Dragon Lore", "Trap Lore", "Bomb Lore", "How to Get Away with Murder"]

        if codex_enabled:
            for location in codex_locations:
                add_rule(world.get_location(location, player), lambda state: state.has("Codex", player))

    world.completion_condition[player] = (
        lambda state: state.has("Complete", player, goal_clear_req)
    )
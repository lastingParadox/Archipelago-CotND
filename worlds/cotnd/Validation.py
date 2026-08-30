from __future__ import annotations

from typing import TYPE_CHECKING

from worlds.cotnd.Items import ALL_ITEMS, CotNDItemData, ItemType, max_zone, owned_dlc
from worlds.cotnd.Options import CotNDOptions, DeathLinkType
from worlds.cotnd.Utils import DLC, warn

if TYPE_CHECKING:
    from . import CotNDWorld

MIN_SPEEDRUN_MINUTES = 3

STORY_CHARACTERS = {"Cadence", "Melody", "Aria"}
STORY_CHARACTERS_AMPLIFIED = {"Nocturna"}

AMPLIFIED_MODES = {"No Return", "Hard", "Phasing", "Randomizer", "Mystery"}

PRICE_RANGE_PREFIXES = ("random", "filler", "useful", "progression")

# Options validation

def cap_option(options: CotNDOptions, name: str, cap: int) -> None:
    option = getattr(options, name)

    if option.value > cap:
        warn(f"Setting {name.replace('_', ' ')} to {cap} to maintain progression.")
        option.value = cap

def raise_option(options: CotNDOptions, name: str, floor: int) -> None:
    option = getattr(options, name)

    if option.value < floor:
        warn(f"Setting {name.replace('_', ' ')} to {floor} to maintain progression.")
        option.value = floor

def available_characters(dlc: DLC, blacklist: set[str]) -> list[CotNDItemData]:
    # Characters that survive both the DLC filter and the blacklist.
    return [item for item in ALL_ITEMS.items if item.type is ItemType.CHARACTER and item.available_with(dlc) and item.name not in blacklist]

def validate_blacklist(options: CotNDOptions, dlc: DLC) -> set[str]:
    blacklist = set(options.character_blacklist.value)

    if options.goal == "story":
        required = STORY_CHARACTERS | (STORY_CHARACTERS_AMPLIFIED if DLC.AMPLIFIED in dlc else set())

        if blocked := blacklist & required:
            warn(f"Removing {', '.join(sorted(blocked))} from the blacklist; the Story goal requires them.")
            blacklist -= required

    if not available_characters(dlc, blacklist):
        warn("Removing Cadence from the blacklist to maintain progression.")
        blacklist.discard("Cadence")

    options.character_blacklist.value = blacklist
    return blacklist

def validate_modes(options: CotNDOptions, dlc: DLC) -> set[str]:
    modes = set(options.included_extra_modes.value)

    if DLC.AMPLIFIED not in dlc:
        if removed := modes & AMPLIFIED_MODES:
            warn(f"Removed Amplified-only modes (no Amplified DLC enabled): {', '.join(sorted(removed))}")

        modes -= AMPLIFIED_MODES
        options.included_extra_modes.value = list(modes)

    return modes

def validate_starting_zone(options: CotNDOptions, dlc: DLC) -> None:
    zones = max_zone(dlc)

    if options.starting_zone.value > zones:
        warn(f"Setting starting zone to {zones} because Zone 5 requires Amplified DLC.")
        options.starting_zone.value = zones

def validate_death_link_type(options: CotNDOptions, dlc: DLC) -> None:
    if DLC.AMPLIFIED not in dlc and options.death_link_type == "marv":
        warn("Changing DeathLink type from Marv to Tempo because Marv requires Amplified DLC.")
        options.death_link_type.value = DeathLinkType.option_Tempo

def validate_price_ranges(options: CotNDOptions) -> None:
    ranges = options.price_ranges.value
    defaults = type(options.price_ranges).default

    for prefix in PRICE_RANGE_PREFIXES:
        min_key, max_key = f"{prefix}_min", f"{prefix}_max"

        # Keys are optional in the YAML; anything omitted falls back to default.
        min_val = ranges.get(min_key, defaults[min_key])
        max_val = ranges.get(max_key, defaults[max_key])

        if max_val < min_val:
            warn(f"Swapping {min_key} ({min_val}) and {max_key} ({max_val}) to maintain proper bounds.")
            min_val, max_val = max_val, min_val

        ranges[min_key], ranges[max_key] = min_val, max_val

def validate_speedrun_times(options: CotNDOptions) -> None:
    times = options.all_zones_speedrun_times.value
    disabled = [char for char, minutes in times.items() if minutes == 0]
    raised = sorted(char for char, minutes in times.items() if 0 < minutes < MIN_SPEEDRUN_MINUTES)

    # Zero is the other way a user spells "untimed", so fold it into the sentinel.
    for char in disabled:
        times[char] = -1

    if raised:
        warn(f"Raising All Zones speedrun times to {MIN_SPEEDRUN_MINUTES} minutes for "
             f"{', '.join(raised)}; anything shorter is below reasonable clears.")

        for char in raised:
            times[char] = MIN_SPEEDRUN_MINUTES

def validate_starting_character(world: CotNDWorld, dlc: DLC, blacklist: set[str]) -> None:
    option = world.options.starting_character
    chosen = option.current_option_name
    characters = sorted(character.name for character in available_characters(dlc, blacklist))

    if chosen in characters:
        return

    fallback = world.random.choice(characters)
    warn(f"Setting Starting Character to {fallback} as {chosen} is not in the item pool.")
    option.value = option.options[fallback.lower().replace(" ", "_")]

def validate_goal_amounts(options: CotNDOptions, dlc: DLC, character_count: int) -> None:
    # A goal cannot ask for more shards than the pool will ever hold.
    if options.goal == "golden_lute_shards":
        raise_option(options, "lute_shards_in_pool", options.golden_lute_shards_goal_clear.value)

    cap_option(options, "all_zones_goal_clear", character_count)
    cap_option(options, "zones_goal_clear", character_count * max_zone(dlc))

def validate_options(world: CotNDWorld) -> None:
    options = world.options
    dlc = owned_dlc(world)

    blacklist = validate_blacklist(options, dlc)
    validate_modes(options, dlc)
    validate_death_link_type(options, dlc)
    validate_starting_zone(options, dlc)
    validate_starting_character(world, dlc, blacklist)
    validate_price_ranges(options)
    validate_speedrun_times(options)
    validate_goal_amounts(options, dlc, len(available_characters(dlc, blacklist)))

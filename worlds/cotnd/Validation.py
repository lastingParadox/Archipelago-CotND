from typing import List

from .Characters import get_available_characters
from .Items import get_starting_pool, CotNDItemData, ItemType, DefaultType
from .Utils import character_requirements


def ensure_min_max(options, min_name: str, max_name: str) -> None:
    min_val = getattr(options, min_name).value
    max_val = getattr(options, max_name).value

    if max_val < min_val:
        print(
            f"[WARNING] Swapping {min_name} ({min_val}) and {max_name} ({max_val}) to maintain proper bounds."
        )
        setattr(options, min_name, type(getattr(options, min_name))(max_val))
        setattr(options, max_name, type(getattr(options, max_name))(min_val))


def validate_blacklist(options, dlcs) -> set[str]:
    blacklist = set(options.character_blacklist.value)
    all_chars = get_available_characters(blacklist, dlcs)
    if len(all_chars) == 0:
        print("[WARNING] Removing Cadence from the blacklist to maintain progression.")
        blacklist.discard("Cadence")
        options.character_blacklist.value = list(blacklist)
    return blacklist


def validate_modes(options, dlcs) -> set[str]:
    included_modes = set(options.included_extra_modes.value)

    if "amplified" not in dlcs:
        amplified_modes = {"No Return", "Hard", "Phasing", "Randomizer", "Mystery"}
        removed = included_modes & amplified_modes
        included_modes -= amplified_modes
        if removed:
            print(
                f"[WARNING] Removed Amplified-only modes (no Amplified DLC enabled): {', '.join(sorted(removed))}"
            )
        options.included_extra_modes.value = list(included_modes)

    return included_modes


def cap_option(options, option_name: str, cap: int):
    option = getattr(options, option_name)
    if option.value > cap:
        print(
            f"[WARNING] Setting {option_name.replace('_', ' ')} to {cap} to maintain progression."
        )
        option.value = cap


def validate_price_ranges(options):
    for prefix in ("randomized", "filler", "useful", "progression"):
        ensure_min_max(options, f"{prefix}_price_min", f"{prefix}_price_max")


def validate_starting_zone(options, dlcs):
    if "amplified" not in dlcs and options.starting_zone.value == 5:
        print(
            "[WARNING] Setting starting zone to 4 because Zone 5 requires Amplified DLC."
        )
        options.starting_zone.value = 4


def validate_death_link_type(options, dlcs):
    if "amplified" not in dlcs and options.death_link_type.value == 2:  # 2 is Marv
        print(
            "[WARNING] Changing DeathLink type from Marv to Tempo because Marv requires Amplified DLC."
        )
        options.death_link_type.value = 1  # 1 is Tempo


def validate_starting_character(world, character_option, items: List[CotNDItemData]):
    characters = [item for item in items if item.type is ItemType.CHARACTER]

    for character in characters:
        if character.name == character_option:
            return character

    # Fallback: pick a random valid character
    new_character = world.random.choice(characters)
    print(
        f"[WARNING] Setting Starting Character to {new_character.name} as {character_option} is not in the item pool."
    )
    return new_character


def collect_starting_pool(world, items_list, starting_inventory, include_materials):
    # When materials are disabled, precollect them all (unlocking all weapons from the start)
    # and remove them from the item pool so they aren't placed in the world.
    if not include_materials:
        for item in items_list:
            if item.type is ItemType.MATERIAL:
                world.multiworld.push_precollected(world.create_item(item.name))
        items_list = [item for item in items_list if item.type is not ItemType.MATERIAL]

    starting_pool = get_starting_pool(
        world.random, items_list, starting_inventory
    )

    # Push to collect
    for item in starting_pool:
        world.multiworld.push_precollected(world.create_item(item.name))

    # Remove pre-collected items from item pool
    remaining_items = items_list.copy()
    for item in starting_pool:
        remaining_items.remove(item)

    return remaining_items


def collect_starting_character(
    world, items_list, starting_character, character_unlocks
):
    character = validate_starting_character(world, starting_character, items_list)

    # Precollect the character itself
    world.multiworld.push_precollected(world.create_item(character.name))

    # Collect items to remove and precollect required items
    items_to_remove = {character.name}  # Track names to remove

    if character_unlocks != 0:
        for requirement in character_requirements.get(character.name, set()):
            if any(item.name == requirement for item in items_list):
                world.multiworld.push_precollected(world.create_item(requirement))
                items_to_remove.add(requirement)

    # Return items not marked for removal, preserving duplicates by name
    remaining_items = [item for item in items_list if item.name not in items_to_remove]
    return remaining_items, character.name

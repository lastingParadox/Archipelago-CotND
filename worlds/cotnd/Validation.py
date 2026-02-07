from typing import List

from .Characters import get_available_characters
from .Items import get_starting_pool, CotNDItemData, ItemType
from .Utils import character_requirements


def ensure_min_max(options, min_name: str, max_name: str) -> None:
    min_val = getattr(options, min_name).value
    max_val = getattr(options, max_name).value

    if max_val < min_val:
        print(f"[WARNING] Swapping {min_name} ({min_val}) and {max_name} ({max_val}) to maintain proper bounds.")
        setattr(options, min_name, type(getattr(options, min_name))(max_val))
        setattr(options, max_name, type(getattr(options, max_name))(min_val))

def validate_blacklist(options, dlcs):
    blacklist = set(options.character_blacklist.value)
    all_chars = get_available_characters(blacklist, dlcs)
    if len(all_chars) == 0:
        print("[WARNING] Removing Cadence from the blacklist to maintain progression.")
        blacklist = [c for c in blacklist if c != "Cadence"]
        options.character_blacklist.value = blacklist
    return blacklist


def validate_modes(options, dlcs):
    included_modes = list(options.included_extra_modes.value)

    if "amplified" not in dlcs:
        amplified_modes = {"No Return", "Hard", "Phasing", "Randomizer", "Mystery"}
        before = set(included_modes)
        included_modes = [mode for mode in included_modes if mode not in amplified_modes]
        removed = before - set(included_modes)
        if removed:
            print(f"[WARNING] Removed Amplified-only modes (no Amplified DLC enabled): {', '.join(removed)}")
        options.included_extra_modes.value = included_modes

    return included_modes


def cap_option(options, option_name: str, cap: int):
    option = getattr(options, option_name)
    if option.value > cap:
        print(f"[WARNING] Setting {option_name.replace('_', ' ')} to {cap} to maintain progression.")
        option.value = cap


def validate_price_ranges(options):
    for prefix in ("randomized", "filler", "useful", "progression"):
        ensure_min_max(options, f"{prefix}_price_min", f"{prefix}_price_max")

def validate_starting_character(world, character_option, items: List[CotNDItemData]):
    characters = [item for item in items if item.type is ItemType.CHARACTER]

    for character in characters:
        if character.name == character_option:
            return character

    # Fallback: pick a random valid character
    new_character = world.random.choice(characters)
    print(f"[WARNING] Setting Starting Character to {new_character.name} as {character_option} is not in the item pool.")
    return new_character


def collect_starting_pool(world, items_list, starting_inventory, include_materials):
    starting_pool = get_starting_pool(
        world.random,
        items_list,
        starting_inventory,
        include_materials
    )

    # Push to collect
    for item in starting_pool:
        world.multiworld.push_precollected(world.create_item(item.name))

    # Remove pre-collected items from item pool
    remaining_items = items_list.copy()
    for item in starting_pool:
        remaining_items.remove(item)

    return remaining_items

def collect_starting_character(world, items_list, starting_character, character_unlocks):
    character = validate_starting_character(world, starting_character, items_list)

    # Precollect the character itself
    world.multiworld.push_precollected(world.create_item(character.name))

    # Index items by name
    items_by_name = {item.name: item for item in items_list}

    # Remove the character from the pool
    items_by_name.pop(character.name, None)

    # Precollect required starting items for this character if logic requires it
    if character_unlocks != 0:
        for requirement in character_requirements.get(character.name, set()):
            if requirement in items_by_name:
                world.multiworld.push_precollected(
                    world.create_item(requirement)
                )
                del items_by_name[requirement]

    # Return remaining items
    return list(items_by_name.values())

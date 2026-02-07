from typing import Set

from worlds.cotnd.Items import ItemType, all_items
from worlds.cotnd.Utils import normalize_dlc, DLC


def get_available_characters(character_blacklist: Set[str] = None, dlc: Set[str] = None):
    if character_blacklist is None:
        character_blacklist = []

    dlc_enums = normalize_dlc(dlc)
    items_list = all_items.copy()

    characters = []

    for item in items_list:
        if item.type != ItemType.CHARACTER:
            continue
        if item.dlc is not DLC.BASE and item.dlc not in dlc_enums:
            continue
        if item.name in character_blacklist:
            continue

        characters.append(item)

    return characters


all_chars = [char.name for char in get_available_characters(None, {"Amplified", "Synchrony", "Miku", "Shovel Knight"})]

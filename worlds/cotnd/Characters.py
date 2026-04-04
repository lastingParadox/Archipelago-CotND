from typing import Optional, Set

from worlds.cotnd.Items import ItemType, all_items, CotNDItemData
from worlds.cotnd.Utils import normalize_dlc, DLC


def get_available_characters(
    character_blacklist: Optional[Set[str]] = None,
    dlc: Optional[Set[str]] = None,
) -> list[CotNDItemData]:
    if character_blacklist is None:
        character_blacklist = set()
    if dlc is None:
        dlc = set()

    dlc_enums = normalize_dlc(dlc)
    items_list = all_items.copy()

    characters: list[CotNDItemData] = []

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

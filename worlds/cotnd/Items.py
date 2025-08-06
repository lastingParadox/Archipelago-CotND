import csv
from importlib.resources import files
from typing import List, TypedDict

from BaseClasses import Item, ItemClassification
from worlds.cotnd.Options import (
    DLC,
    RandomizeCharacters,
)
from . import data

base_code = 247_080

class CotNDItem(Item):
    name: str = "Crypt of the NecroDancer"

class ItemDict(TypedDict):
    name: str
    classification: ItemClassification
    type: str
    cotnd_id: str
    dlc: str
    isDefault: bool
    code: int

def load_item_csv(file_path: str = "items.csv") -> List[ItemDict]:
    items: List[ItemDict] = []
    with files(data).joinpath(file_path).open() as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            classification = {
                "Progression": ItemClassification.progression,
                "Useful": ItemClassification.useful,
                "Filler": ItemClassification.filler,
            }.get(row["Item Classification"], ItemClassification.useful)

            item: ItemDict = {
                "name": row["Display Name"],
                "classification": classification,
                "type": row["Type"],
                "cotnd_id": row["Necrodancer ID"],
                "dlc": row["DLC"],
                "isDefault": row["Default"].lower() == "true",
                "code": 0
            }
            items.append(item)
    return items


def get_default_items(
    dlc: DLC, randomize_characters: RandomizeCharacters
) -> List[ItemDict]:
    items = load_item_csv()
    return [
        item
        for item in items
        if item["isDefault"] == True
        and not (randomize_characters and item["type"] == "Character")
        and (item["dlc"] == "Base" or item["dlc"] in dlc)
    ]


def get_filler_items():
    return load_item_csv("ap_items.csv")

def get_items_list(character_blacklist: List[str], dlc: List[str],
                   randomize_characters: int, randomize_starting_items: int, game_modes: List[str]):
    # Base item list with all items
    filtered_items = load_item_csv() + load_item_csv("game_modes.csv")

    # Map blacklisted characters to be Filler
    for item in filtered_items:
        if item["name"] in character_blacklist:
            item["classification"] = ItemClassification.filler

    # Remove items from DLC not included in options
    filtered_items = list(
        filter(
            lambda item: item["dlc"] == "Base" or item["dlc"] in dlc,
            filtered_items,
        )
    )

    # Remove game modes from run not included in options
    filtered_items = list(
        filter(
            lambda item: item["type"] != "Mode" or item["name"].removesuffix(" Mode") in game_modes,
            filtered_items,
        )
    )

    # Remove all default characters if randomize_characters is False
    if not randomize_characters:
        filtered_items = list(
            filter(
                lambda item: item["type"] != "Character" or not item["isDefault"],
                filtered_items,
            )
        )

    # Remove default items if randomize_starting is False
    if not randomize_starting_items:
        filtered_items = list(
            filter(lambda item: item["type"] == "Character" or item["isDefault"] == False, filtered_items)
        )

    return filtered_items

def get_all_items():
    raw_items = load_item_csv() + load_item_csv("game_modes.csv") + load_item_csv("ap_items.csv")

    for index, item in enumerate(raw_items):
        item["code"] = base_code + index

    return raw_items

def from_id(item_id: int) -> ItemDict:
    matching = [item for item in all_items.values() if item['code'] == item_id]
    if len(matching) == 0:
        raise ValueError(f"No item data for item id '{item_id}'")
    assert len(matching) < 2, f"Multiple item data with id '{item_id}. Please report."
    return matching[0]

all_items = {
    item["name"]: item for item in get_all_items()
}
import csv
from importlib.resources import files
from typing import List, TypedDict

from BaseClasses import Item, ItemClassification
from worlds.cotnd.Options import (
    DLC,
    CotNDOptions,
    RandomizeCharacters,
)

from . import data


class CotNDItem(Item):
    name: str = "Crypt of the Necrodancer"


class ItemDict(TypedDict):
    name: str
    classification: ItemClassification
    type: str
    cotnd_id: str
    dlc: str
    isDefault: bool


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


def get_items_list(options: CotNDOptions) -> List[ItemDict]:
    # Base item list with all items
    filtered_items = load_item_csv()

    # Map blacklisted characters to be Filler
    for item in filtered_items:
        if item["name"] in options.character_blacklist:
            item["classification"] = ItemClassification.filler

    # Remove items from DLC not included in options
    filtered_items = list(
        filter(
            lambda item: item["dlc"] == "Base" or item["dlc"] in options.dlc.value,
            filtered_items,
        )
    )

    # Remove all default characters if randomize_characters is False
    if not options.randomize_characters.value:
        filtered_items = list(
            filter(
                lambda item: item["type"] != "Character" or not item["isDefault"],
                filtered_items,
            )
        )

    # Remove default items if randomize_starting is False
    if not options.randomize_starting_items.value:
        filtered_items = list(
            filter(lambda item: item["type"] == "Character" or item["isDefault"] == False, filtered_items)
        )

    return filtered_items + get_filler_items()


def get_all_items():
    return load_item_csv() + load_item_csv("ap_items.csv")

import csv
from collections import defaultdict
from importlib.resources import files
from typing import List, TypedDict

from BaseClasses import Item, ItemClassification
from worlds.cotnd.Options import (
    DLC,
)
from . import data

base_code = 247_080

PLURALS = {
    "Weapon": "Weapons",
    "Armor": "Armors",
    "Head": "Heads",
    "Feet": "Feet",
    "Shield": "Shields",
    "Spell": "Spells",
    "Scroll": "Scrolls",
    "Tome": "Tomes",
    "Food": "Foods",
    "Charm": "Charms",
    "Heart": "Hearts",
    "Familiar": "Familiars",
    "Storage": "Storages",
    "Misc": "Misc",
    "Torch": "Torches",
    "Shovel": "Shovels",
    "Ring": "Rings",
    "Character": "Characters",
    "Mode": "Modes",
}


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


def char_to_cotnd_id(character: str) -> str:
    match character:
        case "Klarinetta":
            return "Sync_Klarinetta"
        case "Suzu":
            return "Sync_Suzu"
        case "Chaunter":
            return "Sync_Chaunter"
        case "Miku":
            return "Coldsteel_Coldsteel"
        case _:
            return character


def cotnd_id_to_char(cotnd_id: str) -> str:
    match cotnd_id:
        case "Sync_Klarinetta":
            return "Klarinetta"
        case "Sync_Suzu":
            return "Suzu"
        case "Sync_Chaunter":
            return "Chaunter"
        case "Coldsteel_Coldsteel":
            return "Miku"
        case _:
            return cotnd_id


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
        dlc: DLC
) -> List[ItemDict]:
    items = load_item_csv()
    return [
        item
        for item in items
        if item["isDefault"] == True
           and not item["type"] == "Character"
           and (item["dlc"] == "Base" or item["dlc"] in dlc)
    ]


def get_filler_items():
    return load_item_csv("ap_items.csv")

def get_all_npc_items():
    items = load_item_csv("lobby_npcs.csv")
    return [item for item in items]

def get_items_list(character_blacklist: List[str], dlc: List[str], game_modes: List[str], npc_items: bool):
    # Base item list with all items
    filtered_items = load_item_csv() + load_item_csv("game_modes.csv") + load_item_csv("lobby_npcs.csv")

    # Remove blacklisted characters from item list
    filtered_items = list(
        filter(
            lambda item: item["name"] not in character_blacklist,
            filtered_items
        )
    )
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

    # Remove lobby npcs from run if items not included in options
    if not npc_items:
        filtered_items = list(
            filter(
                lambda item: item["type"] != "NPC", filtered_items
            )
        )

    # Remove default items
    filtered_items = list(
        filter(lambda item: item["type"] == "Character" or item["isDefault"] == False, filtered_items)
    )

    return filtered_items


def get_all_items():
    raw_items = load_item_csv() + load_item_csv("game_modes.csv") + load_item_csv("lobby_npcs.csv") + load_item_csv(
        "ap_items.csv")

    for index, item in enumerate(raw_items):
        item["code"] = base_code + index

    return raw_items


def from_id(item_id: int) -> ItemDict:
    matching = [item for item in all_items.values() if item['code'] == item_id]
    if len(matching) == 0:
        raise ValueError(f"No item data for item id '{item_id}'")
    assert len(matching) < 2, f"Multiple item data with id '{item_id}. Please report."
    return matching[0]


def pluralize(word: str) -> str:
    return PLURALS.get(word, word + "s")


def make_item_groups() -> dict[str, set[str]]:
    groups: dict[str, set[str]] = defaultdict(set)

    for file in ["items.csv", "game_modes.csv"]:
        for row in load_item_csv(file):
            type_name = row["type"].strip()
            group_name = pluralize(type_name)
            groups[group_name].add(row["name"].strip())

    return dict(groups)


all_items = {
    item["name"]: item for item in get_all_items()
}

item_name_groups = make_item_groups()

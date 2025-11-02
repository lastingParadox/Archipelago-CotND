from typing import List, Set
from .Items import ItemDict

base_chars = [
    "Cadence",
    "Melody",
    "Aria",
    "Eli",
    "Bolt",
    "Dove",
    "Bard",
    "Monk",
    "Reaper",
    "Dorian",
    "Coda"
]

amplified_chars = ["Nocturna", "Diamond", "Mary", "Tempo"]

synchrony_chars = ["Chaunter", "Klarinetta", "Suzu"]

miku_chars = ["Miku"]

shovel_knight_chars = ["Shovel Knight"]


def get_all_characters(dlcs: Set[str]):
    all_chars = base_chars.copy()
    if "Amplified" in dlcs:
        all_chars += amplified_chars
    if "Synchrony" in dlcs:
        all_chars += synchrony_chars
    if "Miku" in dlcs:
        all_chars += miku_chars
    if "Shovel Knight" in dlcs:
        all_chars += shovel_knight_chars

    return all_chars


def get_available_characters(items_list: List[ItemDict], dlcs: Set[str], blacklist: Set[str]):
    all_chars = get_all_characters(dlcs)

    return [
        item for item in items_list
        if item["type"] == "Character" and item["name"] in all_chars and item["name"] not in blacklist
    ]

all_chars = base_chars + amplified_chars + synchrony_chars + miku_chars
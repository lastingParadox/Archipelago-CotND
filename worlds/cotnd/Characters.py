from .Options import CotNDOptions
from typing import List
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
amplified_chars = [ "Nocturna", "Diamond", "Mary", "Tempo" ]
synchrony_chars = [ "Chaunter", "Klarinetta", "Suzu" ]

def get_available_characters(items_list: List[ItemDict], options: CotNDOptions):
    return [item for item in items_list if item["type"] == "Character" and item["name"] not in options.character_blacklist.value]
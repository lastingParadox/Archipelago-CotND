from dataclasses import dataclass
from Options import (
    DeathLinkMixin,
    PerGameCommonOptions,
    Toggle,
    DefaultOnToggle,
    Range,
    OptionList,
)

all_chars = [
    "Cadence",
    "Melody",
    "Aria",
    "Nocturna",
    "Eli",
    "Bolt",
    "Diamond",
    "Chaunter",
    "Dove",
    "Bard",
    "Mary",
    "Suzu",
    "Monk",
    "Reaper",
    "Tempo",
    "Dorian",
    "Coda",
    "Klarinetta"
]

class DLC(OptionList):
    """Which DLCs to include content from. Amplified includes four new characters, a new zone, and new items. Synchrony includes three new characters and new items."""

    display_name = "DLCs"
    valid_keys = ["Amplified", "Synchrony"]
    default = ["Amplified", "Synchrony"]


class CharacterBlacklist(OptionList):
    """Which characters to exclude from progression."""

    display_name = "Character Blacklist"
    valid_keys = frozenset(all_chars)
    default = ["Coda"]


class RandomizeCharacters(DefaultOnToggle):
    """Whether to include characters in the randomization. Note: If disabled, 8 characters will be unlocked at the start of the run."""

    display_name = "Randomize Characters"


class AllZonesGoalClear(Range):
    """Determines how many character completions are required for the All Zones goal. Default is 8."""

    display_name = "Characters Required for All Zones"
    range_start = 1
    range_end = 18
    default = 8


class RandomizeStartingItems(Toggle):
    """Whether to include base items, or items not unlocked by default, in progression."""

    display_name = "Randomize Starting Items"


@dataclass
class CotNDOptions(DeathLinkMixin, PerGameCommonOptions):
    dlc: DLC
    character_blacklist: CharacterBlacklist
    randomize_starting_items: RandomizeStartingItems
    randomize_characters: RandomizeCharacters
    all_zones_goal_clear: AllZonesGoalClear

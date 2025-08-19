from dataclasses import dataclass
from Options import (
    DeathLinkMixin,
    PerGameCommonOptions,
    Range,
    OptionList, Choice,
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
    "Klarinetta",
    "Miku"
]

all_game_modes = [
    "No Return",
    "Hard",
    "Phasing",
    "Randomizer",
    "Mystery",
    "No Beat",
    "Double Tempo",
    "Low Percent"
]


class DLC(OptionList):
    """Which DLCs to include content from.
    Options include: Amplified, Synchrony, Miku"""

    display_name = "DLCs"
    valid_keys = ["Amplified", "Synchrony", "Miku"]
    default = ["Amplified", "Synchrony"]


class StartingCharactersAmount(Range):
    """How many characters to start the game with. Minimum is 1, maximum is 19. Default is 3.
    Note: If this value exceeds the number of characters in the pool, then this value will equal that number."""

    display_name = "Starting Characters Amount"
    range_start = 1
    range_end = 19
    default = 3


class CharacterBlacklist(OptionList):
    """Which characters to include in checks and progression. Note that this will disable the character from the run entirely if excluded.
    Options include: Cadence, Melody, Aria, Nocturna, Eli, Bolt, Diamond, Chaunter, Dove, Bard, Mary, Suzu, Monk, Reaper, Tempo, Dorian, Coda, Klarinetta, Miku
    Note: If this list consists of all available characters, then Cadence will be removed from the blacklist to prevent progression issues."""

    display_name = "Character Blacklist"
    valid_keys = frozenset(all_chars)
    default = ["Coda"]


class AllZonesGoalClear(Range):
    """Determines how many character completions are required for the All Zones goal. Default is 6.
    Note: If this value exceeds the number of characters in the pool, then this value will equal that number."""

    display_name = "Characters Required for All Zones"
    range_start = 1
    range_end = 19
    default = 6


class IncludedExtraModes(OptionList):
    """Which game modes to include in checks. Note that this will disable the mode from the run entirely if excluded.
    Options include: No Return, Hard, Phasing, Randomizer, Mystery, No Beat, Double Tempo, and Low Percent."""

    display_name = "Included Extra Modes"
    valid_keys = frozenset(all_game_modes)
    default = []


class PriceRandomization(Choice):
    """How to randomize diamond prices in the Archipelago lobby.
    Vanilla: CotND item prices remain at their vanilla price values. All AP and non-CotND item prices will be randomized according to their item classification (Filler, Useful, Progression).
    Vanilla_Rand: CotND item prices remain at their vanilla price values. All AP and non-CotND item prices will be randomized completely.
    Item_Class: All item prices will be randomized according to their item classification (Filler, Useful, Progression).
    Complete: All item prices will be randomized completely.
    """

    display_name = "Price Randomization"
    option_Vanilla = 0
    option_Vanilla_Rand = 1
    option_Item_Class = 2
    option_Complete = 3
    default = 0


class RandomizedPriceMin(Range):
    """Determines the minimum diamond price range for items in the AP Lobby. This option will only be applied if either Price Randomization is set to Vanilla_Rand or Complete."""

    display_name = "Randomized Price Minimum"
    range_start = 1
    range_end = 100
    default = 1


class RandomizedPriceMax(Range):
    """Determines the maximum diamond price range for items in the AP Lobby. This option will only be applied if either Price Randomization is set to Vanilla_Rand or Complete."""

    display_name = "Randomized Price Maximum"
    range_start = 1
    range_end = 100
    default = 10


class FillerPriceMin(Range):
    """Determines the minimum diamond price range for a Filler item in the AP Lobby. This option will only be applied if either Price Randomization is set to Vanilla or Item_Class."""

    display_name = "Filler Item Price Minimum"
    range_start = 1
    range_end = 100
    default = 1


class FillerPriceMax(Range):
    """Determines the maximum diamond price range for a Filler item in the AP Lobby. This option will only be applied if either Price Randomization is set to Vanilla or Item_Class."""

    display_name = "Filler Item Price Maximum"
    range_start = 1
    range_end = 100
    default = 4


class UsefulPriceMin(Range):
    """Determines the minimum diamond price range for a Useful item in the AP Lobby. This option will only be applied if either Price Randomization is set to Vanilla or Item_Class."""

    display_name = "Useful Item Price Minimum"
    range_start = 1
    range_end = 100
    default = 2


class UsefulPriceMax(Range):
    """Determines the maximum diamond price range for a Useful item in the AP Lobby. This option will only be applied if either Price Randomization is set to Vanilla or Item_Class."""

    display_name = "Useful Item Price Maximum"
    range_start = 1
    range_end = 100
    default = 8


class ProgressionPriceMin(Range):
    """Determines the minimum diamond price range for a Progression item in the AP Lobby. This option will only be applied if either Price Randomization is set to Vanilla or Item_Class."""

    display_name = "Progression Item Price Minimum"
    range_start = 1
    range_end = 100
    default = 4


class ProgressionPriceMax(Range):
    """Determines the maximum diamond price range for a Progression item in the AP Lobby. This option will only be applied if either Price Randomization is set to Vanilla or Item_Class."""

    display_name = "Progression Item Price Maximum"
    range_start = 1
    range_end = 100
    default = 10


@dataclass
class CotNDOptions(DeathLinkMixin, PerGameCommonOptions):
    dlc: DLC
    starting_characters_amount: StartingCharactersAmount
    character_blacklist: CharacterBlacklist
    all_zones_goal_clear: AllZonesGoalClear
    included_extra_modes: IncludedExtraModes
    price_randomization: PriceRandomization
    randomized_price_min: RandomizedPriceMin
    randomized_price_max: RandomizedPriceMax
    filler_price_min: FillerPriceMin
    filler_price_max: FillerPriceMax
    useful_price_min: UsefulPriceMin
    useful_price_max: UsefulPriceMax
    progression_price_min: ProgressionPriceMin
    progression_price_max: ProgressionPriceMax

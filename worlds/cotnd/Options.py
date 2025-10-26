from dataclasses import dataclass
from Options import (
    DeathLinkMixin,
    PerGameCommonOptions,
    Range,
    OptionList, Choice, OptionGroup, DefaultOnToggle, Toggle, OptionCounter,
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

class Goal(Choice):
    """What goal to set for the Crypt of the NecroDancer multiworld.
    All_Zones: Clear ALl Zones mode with X amount of characters, where X is the value put for "All Zones Goal Clear". Recommended for experienced players, as this can be challenging.
    Zones: Clear X amount of zones, where X is the value put for "Zones Goal Clear". Will disable "All Zones" checks. Recommended for a quicker and less challenging experience.
    """
    display_name = "Goal"
    option_All_Zones = 0
    option_Zones = 1
    default = 0


class AllZonesGoalClear(Range):
    """Determines how many character completions are required for the All Zones goal. Default is 6.
    Note: If this value exceeds the number of characters in the pool, then this value will equal that number."""

    display_name = "Characters Required for All Zones Goal"
    range_start = 1
    range_end = 19
    default = 6


class ZonesGoalClear(Range):
    """Determines how many separate zone completions are required for the Zones goal. Default is 30.
    Note: If this value exceeds the number of zones in the pool, then this value will equal that number."""

    display_name = "Amount required for Zones Goal"
    range_start = 1
    range_end = 95
    default = 30


class PerLevelZoneClears(DefaultOnToggle):
    """Determines whether zone clear checks are split per level (e.g., 1-1, 1-2, 1-3, Boss)
    instead of just a single 'Zone X' check. Default is false.

    Special final boss cases apply for certain characters (Cadence, Melody, Aria, Nocturna)."""

    display_name = "Per-Level Zone Clears"


class DLC(OptionList):
    """Which DLCs to include content from in progression and checks.
    Options include: Amplified, Synchrony, Miku
    Note: Excluding the Synchrony DLC does not mean that you can play this APWorld without the Synchrony DLC. This is only to exclude content from the Synchrony DLC in the multiworld.
    Note: Excluding the Amplified DLC will remove Zone 5 from progression altogether."""

    display_name = "DLCs"
    valid_keys = ["Amplified", "Synchrony", "Miku"]
    default = ["Amplified", "Synchrony"]


class StartingCharactersAmount(Range):
    """How many characters to start the game with. Minimum is 1, maximum is 19. Default is 2.
    Note: If this value exceeds the number of characters in the pool, then this value will equal that number."""

    display_name = "Starting Characters Amount"
    range_start = 1
    range_end = 19
    default = 2


class CharacterBlacklist(OptionList):
    """Which characters to exclude from checks and progression. Note that this will disable the character from the run entirely if included.
    Options include: Cadence, Melody, Aria, Nocturna, Eli, Bolt, Diamond, Chaunter, Dove, Bard, Mary, Suzu, Monk, Reaper, Tempo, Dorian, Coda, Klarinetta, Miku
    Note: If this list consists of all available characters, then Cadence will be removed from the blacklist to prevent progression issues."""

    display_name = "Character Blacklist"
    valid_keys = frozenset(all_chars)
    default = ["Coda"]


class IncludedExtraModes(OptionList):
    """Which game modes to include in checks. Note that this will disable the mode from the run entirely if excluded.
    Options include: No Return (Amplified), Hard (Amplified), Phasing (Amplified), Randomizer (Amplified), Mystery (Amplified), No Beat, Double Tempo, and Low Percent.
    Note: If you do not have the Amplified DLC enabled, the modes that require it will be disabled."""

    display_name = "Included Extra Modes"
    valid_keys = frozenset(all_game_modes)
    default = []

class IncludeCodexChecks(DefaultOnToggle):
    """Determines whether Codex location checks (Bomb Lore, How to Get Away with Murder, etc.) will be included in progression. Default is true."""

    display_name = "Include Codex Checks"

class LockedLobbyNPCs(DefaultOnToggle):
    """Determines whether the lobby NPCs will be locked and will need to be saved in a run to unlock them in the lobby. Default is true."""

    display_name = "Locked Lobby NPCs"

class LobbyNPCItems(Toggle):
    """Determines whether lobby NPC unlocks will be randomized. Saving the lobby NPC will return a randomized item instead. Default is false.
    Note: If Locked Lobby NPCs is false, this will be disabled."""

    display_name = "Lobby NPC Items"

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

class TrapPercentage(Range):
    """
    Replaces filler items with traps, at the specified rate.
    """
    display_name = "Trap Percentage"
    range_start = 0
    range_end = 100
    default = 20

_default_trap_weights = {
    "Camera Trap": 2,
    "Confusion Trap": 7,
    "Dad Trap": 2,
    "Dead Ringer Trap": 1,
    "Gold Scatter Trap": 6,
    "Haunted Shopkeeper Trap": 4,
    "Monkey Trap": 10,
    "No Return Trap": 3,
    "Skeleton Trap": 5,
    "Tempo Trap": 7
}

class TrapWeights(OptionCounter):
    """
    Specify the weights determining how many copies of each trap item will be in your itempool.
    If you don't want a specific type of trap, you can set the weight for it to 0.
    If you set all trap weights to 0, you will get no traps, bypassing the "Trap Percentage" option.
    """
    display_name = "Trap Weights"
    valid_keys = _default_trap_weights.keys()

    min = 0

    default = _default_trap_weights

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
    goal: Goal
    all_zones_goal_clear: AllZonesGoalClear
    zones_goal_clear: ZonesGoalClear
    per_level_zone_clears: PerLevelZoneClears
    dlc: DLC
    starting_characters_amount: StartingCharactersAmount
    character_blacklist: CharacterBlacklist
    included_extra_modes: IncludedExtraModes
    include_codex_checks: IncludeCodexChecks
    locked_lobby_npcs: LockedLobbyNPCs
    lobby_npc_items: LobbyNPCItems
    trap_percentage: TrapPercentage
    trap_weights: TrapWeights
    price_randomization: PriceRandomization
    randomized_price_min: RandomizedPriceMin
    randomized_price_max: RandomizedPriceMax
    filler_price_min: FillerPriceMin
    filler_price_max: FillerPriceMax
    useful_price_min: UsefulPriceMin
    useful_price_max: UsefulPriceMax
    progression_price_min: ProgressionPriceMin
    progression_price_max: ProgressionPriceMax

option_groups = [
    OptionGroup("Goal Options", [
        Goal,
        AllZonesGoalClear,
        ZonesGoalClear,
        PerLevelZoneClears
    ]),
    OptionGroup("Trap Options", [
        TrapPercentage,
        TrapWeights
    ]),
    OptionGroup("Pricing Options", [
        PriceRandomization,
        RandomizedPriceMin,
        RandomizedPriceMax,
        FillerPriceMin,
        FillerPriceMax,
        UsefulPriceMin,
        UsefulPriceMax,
        ProgressionPriceMin,
        ProgressionPriceMax
    ])
]
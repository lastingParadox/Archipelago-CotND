from dataclasses import dataclass
from Options import (
    DeathLinkMixin,
    PerGameCommonOptions,
    Range,
    OptionList,
    Choice,
    OptionGroup,
    DefaultOnToggle,
    Toggle,
    OptionCounter,
    OptionSet,
    NamedRange,
)
from worlds.cotnd.Characters import all_chars

all_game_modes = [
    "No Return",
    "Hard",
    "Phasing",
    "Randomizer",
    "Mystery",
    "No Beat",
    "Double Tempo",
    "Low Percent",
]


# Goal Options
class Goal(Choice):
    """What goal to set for the Crypt of the NecroDancer multiworld.
    All_Zones: Clear ALl Zones mode with X amount of characters, where X is the value put for "All Zones Goal Clear". Recommended for experienced players, as this can be challenging.
    Zones: Clear X amount of zones, where X is the value put for "Zones Goal Clear". Will disable "All Zones" checks. Recommended for a quicker and less challenging experience.
    """

    display_name = "Goal"
    option_All_Zones = 0
    option_Zones = 1
    default = 1


class AllZonesGoalClear(Range):
    """Determines how many character completions are required for the All Zones goal. Default is 6.
    Note: If this value exceeds the number of characters in the pool, then this value will equal that number.
    """

    display_name = "Characters Required for All Zones Goal"
    range_start = 1
    range_end = 20
    default = 8


class ZonesGoalClear(Range):
    """Determines how many separate zone completions are required for the Zones goal. Default is 30.
    Note: If this value exceeds the number of zones in the pool, then this value will equal that number.
    """

    display_name = "Amount required for Zones Goal"
    range_start = 1
    range_end = 95
    default = 40


class FloorClearChecks(DefaultOnToggle):
    """Determines whether zone clear checks are split per floor (e.g., 1-1, 1-2, 1-3, Boss) instead of just a single 'Zone X' check. Default is true."""

    display_name = "Floor Clear Checks"
    aliases = ["per_level_zone_clears"]


# Content Options
class DLC(OptionSet):
    """Which DLCs to include content from in progression and checks.
    Options include: Amplified, Synchrony, Miku, Shovel Knight
    Note: Excluding the Synchrony DLC does not mean that you can play this APWorld without the Synchrony DLC. This is only to exclude content from the Synchrony DLC in the multiworld.
    Note: Excluding the Amplified DLC will remove Zone 5 from progression altogether."""

    display_name = "DLCs"
    valid_keys = ["Amplified", "Synchrony", "Miku", "Shovel Knight"]
    default = ["Synchrony"]


class IncludedExtraModes(OptionList):
    """Which game modes to include in checks. Note that this will disable the mode from the run entirely if excluded.
    Options include: No Return (Amplified), Hard (Amplified), Phasing (Amplified), Randomizer (Amplified), Mystery (Amplified), No Beat, Double Tempo, and Low Percent.
    Note: If you do not have the Amplified DLC enabled, the modes that require it will be disabled.
    """

    display_name = "Included Extra Modes"
    valid_keys = frozenset(all_game_modes)
    default = []


class IncludeCodexChecks(DefaultOnToggle):
    """Determines whether Tutorial levels (Bomb Lore, How to Get Away with Murder, etc.) will be included in progression.Default is true."""

    display_name = "Include Codex Checks"


class LobbyNPCItems(Toggle):
    """Determines whether lobby NPC unlocks will be randomized. Saving the lobby NPC will return a randomized item instead of unlocking their room."""

    display_name = "Lobby NPC Items"


class IncludeMaterials(Toggle):
    """Whether to include weapon materials/shapes in the multiworld and in level generation. Default is false.
    If set to true, weapons will only spawn with their base material until you unlock the associated material item.
    """

    display_name = "Include Materials"


# Starting Inventory
class StartingInventory(NamedRange):
    """Percentage of starting items granted at world start. Unique items are included if enabled.
    If Character Unlocks is not Item_Only, required items for the starting character are always included.
    Default is 50.

    Presets:
    Vanilla (100): All starting items, like a fresh save.
    Reduced (50): Half of all starting items.
    Minimum (0): Only mandatory items (Dagger, Apple, Shovel)."""

    range_start = 0
    range_end = 100
    special_range_names = {"vanilla": 100, "reduced": 50, "minimum": 0}
    default = 50


# Zone Access
class ZoneAccessKeys(Choice):
    """Controls whether zones are locked behind Zone Access Key items.
    Disabled: Zones have no access requirements.
    Separate: Each zone has its own distinct access key shuffled into the pool. The Starting Zone is freely accessible from the start; all other zones require their unique key.
    Progressive: A single Progressive Zone Access item is used. Each copy found unlocks the next zone in sequence (Zone 1 requires 0, Zone 2 requires 1, etc.).
    Default is Disabled."""

    display_name = "Zone Access Keys"
    option_disabled = 0
    option_separate = 1
    option_progressive = 2
    default = 0


class StartingZone(Choice):
    """When Zone Access Keys are Separate or Progressive, sets the starting accessible zone.
    Separate: The starting zone requires no key; all other zones need their unique key.
    Progressive: Starting Zone minus one Progressive Zone Access items are precollected, granting immediate access to all zones up to and including the starting zone.
    Zone 5 is only valid with Amplified enabled, otherwise pre-generation validation forces Zone 4.
    Has no effect when Zone Access Keys is Disabled. Default is Zone 1."""

    display_name = "Starting Zone"
    option_zone_1 = 1
    option_zone_2 = 2
    option_zone_3 = 3
    option_zone_4 = 4
    option_zone_5 = 5
    default = 1


# Character Options
class StartingCharacter(Choice):
    """Which character to start the game with. Default is Cadence.
    Note: If a selected starting character is not in the item pool, this option will change to a random character available in the item pool.
        The following characters will be removed from the item pool unless their respective DLCs are enabled
        - Amplified: Nocturna, Diamond, Mary, Tempo
        - Synchrony: Klarinetta, Chaunter, Suzu
        - Miku: Hatsune Miku
        - Shovel Knight: Shovel Knight"""

    display_name = "Starting Character"
    option_Cadence = 0
    option_Melody = 1
    option_Aria = 2
    option_Dorian = 3
    option_Eli = 4
    option_Monk = 5
    option_Dove = 6
    option_Coda = 7
    option_Bolt = 8
    option_Bard = 9
    option_Nocturna = 10
    option_Diamond = 11
    option_Mary = 12
    option_Tempo = 13
    option_Reaper = 14
    option_Klarinetta = 15
    option_Chaunter = 16
    option_Suzu = 17
    option_Hatsune_Miku = 18
    option_Shovel_Knight = 19
    default = 0


class CharacterBlacklist(OptionSet):
    """Which characters to exclude from checks and progression. Note that this will disable the character from the run entirely if included.
    Options include: Cadence, Melody, Aria, Nocturna, Eli, Bolt, Diamond, Chaunter, Dove, Bard, Mary, Suzu, Monk, Reaper, Tempo, Dorian, Coda, Klarinetta, Hatsune Miku, Shovel Knight
    Note: If this list consists of all available characters, then Cadence will be removed from the blacklist to prevent progression issues.
    """

    display_name = "Character Blacklist"
    valid_keys = frozenset(all_chars)
    default = ["Coda", "Bolt"]


class CharacterUnlocks(Choice):
    """How characters should be unlocked in the multiworld. All options will require a character item at the very minimum. Default is Item_Only.
    Item_Only: Only the character item is required to unlock a character.
    Required_Items_Soft: The character item (and unique items if enabled) unlocks in-game access to a character. Logic still requires the character's required items.
    Required_Items_Hard: The character item and all required items (and unique item if Include Unique Equipment is enabled) must be received before in-game access to a character is granted.
    """

    display_name = "Character Unlocks"
    option_Item_Only = 0
    option_Required_Items_Soft = 1
    option_Required_Items_Hard = 2
    default = 0


class IncludeUniqueEquipment(Toggle):
    """Whether to include character-specific equipment in the multiworld and in level generation. Default is false.
    If set to true and Character Unlocks is set to either Required_Items_Soft or Required_Items_Hard, the characters who have unique items will require them.
    """

    display_name = "Include Unique Equipment"


class LockCharacterRoom(Toggle):
    """When enabled, a Character Room Key item must be received before you can switch away from your starting character.
    This creates an early-game chokepoint, restricting all runs to your starting character until the key is found.
    Default is false."""

    display_name = "Lock Character Room"


# Trap Options
class TrapPercentage(Range):
    """
    Replaces filler items with traps, at the specified rate.
    Default is 20.
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
    "Tempo Trap": 7,
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


# Pricing Options
class PriceRandomization(Choice):
    """How to randomize diamond prices in the Archipelago lobby.
    Vanilla: CotND item prices remain at their vanilla price values. All AP and non-CotND item prices will be randomized according to their item classification (Filler, Useful, Progression).
    Vanilla_Rand: CotND item prices remain at their vanilla price values. All AP and non-CotND item prices will be randomized completely.
    Item_Class: All item prices will be randomized according to their item classification (Filler, Useful, Progression).
    Complete: All item prices will be randomized completely.
    Default is Vanilla.
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
    goal: Goal
    all_zones_goal_clear: AllZonesGoalClear
    zones_goal_clear: ZonesGoalClear
    floor_clear_checks: FloorClearChecks
    dlc: DLC
    starting_inventory: StartingInventory
    starting_character: StartingCharacter
    character_blacklist: CharacterBlacklist
    character_unlocks: CharacterUnlocks
    include_unique_items: IncludeUniqueEquipment
    include_materials: IncludeMaterials
    included_extra_modes: IncludedExtraModes
    include_codex_checks: IncludeCodexChecks
    lobby_npc_items: LobbyNPCItems
    zone_access_keys: ZoneAccessKeys
    starting_zone: StartingZone
    lock_character_room: LockCharacterRoom
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
    OptionGroup(
        "Goal Options",
        [
            Goal,
            AllZonesGoalClear,
            ZonesGoalClear,
            FloorClearChecks,
        ],
    ),
    OptionGroup(
        "Content Options",
        [
            DLC,
            IncludedExtraModes,
            IncludeCodexChecks,
            LobbyNPCItems,
            IncludeMaterials,
        ],
    ),
    OptionGroup(
        "Starting Inventory",
        [
            StartingInventory,
        ],
    ),
    OptionGroup(
        "Zone Access",
        [
            ZoneAccessKeys,
            StartingZone,
        ],
    ),
    OptionGroup(
        "Character Options",
        [
            StartingCharacter,
            CharacterBlacklist,
            CharacterUnlocks,
            IncludeUniqueEquipment,
            LockCharacterRoom,
        ],
    ),
    OptionGroup("Trap Options", [TrapPercentage, TrapWeights]),
    OptionGroup(
        "Pricing Options",
        [
            PriceRandomization,
            RandomizedPriceMin,
            RandomizedPriceMax,
            FillerPriceMin,
            FillerPriceMax,
            UsefulPriceMin,
            UsefulPriceMax,
            ProgressionPriceMin,
            ProgressionPriceMax,
        ],
    ),
]

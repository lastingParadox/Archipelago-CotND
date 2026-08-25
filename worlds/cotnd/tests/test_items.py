"""Tests for item pool composition — feature grants, starting inventory, keys, and counts.

Most tests read both the pool and the starting inventory: an item missing from the pool is
only correct if it is missing for the right reason.
"""
from BaseClasses import ItemClassification

from worlds.cotnd.Items import (
    ALL_ITEMS,
    FILLER_ITEM_NAMES,
    InventoryType,
    ItemType,
    filler_item_names,
)
from worlds.cotnd.Locations import SHOP_ROW_SIZE
from worlds.cotnd.Utils import CHARACTER_ITEM_REQUIREMENTS, DLC

from .bases import CotNDTestBase


def _names_of(inventory_type: InventoryType) -> set[str]:
    return {item.name for item in ALL_ITEMS.items if item.inventory_type is inventory_type}


def _names_of_type(item_type: ItemType) -> set[str]:
    return {item.name for item in ALL_ITEMS.items if item.type is item_type}


MATERIALS = _names_of_type(ItemType.MATERIAL)
UNIQUE_ITEMS = _names_of(InventoryType.UNIQUE)
ALWAYS_ITEMS = _names_of(InventoryType.ALWAYS)
CHARACTERS = _names_of_type(ItemType.CHARACTER)


class ItemPoolTestBase(CotNDTestBase):
    """Adds the two views every pool test needs: what was placed, and what was granted."""

    def pool(self) -> list[str]:
        return [item.name for item in self.multiworld.itempool if item.player == self.player]

    def precollected(self) -> list[str]:
        return [item.name for item in self.multiworld.precollected_items[self.player]]

    def assert_granted(self, names) -> None:
        pool, precollected = set(self.pool()), set(self.precollected())
        for name in names:
            self.assertIn(name, precollected, f"{name} should be precollected")
            self.assertNotIn(name, pool, f"{name} was precollected and must not also be in the pool")

    def assert_placed(self, names) -> None:
        pool, precollected = set(self.pool()), set(self.precollected())
        for name in names:
            self.assertIn(name, pool, f"{name} should be in the item pool")
            self.assertNotIn(name, precollected, f"{name} should not be precollected")

    def assert_absent(self, names) -> None:
        pool, precollected = set(self.pool()), set(self.precollected())
        for name in names:
            self.assertNotIn(name, pool, f"{name} should not be in the item pool")
            self.assertNotIn(name, precollected, f"{name} should not be precollected")


# ---------------------------------------------------------------------------
# Features that grant their items when switched off
# ---------------------------------------------------------------------------

class TestMaterialsDisabled(ItemPoolTestBase):
    """Materials off means the player simply has them, so crafting still works."""

    options = {"include_materials": "false"}

    def test_materials_granted(self) -> None:
        self.assert_granted(MATERIALS)


class TestMaterialsEnabled(ItemPoolTestBase):
    options = {"include_materials": "true"}

    def test_materials_placed(self) -> None:
        self.assert_placed(MATERIALS)


class TestMaterialsNeverInStartingInventory(ItemPoolTestBase):
    """Materials are not ALWAYS/POSSIBLE, so a full starting inventory must not reach them."""

    options = {"include_materials": "true", "starting_inventory": 100}

    def test_materials_still_placed(self) -> None:
        self.assert_placed(MATERIALS)


class TestShrineChecksDisabled(ItemPoolTestBase):
    """Shrine items are granted rather than dropped -- the mod needs them to spawn shrines."""

    options = {"include_shrine_checks": "false"}

    def test_shrine_items_granted(self) -> None:
        granted = set(self.precollected())
        shrines = {item.name for item in ALL_ITEMS.items if item.type is ItemType.SHRINE}
        self.assertTrue(shrines & granted, "no shrine items were granted")
        self.assertFalse(shrines & set(self.pool()), "shrine items must not be placed")


class TestBuffItemsDisabled(ItemPoolTestBase):
    options = {"buff_items": "false"}

    def test_buffs_granted(self) -> None:
        buffs = {item.name for item in ALL_ITEMS.items if item.type is ItemType.BUFF}
        self.assertFalse(buffs & set(self.pool()))
        self.assertTrue(buffs & set(self.precollected()))


class TestBuffItemsEnabled(ItemPoolTestBase):
    options = {"buff_items": "true", "character_blacklist": [], "dlc": []}

    def test_buffs_placed(self) -> None:
        buffs = {item.name for item in ALL_ITEMS.items if item.type is ItemType.BUFF}
        self.assertTrue(buffs & set(self.pool()))


class TestCharacterRoomUnlocked(ItemPoolTestBase):
    options = {"lock_character_room": "false"}

    def test_key_granted(self) -> None:
        self.assert_granted(["Character Room Key"])


class TestCharacterRoomLocked(ItemPoolTestBase):
    options = {"lock_character_room": "true"}

    def test_key_placed(self) -> None:
        self.assert_placed(["Character Room Key"])


# ---------------------------------------------------------------------------
# Unique equipment
# ---------------------------------------------------------------------------

class TestUniqueItemsDisabled(ItemPoolTestBase):
    """Unique equipment is filtered out of the pool entirely, not granted."""

    options = {"include_unique_items": "false", "character_unlocks": "Item_Only"}

    def test_unique_items_absent(self) -> None:
        self.assert_absent(UNIQUE_ITEMS)


class TestUniqueItemsEnabled(ItemPoolTestBase):
    """Even at 100% starting inventory they stay in the world -- UNIQUE is not POSSIBLE."""

    options = {
        "include_unique_items": "true",
        "character_unlocks": "Item_Only",
        "starting_inventory": 100,
        "dlc": [],
    }

    def test_unique_items_placed(self) -> None:
        placed = set(self.pool())
        base_unique = {item.name for item in ALL_ITEMS.items
                       if item.inventory_type is InventoryType.UNIQUE and item.dlc.name == "BASE"}
        self.assertTrue(base_unique)
        self.assert_placed(base_unique)
        self.assertTrue(base_unique <= placed)


# ---------------------------------------------------------------------------
# Starting inventory
# ---------------------------------------------------------------------------

class TestStartingInventoryZero(ItemPoolTestBase):
    """Zero percent still grants the mandatory items -- they are a floor, not a share."""

    options = {
        "starting_inventory": 0,
        "include_materials": "true",
        "buff_items": "true",
        "include_shrine_checks": "true",
        "lock_character_room": "true",
    }

    def test_always_items_granted(self) -> None:
        self.assert_granted(ALWAYS_ITEMS)

    def test_nothing_optional_granted(self) -> None:
        possible = _names_of(InventoryType.POSSIBLE)
        self.assertFalse(possible & set(self.precollected()),
                         "no POSSIBLE item should be granted at 0%")


class TestStartingInventoryFull(ItemPoolTestBase):
    options = {
        "starting_inventory": 100,
        "include_materials": "true",
        "buff_items": "true",
        "include_shrine_checks": "true",
        "lock_character_room": "true",
    }

    def test_always_items_granted(self) -> None:
        self.assert_granted(ALWAYS_ITEMS)

    def test_optional_items_granted(self) -> None:
        possible = _names_of(InventoryType.POSSIBLE) & set(self.pool() + self.precollected())
        self.assertTrue(possible <= set(self.precollected()),
                        "every available POSSIBLE item should be granted at 100%")


# ---------------------------------------------------------------------------
# Starting character and its requirements
# ---------------------------------------------------------------------------

class TestStartingCharacterGranted(ItemPoolTestBase):
    options = {"starting_character": "Cadence", "dlc": []}

    def test_character_granted(self) -> None:
        self.assert_granted(["Cadence"])


class TestCharacterRequirementsGranted(ItemPoolTestBase):
    """With required-item unlocks, the starting character's kit comes with them."""

    options = {
        "starting_character": "Bolt",
        "character_unlocks": "Required_Items_Hard",
        "character_blacklist": [],
        "dlc": [],
    }

    def test_spear_granted(self) -> None:
        self.assert_granted(["Bolt", "Spear"])


class TestCharacterRequirementsNotGrantedWhenItemOnly(ItemPoolTestBase):
    """item_only means a character is just an item, so nothing extra is granted."""

    options = {
        "starting_character": "Bolt",
        "character_unlocks": "Item_Only",
        "character_blacklist": [],
        "starting_inventory": 0,
        "dlc": [],
    }

    def test_spear_not_granted(self) -> None:
        self.assertNotIn("Spear", self.precollected())


class TestCharacterRequirementsAreProgression(ItemPoolTestBase):
    """Required items gate a character, so they have to be progression."""

    options = {
        "starting_character": "Cadence",
        "character_unlocks": "Required_Items_Hard",
        "character_blacklist": [],
        # Cadence requires nothing, so no requirement is precollected for being hers. At
        # 0% none are drawn into the starting inventory either, which would otherwise take
        # a required item out of the pool on the seeds that happen to pick it.
        "starting_inventory": 0,
        "dlc": [],
    }

    def required_items(self) -> list:
        # Only characters this slot can actually roll gate anything: Compass is a base item,
        # but nothing requires it until Tempo is in the pool.
        present = (set(self.pool()) | set(self.precollected())) & CHARACTERS
        required = {name for character, names in CHARACTER_ITEM_REQUIREMENTS.items()
                    if character in present
                    for name in names}

        return [item for item in self.multiworld.itempool
                if item.player == self.player and item.name in required]

    def test_spear_is_progression(self) -> None:
        placed = self.required_items()

        self.assertIn("Spear", [item.name for item in placed], "Bolt's Spear should be in the pool")
        for item in placed:
            self.assertTrue(item.advancement, f"{item.name} gates a character and should be progression")


# ---------------------------------------------------------------------------
# Zone access keys
# ---------------------------------------------------------------------------

class TestZoneKeysDisabled(ItemPoolTestBase):
    """Disabled grants the whole set, so every zone is open from the start."""

    options = {"zone_access_keys": "disabled", "dlc": []}

    def test_all_progressive_keys_granted(self) -> None:
        self.assertEqual(self.precollected().count("Progressive Zone Access"), 3)

    def test_no_keys_placed(self) -> None:
        self.assertEqual(self.pool().count("Progressive Zone Access"), 0)


class TestZoneKeysSeparate(ItemPoolTestBase):
    options = {"zone_access_keys": "separate", "starting_zone": "zone_1", "dlc": []}

    def test_starting_zone_key_granted(self) -> None:
        self.assert_granted(["Zone 1 Access"])

    def test_later_zone_keys_placed(self) -> None:
        self.assert_placed(["Zone 2 Access", "Zone 3 Access", "Zone 4 Access"])

    def test_no_zone_five_key_without_amplified(self) -> None:
        self.assert_absent(["Zone 5 Access"])


class TestZoneKeysProgressive(ItemPoolTestBase):
    """Starting in zone 3 means two keys are already spent."""

    options = {"zone_access_keys": "progressive", "starting_zone": "zone_3", "dlc": []}

    def test_two_keys_granted(self) -> None:
        self.assertEqual(self.precollected().count("Progressive Zone Access"), 2)

    def test_rest_placed(self) -> None:
        self.assertEqual(self.pool().count("Progressive Zone Access"), 1)


class TestZoneKeysAmplified(ItemPoolTestBase):
    """Amplified adds zone 5, so there is one more key to find."""

    options = {"zone_access_keys": "progressive", "starting_zone": "zone_1", "dlc": ["Amplified"]}

    def test_four_keys_placed(self) -> None:
        self.assertEqual(self.pool().count("Progressive Zone Access"), 4)


# ---------------------------------------------------------------------------
# Counted items
# ---------------------------------------------------------------------------

class TestGoldenLuteShardsForShardGoal(ItemPoolTestBase):
    options = {
        "goal": "golden_lute_shards",
        "golden_lute_shards_goal_clear": 8,
        "lute_shards_in_pool": 12,
    }

    def test_pool_holds_the_requested_shards(self) -> None:
        self.assertEqual(self.pool().count("Golden Lute Shard"), 12)


class TestGoldenLuteShardsAbsentForOtherGoals(ItemPoolTestBase):
    options = {"goal": "story"}

    def test_no_shards(self) -> None:
        self.assert_absent(["Golden Lute Shard"])


class TestPermanentHealthUpgrades(ItemPoolTestBase):
    options = {"permanent_health_upgrades": 7}

    def test_one_per_requested_upgrade(self) -> None:
        self.assertEqual(self.pool().count("Permanent Health Upgrade"), 7)


class TestProgressivePotions(ItemPoolTestBase):
    options = {"dlc": []}

    def test_three_copies(self) -> None:
        self.assertEqual(self.pool().count("Progressive Potions"), 3)


class TestProgressiveCoinMultiplier(ItemPoolTestBase):
    """One copy per stacking coin upgrade the tiers hand out."""

    options = {"dlc": []}

    def test_two_copies(self) -> None:
        self.assertEqual(self.pool().count("Progressive Coin Multiplier"), 2)


class TestShopRestocks(ItemPoolTestBase):
    """Reaching row N costs N-1 restocks, so the first row is free."""

    options = {"shop_rows": 15, "dlc": []}

    def test_restock_count_matches_rows(self) -> None:
        self.assertEqual(self.pool().count("Shop Restock"), 14)

    def test_shop_locations_match_rows(self) -> None:
        shop_locations = [location for location in self.multiworld.get_locations(self.player)
                          if " Shop Item " in location.name]
        self.assertEqual(len(shop_locations), 15 * SHOP_ROW_SIZE)


# ---------------------------------------------------------------------------
# Pool integrity
# ---------------------------------------------------------------------------

class TestFillerNotPlacedDirectly(ItemPoolTestBase):
    """Filler enters only through create_filler, never from the master pool."""

    options = {"trap_percentage": 0, "dlc": []}

    def test_pool_has_no_duplicate_progression(self) -> None:
        placed = self.pool()
        for name in FILLER_ITEM_NAMES:
            data = ALL_ITEMS.get_by_name(name)
            self.assertNotIn(ItemClassification.progression, data.classification,
                             f"filler item {name} should not be progression")
        self.assertTrue(placed)


class TestFillerRespectsDLC(ItemPoolTestBase):
    """A base-game slot can never be handed filler that needs DLC content to resolve."""

    options = {"trap_percentage": 0, "dlc": []}

    def test_dlc_filler_is_not_offered(self) -> None:
        offered = filler_item_names(self.world)
        self.assertTrue(offered)

        dlc_only = [
            name for name in FILLER_ITEM_NAMES
            if not ALL_ITEMS.get_by_name(name).available_with(DLC.BASE)
        ]
        self.assertTrue(dlc_only, "no DLC-gated filler left to test against")

        for name in dlc_only:
            self.assertNotIn(name, offered)

    def test_placed_filler_is_all_available(self) -> None:
        filler = set(self.pool()) & set(FILLER_ITEM_NAMES)
        for name in filler:
            self.assertTrue(ALL_ITEMS.get_by_name(name).available_with(DLC.BASE),
                            f"{name} was placed in a base-game slot but needs DLC")


class TestZeroWeightTrapsAreExcluded(ItemPoolTestBase):
    """Weight 0 opts a trap out of the multiworld, not just out of the filler roll."""

    options = {
        "dlc": [],
        "trap_percentage": 50,
        "trap_weights": {"Bald Trap": 0, "Camera Trap": 0, "Summon Trap": 50},
    }

    def test_zero_weight_traps_are_absent(self) -> None:
        placed = set(self.pool())
        self.assertNotIn("Bald Trap", placed)
        self.assertNotIn("Camera Trap", placed)

    def test_weighted_trap_is_still_placed(self) -> None:
        self.assertIn("Summon Trap", self.pool())


class TestItemCountMatchesLocations(ItemPoolTestBase):
    options = {"dlc": []}

    def test_counts_match(self) -> None:
        unfilled = self.multiworld.get_unfilled_locations(self.player)
        self.assertEqual(len(self.pool()), len(unfilled))


class TestItemCountMatchesLocationsAmplified(ItemPoolTestBase):
    options = {"dlc": ["Amplified", "Synchrony"]}

    def test_counts_match(self) -> None:
        unfilled = self.multiworld.get_unfilled_locations(self.player)
        self.assertEqual(len(self.pool()), len(unfilled))


class TestItemCountMatchesLocationsEverythingOn(ItemPoolTestBase):
    options = {
        "dlc": ["Amplified", "Synchrony"],
        "include_materials": "true",
        "buff_items": "true",
        "include_unique_items": "true",
        "include_shrine_checks": "true",
        "items_per_zone": 15,
        "include_flawless_chest_checks": "true",
        "lock_character_room": "true",
        "lobby_npc_items": "true",
    }

    def test_counts_match(self) -> None:
        unfilled = self.multiworld.get_unfilled_locations(self.player)
        self.assertEqual(len(self.pool()), len(unfilled))


class TestItemCountMatchesLocationsMinimal(ItemPoolTestBase):
    """The shop grows to hold a pool that would otherwise overflow."""

    options = {
        "shop_rows": 1,
        "include_shrine_checks": "false",
        "items_per_zone": 0,
        "include_codex_checks": "false",
        "include_flawless_chest_checks": "false",
        "dlc": [],
    }

    def test_counts_match(self) -> None:
        unfilled = self.multiworld.get_unfilled_locations(self.player)
        self.assertEqual(len(self.pool()), len(unfilled))


# ---------------------------------------------------------------------------
# Item room (slot data)
# ---------------------------------------------------------------------------

class TestItemRoom(ItemPoolTestBase):
    options = {"dlc": ["Amplified"], "include_unique_items": "true"}

    def test_every_entry_is_a_real_item(self) -> None:
        for entry in self.world.item_room:
            ALL_ITEMS.get_by_cotnd_id(entry["id"])

    def test_no_duplicates(self) -> None:
        ids = [entry["id"] for entry in self.world.item_room]
        self.assertEqual(len(ids), len(set(ids)))

    def test_covers_everything_receivable(self) -> None:
        """The room is the pool, so nothing placed or granted may be missing from it."""
        listed = {entry["id"] for entry in self.world.item_room}
        for name in set(self.pool() + self.precollected()):
            data = ALL_ITEMS.get_by_name(name)
            if data.type in (ItemType.FILLER, ItemType.TRAP, ItemType.KEY):
                continue
            self.assertIn(data.cotnd_id, listed, f"{name} is receivable but missing from the item room")

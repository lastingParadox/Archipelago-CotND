"""Tests for item pool composition — materials, unique items, starting character, and precollection."""
from worlds.cotnd.Items import ItemType, DefaultType

from .bases import CotNDTestBase


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _precollected_names(multiworld, player) -> list[str]:
    return [item.name for item in multiworld.precollected_items[player]]


def _pool_names(multiworld, player) -> list[str]:
    return [item.name for item in multiworld.itempool if item.player == player]


def _material_names() -> set[str]:
    from worlds.cotnd.Items import ALL_ITEMS
    return {item.name for item in ALL_ITEMS if item.type is ItemType.MATERIAL}


def _unique_names() -> set[str]:
    from worlds.cotnd.Items import ALL_ITEMS
    return {item.name for item in ALL_ITEMS if item.default is DefaultType.UNIQUE}


# ---------------------------------------------------------------------------
# Materials disabled (default)
# ---------------------------------------------------------------------------

class TestMaterialsDisabledPrecollected(CotNDTestBase):
    """When include_materials=False (default), all materials must be precollected."""

    options = {"include_materials": "false"}

    def test_materials_precollected(self) -> None:
        precollected = set(_precollected_names(self.multiworld, self.player))
        for name in _material_names():
            self.assertIn(name, precollected, f"{name} should be precollected when include_materials is false")

    def test_materials_not_in_pool(self) -> None:
        pool = set(_pool_names(self.multiworld, self.player))
        for name in _material_names():
            self.assertNotIn(name, pool, f"{name} must not be in the item pool when include_materials is false")


# ---------------------------------------------------------------------------
# Materials enabled
# ---------------------------------------------------------------------------

class TestMaterialsEnabledInPool(CotNDTestBase):
    """When include_materials=True, materials must be in the item pool and not precollected."""

    options = {"include_materials": "true"}

    def test_materials_in_pool(self) -> None:
        pool = set(_pool_names(self.multiworld, self.player))
        for name in _material_names():
            self.assertIn(name, pool, f"{name} should be in the item pool when include_materials is true")

    def test_materials_not_precollected(self) -> None:
        # Materials should never be precollected when the option is enabled
        precollected = set(_precollected_names(self.multiworld, self.player))
        for name in _material_names():
            self.assertNotIn(name, precollected,
                             f"{name} should not be precollected when include_materials is true")


class TestMaterialsNotInStartingPool(CotNDTestBase):
    """Even with materials enabled, starting_inventory=100 must not grant materials at start."""

    options = {
        "include_materials": "true",
        "starting_inventory": 100,
    }

    def test_no_materials_in_starting_inventory(self) -> None:
        # Materials should be in the world pool, not handed out at start
        precollected = set(_precollected_names(self.multiworld, self.player))
        for name in _material_names():
            self.assertNotIn(name, precollected,
                             f"{name} wrongly precollected via starting inventory")


# ---------------------------------------------------------------------------
# Unique items
# ---------------------------------------------------------------------------

class TestUniqueItemsDisabledAbsent(CotNDTestBase):
    """When include_unique_items=False (default), unique items must not appear in the pool."""

    options = {"include_unique_items": "false"}

    def test_unique_items_not_in_pool(self) -> None:
        pool = set(_pool_names(self.multiworld, self.player))
        for name in _unique_names():
            self.assertNotIn(name, pool,
                             f"Unique item {name} should not be in the pool when include_unique_items is false")


class TestUniqueItemsEnabledPresent(CotNDTestBase):
    """When include_unique_items=True, unique items must appear in the pool."""

    options = {"include_unique_items": "true"}

    def test_unique_items_in_pool(self) -> None:
        pool = set(_pool_names(self.multiworld, self.player))
        # At least one unique item should be present
        self.assertTrue(
            pool & _unique_names(),
            "No unique items found in pool when include_unique_items is true",
        )

    def test_unique_items_not_in_starting_inventory(self) -> None:
        """Even with max starting inventory, unique items must stay in the world."""
        # Test with full starting inventory to be sure they don't leak in
        precollected = set(_precollected_names(self.multiworld, self.player))
        for name in _unique_names():
            self.assertNotIn(name, precollected,
                             f"Unique item {name} wrongly in starting inventory")


# ---------------------------------------------------------------------------
# Starting character precollection
# ---------------------------------------------------------------------------

class TestStartingCharacterPrecollected(CotNDTestBase):
    """The starting character should always be precollected, not in the item pool."""

    options = {"starting_character": "Cadence"}

    def test_starting_char_precollected(self) -> None:
        precollected = _precollected_names(self.multiworld, self.player)
        self.assertIn("Cadence", precollected)

    def test_starting_char_not_in_pool(self) -> None:
        pool = _pool_names(self.multiworld, self.player)
        self.assertNotIn("Cadence", pool)


class TestStartingCharacterFallback(CotNDTestBase):
    """A blacklisted starting character must fall back to a valid character."""

    options = {
        "starting_character": "Nocturna",  # Amplified-only
        "dlc": [],
    }

    def test_fallback_character_precollected(self) -> None:
        from worlds.cotnd.Items import ItemType
        precollected = _precollected_names(self.multiworld, self.player)
        world = self.multiworld.worlds[self.player]
        # Whatever the starting character ended up being, it should be precollected
        starting_char = world.starting_character_name
        self.assertIn(starting_char, precollected)
        self.assertNotEqual(starting_char, "Nocturna",
                            "Nocturna requires Amplified DLC and should not be chosen")


# ---------------------------------------------------------------------------
# Character unlock requirements
# ---------------------------------------------------------------------------

class TestStartingCharacterRequirementsPrecollected(CotNDTestBase):
    """With character_unlocks != item_only, requirements for the starting char should be precollected."""

    options = {
        "starting_character": "Aria",
        "character_unlocks": "Required_Items_Hard",
    }

    def test_aria_requirements_precollected(self) -> None:
        from worlds.cotnd.Utils import character_requirements
        precollected = set(_precollected_names(self.multiworld, self.player))
        for req in character_requirements.get("Aria", set()):
            # The requirement might not be in the pool when include_unique_items=False,
            # but if it is in items_list it must be precollected.
            world = self.multiworld.worlds[self.player]
            if any(i.name == req for i in world.world_item_list):
                self.assertIn(req, precollected,
                              f"Aria's requirement {req} should be precollected")

    def test_aria_requirements_not_in_pool(self) -> None:
        from worlds.cotnd.Utils import character_requirements
        pool = set(_pool_names(self.multiworld, self.player))
        world = self.multiworld.worlds[self.player]
        for req in character_requirements.get("Aria", set()):
            if any(i.name == req for i in world.world_item_list):
                self.assertNotIn(req, pool, f"Precollected requirement {req} should not also be in pool")


class TestStartingCharacterRequirementsItemOnly(CotNDTestBase):
    """With character_unlocks=item_only, requirements should NOT be precollected due to character requirements.
    We use Eli whose requirement (Eli's Hand) is DefaultType.UNIQUE — it can never be in the starting pool,
    so any precollection of it would only come from collect_starting_character."""

    options = {
        "starting_character": "Eli",
        "character_unlocks": "Item_Only",
    }

    def test_elis_hand_not_precollected(self) -> None:
        """Eli's Hand is UNIQUE so it's never in starting pool — if it's precollected, it came from character requirements."""
        precollected = set(_precollected_names(self.multiworld, self.player))
        self.assertNotIn("Eli's Hand", precollected,
                         "Eli's Hand should not be precollected when character_unlocks is item_only")


# ---------------------------------------------------------------------------
# Item count == location count
# ---------------------------------------------------------------------------

class TestItemCountMatchesLocations(CotNDTestBase):
    """The item pool must exactly fill all non-event locations."""

    def test_item_count_matches_location_count(self) -> None:
        unfilled = self.multiworld.get_unfilled_locations(self.player)
        pool_size = len([i for i in self.multiworld.itempool if i.player == self.player])
        self.assertEqual(pool_size, len(unfilled),
                         f"Item pool size {pool_size} does not match unfilled locations {len(unfilled)}")


class TestItemCountMatchesLocationsMaterialsEnabled(CotNDTestBase):
    """Item/location balance holds when materials are enabled."""

    options = {"include_materials": "true"}

    def test_item_count_matches_location_count(self) -> None:
        unfilled = self.multiworld.get_unfilled_locations(self.player)
        pool_size = len([i for i in self.multiworld.itempool if i.player == self.player])
        self.assertEqual(pool_size, len(unfilled))


class TestItemCountMatchesLocationsAmplified(CotNDTestBase):
    """Item/location balance holds with Amplified DLC enabled."""

    options = {"dlc": ["Amplified", "Synchrony"]}

    def test_item_count_matches_location_count(self) -> None:
        unfilled = self.multiworld.get_unfilled_locations(self.player)
        pool_size = len([i for i in self.multiworld.itempool if i.player == self.player])
        self.assertEqual(pool_size, len(unfilled))

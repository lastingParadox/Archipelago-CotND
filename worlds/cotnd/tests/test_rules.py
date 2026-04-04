"""Tests for Rules.py — zone access, character requirements, shop rules, and completion condition."""
from BaseClasses import CollectionState
from .bases import CotNDTestBase


# ---------------------------------------------------------------------------
# Zone access keys — disabled (default)
# ---------------------------------------------------------------------------

class TestZoneAccessDisabledNoGating(CotNDTestBase):
    """With zone_access_keys=disabled, dungeon locations have no zone key requirements."""

    options = {
        "zone_access_keys": "disabled",
        "floor_clear_checks": "false",
        "starting_character": "Cadence",
        "character_blacklist": [],
        "dlc": [],
    }

    def test_zone1_accessible_without_keys(self) -> None:
        self.collect_by_name("Cadence")
        self.assertTrue(self.can_reach_location("Cadence - Zone 1"))

    def test_zone4_accessible_without_keys(self) -> None:
        self.collect_by_name("Cadence")
        self.assertTrue(self.can_reach_location("Cadence - Zone 4"))


# ---------------------------------------------------------------------------
# Zone access keys — separate
# ---------------------------------------------------------------------------

class TestSeparateZoneAccessKeys(CotNDTestBase):
    """With separate zone keys, each zone requires its own key item."""

    options = {
        "zone_access_keys": "separate",
        "floor_clear_checks": "false",
        "starting_zone": "zone_1",
        "starting_character": "Cadence",
        "character_blacklist": [],
        "dlc": [],
    }

    def test_zone1_accessible_without_key(self) -> None:
        """Zone 1 is the starting zone — no key needed."""
        self.collect_by_name("Cadence")
        self.assertTrue(self.can_reach_location("Cadence - Zone 1"))

    def test_zone2_inaccessible_without_key(self) -> None:
        self.collect_by_name("Cadence")
        self.assertFalse(self.can_reach_location("Cadence - Zone 2"))

    def test_zone2_accessible_with_key(self) -> None:
        self.collect_by_name(["Cadence", "Zone 2 Access"])
        self.assertTrue(self.can_reach_location("Cadence - Zone 2"))

    def test_zone3_inaccessible_without_key(self) -> None:
        self.collect_by_name(["Cadence", "Zone 2 Access"])
        self.assertFalse(self.can_reach_location("Cadence - Zone 3"))

    def test_zone3_accessible_with_key(self) -> None:
        self.collect_by_name(["Cadence", "Zone 2 Access", "Zone 3 Access"])
        self.assertTrue(self.can_reach_location("Cadence - Zone 3"))

    def test_zone4_accessible_with_all_keys(self) -> None:
        self.collect_by_name(["Cadence", "Zone 2 Access", "Zone 3 Access", "Zone 4 Access"])
        self.assertTrue(self.can_reach_location("Cadence - Zone 4"))


class TestSeparateZoneStartingZone3(CotNDTestBase):
    """Starting zone 3 should make zones 1-3 freely accessible but gate 4."""

    options = {
        "zone_access_keys": "separate",
        "floor_clear_checks": "false",
        "starting_zone": "zone_3",
        "starting_character": "Cadence",
        "character_blacklist": [],
        "dlc": [],
    }

    def test_zone3_accessible_without_key(self) -> None:
        self.collect_by_name("Cadence")
        self.assertTrue(self.can_reach_location("Cadence - Zone 3"))

    def test_zone4_blocked_without_key(self) -> None:
        self.collect_by_name("Cadence")
        self.assertFalse(self.can_reach_location("Cadence - Zone 4"))

    def test_zone1_blocked_without_key(self) -> None:
        self.collect_by_name("Cadence")
        self.assertFalse(self.can_reach_location("Cadence - Zone 1"))

    def test_zone1_accessible_with_key(self) -> None:
        self.collect_by_name(["Cadence", "Zone 1 Access"])
        self.assertTrue(self.can_reach_location("Cadence - Zone 1"))


# ---------------------------------------------------------------------------
# Zone access keys — progressive
# ---------------------------------------------------------------------------

class TestProgressiveZoneAccessKeys(CotNDTestBase):
    """Progressive zone access: N copies unlock zone N+1."""

    options = {
        "zone_access_keys": "progressive",
        "floor_clear_checks": "false",
        "starting_zone": "zone_1",
        "starting_character": "Cadence",
        "character_blacklist": [],
        "dlc": [],
    }

    def test_zone1_accessible_with_zero_keys(self) -> None:
        self.collect_by_name("Cadence")
        self.assertTrue(self.can_reach_location("Cadence - Zone 1"))

    def test_zone2_inaccessible_with_zero_keys(self) -> None:
        self.collect_by_name("Cadence")
        self.assertFalse(self.can_reach_location("Cadence - Zone 2"))

    def test_zone2_accessible_with_one_key(self) -> None:
        self.collect_by_name(["Cadence", "Progressive Zone Access"])
        self.assertTrue(self.can_reach_location("Cadence - Zone 2"))

    def test_zone3_requires_two_keys(self) -> None:
        self.collect_by_name("Cadence")
        pza_items = self.get_items_by_name("Progressive Zone Access")
        self.assertGreaterEqual(len(pza_items), 2, "Need at least 2 Progressive Zone Access items in pool")
        self.multiworld.state.collect(pza_items[0])
        self.assertFalse(self.can_reach_location("Cadence - Zone 3"))

    def test_zone3_accessible_with_two_keys(self) -> None:
        self.collect_by_name(["Cadence", "Progressive Zone Access", "Progressive Zone Access"])
        self.assertTrue(self.can_reach_location("Cadence - Zone 3"))


# ---------------------------------------------------------------------------
# Character room key
# ---------------------------------------------------------------------------

class TestCharacterRoomKeyBlocks(CotNDTestBase):
    """With lock_character_room=True, non-starting character locations should require the key."""

    options = {
        "lock_character_room": "true",
        "floor_clear_checks": "false",
        "starting_character": "Cadence",
        "character_blacklist": [],
        "dlc": [],
        "zone_access_keys": "disabled",
    }

    def test_melody_blocked_without_room_key(self) -> None:
        self.collect_by_name("Melody")
        self.assertFalse(self.can_reach_location("Melody - Zone 1"))

    def test_melody_accessible_with_room_key(self) -> None:
        self.collect_by_name(["Melody", "Character Room Key"])
        self.assertTrue(self.can_reach_location("Melody - Zone 1"))

    def test_starting_character_not_blocked(self) -> None:
        """Starting character locations must not require the room key."""
        self.collect_by_name("Cadence")
        self.assertTrue(self.can_reach_location("Cadence - Zone 1"))


class TestCharacterRoomKeyDisabled(CotNDTestBase):
    """Without lock_character_room, non-starting characters are accessible with only character item."""

    options = {
        "lock_character_room": "false",
        "floor_clear_checks": "false",
        "starting_character": "Cadence",
        "character_blacklist": [],
        "dlc": [],
        "zone_access_keys": "disabled",
    }

    def test_melody_accessible_without_room_key(self) -> None:
        self.collect_by_name("Melody")
        self.assertTrue(self.can_reach_location("Melody - Zone 1"))

    def test_character_room_key_not_in_pool(self) -> None:
        pool_names = [i.name for i in self.multiworld.itempool if i.player == self.player]
        self.assertNotIn("Character Room Key", pool_names)


class TestCharacterRoomKeyInPool(CotNDTestBase):
    """With lock_character_room=True, the Character Room Key must be in the item pool."""

    options = {"lock_character_room": "true"}

    def test_character_room_key_in_pool(self) -> None:
        pool_names = [i.name for i in self.multiworld.itempool if i.player == self.player]
        self.assertIn("Character Room Key", pool_names)


# ---------------------------------------------------------------------------
# Character unlock requirements
# ---------------------------------------------------------------------------

class TestCharacterRequirementsHard(CotNDTestBase):
    """With character_unlocks=Required_Items_Hard, character locations need required items."""

    options = {
        "character_unlocks": "Required_Items_Hard",
        "floor_clear_checks": "false",
        "include_unique_items": "true",
        "starting_character": "Cadence",
        "character_blacklist": [],
        "dlc": [],
        "zone_access_keys": "disabled",
    }

    def _fresh_state(self):
        """Return an empty CollectionState, unaffected by precollected starting inventory."""
        return CollectionState(self.multiworld)

    def _can_reach(self, state, location_name: str) -> bool:
        return self.multiworld.get_location(location_name, self.player).can_reach(state)

    def test_monk_blocked_without_blood_shovel(self) -> None:
        """Monk requires Blood Shovel under Required_Items_Hard."""
        state = self._fresh_state()
        state.collect(self.get_item_by_name("Monk"))
        self.assertFalse(self._can_reach(state, "Monk - Zone 1"))

    def test_monk_accessible_with_blood_shovel(self) -> None:
        state = self._fresh_state()
        for item in self.get_items_by_name(["Monk", "Blood Shovel"]):
            state.collect(item)
        self.assertTrue(self._can_reach(state, "Monk - Zone 1"))

    def test_eli_blocked_without_elis_hand(self) -> None:
        """Eli requires Eli's Hand under Required_Items_Hard."""
        state = self._fresh_state()
        state.collect(self.get_item_by_name("Eli"))
        self.assertFalse(self._can_reach(state, "Eli - Zone 1"))

    def test_eli_accessible_with_elis_hand(self) -> None:
        state = self._fresh_state()
        for item in self.get_items_by_name(["Eli", "Eli's Hand"]):
            state.collect(item)
        self.assertTrue(self._can_reach(state, "Eli - Zone 1"))


class TestCharacterRequirementsItemOnly(CotNDTestBase):
    """With character_unlocks=Item_Only, only the character item is needed."""

    options = {
        "character_unlocks": "Item_Only",
        "floor_clear_checks": "false",
        "starting_character": "Cadence",
        "character_blacklist": [],
        "dlc": [],
        "zone_access_keys": "disabled",
    }

    def test_monk_accessible_without_blood_shovel(self) -> None:
        """With item_only, only the character item is needed — no requirement items."""
        state = CollectionState(self.multiworld)
        state.collect(self.get_item_by_name("Monk"))
        self.assertTrue(self.multiworld.get_location("Monk - Zone 1", self.player).can_reach(state))

    def test_eli_accessible_without_elis_hand(self) -> None:
        """With item_only, only the character item is needed — no requirement items."""
        state = CollectionState(self.multiworld)
        state.collect(self.get_item_by_name("Eli"))
        self.assertTrue(self.multiworld.get_location("Eli - Zone 1", self.player).can_reach(state))


# ---------------------------------------------------------------------------
# Shop rules
# ---------------------------------------------------------------------------

class TestShopStockRules(CotNDTestBase):
    """Shop items beyond the first row require Shop Stock Unlock items."""

    options = {"zone_access_keys": "disabled"}

    def test_first_shop_item_accessible_without_unlock(self) -> None:
        self.assertTrue(self.can_reach_location("Hephaestus - Center Shop Item 1"))

    def test_second_shop_item_requires_one_unlock(self) -> None:
        self.assertFalse(self.can_reach_location("Hephaestus - Center Shop Item 2"))
        self.collect_by_name("Shop Stock Unlock")
        self.assertTrue(self.can_reach_location("Hephaestus - Center Shop Item 2"))

    def test_third_shop_item_requires_two_unlocks(self) -> None:
        unlocks = self.get_items_by_name("Shop Stock Unlock")
        self.assertGreaterEqual(len(unlocks), 2, "Need at least 2 Shop Stock Unlock items in pool")
        self.multiworld.state.collect(unlocks[0])
        self.assertFalse(self.can_reach_location("Hephaestus - Center Shop Item 3"))
        self.multiworld.state.collect(unlocks[1])
        self.assertTrue(self.can_reach_location("Hephaestus - Center Shop Item 3"))


class TestMerlinShopRequiresMerlin(CotNDTestBase):
    """Merlin's shop items always additionally require the Merlin NPC item."""

    options = {
        "lobby_npc_items": "true",
        "zone_access_keys": "disabled",
    }

    def test_merlin_shop_blocked_without_merlin(self) -> None:
        self.assertFalse(self.can_reach_location("Merlin - Center Shop Item 1"))

    def test_merlin_shop_accessible_with_merlin(self) -> None:
        self.collect_by_name("Merlin")
        self.assertTrue(self.can_reach_location("Merlin - Center Shop Item 1"))


# ---------------------------------------------------------------------------
# Codex / Tutorial locations
# ---------------------------------------------------------------------------

class TestCodexLocationsRequireCodex(CotNDTestBase):
    """Tutorial (Codex) locations should require the Codex item."""

    options = {
        "include_codex_checks": "true",
        "lobby_npc_items": "true",
        "zone_access_keys": "disabled",
    }

    def test_dragon_lore_blocked_without_codex(self) -> None:
        self.assertFalse(self.can_reach_location("Dragon Lore"))

    def test_dragon_lore_accessible_with_codex(self) -> None:
        self.collect_by_name("Codex")
        self.assertTrue(self.can_reach_location("Dragon Lore"))


# ---------------------------------------------------------------------------
# Extra mode locations
# ---------------------------------------------------------------------------

class TestExtraModeLocationsRequireMode(CotNDTestBase):
    """Extra mode locations require both the character and the mode item."""

    options = {
        "included_extra_modes": ["No Beat"],
        "starting_character": "Cadence",
        "character_blacklist": [],
        "dlc": [],
        "zone_access_keys": "disabled",
    }

    def test_no_beat_blocked_without_mode(self) -> None:
        self.collect_by_name("Cadence")
        self.assertFalse(self.can_reach_location("Cadence - No Beat"))

    def test_no_beat_blocked_without_character(self) -> None:
        self.collect_by_name("No Beat Mode")
        self.assertFalse(self.can_reach_location("Melody - No Beat"))

    def test_no_beat_accessible_with_both(self) -> None:
        self.collect_by_name(["Cadence", "No Beat Mode"])
        self.assertTrue(self.can_reach_location("Cadence - No Beat"))


# ---------------------------------------------------------------------------
# Completion condition
# ---------------------------------------------------------------------------

class TestGoalAllZonesCompletion(CotNDTestBase):
    """All Zones goal: completion requires the configured number of Complete events."""

    options = {
        "goal": "All_Zones",
        "all_zones_goal_clear": 2,
        "starting_character": "Cadence",
        "character_blacklist": [],
        "dlc": [],
    }

    def test_goal_not_met_with_one_complete(self) -> None:
        self.multiworld.state.add_item("Complete", self.player, 1)
        self.assertFalse(self.multiworld.completion_condition[self.player](self.multiworld.state))

    def test_goal_met_with_two_completes(self) -> None:
        self.multiworld.state.add_item("Complete", self.player, 2)
        self.assertTrue(self.multiworld.completion_condition[self.player](self.multiworld.state))


class TestGoalZonesCompletion(CotNDTestBase):
    """Zones goal: completion requires the configured number of Complete events."""

    options = {
        "goal": "Zones",
        "zones_goal_clear": 3,
        "starting_character": "Cadence",
        "character_blacklist": [],
        "dlc": [],
    }

    def test_goal_not_met_with_two_completes(self) -> None:
        self.multiworld.state.add_item("Complete", self.player, 2)
        self.assertFalse(self.multiworld.completion_condition[self.player](self.multiworld.state))

    def test_goal_met_with_three_completes(self) -> None:
        self.multiworld.state.add_item("Complete", self.player, 3)
        self.assertTrue(self.multiworld.completion_condition[self.player](self.multiworld.state))

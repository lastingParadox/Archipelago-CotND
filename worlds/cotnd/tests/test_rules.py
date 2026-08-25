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
        "zone_progress_checks": 1,
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
        "zone_progress_checks": 1,
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
        "zone_progress_checks": 1,
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
        "zone_progress_checks": 1,
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
        "zone_progress_checks": 1,
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
        "zone_progress_checks": 1,
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
        "zone_progress_checks": 1,
        "include_unique_items": "true",
        "starting_character": "Cadence",
        "character_blacklist": [],
        # Eli's Hand needs Amplified *and* include_unique_items to exist at all;
        # without both, Rules.py skips the requirement and the test is vacuous.
        "dlc": ["Amplified"],
        # CollectionState seeds itself from precollected_items, and the default 25%
        # starting inventory would randomly hand out the very items under test.
        "starting_inventory": 0,
        "zone_access_keys": "disabled",
    }

    def _fresh_state(self):
        """A state holding only this world's precollected items.

        Note CollectionState seeds itself from multiworld.precollected_items, so
        classes using this must pin starting_inventory to keep results stable.
        """
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


class TestCharacterRequirementsSkipUnavailableDLC(CotNDTestBase):
    """A requirement from a DLC the slot does not own cannot gate anything.

    Eli is a base character whose Hand is Amplified-only. Gating him on it without that
    DLC makes every Eli location unreachable, which fails generation outright.
    """

    options = {
        "character_unlocks": "Required_Items_Hard",
        "zone_progress_checks": 1,
        "include_unique_items": "true",
        "starting_character": "Cadence",
        "character_blacklist": [],
        "dlc": [],
        "starting_inventory": 0,
        "zone_access_keys": "disabled",
    }

    def test_eli_accessible_without_amplified(self) -> None:
        state = CollectionState(self.multiworld)
        state.collect(self.get_item_by_name("Eli"))
        self.assertTrue(
            self.multiworld.get_location("Eli - Zone 1", self.player).can_reach(state),
            "Eli's Hand is Amplified-only and must not gate Eli without that DLC")


class TestCharacterRequirementsItemOnly(CotNDTestBase):
    """With character_unlocks=Item_Only, only the character item is needed."""

    options = {
        "character_unlocks": "Item_Only",
        "zone_progress_checks": 1,
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
    """Shop items beyond the first row require Shop Restock items."""

    options = {"zone_access_keys": "disabled"}

    def test_first_shop_item_accessible_without_unlock(self) -> None:
        self.assertTrue(self.can_reach_location("Hephaestus - Center Shop Item 1"))

    def test_second_shop_item_requires_one_unlock(self) -> None:
        self.assertFalse(self.can_reach_location("Hephaestus - Center Shop Item 2"))
        self.collect_by_name("Shop Restock")
        self.assertTrue(self.can_reach_location("Hephaestus - Center Shop Item 2"))

    def test_third_shop_item_requires_two_unlocks(self) -> None:
        unlocks = self.get_items_by_name("Shop Restock")
        self.assertGreaterEqual(len(unlocks), 2, "Need at least 2 Shop Restock items in pool")
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
    """Extra mode locations are one per mode, not per character, and need the mode item."""

    options = {
        "included_extra_modes": ["No Beat"],
        "starting_character": "Cadence",
        "character_blacklist": [],
        "dlc": [],
        "zone_access_keys": "disabled",
    }

    def test_no_beat_blocked_without_mode(self) -> None:
        self.collect_by_name("Cadence")
        self.assertFalse(self.can_reach_location("No Beat Mode"))

    def test_no_beat_accessible_with_mode(self) -> None:
        self.collect_by_name("No Beat Mode")
        self.assertTrue(self.can_reach_location("No Beat Mode"))


class TestExtraModeLocationsRequireZoneAccess(CotNDTestBase):
    """EXTRA_MODE sits in all_zones_types, so the mode item alone is not enough."""

    options = {
        "included_extra_modes": ["No Beat"],
        "starting_character": "Cadence",
        "character_blacklist": [],
        "dlc": [],
        "zone_access_keys": "progressive",
    }

    def test_blocked_without_full_zone_access(self) -> None:
        self.collect_by_name("No Beat Mode")
        self.assertFalse(self.can_reach_location("No Beat Mode"))

    def test_accessible_with_full_zone_access(self) -> None:
        self.collect_by_name("No Beat Mode")
        self.collect_by_name("Progressive Zone Access")
        self.assertTrue(self.can_reach_location("No Beat Mode"))


# ---------------------------------------------------------------------------
# Completion condition
# ---------------------------------------------------------------------------

class TestGoalAllZonesCompletion(CotNDTestBase):
    """All Zones goal: completion requires the configured number of Complete events.

    Zone keys are off so the goal count is the only thing gating the catalyst; the
    Ensemble trigger's own zone requirement is covered by TestEnsembleRequiresZoneAccess.
    """

    options = {
        "goal": "All_Zones",
        "all_zones_goal_clear": 2,
        "starting_character": "Cadence",
        "character_blacklist": [],
        "zone_access_keys": "disabled",
        "dlc": [],
    }

    def test_goal_not_met_with_one_complete(self) -> None:
        state = CollectionState(self.multiworld)
        state.add_item("Complete", self.player, 1)
        self.assertFalse(self._can_reach(state, "Ensemble Completion"))

    def test_goal_met_with_two_completes(self) -> None:
        state = CollectionState(self.multiworld)
        state.add_item("Complete", self.player, 2)
        self.assertTrue(self._can_reach(state, "Ensemble Completion"))

    def _can_reach(self, state, location_name: str) -> bool:
        return self.multiworld.get_location(location_name, self.player).can_reach(state)


class TestGoalZonesCompletion(CotNDTestBase):
    """Zones goal: completion requires the configured number of Complete events.

    Zone keys are off so the goal count is the only thing gating the catalyst; the
    Ensemble trigger's own zone requirement is covered by TestEnsembleRequiresZoneAccess.
    """

    options = {
        "goal": "Zones",
        "zones_goal_clear": 3,
        "starting_character": "Cadence",
        "character_blacklist": [],
        "zone_access_keys": "disabled",
        "dlc": [],
    }

    def test_goal_not_met_with_two_completes(self) -> None:
        state = CollectionState(self.multiworld)
        state.add_item("Complete", self.player, 2)
        self.assertFalse(self._can_reach(state, "Ensemble Completion"))

    def test_goal_met_with_three_completes(self) -> None:
        state = CollectionState(self.multiworld)
        state.add_item("Complete", self.player, 3)
        self.assertTrue(self._can_reach(state, "Ensemble Completion"))

    def _can_reach(self, state, location_name: str) -> bool:
        return self.multiworld.get_location(location_name, self.player).can_reach(state)


# ---------------------------------------------------------------------------
# Victory trigger zone gating
# ---------------------------------------------------------------------------

class _VictoryTriggerBase(CotNDTestBase):
    """Shared setup: progressive keys so full zone access is a real requirement."""

    def _state_with_goal_met(self) -> CollectionState:
        state = CollectionState(self.multiworld)
        state.add_item("Complete", self.player, 3)
        return state

    def _can_reach(self, state, location_name: str) -> bool:
        return self.multiworld.get_location(location_name, self.player).can_reach(state)


class TestExpensivePurchaseIgnoresZoneAccess(_VictoryTriggerBase):
    """Buying a lobby item is not played across the zones, so it must not need them."""

    options = {
        "goal": "Zones",
        "zones_goal_clear": 3,
        "victory_trigger": "Expensive_Purchase",
        "zone_access_keys": "progressive",
        "starting_character": "Cadence",
        "character_blacklist": [],
        "dlc": [],
    }

    def test_reachable_without_full_zone_access(self) -> None:
        self.assertTrue(
            self._can_reach(self._state_with_goal_met(), "Expensive Purchase Completion")
        )


class TestEnsembleRequiresZoneAccess(_VictoryTriggerBase):
    """Ensemble is played across every zone, so it keeps the requirement."""

    options = {
        "goal": "Zones",
        "zones_goal_clear": 3,
        "victory_trigger": "Ensemble",
        "zone_access_keys": "progressive",
        "starting_character": "Cadence",
        "character_blacklist": [],
        "dlc": [],
    }

    def test_blocked_without_full_zone_access(self) -> None:
        self.assertFalse(
            self._can_reach(self._state_with_goal_met(), "Ensemble Completion")
        )

    def test_reachable_with_full_zone_access(self) -> None:
        state = self._state_with_goal_met()
        state.add_item("Progressive Zone Access", self.player, 4)
        self.assertTrue(self._can_reach(state, "Ensemble Completion"))


class TestBossRushRequiresZoneAccess(_VictoryTriggerBase):
    """Boss Rush runs all zone bosses in sequence, so it keeps the requirement too."""

    options = {
        "goal": "Zones",
        "zones_goal_clear": 3,
        "victory_trigger": "Boss_Rush",
        "zone_access_keys": "progressive",
        "starting_character": "Cadence",
        "character_blacklist": [],
        "dlc": [],
    }

    def test_blocked_without_full_zone_access(self) -> None:
        self.assertFalse(
            self._can_reach(self._state_with_goal_met(), "Boss Rush Completion")
        )


class TestDisabledTriggerIgnoresZoneAccess(_VictoryTriggerBase):
    """With no catalyst, meeting the goal is the whole requirement."""

    options = {
        "goal": "Zones",
        "zones_goal_clear": 3,
        "victory_trigger": "Disabled",
        "zone_access_keys": "progressive",
        "starting_character": "Cadence",
        "character_blacklist": [],
        "dlc": [],
    }

    def test_reachable_without_full_zone_access(self) -> None:
        self.assertTrue(
            self._can_reach(self._state_with_goal_met(), "Goal Completion")
        )

    def test_still_blocked_without_the_goal(self) -> None:
        self.assertFalse(
            self._can_reach(CollectionState(self.multiworld), "Goal Completion")
        )


# ---------------------------------------------------------------------------
# Story goal
# ---------------------------------------------------------------------------

STORY_EVENTS_BASE = [
    "Cadence - Beat Dead Ringer",
    "Cadence - Beat NecroDancer",
    "Melody - Beat NecroDancer",
    "Aria - Beat Golden Lute",
]

STORY_EVENTS_AMPLIFIED = STORY_EVENTS_BASE + [
    "Nocturna - Beat Frankensteinway",
    "Nocturna - Beat The Conductor",
]


class TestStoryGoalIsDefault(CotNDTestBase):
    options = {"dlc": []}

    def test_default_goal_is_story(self) -> None:
        self.assertEqual(self.world.options.goal.current_key, "story")


class _StoryGoalBase(CotNDTestBase):
    def _location_names(self) -> set[str]:
        return {loc.name for loc in self.multiworld.get_locations(self.player)}

    def _can_reach(self, state, location_name: str) -> bool:
        return self.multiworld.get_location(location_name, self.player).can_reach(state)


class TestStoryGoalBase(_StoryGoalBase):
    """Without Amplified the story stops at Aria; Nocturna's fights must not appear."""

    options = {
        "goal": "Story",
        "dlc": [],
        "zone_access_keys": "disabled",
        "starting_inventory": 0,
        "character_blacklist": [],
    }

    def test_story_events_present(self) -> None:
        names = self._location_names()
        for event in STORY_EVENTS_BASE:
            self.assertIn(event, names)

    def test_nocturna_events_absent(self) -> None:
        names = self._location_names()
        self.assertNotIn("Nocturna - Beat Frankensteinway", names)
        self.assertNotIn("Nocturna - Beat The Conductor", names)

    def test_zone_events_absent(self) -> None:
        """Story keeps only its own completion events."""
        names = self._location_names()
        self.assertNotIn("Cadence - Beat Zone 1", names)
        self.assertNotIn("Cadence - Beat All Zones", names)

    def test_victory_needs_every_story_event(self) -> None:
        state = CollectionState(self.multiworld)
        for event in STORY_EVENTS_BASE[:-1]:
            state.add_item(event, self.player, 1)
        self.assertFalse(self._can_reach(state, "Ensemble Completion"))

        state.add_item(STORY_EVENTS_BASE[-1], self.player, 1)
        self.assertTrue(self._can_reach(state, "Ensemble Completion"))


class TestStoryGoalAmplified(_StoryGoalBase):
    """With Amplified the story extends through Nocturna."""

    options = {
        "goal": "Story",
        "dlc": ["Amplified"],
        "zone_access_keys": "disabled",
        "starting_inventory": 0,
        "character_blacklist": [],
    }

    def test_all_six_story_events_present(self) -> None:
        names = self._location_names()
        for event in STORY_EVENTS_AMPLIFIED:
            self.assertIn(event, names)

    def test_victory_needs_nocturna_too(self) -> None:
        state = CollectionState(self.multiworld)
        for event in STORY_EVENTS_BASE:
            state.add_item(event, self.player, 1)
        self.assertFalse(self._can_reach(state, "Ensemble Completion"))

        for event in STORY_EVENTS_AMPLIFIED[len(STORY_EVENTS_BASE):]:
            state.add_item(event, self.player, 1)
        self.assertTrue(self._can_reach(state, "Ensemble Completion"))


class TestStoryGoalOverridesBlacklist(_StoryGoalBase):
    """Blacklisting a story character would make the goal unreachable."""

    options = {
        "goal": "Story",
        "dlc": [],
        "character_blacklist": ["Melody", "Aria"],
    }

    def test_story_characters_restored(self) -> None:
        blacklist = set(self.world.options.character_blacklist.value)
        self.assertNotIn("Melody", blacklist)
        self.assertNotIn("Aria", blacklist)

    def test_story_events_still_present(self) -> None:
        names = self._location_names()
        self.assertIn("Melody - Beat NecroDancer", names)
        self.assertIn("Aria - Beat Golden Lute", names)


class TestStoryGoalNeedsZoneAccess(_StoryGoalBase):
    """Aria's fight is in Zone 1, Cadence's and Melody's in Zone 4."""

    options = {
        "goal": "Story",
        "dlc": [],
        "zone_access_keys": "progressive",
        "starting_zone": "zone_1",
        "starting_inventory": 0,
        "character_blacklist": [],
    }

    def test_zone4_boss_blocked_without_access(self) -> None:
        state = CollectionState(self.multiworld)
        state.add_item("Cadence", self.player, 1)
        self.assertFalse(self._can_reach(state, "Cadence - Beat Dead Ringer"))

    def test_zone4_boss_reachable_with_access(self) -> None:
        state = CollectionState(self.multiworld)
        state.add_item("Cadence", self.player, 1)
        state.add_item("Progressive Zone Access", self.player, 3)
        self.assertTrue(self._can_reach(state, "Cadence - Beat Dead Ringer"))

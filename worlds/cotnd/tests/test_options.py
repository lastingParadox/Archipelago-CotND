"""Tests for option combinations — location/item presence, DLC gating, and generation smoke tests."""
from worlds.cotnd.Locations import LocationType

from .bases import CotNDTestBase


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _location_names(multiworld, player) -> list[str]:
    return [loc.name for loc in multiworld.get_locations(player)]


def _pool_names(multiworld, player) -> list[str]:
    return [item.name for item in multiworld.itempool if item.player == player]


# ---------------------------------------------------------------------------
# Goal options
# ---------------------------------------------------------------------------

class TestGoalAllZonesLocations(CotNDTestBase):
    """All Zones goal should include All Zones check locations and exclude Beat Zone events."""

    options = {
        "goal": "All_Zones",
        "starting_character": "Cadence",
        "character_blacklist": [],
        "dlc": [],
    }

    def test_all_zones_location_present(self) -> None:
        names = _location_names(self.multiworld, self.player)
        self.assertIn("Cadence - All Zones", names)

    def test_beat_zone_event_absent(self) -> None:
        """Beat Zone N events are only used for the Zones goal."""
        names = _location_names(self.multiworld, self.player)
        self.assertNotIn("Cadence - Beat Zone 1", names)


class TestGoalZonesLocations(CotNDTestBase):
    """Zones goal should not include All Zones check locations."""

    options = {
        "goal": "Zones",
        "starting_character": "Cadence",
        "character_blacklist": [],
        "dlc": [],
    }

    def test_all_zones_location_absent(self) -> None:
        names = _location_names(self.multiworld, self.player)
        self.assertNotIn("Cadence - All Zones", names)


# ---------------------------------------------------------------------------
# Floor clear checks on/off
# ---------------------------------------------------------------------------

class _ZoneProgressBase(CotNDTestBase):
    """Zone Progress Checks: the zone clear is always a check, floors are spaced."""

    def floors_present(self) -> set[int]:
        names = _location_names(self.multiworld, self.player)
        return {n for n in (1, 2, 3) if f"Cadence - Zone 1 - Floor {n}" in names}

    def assert_zone_clear_present(self) -> None:
        self.assertIn("Cadence - Zone 1", _location_names(self.multiworld, self.player))

    def assert_no_boss_locations(self) -> None:
        names = _location_names(self.multiworld, self.player)
        self.assertEqual([n for n in names if n.endswith(" - Boss")], [])


class TestZoneProgressChecksOne(_ZoneProgressBase):
    options = {"zone_progress_checks": 1, "character_blacklist": [], "dlc": []}

    def test_only_zone_clear(self) -> None:
        self.assert_zone_clear_present()
        self.assertEqual(self.floors_present(), set())
        self.assert_no_boss_locations()

    def test_story_bosses_survive(self) -> None:
        """Story bosses are independent of this option."""
        names = _location_names(self.multiworld, self.player)
        self.assertIn("Cadence - Dead Ringer", names)
        self.assertIn("Aria - Golden Lute", names)


class TestZoneProgressChecksTwo(_ZoneProgressBase):
    options = {"zone_progress_checks": 2, "character_blacklist": [], "dlc": []}

    def test_middle_floor_only(self) -> None:
        self.assert_zone_clear_present()
        self.assertEqual(self.floors_present(), {2})


class TestZoneProgressChecksThree(_ZoneProgressBase):
    options = {"zone_progress_checks": 3, "character_blacklist": [], "dlc": []}

    def test_outer_floors(self) -> None:
        """Spacing, not back-loading: floors 1 and 3, deliberately skipping 2."""
        self.assert_zone_clear_present()
        self.assertEqual(self.floors_present(), {1, 3})


class TestZoneProgressChecksFour(_ZoneProgressBase):
    options = {"zone_progress_checks": 4, "character_blacklist": [], "dlc": []}

    def test_every_floor(self) -> None:
        self.assert_zone_clear_present()
        self.assertEqual(self.floors_present(), {1, 2, 3})
        self.assert_no_boss_locations()

    def test_dove_matches_other_characters(self) -> None:
        """Dove has no boss, but her zone clear is the same location as everyone's."""
        names = _location_names(self.multiworld, self.player)
        dove = [n for n in names if n.startswith("Dove - Zone 1")]
        cadence = [n for n in names if n.startswith("Cadence - Zone 1")]
        self.assertEqual(len(dove), len(cadence))
        self.assertIn("Dove - Zone 1", names)


# ---------------------------------------------------------------------------
# Codex checks on/off
# ---------------------------------------------------------------------------

class TestCodexChecksEnabled(CotNDTestBase):
    """With include_codex_checks=True, tutorial locations should be present."""

    options = {"include_codex_checks": "true"}

    def test_codex_locations_present(self) -> None:
        names = _location_names(self.multiworld, self.player)
        self.assertIn("Dragon Lore", names)
        self.assertIn("Bomb Lore", names)


class TestCodexChecksDisabled(CotNDTestBase):
    """With include_codex_checks=False, tutorial locations should be absent."""

    options = {"include_codex_checks": "false"}

    def test_codex_locations_absent(self) -> None:
        names = _location_names(self.multiworld, self.player)
        self.assertNotIn("Dragon Lore", names)
        self.assertNotIn("Bomb Lore", names)


# ---------------------------------------------------------------------------
# DLC gating
# ---------------------------------------------------------------------------

class TestAmplifiedLocationsAbsentWithoutDLC(CotNDTestBase):
    """Zone 5 locations must not appear when Amplified DLC is not enabled."""

    options = {
        "dlc": [],
        "character_blacklist": [],
    }

    def test_zone5_locations_absent(self) -> None:
        names = _location_names(self.multiworld, self.player)
        zone5_locs = [n for n in names if "Zone 5" in n]
        self.assertEqual(zone5_locs, [], f"Found Zone 5 locations without Amplified: {zone5_locs}")

    def test_amplified_characters_absent_from_pool(self) -> None:
        pool = set(_pool_names(self.multiworld, self.player))
        amplified_only = {"Nocturna", "Diamond", "Mary", "Tempo"}
        present = pool & amplified_only
        self.assertEqual(present, set(), f"Amplified characters in pool without DLC: {present}")


class TestAmplifiedLocationsPresent(CotNDTestBase):
    """Zone 5 locations must appear when Amplified DLC is enabled."""

    options = {
        "dlc": ["Amplified"],
        "character_blacklist": [],
    }

    def test_zone5_locations_present(self) -> None:
        names = _location_names(self.multiworld, self.player)
        zone5_locs = [n for n in names if "Zone 5" in n]
        self.assertGreater(len(zone5_locs), 0, "Expected Zone 5 locations with Amplified enabled")

    def test_amplified_characters_in_pool(self) -> None:
        pool = set(_pool_names(self.multiworld, self.player))
        # At least one Amplified character should be in the pool
        amplified_only = {"Nocturna", "Diamond", "Mary", "Tempo"}
        self.assertTrue(pool & amplified_only, "No Amplified characters in pool with Amplified DLC enabled")


class TestSynchronyCharactersGated(CotNDTestBase):
    """Synchrony characters must not appear in the item pool without the Synchrony DLC."""

    options = {"dlc": []}

    def test_synchrony_characters_absent(self) -> None:
        pool = set(_pool_names(self.multiworld, self.player))
        sync_chars = {"Klarinetta", "Chaunter", "Suzu"}
        present = pool & sync_chars
        self.assertEqual(present, set(), f"Synchrony characters in pool without DLC: {present}")


# ---------------------------------------------------------------------------
# Extra modes
# ---------------------------------------------------------------------------

class TestExtraModeLocationsEnabled(CotNDTestBase):
    """Included extra modes should have locations in the world."""

    options = {
        "included_extra_modes": ["No Beat", "Double Tempo"],
        "character_blacklist": [],
        "dlc": [],
    }

    def test_no_beat_location_present(self) -> None:
        names = _location_names(self.multiworld, self.player)
        self.assertIn("No Beat Mode", names)

    def test_double_tempo_location_present(self) -> None:
        names = _location_names(self.multiworld, self.player)
        self.assertIn("Double Tempo Mode", names)

    def test_mode_items_in_pool(self) -> None:
        pool = set(_pool_names(self.multiworld, self.player))
        self.assertIn("No Beat Mode", pool)
        self.assertIn("Double Tempo Mode", pool)


class TestExtraModeLocationsDisabled(CotNDTestBase):
    """Excluded extra modes should not have locations or items."""

    options = {
        "included_extra_modes": [],
        "character_blacklist": [],
        "dlc": [],
    }

    def test_no_extra_mode_locations(self) -> None:
        names = _location_names(self.multiworld, self.player)
        mode_locs = [n for n in names if " - No Beat" in n or " - Double Tempo" in n]
        self.assertEqual(mode_locs, [])

    def test_no_mode_items_in_pool(self) -> None:
        pool = set(_pool_names(self.multiworld, self.player))
        self.assertNotIn("No Beat Mode", pool)
        self.assertNotIn("Double Tempo", pool)


# ---------------------------------------------------------------------------
# Lobby NPC items
# ---------------------------------------------------------------------------

class TestLobbyNPCItemsShuffled(CotNDTestBase):
    """With lobby_npc_items=True, NPC items should be in the general pool."""

    options = {"lobby_npc_items": "true"}

    def test_npc_items_in_pool(self) -> None:
        pool = set(_pool_names(self.multiworld, self.player))
        self.assertIn("Merlin", pool)
        self.assertIn("Codex", pool)


class TestLobbyNPCItemsLocked(CotNDTestBase):
    """With lobby_npc_items=False (default), NPC items are locked to their caged locations."""

    options = {"lobby_npc_items": "false"}

    def test_npc_items_not_in_pool(self) -> None:
        pool = set(_pool_names(self.multiworld, self.player))
        self.assertNotIn("Merlin", pool)
        self.assertNotIn("Codex", pool)

    def test_caged_npc_locations_have_locked_items(self) -> None:
        from worlds.cotnd.Utils import LOBBY_NPCS
        for npc in LOBBY_NPCS:
            loc = self.multiworld.get_location(f"Caged {npc}", self.player)
            self.assertIsNotNone(loc.item, f"Caged {npc} should have a locked item")
            self.assertEqual(loc.item.name, npc)


# ---------------------------------------------------------------------------
# Character blacklist
# ---------------------------------------------------------------------------

class TestBlacklistedCharacterAbsent(CotNDTestBase):
    """Blacklisted characters must not appear in the item pool or have locations."""

    options = {
        # Not the Story goal: that one names Melody and Aria outright and
        # deliberately overrides the blacklist to keep itself reachable.
        "goal": "Zones",
        "character_blacklist": ["Melody", "Aria"],
        "dlc": [],
    }

    def test_blacklisted_characters_not_in_pool(self) -> None:
        pool = set(_pool_names(self.multiworld, self.player))
        self.assertNotIn("Melody", pool)
        self.assertNotIn("Aria", pool)

    def test_blacklisted_character_locations_absent(self) -> None:
        names = _location_names(self.multiworld, self.player)
        melody_locs = [n for n in names if n.startswith("Melody")]
        aria_locs = [n for n in names if n.startswith("Aria")]
        self.assertEqual(melody_locs, [])
        self.assertEqual(aria_locs, [])


# ---------------------------------------------------------------------------
# Zone access key item counts
# ---------------------------------------------------------------------------

class TestSeparateZoneKeyCount(CotNDTestBase):
    """With separate keys, pool should contain one key per zone minus the starting zone."""

    options = {
        "zone_access_keys": "separate",
        "starting_zone": "zone_1",
        "dlc": [],
        "character_blacklist": [],
    }

    def test_non_starting_zone_keys_in_pool(self) -> None:
        pool = _pool_names(self.multiworld, self.player)
        # Zones 2, 3, 4 each get one key (zone 1 is precollected)
        for zone in range(2, 5):
            self.assertIn(f"Zone {zone} Access", pool)

    def test_starting_zone_key_not_in_pool(self) -> None:
        pool = _pool_names(self.multiworld, self.player)
        self.assertNotIn("Zone 1 Access", pool)


class TestProgressiveZoneKeyCount(CotNDTestBase):
    """With progressive keys and starting_zone=1, three keys in pool (unlock zones 2-4)."""

    options = {
        "zone_access_keys": "progressive",
        "starting_zone": "zone_1",
        "dlc": [],
        "character_blacklist": [],
    }

    def test_progressive_key_count(self) -> None:
        pool = _pool_names(self.multiworld, self.player)
        key_count = pool.count("Progressive Zone Access")
        self.assertEqual(key_count, 3, f"Expected 3 Progressive Zone Access items, got {key_count}")


class TestProgressiveZoneKeyCountAmplified(CotNDTestBase):
    """With Amplified, progressive keys should have 4 copies (unlock zones 2-5)."""

    options = {
        "zone_access_keys": "progressive",
        "starting_zone": "zone_1",
        "dlc": ["Amplified"],
        "character_blacklist": [],
    }

    def test_progressive_key_count_amplified(self) -> None:
        pool = _pool_names(self.multiworld, self.player)
        key_count = pool.count("Progressive Zone Access")
        self.assertEqual(key_count, 4, f"Expected 4 Progressive Zone Access items with Amplified, got {key_count}")


class TestProgressiveStartingZone3KeyCount(CotNDTestBase):
    """Starting Zone 3 progressive: 2 keys precollected, 1 remaining in pool (for zone 4)."""

    options = {
        "zone_access_keys": "progressive",
        "starting_zone": "zone_3",
        "dlc": [],
        "character_blacklist": [],
    }

    def test_one_key_in_pool(self) -> None:
        pool = _pool_names(self.multiworld, self.player)
        key_count = pool.count("Progressive Zone Access")
        self.assertEqual(key_count, 1, f"Expected 1 Progressive Zone Access in pool, got {key_count}")

    def test_two_keys_precollected(self) -> None:
        precollected = [i.name for i in self.multiworld.precollected_items[self.player]]
        key_count = precollected.count("Progressive Zone Access")
        self.assertEqual(key_count, 2, f"Expected 2 precollected Progressive Zone Access, got {key_count}")


class TestZoneProgressSlotData(CotNDTestBase):
    """The mod gets the resolved floor list, so it never reimplements the spacing."""

    options = {"zone_progress_checks": 3, "character_blacklist": [], "dlc": []}

    def test_table_matches_generation(self) -> None:
        from worlds.cotnd.Locations import ZONE_PROGRESS_FLOORS

        kept = ZONE_PROGRESS_FLOORS[self.world.options.zone_progress_checks.value]
        names = _location_names(self.multiworld, self.player)
        for floor in (1, 2, 3):
            present = f"Cadence - Zone 1 - Floor {floor}" in names
            self.assertEqual(present, floor in kept, f"floor {floor} mismatch")


class TestZoneProgressCountsScale(CotNDTestBase):
    """FLOOR count is (N-1) per character-zone; ZONE count is one per character-zone."""

    options = {"zone_progress_checks": 3, "character_blacklist": [], "dlc": []}

    def test_counts(self) -> None:
        locs = list(self.multiworld.get_locations(self.player))
        zone_count = sum(1 for loc in locs if _loc_type(loc) is LocationType.ZONE)
        floor_count = sum(1 for loc in locs if _loc_type(loc) is LocationType.FLOOR)
        self.assertEqual(floor_count, zone_count * 2, "N=3 keeps two floors per zone")


def _loc_type(loc):
    from worlds.cotnd.Locations import location_from_name

    return location_from_name(loc.name).type


class TestSpeedrunTimesSlotData(CotNDTestBase):
    """Only timed characters reach the mod; everyone else is absent, meaning untimed."""

    options = {
        "all_zones_speedrun_times": {"Cadence": 6, "Bard": 1, "Coda": 0, "Monk": -1},
        "character_blacklist": [],
        "dlc": [],
    }

    def test_only_timed_characters_shipped(self) -> None:
        times = self.world.fill_slot_data()["all_zones_speedrun_times"]
        self.assertEqual(times.get("Cadence"), 6)
        self.assertNotIn("Dove", times, "untimed characters should be omitted entirely")

    def test_disabled_characters_omitted(self) -> None:
        times = self.world.fill_slot_data()["all_zones_speedrun_times"]
        self.assertNotIn("Coda", times, "zero means untimed, so it should not ship a time")
        self.assertNotIn("Monk", times, "-1 means untimed, so it should not ship a time")

    def test_below_minimum_is_raised_before_shipping(self) -> None:
        times = self.world.fill_slot_data()["all_zones_speedrun_times"]
        self.assertEqual(times.get("Bard"), 3)


class TestSpeedrunTimesDefaultOff(CotNDTestBase):
    """The option is off by default, so the mod sees an empty table."""

    options = {"goal": "All_Zones", "character_blacklist": [], "dlc": []}

    def test_slot_data_empty(self) -> None:
        self.assertEqual(self.world.fill_slot_data()["all_zones_speedrun_times"], {})

    def test_all_zones_location_still_generated(self) -> None:
        self.assertIn("Cadence - All Zones", _location_names(self.multiworld, self.player))

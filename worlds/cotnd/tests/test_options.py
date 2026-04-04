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

class TestFloorClearChecksEnabled(CotNDTestBase):
    """With floor_clear_checks=True, per-floor locations should be present."""

    options = {
        "floor_clear_checks": "true",
        "character_blacklist": [],
        "dlc": [],
    }

    def test_floor_locations_present(self) -> None:
        names = _location_names(self.multiworld, self.player)
        self.assertIn("Cadence - Zone 1 - Floor 1", names)
        self.assertIn("Cadence - Zone 1 - Boss", names)

    def test_zone_clear_location_absent(self) -> None:
        names = _location_names(self.multiworld, self.player)
        self.assertNotIn("Cadence - Zone 1", names)


class TestFloorClearChecksDisabled(CotNDTestBase):
    """With floor_clear_checks=False, only the Zone clear location is present (no per-floor)."""

    options = {
        "floor_clear_checks": "false",
        "character_blacklist": [],
        "dlc": [],
    }

    def test_zone_clear_location_present(self) -> None:
        names = _location_names(self.multiworld, self.player)
        self.assertIn("Cadence - Zone 1", names)

    def test_floor_locations_absent(self) -> None:
        names = _location_names(self.multiworld, self.player)
        self.assertNotIn("Cadence - Zone 1 - Floor 1", names)
        self.assertNotIn("Cadence - Zone 1 - Boss", names)


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
        self.assertIn("Cadence - No Beat", names)

    def test_double_tempo_location_present(self) -> None:
        names = _location_names(self.multiworld, self.player)
        self.assertIn("Cadence - Double Tempo", names)

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

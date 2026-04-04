"""Tests for Validation.py — option clamping, blacklist pruning, and warning fixes."""
import unittest

from worlds.cotnd.Characters import get_available_characters
from worlds.cotnd.Items import ItemType, all_items
from worlds.cotnd.Options import CotNDOptions
from worlds.cotnd.Validation import (
    validate_blacklist,
    validate_modes,
    validate_death_link_type,
    validate_starting_zone,
    cap_option,
    validate_price_ranges,
)

from .bases import CotNDTestBase


# ---------------------------------------------------------------------------
# Blacklist validation
# ---------------------------------------------------------------------------

class TestBlacklistAllChars(CotNDTestBase):
    """Blacklisting every character should rescue Cadence to maintain progression."""

    options = {
        "character_blacklist": [
            "Cadence", "Melody", "Aria", "Dorian", "Eli", "Monk", "Dove",
            "Coda", "Bolt", "Bard", "Reaper",
        ],
        "dlc": [],
    }

    def test_cadence_not_blacklisted(self) -> None:
        blacklist = set(self.multiworld.worlds[self.player].options.character_blacklist.value)
        self.assertNotIn("Cadence", blacklist)

    def test_at_least_one_character_available(self) -> None:
        world = self.multiworld.worlds[self.player]
        chars = get_available_characters(
            set(world.options.character_blacklist.value), world.dlcs
        )
        self.assertGreater(len(chars), 0)


# ---------------------------------------------------------------------------
# Death link type validation
# ---------------------------------------------------------------------------

class TestDeathLinkMarvWithoutAmplified(CotNDTestBase):
    """Marv death link without Amplified DLC must fall back to Tempo."""

    options = {
        "death_link": "true",
        "death_link_type": "Marv",
        "dlc": [],
    }

    def test_death_link_type_is_not_marv(self) -> None:
        death_link_type = self.multiworld.worlds[self.player].options.death_link_type.value
        self.assertNotEqual(death_link_type, 2, "Marv requires Amplified DLC")

    def test_death_link_type_is_tempo(self) -> None:
        death_link_type = self.multiworld.worlds[self.player].options.death_link_type.value
        self.assertEqual(death_link_type, 1)


class TestDeathLinkMarvWithAmplified(CotNDTestBase):
    """Marv death link with Amplified DLC should remain as Marv."""

    options = {
        "death_link": "true",
        "death_link_type": "Marv",
        "dlc": ["Amplified"],
    }

    def test_death_link_type_stays_marv(self) -> None:
        death_link_type = self.multiworld.worlds[self.player].options.death_link_type.value
        self.assertEqual(death_link_type, 2)


# ---------------------------------------------------------------------------
# Starting zone validation
# ---------------------------------------------------------------------------

class TestStartingZone5WithoutAmplified(CotNDTestBase):
    """Starting Zone 5 without Amplified must be clamped to 4."""

    options = {
        "zone_access_keys": "separate",
        "starting_zone": "zone_5",
        "dlc": [],
    }

    def test_starting_zone_clamped_to_4(self) -> None:
        starting_zone = self.multiworld.worlds[self.player].starting_zone
        self.assertEqual(starting_zone, 4)


class TestStartingZone5WithAmplified(CotNDTestBase):
    """Starting Zone 5 with Amplified should remain 5."""

    options = {
        "zone_access_keys": "separate",
        "starting_zone": "zone_5",
        "dlc": ["Amplified"],
    }

    def test_starting_zone_stays_5(self) -> None:
        starting_zone = self.multiworld.worlds[self.player].starting_zone
        self.assertEqual(starting_zone, 5)


# ---------------------------------------------------------------------------
# Amplified modes stripped without Amplified DLC
# ---------------------------------------------------------------------------

class TestAmplifiedModesStrippedWithoutDLC(CotNDTestBase):
    """Amplified-only modes must be removed when Amplified DLC is not enabled."""

    amplified_modes = {"No Return", "Hard", "Phasing", "Randomizer", "Mystery"}

    options = {
        "dlc": [],
        "included_extra_modes": ["No Return", "Hard", "Phasing", "Randomizer", "Mystery", "No Beat"],
    }

    def test_amplified_modes_not_included(self) -> None:
        included = set(self.multiworld.worlds[self.player].options.included_extra_modes.value)
        self.assertTrue(
            included.isdisjoint(self.amplified_modes),
            f"Amplified modes should be removed without DLC, but found: {included & self.amplified_modes}",
        )

    def test_base_modes_still_included(self) -> None:
        included = set(self.multiworld.worlds[self.player].options.included_extra_modes.value)
        self.assertIn("No Beat", included)


class TestAmplifiedModesKeptWithDLC(CotNDTestBase):
    """Amplified modes must remain when Amplified DLC is enabled."""

    options = {
        "dlc": ["Amplified"],
        "included_extra_modes": ["No Return", "Hard", "No Beat"],
    }

    def test_amplified_modes_kept(self) -> None:
        included = set(self.multiworld.worlds[self.player].options.included_extra_modes.value)
        self.assertIn("No Return", included)
        self.assertIn("Hard", included)


# ---------------------------------------------------------------------------
# Price range validation (min/max swap)
# ---------------------------------------------------------------------------

class TestPriceRangeMinMaxSwap(unittest.TestCase):
    """validate_price_ranges should swap min/max when min > max."""

    def _make_options(self, prefix, min_val, max_val):
        """Build a minimal stub with the two price attributes."""
        class Stub:
            pass

        class Val:
            def __init__(self, v):
                self.value = v
            def __class_getitem__(cls, item):
                return cls

        options = Stub()
        min_attr = Val(min_val)
        max_attr = Val(max_val)
        type(min_attr).__init__ = lambda self, v: None.__init__()
        # Use real option types via a simple namedtuple-like approach
        setattr(options, f"{prefix}_price_min", type("O", (), {"value": min_val})())
        setattr(options, f"{prefix}_price_max", type("O", (), {"value": max_val})())
        return options

    def test_price_swap(self) -> None:
        from worlds.cotnd.Validation import ensure_min_max

        class FakeOption:
            def __init__(self, v):
                self.value = v

        class Opts:
            pass

        opts = Opts()
        opts.foo_price_min = FakeOption(10)
        opts.foo_price_max = FakeOption(2)

        # Patch ensure_min_max to accept our stub
        type(opts.foo_price_min).__init__ = lambda self, v: setattr(self, "value", v)
        type(opts.foo_price_max).__init__ = lambda self, v: setattr(self, "value", v)

        ensure_min_max(opts, "foo_price_min", "foo_price_max")
        self.assertLessEqual(opts.foo_price_min.value, opts.foo_price_max.value)

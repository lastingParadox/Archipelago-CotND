"""Tests for Validation.py — option clamping, blacklist pruning, and the fixes it warns about.

Validation runs in generate_early, so world-based tests read already-reconciled options.
"""
from worlds.cotnd.Options import DeathLinkType
from worlds.cotnd.Utils import DLC
from worlds.cotnd.Validation import (
    MIN_SPEEDRUN_MINUTES,
    available_characters,
    validate_price_ranges,
    validate_speedrun_times,
)

from .bases import CotNDTestBase

BASE_CHARACTERS = [
    "Cadence", "Melody", "Aria", "Dorian", "Eli",
    "Monk", "Dove", "Coda", "Bolt", "Bard", "Reaper",
]

AMPLIFIED_MODES = {"No Return", "Hard", "Phasing", "Randomizer", "Mystery"}


# ---------------------------------------------------------------------------
# Blacklist validation
# ---------------------------------------------------------------------------

class TestBlacklistEveryCharacter(CotNDTestBase):
    """Blacklisting every character rescues Cadence, so progression stays possible."""

    options = {
        "goal": "zones",
        "character_blacklist": BASE_CHARACTERS,
        "dlc": [],
    }

    def test_cadence_rescued(self) -> None:
        self.assertNotIn("Cadence", self.world.options.character_blacklist.value)

    def test_only_cadence_rescued(self) -> None:
        """The rescue is minimal -- everyone else stays blacklisted."""
        blacklist = set(self.world.options.character_blacklist.value)
        self.assertEqual(blacklist, set(BASE_CHARACTERS) - {"Cadence"})

    def test_a_character_survives(self) -> None:
        characters = available_characters(DLC.BASE, set(self.world.options.character_blacklist.value))
        self.assertEqual([item.name for item in characters], ["Cadence"])


class TestBlacklistStoryCharacters(CotNDTestBase):
    """The Story goal needs its cast, so blacklisting them is overridden."""

    options = {
        "goal": "story",
        "character_blacklist": ["Cadence", "Melody", "Aria", "Bard"],
        "dlc": [],
    }

    def test_story_characters_restored(self) -> None:
        blacklist = set(self.world.options.character_blacklist.value)
        self.assertTrue(blacklist.isdisjoint({"Cadence", "Melody", "Aria"}))

    def test_non_story_character_stays_blacklisted(self) -> None:
        """Only the goal's own cast is rescued."""
        self.assertIn("Bard", self.world.options.character_blacklist.value)


class TestBlacklistStoryCharactersAmplified(CotNDTestBase):
    """Nocturna joins the required cast only when Amplified is enabled."""

    options = {
        "goal": "story",
        "character_blacklist": ["Nocturna"],
        "dlc": ["Amplified"],
    }

    def test_nocturna_restored(self) -> None:
        self.assertNotIn("Nocturna", self.world.options.character_blacklist.value)


class TestBlacklistKeptWithoutStoryGoal(CotNDTestBase):
    """Any other goal leaves the blacklist alone."""

    options = {
        "goal": "zones",
        "character_blacklist": ["Cadence", "Melody"],
        "dlc": [],
    }

    def test_blacklist_untouched(self) -> None:
        self.assertEqual(set(self.world.options.character_blacklist.value), {"Cadence", "Melody"})


# ---------------------------------------------------------------------------
# DeathLink type validation
# ---------------------------------------------------------------------------

class TestDeathLinkMarvWithoutAmplified(CotNDTestBase):
    """Marv requires Amplified, so it falls back to Tempo."""

    options = {"death_link": "true", "death_link_type": "Marv", "dlc": []}

    def test_falls_back_to_tempo(self) -> None:
        self.assertEqual(self.world.options.death_link_type.value, DeathLinkType.option_Tempo)


class TestDeathLinkMarvWithAmplified(CotNDTestBase):
    options = {"death_link": "true", "death_link_type": "Marv", "dlc": ["Amplified"]}

    def test_stays_marv(self) -> None:
        self.assertEqual(self.world.options.death_link_type.value, DeathLinkType.option_Marv)


class TestDeathLinkOtherTypesUntouched(CotNDTestBase):
    options = {"death_link": "true", "death_link_type": "Absolute", "dlc": []}

    def test_stays_absolute(self) -> None:
        self.assertEqual(self.world.options.death_link_type.value, DeathLinkType.option_Absolute)


# ---------------------------------------------------------------------------
# Starting zone validation
# ---------------------------------------------------------------------------

class TestStartingZoneClampedWithoutAmplified(CotNDTestBase):
    """Zone 5 only exists in Amplified."""

    options = {"zone_access_keys": "separate", "starting_zone": "zone_5", "dlc": []}

    def test_clamped_to_four(self) -> None:
        self.assertEqual(self.world.options.starting_zone.value, 4)


class TestStartingZoneKeptWithAmplified(CotNDTestBase):
    options = {"zone_access_keys": "separate", "starting_zone": "zone_5", "dlc": ["Amplified"]}

    def test_stays_five(self) -> None:
        self.assertEqual(self.world.options.starting_zone.value, 5)


# ---------------------------------------------------------------------------
# Extra mode validation
# ---------------------------------------------------------------------------

class TestAmplifiedModesStrippedWithoutDLC(CotNDTestBase):
    options = {
        "dlc": [],
        "included_extra_modes": sorted(AMPLIFIED_MODES) + ["No Beat"],
    }

    def test_amplified_modes_removed(self) -> None:
        included = set(self.world.options.included_extra_modes.value)
        self.assertTrue(included.isdisjoint(AMPLIFIED_MODES))

    def test_base_modes_kept(self) -> None:
        self.assertIn("No Beat", self.world.options.included_extra_modes.value)


class TestAmplifiedModesKeptWithDLC(CotNDTestBase):
    options = {"dlc": ["Amplified"], "included_extra_modes": ["No Return", "Hard", "No Beat"]}

    def test_all_modes_kept(self) -> None:
        included = set(self.world.options.included_extra_modes.value)
        self.assertEqual(included, {"No Return", "Hard", "No Beat"})


# ---------------------------------------------------------------------------
# Starting character validation
# ---------------------------------------------------------------------------

class TestStartingCharacterFallsBack(CotNDTestBase):
    """A character the pool cannot hold is replaced by one it can."""

    options = {"starting_character": "Nocturna", "dlc": []}

    def test_not_nocturna(self) -> None:
        self.assertNotEqual(self.world.options.starting_character.current_option_name, "Nocturna")

    def test_fallback_is_available(self) -> None:
        chosen = self.world.options.starting_character.current_option_name
        self.assertIn(chosen, BASE_CHARACTERS)


class TestStartingCharacterFallsBackFromBlacklist(CotNDTestBase):
    """The blacklist removes characters from the pool too."""

    options = {
        "goal": "zones",
        "starting_character": "Bard",
        "character_blacklist": ["Bard"],
        "dlc": [],
    }

    def test_not_bard(self) -> None:
        self.assertNotEqual(self.world.options.starting_character.current_option_name, "Bard")


class TestStartingCharacterKept(CotNDTestBase):
    options = {"starting_character": "Cadence", "dlc": []}

    def test_stays_cadence(self) -> None:
        self.assertEqual(self.world.options.starting_character.current_option_name, "Cadence")


# ---------------------------------------------------------------------------
# Goal amount validation
# ---------------------------------------------------------------------------

class TestAllZonesGoalCapped(CotNDTestBase):
    """A goal cannot ask for more clears than there are characters to clear with."""

    options = {"goal": "all_zones", "all_zones_goal_clear": 20, "dlc": [], "character_blacklist": []}

    def test_capped_to_character_count(self) -> None:
        self.assertEqual(self.world.options.all_zones_goal_clear.value, len(BASE_CHARACTERS))


class TestZonesGoalCapped(CotNDTestBase):
    options = {"goal": "zones", "zones_goal_clear": 100, "dlc": [], "character_blacklist": []}

    def test_capped_to_characters_times_zones(self) -> None:
        # Four zones without Amplified.
        self.assertEqual(self.world.options.zones_goal_clear.value, len(BASE_CHARACTERS) * 4)


class TestGoalAmountUnderCapUntouched(CotNDTestBase):
    options = {"goal": "all_zones", "all_zones_goal_clear": 3, "dlc": [], "character_blacklist": []}

    def test_left_alone(self) -> None:
        self.assertEqual(self.world.options.all_zones_goal_clear.value, 3)


class TestLuteShardsRaisedToGoal(CotNDTestBase):
    """The pool must hold at least as many shards as the goal counts."""

    options = {
        "goal": "golden_lute_shards",
        "golden_lute_shards_goal_clear": 30,
        "lute_shards_in_pool": 5,
    }

    def test_pool_raised(self) -> None:
        self.assertGreaterEqual(
            self.world.options.lute_shards_in_pool.value,
            self.world.options.golden_lute_shards_goal_clear.value,
        )


class TestLuteShardsAboveGoalUntouched(CotNDTestBase):
    options = {
        "goal": "golden_lute_shards",
        "golden_lute_shards_goal_clear": 5,
        "lute_shards_in_pool": 20,
    }

    def test_pool_left_alone(self) -> None:
        self.assertEqual(self.world.options.lute_shards_in_pool.value, 20)


# ---------------------------------------------------------------------------
# Price ranges
# ---------------------------------------------------------------------------

class TestPriceRanges(CotNDTestBase):
    """validate_price_ranges is called directly so each case gets its own bounds."""

    options = {"dlc": []}

    def _validate(self, **overrides) -> dict:
        ranges = self.world.options.price_ranges.value
        # Assigned one key at a time: the value is a Counter, whose update() adds.
        for key, bound in overrides.items():
            ranges[key] = bound
        validate_price_ranges(self.world.options)
        return ranges

    def test_swaps_inverted_bounds(self) -> None:
        ranges = self._validate(random_min=10, random_max=2)
        self.assertEqual((ranges["random_min"], ranges["random_max"]), (2, 10))

    def test_leaves_correct_bounds(self) -> None:
        ranges = self._validate(useful_min=2, useful_max=8)
        self.assertEqual((ranges["useful_min"], ranges["useful_max"]), (2, 8))

    def test_equal_bounds_untouched(self) -> None:
        ranges = self._validate(filler_min=5, filler_max=5)
        self.assertEqual((ranges["filler_min"], ranges["filler_max"]), (5, 5))

    def test_fills_missing_keys_from_defaults(self) -> None:
        """Every key is optional in the YAML, so validation has to backfill."""
        self.world.options.price_ranges.value.clear()
        validate_price_ranges(self.world.options)
        ranges = self.world.options.price_ranges.value
        for prefix in ("random", "filler", "useful", "progression"):
            self.assertIn(f"{prefix}_min", ranges)
            self.assertLessEqual(ranges[f"{prefix}_min"], ranges[f"{prefix}_max"])


# ---------------------------------------------------------------------------
# All Zones speedrun times
# ---------------------------------------------------------------------------

class TestSpeedrunTimes(CotNDTestBase):
    options = {"dlc": []}

    def _validate(self, times: dict) -> dict:
        self.world.options.all_zones_speedrun_times.value = times
        validate_speedrun_times(self.world.options)
        return times

    def test_raises_below_minimum(self) -> None:
        times = self._validate({"Cadence": 1, "Bard": 2})
        self.assertEqual(times["Cadence"], MIN_SPEEDRUN_MINUTES)
        self.assertEqual(times["Bard"], MIN_SPEEDRUN_MINUTES)

    def test_zero_stays_disabled(self) -> None:
        # Zero means untimed, so it is not a time to raise
        self.assertEqual(self._validate({"Cadence": 0})["Cadence"], 0)

    def test_valid_times_untouched(self) -> None:
        times = self._validate({"Cadence": 3, "Reaper": 8})
        self.assertEqual((times["Cadence"], times["Reaper"]), (3, 8))

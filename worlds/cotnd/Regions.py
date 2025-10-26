from typing import Dict, List

from .Options import CotNDOptions
from .Locations import  LocationDict, get_available_locations

cotnd_regions: Dict[str, List[str]] = {
    "Menu": ["Crypt"],
    "Crypt": [],
}

def get_regions_to_locations(options: CotNDOptions) -> dict[str, list[LocationDict]]:
    locations = get_available_locations(
        options.dlc.value,
        options.character_blacklist.value,
        [options.goal.value],
        options.included_extra_modes.value,
        bool(options.locked_lobby_npcs.value),
        bool(options.include_codex_checks.value),
        bool(options.per_level_zone_clears.value)
    )

    return {
        "Menu": [loc for loc in locations if "Shop" in loc["name"]],
        "Crypt": [loc for loc in locations if "Shop" not in loc["name"]],
    }
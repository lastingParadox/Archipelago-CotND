from typing import Dict, List

from worlds.cotnd.Locations import CotNDLocationData, LocationType

cotnd_regions: Dict[str, List[str]] = {
    "Menu": ["Crypt"],
    "Crypt": [],
}


def get_regions_to_locations(locations: List[CotNDLocationData]):
    return {
        "Menu": [loc for loc in locations if loc.type is LocationType.SHOP],
        "Crypt": [loc for loc in locations if loc.type is not LocationType.SHOP]
    }

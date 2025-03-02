from typing import Dict, List
from BaseClasses import Location
from .Options import CotNDOptions
from .Characters import base_chars, amplified_chars, synchrony_chars


class CotNDLocation(Location):
    game: str = "Crypt of the Necrodancer"


base_zone_clear_locations = [
    f"{char} - Zone {zone}" for char in base_chars for zone in range(1, 6)
]
amp_zone_clear_locations = [
    f"{char} - Zone {zone}" for char in amplified_chars for zone in range(1, 6)
]
sync_zone_clear_locations = [
    f"{char} - Zone {zone}" for char in synchrony_chars for zone in range(1, 6)
]

base_all_zones_clear_locations = [f"{char} - All Zones" for char in base_chars]
amp_all_zones_clear_locations = [f"{char} - All Zones" for char in amplified_chars]
sync_all_zones_clear_locations = [f"{char} - All Zones" for char in synchrony_chars]

zone_clear_locations = (
    base_zone_clear_locations + amp_zone_clear_locations + sync_zone_clear_locations
)
all_zones_clear_locations = (
    base_all_zones_clear_locations
    + amp_all_zones_clear_locations
    + sync_all_zones_clear_locations
)

hephaestus_locations = (
    [f"Hephaestus - Left Shop Item {i}" for i in range(1, 18)]
    + [f"Hephaestus - Center Shop Item {i}" for i in range(1, 33)]
    + [f"Hephaestus - Right Shop Item {i}" for i in range(1, 14)]
)

merlin_locations = (
    [f"Merlin - Left Shop Item {i}" for i in range(1, 6)]
    + [f"Merlin - Center Shop Item {i}" for i in range(1, 15)]
    + [f"Merlin - Right Shop Item {i}" for i in range(1, 14)]
)

dungeon_master_locations = (
    [f"Dungeon Master - Left Shop Item {i}" for i in range(1, 4)]
    + [f"Dungeon Master - Center Shop Item {i}" for i in range(1, 3)]
    + [f"Dungeon Master - Right Shop Item {i}" for i in range(1, 4)]
)

all_locations = (
    zone_clear_locations
    + hephaestus_locations
    + merlin_locations
    + dungeon_master_locations
)


def get_regions_to_locations(options: CotNDOptions):
    zone_locations = base_zone_clear_locations
    all_zones_locations = base_all_zones_clear_locations

    if "Amplified" in options.dlc.value:
        zone_locations += amp_zone_clear_locations
        all_zones_locations += amp_all_zones_clear_locations

    if "Synchrony" in options.dlc.value:
        zone_locations += sync_zone_clear_locations
        all_zones_locations += sync_all_zones_clear_locations

    return {
        "Menu": hephaestus_locations + merlin_locations + dungeon_master_locations,
        "Crypt": zone_locations + all_zones_locations,
    }

from typing import Any, Dict

from BaseClasses import ItemClassification, Region, Tutorial
from worlds.AutoWorld import World, WebWorld
from .Characters import get_available_characters
from .Items import (
    get_items_list,
    ItemDict,
    CotNDItem,
    get_all_items, get_default_items, get_filler_items,
)
from .Locations import (
    all_locations,
    CotNDLocation,
    hephaestus_locations,
    all_zones_clear_locations, get_regions_to_locations,
)
from .Options import CotNDOptions
from .Regions import cotnd_regions
from .Rules import set_rules

id_offset: int = 247000


class CotNDWeb(WebWorld):
    theme = "partyTime"

    guide_en = Tutorial(
        "Multiworld Setup Guide",
        "A guide to setting up the Crypt of the Necrodancer Archipelago Multiworld",
        "English",
        "setup_en.md",
        "setup/en",
        ["lastingParadox"],
    )

    tutorials = [guide_en]

    bug_report_page = "https://github.com/lastingParadox/Archipelago-CotND/issues"


class CotNDWorld(World):
    """
    Crypt of the NecroDancer is a roguelike rhythm game. Move to the beat in an ever-changing dungeon while fighting
    skeletons, dragons, and rapping moles. Descend into the crypt to defeat the NecroDancer and claim the Golden Lute!
    """

    game = "Crypt of the Necrodancer"
    web = CotNDWeb()
    options_dataclass = CotNDOptions
    options: CotNDOptions
    item_name_to_id = {item["name"]: i + id_offset for i, item in enumerate(get_all_items())}
    location_name_to_id = {
        location: i + id_offset for i, location in enumerate(all_locations)
    }

    item_name_groups = {}

    def generate_early(self) -> None:
        self.dlcs = set(self.options.dlc.value)
        self.items = get_items_list(self.options)
        self.chars = get_available_characters(self.items, self.options)

        for item in get_default_items(self.options.dlc, self.options.randomize_characters):
            self.multiworld.push_precollected(self.create_item(item))

        # Give starting characters
        temp_char_list = [item for item in self.items if item["type"] == "Character"]
        for _ in range(3):
            choice = self.multiworld.random.choice(temp_char_list)
            self.multiworld.push_precollected(self.create_item(choice))
            temp_char_list.remove(choice)
            self.items = [item for item in self.items if item["name"] != choice["name"]]

    def create_regions(self) -> None:
        regions = cotnd_regions
        for region_name in regions.keys():
            self.multiworld.regions.append(
                Region(region_name, self.player, self.multiworld)
            )

        regions_to_locations = get_regions_to_locations(self.options)

        for region_name, region_connections in regions.items():
            region = self.get_region(region_name)
            region.add_exits(region_connections)
            region.add_locations(
                {
                    location: (
                        self.location_name_to_id[location]
                        if location not in all_zones_clear_locations
                        else None
                    )
                    for location in regions_to_locations[region_name]
                },
                CotNDLocation,
            )

    def create_items(self) -> None:
        filler_items = get_filler_items()

        # Create victory event pairs
        for character in self.chars:
            self.get_location(f"{character['name']} - All Zones").place_locked_item(
                self.create_event(f"Complete")
            )

        while len(self.items) < len(self.multiworld.get_unfilled_locations(self.player)):
            self.items.append(self.multiworld.random.choice(filler_items))

        for item in self.items:
            self.multiworld.itempool.append(self.create_item(item))

    def create_item(self, item: ItemDict) -> CotNDItem:
        return CotNDItem(
            item["name"],
            item["classification"],
            self.item_name_to_id[item["name"]],
            self.player,
        )

    def create_event(self, event: str) -> CotNDItem:
        return CotNDItem(event, ItemClassification.progression, None, self.player)

    def set_rules(self) -> None:
        set_rules(self.multiworld, self.player, [item["name"] for item in self.chars])

    def fill_slot_data(self) -> Dict[str, Any]:
        return self.options.as_dict(
            "death_link",
            "dlc",
            "character_blacklist",
            "randomize_starting_items",
            "randomize_characters",
            "all_zones_goal_clear"
        )

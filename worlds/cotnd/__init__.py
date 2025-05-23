from typing import Any, Dict

from BaseClasses import ItemClassification, Region, Tutorial
from worlds.AutoWorld import World, WebWorld
from worlds.LauncherComponents import Component, components, Type, launch_subprocess
from .Characters import get_available_characters
from .Items import (
    get_items_list,
    all_items,
    ItemDict,
    CotNDItem, get_default_items, get_filler_items,
)
from .Locations import (
    CotNDLocation,
    get_regions_to_locations, get_available_locations, all_locations,
)
from .Options import CotNDOptions
from .Regions import cotnd_regions
from .Rules import set_rules


def launch_client():
    from .Client import launch
    launch_subprocess(launch, name="CotNDCLient")

components.append(Component("Crypt of the Necrodancer Client", "CotNDClient", func=launch_client, component_type=Type.CLIENT))

class CotNDWeb(WebWorld):
    theme = "partyTime"

    guide_en = Tutorial(
        "Multiworld Setup Guide",
        "A guide to setting up the Crypt of the NecroDancer Archipelago Multiworld",
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

    game = "Crypt of the NecroDancer"
    web = CotNDWeb()
    options_dataclass = CotNDOptions
    options: CotNDOptions
    item_name_to_id = {item['name']: item['code'] for item in all_items.values()}
    location_name_to_id = {location['name']: location['code'] for location in all_locations.values()}

    item_name_groups = {}

    def generate_early(self) -> None:
        self.dlcs = set(self.options.dlc.value)
        self.items = get_items_list(self.options.character_blacklist.value, self.options.dlc.value,
                                    self.options.randomize_characters.value, self.options.randomize_starting_items.value)
        self.chars = get_available_characters(self.items, self.options)
        self.locations = get_available_locations(self.options.dlc.value)

        # If starting items are randomized, we don't want to give the player default items.
        if not self.options.randomize_starting_items:
            for item in get_default_items(self.options.dlc, self.options.randomize_characters):
                self.multiworld.push_precollected(self.create_item(item['name']))

        # Give starting characters
        temp_char_list = [item for item in self.items if item["type"] == "Character" and item["name"] not in self.options.character_blacklist]
        for _ in range(3):
            choice = self.multiworld.random.choice(temp_char_list)
            self.multiworld.push_precollected(self.create_item(choice['name']))
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
                    location['name']: (
                        location['code']
                        if "All Zones" not in location['name']
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

        unfilled_locations = len(self.multiworld.get_unfilled_locations(self.player))

        while len(self.items) < unfilled_locations:
            self.items.append(self.multiworld.random.choice(filler_items))

        for item in self.items:
            self.multiworld.itempool.append(self.create_item(item['name']))

    def create_item(self, item: str) -> CotNDItem:

        item_dict = all_items[item]

        return CotNDItem(
            item_dict["name"],
            item_dict["classification"],
            item_dict["code"],
            self.player,
        )

    def create_event(self, event: str) -> CotNDItem:
        return CotNDItem(event, ItemClassification.progression, None, self.player)

    def set_rules(self) -> None:
        set_rules(self.multiworld, self.player, [location['name'] for location in self.locations], [item["name"] for item in self.chars], self.options.dlc.value, self.options.all_zones_goal_clear.value)

    def fill_slot_data(self) -> Dict[str, Any]:
        return self.options.as_dict(
            "death_link",
            "dlc",
            "character_blacklist",
            "randomize_starting_items",
            "randomize_characters",
            "all_zones_goal_clear"
        )

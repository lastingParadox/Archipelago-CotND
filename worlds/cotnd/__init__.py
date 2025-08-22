from typing import Any, Dict

from BaseClasses import ItemClassification, Region, Tutorial
from worlds.AutoWorld import World, WebWorld
from worlds.LauncherComponents import Component, components, Type, launch_subprocess, icon_paths
from .Characters import get_available_characters, get_all_characters
from .Items import (
    get_items_list,
    all_items,
    ItemDict,
    CotNDItem, get_default_items, get_filler_items, item_name_groups,
)
from .Locations import (
    CotNDLocation,
    get_regions_to_locations, get_available_locations, all_locations,
)
from .Options import CotNDOptions
from .Regions import cotnd_regions
from .Rules import set_rules


def ensure_min_max(self, min_name: str, max_name: str) -> None:
    min_val = getattr(self.options, min_name).value
    max_val = getattr(self.options, max_name).value

    if max_val < min_val:
        print(f"[WARNING] Swapping {min_name} ({min_val}) and {max_name} ({max_val}) to maintain proper bounds.")
        setattr(self.options, min_name, type(getattr(self.options, min_name))(max_val))
        setattr(self.options, max_name, type(getattr(self.options, max_name))(min_val))


def launch_client():
    from .Client import launch
    launch_subprocess(launch, name="CotNDClient")


icon_paths["cotnd_ico"] = f"ap:{__name__}/data/icon.png"
components.append(
    Component("Crypt of the NecroDancer Client", func=launch_client, component_type=Type.CLIENT, icon="cotnd_ico"))


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
    item_name_groups = item_name_groups
    topology_present = True

    dlcs = []
    chars = []
    items = []
    locations = []

    def generate_early(self) -> None:
        # Prepare items & locations
        self.dlcs = set(self.options.dlc.value)

        all_chars = get_all_characters(self.dlcs)
        # If blacklist contains all available characters, remove Cadence
        blacklist = set(self.options.character_blacklist.value)
        if set(all_chars).issubset(set(blacklist)):
            print("[WARNING] Removing Cadence from the blacklist to maintain progression.")
            blacklist = [c for c in blacklist if c != "Cadence"]
            self.options.character_blacklist.value = blacklist

        # Items & locations after blacklist adjustment
        self.items = get_items_list(
            blacklist,
            self.options.dlc.value,
            self.options.included_extra_modes.value
        )
        self.locations = get_available_locations(
            self.options.dlc.value,
            blacklist,
            self.options.included_extra_modes.value
        )

        # Available characters
        self.chars = get_available_characters(self.items, self.dlcs, blacklist)

        # Cap a value to available character count with a warning
        def cap_option(option_name: str):
            option = getattr(self.options, option_name)
            if option.value > len(self.chars):
                print(
                    f"[WARNING] Setting {option_name.replace('_', ' ')} to {len(self.chars)} to maintain progression.")
                option.value = len(self.chars)

        cap_option("starting_characters_amount")
        cap_option("all_zones_goal_clear")

        # Ensure price ranges are valid
        for prefix in ("randomized", "filler", "useful", "progression"):
            ensure_min_max(self, f"{prefix}_price_min", f"{prefix}_price_max")

        # Give default non-character items
        for item in get_default_items(self.options.dlc):
            self.multiworld.push_precollected(self.create_item(item['name']))

        # Give starting characters
        temp_char_list = [c for c in self.items if c["type"] == "Character" and c["name"] not in blacklist]
        for _ in range(self.options.starting_characters_amount.value):
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
                        if "Beat All Zones" not in location['name']
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
            self.get_location(f"{character['name']} - Beat All Zones").place_locked_item(
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
        set_rules(self.multiworld, self.player, [location['name'] for location in self.locations],
                  [item["name"] for item in self.chars], self.options.dlc.value,
                  self.options.all_zones_goal_clear.value)

    def fill_slot_data(self) -> Dict[str, Any]:
        return self.options.as_dict(
            "death_link",
            "dlc",
            "character_blacklist",
            "all_zones_goal_clear",
            "included_extra_modes",
            "price_randomization",
            "randomized_price_min",
            "randomized_price_max",
            "filler_price_min",
            "filler_price_max",
            "useful_price_min",
            "useful_price_max",
            "progression_price_min",
            "progression_price_max"
        )

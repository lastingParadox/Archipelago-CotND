from typing import Any, Dict, List

from BaseClasses import ItemClassification, Region, Tutorial, MultiWorld
from worlds.AutoWorld import World, WebWorld
from worlds.LauncherComponents import Component, components, Type, launch_subprocess, icon_paths
from .Characters import get_available_characters, get_all_characters
from .Items import (
    get_items_list,
    all_items,
    ItemDict,
    CotNDItem, get_default_items, get_filler_items, item_name_groups, from_id, get_shop_stock_unlocks,
)
from .Locations import (
    CotNDLocation,
    get_available_locations, all_locations, LOBBY_NPCS, get_shop_slot_lengths,
)
from .Options import CotNDOptions
from .Regions import cotnd_regions, get_regions_to_locations
from .Rules import set_rules
from .Validation import (
    validate_blacklist,
    validate_modes,
    validate_lobby_npcs,
    cap_option,
    validate_price_ranges,
    precollect_defaults, precollect_lobby_npcs,
)


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
    location_hint_codes = {}
    topology_present = True

    dlcs = []
    chars = []
    items = []
    locations = []
    caged_npc_locations = {}

    def assign_caged_npcs(self) -> Dict[str, Dict[str, Any]]:
        zones = [1, 2, 3, 4, 5] if "Amplified" in self.options.dlc.value else [1, 2, 3, 4]
        levels = [1, 2, 3]

        # Distribute zones as evenly as possible
        npc_zones = [zones[i % len(zones)] for i in range(len(LOBBY_NPCS))]
        self.random.shuffle(npc_zones)

        # Random levels
        npc_levels = [self.random.choice(levels) for _ in LOBBY_NPCS]

        # Ensure each unlockType is used at least once
        unlock_types = ["Shop", "Dig", "Glass"]
        remaining = len(LOBBY_NPCS) - len(unlock_types)

        # Fill remaining with weighted random choices
        weighted_choices = self.random.choices(
            ["Shop", "Dig", "Glass"],
            weights=[0.6, 0.3, 0.1],
            k=remaining
        )

        # Combine guaranteed + random
        all_unlocks = unlock_types + weighted_choices
        self.random.shuffle(all_unlocks)

        # Adjust levels so Glass is only on 2 or 3
        adjusted_levels = []
        for level, unlock in zip(npc_levels, all_unlocks):
            if unlock == "Glass" and level == 1:
                level = self.random.choice([2, 3])
            adjusted_levels.append(level)

        return {
            npc: {
                "zone": zone,
                "level": level,
                "unlockType": unlock_type
            }
            for npc, zone, level, unlock_type in zip(LOBBY_NPCS, npc_zones, adjusted_levels, all_unlocks)
        }

    def generate_early(self) -> None:
        # Prepare items & locations
        self.dlcs = set(self.options.dlc.value)

        blacklist = validate_blacklist(self.options, self.dlcs)
        included_modes = validate_modes(self.options, self.dlcs)
        validate_lobby_npcs(self.options)

        # Items & locations after blacklist adjustment
        self.items = get_items_list(
            blacklist,
            self.options.dlc.value,
            self.options.included_extra_modes.value,
            bool(self.options.lobby_npc_items.value)
        )
        self.locations = get_available_locations(
            self.options.dlc.value,
            blacklist,
            [self.options.goal.value],
            self.options.included_extra_modes.value,
            bool(self.options.locked_lobby_npcs.value),
            bool(self.options.per_level_zone_clears.value)
        )

        # Logic for adding more shop unlocks based on shop locations available
        # This should probably be moved
        slot_lengths = get_shop_slot_lengths(self.options.dlc.value)
        min_slot_rows = min(slot_lengths.values()) if slot_lengths else 0

        unlocks = get_shop_stock_unlocks(min_slot_rows)
        self.items.extend(unlocks)

        # Available characters
        self.chars = get_available_characters(self.items, self.dlcs, blacklist)

        # Cap certain values
        cap_option(self.options, "starting_characters_amount", len(self.chars))
        cap_option(self.options, "all_zones_goal_clear", len(self.chars))
        cap_option(self.options, "zones_goal_clear",
                   len(self.chars) * (5 if "Amplified" in self.options.dlc.value else 4))

        # Ensure price ranges are valid
        validate_price_ranges(self.options)

        # Precollect defaults
        precollect_defaults(self, self.options)
        if not bool(self.options.locked_lobby_npcs.value):
            precollect_lobby_npcs(self)

        # Give starting characters
        temp_char_list = [c for c in self.items if c["type"] == "Character" and c["name"] not in blacklist]
        for _ in range(self.options.starting_characters_amount.value):
            choice = self.multiworld.random.choice(temp_char_list)
            self.multiworld.push_precollected(self.create_item(choice['name']))
            temp_char_list.remove(choice)
            self.items = [item for item in self.items if item["name"] != choice["name"]]

        # Randomize Lobby NPC placement
        if bool(self.options.locked_lobby_npcs.value):
            self.caged_npc_locations = self.assign_caged_npcs()

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
                        if "Beat" not in location["name"]
                        else None
                    )
                    for location in regions_to_locations[region_name]
                },
                CotNDLocation,
            )

    def create_items(self) -> None:
        # Create victory event pairs
        for character in self.chars:
            if self.options.goal.value == 0:
                self.get_location(f"{character['name']} - Beat All Zones").place_locked_item(
                    self.create_event(f"Complete")
                )
            elif self.options.goal.value == 1:
                for i in range(1, 6 if "Amplified" in self.options.dlc.value else 5):
                    self.get_location(f"{character['name']} - Beat Zone {i}").place_locked_item(
                        self.create_event(f"Complete"))

        # Lock Lobby NPC items to locations
        if self.options.locked_lobby_npcs and not self.options.lobby_npc_items:
            for npc in LOBBY_NPCS:
                self.get_location(f"Caged {npc}").place_locked_item(self.create_item(npc))

        unfilled_locations = len(self.multiworld.get_unfilled_locations(self.player))
        needed_filler = unfilled_locations - len(self.items)

        filler_items = get_filler_items(self, needed_filler)

        self.items.extend(filler_items)

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

        goal_clear_req = self.options.all_zones_goal_clear.value if self.options.goal.value == 0 \
            else self.options.zones_goal_clear.value

        set_rules(self.multiworld, self.player, [location['name'] for location in self.locations],
                  [item["name"] for item in self.chars], self.options.dlc.value,
                  goal_clear_req, bool(self.options.locked_lobby_npcs.value), )

    def post_fill(self):
        hints = self.location_hint_codes[self.player_name] = {
            "Character": [], "Armor": [], "Weapon": [], "Upgrade": []
        }

        for sphere in self.multiworld.get_spheres():
            for location in sphere:
                item = location.item
                if item.game != "Crypt of the NecroDancer" or item.player != self.player or item.code is None:
                    continue

                item_type = from_id(item.code)["type"]
                if item_type in hints:
                    hints[item_type].append(location.address)
                elif item_type in {"Head", "Feet"}:
                    hints["Armor"].append(location.address)

    def fill_slot_data(self) -> Dict[str, Any]:
        fill = self.options.as_dict(
            "death_link",
            "dlc",
            "goal",
            "per_level_zone_clears",
            "character_blacklist",
            "all_zones_goal_clear",
            "zones_goal_clear",
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

        fill["caged_npc_locations"] = self.caged_npc_locations
        fill["location_hint_codes"] = self.location_hint_codes[self.player_name]

        return fill

    @classmethod
    def stage_write_spoiler(cls, multiworld: MultiWorld, spoiler_handle):
        cotnd_players = multiworld.get_game_players(cls.game)
        spoiler_handle.write("\n\nLocked NPC Locations:")
        for player in cotnd_players:
            name = multiworld.get_player_name(player)
            spoiler_handle.write(f"\n{name}\n")
            cotnd_world: CotNDWorld = multiworld.worlds[player]
            max_len = max(len(npc) for npc in cotnd_world.caged_npc_locations)

            for npc, location in cotnd_world.caged_npc_locations.items():
                spoiler_handle.write(
                    f"\n{npc}:{' ' * (max_len - len(npc) + 1)}"
                    f"Zone {location['zone']}-{location['level']}, Unlocked by: {location['unlockType']}"
                )

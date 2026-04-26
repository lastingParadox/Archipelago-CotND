import json
import os
import pkgutil
from copy import copy
from typing import Mapping, Any, cast

from BaseClasses import Tutorial, Region, ItemClassification, MultiWorld
from worlds.AutoWorld import WebWorld, World
from worlds.LauncherComponents import (
    launch_subprocess,
    icon_paths,
    components,
    Component,
    Type,
)
from worlds.cotnd.Characters import get_available_characters
from worlds.cotnd.Items import (
    all_items,
    item_name_groups,
    get_shop_stock_unlocks,
    get_filler_items,
    CotNDItem,
    ItemType,
    CotNDItemData,
    build_master_world_items,
    filter_population_list,
)
from worlds.cotnd.Locations import (
    all_locations,
    location_name_groups,
    get_locations_list,
    get_last_shop_item_row,
    LocationType,
    CotNDLocation,
    CotNDLocationData,
)
from worlds.cotnd.Options import CotNDOptions
from worlds.cotnd.Regions import cotnd_regions, get_regions_to_locations
from worlds.cotnd.Rules import set_rules
from worlds.cotnd.Utils import assign_caged_npcs, LOBBY_NPCS
from worlds.cotnd.Validation import (
    validate_blacklist,
    validate_modes,
    cap_option,
    validate_price_ranges,
    validate_starting_zone,
    validate_death_link_type,
    collect_starting_pool,
    validate_starting_character,
    collect_starting_character,
)


def launch_client():
    from .Client import launch

    launch_subprocess(launch, name="CotNDClient")


icon_paths["cotnd_ico"] = f"ap:{__name__}/data/icon.png"
components.append(
    Component(
        "Crypt of the NecroDancer Client",
        func=launch_client,
        component_type=Type.CLIENT,
        icon="cotnd_ico",
    )
)


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

    _archipelago_json_data = pkgutil.get_data(__name__, "archipelago.json")
    apworld_version: str = json.loads(_archipelago_json_data).get("world_version", "0.0.0")

    game = "Crypt of the NecroDancer"
    options_dataclass = CotNDOptions
    options: CotNDOptions  # pyright: ignore[reportIncompatibleVariableOverride]
    web = CotNDWeb()
    required_client_version = (0, 6, 1)
    item_name_groups = item_name_groups
    location_name_groups = location_name_groups
    topology_present = True

    item_name_to_id = {item.name: item.code for item in all_items}
    location_name_to_id = {
        location.name: location.code for location in all_locations if location.code is not None
    }

    dlcs: set[str] = set()
    chars: list[CotNDItemData] = []
    world_item_list: list[CotNDItemData] = []
    item_from_name: dict[str, CotNDItemData] = {}
    item_from_code: dict[int, CotNDItemData] = {}
    items: list[CotNDItemData] = []
    locations: list[CotNDLocationData] = []
    caged_npc_locations: dict[str, dict[str, Any]] = {}
    starting_zone: int = 1
    starting_character_name: str = ""

    def generate_early(self):
        self.dlcs = set([item.lower() for item in self.options.dlc.value])

        blacklist = validate_blacklist(self.options, self.dlcs)
        included_modes = validate_modes(self.options, self.dlcs)
        validate_death_link_type(self.options, self.dlcs)

        (self.world_item_list, self.item_from_name, self.item_from_code) = (
            build_master_world_items(
                blacklist,
                self.dlcs,
                included_modes,
                bool(self.options.include_unique_items),
                self.options.character_unlocks.current_key,
            )
        )
        self.items = filter_population_list(self.world_item_list)

        # Determine zone key precollection early so we can remove them BEFORE location generation
        zone_key_mode = self.options.zone_access_keys.current_key
        max_zone = 5 if "amplified" in self.dlcs else 4
        starting_zone = min(self.options.starting_zone.value, max_zone)
        self.starting_zone = starting_zone
        
        # Precollect starting zone keys NOW (before location generation)
        if zone_key_mode != "disabled":
            if zone_key_mode == "separate":
                self.multiworld.push_precollected(
                    self.create_item(f"Zone {starting_zone} Access")
                )
            else:  # progressive
                precollect_count = max(0, starting_zone - 1)
                for _ in range(precollect_count):
                    self.multiworld.push_precollected(
                        self.create_item("Progressive Zone Access")
                    )

        # Add zone access keys to item pool for location generation count
        # Add ALL copies so location generation counts them properly
        zone_key_items = []
        if zone_key_mode != "disabled":
            if zone_key_mode == "separate":
                for zone in range(1, max_zone + 1):
                    zone_key_items.append(self.item_from_name[f"Zone {zone} Access"])
            else:  # progressive
                # One progressive key unlocks one zone step (Zone 1->2, ..., max_zone-1->max_zone)
                for _ in range(max(0, max_zone - 1)):
                    zone_key_items.append(self.item_from_name["Progressive Zone Access"])
        
        if self.options.lock_character_room:
            zone_key_items.append(self.item_from_name["Character Room Key"])
        
        self.items.extend(zone_key_items)

        self.locations = get_locations_list(
            self.items,
            self.dlcs,
            blacklist,
            self.options.goal.value,
            included_modes,
            bool(self.options.include_codex_checks.value),
            bool(self.options.floor_clear_checks.value),
        )

        # NOW remove the precollected zone keys from the pool (after location generation)
        # This way fill algorithm gets the right number of items to place
        if zone_key_mode == "separate":
            # Remove the starting zone's access key (it was precollected)
            self.items = [item for item in self.items if not (item.name == f"Zone {starting_zone} Access")]
        elif zone_key_mode == "progressive":
            # Remove precollected copies of Progressive Zone Access
            # Count how many to remove based on name alone (avoiding object identity issues)
            count_to_remove = max(0, starting_zone - 1)
            kept_items = []
            removed_count = 0
            for item in self.items:
                if item.name == "Progressive Zone Access" and removed_count < count_to_remove:
                    removed_count += 1
                else:
                    kept_items.append(item)
            self.items = kept_items

        shop_index = get_last_shop_item_row(self.locations)
        self.items = get_shop_stock_unlocks(self.items, shop_index)

        self.chars = get_available_characters(blacklist, self.dlcs)

        # Cap certain values
        cap_option(self.options, "all_zones_goal_clear", len(self.chars))
        cap_option(
            self.options,
            "zones_goal_clear",
            len(self.chars) * (5 if "amplified" in self.options.dlc.value else 4),
        )

        validate_price_ranges(self.options)
        validate_starting_zone(self.options, self.dlcs)

        self.items = collect_starting_pool(
            self,
            self.items,
            self.options.starting_inventory.value,
            bool(self.options.include_materials.value),
        )

        # Give starting characters
        self.items, self.starting_character_name = collect_starting_character(
            self,
            self.items,
            self.options.starting_character.current_option_name,
            self.options.character_unlocks.value,
        )

        # Character Room Key should already be in pool if enabled; no further action needed

        # Randomize Lobby NPC placement
        self.caged_npc_locations = assign_caged_npcs(self.random, self.dlcs)

    def create_regions(self):
        regions = cotnd_regions
        for region_name in regions.keys():
            self.multiworld.regions.append(
                Region(region_name, self.player, self.multiworld)
            )

        regions_to_loc = get_regions_to_locations(self.locations)

        for region_name, region_connections in regions.items():
            region = self.get_region(region_name)
            region.add_exits(region_connections)
            region.add_locations(
                {
                    location.name: location.code
                    for location in regions_to_loc[region_name]
                },
                CotNDLocation,
            )

    def create_items(self):
        for character in self.chars:
            if self.options.goal == "all_zones":
                self.get_location(
                    f"{character.name} - Beat All Zones"
                ).place_locked_item(self.create_event("Complete"))
            elif self.options.goal == "zones":
                for i in range(1, 6 if "amplified" in self.dlcs else 5):
                    self.get_location(
                        f"{character.name} - Beat Zone {i}"
                    ).place_locked_item(self.create_event("Complete"))

        # Lock Lobby NPC items to locations
        if not self.options.lobby_npc_items:
            locked_npcs = set(LOBBY_NPCS)
            # Remove NPCs that are being hard-locked so they are not also shuffled in the item pool.
            self.items = [item for item in self.items if item.name not in locked_npcs]
            for npc in LOBBY_NPCS:
                item = self.item_from_name[npc]
                self.get_location(f"Caged {npc}").place_locked_item(
                    self.create_item(item.name)
                )

        unfilled_locations = len(self.multiworld.get_unfilled_locations(self.player))
        needed_filler = unfilled_locations - len(self.items)

        filler_items = get_filler_items(self, needed_filler)

        self.items.extend(filler_items)

        for item in self.items:
            self.multiworld.itempool.append(self.create_item(item.name))

    def create_item(self, name: str):
        item = self.item_from_name[name]
        return CotNDItem(item.name, item.classification, item.code, self.player)

    def create_event(self, event: str):
        return CotNDItem(event, ItemClassification.progression, None, self.player)

    def set_rules(self) -> None:
        goal_clear_req = (
            self.options.all_zones_goal_clear.value
            if self.options.goal == "all_zones"
            else self.options.zones_goal_clear.value
        )

        set_rules(
            self.multiworld,
            self.player,
            self.locations,
            self.item_from_name,
            goal_clear_req,
            self.options.character_unlocks.current_key,
            bool(self.options.include_unique_items.value),
            zone_access_keys=self.options.zone_access_keys.current_key,
            starting_zone=self.starting_zone,
            lock_character_room=bool(self.options.lock_character_room.value),
            starting_character=self.starting_character_name,
            caged_npc_locations=self.caged_npc_locations,
        )

    def fill_slot_data(self) -> Mapping[str, Any]:
        fill = self.options.as_dict(
            "death_link",
            "death_link_type",
            "dlc",
            "goal",
            "floor_clear_checks",
            "character_blacklist",
            "character_unlocks",
            "include_unique_items",
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
            "progression_price_max",
            "zone_access_keys",
            "lock_character_room",
            "include_materials",
            "trap_weights",
            "trap_link"
        )

        # fill["item_by_code"] = self.item_from_code
        fill["caged_npc_locations"] = self.caged_npc_locations
        fill["starting_zone"] = self.starting_zone
        fill["starting_character"] = self.starting_character_name
        fill["world_version"] = self.apworld_version

        return fill

    @classmethod
    def stage_write_spoiler(cls, multiworld: MultiWorld, spoiler_handle):
        cotnd_players = multiworld.get_game_players(cls.game)
        spoiler_handle.write("\n\nLocked NPC Locations:")
        for player in cotnd_players:
            name = multiworld.get_player_name(player)
            cotnd_world = cast(CotNDWorld, multiworld.worlds[player])
            spoiler_handle.write(f"\n{name}\n")
            max_len = max(len(npc) for npc in cotnd_world.caged_npc_locations)

            for npc, location in cotnd_world.caged_npc_locations.items():
                spoiler_handle.write(
                    f"\n{npc}:{' ' * (max_len - len(npc) + 1)}"
                    f"Zone {location['zone']}-{location['level']}, Unlocked by: {location['unlockType']}"
                )

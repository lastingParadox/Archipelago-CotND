import json
import pkgutil
from typing import Any, Mapping, cast

from BaseClasses import MultiWorld, Tutorial
from worlds.AutoWorld import WebWorld, World
from worlds.LauncherComponents import launch_subprocess, icon_paths, components, Component, Type
from worlds.cotnd.Items import (ALL_ITEMS, ITEM_NAME_GROUPS, ITEM_NAME_TO_ID, CotNDItem, ItemType,
                                character_requirement_ids, create_multiworld_items,
                                get_random_filler_item_name)
from worlds.cotnd.Locations import (LOCATION_NAME_GROUPS, LOCATION_NAME_TO_ID, ZONE_PROGRESS_FLOORS,
                                    create_all_locations, story_boss_keys)
from worlds.cotnd.Options import CotNDOptions, cotnd_option_groups
from worlds.cotnd.Regions import LOBBY_REGION, create_and_connect_regions
from worlds.cotnd.Rules import set_all_rules
from worlds.cotnd.Utils import assign_caged_npcs, owned_dlc
from worlds.cotnd.Validation import validate_options


def launch_client():
    from .Client import launch

    launch_subprocess(launch, name="CotNDClient")

icon_paths["cotnd_ico"] = f"ap:{__name__}/data/icon.png"
components.append(Component("Crypt of the NecroDancer Client", func=launch_client, component_type=Type.CLIENT, icon="cotnd_ico"))

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

    option_groups = cotnd_option_groups

class CotNDWorld(World):
    """
    Crypt of the NecroDancer is a roguelike rhythm game. Move to the beat in an ever-changing dungeon while fighting
    skeletons, dragons, and rapping moles. Descend into the crypt to defeat the NecroDancer and claim the Golden Lute!
    """

    apworld_version: str = json.loads(pkgutil.get_data(__name__, "archipelago.json") or "").get("world_version", "0.0.0")

    game = "Crypt of the NecroDancer"
    options_dataclass = CotNDOptions
    options: CotNDOptions # pyright: ignore[reportIncompatibleVariableOverride]
    web = CotNDWeb()
    required_client_version = (0, 6, 1)
    item_name_groups = ITEM_NAME_GROUPS
    location_name_groups = LOCATION_NAME_GROUPS
    topology_present = True

    item_name_to_id = ITEM_NAME_TO_ID
    location_name_to_id = LOCATION_NAME_TO_ID

    origin_region_name = LOBBY_REGION
    item_class = CotNDItem

    def __init__(self, multiworld: MultiWorld, player: int):
        super().__init__(multiworld, player)
        self.caged_npcs: dict[str, dict[str, Any]] = {}
        # Where each NPC's unlock item ended up, by cotnd_id. Filled in fill_slot_data.
        self.npc_hint_locations: dict[str, dict[str, Any]] = {}
        self.item_room: list[dict[str, str]] = []

    def generate_early(self) -> None:
        validate_options(self)
        self.caged_npcs = assign_caged_npcs(self.random, owned_dlc(self))

    def create_regions(self) -> None:
        create_and_connect_regions(self)
        create_all_locations(self)

    def create_items(self) -> None:
        create_multiworld_items(self)

    def set_rules(self) -> None:
        set_all_rules(self)

    def create_item(self, name: str) -> CotNDItem:
        item = ALL_ITEMS.get_by_name(name)
        return CotNDItem(name, item.classification, item.code, self.player)

    def get_filler_item_name(self) -> str:
        return get_random_filler_item_name(self)

    def record_npc_hint_locations(self) -> None:
        # Record where each lobby NPC's unlock ended up, so the mod can hint it.
        self.npc_hint_locations = npc_hints = {}

        for location in self.multiworld.get_filled_locations():
            item = location.item

            if (item is None or item.game != self.game or item.player != self.player
                    or item.code is None or location.address is None):
                continue

            data = ALL_ITEMS.get_by_code(item.code)

            if data.type is ItemType.NPC:
                npc_hints[data.cotnd_id] = {
                    "LocationCode": location.address,
                    "LocationName": location.name,
                    "PlayerName": self.multiworld.get_player_name(location.player),
                    "PlayerSlot": location.player,
                }

    def goal_required(self) -> int:
        # How many of the goal's completions the mod should require.
        goal = self.options.goal.current_key

        if goal == "all_zones":
            return self.options.all_zones_goal_clear.value
        if goal == "golden_lute_shards":
            return self.options.golden_lute_shards_goal_clear.value
        if goal == "story":
            return len(story_boss_keys(owned_dlc(self)))

        return self.options.zones_goal_clear.value

    def fill_slot_data(self) -> Mapping[str, Any]:
        options = self.options

        self.record_npc_hint_locations()

        fill = options.as_dict(
            "dlc",
            "character_blacklist",
            "included_extra_modes",
            "include_unique_items",
            "include_materials",
            "include_shrine_checks",
            "include_codex_checks",
            "include_flawless_chest_checks",
            "items_per_zone",
            "item_generation_chance",
            "lock_character_room",
            "buff_items",
            "starting_zone",
            "expensive_purchase_price",
            "diamond_exchange_rate",
            "price_ranges",
            "death_link",
            "trap_link",
            "trap_weights",
            "traplink_excluded_traps",
            toggles_as_bools=True,
        )

        # Resolved here so the mod holds no second copy of who needs what.
        fill["character_requirements"] = character_requirement_ids(self)

        # -1 means "no speedrun target", which the mod reads as absent rather than a time.
        fill["all_zones_speedrun_times"] = {
            character: minutes
            for character, minutes in options.all_zones_speedrun_times.value.items()
            if minutes > 0
        }

        # The resolved floors, not the count, so the mod only does a membership test.
        fill["zone_progress_floors"] = list(ZONE_PROGRESS_FLOORS[options.zone_progress_checks.value])

        fill["goal"] = options.goal.current_option_name
        fill["goal_required"] = self.goal_required()
        fill["victory_trigger"] = options.victory_trigger.current_key
        fill["death_link_type"] = options.death_link_type.current_option_name
        fill["death_link_trigger"] = options.death_link_trigger.current_option_name
        fill["zone_access_keys"] = options.zone_access_keys.current_key
        # Read by the mod's character selector to decide which characters need their kit.
        fill["character_unlocks"] = options.character_unlocks.current_key
        fill["starting_character"] = options.starting_character.current_option_name
        fill["price_randomization"] = options.price_randomization.current_option_name

        fill["caged_npc_locations"] = self.caged_npcs
        fill["npc_hint_locations"] = self.npc_hint_locations
        fill["item_room"] = self.item_room
        fill["world_version"] = self.apworld_version

        return fill

    def interpret_slot_data(self, slot_data: Mapping[str, Any]) -> None:
        caged_npcs = slot_data.get("caged_npc_locations")
        if caged_npcs:
            self.caged_npcs = dict(caged_npcs)

        starting_character = slot_data.get("starting_character")
        if starting_character:
            key = starting_character.lower().replace(" ", "_")
            self.options.starting_character.value = self.options.starting_character.options[key]

        set_all_rules(self)

    @classmethod
    def stage_write_spoiler(cls, multiworld: MultiWorld, spoiler_handle) -> None:
        spoiler_handle.write("\n\nLocked NPC Locations:")

        for player in multiworld.get_game_players(cls.game):
            world = cast(CotNDWorld, multiworld.worlds[player])
            spoiler_handle.write(f"\n{multiworld.get_player_name(player)}\n")

            if not world.caged_npcs:
                continue

            width = max(len(npc) for npc in world.caged_npcs)

            for npc, placement in world.caged_npcs.items():
                spoiler_handle.write(
                    f"\n{npc}:{' ' * (width - len(npc) + 1)}"
                    f"Zone {placement['zone']}-{placement['level']}, "
                    f"Unlocked by: {placement['unlockType']}"
                )

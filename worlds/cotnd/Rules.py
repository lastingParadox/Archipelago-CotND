from typing import List, Dict

from BaseClasses import MultiWorld
from worlds.cotnd.Items import DefaultType, CotNDItemData
from worlds.cotnd.Locations import CotNDLocationData, LocationType
from worlds.generic.Rules import set_rule, add_rule
from worlds.cotnd.Utils import character_requirements


def set_soft_shop_rules(world: MultiWorld, player: int, location: CotNDLocationData):
    if location.type is not LocationType.SHOP:
        return

    loc = world.get_location(location.name, player)

    # Extract shopkeeper and index
    shopkeeper, rest = location.name.split(" - ", 1)
    index = int(rest.split(" Shop Item ")[1])

    # Base rule: stock unlocks for index > 1
    if index != 1:
        set_rule(loc, lambda state, req=index - 1: state.has("Shop Stock Unlock", player, req))

    # Merlin-specific rule
    if shopkeeper == "Merlin":
        add_rule(loc, lambda state: state.has("Merlin", player))


def set_rules(world: MultiWorld, player: int, locations: List[CotNDLocationData],
              item_from_name: Dict[str, CotNDItemData], goal_clear_req: int,
              character_unlocks: str, include_unique: bool):
    for location in locations:
        loc = world.get_location(location.name, player)
        # Character Locations
        if location.type in (
                LocationType.FLOOR, LocationType.BOSS, LocationType.UNIQUE_BOSS, LocationType.ZONE,
                LocationType.ALL_ZONES, LocationType.ALL_ZONES_EVENT, LocationType.ZONES_EVENT):
            set_rule(loc, lambda state, c=location.character: state.has(c, player))

            if character_unlocks != "item_only" and location.character in character_requirements:
                for requirement in character_requirements[location.character]:
                    item = item_from_name[requirement]
                    if item.default is not DefaultType.UNIQUE or include_unique:
                        add_rule(loc, lambda state, i=item: state.has(i.name, player))
            continue

        if location.type is LocationType.EXTRA_MODE:
            mode = location.name.split(" - ")[1]
            set_rule(loc, lambda state, c=location.character, m=mode: state.has(c, player) and state.has(m, player))
            continue

        if location.type is LocationType.SHOP:
            set_soft_shop_rules(world, player, location)
            continue

        if location.type is LocationType.TUTORIAL:
            set_rule(loc, lambda state: state.has("Codex", player))

    world.completion_condition[player] = (lambda state: state.has("Complete", player, goal_clear_req))

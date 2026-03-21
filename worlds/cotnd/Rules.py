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
        set_rule(
            loc,
            lambda state, req=index - 1: state.has("Shop Stock Unlock", player, req),
        )

    # Merlin-specific rule
    if shopkeeper == "Merlin":
        add_rule(loc, lambda state: state.has("Merlin", player))


def set_rules(
    world: MultiWorld,
    player: int,
    locations: List[CotNDLocationData],
    item_from_name: Dict[str, CotNDItemData],
    goal_clear_req: int,
    character_unlocks: str,
    include_unique: bool,
    zone_access_keys: str = "disabled",
    starting_zone: int = 1,
    lock_character_room: bool = False,
    starting_character: str = "",
    caged_npc_locations: dict = None,
):
    max_zone = max((location.zone or 0) for location in locations)

    all_zones_types = (LocationType.ALL_ZONES, LocationType.ALL_ZONES_EVENT)

    def has_zone_access(state, zone: int, character: str | None = None) -> bool:
        if zone_access_keys == "separate":
            return state.has(f"Zone {zone} Access", player)
        if zone_access_keys == "progressive":
            if character == "Aria":
                # Aria clears zones in reverse order (high -> low).
                required = max(0, max_zone - zone)
            else:
                required = max(0, zone - 1)
            return state.has("Progressive Zone Access", player, required)
        return True

    def zone_requires_key(zone: int, character: str | None = None) -> bool:
        if zone_access_keys == "disabled":
            return False
        if zone_access_keys == "separate":
            return zone != starting_zone
        if character == "Aria":
            # Keep Starting Zone semantics by mirroring Aria's reverse route.
            aria_start_zone = max_zone - starting_zone + 1
            return zone < aria_start_zone
        return zone > starting_zone

    def add_zone_gate_rule(loc, zone: int, character: str | None = None):
        if zone_requires_key(zone, character):
            add_rule(loc, lambda state, z=zone, c=character: has_zone_access(state, z, c))

    def add_full_zone_access_rule(loc):
        if zone_access_keys == "separate":
            add_rule(
                loc,
                lambda state, mz=max_zone: all(
                    state.has(f"Zone {z} Access", player) for z in range(1, mz + 1)
                ),
            )
        elif zone_access_keys == "progressive":
            add_rule(
                loc,
                lambda state, req=max(0, max_zone - 1): state.has(
                    "Progressive Zone Access", player, req
                ),
            )

    for location in locations:
        loc = world.get_location(location.name, player)
        # Character Locations
        if location.type in (
            LocationType.FLOOR,
            LocationType.BOSS,
            LocationType.UNIQUE_BOSS,
            LocationType.ZONE,
            LocationType.ALL_ZONES,
            LocationType.ALL_ZONES_EVENT,
            LocationType.ZONES_EVENT,
        ):
            set_rule(loc, lambda state, c=location.character: state.has(c, player))

            if (
                character_unlocks != "item_only"
                and location.character in character_requirements
            ):
                for requirement in character_requirements[location.character]:
                    if requirement in item_from_name:
                        item = item_from_name[requirement]
                        if item.default is not DefaultType.UNIQUE or include_unique:
                            add_rule(loc, lambda state, i=item: state.has(i.name, player))
            continue

        if location.type is LocationType.EXTRA_MODE:
            mode = location.name.split(" - ")[1]
            set_rule(
                loc,
                lambda state, c=location.character, m=mode: state.has(c, player)
                and state.has(m, player),
            )
            continue

        if location.type is LocationType.SHOP:
            set_soft_shop_rules(world, player, location)
            continue

        if location.type is LocationType.TUTORIAL:
            set_rule(loc, lambda state: state.has("Codex", player))

    # All Zones checks require full zone access progression when zone keys are enabled.
    for location in locations:
        if location.type in all_zones_types:
            add_full_zone_access_rule(world.get_location(location.name, player))

    # Zone Access Key rules: gate each zone behind its own key item
    for location in locations:
        if location.zone is not None:
            add_zone_gate_rule(
                world.get_location(location.name, player),
                location.zone,
                location.character,
            )

    # Character Room Key rules: gate all non-starting characters behind the key
    if lock_character_room and starting_character:
        for location in locations:
            if location.character is None or location.character == starting_character:
                continue
            if location.type in (
                LocationType.SHOP,
                LocationType.TUTORIAL,
                LocationType.NPC,
            ):
                continue
            loc = world.get_location(location.name, player)
            add_rule(loc, lambda state: state.has("Character Room Key", player))

    # Caged NPC locations need zone access to the zone they're physically in
    if caged_npc_locations and zone_access_keys != "disabled":
        for npc_name, npc_info in caged_npc_locations.items():
            npc_zone = npc_info.get("zone")
            if npc_zone:
                loc_name = f"Caged {npc_name}"
                try:
                    loc = world.get_location(loc_name, player)
                    add_zone_gate_rule(loc, npc_zone)
                except KeyError:
                    pass  # Location doesn't exist (might be filtered out)

    world.completion_condition[player] = lambda state: state.has(
        "Complete", player, goal_clear_req
    )

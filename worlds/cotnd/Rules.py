from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, ClassVar

from BaseClasses import CollectionState
from rule_builder.rules import Has, HasAll, Rule, True_
from worlds.cotnd.Items import DefaultType
from worlds.cotnd.Locations import LocationType
from worlds.cotnd.Utils import character_requirements

if TYPE_CHECKING:
    from worlds.cotnd import CotNDWorld


@dataclasses.dataclass()
class ZoneGate(Rule["CotNDWorld"], game="Crypt of the NecroDancer"):
    """Gates a location to a specific zone based on the zone_access_keys option."""

    zone: int
    character: str | None = None

    def _instantiate(self, world: CotNDWorld) -> Rule.Resolved:
        zone_access_keys = world.options.zone_access_keys.current_key
        starting_zone = world.starting_zone
        max_zone = max((loc.zone or 0) for loc in world.locations)

        if zone_access_keys == "disabled":
            return True_().resolve(world)

        if zone_access_keys == "separate":
            if self.zone == starting_zone:
                return True_().resolve(world)
            return Has(f"Zone {self.zone} Access").resolve(world)

        # progressive
        if self.character == "Aria":
            # Aria clears zones in reverse order (high -> low).
            aria_start_zone = max_zone - starting_zone + 1
            if self.zone >= aria_start_zone:
                return True_().resolve(world)
            required = max(0, max_zone - self.zone)
        else:
            if self.zone <= starting_zone:
                return True_().resolve(world)
            required = max(0, self.zone - 1)

        if required == 0:
            return True_().resolve(world)
        return Has("Progressive Zone Access", required).resolve(world)

    class Resolved(Rule.Resolved):
        skip_cache: ClassVar[bool] = True

        def _evaluate(self, state: CollectionState) -> bool:
            return False  # Never reached; _instantiate always delegates to another rule


@dataclasses.dataclass()
class FullZoneAccess(Rule["CotNDWorld"], game="Crypt of the NecroDancer"):
    """Requires access to all zones (used for All Zones completion locations)."""

    def _instantiate(self, world: CotNDWorld) -> Rule.Resolved:
        zone_access_keys = world.options.zone_access_keys.current_key
        if zone_access_keys == "disabled":
            return True_().resolve(world)
        max_zone = max((loc.zone or 0) for loc in world.locations)
        if zone_access_keys == "separate":
            return HasAll(*(f"Zone {z} Access" for z in range(1, max_zone + 1))).resolve(world)
        # progressive: need max_zone - 1 keys to unlock all zones
        return Has("Progressive Zone Access", max(0, max_zone - 1)).resolve(world)

    class Resolved(Rule.Resolved):
        skip_cache: ClassVar[bool] = True

        def _evaluate(self, state: CollectionState) -> bool:
            return False  # Never reached; _instantiate always delegates to another rule


def set_rules(world: CotNDWorld) -> None:
    zone_access_keys = world.options.zone_access_keys.current_key
    if world.options.goal == "all_zones":
        goal_clear_req = world.options.all_zones_goal_clear.value
    elif world.options.goal == "golden_lute_shards":
        goal_clear_req = world.options.golden_lute_shards_goal_clear.value
    else:
        goal_clear_req = world.options.zones_goal_clear.value

    all_zones_types = (LocationType.ALL_ZONES, LocationType.ALL_ZONES_EVENT, LocationType.EXTRA_MODE)
    character_location_types = (
        LocationType.FLOOR,
        LocationType.BOSS,
        LocationType.UNIQUE_BOSS,
        LocationType.ZONE,
        LocationType.ALL_ZONES,
        LocationType.ALL_ZONES_EVENT,
        LocationType.ZONES_EVENT,
    )

    for location in world.locations:
        rule: Rule[CotNDWorld] | None = None

        if location.type in character_location_types:
            if location.character is None:
                continue
            rule = Has(location.character)
            if (
                world.options.character_unlocks != "item_only"
                and location.character in character_requirements
            ):
                for requirement in character_requirements[location.character]:
                    if requirement in world.item_from_name:
                        item_data = world.item_from_name[requirement]
                        if item_data.default is not DefaultType.UNIQUE or bool(world.options.include_unique_items.value):
                            rule = rule & Has(item_data.name)

        elif location.type is LocationType.EXTRA_MODE:
            rule = Has(location.name)

        elif location.type is LocationType.SHOP:
            shopkeeper, rest = location.name.split(" - ", 1)
            index = int(rest.split(" Shop Item ")[1])
            if index != 1:
                rule = Has("Shop Stock Unlock", index - 1)
            if shopkeeper == "Merlin":
                merlin_rule: Rule[CotNDWorld] = Has("Merlin")
                rule = merlin_rule if rule is None else rule & merlin_rule

        elif location.type is LocationType.TUTORIAL:
            rule = Has("Codex")

        # Zone access
        if location.type in all_zones_types:
            zone_rule: Rule[CotNDWorld] = FullZoneAccess()
            rule = zone_rule if rule is None else rule & zone_rule
        elif location.zone is not None:
            zone_rule = ZoneGate(location.zone, location.character)
            rule = zone_rule if rule is None else rule & zone_rule

        # Character Room Key
        if (
            world.options.lock_character_room
            and world.starting_character_name
            and location.character is not None
            and location.character != world.starting_character_name
            and location.type not in (LocationType.SHOP, LocationType.TUTORIAL, LocationType.NPC)
        ):
            key_rule: Rule[CotNDWorld] = Has("Character Room Key")
            rule = key_rule if rule is None else rule & key_rule

        if rule is not None:
            world.set_rule(world.get_location(location.name), rule)

    # Caged NPC locations need zone access to the zone they're physically in
    if world.caged_npc_locations and zone_access_keys != "disabled":
        for npc_name, npc_info in world.caged_npc_locations.items():
            npc_zone = npc_info.get("zone")
            if npc_zone:
                try:
                    loc = world.get_location(f"Caged {npc_name}")
                    world.set_rule(loc, ZoneGate(npc_zone))
                except KeyError:
                    pass  # Location doesn't exist (might be filtered out)

    if world.options.goal == "golden_lute_shards":
        ensemble_rule = Has("Golden Lute Shard", goal_clear_req) & FullZoneAccess()
    else:
        ensemble_rule = Has("Complete", goal_clear_req) & FullZoneAccess()
    trigger_location = {0: "Ensemble Completion", 1: "Boss Rush Completion", 2: "Expensive Purchase Completion"}
    victory_location = trigger_location.get(world.options.victory_trigger.value, "Ensemble Completion")
    world.set_rule(world.get_location(victory_location), ensemble_rule)
    world.set_completion_rule(Has("Victory"))


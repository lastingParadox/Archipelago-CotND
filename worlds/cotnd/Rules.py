from __future__ import annotations

from typing import TYPE_CHECKING, Final, Optional

from rule_builder.rules import Has, HasAll, HasAny, Rule

from worlds.cotnd.Items import ALL_ITEMS, InventoryType
from worlds.cotnd.Locations import (ALL_LOCATIONS, VICTORY_TRIGGER_LOCATIONS, LocationType,
                                        available_character_names)
from worlds.cotnd.Regions import ARIA, zone_entrance
from worlds.cotnd.Utils import (CHARACTER_ITEM_REQUIREMENTS, characters_for_shrine, max_zone,
                                    owned_dlc)

if TYPE_CHECKING:
    from . import CotNDWorld

CotNDRule = Rule["CotNDWorld"]

# Shop row N opens once N-1 restocks are in hand, and Merlin only stocks her own row.
MERLIN: Final = "Merlin"

# Reaching these needs the whole crypt open, not just one zone.
FULL_ACCESS_TYPES = (LocationType.ALL_ZONES, LocationType.EXTRA_MODE)
FULL_ACCESS_TRIGGERS = ("ensemble", "boss_rush")

# Rule helpers

def zone_access_rule(world: CotNDWorld, zone: int, character: Optional[str]) -> Optional[CotNDRule]:
    mode = world.options.zone_access_keys.current_key

    if mode == "disabled":
        return None

    start = world.options.starting_zone.value

    if mode == "separate":
        return None if zone == start else Has(f"Zone {zone} Access")

    # Progressive. Aria runs the crypt top-down, so her start and her cost both mirror.
    if character == ARIA:
        zones = max_zone(owned_dlc(world))
        if zone >= zones - start + 1:
            return None
        required = max(0, zones - zone)
    else:
        if zone <= start:
            return None
        required = max(0, zone - 1)

    return Has("Progressive Zone Access", required) if required else None

def full_zone_access_rule(world: CotNDWorld) -> Optional[CotNDRule]:
    mode = world.options.zone_access_keys.current_key

    if mode == "disabled":
        return None

    zones = max_zone(owned_dlc(world))

    if mode == "separate":
        return HasAll(*(f"Zone {zone} Access" for zone in range(1, zones + 1)))

    return Has("Progressive Zone Access", zones - 1) if zones > 1 else None

def character_rule(world: CotNDWorld, character: str) -> CotNDRule:
    rule: CotNDRule = Has(character)

    if world.options.character_unlocks == "item_only":
        return rule

    dlc = owned_dlc(world)

    for requirement in CHARACTER_ITEM_REQUIREMENTS.get(character, ()):
        item = ALL_ITEMS.get_by_name(requirement)
        # A requirement only gates when it is actually in the pool
        if not item.available_with(dlc):
            continue
        # Unique equipment only gates when it is actually in the pool.
        if item.inventory_type is InventoryType.UNIQUE and not world.options.include_unique_items:
            continue
        rule = rule & Has(item.name)

    return rule

def goal_clear_requirement(world: CotNDWorld) -> int:
    goal = world.options.goal.current_key

    if goal == "all_zones":
        return world.options.all_zones_goal_clear.value
    if goal == "golden_lute_shards":
        return world.options.golden_lute_shards_goal_clear.value

    return world.options.zones_goal_clear.value

# Entrance rules

def set_all_entrance_rules(world: CotNDWorld) -> None:
    for zone in range(1, max_zone(owned_dlc(world)) + 1):
        for character in (None, ARIA):
            rule = zone_access_rule(world, zone, character)

            if rule is not None:
                world.set_rule(world.get_entrance(zone_entrance(zone, character)), rule)

# Location rules

def set_all_location_rules(world: CotNDWorld) -> None:
    characters = available_character_names(owned_dlc(world), set(world.options.character_blacklist.value))
    starting_character = world.options.starting_character.current_option_name
    full_access = full_zone_access_rule(world)

    for location in world.get_locations():
        data = ALL_LOCATIONS.get_by_name(location.name)
        rule = location_rule(world, data, characters, starting_character, full_access)

        if rule is not None:
            world.set_rule(location, rule)

def location_rule(world: CotNDWorld, data, characters: set[str], starting_character: str,
                  full_access: Optional[CotNDRule]) -> Optional[CotNDRule]:
    rule: Optional[CotNDRule] = None

    if data.character is not None:
        rule = character_rule(world, data.character)
    elif data.type is LocationType.EXTRA_MODE:
        rule = Has(data.name)
    elif data.type is LocationType.SHOP:
        rule = shop_rule(data)
    elif data.type is LocationType.TUTORIAL:
        rule = Has("Codex")
    elif data.type is LocationType.SHRINE:
        rule = shrine_rule(data, characters)

    # Checks played across the whole crypt, rather than inside one zone's region.
    if data.type in FULL_ACCESS_TYPES or data.goal == "all_zones":
        rule = combine(rule, full_access)

    # Switching away from the starting character costs the room key.
    if (world.options.lock_character_room
            and data.character is not None
            and data.character != starting_character):
        rule = combine(rule, Has("Character Room Key"))

    return rule

def shop_rule(data) -> Optional[CotNDRule]:
    rule: Optional[CotNDRule] = None

    # Row 1 is stocked from the start; every row after it costs one more restock.
    if data.index is not None and data.index > 1:
        rule = Has("Shop Restock", data.index - 1)

    if data.name.startswith(f"{MERLIN} - "):
        rule = combine(rule, Has(MERLIN))

    return rule

def shrine_rule(data, characters: set[str]) -> CotNDRule:
    rule: CotNDRule = Has(data.name)

    # Unlocking the shrine is not enough; somebody in the pool has to be able to meet it.
    capable = characters_for_shrine(data.name, characters)
    if capable != characters:
        rule = rule & HasAny(*sorted(capable))

    return rule

def combine(rule: Optional[CotNDRule], addition: Optional[CotNDRule]) -> Optional[CotNDRule]:
    if addition is None:
        return rule

    return addition if rule is None else rule & addition

# Victory

def set_completion_condition(world: CotNDWorld) -> None:
    goal = world.options.goal.current_key
    required = goal_clear_requirement(world)

    victory_rule: Optional[CotNDRule]

    if goal == "golden_lute_shards":
        victory_rule = Has("Golden Lute Shard", required)
    elif goal == "story":
        # Every story boss, by name -- a counted token would let any N of them pass.
        # Matched against this seed's locations: world.location_names omits events.
        created = {location.name for location in world.multiworld.get_locations(world.player)}
        story_events = sorted(location.name for location in ALL_LOCATIONS.locations
                              if location.goal == "story" and location.name in created)
        victory_rule = HasAll(*story_events)
    else:
        victory_rule = Has("Complete", required)

    # The catalyst carries its own access cost, separate from the goal: Ensemble and Boss
    # Rush are played across every zone. Buying a lobby item or completing outright is not.
    trigger = world.options.victory_trigger.current_key
    if trigger in FULL_ACCESS_TRIGGERS:
        victory_rule = combine(victory_rule, full_zone_access_rule(world))

    if victory_rule is not None:
        world.set_rule(world.get_location(VICTORY_TRIGGER_LOCATIONS[trigger]), victory_rule)

    world.set_completion_rule(Has("Victory"))

def set_all_rules(world: CotNDWorld) -> None:
    set_all_entrance_rules(world)
    set_all_location_rules(world)
    set_completion_condition(world)

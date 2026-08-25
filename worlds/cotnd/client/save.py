"""
save.py — CotNDSaveData

Authoritative Python-side save state for a Crypt of the NecroDancer
Archipelago session.

Derivable fields are recomputed from live AP server data on each call to
:meth:`refresh`.  Non-derivable fields (diamond balance, buffs, banned
items, run items, hints purchased) are stored in-memory, updated via
targeted mod packets, and persisted to AP DataStorage.

DataStorage format: only non-derivable fields are stored (see
:meth:`to_datastorage`).  Derivable fields are recomputed on reconnect
from ctx.items_received and ctx.checked_locations, which the AP server
tracks authoritatively.  On restore the seed name is validated; blobs
from a different seed or an unrecognised version are discarded and a
fresh default is returned.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from worlds.cotnd.Items import ALL_ITEMS, ItemType, item_from_code
from worlds.cotnd.Locations import ALL_LOCATIONS, LocationType, location_from_code
from worlds.cotnd.Utils import LOBBY_NPCS

if TYPE_CHECKING:
    from worlds.cotnd.client.context import CotNDContext

# ---------------------------------------------------------------------------
# Module-level constants / compiled patterns
# ---------------------------------------------------------------------------

_SAVE_VERSION = 3  # Bump when the DataStorage schema changes incompatibly.

# "APDiamond3" is worth 3, so the value comes off the id
_DIAMOND_VALUES: dict[str, int] = {
    item.cotnd_id: int(item.cotnd_id.removeprefix("APDiamond"))
    for item in ALL_ITEMS.items
    if item.cotnd_id.startswith("APDiamond")
}

# Item types the mod must re-apply itself after missing them,
# because nothing in the derived state carries their effect
_REPLAYABLE_ITEM_TYPES: frozenset[ItemType] = frozenset({ItemType.FILLER, ItemType.TRAP})

_CODEX_MAP: dict[str, str] = {
    "Dragon Lore": "DragonLore",
    "Trap Lore": "TrapLore",
    "Bomb Lore": "BombLore",
    "How to Get Away with Murder": "Murder",
}


def _shop_stall(name: str) -> tuple[str, str, int] | None:
    # Split "Hephaestus - Left Shop Item 3" into (shopkeeper, side, slot)
    try:
        shopkeeper, rest = name.split(" - ", 1)
        side, slot = rest.split(" Shop Item ")
        return shopkeeper, side, int(slot)
    except ValueError:
        return None


# Every (shopkeeper, side) pair the location data defines, in first-seen order.
_SHOP_STALLS: list[tuple[str, str]] = list(dict.fromkeys(
    stall[:2]
    for location in ALL_LOCATIONS.locations
    if location.type is LocationType.SHOP
    for stall in (_shop_stall(location.name),)
    if stall is not None
))


def _name_set(value: object) -> dict[str, bool]:
    # The list branch exists only because Lua serialises an empty table as []
    if isinstance(value, dict):
        return {name: True for name, held in value.items() if held}
    if isinstance(value, list):
        return {str(name): True for name in value}
    return {}


class CotNDSaveData:
    # Full save state for a CotND AP session, managed by the client.

    # ------------------------------------------------------------------ #
    # Construction                                                         #
    # ------------------------------------------------------------------ #

    def __init__(self, ctx: CotNDContext) -> None:
        self._ctx = ctx

        self.stored_scouts: list[dict] = []
        self.datastorage_loaded: bool = False

        # --- Non-derivable (mod authority; persisted to DataStorage) ---

        # None means "use AP-received diamond sum"; a real int means the
        # mod has reported its current in-game balance (including spending).
        self.diamonds: int | None = None
        # {"health": N, "characterBuffs": {"CharName": bool, ...}}
        self.buffs: dict = {}
        self.banned_items: dict[str, bool] = {}
        self.next_run_items: dict[str, bool] = {}
        # Incremented each time the player successfully purchases a hint.
        self.hints_purchased: int = 0
        # Shrine toggles. None until seeded from slot data on the first connect;
        # after that the player's choice outlives the YAML.
        self.death_link: bool | None = None
        self.trap_link: bool | None = None

        # --- Derivable (computed by refresh()) ---
        self.zone_access: dict = {"progressiveCount": 0}
        self.character_locations: dict[str, dict[str, bool]] = {}
        self.shop_locations: dict = self._empty_shop_locations()
        self.codex_locations: dict = {
            "DragonLore": None,
            "TrapLore": None,
            "BombLore": None,
            "Murder": None,
        }
        self.chest_locations: dict = {}
        self.unlocked_npcs: dict = {}
        # How many received items the mod has actually parsed
        self.parsed_count: int = 0
        self.shop_consumed_locations: dict = {}
        self.health: int = 0
        self.shop_stock: int = 0
        # Sum of AP diamond items received (before in-game spending).
        self.ap_diamonds: int = 0
        self.character_room_key: bool = False
        # {"ModeName": bool}  False = not yet received, True = unlocked
        self.extra_modes: dict[str, bool] = {}
        self.unlocked_buff_items: dict[str, bool] = {}
        self.golden_lute_shards: int = 0
        self.scouted_locations: bool = False

    # ------------------------------------------------------------------ #
    # Restoration from DataStorage                                         #
    # ------------------------------------------------------------------ #

    @classmethod
    def from_datastorage(cls, raw: dict, ctx: CotNDContext) -> CotNDSaveData:
        # Create an instance and restore non-derivable state from *raw*.

        inst = cls(ctx)
        inst.datastorage_loaded = True

        if not isinstance(raw, dict):
            return inst

        # Version / seed guard.
        if raw.get("_v") != _SAVE_VERSION:
            return inst
        if raw.get("seedName") != ctx.seed_name:
            return inst

        raw_diamonds = raw.get("diamonds")
        if isinstance(raw_diamonds, (int, float)):
            inst.diamonds = max(0, int(raw_diamonds))

        buffs = raw.get("buffs")
        if isinstance(buffs, dict):
            inst.buffs = buffs

        inst.banned_items = _name_set(raw.get("bannedItems"))
        inst.next_run_items = _name_set(raw.get("nextRunItems"))

        hints_purchased = raw.get("hintsPurchased")
        if isinstance(hints_purchased, int):
            inst.hints_purchased = hints_purchased

        parsed = raw.get("parsedCount")
        if isinstance(parsed, int):
            inst.parsed_count = max(0, parsed)

        death_link = raw.get("deathLink")
        if isinstance(death_link, bool):
            inst.death_link = death_link

        trap_link = raw.get("trapLink")
        if isinstance(trap_link, bool):
            inst.trap_link = trap_link

        return inst

    # ------------------------------------------------------------------ #
    # Persistence                                                          #
    # ------------------------------------------------------------------ #

    def to_datastorage(self) -> dict:
        # Serialise non-derivable save state for AP DataStorage.
        
        return {
            "_v": _SAVE_VERSION,
            "seedName": self._ctx.seed_name,
            "diamonds": self.diamonds,
            "buffs": self.buffs,
            "bannedItems": self.banned_items,
            "nextRunItems": self.next_run_items,
            "hintsPurchased": self.hints_purchased,
            "parsedCount": self.parsed_count,
            "deathLink": self.death_link,
            "trapLink": self.trap_link,
        }

    # ------------------------------------------------------------------ #
    # State packet export                                                  #
    # ------------------------------------------------------------------ #

    def to_state_fields(self) -> dict:
        # Return all computed + stored fields for inclusion in the State packet.

        return {
            # Derivable
            "zone_access": self.zone_access,
            "character_locations": self.character_locations,
            "shop_locations": self.shop_locations,
            "codex_locations": self.codex_locations,
            "chest_locations": self.chest_locations,
            "unlocked_npcs": self.unlocked_npcs,
            "shop_consumed_locations": self.shop_consumed_locations,
            "health": self.health,
            "shop_stock": self.shop_stock,
            "diamonds": self.diamonds if self.diamonds is not None else self.ap_diamonds,
            "character_room_key": self.character_room_key,
            "extra_modes": self.extra_modes,
            "unlocked_buff_items": self.unlocked_buff_items,
            "golden_lute_shards": self.golden_lute_shards,
            "scouted_locations": self.scouted_locations,
            # Non-derivable
            "banned_items": self.banned_items,
            "next_run_items": self.next_run_items,
            "buffs": self.buffs,
            "hints_purchased": self.hints_purchased,
        }

    # ------------------------------------------------------------------ #
    # Derivable field computation                                          #
    # ------------------------------------------------------------------ #

    def refresh(self) -> None:
        # Recompute all derivable fields from the current AP context state.
        self.zone_access = self._compute_zone_access()
        self.character_locations = self._compute_character_locations()
        self.unlocked_npcs = self._compute_unlocked_npcs()
        self.shop_locations = self._compute_shop_locations()
        self.codex_locations = self._compute_codex_locations()
        self.chest_locations = self._compute_chest_locations()
        self.shop_consumed_locations = self._compute_shop_consumed()
        (
            self.health,
            self.shop_stock,
            self.ap_diamonds,
            self.character_room_key,
            self.golden_lute_shards,
        ) = self._compute_items_summary()
        self.extra_modes = self._compute_extra_modes()
        self.unlocked_buff_items = self._compute_unlocked_buff_items()
        self.scouted_locations = bool(self.stored_scouts)

    # ------------------------------------------------------------------ #

    def _safe_cotnd_id(self, item_code: int) -> str:
        try:
            return item_from_code(item_code).cotnd_id
        except (KeyError, ValueError):
            return ""

    def _compute_zone_access(self) -> dict:
        ctx = self._ctx
        sd = ctx.slotdata
        starting_zone = sd.get("starting_zone", 1)
        zone_access_keys = sd.get("zone_access_keys", "disabled")

        access: dict = {"progressiveCount": 0, str(starting_zone): True}
        progressive_count = 0
        zone_map = {f"APZone{z}Access": z for z in range(1, 6)}

        for net_item in ctx.items_received:
            cotnd_id = self._safe_cotnd_id(net_item.item)
            z = zone_map.get(cotnd_id)
            if z is not None:
                access[str(z)] = True
            elif cotnd_id == "APProgressiveZoneAccess":
                progressive_count += 1

        if zone_access_keys != "separate":
            access["progressiveCount"] = progressive_count
            for z in range(1, progressive_count + 2):
                access[str(z)] = True

        return access

    def _compute_character_locations(
        self,
        extra_checked_locs: set[int] | None = None,
    ) -> dict[str, dict[str, bool]]:
        ctx = self._ctx
        char_locs: dict[str, dict[str, bool]] = {}

        def _missing_key(loc) -> tuple[str, str] | None:
            # Key used to initialise a False entry from server_locations.
            if loc.character is None:
                return None
            if loc.type == LocationType.ZONE:
                return loc.character, f"Zone {loc.zone}"
            if loc.type == LocationType.ALL_ZONES:
                return loc.character, "All Zones"
            if loc.type == LocationType.EXTRA_MODE:
                return loc.character, loc.name.split(" - ", 1)[1]
            if loc.type == LocationType.UNIQUE_BOSS:
                return loc.character, loc.name.split(" - ", 1)[1]
            return None

        def _checked_key(loc) -> tuple[str, str] | None:
            # Key to set True when a location is checked.
            if loc.character is None:
                return None
            if loc.type == LocationType.ALL_ZONES:
                return loc.character, "All Zones"
            if loc.type == LocationType.EXTRA_MODE:
                return loc.character, loc.name.split(" - ", 1)[1]
            if loc.type == LocationType.UNIQUE_BOSS:
                return loc.character, loc.name.split(" - ", 1)[1]
            if loc.type == LocationType.ZONE:
                return loc.character, f"Zone {loc.zone}"
            return None

        # Build initial structure (all False) from the full server location set.
        for loc_code in ctx.server_locations:
            try:
                loc = location_from_code(loc_code)
            except (KeyError, ValueError):
                continue
            result = _missing_key(loc)
            if result:
                char, key = result
                char_locs.setdefault(char, {}).setdefault(key, False)

        # Use locally-confirmed checked locations when provided
        effective_checked = (
            ctx.checked_locations | extra_checked_locs
            if extra_checked_locs is not None
            else ctx.checked_locations
        )
        for loc_code in effective_checked:
            try:
                loc = location_from_code(loc_code)
            except (KeyError, ValueError):
                continue
            result = _checked_key(loc)
            if result:
                char, key = result
                char_locs.setdefault(char, {})[key] = True

        return char_locs

    def _compute_unlocked_npcs(self) -> dict:
        ctx = self._ctx
        npc_conditions: dict = ctx.slotdata.get("caged_npc_locations") or {}

        if not npc_conditions:
            return {npc: {"unlocked": True} for npc in LOBBY_NPCS}

        unlocked_npcs: dict = {
            npc: {
                "unlocked": False,
                "zone": info.get("zone"),
                "level": info.get("level"),
                "unlockType": info.get("unlockType"),
            }
            for npc, info in npc_conditions.items()
        }

        # Locations checked in-game (type NPC, name = "Caged {npc}")
        for loc_code in ctx.checked_locations:
            try:
                loc = location_from_code(loc_code)
            except (KeyError, ValueError):
                continue
            if loc.type == LocationType.NPC:
                npc = loc.name[6:]  # strip leading "Caged "
                if npc in unlocked_npcs:
                    unlocked_npcs[npc]["unlocked"] = True

        # NPC items received from AP (e.g. Janitor, Diamond Dealer)
        for net_item in ctx.items_received:
            try:
                item_data = item_from_code(net_item.item)
                if item_data.type == ItemType.NPC and item_data.name in unlocked_npcs:
                    unlocked_npcs[item_data.name]["unlocked"] = True
            except (KeyError, ValueError):
                pass

        return unlocked_npcs

    def _scout_entry(self, scout: dict, loc_code_str: str) -> dict:
        # The per-location payload the mod reads to spawn a located item.
        return {
            "Item": scout.get("item", ""),
            "ItemName": scout.get("itemname", "").replace("_", " "),
            "PlayerName": scout.get("playername", ""),
            "LocationCode": loc_code_str,
            "Location": scout.get("location", ""),
            "Classification": scout.get("flags"),
            "Checked": int(loc_code_str) in self._ctx.locations_checked,
        }

    def _scouts_of_type(self, *types: LocationType):
        # Yield (location, code string, scout) for stored scouts of the given types.
        for scout in self.stored_scouts:
            loc_code_str = scout.get("location_code")
            if loc_code_str is None:
                continue
            try:
                loc = location_from_code(int(loc_code_str))
            except (KeyError, ValueError, TypeError):
                continue
            if loc.type in types:
                yield loc, loc_code_str, scout

    def _compute_chest_locations(self) -> dict:
        chest_locations: dict = {}

        for loc, loc_code_str, scout in self._scouts_of_type(
            LocationType.ZONE_ITEM, LocationType.FLAWLESS_CHEST
        ):
            if loc.zone is None:
                continue

            kind = "Flawless" if loc.type is LocationType.FLAWLESS_CHEST else "Item"
            chest_locations.setdefault(str(loc.zone), {}).setdefault(kind, []).append(
                self._scout_entry(scout, loc_code_str)
            )

        for kinds in chest_locations.values():
            for entries in kinds.values():
                entries.sort(key=lambda entry: int(entry["LocationCode"]))

        return chest_locations

    def _compute_shop_locations(self) -> dict:
        shop_locations: dict = self._empty_shop_locations()

        for loc, loc_code_str, scout in self._scouts_of_type(LocationType.SHOP):
            stall = _shop_stall(loc.name)
            if stall is None:
                continue

            shopkeeper, side, slot = stall
            shop_locations.setdefault(shopkeeper, {}).setdefault(side, {"Current": 1, "Slots": {}})
            shop_locations[shopkeeper][side]["Slots"][str(slot)] = self._scout_entry(
                scout, loc_code_str
            )

        return shop_locations

    def _compute_codex_locations(self) -> dict:
        codex_locations: dict = {
            "DragonLore": None,
            "TrapLore": None,
            "BombLore": None,
            "Murder": None,
        }

        for loc, loc_code_str, scout in self._scouts_of_type(LocationType.TUTORIAL):
            codex_key = _CODEX_MAP.get(loc.name)
            if not codex_key:
                continue

            codex_locations[codex_key] = self._scout_entry(scout, loc_code_str)

        return codex_locations

    def mark_items_parsed(self) -> None:
        # Record every AP item as parsed once the mod has been sent them
        self.parsed_count = len(self._ctx.items_received)

    def _is_replayable(self, index: int) -> bool:
        # Whether the item at *index* has an effect only the mod can apply
        try:
            item_data = item_from_code(self._ctx.items_received[index].item)
        except (KeyError, ValueError, IndexError):
            return False
        if item_data.type not in _REPLAYABLE_ITEM_TYPES:
            return False
        # Once the mod reports a balance, diamonds live in it and must not be re-granted.
        return self.diamonds is None or item_data.cotnd_id not in _DIAMOND_VALUES

    def received_items_for_state(self) -> dict:
        # The full item history, minus replayable items the mod has yet to apply
        return {
            key: entry
            for key, entry in self._compute_received_items().items()
            if int(key) < self.parsed_count or not self._is_replayable(int(key))
        }

    def _compute_received_items(self) -> dict:
        # The item history keyed by AP index
        ctx = self._ctx
        result: dict = {}
        for idx, net_item in enumerate(ctx.items_received):
            try:
                item_data = item_from_code(net_item.item)
            except (KeyError, ValueError):
                continue
            if item_data.type == ItemType.BUFF:
                continue
            result[str(idx)] = {
                "item": item_data.cotnd_id,
                "item_name": item_data.name,
                "location_code": str(net_item.location),
                "location_name": ctx.location_names.lookup_in_slot(
                    net_item.location, ctx.slot
                ),
                "playername": ctx.player_names[net_item.player],
            }
        return result

    def _compute_shop_consumed(self) -> dict:
        ctx = self._ctx
        result: dict = {}
        for loc_code in ctx.locations_checked:
            try:
                if location_from_code(loc_code).type == LocationType.SHOP:
                    result[str(loc_code)] = True
            except (KeyError, ValueError):
                pass
        return result

    def _compute_items_summary(self) -> tuple[int, int, int, bool, int]:
        # Returns (health, shop_stock, ap_diamonds, character_room_key, golden_lute_shards)
        health = 0
        shop_stock = 0
        ap_diamonds = 0
        char_room_key = False
        golden_lute_shards = 0

        for net_item in self._ctx.items_received:
            cotnd_id = self._safe_cotnd_id(net_item.item)
            if cotnd_id == "PermHeart2":
                health += 2
            elif cotnd_id == "APShopStock":
                shop_stock += 1
            elif cotnd_id in _DIAMOND_VALUES:
                ap_diamonds += _DIAMOND_VALUES[cotnd_id]
            elif cotnd_id == "APCharRoomKey":
                char_room_key = True
            elif cotnd_id == "APGoldenLuteShard":
                golden_lute_shards += 1

        return health, shop_stock, ap_diamonds, char_room_key, golden_lute_shards

    def _compute_extra_modes(self) -> dict[str, bool]:
        ctx = self._ctx
        # All modes in slot data start as False (locked).
        extra_modes: dict[str, bool] = {
            mode: False for mode in (ctx.slotdata.get("included_extra_modes") or [])
        }
        for net_item in ctx.items_received:
            try:
                item_data = item_from_code(net_item.item)
                if item_data.type != ItemType.MODE:
                    continue
                # Keys are option display names ("No Return"), not cotnd_ids.
                mode = item_data.name.removesuffix(" Mode")
                if mode in extra_modes:
                    extra_modes[mode] = True
            except (KeyError, ValueError):
                pass
        return extra_modes

    def _compute_unlocked_buff_items(self) -> dict[str, bool]:
        result: dict[str, bool] = {}
        for net_item in self._ctx.items_received:
            try:
                item_data = item_from_code(net_item.item)
                if item_data.type == ItemType.BUFF:
                    result[item_data.name.removesuffix(" Buff")] = True
            except (KeyError, ValueError):
                pass
        return result

    # ------------------------------------------------------------------ #
    # Non-derivable field updates (mod packets)                            #
    # ------------------------------------------------------------------ #

    def apply_change_diamonds(self, value: int | float) -> None:
        # Record the mod's current diamond balance (replaces AP-item sum).
        self.diamonds = max(0, int(value))

    def apply_change_buffs(self, buffs: dict | None = None) -> None:
        # Replace the stored buffs dict with the mod's current value.
        if isinstance(buffs, dict):
            self.buffs = buffs

    def apply_change_run_items(
        self,
        banned_items: object = None,
        next_run_items: object = None,
    ) -> None:
        if banned_items is not None:
            self.banned_items = _name_set(banned_items)
        if next_run_items is not None:
            self.next_run_items = _name_set(next_run_items)

    def on_hint_purchased(self) -> None:
        # ncrement the hints-purchased counter when the player buys a hint.
        self.hints_purchased += 1

    def add_scouts(self, location_info: list[dict]) -> None:
        # Extend the internal scout cache with new ``LocationInfo`` entries.
        self.stored_scouts.extend(location_info)

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _empty_shop_locations() -> dict:
        # The full shop scaffold, so the mod always sees every stall even before scouts.
        scaffold: dict = {}

        for shopkeeper, side in _SHOP_STALLS:
            scaffold.setdefault(shopkeeper, {})[side] = {"Current": 1, "Slots": {}}

        return scaffold

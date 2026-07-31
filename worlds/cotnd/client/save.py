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

from worlds.cotnd.Items import ItemType, item_from_code
from worlds.cotnd.Locations import LocationType, location_from_code

if TYPE_CHECKING:
    from worlds.cotnd.client.context import CotNDContext

# ---------------------------------------------------------------------------
# Module-level constants / compiled patterns
# ---------------------------------------------------------------------------

_SAVE_VERSION = 1  # Bump when the DataStorage schema changes incompatibly.

_DIAMOND_VALUES: dict[str, int] = {
    "APDiamond1": 1,
    "APDiamond2": 2,
    "APDiamond3": 3,
    "APDiamond4": 4,
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

_LOBBY_NPCS = ["Beastmaster", "Merlin", "Hintmaster", "Weaponmaster", "Diamond Dealer"]


class CotNDSaveData:
    """Full save state for a CotND AP session, managed by the Python client.

    All fields mirror the Lua ``initSaveData`` structure so the Lua handler
    can consume the State packet without a separate conversion step.
    """

    # ------------------------------------------------------------------ #
    # Construction                                                         #
    # ------------------------------------------------------------------ #

    def __init__(self, ctx: CotNDContext) -> None:
        self._ctx = ctx

        # Scouts accumulated from LocationInfo responses.
        # Used to build shopLocations / codexLocations on refresh().
        self.stored_scouts: list[dict] = []

        # True once from_datastorage() has been called for this instance.
        # _persist_save must not write DataStorage before this flag is set,
        # or it will overwrite the persisted diamonds with null.
        self.datastorage_loaded: bool = False

        # --- Non-derivable (mod authority; persisted to DataStorage) ---

        # None means "use AP-received diamond sum"; a real int means the
        # mod has reported its current in-game balance (including spending).
        self.diamonds: int | None = None
        # {"health": N, "characterBuffs": {"CharName": bool, ...}}
        self.buffs: dict = {}
        # {"ItemName": true, ...}
        self.banned_items: dict = {}
        # {"ItemName": true, ...}
        self.next_run_items: dict = {}
        # Incremented each time the player successfully purchases a hint.
        self.hints_purchased: int = 0

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
        self.unlocked_npcs: dict = {}
        # Record of what the mod has actually parsed, not a mirror of ctx.items_received
        self.received_items: dict = {}
        # False until a persisted parsed-record has been adopted
        self._received_items_known: bool = False
        # True when restored from a valid existing save, as opposed to a brand
        # new game. Distinguishes "upgraded mid-playthrough" from "nothing yet".
        self._had_prior_save: bool = False
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
        """Create an instance and restore non-derivable state from *raw*.

        Returns a clean default instance when *raw* is not a valid save for
        the current seed (wrong seed, unrecognised format, or legacy blob
        written by the Lua mod before this refactor).
        """
        inst = cls(ctx)
        inst.datastorage_loaded = True

        if not isinstance(raw, dict):
            return inst

        # Version / seed guard.
        if raw.get("_v") != _SAVE_VERSION:
            return inst
        if raw.get("seedName") != ctx.seed_name:
            return inst

        inst._had_prior_save = True

        raw_diamonds = raw.get("diamonds")
        if isinstance(raw_diamonds, (int, float)):
            inst.diamonds = int(raw_diamonds)

        buffs = raw.get("buffs")
        if isinstance(buffs, dict):
            inst.buffs = buffs

        banned = raw.get("bannedItems")
        if isinstance(banned, dict):
            inst.banned_items = banned

        next_run = raw.get("nextRunItems")
        if isinstance(next_run, dict):
            inst.next_run_items = next_run

        hints_purchased = raw.get("hintsPurchased")
        if isinstance(hints_purchased, int):
            inst.hints_purchased = hints_purchased

        parsed = raw.get("receivedItems")
        if isinstance(parsed, dict):
            inst.received_items = parsed
            inst._received_items_known = True

        return inst

    # ------------------------------------------------------------------ #
    # Persistence                                                          #
    # ------------------------------------------------------------------ #

    def to_datastorage(self) -> dict:
        """Serialise non-derivable save state for AP DataStorage.

        Only the fields that cannot be recomputed from AP server state are
        stored.  Everything else (zone access, character locations, shop
        state, health, etc.) is recomputed by refresh() on reconnect from
        ctx.items_received and ctx.checked_locations, which the AP server
        already tracks authoritatively.
        """
        return {
            "_v": _SAVE_VERSION,
            "seedName": self._ctx.seed_name,
            "diamonds": self.diamonds,
            "buffs": self.buffs,
            "bannedItems": self.banned_items,
            "nextRunItems": self.next_run_items,
            "hintsPurchased": self.hints_purchased,
            "receivedItems": self.received_items,
        }

    # ------------------------------------------------------------------ #
    # State packet export                                                  #
    # ------------------------------------------------------------------ #

    def to_state_fields(self) -> dict:
        """Return all computed + stored fields for inclusion in the State packet.

        Key names use snake_case to match the existing Python→mod packet
        convention; the Lua handler maps them to its camelCase saveData
        fields.
        """
        ctx = self._ctx
        sd = ctx.slotdata
        return {
            # Derivable
            "zone_access": self.zone_access,
            "character_locations": self.character_locations,
            "shop_locations": self.shop_locations,
            "codex_locations": self.codex_locations,
            "unlocked_npcs": self.unlocked_npcs,
            "received_items": self.received_items_for_state(),
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
            # Static slot data the Lua init handler needs
            "starting_character": sd.get("starting_character"),
        }

    # ------------------------------------------------------------------ #
    # Derivable field computation                                          #
    # ------------------------------------------------------------------ #

    def refresh(self) -> None:
        """Recompute all derivable fields from the current AP context state."""
        self.zone_access = self._compute_zone_access()
        self.character_locations = self._compute_character_locations()
        self.unlocked_npcs = self._compute_unlocked_npcs()
        self.shop_locations = self._compute_shop_locations()
        self.codex_locations = self._compute_codex_locations()
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
        zone_access_keys = sd.get("zone_access_keys", 0)

        access: dict = {"progressiveCount": 0, str(starting_zone): True}
        progressive_count = 0
        zone_map = {f"APZone{z}Access": z for z in range(1, 6)}

        for net_item in ctx.items_received:
            cotnd_id = self._safe_cotnd_id(net_item.item)
            z = zone_map.get(cotnd_id)
            if z is not None:
                access[str(z)] = True
            elif cotnd_id == "APProgressiveZoneAccess" and net_item.location != -2:
                progressive_count += 1

        if zone_access_keys == 2:  # progressive mode (ZoneAccessKeys.option_progressive)
            access["progressiveCount"] = progressive_count
            for z in range(1, progressive_count + 1):
                access[str(z)] = True

        return access

    def _compute_character_locations(
        self,
        extra_checked_locs: set[int] | None = None,
    ) -> dict[str, dict[str, bool]]:
        ctx = self._ctx
        per_level = bool(ctx.slotdata.get("floor_clear_checks"))
        char_locs: dict[str, dict[str, bool]] = {}

        def _missing_key(loc) -> tuple[str, str] | None:
            """Key used to initialise a False entry from server_locations."""
            if loc.character is None:
                return None
            if loc.type == LocationType.ZONE:
                return loc.character, f"Zone {loc.zone}"
            if loc.type == LocationType.ALL_ZONES:
                return loc.character, "All Zones"
            if loc.type == LocationType.EXTRA_MODE:
                return loc.character, loc.name.split(" - ", 1)[1]
            if per_level:
                # Boss locations mark zone boundaries for non-Dove characters.
                # Dove has no boss; her Floor-3 acts as the zone-cleared indicator.
                if loc.type == LocationType.BOSS:
                    return loc.character, f"Zone {loc.zone}"
                if loc.type == LocationType.FLOOR and loc.character == "Dove" and loc.name.endswith(" Floor 3"):
                    return "Dove", f"Zone {loc.zone}"
            return None

        def _checked_key(loc) -> tuple[str, str] | None:
            """Key to set True when a location is checked."""
            if loc.character is None:
                return None
            if loc.type == LocationType.ALL_ZONES:
                return loc.character, "All Zones"
            if loc.type == LocationType.EXTRA_MODE:
                return loc.character, loc.name.split(" - ", 1)[1]
            if per_level:
                # Dove has no boss; her Floor-3 acts as zone-cleared indicator.
                if loc.type == LocationType.FLOOR and loc.character == "Dove" and loc.name.endswith(" Floor 3"):
                    return "Dove", f"Zone {loc.zone}"
                # Use "Zone N" (not "Zone N - Boss") so SaveUpdate sends keys that
                # getHighestZone and calculateGoalCompletion can read directly.
                if loc.type == LocationType.BOSS:
                    return loc.character, f"Zone {loc.zone}"
            else:
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

        # Use locally-confirmed checked locations when provided (e.g. from _event_locations,
        # where the server hasn't echoed the new checks back via RoomUpdate yet).
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
            return {npc: {"unlocked": True} for npc in _LOBBY_NPCS}

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

    def _compute_shop_locations(self) -> dict:
        ctx = self._ctx
        shop_locations: dict = self._empty_shop_locations()

        for scout in self.stored_scouts:
            loc_code_str = scout.get("location_code")
            if loc_code_str is None:
                continue
            try:
                loc = location_from_code(int(loc_code_str))
            except (KeyError, ValueError, TypeError):
                continue
            if loc.type != LocationType.SHOP:
                continue
            # Name format: "{Shopkeeper} - {Side} Shop Item {N}"
            try:
                shopkeeper, rest = loc.name.split(" - ", 1)
                side, slot_str = rest.split(" Shop Item ")
                slot_num = int(slot_str)
            except (ValueError, AttributeError):
                continue
            checked = int(loc_code_str) in ctx.locations_checked
            shop_locations.setdefault(shopkeeper, {})
            shop_locations[shopkeeper].setdefault(side, {"Current": 1, "Slots": {}})
            shop_locations[shopkeeper][side]["Slots"][str(slot_num)] = {
                "Item": scout.get("item", ""),
                "ItemName": scout.get("itemname", "").replace("_", " "),
                "PlayerName": scout.get("playername", ""),
                "LocationCode": loc_code_str,
                "Classification": scout.get("flags"),
                "Checked": checked,
            }

        return shop_locations

    def _compute_codex_locations(self) -> dict:
        ctx = self._ctx
        codex_locations: dict = {
            "DragonLore": None,
            "TrapLore": None,
            "BombLore": None,
            "Murder": None,
        }

        for scout in self.stored_scouts:
            loc_code_str = scout.get("location_code")
            if loc_code_str is None:
                continue
            try:
                loc = location_from_code(int(loc_code_str))
            except (KeyError, ValueError, TypeError):
                continue
            if loc.type != LocationType.TUTORIAL:
                continue
            codex_key = _CODEX_MAP.get(loc.name)
            if not codex_key:
                continue
            checked = int(loc_code_str) in ctx.locations_checked
            codex_locations[codex_key] = {
                "Item": scout.get("item", ""),
                "ItemName": scout.get("itemname", "").replace("_", " "),
                "PlayerName": scout.get("playername", ""),
                "LocationCode": loc_code_str,
                "Classification": scout.get("flags"),
                "Checked": checked,
            }

        return codex_locations

    def mark_items_parsed(self) -> None:
        """Record every AP item as parsed, once the mod has been sent them."""
        self.received_items = self._compute_received_items()
        self._received_items_known = True

    def ensure_received_items_initialized(self) -> None:
        """Seed the parsed record on the first load that lacks one.
        """
        if self._received_items_known:
            return
        if self._had_prior_save:
            self.mark_items_parsed()
        else:
            self._received_items_known = True

    def _replayable_keys(self) -> set[str]:
        """ap_index keys whose effect the mod alone can apply."""
        diamonds_replayable = self.diamonds is not None
        keys: set[str] = set()
        for idx, net_item in enumerate(self._ctx.items_received):
            try:
                item_data = item_from_code(net_item.item)
            except (KeyError, ValueError):
                continue
            if item_data.type not in _REPLAYABLE_ITEM_TYPES:
                continue
            if not diamonds_replayable and item_data.cotnd_id in _DIAMOND_VALUES:
                continue
            keys.add(str(idx))
        return keys

    def received_items_for_state(self) -> dict:
        """Parsed record padded with everything the mod must not re-apply.
        """
        replayable = self._replayable_keys()
        return {
            key: entry
            for key, entry in self._compute_received_items().items()
            if key not in replayable or key in self.received_items
        }

    def _compute_received_items(self) -> dict:
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
                "ap_index": idx,
                "itemType": (
                    "character" if item_data.type == ItemType.CHARACTER else "item"
                ),
                "charId": (
                    item_data.cotnd_id
                    if item_data.type == ItemType.CHARACTER
                    else None
                ),
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
        """Returns (health, shop_stock, ap_diamonds, character_room_key, golden_lute_shards)."""
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
        """Record the mod's current diamond balance (replaces AP-item sum)."""
        self.diamonds = int(value)

    def apply_change_buffs(self, buffs: dict | None = None) -> None:
        """Replace the stored buffs dict with the mod's current value."""
        if isinstance(buffs, dict):
            self.buffs = buffs

    def apply_change_run_items(
        self,
        banned_items: dict | None = None,
        next_run_items: dict | None = None,
    ) -> None:
        if isinstance(banned_items, dict):
            self.banned_items = banned_items
        elif isinstance(banned_items, list) and not banned_items:
            self.banned_items = {}
        if isinstance(next_run_items, dict):
            self.next_run_items = next_run_items
        elif isinstance(next_run_items, list) and not next_run_items:
            self.next_run_items = {}

    def on_hint_purchased(self) -> None:
        """Increment the hints-purchased counter when the player buys a hint."""
        self.hints_purchased += 1

    def add_scouts(self, location_info: list[dict]) -> None:
        """Extend the internal scout cache with new ``LocationInfo`` entries."""
        self.stored_scouts.extend(location_info)

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _empty_shop_locations() -> dict:
        shops = ["Hephaestus", "Merlin", "Dungeon Master"]
        sides = ["Left", "Center", "Right"]
        return {
            shop: {side: {"Current": 1, "Slots": {}} for side in sides}
            for shop in shops
        }

import asyncio
import copy
import json
import random
import time
from typing import Dict, Any

from worlds.cotnd.Items import ItemType, item_from_code, TRAP_ITEMS_BY_COTND_ID
from worlds.cotnd.client.server import CotNDServer
from worlds.cotnd.client.save import CotNDSaveData
from worlds.cotnd.vendor_zstandard import load_vendored_zstandard

load_vendored_zstandard()

import ModuleUpdate
from CommonClient import ClientCommandProcessor, logger, CommonContext
from NetUtils import HintStatus, ClientStatus
from worlds.cotnd.Locations import (
    location_from_name,
    location_from_code,
    LocationType,
)
from worlds.cotnd.Utils import trap_name_to_value

ModuleUpdate.update()


class CotNDCommandProcessor(ClientCommandProcessor):
    def _cmd_deathlink(self):
        """Toggle deathlink."""
        if isinstance(self.ctx, CotNDContext):
            enabled = "DeathLink" not in self.ctx.tags
            asyncio.create_task(self.ctx.update_death_link(enabled), name="Update Deathlink")
            logger.info(f"DeathLink {'enabled' if enabled else 'disabled'}")
            asyncio.create_task(self.ctx.cotnd_server.send_packet({
                "datatype": "SetDeathLink",
                "deathlink": enabled,
            }))

    def _cmd_traplink(self):
        """Toggle traplink."""
        if isinstance(self.ctx, CotNDContext):
            enabled = "TrapLink" not in self.ctx.tags
            asyncio.create_task(self.ctx.update_trap_link(enabled), name="Update Traplink")
            logger.info(f"TrapLink {'enabled' if enabled else 'disabled'}")
            asyncio.create_task(self.ctx.cotnd_server.send_packet({
                "datatype": "SetTrapLink",
                "traplink": enabled,
            }))

    def _cmd_diamonds(self, amount: str = ""):
        """Set or adjust the player's AP diamond count. Usage: /diamonds <value> or /diamonds +/-<delta>"""
        if not isinstance(self.ctx, CotNDContext):
            return
        amount = amount.strip()
        if not amount:
            current = self.ctx.ap_savedata.diamonds
            if current is None:
                current = self.ctx.ap_savedata.ap_diamonds
            logger.info(f"Current diamonds: {current}")
            return
        try:
            if amount.startswith(("+", "-")):
                current = self.ctx.ap_savedata.diamonds
                if current is None:
                    current = self.ctx.ap_savedata.ap_diamonds
                new_value = current + int(amount)
            else:
                new_value = int(amount)
        except ValueError:
            logger.warning(f"Invalid diamond amount: {amount!r}. Use a number or +/-delta.")
            return
        new_value = max(0, new_value)
        self.ctx.ap_savedata.apply_change_diamonds(new_value)
        asyncio.create_task(self.ctx._persist_and_push())
        asyncio.create_task(self.ctx.cotnd_server.send_packet({
            "datatype": "SetDiamonds",
            "value": new_value,
        }))
        logger.info(f"Diamonds set to {new_value}")

    def _cmd_save(self):
        """Print the current DataStorage save blob."""
        if not isinstance(self.ctx, CotNDContext):
            return
        for line in json.dumps(self.ctx.ap_savedata.to_datastorage(), indent=2, default=str).splitlines():
            logger.info(line)


class CotNDContext(CommonContext):
    game = "Crypt of the NecroDancer"
    command_processor = CotNDCommandProcessor
    items_handling = 0b111

    def __init__(self, server_address, password):
        super().__init__(server_address, password)
        self.cotnd_server = CotNDServer(self)
        self.slotdata: dict[str, Any] = {}
        self.ap_savedata: CotNDSaveData = CotNDSaveData(self)
        # Index up to which items have been forwarded to the mod this session.
        self.last_forwarded_index: int = 0
        # Last item index the mod reported as already processed (from its State packet).
        self.game_last_received_index: int | None = None
        # Holds the State event payload while we wait for DataStorage retrieval.
        self._pending_state_data: dict | None = None
        self._hint_requested: bool = False

    # ------------------------------------------------------------------ #
    # GUI / auth                                                           #
    # ------------------------------------------------------------------ #

    def run_gui(self):
        from kvui import GameManager

        class CotNDManager(GameManager):
            logging_pairs = [
                ("Client", "Archipelago"),
                ("CotNDInterface", "Crypt of the NecroDancer"),
            ]
            base_title = "Archipelago Crypt of the NecroDancer Client"

        self.ui = CotNDManager(self)
        self.ui_task = asyncio.create_task(self.ui.async_run(), name="UI")

    async def server_auth(self, password_requested: bool = False):
        if password_requested and not self.password:
            await super(CotNDContext, self).server_auth(password_requested)
        await self.get_username()
        await self.send_connect()

    # ------------------------------------------------------------------ #
    # Tag management                                                       #
    # ------------------------------------------------------------------ #

    async def update_trap_link(self, trap_link: bool):
        old_tags = self.tags.copy()
        if trap_link:
            self.tags.add("TrapLink")
        else:
            self.tags -= {"TrapLink"}
        if old_tags != self.tags and self.server and not self.server.socket.closed:
            await self.send_msgs([{"cmd": "ConnectUpdate", "tags": self.tags}])

    # ------------------------------------------------------------------ #
    # Connection lifecycle                                                 #
    # ------------------------------------------------------------------ #

    async def disconnect(self, allow_autoreconnect: bool = False) -> None:
        try:
            await self.cotnd_server.send_packet({
                "datatype": "Disconnected",
                "reason": "Server shutting down",
            })
        except Exception as e:
            logger.warning(f"Failed to send disconnect notice: {e}")
        if self.cotnd_server.is_running():
            await self.cotnd_server.stop()
        await super().disconnect(allow_autoreconnect)

    def on_deathlink(self, data: Dict[str, str]):
        asyncio.create_task(self.cotnd_server.send_packet({
            "datatype": "Death",
            "msg": data.get("cause"),
            "source": data.get("source"),
        }))
        super().on_deathlink(data)

    # ------------------------------------------------------------------ #
    # AP server package dispatch                                           #
    # ------------------------------------------------------------------ #

    def on_package(self, cmd: str, args: Dict):
        try:
            match cmd:
                case "RoomInfo":
                    self.seed_name = args.get("seed_name")
                case "Connected":
                    self._on_connected(args)
                case "ReceivedItems":
                    self._on_received_items(args)
                case "Retrieved":
                    self._on_retrieved(args)
                case "LocationInfo":
                    self._on_location_info(args)
                case "PrintJSON":
                    self._on_print_json(args)
                case "Bounced":
                    self._on_bounced(args)
        except Exception as e:
            logger.error(f"CotND on_package error ({cmd}): {e}")
        return super().on_package(cmd, args)

    def _on_connected(self, args: dict):
        slot_data = args.get("slot_data")
        self.slotdata = slot_data if isinstance(slot_data, dict) else {}
        # Fresh save for this connection; restored from DataStorage on Retrieved.
        self.ap_savedata = CotNDSaveData(self)
        asyncio.create_task(self.send_msgs([{
            "cmd": "Get",
            "keys": [f"cotnd_{self.slot}_save"],
        }]))
        asyncio.create_task(self.update_death_link(bool(self.slotdata.get("death_link", False))))
        if self.slotdata.get("trap_link", False):
            self.tags.add("TrapLink")
        asyncio.create_task(self.cotnd_server.start(), name="CotNDServer")

    def _on_received_items(self, args: dict):
        """Forward newly received items to the mod and refresh computed save state."""
        new_items = self.items_received[self.last_forwarded_index:]
        indexed_items: list[dict] = []
        trap_items: list[str] = []

        for idx, netitem in enumerate(new_items, start=self.last_forwarded_index):
            try:
                item_info = item_from_code(netitem.item)
            except (KeyError, ValueError):
                continue
            indexed_items.append({
                "item": item_info.cotnd_id,
                "item_name": item_info.name,
                "location_code": str(netitem.location),
                "location_name": self.location_names.lookup_in_slot(netitem.location, self.slot),
                "playername": self.player_names[netitem.player],
                "ap_index": idx,
            })
            if "TrapLink" in self.tags and item_info.type == ItemType.TRAP and self._is_new_trap(args, idx):
                trap_items.append(item_info.name)

        self.last_forwarded_index = len(self.items_received)

        # Recompute all AP-derived save fields (health, zone access, diamonds, etc.).
        self.ap_savedata.refresh()

        if indexed_items:
            asyncio.create_task(self.cotnd_server.send_packet({
                "datatype": "Items",
                "items": indexed_items,
            }))
        if trap_items:
            asyncio.create_task(self.send_trap_links(trap_items))

        # Persist to DataStorage and push the updated state to the mod.
        asyncio.create_task(self._persist_and_push())

    def _is_new_trap(self, args: dict, idx: int) -> bool:
        """True if this trap item should be forwarded over TrapLink."""
        # Incremental delivery: index > 0 means this item is genuinely new.
        if args.get("index", 0) > 0:
            return True
        # Full resync: only send items the mod hasn't already processed.
        if self.game_last_received_index is not None:
            return idx >= self.game_last_received_index
        return False

    def _on_retrieved(self, args: dict):
        """Handle DataStorage Get responses for hint and save-state keys."""
        keys_dict = args.get("keys", {})
        self._handle_hint_retrieved(keys_dict)
        self._handle_save_retrieved(keys_dict)

    def _handle_hint_retrieved(self, keys_dict: dict):
        hints_key = f"_read_hints_{self.team}_{self.slot}"
        if not self._hint_requested or hints_key not in keys_dict:
            return
        self._hint_requested = False
        existing_hints = keys_dict.get(hints_key) or []
        hinted_locations = {hint["location"] for hint in existing_hints}
        candidates = [loc for loc in self.missing_locations if loc not in hinted_locations]
        if candidates:
            loc_id = random.choice(candidates)
            asyncio.create_task(self.send_msgs([{"cmd": "LocationScouts", "locations": [loc_id]}]))
            asyncio.create_task(self.send_msgs([{
                "cmd": "CreateHints",
                "locations": [loc_id],
                "status": HintStatus.HINT_UNSPECIFIED,
            }]))

    def _handle_save_retrieved(self, keys_dict: dict):
        save_key = f"cotnd_{self.slot}_save"
        if save_key not in keys_dict:
            return
        # Restore non-derivable state; derivable state is recomputed in _send_state.
        self.ap_savedata = CotNDSaveData.from_datastorage(keys_dict[save_key], self)
        if self._pending_state_data is not None:
            pending = self._pending_state_data
            self._pending_state_data = None
            asyncio.create_task(self._send_state(pending))

    def _on_location_info(self, args: dict):
        """Cache scouted location data into save and forward to mod."""
        locs = args.get("locations") or []
        location_info: list[dict] = []

        for loc in locs:
            try:
                location = location_from_code(loc.location)
            except (KeyError, ValueError):
                continue
            try:
                item = item_from_code(loc.item)
                item_cotnd_id = item.cotnd_id
                item_name = item.name
            except (KeyError, ValueError):
                item_cotnd_id = "APItem"
                item_name = self.item_names.lookup_in_slot(loc.item, loc.player)

            location_info.append({
                "location": location.name,
                "location_code": str(loc.location),
                "item": item_cotnd_id,
                "playername": self.player_names[loc.player],
                "itemname": item_name,
                "flags": loc.flags,
                "source": location.type.name.title(),
            })

        self.ap_savedata.add_scouts(location_info)
        # Partially refresh — only scout-derived fields need recomputing.
        self.ap_savedata.shop_locations = self.ap_savedata._compute_shop_locations()
        self.ap_savedata.codex_locations = self.ap_savedata._compute_codex_locations()
        self.ap_savedata.scouted_locations = bool(self.ap_savedata.stored_scouts)

        asyncio.create_task(self.cotnd_server.send_packet({
            "datatype": "LocationInfo",
            "location_info": location_info,
        }))
        asyncio.create_task(self._persist_and_push())

    def _on_print_json(self, args: dict):
        FORWARD_TYPES = {
            "Chat", "ServerChat", "CommandResult", "AdminCommandResult",
            "Tutorial", "Countdown",
        }
        msg_type = args.get("type")
        if msg_type not in FORWARD_TYPES:
            return
        message = self.rawjsontotextparser(copy.deepcopy(args["data"]))
        slot = args.get("slot", -1)
        if msg_type == "Chat":
            player = self.player_names[slot] if isinstance(slot, int) else "Unknown"
            prefix = player + ": "
            if message.startswith(prefix):
                message = message[len(prefix):]
        elif msg_type == "ServerChat":
            player = "Server"
        else:
            player = "Archipelago"
        asyncio.create_task(self.cotnd_server.send_packet({
            "datatype": "Chat",
            "msg": message,
            "player": player,
            "slot": slot if msg_type == "Chat" else None,
        }))

    def _on_bounced(self, args: dict):
        if (
            "TrapLink" not in self.tags
            or "TrapLink" not in args.get("tags", [])
            or self.slot is None
            or args.get("data", {}).get("source") == self.slot_info[self.slot].name
        ):
            return
        trap_name: str = args["data"].get("trap_name", "")
        mapping = trap_name_to_value.get(trap_name)
        if mapping is None:
            return
        if isinstance(mapping, tuple):
            handler_id, trap_args = mapping
        else:
            handler_id, trap_args = mapping, {}
        # Pool traps honor the player's weight opt-out; TrapLink-only traps
        # honor the traplink_excluded_traps option.
        pool_item = TRAP_ITEMS_BY_COTND_ID.get(handler_id)
        if pool_item is not None:
            if self.slotdata.get("trap_weights", {}).get(pool_item.name, 0) == 0:
                return
        elif handler_id in self.slotdata.get(
            "traplink_excluded_traps", ["InstantDeathTrap", "TutorialTrap"]
        ):
            return
        asyncio.create_task(self.cotnd_server.send_packet({
            "datatype": "Trap",
            "trap_name": handler_id,
            "args": trap_args,
        }))

    # ------------------------------------------------------------------ #
    # Mod event dispatch                                                   #
    # ------------------------------------------------------------------ #

    async def manage_event(self, datatype: str, data: dict[str, Any] | None = None):
        """Handle packets sent from the mod to the Python client."""
        data = data or {}
        try:
            match datatype:
                case "State":
                    # Mod is (re)connecting — defer full State response until
                    # DataStorage retrieval restores non-derivable save state.
                    game_index = data.get("game_last_received_index")
                    if game_index is not None:
                        self.game_last_received_index = int(game_index)
                    self._pending_state_data = data
                    if self.slot is not None:
                        await self.send_msgs([{
                            "cmd": "Get",
                            "keys": [f"cotnd_{self.slot}_save"],
                        }])
                    else:
                        # Not yet authenticated; send immediately with defaults.
                        self._pending_state_data = None
                        await self._send_state(data)

                case "Death":
                    if "DeathLink" in self.tags:
                        await self.send_death(str(data.get("msg", "")))

                case "Locations":
                    await self._event_locations(data)

                case "ScoutLocation":
                    loc_id = data.get("id")
                    if loc_id and (loc_id in self.missing_locations or loc_id in self.locations_checked):
                        await self.send_msgs([{"cmd": "LocationScouts", "locations": [loc_id]}])

                case "Hint":
                    if self.missing_locations:
                        self._hint_requested = True
                        await self.send_msgs([{
                            "cmd": "Get",
                            "keys": [f"_read_hints_{self.team}_{self.slot}"],
                        }])

                case "HintNpc":
                    await self._event_hint_npc(data)

                case "Chat":
                    await self.send_msgs([{"cmd": "Say", "text": str(data.get("msg", ""))}])

                case "Victory":
                    await self.send_msgs([{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}])

                case "ChangeDiamonds":
                    value = data.get("value")
                    if isinstance(value, (int, float)):
                        self.ap_savedata.apply_change_diamonds(value)
                        await self._persist_and_push()

                case "ChangeBuffs":
                    self.ap_savedata.apply_change_buffs(buffs=data.get("buffs"))
                    await self._persist_and_push()

                case "ChangeRunItems":
                    self.ap_savedata.apply_change_run_items(
                        banned_items=data.get("bannedItems"),
                        next_run_items=data.get("nextRunItems"),
                    )
                    await self._persist_and_push()

                case _:
                    return
        except Exception as e:
            logger.error(f"Manage event error ({datatype}): {e}")

    async def _event_locations(self, data: dict):
        """Resolve location names from the mod and send LocationChecks to AP."""
        locs = data.get("sources")
        if locs is not None:
            resolved_ids: list[int] = []
            for name in locs:
                try:
                    code = location_from_name(name).code
                    if code is not None:
                        resolved_ids.append(code)
                except (KeyError, ValueError):
                    logger.warning(f"Unknown CotND location from mod: {name}")
            self.locations_checked.update(resolved_ids)

        await self.send_msgs([{"cmd": "LocationChecks", "locations": self.locations_checked}])

        # Recompute fields that depend on the checked-locations set.
        # Pass locations_checked (locally updated) so the new IDs are included before
        # the server echoes them back via RoomUpdate (which updates checked_locations).
        self.ap_savedata.character_locations = self.ap_savedata._compute_character_locations(
            extra_checked_locs=self.locations_checked,
        )
        self.ap_savedata.shop_consumed_locations = self.ap_savedata._compute_shop_consumed()
        self.ap_savedata.unlocked_npcs = self.ap_savedata._compute_unlocked_npcs()
        self.ap_savedata.shop_locations = self.ap_savedata._compute_shop_locations()
        self.ap_savedata.codex_locations = self.ap_savedata._compute_codex_locations()
        await self._persist_and_push()

    async def _event_hint_npc(self, data: dict):
        loc_code = data.get("location_code")
        player_slot = data.get("player_slot")
        if loc_code is None or player_slot is None:
            return
        try:
            await self.send_msgs([{
                "cmd": "CreateHints",
                "locations": [int(loc_code)],
                "player": int(player_slot),
                "status": HintStatus.HINT_UNSPECIFIED,
            }])
            self.ap_savedata.on_hint_purchased()
            await self._persist_and_push()
        except (ValueError, TypeError):
            logger.warning(
                f"HintNpc: invalid location_code={loc_code!r} player_slot={player_slot!r}"
            )

    # ------------------------------------------------------------------ #
    # Save management                                                      #
    # ------------------------------------------------------------------ #

    async def _persist_save(self):
        """Write the full save snapshot to AP DataStorage."""
        if self.slot is None:
            return
        if not self.ap_savedata.datastorage_loaded:
            return
        await self.send_msgs([{
            "cmd": "Set",
            "key": f"cotnd_{self.slot}_save",
            "default": {},
            "operations": [{"operation": "replace", "value": self.ap_savedata.to_datastorage()}],
            "want_reply": False,
        }])

    async def _push_save_update(self):
        """Send a SaveUpdate packet to the mod with the current save state."""
        await self.cotnd_server.send_packet({
            "datatype": "SaveUpdate",
            **self.ap_savedata.to_state_fields(),
        })

    async def _persist_and_push(self):
        """Persist to DataStorage and push the updated state to the mod."""
        await self._persist_save()
        await self._push_save_update()

    # ------------------------------------------------------------------ #
    # State packet                                                         #
    # ------------------------------------------------------------------ #

    async def _send_state(self, data: dict):
        """Build and send the full State packet to the mod.

        On init (data["init"] is True) the packet also carries all slot
        config so the mod can initialise its settings.  On reconnect only
        current AP state is sent so the mod can resync without reinitialising.
        """
        is_init = bool(data.get("init", False))
        self.ap_savedata.refresh()

        items_list: list[dict] = []
        for idx, net_item in enumerate(self.items_received):
            try:
                item = item_from_code(net_item.item)
            except (KeyError, ValueError):
                continue
            items_list.append({
                "item": item.cotnd_id,
                "item_name": item.name,
                "location_code": str(net_item.location),
                "location_name": self.location_names.lookup_in_slot(net_item.location, self.slot),
                "playername": self.player_names[net_item.player],
                "ap_index": idx,
            })
        self.last_forwarded_index = len(self.items_received)

        state_packet: dict[str, Any] = {
            "datatype": "State",
            "init": is_init,
            "deathlink": "DeathLink" in self.tags,
            "traplink": "TrapLink" in self.tags,
            "hint_cost": self.hint_cost,
            "missing_locations": [location_from_code(loc).name for loc in self.missing_locations],
            "checked_locations": [location_from_code(loc).name for loc in self.checked_locations],
            "world_version": self.slotdata.get("world_version", ""),
            "items": items_list,
            **self.ap_savedata.to_state_fields(),
        }

        if is_init:
            state_packet.update(self._build_init_config())
            # Scout all shop and tutorial locations so save data can be populated.
            await self.send_msgs([{
                "cmd": "LocationScouts",
                "locations": [
                    loc_id for loc_id in self.missing_locations
                    if location_from_code(loc_id).type in (LocationType.SHOP, LocationType.TUTORIAL)
                ],
            }])

        await self.cotnd_server.send_packet(state_packet)

        # Persist on init so DataStorage immediately reflects the full snapshot.
        if is_init:
            await self._persist_save()

    def _build_init_config(self) -> dict:
        """Slot config fields added to the State packet on first init only."""
        sd = self.slotdata
        death_link_type = sd.get("death_link_type", 1)
        if death_link_type == 0:
            death_link_type_str = "Absolute"
        elif death_link_type == 2:
            death_link_type_str = "Marv"
        else:
            death_link_type_str = "Tempo"

        goal_int = sd.get("goal")
        if goal_int == 0:
            goal_str = "All Zones"
            goal_required = sd.get("all_zones_goal_clear")
        elif goal_int == 2:
            goal_str = "Golden Lute Shards"
            goal_required = sd.get("golden_lute_shards_goal_clear")
        else:
            goal_str = "Zones"
            goal_required = sd.get("zones_goal_clear")

        return {
            "goal": goal_str,
            "goal_required": goal_required,
            "death_link_type": death_link_type_str,
            "per_level_checks": sd.get("floor_clear_checks", 0) != 0,
            "included_extra_modes": sd.get("included_extra_modes"),
            "dlc": sd.get("dlc"),
            "character_blacklist": sd.get("character_blacklist"),
            "character_unlocks": sd.get("character_unlocks"),
            "include_unique_items": sd.get("include_unique_items"),
            "zone_access_keys": sd.get("zone_access_keys"),
            "starting_zone": sd.get("starting_zone"),
            "lock_character_room": sd.get("lock_character_room"),
            "buff_items": sd.get("buff_items"),
            "victory_trigger": sd.get("victory_trigger"),
            "expensive_purchase_price": sd.get("expensive_purchase_price"),
            "caged_npc_locations": sd.get("caged_npc_locations"),
            "npc_hint_locations": sd.get("npc_hint_locations"),
            "pricing": {
                "type": sd.get("price_randomization"),
                "general_price_range": {
                    "min": sd.get("randomized_price_min"),
                    "max": sd.get("randomized_price_max"),
                },
                "filler_price_range": {
                    "min": sd.get("filler_price_min"),
                    "max": sd.get("filler_price_max"),
                },
                "useful_price_range": {
                    "min": sd.get("useful_price_min"),
                    "max": sd.get("useful_price_max"),
                },
                "progression_price_range": {
                    "min": sd.get("progression_price_min"),
                    "max": sd.get("progression_price_max"),
                },
            },
        }

    # ------------------------------------------------------------------ #
    # TrapLink                                                             #
    # ------------------------------------------------------------------ #

    async def send_trap_links(self, traps: list[str]):
        if "TrapLink" not in self.tags or self.slot is None:
            return
        for trap_name in traps:
            await self.send_msgs([{
                "cmd": "Bounce",
                "tags": ["TrapLink"],
                "data": {
                    "time": time.time(),
                    "source": self.player_names[self.slot],
                    "trap_name": trap_name,
                },
            }])
            logger.info(f"Sent linked {trap_name}")

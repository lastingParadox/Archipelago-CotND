import asyncio
import copy
import json
import os
import platform
import random
import struct
import time
import urllib.parse
from typing import Dict, Set, Any

import Utils
from worlds.cotnd.Items import ItemType, item_from_code
from worlds.cotnd.vendor_zstandard import load_vendored_zstandard

_apworld_custom = os.path.join(Utils.user_path(), "custom_worlds", "cotnd.apworld")
_apworld_builtin = os.path.join(Utils.local_path(), "worlds", "cotnd.apworld")
load_vendored_zstandard(_apworld_custom if os.path.exists(_apworld_custom) else _apworld_builtin)

import zstandard

import ModuleUpdate
from CommonClient import ClientCommandProcessor, logger, CommonContext, get_base_parser
from NetUtils import HintStatus, ClientStatus
from Utils import init_logging
from worlds.cotnd.Locations import (
    location_from_name,
    location_from_code,
    LocationType,
)
from worlds.cotnd.Utils import trap_name_to_value

ModuleUpdate.update()
system = platform.system()

if __name__ == '__main__':
    init_logging("CotNDClient", exception_logger="Client")


def get_data_folder_path():
    """Grabs the Archipelago data folder path for Crypt of the NecroDancer. Creates the directory if it does not exist."""
    if system == 'Windows':
        data_path = os.path.expandvars('%LOCALAPPDATA%\\NecroDancer')
    elif system == 'Darwin':
        data_path = os.path.expanduser('~/Library/Application Support/NecroDancer')
    elif system == 'Linux':
        default_path = os.path.expanduser('~/.local/share/NecroDancer')
        flatpak_path = os.path.expanduser('~/.var/app/com.valvesoftware.Steam/.local/share/NecroDancer')

        if os.path.exists(flatpak_path):
            data_path = flatpak_path
        else:
            data_path = default_path
    else:
        logger.error(f'Unrecognized operating system {system}, please report.')
        raise RuntimeError(f'Unsupported operating system: {system}')

    """in.json sends data into the game. out.json gets data out from the game."""
    if not os.path.exists(data_path):
        message = (f'No local data found for NecroDancer at {data_path}. '
                   'Please install and run Crypt of the NecroDancer before attempting to run this client.')
        logger.error(message)
        raise FileNotFoundError(message)

    ap_path = os.path.join(data_path, 'archipelago')
    if not os.path.isdir(ap_path):
        os.mkdir(ap_path)

    return ap_path


class CotNDCommandProcessor(ClientCommandProcessor):
    def _cmd_deathlink(self):
        """Toggle deathlink."""
        if isinstance(self.ctx, CotNDContext):
            death_link_enabled = "DeathLink" not in self.ctx.tags
            asyncio.create_task(self.ctx.update_death_link(death_link_enabled), name="Update Deathlink")
            logger.info(f"DeathLink {'enabled' if death_link_enabled else 'disabled'}")
            asyncio.create_task(self.ctx.cotnd_server.send_packet({
                "datatype": "SetDeathLink",
                "deathlink": death_link_enabled
            }))
    def _cmd_traplink(self):
        """Toggle traplink."""
        if isinstance(self.ctx, CotNDContext):
            trap_link_enabled = "TrapLink" not in self.ctx.tags
            asyncio.create_task(self.ctx.update_trap_link(trap_link_enabled), name="Update Traplink")
            logger.info(f"TrapLink {'enabled' if trap_link_enabled else 'disabled'}")
            asyncio.create_task(self.ctx.cotnd_server.send_packet({
                "datatype": "SetTrapLink",
                "traplink": trap_link_enabled
            }))


class CotNDContext(CommonContext):
    game = "Crypt of the NecroDancer"
    command_processor = CotNDCommandProcessor
    items_handling = 0b111

    def __init__(self, server_address, password):
        super().__init__(server_address, password)
        self.cotnd_server = CotNDServer(self)

        self.slotdata: dict[str, Any] = {}
        self.connected_to_ap = False
        self.last_received_index = 0
        self.game_last_received_index: int | None = None
        self.stored_save_data: list[str] = []
        self._hint_requested: bool = False

    def run_gui(self):
        from kvui import GameManager

        class CotNDManager(GameManager):
            logging_pairs = [
                ("Client", "Archipelago"),
                ("CotNDInterface", "Crypt of the NecroDancer")
            ]
            base_title = "Archipelago Crypt of the NecroDancer Client"

        self.ui = CotNDManager(self)
        self.ui_task = asyncio.create_task(self.ui.async_run(), name="UI")

    async def server_auth(self, password_requested: bool = False):
        if password_requested and not self.password:
            await super(CotNDContext, self).server_auth(password_requested)
        await self.get_username()
        await self.send_connect()

    async def update_trap_link(self, trap_link: bool):
        old_tags = self.tags.copy()
        if trap_link:
            self.tags.add("TrapLink")
        else:
            self.tags -= {"TrapLink"}
        if old_tags != self.tags and self.server and not self.server.socket.closed:
            await self.send_msgs([{"cmd": "ConnectUpdate", "tags": self.tags}])

    async def disconnect(self, allow_autoreconnect: bool = False):
        try:
            await self.cotnd_server.send_packet({
                "datatype": "Disconnected",
                "reason": "Server shutting down"
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

    def on_package(self, cmd: str, args: Dict):
        try:
            # Sent to client upon connecting to AP server
            if cmd == "RoomInfo":
                self.seed_name = args.get("seed_name")
            # Sent to client when the connection handshake is completed
            elif cmd == "Connected":
                self.connected_to_ap = True
                slot_data = args.get("slot_data")
                self.slotdata = slot_data if isinstance(slot_data, dict) else {}
                asyncio.create_task(self.update_death_link(bool(self.slotdata.get("death_link", False))))

                if self.slotdata.get("trap_link", False):
                    self.tags.add("TrapLink")

                logger.info("[CotNDServer] Starting server...")
                asyncio.create_task(
                    self.cotnd_server.start(),
                    name="CotNDServer"
                )
            # Sent to client when they receive an item
            elif cmd == "ReceivedItems":
                new_items = self.items_received[self.last_received_index:]
                print(f"New Items: {new_items}, Index: {self.last_received_index}")
                indexed_items = []
                trap_items: list[str] = []

                for idx, netitem in enumerate(new_items, start=self.last_received_index):
                    item_info = item_from_code(netitem.item)
                    indexed_items.append({
                        "item": item_info.cotnd_id,
                        "item_name": item_info.name,
                        "location_code": str(netitem.location),
                        "location_name": self.location_names.lookup_in_slot(netitem.location, self.slot),
                        "playername": self.player_names[netitem.player],
                        "ap_index": idx
                    })

                    if "TrapLink" in self.tags and item_info.type == ItemType.TRAP:
                        if args.get("index", 0) > 0:
                            # Incremental update — item is genuinely new this session
                            trap_items.append(item_info.name)
                        elif self.game_last_received_index is not None and idx >= self.game_last_received_index:
                            # Full resync — only forward items the mod hasn't processed yet
                            trap_items.append(item_info.name)

                self.last_received_index = len(self.items_received)

                asyncio.create_task(self.cotnd_server.send_packet({
                    "datatype": "Items",
                    "items": indexed_items,
                }))

                if len(trap_items) > 0:
                    asyncio.create_task(self.send_trap_links(trap_items))

            # Sent to client as a response to a "Get" package
            elif cmd == "Retrieved":
                keys_dict = args.get("keys", {})

                # If this is a response to a hint request, pick an unhinted missing location and create the hint.
                hints_key = f"_read_hints_{self.team}_{self.slot}"
                if self._hint_requested and hints_key in keys_dict:
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
                            "status": HintStatus.HINT_UNSPECIFIED
                        }]))

                # Restore player-verified checked locations from server storage.
                save_key = f"cotnd_{self.slot}_save"
                if save_key in keys_dict:
                    stored = keys_dict[save_key]
                    self.stored_save_data = stored if isinstance(stored, list) else []


            # Send to client when acknowledging LocationScouts packet, responding with item in location being scouted
            elif cmd == "LocationInfo":
                locs = args.get("locations") or []
                location_info = []
                for loc in locs:
                    location = location_from_code(loc.location)
                    try:
                        item = item_from_code(loc.item)
                        item_cotnd_id = item.cotnd_id
                        item_name = item.name
                    except (KeyError, ValueError):
                        # Unknown AP item code for this world, use generic metadata.
                        item_cotnd_id = "APItem"
                        item_name = self.item_names.lookup_in_slot(loc.item, loc.player)

                    source = "Hint"
                    if location.type is LocationType.SHOP:
                        source = "Shop"
                    elif location.type is LocationType.TUTORIAL:
                        source = "Tutorial"

                    location_info.append({
                        "location": location.name,
                        "location_code": str(loc.location),
                        "item": item_cotnd_id,
                        "playername": self.player_names[loc.player],
                        "itemname": item_name,
                        "flags": loc.flags,
                        "source": source,
                    })

                asyncio.create_task(self.cotnd_server.send_packet({
                    "datatype": "LocationInfo",
                    "location_info": location_info,
                }))

            # Sent to client purely to display a message to the player.
            elif cmd == "PrintJSON":
                msg_type = args.get("type")
                FORWARD_TYPES = {
                    "Chat", "ServerChat", "CommandResult", "AdminCommandResult",
                    "Tutorial", "Countdown",
                }
                if msg_type not in FORWARD_TYPES:
                    return

                # Flatten the structured data array to plain text.
                message = self.rawjsontotextparser(copy.deepcopy(args["data"]))

                if msg_type == "Chat":
                    slot = args.get("slot")
                    player = self.player_names[slot] if isinstance(slot, int) else "Unknown"
                elif msg_type == "ServerChat":
                    player = "Server"
                else:
                    # CommandResult, AdminCommandResult, Tutorial, Countdown, etc.
                    player = "Archipelago"

                asyncio.create_task(self.cotnd_server.send_packet({
                    "datatype": "Chat",
                    "msg": message,
                    "player": player,
                }))

            # TrapLink handling is still in progress.
            elif cmd == "Bounced" and "TrapLink" in self.tags and "TrapLink" in args.get("tags", []) and self.slot is not None and args.get("data", {}).get("source") != self.slot_info[self.slot].name:
                trap_name: str = args["data"]["trap_name"]
                if trap_name not in trap_name_to_value:
                    return

                cotnd_trap = trap_name_to_value[trap_name]

                if "trap_weights" not in self.slotdata or f"{cotnd_trap}" not in self.slotdata["trap_weights"]:
                    return
                
                if self.slotdata["trap_weights"][cotnd_trap] == 0:
                    return

                cotnd_trap = cotnd_trap.replace(" ", "")

                if cotnd_trap == "WIDETrap":
                    cotnd_trap = "WideTrap"

                asyncio.create_task(self.cotnd_server.send_packet({
                    "datatype": "Trap",
                    "trap_name": cotnd_trap
                }))

        except Exception as e:
            logger.error(f"CotND on_package error: {e}")
            print(e)

        return super().on_package(cmd, args)
    
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
                    "trap_name": trap_name
                }
            }])
            logger.info(f"Sent linked {trap_name}")


    async def manage_event(self, datatype: str, data: dict[str, Any] | None = None):
        data = data or {}
        try:
            match datatype:
                case "State":
                    goal, goal_required = ("All Zones", self.slotdata.get("all_zones_goal_clear")) if self.slotdata.get(
                        "goal") == 0 else ("Zones", self.slotdata.get("zones_goal_clear"))

                    game_index = data.get("game_last_received_index")
                    if game_index is not None:
                        self.game_last_received_index = int(game_index)

                    print("Sending randomizer data to CotND")

                    state_packet = {
                        "datatype": "State",
                        "deathlink": bool("DeathLink" in self.tags),
                        "traplink": bool("TrapLink" in self.tags),
                        "hint_cost": self.hint_cost,
                        "missing_locations": list(
                            [location_from_code(location).name for location in self.missing_locations]),
                        "checked_locations": self.stored_save_data,
                    }

                    items_list = []
                    for idx, net_item in enumerate(self.items_received):
                        item = item_from_code(net_item.item)
                        items_list.append({
                            "item": item.cotnd_id,
                            "item_name": item.name,
                            "location_code": str(net_item.location),
                            "location_name": self.location_names.lookup_in_slot(net_item.location, self.slot),
                            "playername": self.player_names[net_item.player],
                            "ap_index": idx
                        })

                    state_packet["items"] = items_list
                    state_packet["world_version"] = self.slotdata.get("world_version", "")
                    self.last_received_index = len(self.items_received)
                    # If the initial state, send initial state + search for shop locations
                    if data.get("init", False):

                        death_link_type = self.slotdata.get("death_link_type", 1)
                        if death_link_type == 0:
                            death_link_type = "Absolute"
                        elif death_link_type == 2:
                            death_link_type = "Marv"
                        else:
                            death_link_type = "Tempo"

                        state_packet.update({
                            "goal": goal,
                            "goal_required": goal_required,
                            "death_link_type": death_link_type,
                            "per_level_checks": False if self.slotdata.get("floor_clear_checks") == 0 else True,
                            "extra_modes": self.slotdata.get("included_extra_modes"),
                            "dlc": self.slotdata.get("dlc"),
                            "character_blacklist": self.slotdata.get("character_blacklist"),
                            "character_unlocks": self.slotdata.get("character_unlocks"),
                            "include_unique_items": self.slotdata.get("include_unique_items"),
                            "zone_access_keys": self.slotdata.get("zone_access_keys"),
                            "starting_zone": self.slotdata.get("starting_zone"),
                            "lock_character_room": self.slotdata.get("lock_character_room"),
                            "caged_npc_locations": self.slotdata.get("caged_npc_locations"),
                            "pricing": {
                                "type": self.slotdata.get("price_randomization"),
                                "general_price_range": {
                                    "min": self.slotdata.get("randomized_price_min"),
                                    "max": self.slotdata.get("randomized_price_max"),
                                },
                                "filler_price_range": {
                                    "min": self.slotdata.get("filler_price_min"),
                                    "max": self.slotdata.get("filler_price_max"),
                                },
                                "useful_price_range": {
                                    "min": self.slotdata.get("useful_price_min"),
                                    "max": self.slotdata.get("useful_price_max"),
                                },
                                "progression_price_range": {
                                    "min": self.slotdata.get("progression_price_min"),
                                    "max": self.slotdata.get("progression_price_max"),
                                },
                            },
                        })

                        # Scout shop and codex tutorial locations on initial sync
                        await self.send_msgs([{
                            "cmd": "LocationScouts",
                            "locations": [
                                location_id
                                for location_id in self.missing_locations
                                if (
                                    location_from_code(location_id).type
                                    in (LocationType.SHOP, LocationType.TUTORIAL)
                                )
                            ]
                        }])

                    await self.cotnd_server.send_packet(state_packet)

                    # Retrieve stored save data so we can restore player-verified checks on reconnect.
                    await self.send_msgs([{
                        "cmd": "Get",
                        "keys": [
                            f"cotnd_{self.slot}_save",
                        ]
                    }])
                case "Death":
                    print("Sending a death!", self.tags)
                    if "DeathLink" in self.tags:
                        await self.send_death(str(data.get("msg", "")))
                case "Locations":
                    locs = data.get("sources")
                    if locs is not None:
                        resolved_ids = []
                        for name in locs:
                            try:
                                loc_code = location_from_name(name).code
                            except (KeyError, ValueError):
                                logger.warning(f"Unknown CotND location from mod: {name}")
                                continue

                            if loc_code is not None:
                                resolved_ids.append(loc_code)

                        self.locations_checked.update(resolved_ids)
                    await self.send_msgs([{"cmd": "LocationChecks", "locations": self.locations_checked}])

                    # Persist only the checks the player actually made so reconnects and other
                    # players' releases cannot contaminate the save data with unearned progress.
                    if self.slot is not None:
                        checked_names: list[str] = []
                        for loc_id in self.locations_checked:
                            try:
                                checked_names.append(location_from_code(loc_id).name)
                            except (KeyError, ValueError):
                                pass
                        self.stored_save_data = checked_names
                        await self.send_msgs([{
                            "cmd": "Set",
                            "key": f"cotnd_{self.slot}_save",
                            "default": [],
                            "operations": [{"operation": "replace", "value": checked_names}],
                            "want_reply": False
                        }])
                case "ScoutLocation":
                    loc_id = data.get("id")
                    if loc_id and (loc_id in self.missing_locations or loc_id in self.locations_checked):
                        await self.send_msgs([{
                            "cmd": "LocationScouts",
                            "locations": [loc_id]
                        }])
                case "Hint":
                    if not self.missing_locations:
                        return

                    self._hint_requested = True
                    await self.send_msgs([{
                        "cmd": "Get",
                        "keys": [f"_read_hints_{self.team}_{self.slot}"],
                    }])
                case "Chat":
                    await self.send_msgs([{"cmd": "Say", "text": str(data.get("msg", ""))}])
                case "Victory":
                    await self.send_msgs([{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}])
                case _:
                    return
        except Exception as e:
            logger.error(f"Manage event error ({datatype}): {e}")


def _encode_prefix_uint32(n: int) -> bytes:
    if n <= 0xdf:
        return bytes([n])
    elif n <= 0x1fdf:
        first = 0xe0 | (((n - 0xe0) >> 8) & 0x1f)
        second = (n - 0xe0) & 0xff
        return bytes([first, second])
    else:
        return bytes([0xff]) + struct.pack("<I", n)


def _decode_luajit_string(buf: bytes) -> bytes:
    if not buf:
        raise ValueError("Empty LuaJIT string buffer")
    b0 = buf[0]
    if b0 <= 0xdf:
        return buf[1:]
    elif b0 <= 0xff:
        return buf[2:]
    else:
        return buf[5:]


class CotNDPacket:
    def __init__(self, json_str: str):
        packet = json.loads(json_str)
        self.datatype = packet.get("datatype", None)
        for k, v in packet.items():
            if k != "datatype":
                setattr(self, k, v)


class CotNDServer:
    def __init__(self, ctx: CotNDContext):
        self.ctx = ctx
        self.host = "127.0.0.1"
        self.port = 0
        self._server: asyncio.AbstractServer | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._write_lock = asyncio.Lock()
        self.data_path = get_data_folder_path()
        self.cotnd_connected = False
        self._zstd_dctx = zstandard.ZstdDecompressor(
            format=zstandard.FORMAT_ZSTD1_MAGICLESS
        )
        self._zstd_cctx = zstandard.ZstdCompressor(level=3)

    async def send_packet(self, packet: dict):
        if not self.cotnd_connected or self._writer is None:
            print(f"[CotNDServer] WARNING: Not sending message as CotND isn't connected!")
            return

        packet["timestamp"] = time.time()
        await self._send_json(packet)

    async def _send_json(self, obj: dict):
        payload = json.dumps(obj, separators=(",", ":")).encode("utf-8")
        print(f"[CotNDServer] Sending {obj}")
        await self._send_bytes(payload)

    async def _send_bytes(self, payload: bytes):
        writer = self._writer
        if writer is None or writer.is_closing():
            return

        # 1) Serialize string in LuaJIT format (prefix .U + payload)
        serialized = _encode_prefix_uint32(len(payload) + 0x20) + payload
        # 2) Compress magicless
        # compress_magicless must produce magicless zstd frame
        compressed = self._zstd_cctx.compress(serialized)[4:]
        # 3) Prefix length (big-endian uint32)
        header = struct.pack(">I", len(compressed))

        # 4) Serialize writes: concurrent drain() is unsafe on Python < 3.10.
        #    Multiple tasks (LocationInfo, ReceivedItems, PrintJSON, etc.) can all
        #    call send_packet concurrently via asyncio.create_task; the lock ensures
        #    only one write+drain pair is in flight at a time.
        async with self._write_lock:
            writer.write(header + compressed)
            await writer.drain()

    async def _safe_close_writer(self):
        writer = self._writer
        self._writer = None  # Detach FIRST

        if not writer:
            return

        try:
            writer.close()
            try:
                await writer.wait_closed()
            except (ConnectionResetError, ConnectionAbortedError):
                pass  # NORMAL on Windows
        except Exception:
            pass

    async def _handle_client(self, reader, writer):
        addr = writer.get_extra_info("peername")
        print(f"[CotNDServer] Connection from {addr}")
        logger.info("Connected to Crypt of the NecroDancer")

        if self._writer is not None:
            print("[CotNDServer] Rejecting second client")
            writer.close()
            await writer.wait_closed()
            return

        self._writer = writer
        handshake_done = False

        try:
            while True:
                header = await reader.readexactly(4)
                length = struct.unpack(">I", header)[0]
                raw = await reader.readexactly(length)
                if not handshake_done:
                    identity = raw.decode("utf-8", errors="replace")
                    print(f"[CotNDServer] Client identity: {identity}")
                    self.cotnd_connected = True
                    # Send a new framed response
                    player_name = self.ctx.player_names[self.ctx.slot] if self.ctx.slot is not None else ""
                    await self.send_packet(
                        {"datatype": "Handshake", "seed": self.ctx.seed_name,
                         "playerName": player_name})
                    handshake_done = True
                    continue

                print(f"[CotNDServer] Received Raw Message ({length} bytes): {raw}")

                with self._zstd_dctx.stream_reader(raw) as dreader:
                    decompressed = dreader.read()

                if not decompressed:
                    raise asyncio.IncompleteReadError(
                        partial=decompressed,
                        expected=1
                    )

                payload = _decode_luajit_string(decompressed)
                print(f"[CotNDServer] Received Message ({length} bytes): {payload}")
                packet = CotNDPacket(payload.decode("utf-8"))
                await self.process_input(packet)

        except (asyncio.IncompleteReadError, ConnectionResetError, ConnectionAbortedError):
            logger.info("[CotNDServer] Client disconnected")
        except Exception:
            logger.exception("[CotNDServer] Unexpected client error")
        finally:
            print(f"[CotNDServer] Disconnected {addr}")
            logger.info("Disconnected from Crypt of the NecroDancer (Reason: Mod Disconnect)")
            self.cotnd_connected = False
            await self._safe_close_writer()

    async def process_input(self, packet: CotNDPacket):
        datatype = packet.datatype
        match datatype:
            case "State":
                init = bool(getattr(packet, "init", False))
                game_index = getattr(packet, "last_ap_index", None)
                await self.ctx.manage_event(datatype, {"init": init, "game_last_received_index": game_index})
            case "Victory":
                if not self.ctx.finished_game:
                    await self.ctx.manage_event(datatype)
            case "Locations":
                raw_sources = getattr(packet, "sources", []) or []
                source_names: set[str] = set()

                for source in raw_sources:
                    if isinstance(source, str):
                        source_names.add(source)
                    elif isinstance(source, int):
                        try:
                            source_names.add(location_from_code(source).name)
                        except (KeyError, ValueError):
                            continue

                if len(source_names):
                    await self.ctx.manage_event(datatype, {"sources": list(source_names)})
            case "Death" | "Chat":
                message = str(getattr(packet, "msg", "") or "")
                await self.ctx.manage_event(datatype, {"msg": message})
            case "Hint":
                hint_type = getattr(packet, "type", "Random") or "Random"
                await self.ctx.manage_event(datatype, {"type": hint_type})
            case "Disconnected" | "Disconnect":
                await self.ctx.manage_event("Disconnected")
            case "SetDeathLink":
                enabled = bool(getattr(packet, "deathlink", False))
                asyncio.create_task(self.ctx.update_death_link(enabled), name="Update DeathLink")
                asyncio.create_task(self.ctx.cotnd_server.send_packet({
                    "datatype": "SetDeathLink",
                    "deathlink": enabled
                }))
            case "SetTrapLink":
                enabled = bool(getattr(packet, "traplink", False))
                asyncio.create_task(self.ctx.update_trap_link(enabled), name="Update TrapLink")
                asyncio.create_task(self.ctx.cotnd_server.send_packet({
                    "datatype": "SetTrapLink",
                    "traplink": enabled
                }))
            case _:
                return

    async def start(self):
        if self._server is not None:
            return  # Server's already started

        self._server = await asyncio.start_server(
            self._handle_client,
            host=self.host,
            port=self.port
        )
        sock = self._server.sockets[0]
        self.port = sock.getsockname()[1]
        print(f"[CotNDServer] Listening on {self.host}:{self.port}")

        with open(self.data_path + "/port.txt", "w") as f:
            f.write(str(self.port))

        asyncio.create_task(self._server.serve_forever(), name="CotNDServer")

    async def stop(self):
        if not self._server:
            return

        with open(self.data_path + "/port.txt", "w") as _:
            pass

        logger.info("[CotNDServer] Shutting down")
        self._server.close()

        try:
            await self._server.wait_closed()
        except Exception as e:
            logger.error(f"[CotNDServer] Error closing server: {e}")
        self._server = None
        self.cotnd_connected = False

    def is_running(self):
        return self._server is not None

    def get_port(self) -> int:
        return self.port


async def main(args):
    ctx = CotNDContext(args.connect, args.password)
    ctx.auth = args.name
    ctx.run_gui()

    await ctx.exit_event.wait()
    await ctx.shutdown()


def launch():
    import colorama

    parser = get_base_parser(description="CotND Archipelago Client for interfacing with Crypt of the NecroDancer.")
    parser.add_argument("--name", default=None, help="Slot Name to connect as.")
    parser.add_argument("url", nargs="?", help="Archipelago connection url")
    args = parser.parse_args()

    if args.url:
        url = urllib.parse.urlparse(args.url)
        args.connect = url.netloc
        if url.username:
            args.name = urllib.parse.unquote(url.username)
        if url.password:
            args.password = urllib.parse.unquote(url.password)

    colorama.init()

    asyncio.run(main(args))
    colorama.deinit()

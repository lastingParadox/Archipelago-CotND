import asyncio
import json
import os
import platform
import random
import struct
import time
import urllib.parse
from typing import Dict, Set, Any

import Utils
from worlds.cotnd.Items import item_from_code
from worlds.cotnd.vendor_zstandard import load_vendored_zstandard

load_vendored_zstandard(os.path.join(Utils.user_path(), "custom_worlds", "cotnd.apworld"))

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
            logger.info(f"Deathlink {'enabled' if death_link_enabled else 'disabled'}")
            self.ctx.cotnd_server.send_packet({
                "datatype": "SetDeathLink",
                "deathlink": death_link_enabled
            })


class CotNDContext(CommonContext):
    game = "Crypt of the NecroDancer"
    command_processor = CotNDCommandProcessor
    items_handling = 0b111

    def __init__(self, server_address, password):
        super().__init__(server_address, password)
        self.cotnd_server = CotNDServer(self)

        self.slotdata: Dict[str, str | int] = {}
        self.connected_to_ap = False
        self.location_hints_remaining = {}
        self.last_received_index = 0

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
                self.slotdata = args.get("slot_data")
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

                # Update hint counts if this location was hinted
                for netitem in new_items:
                    loc_str = netitem.location
                    for k, locs in self.location_hints_remaining.items():
                        if loc_str in locs:
                            locs.discard(loc_str)
                            break

                self.last_received_index = len(self.items_received)
                counts = {k: len(v) for k, v in self.location_hints_remaining.items()}

                asyncio.create_task(self.cotnd_server.send_packet({
                    "datatype": "Items",
                    "items": indexed_items,
                    "location_hint_amounts": counts,
                }))

            # Sent to client as a response to a "Get" package (used for determining stored hints)
            elif cmd == "Retrieved":
                keys_dict = args.get("keys", {})

                my_hints = keys_dict.get(f"_read_hints_{self.team}_{self.slot}", [])
                hinted_locations = {hint["location"] for hint in my_hints}

                for k, locs in self.location_hints_remaining.items():
                    locs.difference_update(self.checked_locations)
                    locs.difference_update(hinted_locations)

            # Sent when there is a need to update info about the present game session
            elif cmd == "RoomUpdate":
                if args.get("checked_locations"):
                    locations = [location_from_code(location_id).name for location_id in
                                 args.get("checked_locations")]
                    asyncio.create_task(
                        self.cotnd_server.send_packet({"datatype": "Locations", "checked_locations": locations}))


            # Send to client when acknowledging LocationScouts packet, responding with item in location being scouted
            elif cmd == "LocationInfo":
                locs = args.get("locations")
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

                counts = {k: len(v) for k, v in self.location_hints_remaining.items()}

                asyncio.create_task(self.cotnd_server.send_packet({
                    "datatype": "LocationInfo",
                    "location_info": location_info,
                    "location_hint_amounts": counts
                }))

            # Sent to client purely to display a message to the player. We should only send data on args["data"]["type"] == "Chat" || "ServerChat"
            elif cmd == "PrintJSON":
                msg_type = args.get("type")
                if msg_type != "Chat" and msg_type != "ServerChat":
                    return

                if msg_type == "ServerChat":
                    player = "Server"
                else:
                    player = self.player_names[args.get("slot")]

                message = args.get("message")

                asyncio.create_task(self.cotnd_server.send_packet({
                    "datatype": "Chat",
                    "msg": message,
                    "player": player
                }))

        except Exception as e:
            logger.error(f"CotND on_package error: {e}")

        return super().on_package(cmd, args)

    async def manage_event(self, datatype: str, data: Dict[str, Any] = None):
        try:
            match datatype:
                case "State":
                    goal, goal_required = ("All Zones", self.slotdata.get("all_zones_goal_clear")) if self.slotdata.get(
                        "goal") == 0 else ("Zones", self.slotdata.get("zones_goal_clear"))

                    print("Sending randomizer data to CotND")

                    self.location_hints_remaining = {
                        k: {loc for loc in v}
                        for k, v in self.slotdata.get("location_hint_codes", {}).items()
                    }

                    state_packet = {
                        "datatype": "State",
                        "deathlink": bool("DeathLink" in self.tags),
                        "location_hint_amounts": {k: len(v) for k, v in self.location_hints_remaining.items()},
                        "hint_cost": self.hint_cost,
                        "missing_locations": list(
                            [location_from_code(location).name for location in self.missing_locations]),
                        "checked_locations": list(
                            [location_from_code(location).name for location in self.checked_locations]),
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
                    self.last_received_index = len(self.items_received)

                    # If the initial state, send initial state + search for shop locations
                    if data.get("init", False):
                        state_packet.update({
                            "goal": goal,
                            "goal_required": goal_required,
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

                    # Get own hints to filter out already hinted locations
                    await self.send_msgs([{
                        "cmd": "Get",
                        "keys": [f"_read_hints_{self.team}_{self.slot}"]
                    }])
                case "Death":
                    print("Sending a death!", self.tags)
                    if "DeathLink" in self.tags:
                        await self.send_death(data.get("msg"))
                case "Locations":
                    locs = data.get("sources")
                    if locs is not None:
                        resolved_ids = [location_from_name(name).code for name in locs]
                        self.locations_checked.update(resolved_ids)
                    await self.send_msgs([{"cmd": "LocationChecks", "locations": self.locations_checked}])
                case "ScoutLocation":
                    loc_id = data.get("id")
                    if loc_id and (loc_id in self.missing_locations or loc_id in self.locations_checked):
                        await self.send_msgs([{
                            "cmd": "LocationScouts",
                            "locations": [loc_id]
                        }])
                case "Hint":
                    hint_types = data.get("type")

                    # Normalize to list
                    if isinstance(hint_types, str):
                        hint_types = [hint_types]

                    # Nothing to hint if all sets are empty
                    if not any(self.location_hints_remaining.values()):
                        return

                    chosen_locations = []

                    for hint_type in hint_types:
                        chosen_type = hint_type

                        if hint_type == "Random":
                            keys_with_avail = [k for k, locs in self.location_hints_remaining.items() if locs]
                            if not keys_with_avail:
                                continue
                            chosen_type = random.choice(keys_with_avail)

                        if chosen_type in self.location_hints_remaining:
                            available = list(self.location_hints_remaining[chosen_type])
                            if available:
                                loc_id = random.choice(available)

                                # Remove immediately so we don’t repeat it before server confirms
                                self.location_hints_remaining[chosen_type].discard(loc_id)

                                chosen_locations.append(loc_id)

                    # Send one batch if we found any
                    if chosen_locations:
                        await self.send_msgs([{"cmd": "LocationScouts", "locations": chosen_locations}])
                        await self.send_msgs([{
                            "cmd": "CreateHints",
                            "locations": chosen_locations,
                            "status": HintStatus.HINT_PRIORITY
                        }])

                case "Chat":
                    await self.send_msgs([{"cmd": "Say", "text": data.get("msg")}])
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
        if self._writer.is_closing():
            return

        # 1) Serialize string in LuaJIT format (prefix .U + payload)
        serialized = _encode_prefix_uint32(len(payload) + 0x20) + payload
        # 2) Compress magicless
        # compress_magicless must produce magicless zstd frame
        compressed = self._zstd_cctx.compress(serialized)[4:]
        # 3) Prefix length (big-endian uint32)
        header = struct.pack(">I", len(compressed))

        # 4) Send to all connected clients
        self._writer.write(header + compressed)
        await self._writer.drain()

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
                    await self.send_packet(
                        {"datatype": "Handshake", "seed": self.ctx.seed_name,
                         "playerName": self.ctx.player_names[self.ctx.slot]})
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
                init = packet.init or False
                await self.ctx.manage_event(datatype, {"init": init})
            case "Victory":
                if not self.ctx.finished_game:
                    await self.ctx.manage_event(datatype)
            case "Locations":
                sources: Set[int] = set(packet.sources)
                sources.difference_update(self.ctx.checked_locations)
                if len(sources):
                    await self.ctx.manage_event(datatype, {"sources": list(sources)})
            case "Death" | "Chat":
                message = packet.msg or ""
                await self.ctx.manage_event(datatype, {"msg": message})
            case "Hint":
                hint_type = packet.type or "Random"
                await self.ctx.manage_event(datatype, {"type": hint_type})
            case "Disconnected":
                await self.ctx.manage_event(datatype)
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

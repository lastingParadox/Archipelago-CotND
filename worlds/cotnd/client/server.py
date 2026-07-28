from __future__ import annotations

import asyncio
from asyncio import AbstractServer, StreamReader, StreamWriter
import atexit
from enum import Enum
import json
import os
import platform
system = platform.system()
import struct
import time
from typing import TYPE_CHECKING
from CommonClient import logger

if TYPE_CHECKING:
    from worlds.cotnd.client.context import CotNDContext
from worlds.cotnd.Locations import location_from_code
from worlds.cotnd.Utils import MIN_MOD_VERSION, version_at_least
from worlds.cotnd.vendor_zstandard import load_vendored_zstandard

load_vendored_zstandard()

import zstandard


def _encode_prefix_uint32(n: int) -> bytes:
    if n <= 0xDF:
        return bytes([n])
    elif n <= 0x1FDF:
        first = 0xE0 | (((n - 0xE0) >> 8) & 0x1F)
        second = (n - 0xE0) & 0xFF
        return bytes([first, second])
    else:
        return bytes([0xFF]) + struct.pack("<I", n)


def _decode_luajit_string(buf: bytes) -> bytes:
    if not buf:
        raise ValueError("Empty LuaJIT string buffer")
    b0 = buf[0]
    if b0 <= 0xDF:
        return buf[1:]
    elif b0 <= 0xFF:
        return buf[2:]
    else:
        return buf[5:]


def get_data_folder_path():
    """Grabs the Archipelago data folder path for Crypt of the NecroDancer. Creates the directory if it does not exist."""
    if system == "Windows":
        data_path = os.path.expandvars("%LOCALAPPDATA%\\NecroDancer")
    elif system == "Darwin":
        data_path = os.path.expanduser("~/Library/Application Support/NecroDancer")
    elif system == "Linux":
        default_path = os.path.expanduser("~/.local/share/NecroDancer")
        flatpak_path = os.path.expanduser(
            "~/.var/app/com.valvesoftware.Steam/.local/share/NecroDancer"
        )

        if os.path.exists(flatpak_path):
            data_path = flatpak_path
        else:
            data_path = default_path
    else:
        logger.error(f"Unrecognized operating system {system}, please report.")
        raise RuntimeError(f"Unsupported operating system: {system}")

    """in.json sends data into the game. out.json gets data out from the game."""
    if not os.path.exists(data_path):
        message = (
            f"No local data found for NecroDancer at {data_path}. "
            "Please install and run Crypt of the NecroDancer before attempting to run this client."
        )
        logger.error(message)
        raise FileNotFoundError(message)

    ap_path = os.path.join(data_path, "archipelago")
    if not os.path.isdir(ap_path):
        os.mkdir(ap_path)

    return ap_path


class PacketDatatype(Enum):
    STATE = "State"
    VICTORY = "Victory"
    LOCATIONS = "Locations"
    DEATH = "Death"
    CHAT = "Chat"
    HINT = "Hint"
    HINTNPC = "HintNpc"
    DISCONNECT = "Disconnect"
    SET_DEATHLINK = "SetDeathLink"
    SET_TRAPLINK = "SetTrapLink"
    CHANGE_DIAMONDS = "ChangeDiamonds"
    CHANGE_BUFFS = "ChangeBuffs"
    CHANGE_RUN_ITEMS = "ChangeRunItems"


class CotNDPacket:
    def __init__(self, json_str: str):
        packet = json.loads(json_str)
        self.datatype = PacketDatatype(packet.get("datatype", None))
        for k, v in packet.items():
            if k != "datatype":
                setattr(self, k, v)


class CotNDServer:
    host = "127.0.0.1"
    port = 0

    def __init__(self, ctx: CotNDContext):
        self.ctx = ctx
        self._server: AbstractServer | None = None
        self._writer: StreamWriter | None = None
        self._write_lock = asyncio.Lock()
        self.data_path = get_data_folder_path()
        self.cotnd_connected = False
        self._disconnect_reason: str | None = None
        self._zstd_dctx = zstandard.ZstdDecompressor(
            format=zstandard.FORMAT_ZSTD1_MAGICLESS
        )
        self._zstd_cctx = zstandard.ZstdCompressor(level=3)

        _port_file = self.data_path + "/port.txt"
        def _clear_port_file():
            try:
                open(_port_file, "w").close()
            except Exception:
                pass
        atexit.register(_clear_port_file)

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

    def server_print(self, text: str):
        logger.debug("[CotNDServer]: " + text)

    """Sending Packets"""

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

    async def _send_json(self, obj: dict):
        payload = json.dumps(obj, separators=(",", ":")).encode("utf-8")
        self.server_print(f"Sending {obj}")
        await self._send_bytes(payload)

    async def send_packet(self, packet: dict):
        if not self.cotnd_connected or self._writer is None:
            self.server_print(f"WARNING: Not sending message as CotND isn't connected!")
            return

        packet["timestamp"] = time.time()
        await self._send_json(packet)

    """Receiving Packets"""

    async def process_input(self, packet: CotNDPacket):
        datatype = packet.datatype
        match datatype:
            case PacketDatatype.STATE:
                init = bool(getattr(packet, "init", False))
                game_index = getattr(packet, "last_ap_index", None)
                await self.ctx.manage_event(
                    datatype.value, {"init": init, "game_last_received_index": game_index}
                )
            case PacketDatatype.VICTORY:
                if not self.ctx.finished_game:
                    await self.ctx.manage_event(datatype.value)
            case PacketDatatype.LOCATIONS:
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
                    await self.ctx.manage_event(
                        datatype.value, {"sources": list(source_names)}
                    )
            case PacketDatatype.DEATH | PacketDatatype.CHAT:
                message = str(getattr(packet, "msg", "") or "")
                await self.ctx.manage_event(datatype.value, {"msg": message})
            case PacketDatatype.HINT:
                hint_type = getattr(packet, "type", "Random") or "Random"
                await self.ctx.manage_event(datatype.value, {"type": hint_type})
            case PacketDatatype.HINTNPC:
                loc_code = getattr(packet, "location_code", None)
                player_slot = getattr(packet, "player_slot", None)
                await self.ctx.manage_event(
                    datatype.value, {"location_code": loc_code, "player_slot": player_slot}
                )
            case PacketDatatype.DISCONNECT:
                reason = getattr(packet, "reason", None)
                if reason:
                    self._disconnect_reason = str(reason)
                await self.ctx.manage_event("Disconnected")
                await self._safe_close_writer()
            case PacketDatatype.SET_DEATHLINK:
                enabled = bool(getattr(packet, "deathlink", False))
                asyncio.create_task(
                    self.ctx.update_death_link(enabled), name="Update DeathLink"
                )
                asyncio.create_task(
                    self.ctx.cotnd_server.send_packet(
                        {"datatype": "SetDeathLink", "deathlink": enabled}
                    )
                )
            case PacketDatatype.SET_TRAPLINK:
                enabled = bool(getattr(packet, "traplink", False))
                asyncio.create_task(
                    self.ctx.update_trap_link(enabled), name="Update TrapLink"
                )
                asyncio.create_task(
                    self.ctx.cotnd_server.send_packet(
                        {"datatype": "SetTrapLink", "traplink": enabled}
                    )
                )
            case PacketDatatype.CHANGE_DIAMONDS:
                value = getattr(packet, "value", None)
                if isinstance(value, (int, float)):
                    await self.ctx.manage_event(datatype.value, {"value": value})
            case PacketDatatype.CHANGE_BUFFS:
                buffs = getattr(packet, "buffs", None)
                await self.ctx.manage_event(datatype.value, {"buffs": buffs})
            case PacketDatatype.CHANGE_RUN_ITEMS:
                await self.ctx.manage_event(datatype.value, {
                    "bannedItems": getattr(packet, "bannedItems", None),
                    "nextRunItems": getattr(packet, "nextRunItems", None),
                })
            case _:
                return

    """Client Handling"""

    async def _process_handshake(self, raw: bytes):
        identity = raw.decode("utf-8", errors="replace")
        self.server_print(f"Client identity: {identity}")
        self.cotnd_connected = True

        _, _, mod_version = identity.partition(":") or [0, 0, ""]
        version_text = mod_version == '' and 'pre v3.1.0' or 'v' + mod_version
        if not version_at_least(mod_version, MIN_MOD_VERSION):
            message = (
                f"Your AP Redux mod ({version_text}) is too old for this apworld "
                f"(requires v{MIN_MOD_VERSION}+). Update the mod in-game "
                f"(Mods > right-click AP Redux > manage versions) and reconnect."
            )
            self.server_print(f"Rejecting incompatible mod version: {version_text} < v{MIN_MOD_VERSION}")
            self._disconnect_reason = f"Incompatible mod version {version_text} < required v{MIN_MOD_VERSION}"
            await self.send_packet({"datatype": "Chat", "msg": message, "player": "Archipelago"})
            await self.send_packet({"datatype": "Disconnected", "reason": message})
            await self._safe_close_writer()
            self.cotnd_connected = False
            return

        # Send a new framed response
        player_name = (
            self.ctx.player_names[self.ctx.slot] if self.ctx.slot is not None else ""
        )
        await self.send_packet(
            {
                "datatype": "Handshake",
                "seed": self.ctx.seed_name,
                "playerName": player_name,
                "slot": self.ctx.slot,
            }
        )
        self.ctx.log_goal_progress()

    async def _handle_client(self, reader: StreamReader, writer: StreamWriter):
        addr = writer.get_extra_info("peername")
        self.server_print(f"Connection from {addr}")
        logger.info("Connected to Crypt of the NecroDancer")

        if self._writer is not None:
            self.server_print("Rejecting second client")
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
                    await self._process_handshake(raw)
                    handshake_done = True
                    continue

                self.server_print(f"Received Raw Message ({length} bytes): {raw}")

                with self._zstd_dctx.stream_reader(raw) as dreader:
                    decompressed = dreader.read()

                if not decompressed:
                    raise asyncio.IncompleteReadError(partial=decompressed, expected=1)

                payload = _decode_luajit_string(decompressed)
                self.server_print(f"Received Message ({length} bytes): {payload}")
                packet = CotNDPacket(payload.decode("utf-8"))
                await self.process_input(packet)
        except (
            asyncio.IncompleteReadError,
            ConnectionResetError,
            ConnectionAbortedError,
        ):
            self.server_print("Client disconnected")
        except Exception:
            self.server_print("Unexpected client error")
        finally:
            reason = self._disconnect_reason or "Mod Disconnect"
            self._disconnect_reason = None
            self.server_print(f"Disconnected {addr}")
            logger.info(f"Disconnected from Crypt of the NecroDancer (Reason: {reason})")
            self.cotnd_connected = False
            await self._safe_close_writer()

    """Server Management"""

    async def start(self):
        if self._server is not None:
            return  # Server's been started

        self.server_print("Starting server...")

        self._server = await asyncio.start_server(
            self._handle_client, host=self.host, port=self.port
        )
        sock = self._server.sockets[0]
        self.port = sock.getsockname()[1]
        self.server_print(f"Listening on {self.host}:{self.port}")

        with open(self.data_path + "/port.txt", "w") as f:
            f.write(str(self.port))

        asyncio.create_task(self._server.serve_forever(), name="CotNDServer")

    async def stop(self):
        if not self._server:
            return

        with open(self.data_path + "/port.txt", "w") as _:
            pass

        self.server_print("Shutting down")
        self._server.close()

        try:
            await self._server.wait_closed()
        except Exception as e:
            self.server_print(f"Error closing server: {e}")
        self._server = None
        self.cotnd_connected = False

    def is_running(self):
        return self._server is not None

    def get_port(self) -> int:
        return self.port

import asyncio
import json
import logging
import os
import platform
import time
import urllib.parse
from math import floor
from typing import List, Any, Set, Optional, Dict

import ModuleUpdate
from CommonClient import CommonContext, ClientCommandProcessor, get_base_parser
from NetUtils import ClientStatus
from Utils import async_start, init_logging
from worlds.cotnd.Locations import shop_location_range, from_id as location_from_id, all_locations
from worlds.cotnd.Items import from_id as item_from_id

ModuleUpdate.update()
system = platform.system()

if __name__ == '__main__':
    init_logging("CotNDClient", exception_logger="Client")


class CotNDCommandProcessor(ClientCommandProcessor):
    def _cmd_deathlink(self):
        """Toggle deathlink."""
        if isinstance(self.ctx, CotNDContext):
            self.ctx.deathlink = not self.ctx.deathlink
            asyncio.create_task(self.ctx.update_death_link(self.ctx.deathlink), name="Update Deathlink")


class CotNDContext(CommonContext):
    game = "Crypt of the NecroDancer"
    items_handling = 0b111
    want_slot_data = True
    logger = logging.getLogger("CotNDInterface")
    slotdata = dict()
    resync_items = False
    lockable_items = set()
    cotnd_handler = None
    connected_to_ap = False
    _eventqueue: List[Dict] = []

    def __init__(self, server_address, password):
        self.cotnd_handler = CotNDHandler(self)
        super().__init__(server_address, password)

    def on_deathlink(self, data: Dict[str, Any]):
        self.cotnd_handler.enqueue({
            "datatype": "Death",
            "msg": data.get("cause"),
            "timestamp": time.time(),
        })

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
        async_start(self.handle_eventqueue())

    async def server_auth(self, password_requested: bool = False):
        if password_requested and not self.password:
            await super(CotNDContext, self).server_auth(password_requested)
        await self.get_username()
        await self.send_connect()

    def on_cotnd_connect_to_ap(self):
        """When the client connects to both CotND and AP"""
        print("Sending randomizer data to CotND")
        print(self.slotdata)
        self.cotnd_handler.enqueue({
            "datatype": "State",
            "connected": True,
            "goal": self.slotdata.get("all_zones_goal_clear"),
            "deathlink": "DeathLink" in self.tags,
            "extra_modes": self.slotdata.get("included_extra_modes")
        })

        self.cotnd_handler.enqueue({
            "datatype": "Locations",
            "resync": True,
            "missing_locations": list([location_from_id(location)["name"] for location in self.missing_locations]),
            "checked_locations": list([location_from_id(location)["name"] for location in self.checked_locations])
        })

        self.resync_items = True

        # Scout shop locations
        async_start(self.send_msgs([{
            "cmd": "LocationScouts",
            "locations": [location_id for location_id in self.missing_locations if (
                    shop_location_range["start"] <= location_id <= shop_location_range["end"])]
        }]))

    def on_cotnd_reader_connected(self):
        if self.connected_to_ap:
            self.on_cotnd_connect_to_ap()
            async_start(self.send_msgs([{"cmd": "Sync"}]))
        else:
            self.logger.info("Waiting to connect to Archipelago.")

    def on_package(self, cmd: str, args: Dict):
        try:
            if cmd == "RoomInfo":
                self.seed_name = args.get("seed_name")

            elif cmd == "Connected":
                self.connected_to_ap = True
                self.slotdata = args.get("slot_data", {})
                if self.cotnd_handler.connected:
                    print("Connected to AP!")
                    self.on_cotnd_connect_to_ap()
                else:
                    async def cotnd_connect_hint():
                        await asyncio.sleep(1.0)
                        self.logger.info("Waiting for Crypt of the NecroDancer to be launched.")

                    async_start(cotnd_connect_hint())

            elif cmd == "ReceivedItems":
                items = [
                    {"item": item_from_id(netitem.item)["cotnd_id"], "location_code": str(netitem.location), "playername": self.player_names[netitem.player]} for netitem in
                    args["items"]]
                self.cotnd_handler.enqueue({
                    "datatype": "Items",
                    "items": items,
                    "resync": True if self.resync_items else None,
                })
                self.resync_items = False

            elif cmd == "RoomUpdate":
                if args.get("checked_locations"):
                    locations = [location_from_id(location_id)["name"] for location_id in args.get("checked_locations")]
                    self.cotnd_handler.enqueue({"datatype": "Locations", "checked_locations": locations})

            elif cmd == "LocationInfo":
                locs = args.get("locations")
                location_info = []
                for loc in locs:
                    location = location_from_id(loc.location)
                    try:
                        item = item_from_id(loc.item)
                    except ValueError:
                        item = {
                            "name": self.item_names.lookup_in_slot(loc.item, loc.player),
                            "classification": loc.flags,
                            "type": "APItem",
                            "cotnd_id": "APItem",
                            "dlc": "Base",
                            "isDefault": False,
                            "code": loc.item
                        }

                    location_info.append({
                        "location": location["name"],
                        "location_code": str(loc.location),
                        "item": item["cotnd_id"],
                        "playername": self.player_names[loc.player],
                        "itemname": item["name"],
                        "flags": loc.flags
                    })

                self.cotnd_handler.enqueue({
                    "datatype": "LocationInfo",
                    "location_info": location_info,
                }, False)
        except Exception as e:
            self.logger.error(f"CotND on_package error: {e}")

        return super().on_package(cmd, args)

    async def disconnect(self, allow_autoreconnect: bool = False):
        self.cotnd_handler.enqueue({
            "datatype": "Disconnected",
        })

        # Wait for CotND data to flush (with timeout to avoid hanging forever)
        start = time.time()
        while (
                self.cotnd_handler.outgoing_data_dirty
                and time.time() - start < 2  # 2 seconds max wait
        ):
            await asyncio.sleep(0.05)

        self.connected_to_ap = False
        await super().disconnect(allow_autoreconnect)

    async def queue_event(self, data):
        if self.connected_to_ap:
            # Since we're connected, manage event immediately
            await self.manage_event(data)
        else:
            # Queue for when we connect to AP again
            self._eventqueue.append(data)

    async def handle_eventqueue(self):
        while True:
            try:
                while self.connected_to_ap and len(self._eventqueue):
                    await self.manage_event(self._eventqueue.pop(0))
            except Exception as e:
                self.logger.error(f"CotND event queue error: {e}")
            await asyncio.sleep(3.0)

    async def manage_event(self, event: Dict):
        eventtype = event.get("datatype")
        try:
            if eventtype == "Death":
                if "DeathLink" in self.tags:
                    await self.send_death(event.get("msg"))
                else:
                    print("DeathLink is disabled.")

            elif eventtype == "Location":
                locs = event.get("sources")
                if locs is not None:
                    resolved_ids = [all_locations[name]["code"] for name in locs if name in all_locations]
                    self.locations_checked.update(resolved_ids)
                await self.send_msgs([{"cmd": "LocationChecks", "locations": self.locations_checked}])

            elif eventtype == "ScoutLocation":
                loc_id = event.get("id")
                if loc_id and (loc_id in self.missing_locations or loc_id in self.locations_checked):
                    await self.send_msgs([{
                        "cmd": "LocationScouts",
                        "locations": [loc_id],
                    }])
            elif eventtype == "Victory":
                await self.send_msgs([{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}])

        except Exception as e:
            self.logger.error(f"Manage event error ({eventtype}): {e}")


class CotNDHandler:
    logger = logging.getLogger("CotNDInterface")
    ctx = None
    lastping = time.time()
    _sendqueue: List[Any] = []
    _sendqueue_lowpriority: List[Any] = []
    filedata_location_scouts: Set[int] = set()
    outgoing_data_dirty = False
    waiting_for_cotnd = False
    connected_timestamp = time.time()
    session_id: Optional[int] = None  # DST's connected timestamp
    _cached_timestamps: Dict[str, Set[int]] = {
        "Death": set(),
        "Hint": set(),
    }

    def __init__(self, ctx: CotNDContext):
        self.ctx = ctx
        self._connected = False
        self.last_mod_message_time = time.time()
        self.disconnect_timeout = 10  # seconds

    @property
    def connected(self):
        return self._connected

    @connected.setter
    def connected(self, value: bool):
        if self._connected != value:
            self._connected = value
            if not value:
                self._sendqueue.clear()
                self._sendqueue_lowpriority.clear()

    def enqueue(self, data, priority=True):
        if self.connected:
            data["timestamp"] = time.time()
            (self._sendqueue if priority else self._sendqueue_lowpriority).append(data)
            self.outgoing_data_dirty = True

    async def handle_incoming_filedata(self, file_data: Dict[str, Any]):
        """Since the filedata is sent all at once and isn't cleared, verifying must be done to reduce redundant data."""
        for datatype, data in file_data.items():
            if datatype == "Victory":
                if not self.ctx.finished_game:
                    await self.handle_cotnd_filedata_entry({"datatype": datatype})
            elif datatype == "Location":
                _sources: Set[int] = set(data)
                _sources.difference_update(self.ctx.checked_locations)
                if len(_sources):
                    await self.handle_cotnd_filedata_entry({
                        "datatype": datatype,
                        "sources": list(_sources)
                    })
            elif datatype == "Death":
                for deathdata in data:
                    timestamp: Optional[int] = deathdata.get("timestamp")
                    # Verify timestamp hasn't been sent yet and is after connection time
                    if timestamp and timestamp > self.connected_timestamp and not timestamp in self._cached_timestamps[
                        datatype]:
                        self._cached_timestamps[datatype].add(timestamp)
                        await self.handle_cotnd_filedata_entry({
                            "datatype": datatype,
                            "msg": deathdata.get("msg", "")
                        })
            elif datatype == "ScoutLocation":
                _scouts: Set[int] = set(data)
                _scouts.difference_update(self.filedata_location_scouts)
                self.filedata_location_scouts.update(_scouts)
                if len(_scouts):
                    for scout_id in list(_scouts):
                        await self.handle_cotnd_filedata_entry({
                            "datatype": datatype,
                            "id": scout_id
                        })
            elif datatype == "Bounce":
                self.outgoing_data_dirty = True

    async def handle_cotnd_filedata_entry(self, data: Dict[str, Any]):
        """Sends data over to CotNDContext for event handling."""
        try:
            datatype: str = data.get("datatype")

            if datatype in {"Chat", "Join", "Leave", "Death", "Connect", "Disconnect", "DeathLink"}:
                # Instant event
                await self.ctx.manage_event(data)

            elif datatype in {"Location", "Hint", "Victory", "ScoutLocation"}:
                # Queued event
                await self.ctx.queue_event(data)

        except Exception as e:
            print(f"Handle CotND filedata entry error: {e}")

    def get_data_folder_path(self):
        """Grabs the Archipelago data folder path for Crypt of the NecroDancer. Creates the directory if it does not exist."""
        if system == 'Windows':
            data_path = os.path.expandvars('%LOCALAPPDATA%\\NecroDancer')
        elif system == 'Darwin':
            data_path = os.path.expanduser('~/Library/Application Support/NecroDancer')
        elif system == 'Linux':
            data_path = os.path.expanduser('~/.local/share/NecroDancer')
        else:
            self.logger.error(f'Unrecognized operating system {system}, please report.')
            raise RuntimeError(f'Unsupported operating system: {system}')

        """in.log sends data into the game. out.log gets data out from the game."""
        if not os.path.exists(data_path):
            message = (f'No local data found for NecroDancer at {data_path}. '
                       'Please install and run Crypt of the NecroDancer before attempting to run this client.')
            self.logger.error(message)
            raise FileNotFoundError(message)

        ap_path = os.path.join(data_path, 'archipelago')
        if not os.path.isdir(ap_path):
            os.mkdir(ap_path)

        return ap_path

    def read_incoming_data(self, base_dir: str) -> Optional[Dict]:
        """Read AP data coming from CotND."""
        out_file = base_dir + "/out.log"
        if os.path.isfile(out_file):
            with open(out_file) as f:
                raw = f.read()

            data = json.loads(raw or "{}")
            self.last_mod_message_time = time.time()

            # Check timestamp
            _timestamp: int = data.get("timestamp", floor(time.time()))
            _time_delta = floor(time.time()) - _timestamp
            if _time_delta > self.disconnect_timeout:
                print(f"Current data is too old! It's from {_time_delta} seconds ago.")
                return None
            return data
        return None

    def write_outgoing_data(self, base_dir: str, main_data: Dict[str, any] = None):
        """Send AP data to CotND."""
        in_file = base_dir + "/in.log"

        # Skip writing if data is not dirty and the in.log file already has content
        if not self.outgoing_data_dirty and os.path.exists(in_file):
            if os.path.getsize(in_file) > 0:
                return

        self.outgoing_data_dirty = False

        send_data = {
            "seed_name": self.ctx.seed_name,
            "slot": self.ctx.slot,
            "slot_name": self.ctx.player_names[self.ctx.slot],
            "connected_timestamp": floor(self.connected_timestamp),
            "timestamp": floor(time.time())
        }

        if main_data:
            send_data.update(main_data)

        if not self.waiting_for_cotnd:
            send_data["data"] = self._sendqueue
            send_data["data_lowpriority"] = self._sendqueue_lowpriority

        with open(in_file, "w") as f:
            f.write(json.dumps(send_data))

    async def run_reader(self):
        self.logger.info(f"Running Crypt of the NecroDancer Client")
        while True:
            try:
                base_dir = self.get_data_folder_path()
                if not self.connected:
                    self.connected = True
                    self.ctx.on_cotnd_reader_connected()

                    await self.handle_io(base_dir)
                    self.connected = False
                    self.logger.info(f"Disconnected from Crypt of the NecroDancer (timed out)")
                    await asyncio.sleep(3.0)
            except Exception as e:
                self.logger.error(f"CotND file reader error: {e}")
            finally:
                self.connected = False
            print("Restarting connection loop in 5 seconds.")
            await asyncio.sleep(5.0)

    async def handle_io(self, base_dir: str):
        while not self.ctx.seed_name or not self.ctx.slot or not self.ctx.connected_to_ap:
            await asyncio.sleep(0.5)

        # Start of session
        self.connected_timestamp = time.time()
        self.outgoing_data_dirty = True
        self.waiting_for_cotnd = False
        await asyncio.sleep(1.0)

        while True:
            connect_data = self.read_incoming_data(base_dir)
            # Todo: This is unstable, please fix
            if connect_data is not None and connect_data.get("ModStart") == True:
                break
            else:
                if not self.waiting_for_cotnd:
                    self.waiting_for_cotnd = True
                    self.logger.info(
                        "Waiting to connect to Crypt of the NecroDancer. Please head to the Archipelago trap and select \"Connect\".")
                await asyncio.sleep(2.0)

        self.waiting_for_cotnd = False
        self.logger.info(f"Detected Crypt of the NecroDancer AP Mod.")

        while self.ctx.connected_to_ap:
            try:
                self.write_outgoing_data(base_dir)
                await asyncio.sleep(1.0)
                incoming_data = self.read_incoming_data(base_dir)
                if incoming_data:
                    # Todo: Seems a bit simplistic, check in future
                    await self.handle_incoming_filedata(incoming_data)
                else:
                    break

                if time.time() - self.last_mod_message_time > self.disconnect_timeout:
                    self.logger.warning(
                        f"No response from Crypt of the NecroDancer for over {self.disconnect_timeout} seconds. Disconnecting.")
                    break  # This will exit handle_io and trigger reconnection
            except Exception as e:
                self.logger.error(f"CotND Handle IO Error: {e}")
                raise


async def main(args):
    ctx = CotNDContext(args.connect, args.password)
    ctx.auth = args.name
    ctx.run_gui()

    dst_handler_task = asyncio.create_task(ctx.cotnd_handler.run_reader(), name="CotND Handler")

    await ctx.exit_event.wait()
    dst_handler_task.cancel()
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

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from BaseClasses import Region
from worlds.cotnd.Utils import max_zone, owned_dlc

if TYPE_CHECKING:
    from . import CotNDWorld

# The lobby is everything reachable without starting a run: the AP shop and the Codex.
# The Crypt covers a run's zone-agnostic checks, and each zone is its own region
LOBBY_REGION: Final = "AP Lobby"
CRYPT_REGION: Final = "Crypt"

# Aria descends the crypt instead of climbing it, so her zone gating is the mirror of everyone else's
ARIA: Final = "Aria"

def zone_region(zone: int, character: str | None = None) -> str:
    if character == ARIA:
        return f"Zone {zone} ({ARIA})"

    return f"Zone {zone}"

def zone_entrance(zone: int, character: str | None = None) -> str:
    return f"{CRYPT_REGION} to {zone_region(zone, character)}"

def create_and_connect_regions(world: CotNDWorld) -> None:
    create_all_regions(world)
    connect_regions(world)

def create_all_regions(world: CotNDWorld) -> None:
    names = [LOBBY_REGION, CRYPT_REGION]
    for zone in range(1, max_zone(owned_dlc(world)) + 1):
        names += [zone_region(zone), zone_region(zone, ARIA)]

    world.multiworld.regions += [Region(name, world.player, world.multiworld) for name in names]

def connect_regions(world: CotNDWorld) -> None:
    lobby = world.get_region(LOBBY_REGION)
    crypt = world.get_region(CRYPT_REGION)

    lobby.connect(crypt, f"{LOBBY_REGION} to {CRYPT_REGION}")

    for zone in range(1, max_zone(owned_dlc(world)) + 1):
        for character in (None, ARIA):
            crypt.connect(world.get_region(zone_region(zone, character)),
                          zone_entrance(zone, character))

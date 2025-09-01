from .Characters import get_all_characters
from .Items import get_default_items, get_all_npc_items


def ensure_min_max(options, min_name: str, max_name: str) -> None:
    min_val = getattr(options, min_name).value
    max_val = getattr(options, max_name).value

    if max_val < min_val:
        print(f"[WARNING] Swapping {min_name} ({min_val}) and {max_name} ({max_val}) to maintain proper bounds.")
        setattr(options, min_name, type(getattr(options, min_name))(max_val))
        setattr(options, max_name, type(getattr(options, max_name))(min_val))

def validate_blacklist(options, dlcs):
    all_chars = get_all_characters(dlcs)
    blacklist = set(options.character_blacklist.value)
    if set(all_chars).issubset(blacklist):
        print("[WARNING] Removing Cadence from the blacklist to maintain progression.")
        blacklist = [c for c in blacklist if c != "Cadence"]
        options.character_blacklist.value = blacklist
    return blacklist


def validate_modes(options, dlcs):
    included_modes = list(options.included_extra_modes.value)

    if "Amplified" not in dlcs:
        amplified_modes = {"No Return", "Hard", "Phasing", "Randomizer", "Mystery"}
        before = set(included_modes)
        included_modes = [mode for mode in included_modes if mode not in amplified_modes]
        removed = before - set(included_modes)
        if removed:
            print(f"[WARNING] Removed Amplified-only modes (no Amplified DLC enabled): {', '.join(removed)}")
        options.included_extra_modes.value = included_modes

    return included_modes


def validate_lobby_npcs(options):
    if options.lobby_npc_items and not options.locked_lobby_npcs:
        print("[WARNING] Disabling Lobby NPC items as Locked Lobby NPCs is disabled.")
        options.lobby_npc_items.value = False


def cap_option(options, option_name: str, cap: int):
    option = getattr(options, option_name)
    if option.value > cap:
        print(f"[WARNING] Setting {option_name.replace('_', ' ')} to {cap} to maintain progression.")
        option.value = cap


def validate_price_ranges(options):
    for prefix in ("randomized", "filler", "useful", "progression"):
        ensure_min_max(options, f"{prefix}_price_min", f"{prefix}_price_max")


def precollect_defaults(world, options):
    for item in get_default_items(options.dlc):
        world.multiworld.push_precollected(world.create_item(item['name']))

def precollect_lobby_npcs(world):
    for item in get_all_npc_items():
        world.multiworld.push_precollected(world.create_item(item['name']))
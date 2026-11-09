from __future__ import annotations

import argparse
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional

import vdf
from rich.console import Console
from rich.table import Table

logger = logging.getLogger(__name__)

STEAM_GAME_PAGE = "https://store.steampowered.com/app"

# Valve compatibility tools / runtimes are installed as regular apps but are
# not games, so they are hidden from the games table.
TOOL_NAME_PREFIXES = (
    "proton",
    "steam linux runtime",
    "steamworks common redistributables",
)


def candidate_steam_dirs(
    home: Path, env: Mapping[str, str], explicit: Optional[str] = None
) -> list[Path]:
    """Every place Steam may live, most specific first.

    Covers the native install on any distro (Debian/Ubuntu symlinks under
    ``~/.steam``), Flatpak, Snap and a custom ``STEAM_DIR``.
    """
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    if env.get("STEAM_DIR"):
        candidates.append(Path(env["STEAM_DIR"]).expanduser())
    if env.get("XDG_DATA_HOME"):
        candidates.append(Path(env["XDG_DATA_HOME"]) / "Steam")
    flatpak = home / ".var" / "app" / "com.valvesoftware.Steam"
    candidates += [
        home / ".local" / "share" / "Steam",
        home / ".steam" / "steam",
        home / ".steam" / "root",
        home / ".steam" / "debian-installation",
        flatpak / ".local" / "share" / "Steam",
        flatpak / "data" / "Steam",
        home / "snap" / "steam" / "common" / ".local" / "share" / "Steam",
    ]
    return candidates


def find_steam_dir(
    home: Optional[Path] = None,
    env: Optional[Mapping[str, str]] = None,
    explicit: Optional[str] = None,
) -> Optional[Path]:
    """Return the first candidate that actually looks like a Steam install."""
    home = Path.home() if home is None else home
    env = os.environ if env is None else env
    for path in candidate_steam_dirs(home, env, explicit):
        if (path / "steamapps").is_dir() or (path / "userdata").is_dir():
            return path
    return None


def not_found_message(
    home: Optional[Path] = None, env: Optional[Mapping[str, str]] = None
) -> str:
    home = Path.home() if home is None else home
    env = os.environ if env is None else env
    searched = "\n".join(f"  {p}" for p in candidate_steam_dirs(home, env))
    return (
        "Could not find a Steam installation. Looked in:\n"
        f"{searched}\n\n"
        "Start Steam once so it creates its folders, or point this tool at "
        "your install:\n"
        "  STEAM_DIR=/path/to/Steam <command>   (or use --steam-dir PATH)"
    )


@dataclass
class SteamGame:
    name: str
    appid: int
    steamapps: Path
    compatdata: Path | None
    compat_tool: str | None


@dataclass
class Shortcut:
    name: str
    appid: int | None
    compatdata: Path | None
    compat_tool: str | None


@dataclass
class UserShortcuts:
    user_id: str
    shortcuts: list[Shortcut]


def normalize_appid(appid: int | None) -> int | None:
    """Convert a signed 32-bit appid to its unsigned representation."""
    if appid is not None and appid < 0:
        appid += 2**32
    return appid


def is_tool(name: str) -> bool:
    """Return True for Valve runtimes/compat tools, which are not games."""
    return name.lower().startswith(TOOL_NAME_PREFIXES)


def load_compat_tools(config: Path) -> dict[int, str]:
    """Map appid -> the Proton/compat tool Steam is configured to use.

    An app with no entry either runs natively or falls back to Steam's default
    compat tool, so an empty prefix for one of these is expected, not broken.
    """
    if not config.is_file():
        return {}

    try:
        with open(config, "r") as f:
            data = vdf.load(f)
    except (SyntaxError, OSError) as exc:
        logger.warning("Failed to parse %s: %s, skipping", config, exc)
        return {}

    mapping: dict[int, str] = {}

    def walk(node: object) -> None:
        if not isinstance(node, dict):
            return
        for key, value in node.items():
            if key == "CompatToolMapping" and isinstance(value, dict):
                for appid, cfg in value.items():
                    if not isinstance(cfg, dict):
                        continue
                    name = cfg.get("name")
                    try:
                        if name:
                            mapping[int(appid)] = name
                    except ValueError:
                        continue
            else:
                walk(value)

    walk(data)

    return mapping


def find_compatdata(steamapps: Path, appid: int | None) -> Path | None:
    """Return the Proton prefix directory for an app, if one exists.

    Steam leaves behind empty compatdata directories (a game installed but
    never launched, or a prefix that was wiped), so the directory existing is
    not enough. A real prefix always contains ``pfx/``.
    """
    if appid is None:
        return None
    path = steamapps / "compatdata" / str(appid)
    return path if (path / "pfx").is_dir() else None


def load_libraries(steamapps: Path) -> list[Path]:
    """Return every existing steamapps directory listed in libraryfolders.vdf.

    Steam stores games across multiple library folders (extra drives, external
    disks). Only scanning the default one hides most of the library.
    """
    libraries: list[Path] = []
    seen: set[Path] = set()

    def add(candidate: Path) -> None:
        if not candidate.is_dir():
            return
        resolved = candidate.resolve()
        if resolved in seen:
            return
        seen.add(resolved)
        libraries.append(resolved)

    add(steamapps)

    index = steamapps / "libraryfolders.vdf"
    if index.is_file():
        try:
            with open(index, "r") as f:
                data = vdf.load(f)
        except (SyntaxError, OSError) as exc:
            logger.warning("Failed to parse %s: %s, skipping", index, exc)
            return libraries

        for entry in data.get("libraryfolders", {}).values():
            if not isinstance(entry, dict):
                continue
            path = entry.get("path")
            if path:
                add(Path(path) / "steamapps")

    return libraries


def load_user_shortcuts(
    steam_userdata: Path, steamapps: Path, compat_tools: dict[int, str]
) -> list[UserShortcuts]:
    """Read all shortcuts.vdf files and return structured data."""
    results: list[UserShortcuts] = []

    for path in sorted(steam_userdata.glob("*/config/shortcuts.vdf")):
        user_id = path.parent.parent.name

        try:
            with open(path, "rb") as f:
                data = vdf.binary_load(f)
        except (SyntaxError, OSError) as exc:
            logger.warning("Failed to parse %s: %s, skipping", path, exc)
            continue

        shortcuts: list[Shortcut] = []
        for _key, entry in data.get("shortcuts", {}).items():
            name = entry.get("AppName") or entry.get("appname", "Unknown")
            appid = normalize_appid(entry.get("appid"))
            shortcuts.append(Shortcut(
                name=name,
                appid=appid,
                compatdata=find_compatdata(steamapps, appid),
                compat_tool=compat_tools.get(appid) if appid else None,
            ))

        shortcuts.sort(key=lambda s: s.name.lower())

        results.append(UserShortcuts(
            user_id=user_id,
            shortcuts=shortcuts,
        ))

    return results


def load_steam_games(
    libraries: list[Path],
    shortcut_appids: set[int],
    compat_tools: dict[int, str],
) -> list[SteamGame]:
    """Read app manifests from every library and return structured data."""
    games: list[SteamGame] = []
    seen: set[int] = set()

    for steamapps in libraries:
        for manifest in sorted(steamapps.glob("appmanifest_*.acf")):
            try:
                appid = int(manifest.stem.removeprefix("appmanifest_"))
            except ValueError:
                continue

            if appid in shortcut_appids or appid in seen:
                continue

            try:
                with open(manifest, "r") as f:
                    data = vdf.load(f)
            except (SyntaxError, OSError) as exc:
                logger.warning(
                    "Failed to parse %s: %s, skipping", manifest, exc
                )
                continue

            name = data.get("AppState", {}).get("name", "Unknown")
            if is_tool(name):
                continue

            seen.add(appid)
            games.append(SteamGame(
                name=name,
                appid=appid,
                steamapps=steamapps,
                compatdata=find_compatdata(steamapps, appid),
                compat_tool=compat_tools.get(appid),
            ))

    games.sort(key=lambda g: g.name.lower())

    return games


def display_path(path: Path | None) -> str:
    """Render a path with the home directory collapsed to ``~``."""
    if path is None:
        return "N/A"

    home = Path.home()
    for base in (home, home.resolve()):
        try:
            return f"~/{path.relative_to(base)}/"
        except ValueError:
            continue
    return f"{path}/"


def display_runtime(compat_tool: str | None, compatdata: Path | None) -> str:
    """Describe how an app runs, so a missing prefix is not just ``N/A``."""
    if compat_tool:
        return compat_tool if compatdata else f"{compat_tool} (no prefix yet)"
    return "Steam default" if compatdata else "Native"


def display_steam_games(games: list[SteamGame]) -> None:
    console = Console()
    table = Table(
        title="Steam Games",
        caption=f"{len(games)} games found",
    )
    table.add_column("App ID", style="green", justify="right")
    table.add_column("Name", style="bold cyan")
    table.add_column("Install Path", style="dim")
    table.add_column("Runtime", style="magenta")
    table.add_column("Prefix", style="dim")

    for game in games:
        table.add_row(
            str(game.appid),
            f"{game.name}\n[dim blue]{STEAM_GAME_PAGE}/{game.appid}[/dim blue]",
            display_path(game.steamapps),
            display_runtime(game.compat_tool, game.compatdata),
            display_path(game.compatdata),
        )

    console.print(table)


def display_shortcuts(user_shortcuts_list: list[UserShortcuts]) -> None:
    console = Console()

    for user in user_shortcuts_list:
        table = Table(
            title="Non-Steam Shortcuts",
            caption=f"User: {user.user_id}",
        )
        table.add_column("App ID", style="green", justify="right")
        table.add_column("Name", style="bold cyan")
        table.add_column("Runtime", style="magenta")
        table.add_column("Prefix", style="dim")

        for shortcut in user.shortcuts:
            table.add_row(
                str(shortcut.appid) if shortcut.appid is not None else "N/A",
                shortcut.name,
                display_runtime(shortcut.compat_tool, shortcut.compatdata),
                display_path(shortcut.compatdata),
            )

        console.print(table)


def main(argv: Optional[list[str]] = None) -> None:
    logging.basicConfig(level=logging.WARNING)

    parser = argparse.ArgumentParser(
        description="List your Steam games and non-Steam shortcuts."
    )
    parser.add_argument(
        "--steam-dir",
        help="Steam install folder (default: auto-detect, or $STEAM_DIR)",
    )
    args = parser.parse_args(argv)

    steam_dir = find_steam_dir(explicit=args.steam_dir)
    if steam_dir is None:
        print(not_found_message(), file=sys.stderr)
        sys.exit(1)

    steamapps = steam_dir / "steamapps"
    compat_tools = load_compat_tools(steam_dir / "config" / "config.vdf")

    user_shortcuts_list = load_user_shortcuts(
        steam_dir / "userdata", steamapps, compat_tools
    )

    shortcut_appids: set[int] = set()
    for user in user_shortcuts_list:
        for shortcut in user.shortcuts:
            if shortcut.appid is not None:
                shortcut_appids.add(shortcut.appid)

    libraries = load_libraries(steamapps)
    games = load_steam_games(libraries, shortcut_appids, compat_tools)
    display_steam_games(games)
    display_shortcuts(user_shortcuts_list)


if __name__ == "__main__":
    main()

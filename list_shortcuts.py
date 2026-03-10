import logging
from dataclasses import dataclass
from pathlib import Path

import vdf
from rich.console import Console
from rich.table import Table

logger = logging.getLogger(__name__)

STEAM_DIR = Path.home() / ".local" / "share" / "Steam"
STEAM_USERDATA = STEAM_DIR / "userdata"
STEAM_APPS = STEAM_DIR / "steamapps"
STEAM_GAME_PAGE = "https://store.steampowered.com/app"


@dataclass
class SteamGame:
    name: str
    appid: int


@dataclass
class Shortcut:
    name: str
    appid: int | None


@dataclass
class UserShortcuts:
    user_id: str
    shortcuts: list[Shortcut]


def normalize_appid(appid: int | None) -> int | None:
    """Convert a signed 32-bit appid to its unsigned representation."""
    if appid is not None and appid < 0:
        appid += 2**32
    return appid


def load_user_shortcuts(steam_userdata: Path) -> list[UserShortcuts]:
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
            shortcuts.append(Shortcut(name=name, appid=appid))

        shortcuts.sort(key=lambda s: s.name.lower())

        results.append(UserShortcuts(
            user_id=user_id,
            shortcuts=shortcuts,
        ))

    return results


def load_steam_games(
    steam_apps: Path, shortcut_appids: set[int]
) -> list[SteamGame]:
    """Read compatdata directories and manifests, return structured data."""
    games: list[SteamGame] = []
    compatdata_dir = steam_apps / "compatdata"

    if not compatdata_dir.is_dir():
        return games

    for d in sorted(compatdata_dir.iterdir()):
        try:
            appid = int(d.name)
        except ValueError:
            continue

        if appid in shortcut_appids:
            continue

        manifest = steam_apps / f"appmanifest_{appid}.acf"
        if not manifest.is_file():
            continue

        try:
            with open(manifest, "r") as f:
                data = vdf.load(f)
        except (SyntaxError, OSError) as exc:
            logger.warning("Failed to parse %s: %s, skipping", manifest, exc)
            continue

        name = data.get("AppState", {}).get("name", "Unknown")
        games.append(SteamGame(name=name, appid=appid))

    games.sort(key=lambda g: g.name.lower())

    return games


def compatdata_path(appid: int | None) -> str:
    if appid is None:
        return "N/A"
    return f"~/.local/share/Steam/steamapps/compatdata/{appid}/"


def display_steam_games(games: list[SteamGame]) -> None:
    console = Console()
    table = Table(
        title="Steam Games (Proton/Compatdata)",
        caption=f"{len(games)} games found",
    )
    table.add_column("App ID", style="green", justify="right")
    table.add_column("Name", style="bold cyan")
    table.add_column("Path", style="dim")

    for game in games:
        table.add_row(
            str(game.appid),
            f"{game.name}\n[dim blue]{STEAM_GAME_PAGE}/{game.appid}[/dim blue]",
            compatdata_path(game.appid),
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
        table.add_column("Path", style="dim")

        for shortcut in user.shortcuts:
            table.add_row(
                str(shortcut.appid) if shortcut.appid is not None else "N/A",
                shortcut.name,
                compatdata_path(shortcut.appid),
            )

        console.print(table)


def main() -> None:
    logging.basicConfig(level=logging.WARNING)

    user_shortcuts_list = load_user_shortcuts(STEAM_USERDATA)

    shortcut_appids: set[int] = set()
    for user in user_shortcuts_list:
        for shortcut in user.shortcuts:
            if shortcut.appid is not None:
                shortcut_appids.add(shortcut.appid)

    games = load_steam_games(STEAM_APPS, shortcut_appids)
    display_steam_games(games)
    display_shortcuts(user_shortcuts_list)


if __name__ == "__main__":
    main()

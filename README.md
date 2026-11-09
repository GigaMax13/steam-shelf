# steam-shelf

Quickly see all your Steam games and non-Steam shortcuts from the terminal.

## Sample Output

```
$ ./run.sh

                                  Steam Games
┏━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃   App ID ┃ Name                                       ┃ Install Path               ┃ Prefix                        ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│   292030 │ The Witcher 3: Wild Hunt                   │ ~/.local/share/Steam/stea… │ ~/.local/share/Steam/steama…  │
│          │ https://store.steampowered.com/app/292030  │                            │                               │
│  1091500 │ Cyberpunk 2077                             │ /mnt/games/SteamLibrary/s… │ /mnt/games/SteamLibrary/ste…  │
│          │ https://store.steampowered.com/app/1091500 │                            │                               │
│  1245620 │ Elden Ring                                 │ /mnt/games/SteamLibrary/s… │ N/A                           │
│          │ https://store.steampowered.com/app/1245620 │                            │                               │
└──────────┴────────────────────────────────────────────┴────────────────────────────┴───────────────────────────────┘
                                 3 games found

                              Non-Steam Shortcuts
┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃     App ID ┃ Name                  ┃ Prefix                       ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 2837212789 │ Heroic Games Launcher │ ~/.../compatdata/2837212789/ │
│ 3914207643 │ Lutris                │ ~/.../compatdata/3914207643/ │
└────────────┴───────────────────────┴──────────────────────────────┘
                        User: 12345678
```

## Features

- Lists every installed Steam game across **all** library folders (extra drives
  and external disks listed in `libraryfolders.vdf`), not just the default one
- Lists non-Steam shortcuts per user profile
- Shows app IDs, install paths, Steam store page links, and how each app runs
  (`Runtime`: the configured Proton/compat tool, `Steam default`, or `Native`)
- Reports a Proton prefix only when it is real — Steam leaves behind empty
  `compatdata/<appid>/` stubs that contain no `pfx/`
- Hides Valve runtimes and compatibility tools (Proton, Steam Linux Runtime,
  Steamworks Common Redistributables)
- Formatted terminal tables via [Rich](https://github.com/Textualize/rich)
- Multi-user support (iterates all profiles under `userdata/`)
- Graceful handling of malformed VDF files and missing library folders

## Quick start (no GitHub knowledge needed)

Works on any common Linux distro: Ubuntu, Debian, Fedora, Arch, openSUSE,
Linux Mint, Pop!_OS, Bazzite, SteamOS, and more. Steam can be the normal
install, Flatpak, or Snap.

1. Open **[steam-shelf.sh](https://raw.githubusercontent.com/gigamax13/steam-shelf/main/steam-shelf.sh)**
   in your browser.
2. Select everything (`Ctrl+A`) and copy it (`Ctrl+C`).
3. Open a terminal, paste (`Ctrl+Shift+V`), and press `Enter`.

That's it. The first run installs two small helper libraries (a few
seconds, needs internet); after that it starts instantly. Nothing is installed
system-wide and no `sudo` is needed: everything lives in `~/.cache/steam-shelf`.

If you are comfortable with a terminal, the same thing as one line:

```sh
curl -fsSL https://raw.githubusercontent.com/gigamax13/steam-shelf/main/steam-shelf.sh | sh
```

If you see "Python 3 is not installed", the message tells you the exact
command for your distro (for example `sudo apt install python3 python3-venv python3-pip`).
Python 3.9 or newer is needed.

### Options

Steam is found automatically. If yours is somewhere unusual, pass it:

```sh
curl -fsSL https://raw.githubusercontent.com/gigamax13/steam-shelf/main/steam-shelf.sh | sh -s -- --steam-dir /path/to/Steam
```

(or set `STEAM_DIR=/path/to/Steam`). Searched automatically:
`~/.local/share/Steam`, `~/.steam/steam`, `~/.steam/root`,
`~/.steam/debian-installation`, Flatpak, Snap, and `$XDG_DATA_HOME/Steam`.

## Developer setup

```sh
git clone https://github.com/gigamax13/steam-shelf.git
cd steam-shelf
./setup.sh      # venv + dependencies
./run.sh        # run from source
```

`steam-shelf.sh` is generated: it embeds `list_shortcuts.py` inside
`installer.sh.in`. After changing either, run `python3 build.py`.

Tests:

```sh
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```

The installer tests need internet (they do a real dependency install) and
fail if `steam-shelf.sh` is out of date.

## Output

Two tables:

1. **Steam Games** -- every installed game with an `appmanifest_*.acf`. Columns: app ID, name (with store link), install path, runtime, prefix.
2. **Non-Steam Shortcuts** -- entries from each user's `shortcuts.vdf`, per user profile. Columns: app ID, name, runtime, prefix.

Games that also appear as non-Steam shortcuts are deduplicated and shown only in the shortcuts table.

## How It Works

- Parses `shortcuts.vdf` (binary VDF) for non-Steam shortcuts
- Reads `appmanifest_*.acf` files and `compatdata/` directories for Proton games
- Deduplicates entries that appear in both sources
- Renders tables with Rich

## Project Structure

```
steam-shelf/
├── steam-shelf.sh      # Single-file script for end users (generated)
├── list_shortcuts.py   # Main program: discovery, parsing, display
├── installer.sh.in     # Template for steam-shelf.sh
├── build.py            # Generates steam-shelf.sh
├── tests/              # pytest suite
├── requirements.txt    # Python dependencies (rich, vdf)
├── setup.sh / run.sh   # Developer venv helpers
```

## License

[MIT](LICENSE)

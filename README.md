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

## Requirements

- Python 3.12+
- Linux with a standard Steam installation (`~/.local/share/Steam`)

## Setup

```sh
git clone https://github.com/gigamax13/steam-shelf.git
cd steam-shelf
./setup.sh
```

`setup.sh` creates a virtual environment in `.venv/` and installs dependencies from `requirements.txt`.

## Usage

```sh
./run.sh
```

This displays two tables:

1. **Steam Games (Proton/Compatdata)** -- all installed games that have a compatdata directory and a matching `appmanifest_*.acf` file. Columns: name, app ID, compatdata path, and Steam store page link.
2. **Non-Steam Shortcuts** -- entries from each user's `shortcuts.vdf`, shown per user profile. Columns: name, app ID, and compatdata path.

Games that also appear as non-Steam shortcuts are deduplicated and shown only in the shortcuts table.

## How It Works

- Parses `shortcuts.vdf` (binary VDF) for non-Steam shortcuts
- Reads `appmanifest_*.acf` files and `compatdata/` directories for Proton games
- Deduplicates entries that appear in both sources
- Renders tables with Rich

## Project Structure

```
steam-shelf/
├── list_shortcuts.py   # Main script: data loading, parsing, and display
├── requirements.txt    # Python dependencies (rich, vdf)
├── setup.sh            # Creates venv and installs dependencies
└── run.sh              # Runs the script inside the venv
```

## License

[MIT](LICENSE)

# steam-shelf

Quickly see all your Steam games and non-Steam shortcuts from the terminal.

## Sample Output

```
$ ./run.sh

                              Steam Games (Proton/Compatdata)
┏━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃   App ID ┃ Name                                        ┃ Path                     ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│   292030 │ The Witcher 3: Wild Hunt                    │ ~/.../compatdata/292030/  │
│          │ https://store.steampowered.com/app/292030   │                          │
│  1091500 │ Cyberpunk 2077                              │ ~/.../compatdata/1091500/ │
│          │ https://store.steampowered.com/app/1091500  │                          │
│  1245620 │ Elden Ring                                  │ ~/.../compatdata/1245620/ │
│          │ https://store.steampowered.com/app/1245620  │                          │
└──────────┴─────────────────────────────────────────────┴──────────────────────────┘
                               3 games found

                              Non-Steam Shortcuts
┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃     App ID ┃ Name                  ┃ Path                        ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 2837212789 │ Heroic Games Launcher │ ~/.../compatdata/2837212789/ │
│ 3914207643 │ Lutris                │ ~/.../compatdata/3914207643/ │
└────────────┴───────────────────────┴─────────────────────────────┘
                        User: 12345678
```

## Features

- Lists installed Steam games running under Proton (with compatdata)
- Lists non-Steam shortcuts per user profile
- Shows app IDs, compatdata paths, and Steam store page links
- Formatted terminal tables via [Rich](https://github.com/Textualize/rich)
- Multi-user support (iterates all profiles under `userdata/`)
- Graceful handling of malformed VDF files

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

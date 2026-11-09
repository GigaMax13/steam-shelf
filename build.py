"""Generate steam-shelf.sh: list_shortcuts.py embedded in installer.sh.in.

Usage: python3 build.py          write steam-shelf.sh
       python3 build.py --check  exit 1 if steam-shelf.sh is out of date
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HEREDOC_TAG = "STEAM_SHELF_PY_EOF"
OUTPUT = ROOT / "steam-shelf.sh"


def render() -> str:
    template = (ROOT / "installer.sh.in").read_text()
    source = (ROOT / "list_shortcuts.py").read_text().rstrip("\n")
    if HEREDOC_TAG in source:
        raise ValueError("python source contains the heredoc terminator")
    return template.replace("@@HEREDOC_TAG@@", HEREDOC_TAG).replace(
        "@@PYTHON@@", source
    )


def main(argv: list[str]) -> int:
    rendered = render()
    if "--check" in argv:
        current = OUTPUT.read_text() if OUTPUT.exists() else ""
        return 0 if current == rendered else 1
    OUTPUT.write_text(rendered)
    OUTPUT.chmod(0o755)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

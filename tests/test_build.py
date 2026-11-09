import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import build  # noqa: E402


def test_render_embeds_python_source():
    out = build.render()
    assert (ROOT / "list_shortcuts.py").read_text() in out
    assert out.startswith("#!/bin/sh\n")


def test_python_source_cannot_terminate_heredoc():
    src = (ROOT / "list_shortcuts.py").read_text()
    assert build.HEREDOC_TAG not in src

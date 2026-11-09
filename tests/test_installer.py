"""Black-box tests for the single-file installer, steam-shelf.sh."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "steam-shelf.sh"
REAL_PY = shutil.which("python3") or sys.executable

BASE_TOOLS = [
    "sh", "mkdir", "cat", "rm", "chmod", "uname", "grep", "sed", "dirname",
    "env", "tr", "head", "mktemp", "mv", "ls", "cp",
]


def make_env(tmp_path: Path, path: str | None = None, **extra) -> dict:
    home = tmp_path / "home"
    steam = home / ".steam" / "steam" / "steamapps"
    steam.mkdir(parents=True, exist_ok=True)
    (steam / "appmanifest_10.acf").write_text(
        '"AppState"\n{\n\t"name"\t\t"Test Game"\n}\n'
    )
    env = {
        "HOME": str(home),
        "PATH": path or os.environ["PATH"],
        "XDG_CACHE_HOME": str(tmp_path / "cache"),
        "TERM": "dumb",
    }
    env.update(extra)
    return env


def run(args, env, stdin=None, timeout=240):
    return subprocess.run(
        args, env=env, input=stdin, capture_output=True, text=True,
        timeout=timeout,
    )


def tool_dir(tmp_path: Path, python: str | None = "real") -> Path:
    """A PATH containing only basic tools plus an optional python3 stand-in."""
    d = tmp_path / "bin"
    d.mkdir()
    for tool in BASE_TOOLS:
        found = shutil.which(tool)
        if found:
            (d / tool).symlink_to(found)
    if python == "real":
        (d / "python3").symlink_to(REAL_PY)
    elif python:
        (d / "python3").write_text(python)
        (d / "python3").chmod(0o755)
    return d


def wrapper(body: str) -> str:
    return f'#!/bin/sh\n{body}\nexec "{REAL_PY}" "$@"\n'


# --- static properties -----------------------------------------------------

def test_script_exists_and_is_syntactically_valid():
    assert SCRIPT.is_file()
    assert run(["sh", "-n", str(SCRIPT)], os.environ).returncode == 0


def test_script_is_paste_safe():
    """Pasted into a live terminal, a bare `exit` or `set -e` would kill it."""
    for line in SCRIPT.read_text().splitlines():
        assert not line.startswith(("exit", "set -e", "set -u")), line


def test_script_is_in_sync_with_source():
    sys.path.insert(0, str(ROOT))
    import build

    assert SCRIPT.read_text() == build.render()


# --- happy path ------------------------------------------------------------

@pytest.fixture(scope="module")
def warm(tmp_path_factory):
    """One real install, reused: later runs must not need the network."""
    tmp = tmp_path_factory.mktemp("warm")
    env = make_env(tmp)
    first = run(["sh", str(SCRIPT)], env)
    return tmp, env, first


def test_first_run_installs_and_lists_games(warm):
    _, _, first = warm
    assert first.returncode == 0, first.stderr
    assert "Test Game" in first.stdout


def test_second_run_skips_install(warm):
    _, env, _ = warm
    second = run(["sh", str(SCRIPT)], env, timeout=30)
    assert second.returncode == 0, second.stderr
    assert "Test Game" in second.stdout
    assert "nstalling" not in second.stdout + second.stderr


def test_works_when_piped_to_sh_like_curl(warm):
    _, env, _ = warm
    out = run(["sh", "-s", "--"], env, stdin=SCRIPT.read_text(), timeout=30)
    assert out.returncode == 0, out.stderr
    assert "Test Game" in out.stdout


def test_works_under_bash_when_pasted(warm):
    _, env, _ = warm
    out = run(["bash", "-c", SCRIPT.read_text()], env, timeout=30)
    assert out.returncode == 0, out.stderr
    assert "Test Game" in out.stdout


def test_arguments_are_passed_through(warm):
    tmp, env, _ = warm
    other = tmp / "other"
    (other / "steamapps").mkdir(parents=True)
    (other / "steamapps" / "appmanifest_7.acf").write_text(
        '"AppState"\n{\n\t"name"\t\t"Elsewhere Game"\n}\n'
    )
    out = run(["sh", str(SCRIPT), "--steam-dir", str(other)], env, timeout=30)
    assert "Elsewhere Game" in out.stdout


def test_missing_steam_gives_friendly_error(warm):
    tmp, env, _ = warm
    empty = tmp / "emptyhome"
    empty.mkdir()
    env = dict(env, HOME=str(empty))
    out = run(["sh", str(SCRIPT)], env, timeout=30)
    assert out.returncode == 1
    assert "Could not find a Steam installation" in out.stderr
    assert "Traceback" not in out.stderr


# --- failure / fallback paths ---------------------------------------------

def test_no_python_gives_install_hint(tmp_path):
    env = make_env(tmp_path, path=str(tool_dir(tmp_path, python=None)))
    out = run(["sh", str(SCRIPT)], env, timeout=30)
    assert out.returncode != 0
    assert "Python 3" in out.stderr


def test_too_old_python_is_rejected(tmp_path):
    fake = "#!/bin/sh\nexit 1\n"  # version check fails
    env = make_env(tmp_path, path=str(tool_dir(tmp_path, python=fake)))
    out = run(["sh", str(SCRIPT)], env, timeout=30)
    assert out.returncode != 0
    assert "3.9" in out.stderr


def test_falls_back_to_pip_target_when_venv_missing(tmp_path):
    py = wrapper('case "$*" in *"-m venv"*) echo "no ensurepip" >&2; exit 1;; esac')
    env = make_env(tmp_path, path=str(tool_dir(tmp_path, python=py)))
    out = run(["sh", str(SCRIPT)], env)
    assert out.returncode == 0, out.stderr
    assert "Test Game" in out.stdout


@pytest.mark.parametrize(
    "os_release, expected",
    [
        ("ID=ubuntu\nID_LIKE=debian\n", "apt install"),
        ("ID=debian\n", "apt install"),
        ("ID=fedora\n", "dnf install"),
        ("ID=bazzite\nID_LIKE=\"fedora\"\n", "dnf install"),
        ("ID=arch\n", "pacman"),
        ("ID=endeavouros\nID_LIKE=arch\n", "pacman"),
        ("ID=opensuse-tumbleweed\nID_LIKE=\"opensuse suse\"\n", "zypper"),
        ("ID=weirdos\n", "python3-venv"),
    ],
)
def test_no_venv_and_no_pip_gives_distro_specific_hint(
    tmp_path, os_release, expected
):
    py = wrapper(
        'case "$*" in *"-m venv"*|*"-m pip"*) exit 1;; esac'
    )
    osr = tmp_path / "os-release"
    osr.write_text(os_release)
    env = make_env(
        tmp_path,
        path=str(tool_dir(tmp_path, python=py)),
        STEAM_SHELF_OS_RELEASE=str(osr),
    )
    out = run(["sh", str(SCRIPT)], env, timeout=60)
    assert out.returncode != 0
    assert expected in out.stderr
    assert "Traceback" not in out.stderr

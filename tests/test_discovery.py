from pathlib import Path

import pytest

import list_shortcuts as ls


def make_steam(root: Path) -> Path:
    (root / "steamapps").mkdir(parents=True)
    return root


@pytest.mark.parametrize(
    "rel",
    [
        ".local/share/Steam",
        ".steam/steam",
        ".steam/root",
        ".steam/debian-installation",
        ".var/app/com.valvesoftware.Steam/.local/share/Steam",
        ".var/app/com.valvesoftware.Steam/data/Steam",
        "snap/steam/common/.local/share/Steam",
    ],
)
def test_finds_steam_in_known_locations(tmp_path, rel):
    steam = make_steam(tmp_path / rel)
    found = ls.find_steam_dir(home=tmp_path, env={})
    assert found.resolve() == steam.resolve()


def test_env_override_wins(tmp_path):
    make_steam(tmp_path / ".local/share/Steam")
    custom = make_steam(tmp_path / "elsewhere")
    found = ls.find_steam_dir(home=tmp_path, env={"STEAM_DIR": str(custom)})
    assert found.resolve() == custom.resolve()


def test_explicit_argument_wins_over_env(tmp_path):
    a = make_steam(tmp_path / "a")
    b = make_steam(tmp_path / "b")
    found = ls.find_steam_dir(
        home=tmp_path, env={"STEAM_DIR": str(b)}, explicit=str(a)
    )
    assert found.resolve() == a.resolve()


def test_prefers_default_over_later_candidates(tmp_path):
    default = make_steam(tmp_path / ".local/share/Steam")
    make_steam(tmp_path / ".var/app/com.valvesoftware.Steam/data/Steam")
    assert ls.find_steam_dir(home=tmp_path, env={}).resolve() == default.resolve()


def test_ignores_dirs_that_are_not_steam(tmp_path):
    (tmp_path / ".steam/steam").mkdir(parents=True)  # no steamapps/userdata
    assert ls.find_steam_dir(home=tmp_path, env={}) is None


def test_userdata_alone_counts(tmp_path):
    steam = tmp_path / ".local/share/Steam"
    (steam / "userdata").mkdir(parents=True)
    assert ls.find_steam_dir(home=tmp_path, env={}).resolve() == steam.resolve()


def test_returns_none_when_nothing_found(tmp_path):
    assert ls.find_steam_dir(home=tmp_path, env={}) is None


def test_xdg_data_home_is_honoured(tmp_path):
    xdg = tmp_path / "data"
    steam = make_steam(xdg / "Steam")
    found = ls.find_steam_dir(home=tmp_path, env={"XDG_DATA_HOME": str(xdg)})
    assert found.resolve() == steam.resolve()


def test_missing_steam_message_lists_searched_paths(tmp_path):
    msg = ls.not_found_message(home=tmp_path, env={})
    assert "STEAM_DIR" in msg
    assert str(tmp_path / ".local/share/Steam") in msg


def test_main_exits_nonzero_when_no_steam(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("STEAM_DIR", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    with pytest.raises(SystemExit) as exc:
        ls.main([])
    assert exc.value.code == 1
    assert "Steam" in capsys.readouterr().err


def test_main_runs_end_to_end(tmp_path, monkeypatch, capsys):
    steam = make_steam(tmp_path / ".steam/steam")
    (steam / "steamapps" / "appmanifest_10.acf").write_text(
        '"AppState"\n{\n\t"name"\t\t"Test Game"\n}\n'
    )
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("STEAM_DIR", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    ls.main([])
    assert "Test Game" in capsys.readouterr().out

import json
from pathlib import Path

from chess_explorer import import_pgn


def test_import_pgn_files(tmp_path: Path, sample_pgn_path: Path):
    out = tmp_path / "out.json"
    import_pgn.import_pgn_files("Hero", [sample_pgn_path], out_path=out, quiet=True)

    data = json.loads(out.read_text(encoding="utf-8"))
    games = data["games"]
    assert len(games) == 2  # third game skipped (username not present)
    ids = {g["game_id"] for g in games}
    assert "game1" in ids
    assert "game2" in ids

    colors = {g["color"] for g in games}
    assert colors == {"white", "black"}


def test_import_pgn_cli(tmp_path: Path, sample_pgn_path: Path, monkeypatch, capsys):
    out = tmp_path / "cli.json"
    argv = [
        "import_pgn.py",
        "Hero",
        str(sample_pgn_path),
        "--output",
        str(out),
        "--quiet",
    ]
    monkeypatch.setattr(import_pgn.sys, "argv", argv)
    import_pgn.main()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert len(data["games"]) == 2
    out_str = capsys.readouterr().out
    assert "Imported" in out_str or out_str == ""

import sys
from types import SimpleNamespace

import chess_explorer.top_positions as top_positions
import chess_explorer.import_pgn as import_pgn


def test_top_positions_cli_skip_eval(sample_games_path, monkeypatch, capsys):
    argv = ["top_positions.py", "--input", str(sample_games_path), "--plys", "4", "--limit", "2", "--skip-eval"]
    monkeypatch.setattr(sys, "argv", argv)
    top_positions.main()
    out = capsys.readouterr().out
    assert "Found" in out
    assert "FEN:" in out


def test_import_pgn_cli(sample_pgn_path, tmp_path, monkeypatch, capsys):
    out = tmp_path / "pgn.json"
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
    data = out.read_text(encoding="utf-8")
    assert "game1" in data

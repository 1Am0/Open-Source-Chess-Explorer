import argparse
import io
import sys
from pathlib import Path
from typing import Iterable, List

import chess.pgn
from tqdm import tqdm

from .constants import DEFAULT_GAMES_FILE
from .import_games import load_store, parse_game, save_store


def _collect_pgn_files(paths: Iterable[Path]) -> List[Path]:
    files: List[Path] = []
    for p in paths:
        p = Path(p)
        if p.is_dir():
            files.extend(sorted(p.rglob("*.pgn")))
        elif p.is_file() and p.suffix.lower() == ".pgn":
            files.append(p)
    return files


def import_pgn_files(username: str, inputs: Iterable[Path], out_path: Path = DEFAULT_GAMES_FILE, *, quiet: bool = False) -> None:
    username_l = username.lower().strip()
    files = _collect_pgn_files(inputs)
    if not files:
        if not quiet:
            print("No PGN files found.")
        return

    store = load_store(out_path)
    existing_ids = {g.get("game_id") for g in store["games"]}
    new_entries = []

    for file in files:
        with file.open("r", encoding="utf-8") as f:
            bar = tqdm(disable=quiet, desc=file.name, unit="game")
            game_idx = 0
            while True:
                game = chess.pgn.read_game(f)
                if game is None:
                    break
                game_idx += 1
                headers = game.headers
                white = headers.get("White", "").lower()
                black = headers.get("Black", "").lower()
                if white != username_l and black != username_l:
                    bar.update(1)
                    continue

                exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
                pgn_text = game.accept(exporter)
                parsed = parse_game(
                    pgn_text,
                    username,
                    time_class=headers.get("TimeClass"),
                    time_control_raw=headers.get("TimeControl"),
                )
                if not parsed.get("game_id"):
                    parsed["game_id"] = f"{file.name}-{game_idx}"

                if parsed["game_id"] in existing_ids:
                    bar.update(1)
                    continue

                new_entries.append(parsed)
                existing_ids.add(parsed["game_id"])
                bar.update(1)
            bar.close()

    if new_entries:
        store["games"] = new_entries + store["games"]
        save_store(store, out_path)

    if not quiet:
        print(f"Imported {len(new_entries)} new games to {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import local PGN files into games.json")
    parser.add_argument("username", help="Your username to identify color in PGNs")
    parser.add_argument("inputs", nargs="+", help="PGN files or directories containing PGNs")
    parser.add_argument(
        "--output", "-o", default=str(DEFAULT_GAMES_FILE), help="Path to output JSON (default games.json)"
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress progress and summary output")
    args = parser.parse_args()

    import_pgn_files(args.username, [Path(p) for p in args.inputs], out_path=Path(args.output), quiet=args.quiet)


if __name__ == "__main__":
    main()

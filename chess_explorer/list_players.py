import argparse
from pathlib import Path

from .storage import list_players, load_store, path_for_player


def describe_players(games_dir: Path, legacy_path: Path | None) -> list[tuple[str, int]]:
    names = list_players(games_dir)
    entries: list[tuple[str, int]] = []
    for name in names:
        path = path_for_player(name, games_dir)
        store = load_store(path)
        entries.append((name, len(store.get("games", []))))
    if legacy_path and legacy_path.exists():
        store = load_store(legacy_path)
        entries.insert(0, ("default", len(store.get("games", []))))
    return entries


def main() -> None:
    parser = argparse.ArgumentParser(description="List available player stores (games/<player>.json)")
    parser.add_argument("--games-dir", default="games", help="Directory for per-player JSON files (default games)")
    parser.add_argument(
        "--legacy-games",
        default=None,
        help="Optional legacy single games file (default autodetect games.json if present)",
    )
    args = parser.parse_args()

    games_dir = Path(args.games_dir).resolve()
    legacy_path = Path(args.legacy_games).resolve() if args.legacy_games else Path("games.json").resolve()
    if not legacy_path.exists():
        legacy_path = None

    games_dir.mkdir(parents=True, exist_ok=True)
    entries = describe_players(games_dir, legacy_path)

    if not entries:
        print("No players found. Add one via import or create a JSON under games/.")
        return

    for name, count in entries:
        print(f"{name}: {count} games")


if __name__ == "__main__":
    main()

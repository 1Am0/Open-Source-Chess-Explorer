import argparse
import concurrent.futures
import datetime as dt
import io
import json
from pathlib import Path
from typing import Dict, List, Tuple

import requests
import chess.pgn

GAMES_FILE = Path("games.json")
SCHEMA_VERSION = 1
HEADERS = {"User-Agent": "Open-Source-Chess-Explorer/1.0"}


def load_store() -> Dict:
    if not GAMES_FILE.exists():
        return {"version": SCHEMA_VERSION, "games": []}
    with GAMES_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if "version" not in data:
        data["version"] = SCHEMA_VERSION
    if "games" not in data:
        data["games"] = []
    return data


def save_store(store: Dict) -> None:
    GAMES_FILE.write_text(json.dumps(store, indent=4), encoding="utf-8")


def _print_progress(done: int, total: int, width: int = 30) -> None:
    pct = done / total if total else 1
    filled = int(width * pct)
    bar = "#" * filled + "-" * (width - filled)
    print(f"\rFetching archives [{bar}] {done}/{total}", end="", flush=True)


def _fetch_month(idx_url: Tuple[int, str]) -> Tuple[int, List[Dict]]:
    idx, archive_url = idx_url
    r = requests.get(archive_url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    monthly_games = r.json().get("games", [])
    return idx, list(reversed(monthly_games))


def fetch_all_archives(username: str) -> List[Dict]:
    archives_url = f"https://api.chess.com/pub/player/{username}/games/archives"
    r = requests.get(archives_url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    archives = r.json().get("archives", [])
    if not archives:
        return []

    items: List[Tuple[int, str]] = [(i, url) for i, url in enumerate(reversed(archives))]
    total = len(items)
    all_games: List[Dict] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, total)) as ex:
        for done, (idx, games) in enumerate(ex.map(_fetch_month, items), 1):
            # idx preserves newest->oldest order because items was built in that order
            all_games.append((idx, games))
            _print_progress(done, total)

    print()
    # sort by idx to maintain newest->oldest and flatten
    all_games_sorted: List[Dict] = []
    for _, games in sorted(all_games, key=lambda x: x[0]):
        all_games_sorted.extend(games)

    return all_games_sorted


def time_control_label(tc: str) -> str:
    """Map chess.com TimeControl to bullet/blitz/rapid/daily.

    Chess.com encodes as seconds[+increment] or correspondence like "1/86400".
    We approximate total time as base + 40 * increment (standard heuristic).
    Thresholds (per chess.com):
      - daily/correspondence: if tc has "/" or total >= 86400 seconds
      - bullet: total < 180s
      - blitz: 180s <= total < 600s
      - rapid: 600s <= total < 3600s
      - classical: total >= 3600s (rare in chess.com live)
    This correctly classifies 10+0 (600s) as rapid.
    """
    if not tc:
        return "rapid"
    if "/" in tc:
        return "daily"
    parts = tc.split("+")
    try:
        base = int(parts[0])
        inc = int(parts[1]) if len(parts) > 1 else 0
    except ValueError:
        return "rapid"

    total = base + 40 * inc
    if total >= 86400:
        return "daily"
    if total < 180:
        return "bullet"
    if total < 600:
        return "blitz"
    if total < 3600:
        return "rapid"
    return "classical"


def parse_game(pgn_text: str, username: str, time_class: str | None = None) -> Dict:
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        raise ValueError("Invalid PGN")
    headers = game.headers
    white = headers.get("White", "")
    black = headers.get("Black", "")
    username_l = username.lower()
    color = "white" if white.lower() == username_l else "black"
    opponent = black if color == "white" else white

    # Build SAN moves
    board = game.board()
    moves_san = []
    for move in game.mainline_moves():
        moves_san.append(board.san(move))
        board.push(move)

    raw_result = headers.get("Result", "*")
    if raw_result == "1-0":
        result = "1-0" if color == "white" else "0-1"
    elif raw_result == "0-1":
        result = "0-1" if color == "white" else "1-0"
    elif raw_result in ("1/2-1/2", "½-½"):
        result = "1/2-1/2"
    else:
        result = raw_result

    # Prefer end date if available, fallback to UTCDate/Date
    date_tag = headers.get("EndDate") or headers.get("UTCDate") or headers.get("Date", "0000.00.00")
    try:
        date = dt.datetime.strptime(date_tag, "%Y.%m.%d").date().isoformat()
    except ValueError:
        date = dt.date.today().isoformat()

    if time_class:
        tc = time_class.lower()
    else:
        tc = time_control_label(headers.get("TimeControl", ""))
    termination = headers.get("Termination", "")

    # Chess.com game_id is at end of URL
    url = headers.get("Link") or headers.get("Site", "")
    game_id = url.rstrip("/").split("/")[-1] if url else headers.get("Event", "")

    my_rating = int(headers.get("WhiteElo" if color == "white" else "BlackElo", 0))
    opp_rating = int(headers.get("BlackElo" if color == "white" else "WhiteElo", 0))

    return {
        "game_id": game_id,
        "moves": moves_san,
        "result": result,
        "color": color,
        "date": date,
        "opponent": opponent,
        "my_rating": my_rating,
        "opponent_rating": opp_rating,
        "time_control": tc,
        "termination": termination,
        "url": url,
    }


def import_games(username: str) -> None:
    username = username.strip()
    raw_games = fetch_all_archives(username)
    if not raw_games:
        print("No games found.")
        return

    store = load_store()
    existing_ids = {g.get("game_id") for g in store["games"]}

    new_entries: List[Dict] = []

    added = 0
    for g in raw_games:
        pgn = g.get("pgn", "")
        if not pgn:
            continue
        game = parse_game(pgn, username, time_class=g.get("time_class"))
        if game["game_id"] in existing_ids:
            continue
        new_entries.append(game)
        existing_ids.add(game["game_id"])
        added += 1

    if new_entries:
        store["games"] = new_entries + store["games"]

    # Ensure newest-first ordering for the entire store
    def _sort_key(game: Dict) -> Tuple[str, str]:
        return (game.get("date", "0000-00-00"), game.get("game_id", ""))

    store["games"].sort(key=_sort_key, reverse=True)

    save_store(store)
    print(f"Imported {added} new games to {GAMES_FILE}")


def main():
    parser = argparse.ArgumentParser(description="Import Chess.com games into games.json")
    parser.add_argument("username", nargs="?", help="Chess.com username")
    args = parser.parse_args()

    if args.username:
        import_games(args.username)
    else:
        username = input("Enter chess.com username: ").strip()
        import_games(username)


if __name__ == "__main__":
    main()
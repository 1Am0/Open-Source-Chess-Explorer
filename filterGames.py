import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from datetime import datetime

from Trie import Trie

GAMES_FILE = Path("games.json")


def _parse_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None


def filter_games(
    games: Iterable[Dict],
    *,
    color: Optional[str] = None,
    result: Optional[str] = None,
    opponent: Optional[str] = None,
    time_control: Optional[str] = None,
    time_control_raw: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    min_my_rating: Optional[int] = None,
    max_my_rating: Optional[int] = None,
    min_opponent_rating: Optional[int] = None,
    max_opponent_rating: Optional[int] = None,
    moves_start: Optional[int] = None,
    moves_end: Optional[int] = None,
) -> List[Dict]:
    """Return filtered games as a list of dicts without mutating the originals."""
    df = _parse_date(date_from)
    dt_ = _parse_date(date_to)

    filtered: List[Dict] = []
    for game in games:
        g_color = game.get("color")
        g_result = game.get("result")
        g_opponent = game.get("opponent", "")
        g_time = game.get("time_control")
        g_time_raw = game.get("time_control_raw")
        g_date_raw = game.get("date")
        g_date = _parse_date(g_date_raw)
        g_my = game.get("my_rating")
        g_opp = game.get("opponent_rating")

        if color and g_color != color:
            continue
        if result and g_result != result:
            continue
        if opponent and g_opponent.lower() != opponent.lower():
            continue
        if time_control and g_time != time_control:
            continue
        if time_control_raw and g_time_raw != time_control_raw:
            continue
        if df and (not g_date or g_date < df):
            continue
        if dt_ and (not g_date or g_date > dt_):
            continue
        if min_my_rating is not None and (g_my is None or g_my < min_my_rating):
            continue
        if max_my_rating is not None and (g_my is None or g_my > max_my_rating):
            continue
        if min_opponent_rating is not None and (g_opp is None or g_opp < min_opponent_rating):
            continue
        if max_opponent_rating is not None and (g_opp is None or g_opp > max_opponent_rating):
            continue

        start = moves_start if moves_start is not None else 0
        end = moves_end if moves_end is not None else None
        moves = game.get("moves", [])
        sliced_moves = moves[start:end]

        # Copy to avoid mutating input
        new_game = dict(game)
        new_game["moves"] = sliced_moves
        filtered.append(new_game)

    return filtered


def filter_games_to_json(games: Iterable[Dict], **kwargs) -> str:
    """Filter games and return a JSON string with schema {"version": 1, "games": [...]}."""
    filtered = filter_games(games, **kwargs)
    return json.dumps({"version": 1, "games": filtered}, indent=2)


def build_trie_from_games(games: Iterable[Dict]) -> Trie:
    """Create a Trie populated with the given games."""
    trie = Trie()
    for game in games:
        moves = game.get("moves") or []
        result = game.get("result", "*")
        trie.add_game(moves, result)
    return trie


def build_color_tries(games: Iterable[Dict]) -> Dict[str, Trie]:
    """Create separate tries for white and black games."""
    tries = {"white": Trie(), "black": Trie()}
    for game in games:
        color = game.get("color")
        if color not in tries:
            continue
        moves = game.get("moves") or []
        result = game.get("result", "*")
        tries[color].add_game(moves, result)
    return tries


def load_games(path: Path = GAMES_FILE) -> List[Dict]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("games", [])

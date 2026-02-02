import argparse
import csv
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from .constants import USER_AGENT
from .filter_games import filter_games, load_games

try:
    import chess
except ImportError:  # pragma: no cover - import guard
    sys.exit("python-chess is required: pip install python-chess")


CONTACTABLE_UA = f"{USER_AGENT} (+https://github.com/antho)"
DEFAULT_CACHE_PATH = Path(".cache/lichess_eval.json")
DEFAULT_CACHE_TTL = 7 * 24 * 60 * 60  # 7 days


def _load_cache(cache_path: Path) -> Dict[str, Dict]:
    if not cache_path.exists():
        return {}
    try:
        with cache_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_cache(cache_path: Path, cache: Dict[str, Dict]) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache, indent=2), encoding="utf-8")


def _format_eval(score: Dict[str, float | int | None]) -> str:
    if not score:
        return "eval unavailable"
    if score.get("mate") is not None:
        return f"#{score['mate']}" + (f" depth {score.get('depth')}" if score.get("depth") is not None else "")
    if score.get("cp") is not None:
        cp = score.get("cp")
        depth_part = f" depth {score.get('depth')}" if score.get("depth") is not None else ""
        return f"{cp/100:.2f}{depth_part}" if isinstance(cp, (int, float)) else f"?{depth_part}"
    return "eval unavailable"


def _get_cached_eval(fen: str, cache: Dict[str, Dict], ttl: int) -> str | None:
    entry = cache.get(fen)
    if not entry:
        return None
    ts = entry.get("ts")
    if ts is None or (time.time() - ts) > ttl:
        return None
    return _format_eval(entry)


def _fetch_lichess_eval(
    fen: str,
    *,
    retries: int = 1,
    debug: bool = False,
    cache: Dict[str, Dict],
    cache_path: Path,
    ttl: int,
) -> str:
    """Return a short human-friendly eval string from Lichess cloud eval."""
    cached = _get_cached_eval(fen, cache, ttl)
    if cached is not None:
        return cached

    url = "https://lichess.org/api/cloud-eval?fen=" + urllib.parse.quote(fen)
    headers = {"User-Agent": CONTACTABLE_UA, "Accept": "application/json"}
    req = urllib.request.Request(url, headers=headers)

    attempt = 0
    while True:
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                payload = json.loads(resp.read())
            break
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return "eval unavailable (not cached on lichess)"
            return f"eval unavailable (http {e.code})"
        except urllib.error.URLError as e:
            if attempt >= retries:
                detail = f": {e.reason}" if debug and getattr(e, "reason", None) else ""
                return f"eval unavailable (network error{detail})"
            attempt += 1
            continue
        except json.JSONDecodeError:
            return "eval unavailable (bad response)"

    pvs = payload.get("pvs") or []
    best = pvs[0] if pvs else None
    depth = payload.get("depth")
    if not best:
        return "eval unavailable"

    score_entry: Dict[str, int | float | None] = {
        "mate": best.get("mate"),
        "cp": best.get("cp"),
        "depth": depth,
        "ts": time.time(),
    }
    cache[fen] = score_entry
    _save_cache(cache_path, cache)
    return _format_eval(score_entry)


def _fen_after_plys(moves: Iterable[str], ply_target: int) -> str:
    board = chess.Board()
    for idx, san in enumerate(moves):
        if idx >= ply_target:
            break
        try:
            board.push_san(san)
        except ValueError:
            break
    return board.fen()


def most_common_positions(games: Iterable[Dict], ply_target: int) -> Counter:
    counts: Counter = Counter()
    for game in games:
        moves = game.get("moves") or []
        if len(moves) < ply_target:
            continue
        fen = _fen_after_plys(moves, ply_target)
        counts[fen] += 1
    return counts


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Show the most common positions (as FEN) after N plies with Lichess evals."
    )
    ap.add_argument("--input", default="games.json", help="Path to games JSON (default games.json)")
    ap.add_argument("--color", choices=["white", "black"])
    ap.add_argument("--result", choices=["1-0", "0-1", "1/2-1/2"])
    ap.add_argument("--opponent")
    ap.add_argument("--time-control", dest="time_control", choices=["bullet", "blitz", "rapid", "classical"])
    ap.add_argument("--time-control-raw", dest="time_control_raw")
    ap.add_argument("--date-from")
    ap.add_argument("--date-to")
    ap.add_argument("--min-my-rating", type=int)
    ap.add_argument("--max-my-rating", type=int)
    ap.add_argument("--min-opponent-rating", type=int)
    ap.add_argument("--max-opponent-rating", type=int)
    ap.add_argument("--moves-start", type=int)
    ap.add_argument("--moves-end", type=int)
    ap.add_argument(
        "--plys", type=int, default=10, help="Number of plies to reach before recording a position (default 10)"
    )
    ap.add_argument("--limit", type=int, default=5, help="How many top positions to show (default 5)")
    ap.add_argument("--skip-eval", action="store_true", help="Skip calling Lichess cloud eval API")
    ap.add_argument("--eval-debug", action="store_true", help="Show eval request URLs and network error details")
    ap.add_argument("--eval-cache", default=str(DEFAULT_CACHE_PATH), help="Path to eval cache file (JSON)")
    ap.add_argument("--eval-cache-ttl", type=int, default=DEFAULT_CACHE_TTL, help="Cache TTL in seconds (default 7 days)")
    ap.add_argument("--output-json", help="Write results to a JSON file")
    ap.add_argument("--output-csv", help="Write results to a CSV file")
    args = ap.parse_args()

    games = load_games(Path(args.input))
    filtered = filter_games(
        games,
        color=args.color,
        result=args.result,
        opponent=args.opponent,
        time_control=args.time_control,
        time_control_raw=args.time_control_raw,
        date_from=args.date_from,
        date_to=args.date_to,
        min_my_rating=args.min_my_rating,
        max_my_rating=args.max_my_rating,
        min_opponent_rating=args.min_opponent_rating,
        max_opponent_rating=args.max_opponent_rating,
        moves_start=args.moves_start,
        moves_end=args.moves_end,
    )

    if not filtered:
        print("No games match the provided filters.")
        return

    if args.plys <= 0:
        print("--plys must be positive")
        return

    counts = most_common_positions(filtered, args.plys)
    if not counts:
        print("No positions reached the requested ply depth.")
        return

    top_positions: List[Tuple[str, int]] = counts.most_common(args.limit)
    print(f"Found {len(filtered)} games after filtering. Showing top {len(top_positions)} positions at ply {args.plys}.")

    cache_path = Path(args.eval_cache)
    cache = _load_cache(cache_path)

    results: List[Dict[str, str | int]] = []
    for idx, (fen, freq) in enumerate(top_positions, start=1):
        if args.eval_debug:
            print(f"Eval URL: https://lichess.org/api/cloud-eval?fen={urllib.parse.quote(fen)}")
        eval_str = "(skipped)" if args.skip_eval else _fetch_lichess_eval(
            fen,
            debug=args.eval_debug,
            retries=1,
            cache=cache,
            cache_path=cache_path,
            ttl=args.eval_cache_ttl,
        )
        print(f"\n{idx}. Seen in {freq} games")
        print(f"FEN: {fen}")
        print(f"Eval: {eval_str}")
        results.append({"rank": idx, "fen": fen, "count": freq, "eval": eval_str})

    if args.output_json:
        Path(args.output_json).write_text(json.dumps({"plys": args.plys, "positions": results}, indent=2), encoding="utf-8")
    if args.output_csv:
        with Path(args.output_csv).open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["rank", "fen", "count", "eval"])
            writer.writeheader()
            writer.writerows(results)


if __name__ == "__main__":
    main()

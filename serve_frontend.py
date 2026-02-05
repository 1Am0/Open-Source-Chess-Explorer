"""Serve a minimal web UI over the existing chess explorer data."""

import argparse
import json
import time
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from socketserver import TCPServer
from typing import Dict, Iterable, List, Tuple
from urllib.parse import urlparse

import chess

from chess_explorer.filter_games import build_color_tries, filter_games
from chess_explorer.import_games import import_games
from chess_explorer.storage import (
    list_players,
    load_games,
    load_store,
    path_for_player,
)
from chess_explorer.trie import Trie


class GameCache:
    """Cache filtered games and tries keyed by player + filter tuple."""

    def __init__(self, games_dir: Path, legacy_path: Path | None) -> None:
        self.games_dir = games_dir
        self.legacy_path = legacy_path if legacy_path and legacy_path.exists() else None
        self._mtimes: Dict[str, float | None] = {}
        self._games: Dict[str, List[Dict]] = {}
        self._tries_cache: Dict[Tuple[str, Tuple], Tuple[Dict[str, Trie], Dict[str, int], List[Dict]]] = {}

    def _player_key_and_path(self, player: str | None) -> Tuple[str, Path | None]:
        if player:
            return player, path_for_player(player, self.games_dir)
        if self.legacy_path and self.legacy_path.exists():
            return "default", self.legacy_path
        players = list_players(self.games_dir)
        if players:
            first = players[0]
            return first, path_for_player(first, self.games_dir)
        return "default", None

    def _load_games_if_needed(self, player_key: str, path: Path | None) -> None:
        if path is None or not path.exists():
            self._games[player_key] = []
            self._mtimes[player_key] = None
            self._tries_cache = {k: v for k, v in self._tries_cache.items() if k[0] != player_key}
            return

        try:
            mtime = path.stat().st_mtime
        except OSError:
            mtime = None

        if self._mtimes.get(player_key) == mtime:
            return

        self._games[player_key] = load_games(path)
        self._tries_cache = {k: v for k, v in self._tries_cache.items() if k[0] != player_key}
        self._mtimes[player_key] = mtime

    def invalidate(self) -> None:
        self._mtimes.clear()
        self._games.clear()
        self._tries_cache.clear()

    def _filters_key(self, filters: Dict) -> Tuple:
        return (
            filters.get("color"),
            filters.get("result"),
            filters.get("opponent"),
            filters.get("time_control"),
            filters.get("time_control_raw"),
            filters.get("date_from"),
            filters.get("date_to"),
            filters.get("min_my_rating"),
            filters.get("max_my_rating"),
            filters.get("min_opponent_rating"),
            filters.get("max_opponent_rating"),
            filters.get("moves_start"),
            filters.get("moves_end"),
        )

    def get_filtered(
        self, filters: Dict, player: str | None
    ) -> Tuple[str, Dict[str, Trie], Dict[str, int], List[Dict]]:
        player_key, path = self._player_key_and_path(player)
        self._load_games_if_needed(player_key, path)
        key = (player_key, self._filters_key(filters))
        cached = self._tries_cache.get(key)
        if cached:
            tries, counts, filtered = cached
            return player_key, tries, counts, filtered

        games = self._games.get(player_key, [])
        filtered = filter_games(games, **filters)
        tries = build_color_tries(filtered)
        counts = {color: len([g for g in filtered if g.get("color") == color]) for color in ("white", "black")}
        self._tries_cache[key] = (tries, counts, filtered)
        return player_key, tries, counts, filtered


def empty_stats() -> Dict[str, float]:
    return {
        "wins": 0,
        "losses": 0,
        "draws": 0,
        "total": 0,
        "winRate": 0.0,
        "drawRate": 0.0,
        "lossRate": 0.0,
    }


def available_players(games_dir: Path, legacy_path: Path | None) -> List[str]:
    names = set(list_players(games_dir))
    if legacy_path and legacy_path.exists():
        names.add("default")
    return sorted(names)


def next_moves_for_path(trie: Trie, path: Iterable[str]) -> Tuple[Dict[str, float], List[Dict[str, Dict]]]:
    node = trie.find(path)
    if node is None:
        return empty_stats(), []
    stats = node.stats()
    moves = [
        {"move": mv, "stats": st}
        for mv, st in sorted(
            node.next_moves().items(), key=lambda kv: (kv[1].get("total", 0), kv[0]), reverse=True
        )
    ]
    return stats, moves


def build_response(payload: Dict, cache: GameCache) -> Dict:
    t0 = time.perf_counter()
    raw_path = payload.get("path") or []
    if not isinstance(raw_path, list):
        raise ValueError("path must be a list of SAN moves")
    path: List[str] = [str(m) for m in raw_path]

    t1 = time.perf_counter()
    filters = {
        "color": payload.get("color") or None,
        "result": payload.get("result") or None,
        "opponent": payload.get("opponent") or None,
        "time_control": payload.get("time_control") or None,
        "time_control_raw": payload.get("time_control_raw") or None,
        "date_from": payload.get("date_from") or None,
        "date_to": payload.get("date_to") or None,
        "min_my_rating": payload.get("min_my_rating"),
        "max_my_rating": payload.get("max_my_rating"),
        "min_opponent_rating": payload.get("min_opponent_rating"),
        "max_opponent_rating": payload.get("max_opponent_rating"),
        "moves_start": payload.get("moves_start"),
        "moves_end": payload.get("moves_end"),
    }

    t2 = time.perf_counter()
    player = payload.get("player")
    player_key, tries, counts, filtered = cache.get_filtered(filters, player)
    if not filtered:
        t_done = time.perf_counter()
        duration_ms = (t_done - t0) * 1000
        print(f"[perf] path={duration_ms:.1f}ms (empty result)", flush=True)
        return {
            "player": player_key,
            "games": 0,
            "path": path,
            "fen": chess.STARTING_FEN,
            "stats": empty_stats(),
            "next": [],
        }

    chosen = filters["color"] or ("white" if counts.get("white", 0) >= counts.get("black", 0) else "black")
    if counts.get(chosen, 0) == 0:
        chosen = "black" if chosen == "white" else "white"

    trie = tries[chosen]

    t3 = time.perf_counter()
    board = chess.Board()
    for san in path:
        try:
            board.push_san(san)
        except ValueError:
            raise ValueError(f"Invalid move sequence: {san}")

    t4 = time.perf_counter()
    stats, moves = next_moves_for_path(trie, path)

    t_done = time.perf_counter()
    duration_ms = (t_done - t0) * 1000
    print(
        "[perf] total={:.1f}ms path_parse={:.1f}ms filters={:.1f}ms cache+filter={:.1f}ms board={:.1f}ms next={:.1f}ms".format(
            duration_ms,
            (t1 - t0) * 1000,
            (t2 - t1) * 1000,
            (t3 - t2) * 1000,
            (t4 - t3) * 1000,
            (t_done - t4) * 1000,
        ),
        flush=True,
    )

    return {
        "player": player_key,
        "color": chosen,
        "games": len(filtered),
        "path": path,
        "fen": board.fen(),
        "stats": stats,
        "next": moves,
    }


def handle_import(payload: Dict, cache: GameCache, games_dir: Path) -> Dict:
    username = (payload.get("username") or "").strip()
    if not username:
        return {"error": "username is required"}, 400

    player = (payload.get("player") or username).strip()
    target_path = path_for_player(player, games_dir)

    before = load_store(target_path)
    before_count = len(before.get("games", []))
    try:
        import_games(username, player=player, out_path=target_path, quiet=False)
    except Exception as exc:  # noqa: BLE001 - return message to client
        return {"error": str(exc)}, 500

    cache.invalidate()
    after = load_store(target_path)
    after_count = len(after.get("games", []))
    added = max(0, after_count - before_count)
    return {"imported": added, "total": after_count, "username": username, "player": player}, 200


def make_handler(frontend_dir: Path, cache: GameCache, games_dir: Path, legacy_path: Path | None):
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            self._games_dir = games_dir
            self._legacy_path = legacy_path
            super().__init__(*args, directory=str(frontend_dir), **kwargs)

        def log_message(self, fmt, *args):  # noqa: N802 - keep server quiet
            return

        def _json(self, payload: Dict, status: int = 200):
            data = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):  # noqa: N802 - HTTP verb
            parsed = urlparse(self.path)
            try:
                length = int(self.headers.get("Content-Length", 0))
            except ValueError:
                length = 0
            body = self.rfile.read(length) if length else b"{}"

            try:
                payload = json.loads(body or b"{}")
            except json.JSONDecodeError:
                self._json({"error": "invalid json"}, status=400)
                return

            if parsed.path == "/api/next-moves":
                try:
                    response = build_response(payload, cache)
                except ValueError as exc:
                    self._json({"error": str(exc)}, status=400)
                    return
                self._json(response, status=200)
                return

            if parsed.path == "/api/import":
                response, status = handle_import(payload, cache, self._games_dir)
                self._json(response, status=status)
                return

            self.send_error(404)

        def do_GET(self):  # noqa: N802 - HTTP verb
            parsed = urlparse(self.path)
            if parsed.path == "/api/players":
                players = available_players(self._games_dir, self._legacy_path)
                self._json({"players": players}, status=200)
                return
            super().do_GET()

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve a simple Chess Explorer frontend")
    parser.add_argument("--port", type=int, default=8000, help="Port to serve (default 8000)")
    parser.add_argument("--games-dir", default="games", help="Directory for per-player games JSON files (default games)")
    parser.add_argument(
        "--legacy-games",
        default=None,
        help="Optional legacy single games file (default autodetect games.json if present)",
    )
    parser.add_argument("--frontend", default="frontend", help="Directory containing index.html")
    args = parser.parse_args()

    front = Path(args.frontend).resolve()
    if not front.exists():
        raise SystemExit(f"Frontend directory not found: {front}")
    games_dir = Path(args.games_dir).resolve()
    games_dir.mkdir(parents=True, exist_ok=True)

    legacy_path = Path(args.legacy_games).resolve() if args.legacy_games else Path("games.json").resolve()
    if not legacy_path.exists():
        legacy_path = None

    cache = GameCache(games_dir, legacy_path)
    handler = make_handler(front, cache, games_dir, legacy_path)
    with TCPServer(("", args.port), handler) as httpd:
        target = legacy_path if legacy_path else games_dir
        print(f"Serving {front} on http://localhost:{args.port} (games at {target})")
        print("Press Ctrl+C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping server.")


if __name__ == "__main__":
    main()

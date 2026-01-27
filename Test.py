from Trie import Trie
import io
import json
from pathlib import Path
import re
import requests
import chess
import chess.pgn
from rich.console import Console, Group
from rich.live import Live
from rich.table import Table


HEADERS = {"User-Agent": "OpenSourceChessExplorer/0.1 (+https://github.com/antho/Open-Source-Chess-Explorer)"}
EVAL_CACHE_PATH = Path("eval_cache.json")


def format_bar(stats: dict, width: int = 30) -> str:
    total = stats.get("total", 0)
    if total == 0:
        return " " * width
    w_count = int(round(width * stats.get("winRate", 0)))
    d_count = int(round(width * stats.get("drawRate", 0)))
    l_count = width - w_count - d_count
    return "#" * w_count + "=" * d_count + "-" * l_count


def main() -> None:
    tries = {"white": Trie(), "black": Trie()}
    eval_cache: dict[str, str] = {}
    console = Console()

    def normalize_eval_str(val: str) -> str:
        if val.startswith("Mate in"):
            return val.split("(")[0].strip()
        m = re.search(r"([+-]?\d+(?:\.\d+)?)", val)
        if m:
            return f"{float(m.group(1)):+.2f}"
        return val

    def load_eval_cache() -> dict[str, str]:
        if EVAL_CACHE_PATH.exists():
            try:
                raw = json.loads(EVAL_CACHE_PATH.read_text(encoding="utf-8"))
                return {k: normalize_eval_str(v) for k, v in raw.items()}
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def save_eval_cache() -> None:
        try:
            EVAL_CACHE_PATH.write_text(json.dumps(eval_cache, indent=2), encoding="utf-8")
        except OSError:
            pass

    def parse_pgn_moves(pgn: str) -> tuple[list[str], str]:
        game = chess.pgn.read_game(io.StringIO(pgn))
        if game is None:
            return [], "1/2-1/2"
        result = game.headers.get("Result", "1/2-1/2")
        board = game.board()
        moves: list[str] = []
        for move in game.mainline_moves():
            moves.append(board.san(move))
            board.push(move)
        return moves, result

    def map_result_to_player(result: str, color: str) -> str:
        token = result.strip()
        if color == "black":
            if token == "1-0":
                return "0-1"
            if token == "0-1":
                return "1-0"
        return token

    def fetch_last_games(username: str, count: int = 10) -> list[tuple[str, list[str], str]]:
        uname = username.lower()
        archives_url = f"https://api.chess.com/pub/player/{username}/games/archives"
        resp = requests.get(archives_url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        archives = resp.json().get("archives", [])
        parsed_games: list[tuple[str, list[str], str]] = []
        for archive_url in reversed(archives):
            if len(parsed_games) >= count:
                break
            resp = requests.get(archive_url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            games_json = resp.json().get("games", [])
            for game in reversed(games_json):
                if len(parsed_games) >= count:
                    break
                white = game.get("white", {})
                black = game.get("black", {})
                if white.get("username", "").lower() == uname:
                    color = "white"
                elif black.get("username", "").lower() == uname:
                    color = "black"
                else:
                    print("Skipping game not involving user.")
                    continue
                pgn = game.get("pgn", "")
                moves, result = parse_pgn_moves(pgn)
                player_result = map_result_to_player(result, color)
                parsed_games.append((color, moves, player_result))
        return parsed_games

    def line_to_board(line: list[str]) -> chess.Board | None:
        board = chess.Board()
        try:
            for san in line:
                board.push_san(san)
        except ValueError:
            return None
        return board

    def format_eval(eval_json: dict, board: chess.Board) -> str:
        if not eval_json:
            return "no eval"
        pvs = eval_json.get("pvs", [])
        if not pvs:
            return "no eval"
        pv = pvs[0]
        depth = pv.get("depth") or eval_json.get("depth")
        if "mate" in pv:
            return f"Mate in {pv['mate']}"
        if "cp" in pv:
            cp = pv["cp"]
            score = cp / 100.0
            return f"{score:+.2f}"
        return "no eval"

    def fetch_cloud_eval(board: chess.Board) -> str:
        fen = board.fen()
        cached = eval_cache.get(fen)
        if cached is not None:
            return cached
        try:
            resp = requests.get(
                "https://lichess.org/api/cloud-eval",
                params={"fen": fen},
                headers={**HEADERS, "Accept": "application/json"},
                timeout=10,
            )
            if resp.status_code == 429:
                eval_cache[fen] = "rate limited"
                return "rate limited"
            resp.raise_for_status()
            eval_json = resp.json()
            formatted = normalize_eval_str(format_eval(eval_json, board))
        except requests.RequestException:
            formatted = "eval unavailable"
        eval_cache[fen] = formatted
        save_eval_cache()
        return formatted

    username = input("Enter chess.com username: ").strip()
    games = fetch_last_games(username)

    for color, moves, result in games:
        tries[color].add_game(moves, result)

    eval_cache.update(load_eval_cache())

    def print_out(line, color):
        trie = tries[color]

        def compute_state():
            node = trie.find(line)
            board = line_to_board(line)
            line_eval = "invalid line" if board is None else eval_cache.get(board.fen(), "pending eval")
            next_moves = trie.next_moves(line) if node else {}
            sorted_moves = sorted(next_moves.items(), key=lambda kv: kv[1].get("total", 0), reverse=True)[:5]
            cont = []
            for move, stats in sorted_moves:
                if board:
                    try:
                        next_board = board.copy(stack=False)
                        next_board.push_san(move)
                        fen = next_board.fen()
                        eval_str = eval_cache.get(fen, "pending eval")
                        cont.append((move, stats, eval_str, fen, next_board))
                    except ValueError:
                        cont.append((move, stats, "invalid move", None, None))
                else:
                    cont.append((move, stats, "invalid line", None, None))
            return node, board, line_eval, cont

        def render_view(node, board, line_eval, cont):
            header = f"Perspective: {color.capitalize()}"
            line_txt = f"Line: {' '.join(line) if line else 'Starting Position'}"
            eval_txt = f"Eval: {line_eval}"
            if not node:
                return Group(header, line_txt, eval_txt, "<missing in this perspective>")
            stats = node.stats()
            totals_bar = format_bar(stats)
            totals_txt = f"Totals |{totals_bar}| T:{stats['total']:3} W:{stats['wins']:3} D:{stats['draws']:3} L:{stats['losses']:3}"
            table = Table(show_edge=False, show_header=True, pad_edge=False)
            table.add_column("Move", justify="left", no_wrap=True)
            table.add_column("Bar", justify="left", no_wrap=True)
            table.add_column("T", justify="right", no_wrap=True)
            table.add_column("W", justify="right", no_wrap=True)
            table.add_column("D", justify="right", no_wrap=True)
            table.add_column("L", justify="right", no_wrap=True)
            table.add_column("Eval", justify="left")
            for move, stats_move, eval_str, _fen, _b in cont:
                total = stats_move.get("total", 0)
                wins = stats_move.get("wins", 0)
                draws = stats_move.get("draws", 0)
                losses = stats_move.get("losses", 0)
                bar = format_bar(stats_move)
                table.add_row(move, f"|{bar}|", str(total), str(wins), str(draws), str(losses), eval_str)
            return Group(header, line_txt, eval_txt, totals_txt, "-" * 100, table)

        node, board, line_eval, cont = compute_state()
        with Live(render_view(node, board, line_eval, cont), console=console, refresh_per_second=8, screen=False) as live:
            pending: list[tuple[str, chess.Board]] = []
            if board and line_eval == "pending eval":
                pending.append((board.fen(), board))
            for _move, _stats_move, eval_str, fen, b in cont:
                if fen and b and eval_str == "pending eval":
                    pending.append((fen, b))
            seen: set[str] = set()
            unique_pending = []
            for fen, b in pending:
                if fen in seen:
                    continue
                seen.add(fen)
                unique_pending.append((fen, b))
            for fen, b in unique_pending:
                fetch_cloud_eval(b)
                node, board, line_eval, cont = compute_state()
                live.update(render_view(node, board, line_eval, cont))

    line: list[str] = []
    color = "white"
    while True:
        print_out(line, color)
        user_input = input("Enter next move (or 'back' to undo, 'reset' to start over, 'white'/'black' to switch, 'exit' to quit): ").strip()
        cmd = user_input.lower()
        if cmd == "back":
            if line:
                line.pop()
            continue
        if cmd == "reset":
            line = []
            continue
        if cmd in {"white", "black"}:
            color = cmd
            continue
        if cmd == "exit":
            break
        line.append(user_input)

if __name__ == "__main__":
    main()
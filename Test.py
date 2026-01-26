from Trie import Trie
import io
import requests
import chess.pgn


HEADERS = {"User-Agent": "OpenSourceChessExplorer/0.1 (+https://github.com/antho/Open-Source-Chess-Explorer)"}


def format_bar(stats: dict, width: int = 30) -> str:
    total = stats.get("total", 0)
    if total == 0:
        return " " * width
    w_count = int(round(width * stats.get("winRate", 0)))
    d_count = int(round(width * stats.get("drawRate", 0)))
    l_count = width - w_count - d_count
    return "#" * w_count + "=" * d_count + "-" * l_count


def print_next_move_bars(next_moves: dict) -> None:
    if not next_moves:
        print("No continuations available.")
        return
    sorted_moves = sorted(next_moves.items(), key=lambda kv: kv[1].get("total", 0), reverse=True)
    for move, stats in sorted_moves:
        total = stats.get("total", 0)
        bar = format_bar(stats)
        wins = stats.get("wins", 0)
        draws = stats.get("draws", 0)
        losses = stats.get("losses", 0)
        print(f"{move:6} |{bar}| T:{total:3} W:{wins:3} D:{draws:3} L:{losses:3}")


def main() -> None:
    trie = Trie()

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

    def fetch_last_games(username: str, count: int = 10) -> list[tuple[list[str], str]]:
        uname = username.lower()
        archives_url = f"https://api.chess.com/pub/player/{username}/games/archives"
        resp = requests.get(archives_url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        archives = resp.json().get("archives", [])
        parsed_games: list[tuple[list[str], str]] = []
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
                if white.get("username", "").lower() != uname:
                    continue
                pgn = game.get("pgn", "")
                moves, result = parse_pgn_moves(pgn)
                parsed_games.append((moves, result))
        return parsed_games

    username = input("Enter chess.com username: ").strip()
    games = fetch_last_games(username)

    for moves, result in games:
        trie.add_game(moves, result)

    def printOut(line):
        node = trie.find(line)

        print("Line:", " ".join(line) if line else "Starting Position")
        if node:
            stats = node.stats()
            bar = format_bar(stats)
            print(f"Totals |{bar}| T:{stats['total']:3} W:{stats['wins']:3} D:{stats['draws']:3} L:{stats['losses']:3}")
            print("-" * 100)
            print_next_move_bars(trie.next_moves(line))
        else:
            line.pop()
            print("<missing>")

    line = []
    while True:
        printOut(line)
        user_input = input("Enter next move (or 'back' to undo, 'exit' to quit): ").strip()
        if user_input.lower() == "back":
            if line:
                line.pop()
            continue
        if user_input.lower() == "exit":
            break
        line.append(user_input)

if __name__ == "__main__":
    main()
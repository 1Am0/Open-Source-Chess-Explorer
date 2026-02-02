import argparse
from pathlib import Path
from typing import Dict, List, Tuple

from .filter_games import build_color_tries, filter_games, load_games
from .trie import Trie


def _format_stats(stats: Dict[str, float]) -> str:
    total = stats.get("total", 0)
    w = stats.get("wins", 0)
    d = stats.get("draws", 0)
    l = stats.get("losses", 0)
    return f"T {total} | W {w} D {d} L {l}" if total else "T 0"


def _list_next_moves(trie: Trie, path: List[str], top: int) -> List[Tuple[str, Dict[str, float]]]:
    node = trie.find(path)
    if node is None:
        return []
    items = list(node.next_moves().items())
    items.sort(key=lambda kv: (kv[1].get("total", 0), kv[0]), reverse=True)
    return items[:top]


def interactive_traverse(trie: Trie, *, color_label: str = "", top: int = 20) -> None:
    path: List[str] = []
    while True:
        node = trie.find(path)
        stats = node.stats() if node else {"total": 0, "wins": 0, "draws": 0, "losses": 0}
        prefix = f"[{color_label}] " if color_label else ""
        print("\n" + prefix + "Path:", " ".join(path) if path else "<start>")
        print(prefix + "Current:", _format_stats(stats))

        moves = _list_next_moves(trie, path, top)
        if not moves:
            print("No further moves. (b)ack, (r)eset, (q)uit")
        else:
            print("Next moves (choose number, or b/r/q):")
            for idx, (move, st) in enumerate(moves, 1):
                print(f"  {idx}. {move}  {_format_stats(st)}")

        choice = input("> ").strip().lower()
        if choice in {"q", "quit"}:
            break
        if choice in {"r", "reset"}:
            path = []
            continue
        if choice in {"b", "back"}:
            if path:
                path.pop()
            else:
                print("Already at root.")
            continue

        if choice.isdigit():
            num = int(choice)
            if 1 <= num <= len(moves):
                path.append(moves[num - 1][0])
            else:
                print("Invalid selection.")
            continue

        print("Commands: number to dive, b=back, r=reset, q=quit")


def main() -> None:
    ap = argparse.ArgumentParser(description="Filter games and explore move trie interactively.")
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
    ap.add_argument("--top", type=int, default=20, help="How many next moves to display (default 20)")
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

    tries = build_color_tries(filtered)
    counts = {"white": 0, "black": 0}
    for g in filtered:
        col = g.get("color")
        if col in counts:
            counts[col] += 1

    if args.color:
        if counts.get(args.color, 0) == 0:
            print(f"No {args.color} games match the provided filters.")
            return
        chosen = args.color
    else:
        available = [c for c, n in counts.items() if n > 0]
        if not available:
            print("No games match the provided filters.")
            return
        if len(available) == 1:
            chosen = available[0]
        else:
            choice = input("Explore color? [w/b] (default w): ").strip().lower()
            chosen = "black" if choice.startswith("b") else "white"
            if counts[chosen] == 0:
                chosen = "black" if chosen == "white" else "white"

    trie = tries[chosen]
    print(f"Loaded {counts[chosen]} {chosen} games into trie. Interactive traversal starting.")
    interactive_traverse(trie, color_label=chosen, top=args.top)


if __name__ == "__main__":
    main()

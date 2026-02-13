#!/usr/bin/env python3
"""Benchmark trie building performance for a player's games."""

import argparse
import time
from pathlib import Path

from chess_explorer.filter_games import build_color_tries
from chess_explorer.storage import load_games, path_for_player


def benchmark_trie(username: str, games_dir: Path = Path("games")) -> None:
    """Load games for a player and time trie construction."""
    player_path = path_for_player(username, games_dir)
    
    if not player_path.exists():
        print(f"❌ Player file not found: {player_path}")
        print(f"\nAvailable players in {games_dir}:")
        for p in sorted(games_dir.glob("*.json")):
            print(f"  - {p.stem}")
        return
    
    print(f"Loading games from: {player_path}")
    t0 = time.perf_counter()
    games = load_games(player_path)
    t1 = time.perf_counter()
    load_ms = (t1 - t0) * 1000
    print(f"  ✓ Loaded {len(games)} games in {load_ms:.1f}ms")
    
    if not games:
        print("❌ No games found")
        return
    
    print(f"\nBuilding tries...")
    t0 = time.perf_counter()
    tries = build_color_tries(games)
    t1 = time.perf_counter()
    trie_ms = (t1 - t0) * 1000
    
    white_total = tries["white"].root.totalWins + tries["white"].root.totalLosses + tries["white"].root.totalDraws
    black_total = tries["black"].root.totalWins + tries["black"].root.totalLosses + tries["black"].root.totalDraws
    
    print(f"  ✓ Built tries in {trie_ms:.1f}ms")
    print(f"    - White games: {white_total}")
    print(f"    - Black games: {black_total}")
    print(f"\nTotal time: {load_ms + trie_ms:.1f}ms")
    print(f"  - JSON parsing: {load_ms:.1f}ms ({load_ms/(load_ms+trie_ms)*100:.0f}%)")
    print(f"  - Trie building: {trie_ms:.1f}ms ({trie_ms/(load_ms+trie_ms)*100:.0f}%)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark trie building for a player")
    parser.add_argument("username", help="Player username (e.g., 'anthon2010')")
    parser.add_argument("--games-dir", default="games", help="Directory with player JSON files")
    args = parser.parse_args()
    
    benchmark_trie(args.username, Path(args.games_dir))


if __name__ == "__main__":
    main()

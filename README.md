# Open-Source Chess Explorer

Command-line helpers to import all your chess.com games and explore openings with fast per-move stats.

Code now lives under the package `chess_explorer/`; installable entry points replace the old root scripts.

## Features
- Import all chess.com archive months for a username into `games.json` (newest-first, deduped by `game_id`).
- Simple JSON schema: `{"version": 1, "games": [...]}` with moves, result, color, ratings, time control, opponent, date, termination, url.
- Programmatic filtering helpers (`filter_games.py`) to slice by color, result, opponent, time control, dates, ratings, and move ranges; build separate tries for white/black.
- Interactive terminal explorer (`explore_trie.py`) to browse next moves, step back/reset, and choose color-specific tries.
- Local PGN import: ingest your own PGN files into the same JSON schema.

## Requirements
- Python 3.10+
- Packages: `python-chess`, `requests`

## Quick Start
1) Create and activate a virtual env (optional but recommended):
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
2) Install package in editable mode (installs deps and entry points):
   ```bash
   pip install -e .
   ```
3) Import your games (fetches all archives, shows a monthly progress bar):
   ```bash
   chess-explore-import your_chesscom_username --player your_chesscom_username
   ```
   - By default stores data in `games/<player>.json`; `--output` overrides that.
   - Stores chess.com `time_class` when present and the raw `TimeControl` as `time_control_raw`.
   - Add `--quiet` to suppress progress and summary output.
    - To import local PGNs instead of chess.com archives:
       ```bash
       chess-explore-import-pgn your_username path/to/file_or_dir.pgn --player your_username
       ```
4) Explore filtered games interactively:
   ```bash
   chess-explore-explore --player your_chesscom_username --color white --time-control blitz --date-from 2025-11-30 --top 15
   ```
5) Show top positions with optional evals:
   ```bash
   chess-explore-top --player your_chesscom_username --plys 10 --limit 5 --skip-eval
   ```
   - Write structured output: `--output-json top.json` or `--output-csv top.csv`.
   - Eval caching: `--eval-cache .cache/lichess_eval.json --eval-cache-ttl 604800` (7 days default).
   - Filters: `--color white|black`, `--result 1-0|0-1|1/2-1/2`, `--opponent NAME`, `--time-control bullet|blitz|rapid|classical`, `--date-from YYYY-MM-DD`, `--date-to YYYY-MM-DD`, rating bounds, and `--moves-start/--moves-end` to slice move lists.
   - Controls: number = dive, `b` = back, `r` = reset, `q` = quit.

6) Optional: start the lightweight web UI (uses the same filters as `chess-explore-explore`):
   ```bash
   python serve_frontend.py --port 8000 --games-dir games
   ```
   Then open http://localhost:8000 to play moves on a board and see next-move stats. No top-position calls are used.

7) List available player stores:
   ```bash
   chess-explore-players --games-dir games
   ```

## Programmatic filtering
```python
from chess_explorer.filter_games import load_games, filter_games, build_color_tries

games = load_games()
subset = filter_games(games, color="white", time_control="blitz", date_from="2025-11-30", moves_end=20)
tries = build_color_tries(subset)
white_trie = tries["white"]
```

## Data Notes
- Time controls prefer chess.com `time_class` when present; otherwise derived from `TimeControl` using chess.com thresholds (daily if correspondence, bullet/blitz/rapid/classical by total time; 10+0 is rapid). Raw `TimeControl` is stored as `time_control_raw` for exact matching.
- Dates prefer PGN `EndDate` when present (fallback to `UTCDate`/`Date`).
- Imports run parallel per-month and dedupe by `game_id` before writing.
- Eval lookups cache Lichess cloud-eval responses per FEN on disk with a TTL to reduce network calls and allow reuse.

## Contributing
PRs welcome. Ideas: strict time-control matching (e.g., exact 10+0), local PGN import, tests for filters/parsing, richer stats output.

Run tests locally:
```bash
pip install -e .[dev]
pytest
```

## Layout
- `chess_explorer/` package with `import_games.py`, `filter_games.py`, `trie.py`, `explore_trie.py`, `top_positions.py`, and shared constants.
- Console scripts via `pip install -e .`: `chess-explore-import`, `chess-explore-explore`, `chess-explore-top`.
- Default data files live under `games/<player>.json`; legacy `games.json` is still supported for single-player setups.
- Examples: `examples/sample_games.json` is a tiny dataset used by tests and CLI demos.

## License
MIT. See [LICENSE](LICENSE).

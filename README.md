# Open-Source Chess Explorer

Command-line helpers to import all your chess.com games and explore openings with fast per-move stats.

## Features
- Import all chess.com archive months for a username into `games.json` (newest-first, deduped by `game_id`).
- Simple JSON schema: `{"version": 1, "games": [...]}` with moves, result, color, ratings, time control, opponent, date, termination, url.
- Programmatic filtering helpers (`filterGames.py`) to slice by color, result, opponent, time control, dates, ratings, and move ranges; build separate tries for white/black.
- Interactive terminal explorer (`exploreTrie.py`) to browse next moves, step back/reset, and choose color-specific tries.

## Requirements
- Python 3.10+
- Packages: `python-chess`, `requests`

## Quick Start
1) Create and activate a virtual env (optional but recommended):
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
2) Install deps:
   ```bash
   pip install python-chess requests
   ```
3) Import your games (fetches all archives, shows a monthly progress bar):
   ```bash
   python importGames.py your_chesscom_username --output games.json
   ```
   - `--output` lets you write to a custom file; defaults to `games.json`.
   - Stores chess.com `time_class` when present and the raw `TimeControl` as `time_control_raw`.
4) Explore filtered games interactively:
   ```bash
   python exploreTrie.py --color white --time-control blitz --date-from 2025-11-30 --top 15
   ```
   - Filters: `--color white|black`, `--result 1-0|0-1|1/2-1/2`, `--opponent NAME`, `--time-control bullet|blitz|rapid|classical`, `--date-from YYYY-MM-DD`, `--date-to YYYY-MM-DD`, rating bounds, and `--moves-start/--moves-end` to slice move lists.
   - Controls: number = dive, `b` = back, `r` = reset, `q` = quit.

## Programmatic filtering
```python
from filterGames import load_games, filter_games, build_color_tries

games = load_games()
subset = filter_games(games, color="white", time_control="blitz", date_from="2025-11-30", moves_end=20)
tries = build_color_tries(subset)
white_trie = tries["white"]
```

## Data Notes
- Time controls prefer chess.com `time_class` when present; otherwise derived from `TimeControl` using chess.com thresholds (daily if correspondence, bullet/blitz/rapid/classical by total time; 10+0 is rapid). Raw `TimeControl` is stored as `time_control_raw` for exact matching.
- Dates prefer PGN `EndDate` when present (fallback to `UTCDate`/`Date`).
- Imports run parallel per-month and dedupe by `game_id` before writing.

## Contributing
PRs welcome. Ideas: strict time-control matching (e.g., exact 10+0), local PGN import, tests for filters/parsing, richer stats output.

## License
MIT. See [LICENSE](LICENSE).

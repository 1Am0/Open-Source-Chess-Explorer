# Open-Source Chess Explorer

Command-line helper for exploring your chess.com games with fast per-move stats and on-demand Lichess cloud evals.

## Features
- Pulls your recent chess.com games and builds color-aware opening trees.
- Displays top continuations with win/draw/loss bars and cached cloud evals.
- Interactive REPL: walk lines, undo/reset, swap perspective, and validate move input.
- Eval cache persisted to `eval_cache.json` to avoid repeated API calls.

## Requirements
- Python 3.10+
- Packages: `python-chess`, `requests`, `rich` (see `requirements.txt` note below)

## Quick Start
1) Create and activate a virtual env (optional but recommended):
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
2) Install deps:
   ```bash
   pip install python-chess requests rich
   ```
3) Run:
   ```bash
   python Test.py
   ```
4) Enter your chess.com username when prompted.

## REPL Commands
- Enter legal SAN moves to extend the line (invalid inputs are rejected in red).
- `back` – undo last move
- `reset` – return to starting position
- `white` / `black` – switch perspective
- `exit` – quit

## Data Sources & Limits
- Games fetched from chess.com public archives.
- Evals retrieved from Lichess cloud eval; expect occasional HTTP 429 rate limits.
- Eval cache stored in `eval_cache.json` (ignored by git by default).

## Notes
- Only SAN input is accepted today. UCI/auto-complete could be added later.
- If your line becomes invalid (e.g., typo earlier), reset or step back.

## Contributing
PRs welcome. Ideas: configurable game count, local PGN import, better theming, tests for parsers/formatters, and a help menu.

## License
MIT. See [LICENSE](LICENSE).

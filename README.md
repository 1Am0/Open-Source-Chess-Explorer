# Open-Source Chess Explorer

A fast chess opening explorer with a modern web UI and command-line tools to import and analyze all your chess.com games.

Code lives under the package `chess_explorer/` with installable CLI entry points and a lightweight web frontend.

## Features
- 🌐 **Modern Web UI** - Interactive board with drag-and-drop moves, real-time statistics, and advanced filtering
- � **Opening Recognition** - Automatic opening detection with ECO codes from comprehensive Lichess database (3,800+ openings)
- 📥 **Chess.com & Lichess Import** - Fetch all your games from both platforms with parallel processing and progress tracking
- 🎯 **Multi-Player Support** - Select and merge games from multiple players with quick-access toolbar
- ⚡ **Performance Optimized** - Parallel parsing, orjson support, smart caching, and debounced navigation for instant responses
- 🔍 **Advanced Filters** - Color, result, opponent, time control, rating ranges, date ranges
- 📊 **Move Statistics** - Win/draw/loss breakdown per move with visual percentage bars
- 🎮 **Interactive Terminal** - Browse openings in your terminal with keyboard navigation
- 📝 **Local PGN Import** - Import your own PGN files into the same JSON schema

## Requirements
- Python 3.10+
- Core packages: `python-chess`, `requests`, `tqdm`
- Optional for 2-3x faster performance: `orjson`

## Quick Start

### 💻 Windows Executable (Easiest!)

**For non-technical users on Windows:**
1. Download the latest `ChessExplorer.zip` from [Releases](https://github.com/yourusername/Open-Source-Chess-Explorer/releases)
2. Extract the zip file
3. Double-click `ChessExplorer.exe`
4. Your browser opens automatically - start importing games!

No Python installation required! See `README.txt` in the download for detailed instructions.

### Web UI (For Developers)
1) Create and activate a virtual env:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # Linux/Mac
   ```

2) Install package with optional performance boost:
   ```bash
   pip install -e .
   pip install -e .[perf]  # Optional: adds orjson for 2-3x faster performance
   ```

3) Import your chess.com games:
   ```bash
   chess-explore-import your_username --player your_username
   ```
   - Parallel processing with progress bars
   - Stores in `games/<player>.json`
   - Use `--output` to override location

4) Start the web server:
   ```bash
   python serve_frontend.py --port 8000 --games-dir games
   ```
   Open http://localhost:8000 in your browser!
   
   The UI automatically loads the comprehensive Lichess opening database (3,800+ openings) and displays:
   - Current opening name and ECO code as you play/navigate moves
   - Player selector in the main toolbar for quick switching
   - Advanced filter panel with all criteria
   - Visual statistics with color-coded win/draw/loss bars

**Web UI Features:**
- **Opening Recognition** - Automatic opening detection with names and ECO codes from comprehensive Lichess database (3,800+ openings)
- **Interactive Board** - Drag and drop pieces on a responsive chessboard
- **Smart Navigation** - Click moves to jump to positions, debounced loading for smooth rapid navigation
- **Player Selection** - Quick-access player selector with refresh button in main toolbar
- **Advanced Filters** - Filter by player, color, result, time control, opponent rating, date ranges
- **Visual Statistics** - Real-time win/draw/loss percentage bars for each candidate move
- **Keyboard Shortcuts** - Arrow keys for navigation, F to flip board, Escape to close overlays
- **Move History** - Numbered move notation with current position highlighting
- **Board Controls** - Flip board view, jump to start/end, step through moves
- **Performance Optimized** - Smart caching for instant loads, debounced API calls during rapid navigation

### Command Line Tools

Import games from Chess.com (fetches all archives, shows progress):
   ```bash
   chess-explore-import your_chesscom_username --player your_chesscom_username
   ```
   - By default stores data in `games/<player>.json`; `--output` overrides that.
   - Stores chess.com `time_class` when present and the raw `TimeControl` as `time_control_raw`.
   - Add `--quiet` to suppress progress and summary output.

Import games from Lichess:
   ```bash
   chess-explore-import-lichess your_lichess_username --player your_username
   ```
   - Streams games directly from Lichess API with automatic duplicate detection
   - Optional filters: `--max 100`, `--rated`, `--perf-type blitz`
   - Stores in `games/lichess/<player>.json` by default

To import local PGN files:
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

6) List available player stores:
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

## Performance

**orjson (Recommended):**
Installing orjson provides 2-3x faster JSON parsing and serialization:
```bash
pip install -e .[perf]  # or: pip install orjson
```
The application automatically detects and uses it when available.

**Caching:**
- Trie structures are cached per player and filter combination
- Subsequent loads are near-instant (<50ms)
- Cache invalidates automatically on new imports

**Parallel Processing:**
- Import: Fetches archives and parses PGN files using multiple threads
- ~7,000 games import in under 10 seconds with orjson

## Data Notes
- Time controls prefer chess.com `time_class` when present; otherwise derived from `TimeControl` using chess.com thresholds (daily if correspondence, bullet/blitz/rapid/classical by total time; 10+0 is rapid). Raw `TimeControl` is stored as `time_control_raw` for exact matching.
- Dates prefer PGN `EndDate` when present (fallback to `UTCDate`/`Date`).
- Imports run parallel per-month and per-game with deduplication by `game_id` before writing.
- Eval lookups cache Lichess cloud-eval responses per FEN on disk with a TTL to reduce network calls and allow reuse.

## Building Windows Executable

To create a standalone Windows executable:

```bash
pip install pyinstaller
build_exe.bat
```

This creates `dist/ChessExplorer_Release/ChessExplorer.exe` with all dependencies bundled. Users can double-click to launch - no Python required!

The executable:
- Auto-opens browser to http://localhost:8000
- Includes comprehensive opening recognition (3,800+ openings with ECO codes)
- Includes all frontend files and Python dependencies
- Stores games in `games/` folder next to the .exe
- ~30-40 MB download size (zipped)

## Project Structure
```
├── chess_explorer/        # Python package
│   ├── import_games.py   # Chess.com API import with parallel processing
│   ├── filter_games.py   # Game filtering and trie building
│   ├── trie.py           # Move tree data structure
│   ├── explore_trie.py   # Terminal UI explorer
│   ├── top_positions.py  # Position analysis
│   └── storage.py        # JSON persistence with orjson support
├── frontend/             # Web UI (vanilla JS + chessboard.js)
│   ├── index.html       # Main UI with player selector and filters
│   ├── app.js           # Opening recognition, navigation, and API logic
│   └── styles.css       # Modern dark theme with visual statistics
├── serve_frontend.py     # Development web server
├── games/                # Player data (.json files)
├── examples/             # Sample datasets
└── tests/                # Test suite
```

**Console scripts** (via `pip install -e .`):
- `chess-explore-import` - Import games from Chess.com
- `chess-explore-import-lichess` - Import games from Lichess
- `chess-explore-import-pgn` - Import local PGN files
- `chess-explore-explore` - Interactive terminal explorer
- `chess-explore-top` - Analyze top positions
- `chess-explore-players` - List available players

**Data storage:**
- Default: `games/<player>.json` (one file per player)
- Legacy: `games.json` (single file, still supported)
- Format: `{"version": 1, "games": [...]}`
Testing

**Run tests:**
```bash
pip install -e .[dev]
pytest
```

Test coverage includes:
- CLI smoke tests for all import and explore commands
- PGN import validation and error handling
- Lichess API import with mocked streaming responses
- Filter and trie building logic
- Duplicate detection and game mergingest
```

**Benchmark trie building performance:**
```bash
python benchmark_trie.py your_username
```
Shows detailed breakdown of JSON parsing vs trie construction time.

**Contributing:**
PRs welcome! Ideas: advanced time-control matching, additional frontend features, expanded test coverage, richer statistics.

## License
MIT. See [LICENSE](LICENSE).

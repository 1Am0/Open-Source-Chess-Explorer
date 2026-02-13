from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

try:
    import orjson
    HAS_ORJSON = True
except ImportError:
    HAS_ORJSON = False

from .constants import DEFAULT_GAMES_FILE, GAMES_DIR, SCHEMA_VERSION


def ensure_games_dir(games_dir: Path = GAMES_DIR) -> None:
    games_dir.mkdir(parents=True, exist_ok=True)


def _sanitize_player_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        return "default"
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in cleaned)


def path_for_player(player: Optional[str], games_dir: Path = GAMES_DIR) -> Path:
    ensure_games_dir(games_dir)
    if not player:
        return DEFAULT_GAMES_FILE
    return games_dir / f"{_sanitize_player_name(player)}.json"


def resolve_store_path(player: Optional[str] = None, output: Optional[Path | str] = None) -> Path:
    if output:
        return Path(output)
    return path_for_player(player)


def load_store(path: Path) -> Dict:
    if not path.exists():
        return {"version": SCHEMA_VERSION, "games": []}
    
    if HAS_ORJSON:
        data = orjson.loads(path.read_bytes())
    else:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    
    if "version" not in data:
        data["version"] = SCHEMA_VERSION
    if "games" not in data:
        data["games"] = []
    return data


def save_store(store: Dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    
    if HAS_ORJSON:
        # orjson doesn't support indent parameter, but it's much faster
        # Write without indentation for speed (2-3x faster than json.dumps)
        path.write_bytes(orjson.dumps(store))
    else:
        path.write_text(json.dumps(store, indent=4), encoding="utf-8")


def load_games(path: Path) -> List[Dict]:
    store = load_store(path)
    return store.get("games", [])


def list_players(games_dir: Path = GAMES_DIR) -> List[str]:
    if not games_dir.exists():
        return []
    return sorted(p.stem for p in games_dir.glob("*.json") if p.is_file())

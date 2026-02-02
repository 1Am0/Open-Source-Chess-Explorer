from pathlib import Path
import json
import pytest


@pytest.fixture(scope="session")
def sample_games_path() -> Path:
    return Path(__file__).parent.parent / "examples" / "sample_games.json"


@pytest.fixture()
def sample_games(sample_games_path: Path):
    with sample_games_path.open("r", encoding="utf-8") as f:
        return json.load(f)["games"]


@pytest.fixture(scope="session")
def sample_pgn_path() -> Path:
    return Path(__file__).parent / "fixtures" / "sample.pgn"

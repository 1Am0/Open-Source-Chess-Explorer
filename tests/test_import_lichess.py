"""Tests for import_lichess module"""
import json
from pathlib import Path
from unittest.mock import Mock, patch
import io

import pytest
import requests

from chess_explorer import import_lichess


# Sample PGN data that simulates Lichess API response
SAMPLE_LICHESS_PGN = """[Event "Rated Blitz game"]
[Site "https://lichess.org/abc123"]
[Date "2025.12.10"]
[White "testuser"]
[Black "opponent1"]
[Result "1-0"]
[WhiteElo "1500"]
[BlackElo "1480"]
[TimeControl "300+0"]
[Termination "Normal"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 1-0

[Event "Rated Blitz game"]
[Site "https://lichess.org/def456"]
[Date "2025.12.11"]
[White "opponent2"]
[Black "testuser"]
[Result "0-1"]
[WhiteElo "1520"]
[BlackElo "1505"]
[TimeControl "300+0"]
[Termination "Normal"]

1. d4 d5 2. c4 e6 3. Nc3 Nf6 4. Bg5 Be7 0-1

[Event "Rated Rapid game"]
[Site "https://lichess.org/ghi789"]
[Date "2025.12.12"]
[White "testuser"]
[Black "opponent3"]
[Result "1/2-1/2"]
[WhiteElo "1510"]
[BlackElo "1515"]
[TimeControl "600+0"]
[Termination "Normal"]

1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 1/2-1/2

"""


@pytest.fixture
def mock_lichess_response():
    """Create a mock response object that simulates Lichess API streaming."""
    mock_response = Mock(spec=requests.Response)
    mock_response.status_code = 200
    mock_response.raise_for_status = Mock()
    
    # Create a mock raw object with read method
    pgn_bytes = SAMPLE_LICHESS_PGN.encode('utf-8')
    mock_response.raw = io.BytesIO(pgn_bytes)
    
    return mock_response


def test_fetch_lichess_games_basic(mock_lichess_response):
    """Test basic fetching of games from Lichess."""
    with patch('requests.Session') as mock_session_class:
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_session.get.return_value = mock_lichess_response
        mock_session.headers = Mock()
        
        games = list(import_lichess.fetch_lichess_games("testuser", show_progress=False))
        
        # Should fetch 3 games from the sample PGN
        assert len(games) == 3
        
        # Verify API was called correctly
        mock_session.get.assert_called_once()
        call_args = mock_session.get.call_args
        assert "lichess.org/api/games/user/testuser" in call_args[0][0]
        
        # Check that returned strings contain PGN data
        assert all(isinstance(g, str) for g in games)
        assert any("testuser" in g for g in games)


def test_fetch_lichess_games_with_filters(mock_lichess_response):
    """Test fetching games with various filters."""
    with patch('requests.Session') as mock_session_class:
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_session.get.return_value = mock_lichess_response
        mock_session.headers = Mock()
        
        list(import_lichess.fetch_lichess_games(
            "testuser",
            max_games=10,
            rated=True,
            perf_type="blitz",
            show_progress=False
        ))
        
        # Check that params were passed correctly
        call_args = mock_session.get.call_args
        params = call_args[1]['params']
        assert params['max'] == '10'
        assert params['rated'] == 'true'
        assert params['perfType'] == 'blitz'


def test_fetch_lichess_games_network_error():
    """Test handling of network errors during fetch."""
    with patch('requests.Session') as mock_session_class:
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_session.headers = Mock()
        mock_session.get.side_effect = requests.exceptions.RequestException("Network error")
        
        games = list(import_lichess.fetch_lichess_games("testuser", show_progress=False))
        
        # Should return empty list on error
        assert games == []


def test_fetch_lichess_games_http_error():
    """Test handling of HTTP errors (e.g., 404 for non-existent user)."""
    with patch('requests.Session') as mock_session_class:
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_session.headers = Mock()
        
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_session.get.return_value = mock_response
        
        games = list(import_lichess.fetch_lichess_games("nonexistentuser", show_progress=False))
        
        # Should return empty list on HTTP error
        assert games == []


def test_import_lichess_games(tmp_path: Path, mock_lichess_response):
    """Test importing Lichess games to a JSON file."""
    out_path = tmp_path / "testuser_lichess.json"
    
    with patch('requests.Session') as mock_session_class:
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_session.get.return_value = mock_lichess_response
        mock_session.headers = Mock()
        
        import_lichess.import_lichess_games(
            "testuser",
            player="testuser",
            out_path=out_path,
            quiet=True
        )
        
        # Check that file was created
        assert out_path.exists()
        
        # Load and verify the data
        data = json.loads(out_path.read_text(encoding="utf-8"))
        games = data["games"]
        
        # Should have imported 3 games
        assert len(games) == 3
        
        # Verify game IDs are present
        game_ids = {g.get("game_id") for g in games}
        assert "abc123" in game_ids
        assert "def456" in game_ids
        assert "ghi789" in game_ids
        
        # Verify color assignment
        colors = {g["game_id"]: g["color"] for g in games}
        assert colors["abc123"] == "white"  # testuser was white
        assert colors["def456"] == "black"  # testuser was black


def test_import_lichess_games_duplicates(tmp_path: Path, mock_lichess_response):
    """Test that duplicate games are not imported twice."""
    out_path = tmp_path / "testuser_lichess.json"
    
    with patch('requests.Session') as mock_session_class:
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_session.get.return_value = mock_lichess_response
        mock_session.headers = Mock()
        
        # Import once
        import_lichess.import_lichess_games(
            "testuser",
            player="testuser",
            out_path=out_path,
            quiet=True
        )
        
        first_data = json.loads(out_path.read_text(encoding="utf-8"))
        first_count = len(first_data["games"])
        assert first_count == 3
        
        # Create a new mock response for the second import
        mock_response2 = Mock(spec=requests.Response)
        mock_response2.status_code = 200
        mock_response2.raise_for_status = Mock()
        pgn_bytes = SAMPLE_LICHESS_PGN.encode('utf-8')
        mock_response2.raw = io.BytesIO(pgn_bytes)
        mock_session.get.return_value = mock_response2
        
        # Import again (should skip duplicates)
        import_lichess.import_lichess_games(
            "testuser",
            player="testuser",
            out_path=out_path,
            quiet=True
        )
        
        second_data = json.loads(out_path.read_text(encoding="utf-8"))
        second_count = len(second_data["games"])
        
        # Count should remain the same (duplicates skipped)
        assert second_count == first_count


def test_import_lichess_games_max_games(tmp_path: Path):
    """Test that max_games parameter limits the number of games fetched."""
    out_path = tmp_path / "testuser_lichess.json"
    
    # Create a mock response with only one game
    single_game_pgn = """[Event "Rated Blitz game"]
[Site "https://lichess.org/abc123"]
[Date "2025.12.10"]
[White "testuser"]
[Black "opponent1"]
[Result "1-0"]
[WhiteElo "1500"]
[BlackElo "1480"]
[TimeControl "300+0"]
[Termination "Normal"]

1. e4 e5 2. Nf3 Nc6 1-0

"""
    
    with patch('requests.Session') as mock_session_class:
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_session.headers = Mock()
        
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_response.raw = io.BytesIO(single_game_pgn.encode('utf-8'))
        mock_session.get.return_value = mock_response
        
        import_lichess.import_lichess_games(
            "testuser",
            player="testuser",
            out_path=out_path,
            max_games=1,
            quiet=True
        )
        
        # Verify max parameter was passed
        call_args = mock_session.get.call_args
        params = call_args[1]['params']
        assert params['max'] == '1'
        
        # Verify only 1 game was imported
        data = json.loads(out_path.read_text(encoding="utf-8"))
        assert len(data["games"]) == 1


def test_import_lichess_games_empty_response(tmp_path: Path):
    """Test handling of empty response (user has no games)."""
    out_path = tmp_path / "empty_user.json"
    
    with patch('requests.Session') as mock_session_class:
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_session.headers = Mock()
        
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_response.raw = io.BytesIO(b"")  # Empty response
        mock_session.get.return_value = mock_response
        
        import_lichess.import_lichess_games(
            "emptyuser",
            player="emptyuser",
            out_path=out_path,
            quiet=True
        )
        
        # File should not be created when there are no games
        assert not out_path.exists()


def test_import_lichess_games_sorting(tmp_path: Path, mock_lichess_response):
    """Test that games are sorted by date in descending order."""
    out_path = tmp_path / "testuser_lichess.json"
    
    with patch('requests.Session') as mock_session_class:
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_session.get.return_value = mock_lichess_response
        mock_session.headers = Mock()
        
        import_lichess.import_lichess_games(
            "testuser",
            player="testuser",
            out_path=out_path,
            quiet=True
        )
        
        data = json.loads(out_path.read_text(encoding="utf-8"))
        games = data["games"]
        dates = [g.get("date") for g in games]
        
        # Dates should be in descending order (most recent first)
        assert dates == sorted(dates, reverse=True)


def test_import_cli_without_username(monkeypatch):
    """Test CLI prompts for username when not provided."""
    import sys
    
    with patch('requests.Session') as mock_session_class, \
         patch('builtins.input', return_value='testuser'):
        
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_session.headers = Mock()
        
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_response.raw = io.BytesIO(b"")
        mock_session.get.return_value = mock_response
        
        monkeypatch.setattr(sys, "argv", ["import_lichess.py", "--quiet"])
        
        import_lichess.main()
        
        # Should have called the API with the input username
        mock_session.get.assert_called_once()
        call_args = mock_session.get.call_args
        assert "testuser" in call_args[0][0]

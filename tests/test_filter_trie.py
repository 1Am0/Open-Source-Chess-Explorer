from chess_explorer.filter_games import filter_games, build_trie_from_games, build_color_tries
from chess_explorer.import_games import time_control_label


def test_time_control_label_buckets():
    assert time_control_label("60+0") == "bullet"
    assert time_control_label("600+0") == "rapid"
    assert time_control_label("1/86400") == "daily"
    assert time_control_label("180+10") == "blitz"


def test_filter_by_color(sample_games):
    white_only = filter_games(sample_games, color="white")
    assert all(g["color"] == "white" for g in white_only)
    assert len(white_only) == 2


def test_moves_slicing(sample_games):
    sliced = filter_games(sample_games, moves_start=2, moves_end=4)
    for g in sliced:
        assert len(g["moves"]) == 2


def test_trie_counts(sample_games):
    trie = build_trie_from_games(sample_games)
    stats_root = trie.root.stats()
    assert stats_root["total"] == 3
    nxt = trie.next_moves([])
    assert "e4" in nxt and "d4" in nxt and "Nf3" in nxt


def test_color_tries(sample_games):
    tries = build_color_tries(sample_games)
    assert tries["white"].root.stats()["total"] == 2
    assert tries["black"].root.stats()["total"] == 1

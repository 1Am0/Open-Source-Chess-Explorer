from typing import Dict, Iterable, Optional


class TrieNode:
    """A node in the move trie with aggregated results."""

    def __init__(self, val: Optional[str] = None) -> None:
        self.val = val
        self.children: Dict[str, TrieNode] = {}
        self.totalWins = 0
        self.totalLosses = 0
        self.totalDraws = 0

    def _increment_result(self, result: str) -> None:
        token = result.strip().lower()
        if token in {"1-0", "w", "white", "win", "wins"}:
            self.totalWins += 1
        elif token in {"0-1", "b", "black", "loss", "lose", "loses"}:
            self.totalLosses += 1
        elif token in {"1/2-1/2", "draw", "d", "=", "½"}:
            self.totalDraws += 1
        else:
            raise ValueError(f"Unknown result token: {result}")

    def stats(self) -> Dict[str, float]:
        total = self.totalWins + self.totalLosses + self.totalDraws
        if total == 0:
            return {
                "wins": 0,
                "losses": 0,
                "draws": 0,
                "total": 0,
                "winRate": 0.0,
                "drawRate": 0.0,
                "lossRate": 0.0,
            }
        return {
            "wins": self.totalWins,
            "losses": self.totalLosses,
            "draws": self.totalDraws,
            "total": total,
            "winRate": self.totalWins / total,
            "drawRate": self.totalDraws / total,
            "lossRate": self.totalLosses / total,
        }

    def next_moves(self) -> Dict[str, Dict[str, float]]:
        return {move: child.stats() for move, child in self.children.items()}

    def is_leaf(self) -> bool:
        return len(self.children) == 0

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"TrieNode(val={self.val!r}, wins={self.totalWins}, "
            f"losses={self.totalLosses}, draws={self.totalDraws}, "
            f"children={list(self.children)})"
        )

    def __str__(self) -> str:
        return (
            f"{self.val or 'ROOT'}: W {self.totalWins}, D {self.totalDraws}, "
            f"L {self.totalLosses}, children {list(self.children)}"
        )


class Trie:
    """Container for move trie operations."""

    def __init__(self) -> None:
        self.root = TrieNode()

    def add_game(self, moves: Iterable[str], result: str) -> None:
        node = self.root
        node._increment_result(result)
        for move in moves:
            node = node.children.setdefault(move, TrieNode(move))
            node._increment_result(result)

    def find(self, moves: Iterable[str]) -> Optional[TrieNode]:
        node: Optional[TrieNode] = self.root
        for move in moves:
            if node is None:
                return None
            node = node.children.get(move)
        return node

    def stats(self, moves: Iterable[str]) -> Dict[str, float]:
        node = self.find(moves)
        return node.stats() if node else {
            "wins": 0,
            "losses": 0,
            "draws": 0,
            "total": 0,
            "winRate": 0.0,
            "drawRate": 0.0,
            "lossRate": 0.0,
        }

    def next_moves(self, moves: Iterable[str]) -> Dict[str, Dict[str, float]]:
        node = self.find(moves)
        return node.next_moves() if node else {}

    
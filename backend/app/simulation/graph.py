from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Iterable


class ConductiveGraph:
    def __init__(self, edges: Iterable[tuple[str, str]] = ()):
        self._adjacency: dict[str, set[str]] = defaultdict(set)
        for left, right in edges:
            self.add(left, right)

    def add(self, left: str, right: str) -> None:
        self._adjacency[left].add(right)
        self._adjacency[right].add(left)

    def reachable(self, start: str) -> set[str]:
        visited: set[str] = set()
        pending = deque([start])
        while pending:
            node = pending.popleft()
            if node in visited:
                continue
            visited.add(node)
            pending.extend(self._adjacency.get(node, ()) - visited)
        return visited

    def connected(self, left: str, right: str) -> bool:
        return right in self.reachable(left)

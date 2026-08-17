from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Literal


TerminalRole = Literal["functional", "free_junction", "external"]


class UnionFind:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, value: str) -> str:
        self.parent.setdefault(value, value)
        if self.parent[value] != value:
            self.parent[value] = self.find(self.parent[value])
        return self.parent[value]

    def union(self, left: str, right: str) -> None:
        left_root, right_root = self.find(left), self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root


@dataclass(frozen=True)
class NetworkComponent:
    terminals: frozenset[str]
    signature: frozenset[str]
    edge_count: int

    @property
    def has_loop(self) -> bool:
        return self.edge_count >= len(self.terminals)


@dataclass
class NetworkComparison:
    correct_net_ids: list[str] = field(default_factory=list)
    missing_net_ids: list[str] = field(default_factory=list)
    merged_component_count: int = 0
    extra_component_count: int = 0
    isolated_junction_count: int = 0
    loop_count: int = 0

    @property
    def electrically_equivalent(self) -> bool:
        return not self.missing_net_ids and not self.merged_component_count and not self.extra_component_count


def build_network_components(
    edges: Iterable[tuple[str, str]], roles: dict[str, TerminalRole]
) -> list[NetworkComponent]:
    edge_list = [tuple(sorted(edge)) for edge in edges]
    union = UnionFind()
    for left, right in edge_list:
        union.union(left, right)
    grouped_nodes: dict[str, set[str]] = {}
    grouped_edges: dict[str, int] = {}
    for terminal in union.parent:
        grouped_nodes.setdefault(union.find(terminal), set()).add(terminal)
    for left, _ in edge_list:
        root = union.find(left)
        grouped_edges[root] = grouped_edges.get(root, 0) + 1
    return [
        NetworkComponent(
            terminals=frozenset(terminals),
            signature=frozenset(
                terminal for terminal in terminals if roles.get(terminal, "functional") != "free_junction"
            ),
            edge_count=grouped_edges.get(root, 0),
        )
        for root, terminals in grouped_nodes.items()
    ]


def compare_networks(
    components: list[NetworkComponent], expected_nets: dict[str, frozenset[str]]
) -> NetworkComparison:
    comparison = NetworkComparison(loop_count=sum(component.has_loop for component in components))
    unmatched_components = list(components)

    for net_id, expected_signature in expected_nets.items():
        matched = next((item for item in unmatched_components if item.signature == expected_signature), None)
        if matched is None:
            comparison.missing_net_ids.append(net_id)
        else:
            comparison.correct_net_ids.append(net_id)
            unmatched_components.remove(matched)

    expected_signatures = list(expected_nets.values())
    for component in unmatched_components:
        if not component.signature:
            comparison.isolated_junction_count += 1
        else:
            touched = [expected for expected in expected_signatures if expected & component.signature]
            if len(touched) >= 2 or any(expected < component.signature for expected in touched):
                comparison.merged_component_count += 1
            else:
                comparison.extra_component_count += 1
    return comparison

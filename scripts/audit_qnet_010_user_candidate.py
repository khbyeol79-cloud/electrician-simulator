from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.domain import WiringConnection  # noqa: E402
from app.domain.answer_definition import AnswerDefinition  # noqa: E402
from app.services.wiring_network_service import expected_net_candidates  # noqa: E402


PROBLEM_ID = "qnet_electrician_practical_010"
PACKAGE = ROOT / "problems" / PROBLEM_ID

RAW_USER_CANDIDATE = """L1>MCCB-L1
L2>MCCB-L2
L3>MCCB-L3
MCCB-T1>EOCR-1(L1)
MCCB-T2>EOCR-2(L2)
MCCB-T3>EOCR-3(L3)
EOCR-7(U)>MC1-1
EOCR-8(V)>MC1-2
EOCR-9(W)>MC1-3
MC1-7>M1-U
MC1-8>M1-V
MC1-9>M1-W
EOCR-7(U)>MC2-1
EOCR-8(V)>MC2-2
EOCR-9(W)>MC2-3
MC2-7>M2-U
MC2-8>M2-V
MC2-9>M2-W
MCCB-T1>F1
MCCB-T3>F3
F2>EOCR-4
F4>EOCR-12
EOCR-10>PB0-1
PB0-2>PB1-1
PB1-1>X1-1
PB1-2>X1-3
X1-3>X1-2
X1-2>LS1-1
LS1-1>T1-6
LS1-2>T1-2
T1-8>MC1-6
X1-1>PB2-1
PB2-1>X2-1
PB22-2>X2-3
X2-3>X2-2
X2-2>LS2-1
LS2-1>T2-6
LS2-2>T2-2
T2-8>MC2-6
X2-1>X1-6
X1-6>X2-6
X1-8>MC1-5
X2-8>MC2-5
MC1-11>MC2-11
MC2-11>WL-1
X2-6>MC1-4
MC1-10>RL-1
MC1-4>MC2-4
MC2-10>GL-1
F2>EOCR-6
EOCR-6>EOCR-5
EOCR-11>YL
GL-2>RL-2
RL-2>WL-2
WL-2>MC2-12
MC2-12>T2-7
T2-7>X2-7
X2-7>MC1-12
MC1-12>T1-7
T1-7>X1-7
X1-7>YL-2
YL-2>EOCR-12"""

EOCR_PIN_ALIASES = {
    "1": "EOCR-L1", "2": "EOCR-L2", "3": "EOCR-L3",
    "4": "EOCR-96", "5": "EOCR-98", "6": "EOCR-A1",
    "7": "EOCR-U", "8": "EOCR-V", "9": "EOCR-W",
    "10": "EOCR-95", "11": "EOCR-97", "12": "EOCR-A2",
}

# The candidate reverses the two used ends of these dry contacts. This map is
# only an audit projection; it does not loosen production grading semantics.
CONTACT_ORIENTATION_PAIRS = (
    ("EOCR-95", "EOCR-96"), ("EOCR-97", "EOCR-98"),
    ("X1-8", "X1-6"), ("X2-8", "X2-6"),
    ("T1-8", "T1-6"), ("T2-8", "T2-6"),
)
CONTACT_ORIENTATION_MAP = {
    terminal: opposite
    for left, right in CONTACT_ORIENTATION_PAIRS
    for terminal, opposite in ((left, right), (right, left))
}


@dataclass(frozen=True)
class CandidateConnection:
    raw: str
    left: str
    right: str
    corrections: tuple[str, ...]

    @property
    def key(self) -> tuple[str, str]:
        return tuple(sorted((self.left, self.right)))


def normalize_terminal(value: str) -> tuple[str, list[str]]:
    original = value.strip()
    normalized = original
    corrections: list[str] = []
    if normalized == "PB22-2":
        normalized = "PB2-2"
        corrections.append("PB22-2 오타를 PB2-2로 정규화")
    if normalized == "YL":
        normalized = "YL-1"
        corrections.append("YL 단자 누락을 YL-1 후보로 정규화")
    if normalized in {"L1", "L2", "L3"}:
        normalized = f"PWR-{normalized}"
        corrections.append(f"외부 전원 {original}을 {normalized}로 정규화")
    fuse_match = re.fullmatch(r"F([1-4])", normalized)
    if fuse_match:
        normalized = f"F-{fuse_match.group(1)}"
        corrections.append(f"단일 F 기구 명칭 {original}을 {normalized}로 정규화")
    eocr_match = re.fullmatch(r"EOCR-(\d+)(?:\([^)]*\))?", normalized)
    if eocr_match and eocr_match.group(1) in EOCR_PIN_ALIASES:
        mapped = EOCR_PIN_ALIASES[eocr_match.group(1)]
        if mapped != normalized:
            corrections.append(f"EOCR 12P 핀 {original}을 {mapped}로 정규화")
        normalized = mapped
    return normalized, corrections


def normalize_candidate(raw_text: str = RAW_USER_CANDIDATE) -> list[CandidateConnection]:
    result: list[CandidateConnection] = []
    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.count(">") != 1:
            raise ValueError(f"후보 결선 형식 오류: {line}")
        raw_left, raw_right = line.split(">")
        left, left_corrections = normalize_terminal(raw_left)
        right, right_corrections = normalize_terminal(raw_right)
        result.append(CandidateConnection(line, left, right, tuple(left_corrections + right_corrections)))
    return result


def candidate_wiring_connections(raw_text: str = RAW_USER_CANDIDATE) -> list[WiringConnection]:
    return [
        WiringConnection(**{"from": item.left, "to": item.right, "wire_color": "yellow"})
        for item in normalize_candidate(raw_text)
    ]


def build_components(connections: list[CandidateConnection], *, project_contact_orientation: bool = False) -> set[frozenset[str]]:
    parent: dict[str, str] = {}

    def projected(terminal: str) -> str:
        return CONTACT_ORIENTATION_MAP.get(terminal, terminal) if project_contact_orientation else terminal

    def find(value: str) -> str:
        parent.setdefault(value, value)
        if parent[value] != value:
            parent[value] = find(parent[value])
        return parent[value]

    def union(left: str, right: str) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    for item in connections:
        union(projected(item.left), projected(item.right))
    grouped: dict[str, set[str]] = {}
    for terminal in parent:
        grouped.setdefault(find(terminal), set()).add(terminal)
    return {frozenset(group) for group in grouped.values()}


def audit_candidate() -> dict[str, object]:
    candidate = normalize_candidate()
    answer = json.loads((PACKAGE / "answer.json").read_text(encoding="utf-8"))
    problem = json.loads((PACKAGE / "problem.json").read_text(encoding="utf-8"))
    definition = AnswerDefinition.model_validate(answer)
    expected = {item.net_id: frozenset(item.terminals) for item in definition.expected_nets}
    expected_candidates = expected_net_candidates(expected, definition.allowed_alternatives)
    actual_components = build_components(candidate)
    projected_components = build_components(candidate, project_contact_orientation=True)
    exact_matches, exact_alternatives = max(
        ((sorted(net_id for net_id, terminals in item.items() if terminals in actual_components), alternatives) for item, alternatives in expected_candidates),
        key=lambda result: len(result[0]),
    )
    projected_matches, projected_alternatives = max(
        ((sorted(net_id for net_id, terminals in item.items() if terminals in projected_components), alternatives) for item, alternatives in expected_candidates),
        key=lambda result: len(result[0]),
    )
    phase_ids = {"PWR-L1", "PWR-L2", "PWR-L3"}
    phase_short = any(len(component & phase_ids) > 1 for component in actual_components)
    fuse_merged = any({"F-1", "F-3"}.issubset(component) or {"F-2", "F-4"}.issubset(component) for component in actual_components)
    correction_counts = Counter(correction for item in candidate for correction in item.corrections)
    terminal_degrees = Counter(terminal for item in candidate for terminal in (item.left, item.right))
    terminal_capacities = {item["terminal_id"]: item["max_connections"] for item in problem["circuit"]["terminals"]}
    capacity_overflows = sorted(
        terminal for terminal, degree in terminal_degrees.items()
        if terminal in terminal_capacities and degree > terminal_capacities[terminal]
    )
    terminals = {terminal for item in candidate for terminal in (item.left, item.right)}
    return {
        "raw_line_count": len(candidate),
        "unique_wire_count": len({item.key for item in candidate}),
        "corrections": sorted(correction_counts),
        "exact_expected_net_matches": len(exact_matches),
        "exact_expected_net_ids": exact_matches,
        "exact_alternative_ids": list(exact_alternatives),
        "projected_expected_net_matches": len(projected_matches),
        "projected_alternative_ids": list(projected_alternatives),
        "projected_missing_net_ids": sorted(set(expected) - set(projected_matches)),
        "missing_protective_earth": not {"PWR-PE", "M1-PE", "M2-PE"}.issubset(terminals),
        "phase_short_detected": phase_short,
        "fuse_channel_merge_detected": fuse_merged,
        "capacity_overflow_terminal_ids": capacity_overflows,
        "production_grading_relaxed": False,
        "classification": "기능 Net 후보이나 완성 실기결선으로는 오답",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Q-Net 010 사용자 후보 답안 비공개 감사")
    parser.parse_args()
    print(json.dumps(audit_candidate(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

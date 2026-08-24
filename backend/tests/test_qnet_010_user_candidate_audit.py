from __future__ import annotations

from app.domain import WiringConnection
from app.repositories import ProblemRepository
from app.services import DeviceBehaviorRuntimeComposer
from app.services.wiring_network_service import build_network_components, compare_network_candidates
from app.simulation import passes_operation_requirements
from problem_test_utils import PROJECT_ROOT
from scripts.audit_qnet_010_user_candidate import (
    CONTACT_ORIENTATION_MAP,
    RAW_USER_CANDIDATE,
    audit_candidate,
    candidate_wiring_connections,
    normalize_candidate,
    normalize_terminal,
)


PROBLEM_ID = "qnet_electrician_practical_010"


def package():
    repository = ProblemRepository(PROJECT_ROOT / "problems", PROJECT_ROOT / "schemas", PROJECT_ROOT / "catalog")
    assert repository.reload().excluded == 0
    result = repository._get_package_internal(PROBLEM_ID)
    assert result is not None
    return repository, result


def roles(item) -> dict[str, str]:
    result = {pin.terminal_id: pin.terminal_role for board_item in item.board.items for pin in board_item.pins}
    result.update({terminal.terminal_id: "external" for device in item.problem.wiring_semantics.external_devices for terminal in device.terminals})
    return result


def comparison(item, connections: list[WiringConnection]):
    components = build_network_components((connection.key for connection in connections), roles(item))
    expected = {net.net_id: frozenset(net.terminals) for net in item.answer.expected_nets}
    return compare_network_candidates(components, expected, item.answer.allowed_alternatives)


def test_user_original_is_preserved_and_obvious_notation_errors_are_normalized():
    assert "PB22-2>X2-3" in RAW_USER_CANDIDATE
    assert "EOCR-11>YL" in RAW_USER_CANDIDATE
    normalized = normalize_candidate()
    assert len(normalized) == 62
    assert any(item.raw == "PB22-2>X2-3" and item.left == "PB2-2" for item in normalized)
    assert any(item.raw == "EOCR-11>YL" and item.right == "YL-1" for item in normalized)
    assert normalize_terminal("F1")[0] == "F-1"
    assert normalize_terminal("EOCR-7(U)")[0] == "EOCR-U"


def test_wire_direction_is_ignored_but_terminal_identity_is_not_relaxed():
    forward = normalize_candidate("PB0-1>EOCR-96")[0]
    reverse = normalize_candidate("EOCR-96>PB0-1")[0]
    assert forward.key == reverse.key
    assert normalize_candidate("X1-8>MC1-5")[0].key != normalize_candidate("X1-6>MC1-5")[0].key


def test_candidate_audit_separates_functional_projection_from_completed_practical_wiring():
    result = audit_candidate()
    assert result["raw_line_count"] == 62
    assert result["exact_expected_net_matches"] == 21
    assert result["projected_expected_net_matches"] == 31
    assert result["projected_alternative_ids"] == ["T1_CONTACT_SWAP", "T2_CONTACT_SWAP"]
    assert result["projected_missing_net_ids"] == ["P04_PE"]
    assert result["missing_protective_earth"] is True
    assert result["phase_short_detected"] is False
    assert result["fuse_channel_merge_detected"] is False
    assert result["capacity_overflow_terminal_ids"] == ["LS1-1", "LS2-1", "PB1-1", "PB2-1", "RL-2", "WL-2", "YL-2"]
    assert result["production_grading_relaxed"] is False


def test_unmodified_candidate_is_rejected_by_private_grading():
    _, item = package()
    result = comparison(item, candidate_wiring_connections())
    assert not result.electrically_equivalent
    assert "P04_PE" in result.missing_net_ids


def test_candidate_functional_notation_passes_operation_but_remains_incomplete():
    repository, item = package()
    runtime = DeviceBehaviorRuntimeComposer(repository.catalog).compose(item.problem.circuit, item.problem.operation)
    assert passes_operation_requirements(
        circuit=runtime.circuit,
        definition=runtime.operation,
        connections=candidate_wiring_connections(),
        tests=item.answer.operation_tests,
    )


def test_audit_projection_plus_pe_is_electrically_equivalent_without_changing_grader_rules():
    _, item = package()
    projected = [
        WiringConnection(**{
            "from": CONTACT_ORIENTATION_MAP.get(connection.from_terminal, connection.from_terminal),
            "to": CONTACT_ORIENTATION_MAP.get(connection.to, connection.to),
        })
        for connection in candidate_wiring_connections()
    ]
    projected.extend([
        WiringConnection(**{"from": "PWR-PE", "to": "M1-PE"}),
        WiringConnection(**{"from": "M1-PE", "to": "M2-PE"}),
    ])
    result = comparison(item, projected)
    assert result.electrically_equivalent
    assert result.alternative_ids == ("T1_CONTACT_SWAP", "T2_CONTACT_SWAP")


def test_user_candidate_never_enters_frontend_source_or_bundle():
    frontend_files = [*(PROJECT_ROOT / "frontend" / "src").rglob("*"), *(PROJECT_ROOT / "frontend" / "dist").rglob("*")]
    text = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in frontend_files if path.is_file())
    assert "PB22-2>X2-3" not in text
    assert "EOCR-11>YL" not in text


def test_public_problem_exposes_only_safe_contact_display_metadata():
    repository, _ = package()
    public = repository.get_public(PROBLEM_ID)
    assert public is not None
    contact_types = {device["device_id"]: device.get("contact_type") for device in public.wiring_semantics["external_devices"]}
    assert contact_types == {"PB0": "NC", "PB1": "NO", "PB2": "NO", "LS1": "NO", "LS2": "NO", "YL": None, "WL": None, "RL": None, "GL": None, "M1": None, "M2": None, "PWR": None}
    serialized = public.model_dump_json()
    for secret in ("expected_nets", "allowed_alternatives", "operation_tests", "PB22-2>X2-3"):
        assert secret not in serialized

    demo = repository.get_public("operation_demo_001")
    assert demo is not None
    demo_types = {device["device_id"]: device.get("contact_type") for device in demo.wiring_semantics["external_devices"]}
    assert demo_types["PB0"] == "NC"
    assert demo_types["PB1"] == "NO"
    assert demo_types["LS1"] == "NO"

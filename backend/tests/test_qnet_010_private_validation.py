from __future__ import annotations

from copy import deepcopy
import shutil

import pytest
from fastapi.testclient import TestClient

from app.domain import WiringConnection
from app.core.config import Settings
from app.core.paths import AppPaths
from app.main import create_app
from app.repositories import ProblemRepository
from app.services import DeviceBehaviorRuntimeComposer
from app.services.wiring_network_service import build_network_components, compare_network_candidates
from app.simulation import passes_operation_requirements
from problem_test_utils import PROJECT_ROOT
from scripts.build_qnet_010_private_definition import build_answer, build_problem


PROBLEM_ID = "qnet_electrician_practical_010"


@pytest.fixture(scope="module")
def package():
    repository = ProblemRepository(PROJECT_ROOT / "problems", PROJECT_ROOT / "schemas", PROJECT_ROOT / "catalog")
    stats = repository.reload()
    assert stats.excluded == 0
    item = repository._get_package_internal(PROBLEM_ID)
    assert item is not None
    return item


def connections(package) -> list[WiringConnection]:
    return [
        WiringConnection(**{
            "from": item.from_terminal,
            "to": item.to,
            "wire_color": item.wire_color,
        })
        for item in package.answer.wiring_connections
    ]


def roles(package) -> dict[str, str]:
    result = {
        pin.terminal_id: pin.terminal_role
        for item in package.board.items
        for pin in item.pins
    }
    result.update({
        terminal.terminal_id: "external"
        for device in package.problem.wiring_semantics.external_devices
        for terminal in device.terminals
    })
    return result


def comparison(package, items: list[WiringConnection]):
    components = build_network_components((item.key for item in items), roles(package))
    expected = {item.net_id: frozenset(item.terminals) for item in package.answer.expected_nets}
    return compare_network_candidates(components, expected, package.answer.allowed_alternatives)


def runtime(package):
    repository = ProblemRepository(PROJECT_ROOT / "problems", PROJECT_ROOT / "schemas", PROJECT_ROOT / "catalog")
    repository.reload()
    return DeviceBehaviorRuntimeComposer(repository.catalog).compose(
        package.problem.circuit, package.problem.operation
    )


def remap(items: list[WiringConnection], mapping: dict[str, str]) -> list[WiringConnection]:
    return [
        WiringConnection(**{
            "from": mapping.get(item.from_terminal, item.from_terminal),
            "to": mapping.get(item.to, item.to),
            "wire_color": item.wire_color,
        })
        for item in items
    ]


def remove_terminal_edge(items: list[WiringConnection], terminal: str) -> list[WiringConnection]:
    result = deepcopy(items)
    result.remove(next(item for item in result if terminal in item.key))
    return result


def test_qnet_010_stays_draft_unverified_but_has_complete_private_definitions(package):
    assert package.manifest.status == "draft"
    assert package.answer.verification.status == "unverified"
    assert package.problem.circuit.definition_status == "functional"
    assert package.problem.operation is not None
    assert package.problem.operation.simulation_status == "functional"
    assert package.problem.operation.simulation_mode == "actual_wiring"
    assert len(package.answer.expected_nets) == 32
    assert len(package.answer.operation_tests) == 5


def test_committed_qnet_010_json_matches_reproducible_catalog_builder():
    import json

    problem = json.loads((PROJECT_ROOT / "problems" / PROBLEM_ID / "problem.json").read_text(encoding="utf-8"))
    answer = json.loads((PROJECT_ROOT / "problems" / PROBLEM_ID / "answer.json").read_text(encoding="utf-8"))
    assert problem == build_problem()
    assert answer == build_answer()


def test_fuse_is_one_four_terminal_device_with_two_and_only_two_intrinsic_channels(package):
    fuse = next(item for item in package.problem.circuit.devices if item.device_id == "F")
    assert fuse.behavior_model_id == "fuse_dual_4terminal_training"
    pairs = {
        frozenset((item.from_terminal, item.to))
        for item in package.problem.operation.internal_connections
        if item.from_terminal.startswith("F-") or item.to.startswith("F-")
    }
    assert pairs == {frozenset(("F-1", "F-2")), frozenset(("F-3", "F-4"))}
    for forbidden in (("F-1", "F-3"), ("F-1", "F-4"), ("F-2", "F-3"), ("F-2", "F-4")):
        assert frozenset(forbidden) not in pairs


def test_canonical_and_tb_renumbered_wiring_are_electrically_equivalent(package):
    original = connections(package)
    assert comparison(package, original).electrically_equivalent
    tb_mapping = {
        "TB5-01": "TB5-11", "TB5-02": "TB5-12", "TB5-03": "TB5-13", "TB5-04": "TB5-14",
        "TB5-05": "TB5-15", "TB5-06": "TB5-16", "TB5-07": "TB5-17", "TB5-08": "TB5-18",
        "TB6-01": "TB6-11", "TB6-02": "TB6-12", "TB6-03": "TB6-13", "TB6-04": "TB6-14",
    }
    changed = comparison(package, remap(original, tb_mapping))
    assert changed.electrically_equivalent


def test_same_net_with_different_wire_tree_is_electrically_equivalent(package):
    original = connections(package)
    target_nodes = {"F-2", "EOCR-A1", "EOCR-95", "EOCR-97"}
    changed = [item for item in original if not set(item.key).issubset(target_nodes)]
    changed.extend([
        WiringConnection(**{"from": "F-2", "to": "EOCR-95"}),
        WiringConnection(**{"from": "EOCR-95", "to": "EOCR-A1"}),
        WiringConnection(**{"from": "EOCR-A1", "to": "EOCR-97"}),
    ])
    assert comparison(package, changed).electrically_equivalent


@pytest.mark.parametrize("device_id", ["X1", "X2", "T1", "T2"])
def test_equivalent_8p_changeover_contact_groups_are_accepted_as_a_whole(package, device_id):
    mapping = {
        f"{device_id}-1": f"{device_id}-8", f"{device_id}-8": f"{device_id}-1",
        f"{device_id}-4": f"{device_id}-5", f"{device_id}-5": f"{device_id}-4",
        f"{device_id}-3": f"{device_id}-6", f"{device_id}-6": f"{device_id}-3",
    }
    result = comparison(package, remap(connections(package), mapping))
    assert result.electrically_equivalent
    assert f"{device_id}_CONTACT_SWAP" in result.alternative_ids


def test_partial_8p_pin_substitution_is_not_accepted(package):
    result = comparison(package, remap(connections(package), {"X1-3": "X1-6"}))
    assert not result.electrically_equivalent


@pytest.mark.parametrize("terminal", ["MCCB-L1", "PB0-1", "F-1", "EOCR-95", "T1-3", "MC1-1"])
def test_required_connection_omission_is_rejected(package, terminal):
    assert not comparison(package, remove_terminal_edge(connections(package), terminal)).electrically_equivalent


@pytest.mark.parametrize("left,right", [
    ("PWR-L1", "PWR-L2"),
    ("PWR-L1", "PWR-L3"),
    ("F-1", "F-3"),
    ("F-2", "F-4"),
    ("EOCR-96", "PB0-2"),
    ("F-1", "F-2"),
    ("EOCR-L1", "EOCR-U"),
    ("T1-1", "MC1-6"),
    ("MC1-1", "MC1-7"),
    ("F-2", "MC1-6"),
    ("MC1-5", "MC1-11"),
])
def test_short_merge_and_stop_fuse_eocr_timer_mc_bypasses_are_rejected(package, left, right):
    items = connections(package) + [WiringConnection(**{"from": left, "to": right})]
    assert not comparison(package, items).electrically_equivalent


def test_isolated_tb_jumper_is_detected_for_reject_policy(package):
    items = connections(package) + [WiringConnection(**{"from": "TB5-19", "to": "TB5-20"})]
    result = comparison(package, items)
    assert result.electrically_equivalent
    assert result.isolated_junction_count == 1
    assert package.problem.wiring_semantics.extra_jumper_policy == "reject"


def test_canonical_actual_wiring_passes_all_private_operation_tests(package):
    composed = runtime(package)
    assert passes_operation_requirements(
        circuit=composed.circuit,
        definition=composed.operation,
        connections=connections(package),
        tests=package.answer.operation_tests,
    )


def test_tb_renumbering_and_all_8p_contact_swaps_still_pass_actual_operation(package):
    mapping = {
        "TB5-01": "TB5-11", "TB5-02": "TB5-12", "TB5-03": "TB5-13", "TB5-04": "TB5-14",
        "TB5-05": "TB5-15", "TB5-06": "TB5-16", "TB5-07": "TB5-17", "TB5-08": "TB5-18",
        "TB6-01": "TB6-11", "TB6-02": "TB6-12", "TB6-03": "TB6-13", "TB6-04": "TB6-14",
    }
    for device_id in ("X1", "X2", "T1", "T2"):
        mapping.update({
            f"{device_id}-1": f"{device_id}-8", f"{device_id}-8": f"{device_id}-1",
            f"{device_id}-4": f"{device_id}-5", f"{device_id}-5": f"{device_id}-4",
            f"{device_id}-3": f"{device_id}-6", f"{device_id}-6": f"{device_id}-3",
        })
    alternative = remap(connections(package), mapping)
    assert comparison(package, alternative).electrically_equivalent
    composed = runtime(package)
    assert passes_operation_requirements(
        circuit=composed.circuit,
        definition=composed.operation,
        connections=alternative,
        tests=package.answer.operation_tests,
    )


def test_stop_bypass_fails_both_network_answer_and_actual_operation_requirements(package):
    bypassed = connections(package) + [WiringConnection(**{"from": "EOCR-96", "to": "PB0-2"})]
    assert not comparison(package, bypassed).electrically_equivalent
    composed = runtime(package)
    assert not passes_operation_requirements(
        circuit=composed.circuit,
        definition=composed.operation,
        connections=bypassed,
        tests=package.answer.operation_tests,
    )


def test_public_package_never_contains_private_answer_keys(package):
    repository = ProblemRepository(PROJECT_ROOT / "problems", PROJECT_ROOT / "schemas", PROJECT_ROOT / "catalog")
    repository.reload()
    public = repository.get_public(PROBLEM_ID)
    serialized = public.model_dump_json()
    for secret in ("expected_nets", "allowed_alternatives", "wiring_connections", "operation_tests", "answer.json"):
        assert secret not in serialized


def qnet_paths(tmp_path) -> AppPaths:
    bundle = tmp_path / "bundle"
    for name in ("schemas", "catalog", "free_templates"):
        shutil.copytree(PROJECT_ROOT / name, bundle / name)
    shutil.copytree(PROJECT_ROOT / "problems" / PROBLEM_ID, bundle / "problems" / PROBLEM_ID)
    dist = bundle / "frontend" / "dist"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text("<html>test</html>", encoding="utf-8")
    return AppPaths(
        project_root=bundle,
        bundle_root=bundle,
        frontend_dist=dist,
        problems_dir=bundle / "problems",
        catalog_dir=bundle / "catalog",
        writable_root=tmp_path / "data",
        database_file=tmp_path / "data" / "test.db",
        logs_dir=tmp_path / "logs",
        log_file=tmp_path / "logs" / "test.log",
    )


def test_unverified_public_apis_block_grading_and_operation_but_internal_data_remains(tmp_path, package):
    payload = [item.model_dump(by_alias=True, mode="json", exclude={"connection_id"}) for item in package.answer.wiring_connections]
    with TestClient(create_app(Settings(paths=qnet_paths(tmp_path)))) as client:
        detail = client.get(f"/api/problems/{PROBLEM_ID}")
        assert detail.status_code == 200
        assert detail.json()["operation"] is None
        for secret in ("expected_nets", "allowed_alternatives", "wiring_connections", "operation_tests", "answer.json"):
            assert secret not in detail.text

        submitted = client.post(
            f"/api/problems/{PROBLEM_ID}/wiring-attempts/submit",
            json={"problem_version": 1, "connections": payload},
        )
        assert submitted.status_code == 200
        assert submitted.json()["gradable"] is False
        assert submitted.json()["overall_correct"] is None

        setup = client.get(f"/api/problems/{PROBLEM_ID}/operation-setup")
        assert setup.status_code == 200
        assert setup.json()["operation"] is None
        assert setup.json()["operation_ready"] is False
        assert setup.json()["preview_allowed"] is False
        assert "근거 검증 대기" in setup.json()["message"]
        assert "operation_tests" not in setup.text

        session = client.post(
            f"/api/problems/{PROBLEM_ID}/operation-sessions",
            json={"problem_version": 1},
        )
        assert session.status_code == 409
        assert "검증되지 않아" in session.json()["detail"]

        overloaded = [*payload,
            {"from": "MCCB-L1", "to": "TB5-19", "wire_color": "yellow"},
            {"from": "MCCB-L1", "to": "TB5-20", "wire_color": "yellow"},
        ]
        capacity = client.post(
            f"/api/problems/{PROBLEM_ID}/wiring-attempts/submit",
            json={"problem_version": 1, "connections": overloaded},
        )
        assert capacity.status_code == 422
        assert capacity.json()["detail"]["code"] == "too_many_connections"


def test_frontend_source_and_production_bundle_contain_no_private_qnet_010_answers():
    files = [
        *list((PROJECT_ROOT / "frontend" / "src").rglob("*")),
        *list((PROJECT_ROOT / "frontend" / "dist").rglob("*")),
    ]
    text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in files
        if path.is_file()
    )
    for secret in ("P01_L1_IN", "C16_RETURN", "X1_CONTACT_SWAP", "PB1_TIMER_MC1"):
        assert secret not in text

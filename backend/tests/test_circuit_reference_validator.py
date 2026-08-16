from __future__ import annotations

from copy import deepcopy

import pytest

from app.domain import AnswerDefinition, ProblemDefinition
from app.services import CatalogService, CircuitReferenceValidator
from problem_test_utils import PROJECT_ROOT


def valid_data():
    problem = {
        "schema_version": "1.0", "problem_id": "fixture_001", "description": "가상 참조 검사 데이터",
        "instructions": ["검사"], "learning_objectives": [],
        "power_supply": {"system": "3P3W_AC_220V", "voltage": 220, "frequency": 60, "wire_colors": {"L1": "brown", "L2": "black", "L3": "gray", "PE": "green", "control": "yellow"}},
        "schematic": {"file": "schematic.svg", "format": "svg", "view_box": "0 0 10 10"},
        "board": {"layout_id": "fixture_board"}, "available_devices": [],
        "circuit": {
            "schema_version": "1.0", "definition_status": "structure_only",
            "devices": [{"device_id": "X1", "device_type_id": "auxiliary_relay_8p", "label": "X1", "socket_type_id": "socket_8p_base", "board_position": {"row": 1, "column": 1, "x": 0.5, "y": 0.5}, "installed_initially": False}],
            "terminals": [
                {"terminal_id": "X1-1", "device_id": "X1", "pin_number": 1, "terminal_type": "socket_pin", "electrical_role": "contact_common", "max_connections": 2, "enabled": True},
                {"terminal_id": "X1-2", "device_id": "X1", "pin_number": 2, "terminal_type": "socket_pin", "electrical_role": "coil", "max_connections": 2, "enabled": True},
                {"terminal_id": "X1-4", "device_id": "X1", "pin_number": 4, "terminal_type": "socket_pin", "electrical_role": "contact_no", "max_connections": 2, "enabled": True},
                {"terminal_id": "X1-7", "device_id": "X1", "pin_number": 7, "terminal_type": "socket_pin", "electrical_role": "coil", "max_connections": 2, "enabled": True}
            ],
            "coils": [{"coil_id": "X1-COIL", "owner_device_id": "X1", "terminal_a_id": "X1-2", "terminal_b_id": "X1-7", "rated_voltage": 220, "voltage_type": "AC", "frequency": 60}],
            "contacts": [{"contact_id": "X1-C1", "owner_device_id": "X1", "contact_type": "NO", "common_terminal_id": "X1-1", "switched_terminal_id": "X1-4", "controlled_by_coil_id": "X1-COIL", "normal_state": "open"}]
        },
        "socket_questions": [{"question_id": "SQ001", "target_element_type": "contact", "target_element_id": "X1-C1", "display_label": "X1", "answer_slots": [{"slot_id": "upper", "position": "above"}, {"slot_id": "lower", "position": "below"}]}]
    }
    answer = {
        "schema_version": "1.0", "problem_id": "fixture_001", "answer_version": 1,
        "verification": {"status": "unverified", "verified_by": None, "verified_at": None, "notes": "테스트 전용 가상 데이터"},
        "socket_pin_answers": {"SQ001": {"upper": 1, "lower": 4}},
        "required_connections": [{"connection_id": "C1", "from": "X1-1", "to": "X1-4", "wire_color": "yellow"}],
        "expected_nets": [{"net_id": "N1", "terminals": ["X1-1", "X1-4"]}],
        "allowed_alternatives": [], "forbidden_connections": [],
        "wire_color_rules": {"L1": "brown", "L2": "black", "L3": "gray", "PE": "green", "control": "yellow"},
        "operation_tests": []
    }
    return problem, answer


def validate(problem_data, answer_data):
    service = CatalogService(PROJECT_ROOT / "catalog", PROJECT_ROOT / "schemas")
    return CircuitReferenceValidator(service).validate(
        ProblemDefinition.model_validate(problem_data), AnswerDefinition.model_validate(answer_data)
    )


def test_valid_virtual_circuit_references():
    problem, answer = valid_data()
    assert validate(problem, answer) == []


@pytest.mark.parametrize(
    "mutation, expected_code",
    [
        (lambda p, a: p["circuit"]["devices"].append(deepcopy(p["circuit"]["devices"][0])), "duplicate_device_id"),
        (lambda p, a: p["circuit"]["terminals"].append(deepcopy(p["circuit"]["terminals"][0])), "duplicate_terminal_id"),
        (lambda p, a: p["circuit"]["terminals"][0].update(device_id="MISSING"), "unknown_terminal_device"),
        (lambda p, a: p["circuit"]["devices"][0].update(socket_type_id="socket_missing"), "unknown_socket_type"),
        (lambda p, a: p["circuit"]["terminals"][0].update(pin_number=9), "invalid_socket_pin"),
        (lambda p, a: p["circuit"]["terminals"][1].update(pin_number=1), "duplicate_device_pin"),
        (lambda p, a: p["circuit"]["contacts"][0].update(common_terminal_id="X1-99"), "unknown_contact_terminal"),
        (lambda p, a: p["circuit"]["contacts"][0].update(controlled_by_coil_id="MISSING"), "unknown_contact_coil"),
        (lambda p, a: p["circuit"]["coils"][0].update(terminal_b_id="X1-2"), "same_coil_terminals"),
        (lambda p, a: p["circuit"]["contacts"][0].update(normal_state="closed"), "invalid_contact_normal_state"),
        (lambda p, a: p["socket_questions"][0].update(target_element_id="MISSING"), "unknown_question_target"),
        (lambda p, a: a["required_connections"][0].update(to="MISSING"), "unknown_answer_terminal"),
        (lambda p, a: a["expected_nets"][0]["terminals"].append("MISSING"), "unknown_expected_net_terminal"),
    ],
)
def test_reference_errors_are_reported_with_codes(mutation, expected_code):
    problem, answer = valid_data()
    mutation(problem, answer)
    codes = {issue.code for issue in validate(problem, answer)}
    assert expected_code in codes

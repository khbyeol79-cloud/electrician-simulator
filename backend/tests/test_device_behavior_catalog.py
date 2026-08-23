from __future__ import annotations

import json
import shutil

import pytest

from app.services import CatalogError, CatalogService
from problem_test_utils import PROJECT_ROOT


def _catalog(tmp_path, mutate=None):
    catalog_dir = tmp_path / "catalog"
    shutil.copytree(PROJECT_ROOT / "catalog", catalog_dir)
    path = catalog_dir / "device_behaviors.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if mutate:
        mutate(data)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return CatalogService(catalog_dir, PROJECT_ROOT / "schemas")


def _model(data, model_id: str):
    return next(item for item in data["models"] if item["model_id"] == model_id)


def test_behavior_catalog_loads_and_keeps_problem_answers_out():
    catalog = CatalogService(PROJECT_ROOT / "catalog", PROJECT_ROOT / "schemas")
    assert len(catalog.device_behaviors()) == 17
    serialized = json.dumps(
        [item.model_dump(mode="json") for item in catalog.device_behaviors()],
        ensure_ascii=False,
    )
    assert "expected_nets" not in serialized
    assert "wiring_connections" not in serialized
    assert "TB5-" not in serialized
    assert "TB6-" not in serialized


def test_behavior_catalog_rejects_duplicate_model_id(tmp_path):
    def mutate(data):
        data["models"].append(data["models"][0])

    with pytest.raises(CatalogError, match="카탈로그 ID가 중복"):
        _catalog(tmp_path, mutate)


def test_behavior_catalog_rejects_wrong_schema_version(tmp_path):
    def mutate(data):
        data["schema_version"] = "2.0"

    with pytest.raises(CatalogError, match="카탈로그 형식 오류"):
        _catalog(tmp_path, mutate)


def test_behavior_catalog_rejects_unknown_device_type(tmp_path):
    def mutate(data):
        data["models"][0]["device_type_id"] = "missing_device"

    with pytest.raises(CatalogError, match="존재하지 않는 기구 종류"):
        _catalog(tmp_path, mutate)


def test_behavior_catalog_rejects_unknown_socket_type(tmp_path):
    def mutate(data):
        _model(data, "auxiliary_relay_8p_training_partial")["compatible_socket_type_ids"] = ["missing_socket"]

    with pytest.raises(CatalogError, match="존재하지 않는 소켓"):
        _catalog(tmp_path, mutate)


@pytest.mark.parametrize("field", ["terminal_key", "terminal_suffix", "pin_number"])
def test_behavior_catalog_rejects_duplicate_terminal_identity(tmp_path, field):
    def mutate(data):
        terminal = _model(data, "auxiliary_relay_8p_training_partial")["terminals"][1]
        terminal[field] = _model(data, "auxiliary_relay_8p_training_partial")["terminals"][0][field]

    with pytest.raises(CatalogError, match=field):
        _catalog(tmp_path, mutate)


def test_behavior_catalog_rejects_socket_pin_out_of_range(tmp_path):
    def mutate(data):
        _model(data, "auxiliary_relay_8p_training_partial")["terminals"][0]["pin_number"] = 12

    with pytest.raises(CatalogError, match="호환 소켓 범위"):
        _catalog(tmp_path, mutate)


def test_behavior_catalog_rejects_missing_coil_terminal(tmp_path):
    def mutate(data):
        _model(data, "auxiliary_relay_8p_training_partial")["coils"][0]["terminal_a_key"] = "missing_terminal"

    with pytest.raises(CatalogError, match="존재하지 않는 단자 키"):
        _catalog(tmp_path, mutate)


def test_behavior_catalog_rejects_missing_contact_terminal(tmp_path):
    def mutate(data):
        _model(data, "auxiliary_relay_8p_training_partial")["contacts"][0]["switched_terminal_key"] = "missing_terminal"

    with pytest.raises(CatalogError, match="존재하지 않는 단자 키"):
        _catalog(tmp_path, mutate)


def test_behavior_catalog_rejects_missing_contact_coil(tmp_path):
    def mutate(data):
        _model(data, "auxiliary_relay_8p_training_partial")["contacts"][0]["controlled_by_key"] = "missing_coil"

    with pytest.raises(CatalogError, match="존재하지 않는 코일 키"):
        _catalog(tmp_path, mutate)


def test_behavior_catalog_rejects_generated_id_suffix_collision(tmp_path):
    def mutate(data):
        _model(data, "auxiliary_relay_8p_training_partial")["contacts"][0]["id_suffix"] = "COIL"

    with pytest.raises(CatalogError, match="충돌하는 ID suffix"):
        _catalog(tmp_path, mutate)


def test_behavior_catalog_rejects_missing_timed_contact(tmp_path):
    def mutate(data):
        _model(data, "timer_8p_on_delay_training_partial")["timer"]["timed_contact_keys"] = ["missing_contact"]

    with pytest.raises(CatalogError, match="계시 접점"):
        _catalog(tmp_path, mutate)


def test_behavior_catalog_rejects_invalid_intrinsic_connection(tmp_path):
    def mutate(data):
        data["models"][1]["intrinsic_connections"][0]["to_terminal_key"] = "missing_terminal"

    with pytest.raises(CatalogError, match="존재하지 않는 단자 키"):
        _catalog(tmp_path, mutate)


def test_behavior_catalog_rejects_contact_state_contradiction(tmp_path):
    def mutate(data):
        _model(data, "push_button_no")["contacts"][0]["normal_state"] = "closed"

    with pytest.raises(CatalogError, match="기본 상태가 모순"):
        _catalog(tmp_path, mutate)


def test_behavior_catalog_rejects_capability_contradiction(tmp_path):
    def mutate(data):
        _model(data, "auxiliary_relay_8p_training_partial")["capabilities"] = ["relay_contacts"]

    with pytest.raises(CatalogError, match="coil 동작"):
        _catalog(tmp_path, mutate)


def test_behavior_catalog_rejects_answer_only_field_with_path(tmp_path):
    def mutate(data):
        data["models"][0]["expected_nets"] = []

    with pytest.raises(CatalogError) as error:
        _catalog(tmp_path, mutate)
    message = str(error.value)
    assert "device_behaviors.json" in message
    assert "models.0" in message or "models[0]" in message


def test_device_models_keep_scenario_relationships_out():
    catalog = CatalogService(PROJECT_ROOT / "catalog", PROJECT_ROOT / "schemas")
    contactor = catalog.get_device_behavior("magnetic_contactor_12p_training")
    eocr = catalog.get_device_behavior("eocr_12p_training")
    motor = catalog.get_device_behavior("motor_three_phase")
    assert contactor is not None and eocr is not None and motor is not None
    payload = json.dumps(
        [
            contactor.model_dump(mode="json"),
            eocr.model_dump(mode="json"),
            motor.model_dump(mode="json"),
        ],
        ensure_ascii=False,
    )
    for forbidden in ("forward_coil_id", "reverse_coil_id", "protected_coil_ids", "protected_motor_ids", "start_control_id", "contactor_ids"):
        assert forbidden not in payload
    assert eocr.protection is not None
    assert motor.motor is not None and motor.motor.phase_terminal_keys == ["phase_u", "phase_v", "phase_w"]


def test_qnet_page_9_verifies_all_8p_changeover_pins():
    catalog = CatalogService(PROJECT_ROOT / "catalog", PROJECT_ROOT / "schemas")
    relay = catalog.get_device_behavior("auxiliary_relay_8p_training_partial")
    timer = catalog.get_device_behavior("timer_8p_on_delay_training_partial")
    assert relay is not None and timer is not None
    assert {item.pin_number for item in relay.terminals} == set(range(1, 9))
    assert {item.pin_number for item in timer.terminals} == set(range(1, 9))
    assert relay.definition_status == timer.definition_status == "verified"
    assert [(item.common_terminal_key, item.nc_terminal_key, item.no_terminal_key) for item in relay.contacts] == [
        ("contact_1_common", "contact_1_nc", "contact_1_no"),
        ("contact_2_common", "contact_2_nc", "contact_2_no"),
    ]
    assert all(item.contact_type == "CHANGEOVER" for item in [*relay.contacts, *timer.contacts])


def test_qnet_010_page_9_verifies_12p_contactor_and_eocr():
    """Q-Net 공개문제 010의 8~9쪽에 근거한 공통 12P 핀 회귀검사."""
    catalog = CatalogService(PROJECT_ROOT / "catalog", PROJECT_ROOT / "schemas")
    contactor = catalog.get_device_behavior("magnetic_contactor_12p_training")
    eocr = catalog.get_device_behavior("eocr_12p_training")
    assert contactor is not None and eocr is not None
    assert contactor.definition_status == "verified"
    assert eocr.definition_status == "verified"

    contactor_pins = {item.terminal_key: item.pin_number for item in contactor.terminals}
    assert contactor_pins == {
        "line_1": 1, "line_2": 2, "line_3": 3,
        "aux_no_common": 4, "aux_nc_common": 5, "coil_a": 6,
        "load_1": 7, "load_2": 8, "load_3": 9,
        "aux_no": 10, "aux_nc": 11, "coil_b": 12,
    }
    assert {
        (item.contact_type, item.common_terminal_key, item.switched_terminal_key)
        for item in contactor.contacts
    } >= {
        ("NO", "line_1", "load_1"),
        ("NO", "line_2", "load_2"),
        ("NO", "line_3", "load_3"),
        ("NO", "aux_no_common", "aux_no"),
        ("NC", "aux_nc_common", "aux_nc"),
    }

    eocr_pins = {item.terminal_key: item.pin_number for item in eocr.terminals}
    assert eocr_pins == {
        "line_1": 1, "line_2": 2, "line_3": 3,
        "trip_nc": 4, "trip_no": 5, "supply_a": 6,
        "load_u": 7, "load_v": 8, "load_w": 9,
        "trip_common_nc": 10, "trip_common_no": 11, "supply_b": 12,
    }
    assert {
        (item.contact_type, item.common_terminal_key, item.switched_terminal_key)
        for item in eocr.contacts
    } == {
        ("NC", "trip_common_nc", "trip_nc"),
        ("NO", "trip_common_no", "trip_no"),
    }
    assert {
        (item.from_terminal_key, item.to_terminal_key)
        for item in eocr.intrinsic_connections
    } == {
        ("line_1", "load_u"),
        ("line_2", "load_v"),
        ("line_3", "load_w"),
    }


def test_qnet_010_dual_fuse_has_four_terminals_and_two_isolated_channels():
    catalog = CatalogService(PROJECT_ROOT / "catalog", PROJECT_ROOT / "schemas")
    fuse = catalog.get_device_behavior("fuse_dual_4terminal_training")
    assert fuse is not None
    assert fuse.definition_status == "reviewed"
    assert all(item.pin_number is None for item in fuse.terminals)
    assert {item.terminal_suffix for item in fuse.terminals} == {"1", "2", "3", "4"}
    pairs = {
        frozenset((item.from_terminal_key, item.to_terminal_key))
        for item in fuse.intrinsic_connections
    }
    assert pairs == {
        frozenset(("channel_1_input", "channel_1_output")),
        frozenset(("channel_2_input", "channel_2_output")),
    }


def test_existing_single_pole_fuse_model_is_kept_for_workspace_compatibility():
    catalog = CatalogService(PROJECT_ROOT / "catalog", PROJECT_ROOT / "schemas")
    legacy = catalog.get_device_behavior("fuse_single_pole_training")
    dual = catalog.get_device_behavior("fuse_dual_4terminal_training")
    assert legacy is not None and dual is not None
    assert {item.terminal_suffix for item in legacy.terminals} == {"1", "2"}
    assert {item.terminal_suffix for item in dual.terminals} == {"1", "2", "3", "4"}


def test_dual_fuse_uses_direct_terminals_without_socket_pin_numbers():
    """4단자 F는 직접 나사단자 기구이므로 socket pin_number를 가지지 않는다."""
    catalog = CatalogService(PROJECT_ROOT / "catalog", PROJECT_ROOT / "schemas")
    fuse = catalog.get_device_behavior("fuse_dual_4terminal_training")
    assert fuse is not None
    assert fuse.compatible_socket_type_ids == []
    assert [item.terminal_suffix for item in fuse.terminals] == ["1", "2", "3", "4"]
    assert all(item.pin_number is None for item in fuse.terminals)
    assert {
        (item.from_terminal_key, item.to_terminal_key)
        for item in fuse.intrinsic_connections
    } == {
        ("channel_1_input", "channel_1_output"),
        ("channel_2_input", "channel_2_output"),
    }

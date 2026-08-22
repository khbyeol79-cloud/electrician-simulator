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


def test_behavior_catalog_loads_and_keeps_problem_answers_out():
    catalog = CatalogService(PROJECT_ROOT / "catalog", PROJECT_ROOT / "schemas")
    assert len(catalog.device_behaviors()) == 16
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
        data["models"][8]["compatible_socket_type_ids"] = ["missing_socket"]

    with pytest.raises(CatalogError, match="존재하지 않는 소켓"):
        _catalog(tmp_path, mutate)


@pytest.mark.parametrize("field", ["terminal_key", "terminal_suffix", "pin_number"])
def test_behavior_catalog_rejects_duplicate_terminal_identity(tmp_path, field):
    def mutate(data):
        terminal = data["models"][8]["terminals"][1]
        terminal[field] = data["models"][8]["terminals"][0][field]

    with pytest.raises(CatalogError, match=field):
        _catalog(tmp_path, mutate)


def test_behavior_catalog_rejects_socket_pin_out_of_range(tmp_path):
    def mutate(data):
        data["models"][8]["terminals"][0]["pin_number"] = 12

    with pytest.raises(CatalogError, match="호환 소켓 범위"):
        _catalog(tmp_path, mutate)


def test_behavior_catalog_rejects_missing_coil_terminal(tmp_path):
    def mutate(data):
        data["models"][8]["coils"][0]["terminal_a_key"] = "missing_terminal"

    with pytest.raises(CatalogError, match="존재하지 않는 단자 키"):
        _catalog(tmp_path, mutate)


def test_behavior_catalog_rejects_missing_contact_terminal(tmp_path):
    def mutate(data):
        data["models"][8]["contacts"][0]["switched_terminal_key"] = "missing_terminal"

    with pytest.raises(CatalogError, match="존재하지 않는 단자 키"):
        _catalog(tmp_path, mutate)


def test_behavior_catalog_rejects_missing_contact_coil(tmp_path):
    def mutate(data):
        data["models"][8]["contacts"][0]["controlled_by_key"] = "missing_coil"

    with pytest.raises(CatalogError, match="존재하지 않는 코일 키"):
        _catalog(tmp_path, mutate)


def test_behavior_catalog_rejects_generated_id_suffix_collision(tmp_path):
    def mutate(data):
        data["models"][8]["contacts"][0]["id_suffix"] = "COIL"

    with pytest.raises(CatalogError, match="충돌하는 ID suffix"):
        _catalog(tmp_path, mutate)


def test_behavior_catalog_rejects_missing_timed_contact(tmp_path):
    def mutate(data):
        data["models"][9]["timer"]["timed_contact_keys"] = ["missing_contact"]

    with pytest.raises(CatalogError, match="계시 접점"):
        _catalog(tmp_path, mutate)


def test_behavior_catalog_rejects_invalid_intrinsic_connection(tmp_path):
    def mutate(data):
        data["models"][1]["intrinsic_connections"][0]["to_terminal_key"] = "missing_terminal"

    with pytest.raises(CatalogError, match="존재하지 않는 단자 키"):
        _catalog(tmp_path, mutate)


def test_behavior_catalog_rejects_contact_state_contradiction(tmp_path):
    def mutate(data):
        data["models"][4]["contacts"][0]["normal_state"] = "closed"

    with pytest.raises(CatalogError, match="기본 상태가 모순"):
        _catalog(tmp_path, mutate)


def test_behavior_catalog_rejects_capability_contradiction(tmp_path):
    def mutate(data):
        data["models"][8]["capabilities"] = ["relay_contacts"]

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

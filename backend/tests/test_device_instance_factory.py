from __future__ import annotations

import copy

import pytest
from pydantic import ValidationError

from app.domain.device_behavior import DeviceInstanceCreate
from app.domain.problem_definition import BoardPosition
from app.services import CatalogService, DeviceInstanceError, DeviceInstanceFactory
from problem_test_utils import PROJECT_ROOT


@pytest.fixture
def factory():
    catalog = CatalogService(PROJECT_ROOT / "catalog", PROJECT_ROOT / "schemas")
    return DeviceInstanceFactory(catalog)


def request(model_id: str, instance_id: str, settings=None, socket_type_id=None):
    return DeviceInstanceCreate(
        model_id=model_id,
        instance_id=instance_id,
        label=instance_id,
        board_position=BoardPosition(row=1, column=2, x=0.25, y=0.5),
        settings=settings or {},
        socket_type_id=socket_type_id,
    )


def test_same_instance_input_is_deterministic(factory):
    first = factory.create(request("auxiliary_relay_8p_training_partial", "X1"))
    second = factory.create(request("auxiliary_relay_8p_training_partial", "X1"))
    assert first == second


def test_two_instances_never_share_ids(factory):
    first = factory.create(request("auxiliary_relay_8p_training_partial", "X1"))
    second = factory.create(request("auxiliary_relay_8p_training_partial", "X2"))
    first_ids = set(first.terminal_ids.values()) | set(first.coil_ids.values()) | set(first.contact_ids.values())
    second_ids = set(second.terminal_ids.values()) | set(second.coil_ids.values()) | set(second.contact_ids.values())
    assert first_ids.isdisjoint(second_ids)


def test_relay_fragment_matches_qnet_page_9_pin_map(factory):
    instance = factory.create(request("auxiliary_relay_8p_training_partial", "VR1"))
    assert instance.terminal_ids == {
        "coil_a": "VR1-2",
        "coil_b": "VR1-7",
        "contact_1_common": "VR1-1",
        "contact_1_nc": "VR1-4",
        "contact_1_no": "VR1-3",
        "contact_2_common": "VR1-8",
        "contact_2_nc": "VR1-5",
        "contact_2_no": "VR1-6",
    }
    assert instance.coil_ids["main_coil"] == "VR1-COIL"
    assert instance.contact_ids["contact_1"] == "VR1-C1"
    assert instance.contact_ids["contact_2"] == "VR1-C2"
    assert instance.coils[0].rated_voltage == 220
    assert instance.contacts[0].controlled_by_coil_id == "VR1-COIL"


def test_timer_fragment_resolves_delay_and_contact(factory):
    instance = factory.create(
        request("timer_8p_on_delay_training_partial", "T1", {"delay_ms": 2500})
    )
    assert instance.timers[0].delay_ms == 2500
    assert instance.timers[0].coil_id == "T1-COIL"
    assert instance.timers[0].timed_contact_ids == ["T1-C1", "T1-C2"]
    assert instance.contacts[0].controlled_by_coil_id == "T1-COIL"


def test_contactor_fragment_has_general_role_without_scenario_targets(factory):
    instance = factory.create(request("magnetic_contactor_12p_training", "MC1"))
    assert instance.contactors[0].role == "general"
    assert instance.contactors[0].start_control_id is None
    assert instance.contactors[0].motor_id is None
    assert {item.contact_id for item in instance.contacts} >= {
        "MC1-MAIN1", "MC1-MAIN2", "MC1-MAIN3", "MC1-HOLD", "MC1-INTERLOCK"
    }


def test_manual_controls_are_operation_fragments_not_coil_contacts(factory):
    start = factory.create(request("push_button_no", "PB1"))
    stop = factory.create(request("push_button_nc", "PB0"))
    assert not start.contacts and not stop.contacts
    assert start.controls[0].contact_type == "NO"
    assert stop.controls[0].contact_type == "NC"
    assert start.controls[0].terminal_a_id == "PB1-1"
    assert stop.controls[0].terminal_b_id == "PB0-2"


def test_indicator_color_is_instance_setting(factory):
    red = factory.create(
        request("indicator_lamp_two_terminal", "RL", {"display_color": "red"})
    )
    green = factory.create(
        request("indicator_lamp_two_terminal", "GL", {"display_color": "green"})
    )
    assert red.indicators[0].display_color == "red"
    assert green.indicators[0].display_color == "green"


def test_eocr_protection_contacts_are_runtime_fragments(factory):
    instance = factory.create(request("eocr_12p_training", "EOCR"))
    assert "overload_protection" in instance.deferred_operation_capabilities
    assert "protection_contacts" not in instance.deferred_operation_capabilities
    assert {item.contact_id for item in instance.contacts} == {
        "EOCR-TRIP-NC", "EOCR-TRIP-NO"
    }
    assert {item.controller_type for item in instance.contacts} == {"protection"}
    assert {item.controller_id for item in instance.contacts} == {"EOCR"}
    assert len(instance.intrinsic_connections) == 3


def test_motor_direction_relationship_is_deferred(factory):
    instance = factory.create(request("motor_three_phase", "M1"))
    assert set(instance.terminal_ids.values()) == {"M1-U", "M1-V", "M1-W"}
    assert "three_phase_load" in instance.deferred_operation_capabilities


def test_invalid_instance_id_is_rejected_before_factory():
    with pytest.raises(ValidationError):
        request("push_button_no", "PB-1")


def test_unknown_or_invalid_setting_is_rejected(factory):
    with pytest.raises(DeviceInstanceError, match="정의되지 않은 설정"):
        factory.create(request("indicator_lamp_two_terminal", "GL", {"answer": "green"}))
    with pytest.raises(DeviceInstanceError, match="허용 목록"):
        factory.create(request("indicator_lamp_two_terminal", "GL", {"display_color": "blue"}))
    with pytest.raises(DeviceInstanceError, match="최댓값"):
        factory.create(request("timer_8p_on_delay_training_partial", "T1", {"delay_ms": 9999999}))


def test_socket_compatibility_is_enforced(factory):
    with pytest.raises(DeviceInstanceError, match="호환되지 않습니다"):
        factory.create(
            request(
                "auxiliary_relay_8p_training_partial",
                "X1",
                socket_type_id="socket_12p_base",
            )
        )


def test_factory_does_not_mutate_catalog(factory):
    before = copy.deepcopy(factory.catalog.get_device_behavior("timer_8p_on_delay_training_partial"))
    factory.create(request("timer_8p_on_delay_training_partial", "T1", {"delay_ms": 3000}))
    after = factory.catalog.get_device_behavior("timer_8p_on_delay_training_partial")
    assert after == before


def test_board_position_comes_from_request(factory):
    position = BoardPosition(row=4, column=5, x=0.7, y=0.8)
    item = DeviceInstanceCreate(
        model_id="push_button_no",
        instance_id="PB1",
        label="기동",
        board_position=position,
    )
    instance = factory.create(item)
    assert instance.device.board_position == position

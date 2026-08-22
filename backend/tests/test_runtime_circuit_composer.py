from __future__ import annotations

import copy

import pytest

from app.services import RuntimeCompositionError
from actual_wiring_test_utils import compose_actual, source_definition


def test_composer_is_deterministic_idempotent_and_does_not_mutate_sources():
    circuit, operation = source_definition()
    before_circuit = copy.deepcopy(circuit)
    before_operation = copy.deepcopy(operation)
    first = compose_actual()
    second = compose_actual()
    assert first == second
    assert circuit == before_circuit
    assert operation == before_operation
    assert first.catalog_composed is True
    assert set(first.model_ids) == {item.behavior_model_id for item in circuit.devices}
    assert len({item.terminal_id for item in first.circuit.terminals}) == len(first.circuit.terminals)
    assert len({item.coil_id for item in first.circuit.coils}) == len(first.circuit.coils)
    assert len({item.contact_id for item in first.circuit.contacts}) == len(first.circuit.contacts)


def test_composer_adds_mc_main_contacts_eocr_contacts_and_intrinsic_paths():
    result = compose_actual()
    contacts = {item.contact_id: item for item in result.circuit.contacts}
    assert {"MC1-MAIN1", "MC1-MAIN2", "MC1-MAIN3"} <= set(contacts)
    assert contacts["MC1-MAIN1"].controller_type == "coil"
    assert contacts["EOCR-TRIP-NC"].controller_type == "protection"
    assert contacts["EOCR-TRIP-NO"].controller_id == "EOCR"
    pairs = {tuple(sorted((item.from_terminal, item.to))) for item in result.operation.internal_connections}
    assert tuple(sorted(("EOCR-L1", "EOCR-U"))) in pairs
    protection = result.operation.protection_devices[0]
    assert set(protection.protection_contact_ids) == {"EOCR-TRIP-NC", "EOCR-TRIP-NO"}
    assert any("magnetic_contactor_12p_training" in item for item in result.warnings)
    assert any("eocr_12p_training" in item for item in result.warnings)


def test_unknown_and_mismatched_explicit_model_bindings_are_rejected():
    from app.services import CatalogService, DeviceBehaviorRuntimeComposer
    from problem_test_utils import PROJECT_ROOT

    circuit, operation = source_definition()
    composer = DeviceBehaviorRuntimeComposer(
        CatalogService(PROJECT_ROOT / "catalog", PROJECT_ROOT / "schemas")
    )
    circuit.devices[0].behavior_model_id = "missing_model"
    with pytest.raises(RuntimeCompositionError, match="존재하지 않는"):
        composer.compose(circuit, operation)

    circuit, operation = source_definition()
    circuit.devices[0].behavior_model_id = "push_button_no"
    with pytest.raises(RuntimeCompositionError, match="일치하지 않습니다"):
        composer.compose(circuit, operation)


def test_composer_is_idempotent_for_already_composed_definition():
    from app.services import CatalogService, DeviceBehaviorRuntimeComposer
    from problem_test_utils import PROJECT_ROOT

    composer = DeviceBehaviorRuntimeComposer(
        CatalogService(PROJECT_ROOT / "catalog", PROJECT_ROOT / "schemas")
    )
    first = compose_actual()
    second = composer.compose(first.circuit, first.operation)
    assert second.circuit == first.circuit
    assert second.operation == first.operation


def test_actual_mode_uses_central_compatibility_mapping_for_legacy_device_type():
    from app.services import CatalogService, DeviceBehaviorRuntimeComposer
    from problem_test_utils import PROJECT_ROOT

    circuit, operation = source_definition()
    circuit.devices[0].behavior_model_id = None
    composer = DeviceBehaviorRuntimeComposer(
        CatalogService(PROJECT_ROOT / "catalog", PROJECT_ROOT / "schemas")
    )
    result = composer.compose(circuit, operation)
    assert "power_3p_control_training" in result.model_ids
    assert circuit.devices[0].behavior_model_id is None


def test_always_conductive_path_cannot_duplicate_dynamic_mc_contact():
    from app.domain.operation_definition import TerminalPair
    from app.services import CatalogService, DeviceBehaviorRuntimeComposer
    from problem_test_utils import PROJECT_ROOT

    circuit, operation = source_definition()
    operation.internal_connections.append(
        TerminalPair(**{"from": "MC1-1", "to": "MC1-7"})
    )
    composer = DeviceBehaviorRuntimeComposer(
        CatalogService(PROJECT_ROOT / "catalog", PROJECT_ROOT / "schemas")
    )
    with pytest.raises(RuntimeCompositionError, match="항상 도통 연결"):
        composer.compose(circuit, operation)

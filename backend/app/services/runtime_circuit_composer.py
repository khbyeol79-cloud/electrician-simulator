from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar

from pydantic import BaseModel

from app.domain.device_behavior import DeviceInstanceCreate
from app.domain.operation_definition import OperationDefinition, TerminalPair
from app.domain.problem_definition import CircuitDefinition, CircuitDevice

from .catalog_service import CatalogService
from .device_instance_factory import DeviceInstanceError, DeviceInstanceFactory


class RuntimeCompositionError(ValueError):
    """카탈로그 조각을 현재 회로 정의와 안전하게 합칠 수 없을 때 발생한다."""


@dataclass(frozen=True)
class RuntimeCircuitComposition:
    circuit: CircuitDefinition
    operation: OperationDefinition
    catalog_composed: bool
    model_ids: tuple[str, ...]
    warnings: tuple[str, ...]


T = TypeVar("T", bound=BaseModel)


class DeviceBehaviorRuntimeComposer:
    """저장 데이터를 바꾸지 않고 실행용 회로 정의만 완성한다."""

    _COMPATIBLE_MODELS = {
        "mccb": "mccb_3p_training",
        "fuse": "fuse_dual_4terminal_training",
        "power_source": "power_3p_control_training",
        "auxiliary_relay_8p": "auxiliary_relay_8p_training_partial",
        "timer_8p": "timer_8p_on_delay_training_partial",
        "auxiliary_relay_12p": "magnetic_contactor_12p_training",
        "eocr": "eocr_12p_training",
        "indicator_lamp": "indicator_lamp_two_terminal",
        "motor": "motor_three_phase",
    }

    def __init__(self, catalog: CatalogService):
        self.catalog = catalog
        self.factory = DeviceInstanceFactory(catalog)

    def compose(
        self,
        circuit: CircuitDefinition,
        operation: OperationDefinition,
    ) -> RuntimeCircuitComposition:
        runtime_circuit = circuit.model_copy(deep=True)
        runtime_operation = operation.model_copy(deep=True)
        model_ids: list[str] = []
        warnings: list[str] = []

        for device in runtime_circuit.devices:
            model_id = self._model_id(device, runtime_operation)
            if model_id is None:
                continue
            model = self.catalog.get_device_behavior(model_id)
            if model is None:
                raise RuntimeCompositionError(
                    f"{device.device_id}가 존재하지 않는 기구 동작 모델을 참조합니다: {model_id}"
                )
            if model.device_type_id != device.device_type_id:
                raise RuntimeCompositionError(
                    f"{device.device_id}의 기구 종류와 동작 모델이 일치하지 않습니다: "
                    f"{device.device_type_id} / {model.device_type_id}"
                )
            try:
                fragment = self.factory.create(
                    DeviceInstanceCreate(
                        model_id=model_id,
                        instance_id=device.device_id,
                        label=device.label,
                        board_position=device.board_position,
                        settings=self._settings(device, model_id, runtime_operation),
                        socket_type_id=device.socket_type_id,
                        installed_initially=device.installed_initially,
                    )
                )
            except DeviceInstanceError as exc:
                raise RuntimeCompositionError(str(exc)) from exc

            if self._upgrade_known_legacy_fragment(runtime_circuit, runtime_operation, fragment, model_id):
                warnings.append(f"{device.device_id}: 저장된 구형 기구 정의를 PDF 검수 모델로 실행합니다. 저장 결선은 변경하지 않습니다.")
            self._merge_models(runtime_circuit.terminals, fragment.terminals, "단자", "terminal_id")
            self._merge_models(runtime_circuit.coils, fragment.coils, "코일", "coil_id")
            self._merge_models(runtime_circuit.contacts, fragment.contacts, "접점", "contact_id")
            self._validate_dynamic_connection_conflicts(
                runtime_circuit, runtime_operation, fragment.intrinsic_connections
            )
            self._merge_operation(runtime_operation, fragment)
            self._bind_protection_contacts(runtime_operation, device.device_id, fragment)
            model_ids.append(model_id)
            if model.definition_status == "unverified":
                warnings.append(
                    f"{device.device_id}은(는) 검증 전 교육용 동작 모델 {model_id}을 사용합니다."
                )

        return RuntimeCircuitComposition(
            circuit=runtime_circuit,
            operation=runtime_operation,
            catalog_composed=bool(model_ids),
            model_ids=tuple(model_ids),
            warnings=tuple(warnings),
        )

    @staticmethod
    def _upgrade_known_legacy_fragment(circuit, operation, fragment, model_id: str) -> bool:
        """Recognize only the exact pre-PDF catalog shapes, on runtime copies.

        Unknown/custom conflicts still fail normal composition. Terminal IDs,
        saved wires and the persisted workspace are never migrated here.
        """
        owner = fragment.device.device_id
        contact = next((c for c in fragment.contacts if c.contact_id == f"{owner}-C1"), None)
        if contact is None:
            return False
        roles = {}
        if model_id == "timer_8p_on_delay_training_partial":
            legacy_contact = contact.model_copy(update={
                "contact_type": "CHANGEOVER", "nc_terminal_id": f"{owner}-4",
                "no_terminal_id": f"{owner}-3", "controller_type": "timer",
                "controller_id": f"{owner}-TIMER", "normal_state": "closed",
            })
            roles = {4: "contact_nc"}
        elif model_id == "flasher_relay_8p_training":
            legacy_contact = contact.model_copy(update={
                "contact_type": "NO", "common_terminal_id": f"{owner}-5",
                "switched_terminal_id": f"{owner}-8", "nc_terminal_id": None,
                "no_terminal_id": None, "normal_state": "open",
            })
            roles = {5: "contact_common", 6: "unassigned", 8: "contact_no"}
        elif model_id == "floatless_level_switch_8p_training":
            legacy_contact = contact.model_copy(update={
                "contact_type": "NO", "common_terminal_id": f"{owner}-3",
                "switched_terminal_id": f"{owner}-4", "nc_terminal_id": None,
                "no_terminal_id": None, "normal_state": "open",
            })
            roles = {2: "unassigned", 3: "contact_common", 4: "contact_no"}
        else:
            return False
        existing = next((c for c in circuit.contacts if c.contact_id == contact.contact_id), None)
        if existing != legacy_contact:
            return False
        replacements = [(circuit.contacts, "contact_id", contact, legacy_contact)]
        for terminal in fragment.terminals:
            if terminal.pin_number in roles:
                legacy = terminal.model_copy(update={"electrical_role": roles[terminal.pin_number]})
                replacements.append((circuit.terminals, "terminal_id", terminal, legacy))
        for timer in fragment.timers:
            legacy = timer.model_copy(update={"timed_contact_ids": [f"{owner}-C1", f"{owner}-C2"]})
            replacements.append((operation.timers, "timer_id", timer, legacy))
        # Do not partially upgrade a definition with unrelated user changes.
        for items, key, current, legacy in replacements:
            old = next((i for i in items if getattr(i, key) == getattr(current, key)), None)
            if old is not None and old != legacy and old != current:
                return False
        for items, key, current, legacy in replacements:
            for index, old in enumerate(items):
                if getattr(old, key) == getattr(current, key):
                    items[index] = current.model_copy(deep=True)
        return True

    def _model_id(self, device: CircuitDevice, operation: OperationDefinition) -> str | None:
        if device.behavior_model_id:
            return device.behavior_model_id
        if operation.simulation_mode != "actual_wiring":
            return None
        if device.device_type_id in {"push_button", "limit_switch"}:
            control = next(
                (item for item in operation.controls if item.control_id == device.device_id),
                None,
            )
            if control is None:
                return None
            prefix = "push_button" if device.device_type_id == "push_button" else "limit_switch"
            return f"{prefix}_{control.contact_type.lower()}"
        return self._COMPATIBLE_MODELS.get(device.device_type_id)

    @staticmethod
    def _settings(
        device: CircuitDevice,
        model_id: str,
        operation: OperationDefinition,
    ) -> dict[str, object]:
        if model_id == "timer_8p_on_delay_training_partial":
            timer = next(
                (
                    item
                    for item in operation.timers
                    if item.coil_id.startswith(f"{device.device_id}-")
                ),
                None,
            )
            return {"delay_ms": timer.delay_ms} if timer else {}
        if model_id == "flasher_relay_8p_training":
            flasher = next(
                (
                    item
                    for item in operation.flashers
                    if item.coil_id.startswith(f"{device.device_id}-")
                ),
                None,
            )
            return {"flash_interval_ms": flasher.interval_ms} if flasher else {}
        if model_id == "indicator_lamp_two_terminal":
            indicator = next(
                (item for item in operation.indicators if item.indicator_id == device.device_id),
                None,
            )
            return {"display_color": indicator.display_color} if indicator else {}
        return {}

    @staticmethod
    def _merge_models(target: list[T], additions: list[T], label: str, id_field: str) -> None:
        indexed = {getattr(item, id_field): item for item in target}
        for item in additions:
            item_id = getattr(item, id_field)
            existing = indexed.get(item_id)
            if existing is None:
                target.append(item)
                indexed[item_id] = item
                continue
            if existing != item:
                raise RuntimeCompositionError(
                    f"카탈로그와 기존 회로의 {label} 정의가 충돌합니다: {item_id}"
                )

    def _merge_operation(self, operation: OperationDefinition, fragment) -> None:
        self._merge_operation_items(operation.controls, fragment.controls, "입력기구", "control_id")
        self._merge_operation_items(operation.timers, fragment.timers, "타이머", "timer_id")
        self._merge_operation_items(operation.flashers, fragment.flashers, "플리커", "flasher_id")
        self._merge_operation_items(
            operation.level_relays, fragment.level_relays, "수위계전기", "level_relay_id"
        )
        self._merge_operation_items(operation.indicators, fragment.indicators, "표시등", "indicator_id")
        self._merge_operation_items(
            operation.audible_outputs, fragment.audible_outputs, "가청출력", "output_id"
        )
        self._merge_operation_items(operation.fuse_channels, fragment.fuse_channels, "FUSE 채널", "channel_id")
        self._merge_contactors(operation.contactors, fragment.contactors)
        existing_pairs = {
            tuple(sorted((item.from_terminal, item.to)))
            for item in operation.internal_connections
        }
        for pair in fragment.intrinsic_connections:
            key = tuple(sorted((pair.from_terminal, pair.to)))
            if key not in existing_pairs:
                operation.internal_connections.append(
                    TerminalPair(**{"from": pair.from_terminal, "to": pair.to})
                )
                existing_pairs.add(key)

    @staticmethod
    def _validate_dynamic_connection_conflicts(
        circuit: CircuitDefinition,
        operation: OperationDefinition,
        intrinsic_connections: list[TerminalPair],
    ) -> None:
        always_conductive = {
            tuple(sorted((item.from_terminal, item.to)))
            for item in [*operation.internal_connections, *intrinsic_connections]
        }
        for contact in circuit.contacts:
            if contact.contact_type == "CHANGEOVER":
                targets = [contact.nc_terminal_id, contact.no_terminal_id]
            else:
                targets = [contact.switched_terminal_id]
            for target in targets:
                if target is None:
                    continue
                pair = tuple(sorted((contact.common_terminal_id, target)))
                if pair in always_conductive:
                    raise RuntimeCompositionError(
                        "항상 도통 연결과 동적 접점의 단자쌍이 충돌합니다: "
                        f"{contact.contact_id} ({pair[0]} ↔ {pair[1]})"
                    )

    @staticmethod
    def _merge_operation_items(target: list[T], additions: list[T], label: str, id_field: str) -> None:
        indexed = {getattr(item, id_field): item for item in target}
        for item in additions:
            item_id = getattr(item, id_field)
            existing = indexed.get(item_id)
            if existing is None:
                target.append(item)
                indexed[item_id] = item
            elif (
                existing.model_dump(exclude={"label"})
                != item.model_dump(exclude={"label"})
            ):
                raise RuntimeCompositionError(
                    f"카탈로그와 기존 회로의 {label} 정의가 충돌합니다: {item_id}"
                )

    @staticmethod
    def _merge_contactors(target, additions) -> None:
        indexed = {item.contactor_id: item for item in target}
        for item in additions:
            existing = indexed.get(item.contactor_id)
            if existing is None:
                target.append(item)
                indexed[item.contactor_id] = item
            elif existing.coil_id != item.coil_id:
                raise RuntimeCompositionError(
                    f"카탈로그와 기존 회로의 전자접촉기 코일이 충돌합니다: {item.contactor_id}"
                )

    @staticmethod
    def _bind_protection_contacts(operation: OperationDefinition, device_id: str, fragment) -> None:
        contact_ids = [
            item.contact_id
            for item in fragment.contacts
            if item.controller_type == "protection"
        ]
        if not contact_ids:
            return
        protection = next(
            (
                item
                for item in operation.protection_devices
                if item.protection_device_id == device_id
            ),
            None,
        )
        if protection is None:
            raise RuntimeCompositionError(
                f"{device_id} 보호접점을 제어할 operation.protection_devices 정의가 없습니다."
            )
        protection.protection_contact_ids = list(
            dict.fromkeys([*protection.protection_contact_ids, *contact_ids])
        )
        supply_a = fragment.terminal_ids.get("supply_a")
        supply_b = fragment.terminal_ids.get("supply_b")
        # A1-A2 power enforcement is opt-in on the operation definition so
        # older training packages keep their established behavior. Audited
        # packages such as Q-Net 010 explicitly declare both terminals.
        if supply_a and supply_b and (
            protection.supply_terminal_a_id or protection.supply_terminal_b_id
        ):
            protection.supply_terminal_a_id = supply_a
            protection.supply_terminal_b_id = supply_b

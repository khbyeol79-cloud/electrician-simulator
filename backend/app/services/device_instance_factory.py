from __future__ import annotations

from typing import Any, cast

from app.domain.device_behavior import (
    BehaviorConfigurableProperty,
    DeviceBehaviorModel,
    DeviceInstanceCreate,
    DeviceInstanceDefinition,
    SettingValue,
)
from app.domain.operation_definition import (
    OperationAudibleOutput,
    OperationContactor,
    OperationControl,
    OperationFlasher,
    OperationFuseChannel,
    OperationIndicator,
    OperationLevelRelay,
    OperationTimer,
    TerminalPair,
)
from app.domain.problem_definition import CircuitCoil, CircuitContact, CircuitDevice, CircuitTerminal

from .catalog_service import CatalogService


class DeviceInstanceError(ValueError):
    """기구 모델을 실제 회로 인스턴스로 만들 수 없을 때 발생한다."""


class DeviceInstanceFactory:
    def __init__(self, catalog: CatalogService):
        self.catalog = catalog

    def create(self, request: DeviceInstanceCreate) -> DeviceInstanceDefinition:
        model = self.catalog.get_device_behavior(request.model_id)
        if model is None:
            raise DeviceInstanceError(f"존재하지 않는 기구 동작 모델입니다: {request.model_id}")
        settings = self._settings(model, request.settings)
        socket_type_id = self._socket_type(model, request.socket_type_id)

        terminal_ids = {
            terminal.terminal_key: f"{request.instance_id}-{terminal.terminal_suffix}"
            for terminal in model.terminals
        }
        coil_ids = {
            coil.coil_key: f"{request.instance_id}-{coil.id_suffix}"
            for coil in model.coils
        }
        contact_ids = {
            contact.contact_key: f"{request.instance_id}-{contact.id_suffix}"
            for contact in model.contacts
        }

        device = CircuitDevice(
            device_id=request.instance_id,
            device_type_id=model.device_type_id,
            label=request.label,
            socket_type_id=socket_type_id,
            behavior_model_id=model.model_id,
            board_position=request.board_position,
            installed_initially=request.installed_initially,
        )
        terminals = [
            CircuitTerminal(
                terminal_id=terminal_ids[item.terminal_key],
                device_id=request.instance_id,
                pin_number=item.pin_number,
                terminal_type=item.terminal_type,
                electrical_role=item.electrical_role,
                max_connections=item.max_connections,
                enabled=item.enabled,
            )
            for item in model.terminals
        ]
        coils = [
            CircuitCoil(
                coil_id=coil_ids[item.coil_key],
                owner_device_id=request.instance_id,
                terminal_a_id=terminal_ids[item.terminal_a_key],
                terminal_b_id=terminal_ids[item.terminal_b_key],
                rated_voltage=float(settings[item.rated_voltage_property_key]),
                voltage_type=cast(Any, settings[item.voltage_type_property_key]),
                frequency=(
                    float(settings[item.frequency_property_key])
                    if item.frequency_property_key is not None
                    else None
                ),
            )
            for item in model.coils
        ]

        circuit_contacts: list[CircuitContact] = []
        for item in model.contacts:
            if item.actuation == "manual":
                continue
            if item.actuation == "coil":
                controlled_by_coil_id = coil_ids[item.controlled_by_key]
                controller_id = controlled_by_coil_id
            elif item.actuation == "timer":
                if model.timer is None:
                    raise DeviceInstanceError(
                        f"{model.model_id}의 계시 접점에 타이머 정의가 없습니다."
                    )
                controlled_by_coil_id = coil_ids[model.timer.coil_key]
                controller_id = f"{request.instance_id}-{model.timer.id_suffix}"
            elif item.actuation == "flasher":
                if model.flasher is None:
                    raise DeviceInstanceError(
                        f"{model.model_id}의 플리커 접점에 플리커 정의가 없습니다."
                    )
                controlled_by_coil_id = coil_ids[model.flasher.coil_key]
                controller_id = f"{request.instance_id}-{model.flasher.id_suffix}"
            elif item.actuation == "level":
                if model.level_relay is None:
                    raise DeviceInstanceError(
                        f"{model.model_id}의 수위 접점에 수위계전기 정의가 없습니다."
                    )
                controlled_by_coil_id = None
                controller_id = f"{request.instance_id}-{model.level_relay.id_suffix}"
            else:
                controlled_by_coil_id = None
                controller_id = request.instance_id
            circuit_contacts.append(
                CircuitContact(
                    contact_id=contact_ids[item.contact_key],
                    owner_device_id=request.instance_id,
                    contact_type=item.contact_type,
                    common_terminal_id=terminal_ids[item.common_terminal_key],
                    switched_terminal_id=terminal_ids[item.switched_terminal_key],
                    nc_terminal_id=(terminal_ids[item.nc_terminal_key] if item.nc_terminal_key else None),
                    no_terminal_id=(terminal_ids[item.no_terminal_key] if item.no_terminal_key else None),
                    controller_type=item.actuation,
                    controller_id=controller_id,
                    controlled_by_coil_id=controlled_by_coil_id,
                    normal_state=item.normal_state,
                )
            )

        controls: list[OperationControl] = []
        if model.control:
            contact = next(item for item in model.contacts if item.contact_key == model.control.contact_key)
            alternate = next(
                (
                    item
                    for item in model.contacts
                    if item.contact_key == model.control.alternate_contact_key
                ),
                None,
            )
            controls.append(
                OperationControl(
                    control_id=request.instance_id,
                    label=request.label,
                    control_type=model.control.control_type,
                    mode=model.control.mode,
                    contact_type=cast(Any, contact.contact_type),
                    terminal_a_id=terminal_ids[contact.common_terminal_key],
                    terminal_b_id=terminal_ids[contact.switched_terminal_key],
                    alternate_terminal_a_id=(
                        terminal_ids[alternate.common_terminal_key] if alternate else None
                    ),
                    alternate_terminal_b_id=(
                        terminal_ids[alternate.switched_terminal_key] if alternate else None
                    ),
                    initial_active=model.control.initial_active,
                )
            )

        timers: list[OperationTimer] = []
        if model.timer:
            timers.append(
                OperationTimer(
                    timer_id=f"{request.instance_id}-{model.timer.id_suffix}",
                    label=request.label,
                    coil_id=coil_ids[model.timer.coil_key],
                    mode=model.timer.mode,
                    delay_ms=int(settings[model.timer.delay_property_key]),
                    timed_contact_ids=[contact_ids[key] for key in model.timer.timed_contact_keys],
                    retentive=model.timer.retentive,
                )
            )

        flashers: list[OperationFlasher] = []
        if model.flasher:
            flashers.append(
                OperationFlasher(
                    flasher_id=f"{request.instance_id}-{model.flasher.id_suffix}",
                    label=request.label,
                    coil_id=coil_ids[model.flasher.coil_key],
                    interval_ms=int(settings[model.flasher.interval_property_key]),
                    contact_ids=[contact_ids[key] for key in model.flasher.contact_keys],
                )
            )

        level_relays: list[OperationLevelRelay] = []
        if model.level_relay:
            level_relays.append(
                OperationLevelRelay(
                    level_relay_id=f"{request.instance_id}-{model.level_relay.id_suffix}",
                    label=request.label,
                    supply_terminal_a_id=terminal_ids[model.level_relay.supply_terminal_a_key],
                    supply_terminal_b_id=terminal_ids[model.level_relay.supply_terminal_b_key],
                    electrode_terminal_ids=[
                        terminal_ids[key] for key in model.level_relay.electrode_terminal_keys
                    ],
                    external_electrode_terminal_ids=[
                        f"{request.instance_id}-E1",
                        f"{request.instance_id}-E2",
                        f"{request.instance_id}-E3",
                    ],
                    contact_ids=[contact_ids[key] for key in model.level_relay.contact_keys],
                )
            )

        indicators: list[OperationIndicator] = []
        if model.indicator:
            indicators.append(
                OperationIndicator(
                    indicator_id=request.instance_id,
                    label=request.label,
                    display_color=cast(Any, settings[model.indicator.display_color_property_key]),
                    terminal_a_id=terminal_ids[model.indicator.terminal_a_key],
                    terminal_b_id=terminal_ids[model.indicator.terminal_b_key],
                )
            )

        audible_outputs: list[OperationAudibleOutput] = []
        if model.audible_output:
            audible_outputs.append(
                OperationAudibleOutput(
                    output_id=request.instance_id,
                    label=request.label,
                    terminal_a_id=terminal_ids[model.audible_output.terminal_a_key],
                    terminal_b_id=terminal_ids[model.audible_output.terminal_b_key],
                )
            )

        contactors: list[OperationContactor] = []
        if "contactor" in model.capabilities and coils:
            contactors.append(
                OperationContactor(
                    contactor_id=request.instance_id,
                    label=request.label,
                    coil_id=coils[0].coil_id,
                    role="general",
                    start_control_id=None,
                    motor_id=None,
                )
            )

        intrinsic_connections = [
            TerminalPair(
                **{
                    "from": terminal_ids[item.from_terminal_key],
                    "to": terminal_ids[item.to_terminal_key],
                }
            )
            for item in model.intrinsic_connections
        ]
        fuse_channels = []
        if model.device_type_id == "fuse":
            fuse_channels = [
                OperationFuseChannel(
                    channel_id=f"{request.instance_id}-CH{index}",
                    label=f"{request.label} {pair.from_terminal.rsplit('-', 1)[-1]}-{pair.to.rsplit('-', 1)[-1]}",
                    terminal_a_id=pair.from_terminal,
                    terminal_b_id=pair.to,
                )
                for index, pair in enumerate(intrinsic_connections, start=1)
            ]
        deferred = [
            capability
            for capability in ("power_source", "three_phase_load", "overload_protection")
            if capability in model.capabilities
        ]
        return DeviceInstanceDefinition(
            model_id=model.model_id,
            instance_id=request.instance_id,
            device=device,
            terminals=terminals,
            coils=coils,
            contacts=circuit_contacts,
            controls=controls,
            timers=timers,
            flashers=flashers,
            level_relays=level_relays,
            indicators=indicators,
            audible_outputs=audible_outputs,
            contactors=contactors,
            fuse_channels=fuse_channels,
            intrinsic_connections=intrinsic_connections,
            terminal_ids=terminal_ids,
            coil_ids=coil_ids,
            contact_ids=contact_ids,
            settings=settings,
            deferred_operation_capabilities=deferred,
        )

    def _socket_type(self, model: DeviceBehaviorModel, requested: str | None) -> str | None:
        compatible = model.compatible_socket_type_ids
        if requested is not None and requested not in compatible:
            raise DeviceInstanceError(
                f"{model.model_id} 모델은 {requested} 소켓과 호환되지 않습니다."
            )
        if requested is not None:
            return requested
        if len(compatible) == 1:
            return compatible[0]
        return None

    def _settings(self, model: DeviceBehaviorModel, supplied: dict[str, Any]) -> dict[str, SettingValue]:
        definitions = {item.property_key: item for item in model.configurable_properties}
        unknown = sorted(set(supplied) - set(definitions))
        if unknown:
            raise DeviceInstanceError(
                f"{model.model_id} 모델에 정의되지 않은 설정입니다: {unknown[0]}"
            )
        result: dict[str, SettingValue] = {}
        for key, definition in definitions.items():
            value = supplied.get(key, definition.default)
            if value is None:
                if definition.required:
                    raise DeviceInstanceError(f"필수 기구 설정이 없습니다: {key}")
                continue
            self._validate_setting(model, definition, value)
            result[key] = cast(SettingValue, value)
        return result

    @staticmethod
    def _validate_setting(
        model: DeviceBehaviorModel,
        definition: BehaviorConfigurableProperty,
        value: Any,
    ) -> None:
        if definition.value_type == "boolean":
            valid = isinstance(value, bool)
        elif definition.value_type == "integer":
            valid = isinstance(value, int) and not isinstance(value, bool)
        elif definition.value_type == "number":
            valid = isinstance(value, (int, float)) and not isinstance(value, bool)
        elif definition.value_type == "voltage_type":
            valid = isinstance(value, str)
        elif definition.value_type == "color":
            valid = isinstance(value, str)
        else:
            valid = isinstance(value, str)
        if not valid:
            raise DeviceInstanceError(
                f"{model.model_id}의 {definition.property_key} 설정 타입이 올바르지 않습니다."
            )
        if definition.choices and value not in definition.choices:
            raise DeviceInstanceError(
                f"{model.model_id}의 {definition.property_key} 설정값이 허용 목록에 없습니다."
            )
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if definition.minimum is not None and value < definition.minimum:
                raise DeviceInstanceError(
                    f"{model.model_id}의 {definition.property_key} 설정이 최솟값보다 작습니다."
                )
            if definition.maximum is not None and value > definition.maximum:
                raise DeviceInstanceError(
                    f"{model.model_id}의 {definition.property_key} 설정이 최댓값보다 큽니다."
                )

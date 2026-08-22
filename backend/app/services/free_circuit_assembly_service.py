from __future__ import annotations

from dataclasses import dataclass

from app.domain.board_definition import BoardDefinition, ForbiddenArea
from app.domain.device_behavior import DeviceInstanceCreate, DeviceInstanceDefinition
from app.domain.free_circuit import (
    FreeCircuitAssembly,
    FreeCircuitDevicePlacement,
    FreeCircuitInstalledDevice,
    FreeCircuitMountingSlot,
    FreeCircuitPaletteItem,
    FreeCircuitPaletteResponse,
    FreeCircuitWorkspaceUpdate,
)
from app.domain.operation_definition import (
    OperationDefinition,
    OperationMotor,
    OperationPower,
    OperationProtectionDevice,
)
from app.domain.operation_setup import DeviceLayoutDefinition, FixedDevicePlacement
from app.domain.problem_definition import (
    BoardPosition,
    CircuitDefinition,
    ExternalWiringDevice,
    ExternalWiringTerminal,
    WiringSemantics,
)
from app.repositories.problem_repository import ProblemRepository
from app.services.device_instance_factory import DeviceInstanceError, DeviceInstanceFactory


EMPTY_BOARD_TEMPLATE_ID = "empty_board_001"


@dataclass(frozen=True)
class _PaletteDefinition:
    palette_id: str
    model_id: str
    name: str
    category: str
    mounting_kind: str
    default_zone: str
    prototype_id: str | None
    id_prefix: str
    max_instances: int | None = None
    default_properties: dict[str, str | int | float | bool] | None = None


_PALETTE = (
    _PaletteDefinition("mccb", "mccb_3p_training", "MCCB", "보호·전원", "internal", "internal_upper", "MCCB", "MCCB", 1),
    _PaletteDefinition("fuse", "fuse_single_pole_training", "FUSE", "보호·전원", "internal", "internal_upper", "F", "F", 1),
    _PaletteDefinition("relay_8p", "auxiliary_relay_8p_training_partial", "8P 보조릴레이", "제어", "internal", "internal_upper", "X1", "X"),
    _PaletteDefinition("timer_8p", "timer_8p_on_delay_training_partial", "8P 온딜레이 타이머", "제어", "internal", "internal_lower", "T1", "T", default_properties={"delay_ms": 1000}),
    _PaletteDefinition("contactor_12p", "magnetic_contactor_12p_training", "12P 전자접촉기", "동력", "internal", "internal_lower", "MC1", "MC"),
    _PaletteDefinition("eocr", "eocr_12p_training", "EOCR", "보호·전원", "internal", "internal_upper", "EOCR", "EOCR", 1),
    _PaletteDefinition("power", "power_3p_control_training", "3상·제어 전원", "외부", "external", "external_top", None, "PWR", 1),
    _PaletteDefinition("pb_no", "push_button_no", "NO Push Button", "외부", "external", "external_top", None, "PB"),
    _PaletteDefinition("pb_nc", "push_button_nc", "NC Push Button", "외부", "external", "external_top", None, "PB"),
    _PaletteDefinition("ls_no", "limit_switch_no", "NO Limit Switch", "외부", "external", "external_top", None, "LS"),
    _PaletteDefinition("ls_nc", "limit_switch_nc", "NC Limit Switch", "외부", "external", "external_top", None, "LS"),
    _PaletteDefinition("lamp_green", "indicator_lamp_two_terminal", "녹색 표시등", "외부", "external", "external_bottom", None, "GL", default_properties={"display_color": "green"}),
    _PaletteDefinition("lamp_red", "indicator_lamp_two_terminal", "적색 표시등", "외부", "external", "external_bottom", None, "RL", default_properties={"display_color": "red"}),
    _PaletteDefinition("motor", "motor_three_phase", "3상 Motor", "외부", "external", "external_bottom", None, "M", 1),
)


class FreeCircuitAssemblyError(ValueError):
    pass


class FreeCircuitAssemblyService:
    """설치 목록을 권위 데이터로 사용해 보드와 실행 정의를 재구성한다."""

    INTERNAL_X = (90.0, 330.0, 570.0, 810.0, 1050.0)
    INTERNAL_Y = {"internal_upper": 200.0, "internal_lower": 500.0}

    def __init__(self, repository: ProblemRepository):
        self.repository = repository
        self.catalog = repository.catalog
        self.factory = DeviceInstanceFactory(self.catalog)
        package = repository._get_package_internal("forward_reverse_interlock_demo_001")
        if package is None or package.board is None:
            package = repository._get_package_internal("operation_demo_001")
        if package is None or package.board is None:
            raise FreeCircuitAssemblyError("빈보드의 공통 제어함 배치를 준비할 수 없습니다.")
        self.source_board = package.board

    def palette(self) -> FreeCircuitPaletteResponse:
        items: list[FreeCircuitPaletteItem] = []
        for definition in _PALETTE:
            model = self.catalog.get_device_behavior(definition.model_id)
            if model is None:
                items.append(FreeCircuitPaletteItem(
                    palette_id=definition.palette_id, model_id=definition.model_id,
                    device_type_id="unknown", name=definition.name,
                    category=definition.category, mounting_kind=definition.mounting_kind,
                    default_zone=definition.default_zone, definition_status="missing",
                    enabled=False, disabled_reason="공통 기구 모델을 찾을 수 없습니다.",
                ))
                continue
            defaults = {
                item.property_key: item.default
                for item in model.configurable_properties if item.default is not None
            }
            defaults.update(definition.default_properties or {})
            items.append(FreeCircuitPaletteItem(
                palette_id=definition.palette_id, model_id=model.model_id,
                device_type_id=model.device_type_id, name=definition.name,
                category=definition.category, mounting_kind=definition.mounting_kind,
                default_zone=definition.default_zone,
                socket_type_id=(model.compatible_socket_type_ids[0] if len(model.compatible_socket_type_ids) == 1 else None),
                definition_status=model.definition_status,
                capabilities=list(model.capabilities), default_properties=defaults,
                max_instances=definition.max_instances,
            ))
        return FreeCircuitPaletteResponse(items=items, slots=self.slots())

    def slots(self) -> list[FreeCircuitMountingSlot]:
        result = []
        for zone in ("internal_upper", "internal_lower"):
            for column, x in enumerate(self.INTERNAL_X):
                result.append(FreeCircuitMountingSlot(
                    slot_id=f"{zone}-{column}", zone=zone, column=column,
                    x=x, y=self.INTERNAL_Y[zone], width=200, height=180,
                ))
        for zone in ("external_top", "external_bottom"):
            for column in range(10):
                result.append(FreeCircuitMountingSlot(
                    slot_id=f"{zone}-{column}", zone=zone, column=column,
                    x=30 + column * 130, y=0 if zone == "external_top" else 875,
                    width=120, height=55,
                ))
        return result

    def empty_board(self) -> BoardDefinition:
        board = self.source_board.model_copy(deep=True)
        board.board_id = "free_empty_board_v1"
        board.items = [item for item in board.items if item.item_id in {"TB5", "TB6"}]
        board.forbidden_areas = [area for area in board.forbidden_areas if area.area_id.startswith(("TB5", "TB6"))]
        return board

    def empty_workspace(self, name: str) -> FreeCircuitWorkspaceUpdate:
        workspace = FreeCircuitWorkspaceUpdate(
            name=name,
            circuit=CircuitDefinition(schema_version="1.0", definition_status="functional"),
            operation=OperationDefinition(
                schema_version="1.0", simulation_status="functional", simulation_mode="actual_wiring",
                power=OperationPower(line_terminal_id="", return_terminal_id=""),
            ),
            board=self.empty_board(),
            device_layout=DeviceLayoutDefinition(), wiring_semantics=WiringSemantics(),
            assembly=FreeCircuitAssembly(),
        )
        return self.compose(workspace)

    def add(self, workspace: FreeCircuitWorkspaceUpdate, palette_id: str, placement: FreeCircuitDevicePlacement) -> FreeCircuitWorkspaceUpdate:
        if workspace.assembly is None or workspace.assembly.mode != "editable":
            raise FreeCircuitAssemblyError("이 작업공간은 기구 배치를 변경할 수 없습니다.")
        definition = self._definition(palette_id)
        self._validate_zone(definition, placement)
        if any(item.placement.zone == placement.zone and item.placement.column == placement.column for item in workspace.assembly.installed_devices):
            raise FreeCircuitAssemblyError("선택한 장착칸에는 이미 기구가 있습니다.")
        count = sum(item.palette_id == palette_id for item in workspace.assembly.installed_devices)
        if definition.max_instances is not None and count >= definition.max_instances:
            raise FreeCircuitAssemblyError(f"{definition.name}은(는) 최대 {definition.max_instances}개 설치할 수 있습니다.")
        instance_id = self._new_instance_id(workspace.assembly, definition)
        workspace.assembly.installed_devices.append(FreeCircuitInstalledDevice(
            instance_id=instance_id, palette_id=palette_id, model_id=definition.model_id,
            label=instance_id, placement=placement,
            properties=dict(definition.default_properties or {}),
        ))
        return self.compose(workspace)

    def move(self, workspace: FreeCircuitWorkspaceUpdate, instance_id: str, placement: FreeCircuitDevicePlacement) -> FreeCircuitWorkspaceUpdate:
        device = self._installed(workspace, instance_id)
        definition = self._definition(device.palette_id)
        self._validate_zone(definition, placement)
        if any(item.instance_id != instance_id and item.placement.zone == placement.zone and item.placement.column == placement.column for item in workspace.assembly.installed_devices):
            raise FreeCircuitAssemblyError("선택한 장착칸에는 이미 기구가 있습니다.")
        device.placement = placement
        return self.compose(workspace)

    def update(
        self, workspace: FreeCircuitWorkspaceUpdate, instance_id: str,
        placement: FreeCircuitDevicePlacement | None = None,
        properties: dict[str, str | int | float | bool] | None = None,
        label: str | None = None,
    ) -> FreeCircuitWorkspaceUpdate:
        device = self._installed(workspace, instance_id)
        if placement is not None:
            definition = self._definition(device.palette_id)
            self._validate_zone(definition, placement)
            if any(item.instance_id != instance_id and item.placement.zone == placement.zone and item.placement.column == placement.column for item in workspace.assembly.installed_devices):
                raise FreeCircuitAssemblyError("선택한 장착칸에는 이미 기구가 있습니다.")
            device.placement = placement
        if properties is not None:
            device.properties = properties
        if label is not None:
            normalized = label.strip()
            if not normalized:
                raise FreeCircuitAssemblyError("기구 표시 이름을 입력해 주세요.")
            device.label = normalized
        return self.compose(workspace)

    def delete(self, workspace: FreeCircuitWorkspaceUpdate, instance_id: str, remove_connected_wires: bool) -> FreeCircuitWorkspaceUpdate:
        device = self._installed(workspace, instance_id)
        prefix = f"{device.instance_id}-"
        connected = [item for item in workspace.connections if item.from_terminal.startswith(prefix) or item.to.startswith(prefix)]
        if connected and not remove_connected_wires:
            raise FreeCircuitAssemblyError(f"이 기구에는 전선 {len(connected)}가닥이 연결되어 있습니다. 연결 전선 삭제 확인이 필요합니다.")
        workspace.connections = [item for item in workspace.connections if item not in connected]
        workspace.assembly.installed_devices = [item for item in workspace.assembly.installed_devices if item.instance_id != instance_id]
        return self.compose(workspace)

    def compose(self, workspace: FreeCircuitWorkspaceUpdate) -> FreeCircuitWorkspaceUpdate:
        if workspace.assembly is None:
            return workspace
        board = self.empty_board()
        fragments: list[tuple[FreeCircuitInstalledDevice, DeviceInstanceDefinition]] = []
        for installed in workspace.assembly.installed_devices:
            definition = self._definition(installed.palette_id)
            if installed.model_id != definition.model_id:
                raise FreeCircuitAssemblyError(f"{installed.instance_id}의 팔레트 모델이 일치하지 않습니다.")
            self._validate_zone(definition, installed.placement)
            fragment = self._fragment(installed)
            fragments.append((installed, fragment))
            if definition.mounting_kind == "internal":
                board.items.append(self._board_item(installed, fragment, definition))
        # 단자는 기구 본체의 상·하단 경계에 놓인다. 금지영역을 본체보다
        # 크게 만들면 단자도 영역 안에 갇혀 첫 배선이 출발하지 못한다.
        # 기존 고정 보드와 같은 경계 규칙을 사용해 다른 전선의 본체 통과는
        # 막되, 해당 기구 단자에서는 통로 방향으로 빠져나갈 수 있게 한다.
        board.forbidden_areas.extend(ForbiddenArea(
            area_id=f"{item.item_id}_body", x=item.x, y=item.y,
            width=item.width, height=item.height,
        ) for item in board.items if item.item_id not in {"TB5", "TB6"})

        devices = [fragment.device for _, fragment in fragments]
        workspace.circuit = CircuitDefinition(
            schema_version="1.0", definition_status="functional", devices=devices,
        )
        controls = [value for _, fragment in fragments for value in fragment.controls]
        timers = [value for _, fragment in fragments for value in fragment.timers]
        indicators = [value for _, fragment in fragments for value in fragment.indicators]
        contactors = [value for _, fragment in fragments for value in fragment.contactors]
        intrinsic = [value for _, fragment in fragments for value in fragment.intrinsic_connections]
        power_fragment = next((fragment for installed, fragment in fragments if installed.palette_id == "power"), None)
        motor_fragments = [(installed, fragment) for installed, fragment in fragments if installed.palette_id == "motor"]
        phase_sources = [power_fragment.terminal_ids[key] for key in ("phase_1", "phase_2", "phase_3")] if power_fragment else []
        power = OperationPower(
            line_terminal_id=(power_fragment.terminal_ids["control_line"] if power_fragment else ""),
            return_terminal_id=(power_fragment.terminal_ids["neutral"] if power_fragment else ""),
            phase_terminal_ids=phase_sources,
        )
        motors = [OperationMotor(
            motor_id=installed.instance_id, label=installed.label,
            phase_terminal_ids=[fragment.terminal_ids[key] for key in ("phase_u", "phase_v", "phase_w")],
            phase_source_terminal_ids=phase_sources,
        ) for installed, fragment in motor_fragments]
        coil_ids = [coil.coil_id for _, fragment in fragments for coil in fragment.coils]
        protections = [OperationProtectionDevice(
            protection_device_id=installed.instance_id, label=installed.label,
            protected_coil_ids=coil_ids, protected_motor_ids=[motor.motor_id for motor in motors],
            reset_mode="manual",
        ) for installed, _ in fragments if installed.palette_id == "eocr"]
        workspace.operation = OperationDefinition(
            schema_version="1.0", simulation_status="functional", simulation_mode="actual_wiring",
            power=power, controls=controls, timers=timers, indicators=indicators,
            motors=motors, contactors=contactors, protection_devices=protections,
            internal_connections=intrinsic,
        )
        workspace.board = board
        workspace.device_layout = DeviceLayoutDefinition(fixed_placements=[
            FixedDevicePlacement(
                mount_device_id=installed.instance_id, label=installed.label,
                device_type_id=fragment.device.device_type_id,
                graphic_type=("timer" if installed.palette_id == "timer_8p" else "contactor" if installed.palette_id == "contactor_12p" else "relay"),
                socket_id=installed.instance_id,
                socket_type_id=fragment.device.socket_type_id,
            )
            for installed, fragment in fragments if fragment.device.socket_type_id
        ])
        workspace.wiring_semantics = WiringSemantics(external_devices=[
            self._external_device(installed, fragment)
            for installed, fragment in fragments
            if self._definition(installed.palette_id).mounting_kind == "external"
        ])
        return workspace

    def _fragment(self, installed: FreeCircuitInstalledDevice) -> DeviceInstanceDefinition:
        position = installed.placement
        try:
            return self.factory.create(DeviceInstanceCreate(
                model_id=installed.model_id, instance_id=installed.instance_id,
                label=installed.label,
                board_position=BoardPosition(
                    row=0 if position.zone.endswith("upper") or position.zone.endswith("top") else 1,
                    column=position.column, x=min(.95, .06 + position.column * .18),
                    y=.22 if position.zone == "internal_upper" else .55 if position.zone == "internal_lower" else .03 if position.zone == "external_top" else .94,
                ), settings=installed.properties,
            ))
        except DeviceInstanceError as exc:
            raise FreeCircuitAssemblyError(str(exc)) from exc

    def _board_item(self, installed, fragment, definition):
        prototype = next((item for item in self.source_board.items if item.item_id == definition.prototype_id), None)
        if prototype is None:
            raise FreeCircuitAssemblyError(f"{definition.name}의 보드 그래픽을 찾을 수 없습니다.")
        item = prototype.model_copy(deep=True)
        x = self.INTERNAL_X[installed.placement.column]
        y = self.INTERNAL_Y[installed.placement.zone]
        dx, dy = x - item.x, y - item.y
        item.item_id = installed.instance_id
        item.label = installed.label
        item.x, item.y = x, y
        item.row = 1 if installed.placement.zone == "internal_upper" else 2
        item.label_area.x += dx
        item.label_area.y += dy
        terminal_by_pin = {terminal.pin_number: terminal.terminal_id for terminal in fragment.terminals if terminal.pin_number is not None}
        suffixes = {terminal.terminal_id.rsplit("-", 1)[-1]: terminal.terminal_id for terminal in fragment.terminals}
        for pin in item.pins:
            pin.x += dx
            pin.y += dy
            terminal_id = terminal_by_pin.get(pin.number) or suffixes.get(pin.label)
            if terminal_id:
                pin.terminal_id = terminal_id
                pin.enabled = True
            else:
                pin.terminal_id = f"{installed.instance_id}-{pin.number or pin.label}"
                pin.enabled = False
        return item

    @staticmethod
    def _external_device(installed, fragment):
        colors = {"L": "brown", "L1": "brown", "L2": "black", "L3": "gray", "N": "black", "U": "brown", "V": "black", "W": "gray"}
        return ExternalWiringDevice(
            device_id=installed.instance_id, label=installed.label,
            placement="top" if installed.placement.zone == "external_top" else "bottom",
            terminals=[ExternalWiringTerminal(
                terminal_id=terminal.terminal_id,
                label=terminal.terminal_id.rsplit("-", 1)[-1],
                operation_terminal_id=terminal.terminal_id,
                max_connections=1,
                wire_color=colors.get(terminal.terminal_id.rsplit("-", 1)[-1], "yellow"),
            ) for terminal in fragment.terminals if terminal.enabled],
        )

    def _definition(self, palette_id):
        definition = next((item for item in _PALETTE if item.palette_id == palette_id), None)
        if definition is None or self.catalog.get_device_behavior(definition.model_id) is None:
            raise FreeCircuitAssemblyError(f"팔레트에 허용되지 않은 기구입니다: {palette_id}")
        return definition

    @staticmethod
    def _validate_zone(definition, placement):
        kind = "internal" if placement.zone.startswith("internal") else "external"
        if kind != definition.mounting_kind:
            raise FreeCircuitAssemblyError("내부 기구와 외부 기구의 장착 영역이 일치하지 않습니다.")
        maximum = 4 if kind == "internal" else 9
        if placement.column > maximum:
            raise FreeCircuitAssemblyError("장착 그리드 범위를 벗어났습니다.")

    @staticmethod
    def _new_instance_id(assembly, definition):
        used = {item.instance_id for item in assembly.installed_devices}
        for number in range(1, 100):
            candidate = f"{definition.id_prefix}{number}"
            if candidate not in used:
                return candidate
        raise FreeCircuitAssemblyError("새 기구 ID를 생성할 수 없습니다.")

    @staticmethod
    def _installed(workspace, instance_id):
        if workspace.assembly is None:
            raise FreeCircuitAssemblyError("설치 정보를 사용할 수 없는 작업공간입니다.")
        device = next((item for item in workspace.assembly.installed_devices if item.instance_id == instance_id), None)
        if device is None:
            raise FreeCircuitAssemblyError("설치된 기구를 찾을 수 없습니다.")
        return device

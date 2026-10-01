from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from app.domain.free_circuit import FreeCircuitTemplate
from app.domain.board_definition import BoardItem, BoardPin, BoardRect
from app.domain.operation_definition import (
    OperationContactor,
    OperationDefinition,
    OperationInterlock,
    OperationMotor,
    OperationPower,
    OperationProtectionDevice,
)
from app.domain.problem_definition import (
    BoardPosition,
    CircuitDefinition,
    CircuitDevice,
    ExternalWiringDevice,
    ExternalWiringTerminal,
    WiringSemantics,
)
from app.repositories.problem_repository import ProblemRepository
from app.services.free_circuit_assembly_service import (
    EMPTY_BOARD_TEMPLATE_ID,
    FreeCircuitAssemblyService,
)


BASIC_BOARD_TEMPLATE_ID = "basic_board_001"
LEGACY_FREE_TEMPLATE_IDS = (
    "operation_demo_001",
    "forward_reverse_interlock_demo_001",
    "eocr_sequence_demo_001",
)


class FreeCircuitTemplateError(ValueError):
    """자유회로 템플릿 데이터가 없거나 서로 일치하지 않을 때 발생한다."""


class BasicBoardTemplateConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(pattern=r"^1\.0$")
    template_id: str = Field(pattern=r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
    name: str
    description: str
    layout_source_id: str
    simulation_mode: str = Field(pattern=r"^actual_wiring$")
    device_models: dict[str, str]


class FreeCircuitTemplateService:
    """Q-Net 문제 목록과 분리된 신규 템플릿과 구형 호환 템플릿을 제공한다."""

    def __init__(self, repository: ProblemRepository, template_root: Path | None = None):
        self.repository = repository
        self.template_root = (
            template_root or repository.problems_dir.parent / "free_templates"
        ).resolve()

    def visible_templates(self) -> list[FreeCircuitTemplate]:
        return [self.get(BASIC_BOARD_TEMPLATE_ID), self.get(EMPTY_BOARD_TEMPLATE_ID)]

    def get(self, template_id: str) -> FreeCircuitTemplate:
        if template_id == BASIC_BOARD_TEMPLATE_ID:
            return self._basic_board()
        if template_id == EMPTY_BOARD_TEMPLATE_ID:
            workspace = FreeCircuitAssemblyService(self.repository).empty_workspace("빈보드")
            return FreeCircuitTemplate(
                template_id=EMPTY_BOARD_TEMPLATE_ID,
                name="빈보드",
                description="TB5·TB6만 배치된 자유 기구 설치 보드",
                board=workspace.board,
                circuit=workspace.circuit,
                operation=workspace.operation,
                device_layout=workspace.device_layout,
                wiring_semantics=workspace.wiring_semantics,
                assembly=workspace.assembly,
            )
        if template_id in LEGACY_FREE_TEMPLATE_IDS:
            return self._legacy(template_id)
        raise FreeCircuitTemplateError("자유회로 시작 템플릿을 찾을 수 없습니다.")

    def _config(self) -> BasicBoardTemplateConfig:
        path = self.template_root / BASIC_BOARD_TEMPLATE_ID / "template.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            config = BasicBoardTemplateConfig.model_validate(payload)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise FreeCircuitTemplateError(
                f"기본보드 설정을 읽을 수 없습니다: {path}"
            ) from exc
        if config.template_id != BASIC_BOARD_TEMPLATE_ID:
            raise FreeCircuitTemplateError("기본보드 설정의 template_id가 일치하지 않습니다.")
        return config

    def _basic_board(self) -> FreeCircuitTemplate:
        config = self._config()
        package = self.repository._get_package_internal(config.layout_source_id)
        if package is None or package.board is None:
            package = self.repository._get_package_internal("operation_demo_001")
        if package is None or package.board is None:
            raise FreeCircuitTemplateError("기본보드의 공통 제어함 배치를 준비할 수 없습니다.")

        board = package.board.model_copy(deep=True)
        board.board_id = "free_basic_board_v1"
        self._upgrade_basic_board_fuse(board)
        devices = self._devices(config, board)
        circuit = CircuitDefinition(
            schema_version="1.0",
            definition_status="functional",
            devices=devices,
            terminals=[],
            contacts=[],
            coils=[],
        )
        operation = OperationDefinition(
            schema_version="1.0",
            simulation_status="functional",
            simulation_mode="actual_wiring",
            power=OperationPower(
                line_terminal_id="PWR-L",
                return_terminal_id="PWR-N",
                phase_terminal_ids=["PWR-L1", "PWR-L2", "PWR-L3"],
            ),
            controls=[],
            timers=[],
            indicators=[],
            motors=[
                OperationMotor(
                    motor_id="M1",
                    label="M1 모터",
                    forward_coil_id="MC1-COIL",
                    reverse_coil_id="MC2-COIL",
                    phase_terminal_ids=["M1-U", "M1-V", "M1-W"],
                    phase_source_terminal_ids=["PWR-L1", "PWR-L2", "PWR-L3"],
                    forward_phase_order=[0, 1, 2],
                )
            ],
            contactors=[
                OperationContactor(
                    contactor_id="MC1", label="MC1", coil_id="MC1-COIL",
                    role="forward", start_control_id="PB1", motor_id="M1",
                ),
                OperationContactor(
                    contactor_id="MC2", label="MC2", coil_id="MC2-COIL",
                    role="reverse", start_control_id="PB2", motor_id="M1",
                ),
            ],
            interlocks=[
                OperationInterlock(
                    interlock_id="ELEC-MC1-MC2",
                    label="MC1·MC2 실제 NC 전기적 인터록",
                    type="electrical",
                    contactor_ids=["MC1", "MC2"],
                    contact_ids=["MC1-INTERLOCK", "MC2-INTERLOCK"],
                )
            ],
            protection_devices=[
                OperationProtectionDevice(
                    protection_device_id="EOCR",
                    label="EOCR",
                    protected_coil_ids=["MC1-COIL", "MC2-COIL"],
                    protected_motor_ids=["M1"],
                    protection_contact_ids=[],
                    reset_mode="restart_required",
                )
            ],
            direction_change_policy="stop_before_reverse",
            internal_connections=[],
        )
        return FreeCircuitTemplate(
            template_id=config.template_id,
            name=config.name,
            description=config.description,
            board=board,
            circuit=circuit,
            operation=operation,
            device_layout=package.problem.device_layout,
            wiring_semantics=self._wiring_semantics(),
        )

    @staticmethod
    def _upgrade_basic_board_fuse(board) -> None:
        """New workspaces always expose the physical two-channel 4-terminal FUSE."""
        old = next((item for item in board.items if item.item_id == "F"), None)
        if old is None:
            raise FreeCircuitTemplateError("기본보드 FUSE 배치를 찾을 수 없습니다.")
        x, y, width, height = old.x, old.y, 120.0, 150.0
        pin_x = {"1": x + 35, "2": x + 35, "3": x + 85, "4": x + 85}
        upgraded = BoardItem(
            item_id="F", label="F", item_type="component", row=old.row,
            x=x, y=y, width=width, height=height,
            pins=[
                BoardPin(
                    terminal_id=f"F-{number}", label=number, number=int(number),
                    side="top" if number in {"1", "3"} else "bottom",
                    x=pin_x[number], y=y if number in {"1", "3"} else y + height,
                    max_connections=2,
                )
                for number in ("1", "3", "2", "4")
            ],
            label_area=BoardRect(x=x + 44, y=y + 64, width=32, height=22),
        )
        board.items[board.items.index(old)] = upgraded

    def _legacy(self, template_id: str) -> FreeCircuitTemplate:
        package = self.repository._get_package_internal(template_id)
        if package is None or package.board is None or package.problem.operation is None:
            raise FreeCircuitTemplateError("기존 자유회로 시작 템플릿이 준비되지 않았습니다.")
        descriptions = {
            "operation_demo_001": "기존 자기유지·릴레이·타이머 실험 보드",
            "forward_reverse_interlock_demo_001": "기존 정·역회전·인터록 실험 보드",
            "eocr_sequence_demo_001": "기존 EOCR 보호 실험 보드",
        }
        return FreeCircuitTemplate(
            template_id=template_id,
            name=descriptions[template_id].removesuffix(" 실험 보드"),
            description=descriptions[template_id],
            board=package.board,
            circuit=package.problem.circuit,
            operation=package.problem.operation,
            device_layout=package.problem.device_layout,
            wiring_semantics=package.problem.wiring_semantics,
        )

    @staticmethod
    def _devices(config: BasicBoardTemplateConfig, board) -> list[CircuitDevice]:
        labels = {
            "MCCB": "MCCB", "F": "FUSE", "X1": "X1 보조릴레이",
            "X2": "X2 보조릴레이", "T1": "T1 타이머", "T2": "T2 타이머",
            "MC1": "MC1", "MC2": "MC2", "EOCR": "EOCR", "PWR": "외부 전원",
            "PB0": "PB0 정지", "PB1": "PB1 기동", "PB2": "PB2 기동",
            "LS1": "LS1 NO", "LS2": "LS2 NC", "GL": "GL 녹색 표시등",
            "RL": "RL 적색 표시등", "M1": "M1 모터",
        }
        types = {
            "MCCB": "mccb", "F": "fuse", "X1": "auxiliary_relay_8p",
            "X2": "auxiliary_relay_8p", "T1": "timer_8p", "T2": "timer_8p",
            "MC1": "auxiliary_relay_12p", "MC2": "auxiliary_relay_12p", "EOCR": "eocr",
            "PWR": "power_source", "PB0": "push_button", "PB1": "push_button",
            "PB2": "push_button", "LS1": "limit_switch", "LS2": "limit_switch",
            "GL": "indicator_lamp", "RL": "indicator_lamp", "M1": "motor",
        }
        sockets = {
            "X1": "socket_8p_base", "X2": "socket_8p_base",
            "T1": "socket_8p_base", "T2": "socket_8p_base",
            "MC1": "socket_12p_base", "MC2": "socket_12p_base",
            "EOCR": "socket_12p_base",
        }
        external_positions = {
            "PWR": (0, 0, .02, .03), "PB0": (0, 1, .15, .03),
            "PB1": (0, 2, .25, .03), "PB2": (0, 3, .35, .03),
            "LS1": (0, 4, .45, .03), "LS2": (0, 5, .55, .03),
            "GL": (3, 0, .35, .94), "RL": (3, 1, .48, .94), "M1": (3, 2, .65, .94),
        }
        board_items = {item.item_id: item for item in board.items}
        devices: list[CircuitDevice] = []
        for device_id, model_id in config.device_models.items():
            item = board_items.get(device_id)
            if item:
                position = BoardPosition(
                    row=item.row,
                    column=len(devices),
                    x=max(0, min(1, item.x / board.width)),
                    y=max(0, min(1, item.y / board.height)),
                )
            else:
                row, column, x, y = external_positions[device_id]
                position = BoardPosition(row=row, column=column, x=x, y=y)
            devices.append(CircuitDevice(
                device_id=device_id,
                device_type_id=types[device_id],
                label=labels[device_id],
                socket_type_id=sockets.get(device_id),
                behavior_model_id=model_id,
                board_position=position,
                installed_initially=True,
            ))
        return devices

    @staticmethod
    def _wiring_semantics() -> WiringSemantics:
        def terminal(terminal_id: str, label: str, color: str = "yellow"):
            return ExternalWiringTerminal(
                terminal_id=terminal_id,
                label=label,
                operation_terminal_id=terminal_id,
                max_connections=1,
                wire_color=color,
            )

        return WiringSemantics(
            schema_version="1.0",
            extra_jumper_policy="warning",
            external_devices=[
                ExternalWiringDevice(device_id="PWR", label="외부 전원", placement="top", terminals=[
                    terminal("PWR-L", "L", "brown"), terminal("PWR-N", "N", "black"),
                    terminal("PWR-L1", "L1", "brown"), terminal("PWR-L2", "L2", "black"),
                    terminal("PWR-L3", "L3", "gray"),
                ]),
                ExternalWiringDevice(device_id="PB0", label="PB0 정지(NC)", placement="top", terminals=[terminal("PB0-1", "1"), terminal("PB0-2", "2")]),
                ExternalWiringDevice(device_id="PB1", label="PB1 기동(NO)", placement="top", terminals=[terminal("PB1-1", "1"), terminal("PB1-2", "2")]),
                ExternalWiringDevice(device_id="PB2", label="PB2 기동(NO)", placement="top", terminals=[terminal("PB2-1", "1"), terminal("PB2-2", "2")]),
                ExternalWiringDevice(device_id="LS1", label="LS1(NO)", placement="top", terminals=[terminal("LS1-1", "1"), terminal("LS1-2", "2")]),
                ExternalWiringDevice(device_id="LS2", label="LS2(NC)", placement="top", terminals=[terminal("LS2-1", "1"), terminal("LS2-2", "2")]),
                ExternalWiringDevice(device_id="GL", label="GL 녹색 표시등", placement="bottom", terminals=[terminal("GL-1", "1"), terminal("GL-2", "2")]),
                ExternalWiringDevice(device_id="RL", label="RL 적색 표시등", placement="bottom", terminals=[terminal("RL-1", "1"), terminal("RL-2", "2")]),
                ExternalWiringDevice(device_id="M1", label="M1 모터", placement="bottom", terminals=[
                    terminal("M1-U", "U", "brown"), terminal("M1-V", "V", "black"), terminal("M1-W", "W", "gray"),
                ]),
            ],
        )

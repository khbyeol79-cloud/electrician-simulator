from __future__ import annotations

from dataclasses import dataclass

from app.domain.operation_definition import (
    ControlState,
    OperationAction,
    OperationDefinition,
    OperationFault,
    OperationSessionState,
    TimerState,
)
from app.domain.problem_definition import CircuitDefinition
from app.domain.wiring_attempt import WiringConnection

from .graph import ConductiveGraph


MAX_RESOLUTION_CYCLES = 50


class SimulationDefinitionError(ValueError):
    pass


@dataclass
class RuntimeTimer:
    elapsed_ms: int = 0
    completed: bool = False
    energized: bool = False


class OperationEngine:
    """결선과 공개 회로 정의로 도통 상태를 계산하는 결정적 논리 엔진."""

    def __init__(
        self,
        *,
        session_id: str,
        problem_id: str,
        wiring_attempt_id: int,
        circuit: CircuitDefinition,
        definition: OperationDefinition,
        connections: list[WiringConnection],
    ):
        self.session_id = session_id
        self.problem_id = problem_id
        self.wiring_attempt_id = wiring_attempt_id
        self.circuit = circuit
        self.definition = definition
        self.connections = connections
        self.powered = False
        self.tripped = False
        self.elapsed_ms = 0
        self.controls = {item.control_id: item.initial_active for item in definition.controls}
        self.coils = {item.coil_id: False for item in circuit.coils}
        self.contacts: dict[str, str] = {}
        self.timers = {item.timer_id: RuntimeTimer() for item in definition.timers}
        self.indicators = {item.indicator_id: "off" for item in definition.indicators}
        self.motors = {item.motor_id: "stopped" for item in definition.motors}
        self.faults: list[OperationFault] = []
        self.stable = True
        self.events: list[str] = ["동작시험 세션 시작"]
        self._validate_definition()
        self.resolve()

    def _validate_definition(self) -> None:
        coil_ids = set(self.coils)
        contact_ids = {item.contact_id for item in self.circuit.contacts}
        control_ids = set(self.controls)
        errors: list[str] = []
        for contact in self.circuit.contacts:
            if contact.controlled_by_coil_id not in coil_ids:
                errors.append(f"접점 {contact.contact_id}의 코일 참조가 없습니다.")
        for timer in self.definition.timers:
            if timer.coil_id not in coil_ids:
                errors.append(f"타이머 {timer.timer_id}의 코일 참조가 없습니다.")
            for contact_id in timer.timed_contact_ids:
                if contact_id not in contact_ids:
                    errors.append(f"타이머 접점 참조가 없습니다: {contact_id}")
        if len(control_ids) != len(self.definition.controls):
            errors.append("입력기구 ID가 중복되었습니다.")
        if errors:
            raise SimulationDefinitionError(" ".join(errors))

    def _timer_for_contact(self, contact_id: str) -> RuntimeTimer | None:
        for timer_definition in self.definition.timers:
            if contact_id in timer_definition.timed_contact_ids:
                return self.timers[timer_definition.timer_id]
        return None

    def _contact_active(self, contact) -> bool:
        timer = self._timer_for_contact(contact.contact_id)
        return timer.completed if timer is not None else self.coils.get(contact.controlled_by_coil_id, False)

    def _conductive_graph(self) -> ConductiveGraph:
        edges = [(item.from_terminal, item.to) for item in self.connections]
        edges.extend((item.from_terminal, item.to) for item in self.definition.internal_connections)
        graph = ConductiveGraph(edges)

        for control in self.definition.controls:
            active = self.controls[control.control_id]
            closed = active if control.contact_type == "NO" else not active
            if closed:
                graph.add(control.terminal_a_id, control.terminal_b_id)

        for contact in self.circuit.contacts:
            active = self._contact_active(contact)
            if contact.contact_type == "CHANGEOVER":
                target = contact.no_terminal_id if active else contact.nc_terminal_id
                if target:
                    graph.add(contact.common_terminal_id, target)
            else:
                closed = active if contact.contact_type == "NO" else not active
                if closed:
                    graph.add(contact.common_terminal_id, contact.switched_terminal_id)
        return graph

    @staticmethod
    def _load_energized(graph: ConductiveGraph, line: str, returning: str, terminal_a: str, terminal_b: str) -> bool:
        hot = graph.reachable(line)
        cold = graph.reachable(returning)
        return (terminal_a in hot and terminal_b in cold) or (terminal_b in hot and terminal_a in cold)

    def _detect_faults(self, graph: ConductiveGraph) -> list[OperationFault]:
        faults: list[OperationFault] = []
        power = self.definition.power
        if graph.connected(power.line_terminal_id, power.return_terminal_id):
            faults.append(OperationFault(code="direct_short", message="전원과 복귀선의 직접 단락 경로가 감지되었습니다.", severity="danger", trip_required=True))
        phases = power.phase_terminal_ids
        for index, first in enumerate(phases):
            for second in phases[index + 1:]:
                if graph.connected(first, second):
                    faults.append(OperationFault(code="phase_short", message="직접적인 상간 단락 경로가 감지되었습니다.", severity="danger", trip_required=True))
                    return faults
        return faults

    def _update_timer_energization(self) -> None:
        for definition in self.definition.timers:
            timer = self.timers[definition.timer_id]
            energized = self.coils.get(definition.coil_id, False) and self.powered and not self.tripped
            if not energized and timer.energized and not definition.retentive:
                timer.elapsed_ms = 0
                timer.completed = False
            timer.energized = energized

    def resolve(self) -> None:
        previous = dict(self.coils)
        seen: set[tuple[tuple[str, bool], ...]] = set()
        self.stable = True

        for _ in range(MAX_RESOLUTION_CYCLES):
            graph = self._conductive_graph()
            immediate_faults = self._detect_faults(graph)
            if self.powered and any(item.trip_required for item in immediate_faults):
                self.tripped = True
                self.powered = False
            next_coils: dict[str, bool] = {}
            for coil in self.circuit.coils:
                next_coils[coil.coil_id] = bool(
                    self.powered
                    and not self.tripped
                    and self._load_energized(
                        graph,
                        self.definition.power.line_terminal_id,
                        self.definition.power.return_terminal_id,
                        coil.terminal_a_id,
                        coil.terminal_b_id,
                    )
                )
            signature = tuple(sorted(next_coils.items()))
            if next_coils == self.coils:
                self.faults = immediate_faults
                break
            if signature in seen:
                self.stable = False
                self.faults = immediate_faults + [OperationFault(code="unstable_circuit", message="회로 상태가 안정되지 않았습니다. 결선 또는 회로 정의를 확인해 주세요.", severity="error", trip_required=True)]
                self.powered = False
                self.tripped = True
                self.coils = {key: False for key in self.coils}
                break
            seen.add(signature)
            self.coils = next_coils
        else:
            self.stable = False
            self.faults = [OperationFault(code="resolution_limit", message="회로 상태 계산의 최대 반복 횟수를 초과했습니다.", severity="error", trip_required=True)]
            self.powered = False
            self.tripped = True
            self.coils = {key: False for key in self.coils}

        self._update_timer_energization()
        graph = self._conductive_graph()
        self._update_outputs(graph)
        self._update_contact_states()
        for coil_id, value in self.coils.items():
            if previous.get(coil_id) != value:
                self._event(f"{coil_id} {'여자' if value else '무여자'}")

    def _update_contact_states(self) -> None:
        for contact in self.circuit.contacts:
            active = self._contact_active(contact)
            if contact.contact_type == "NO":
                closed = active
            elif contact.contact_type == "NC":
                closed = not active
            else:
                closed = True
            self.contacts[contact.contact_id] = "closed" if closed else "open"

    def _update_outputs(self, graph: ConductiveGraph) -> None:
        line = self.definition.power.line_terminal_id
        returning = self.definition.power.return_terminal_id
        for item in self.definition.indicators:
            self.indicators[item.indicator_id] = "on" if self.powered and self._load_energized(graph, line, returning, item.terminal_a_id, item.terminal_b_id) else "off"

        for motor in self.definition.motors:
            forward = bool(motor.forward_coil_id and self.coils.get(motor.forward_coil_id))
            reverse = bool(motor.reverse_coil_id and self.coils.get(motor.reverse_coil_id))
            if forward and reverse:
                self.motors[motor.motor_id] = "simultaneous_fault"
                if not any(item.code == "simultaneous_contactor" for item in self.faults):
                    self.faults.append(OperationFault(code="simultaneous_contactor", message="정·역 전자접촉기가 동시에 여자되었습니다.", severity="danger", trip_required=True))
                continue
            phase_ok = True
            mapped: list[int] = []
            if motor.phase_terminal_ids or motor.phase_source_terminal_ids:
                if len(motor.phase_terminal_ids) != 3 or len(motor.phase_source_terminal_ids) != 3:
                    self.motors[motor.motor_id] = "connection_error"
                    continue
                for terminal in motor.phase_terminal_ids:
                    matches = [index for index, source in enumerate(motor.phase_source_terminal_ids) if graph.connected(source, terminal)]
                    if len(matches) != 1:
                        phase_ok = False
                        break
                    mapped.append(matches[0])
                phase_ok = phase_ok and len(set(mapped)) == 3
            if (forward or reverse) and not phase_ok:
                self.motors[motor.motor_id] = "phase_loss"
                self.faults.append(OperationFault(code="motor_phase_loss", message=f"{motor.label}의 결상 또는 상 연결 오류가 감지되었습니다.", severity="error"))
            elif forward:
                self.motors[motor.motor_id] = "forward" if not mapped or mapped == motor.forward_phase_order else "reverse"
            elif reverse:
                self.motors[motor.motor_id] = "reverse"
            else:
                self.motors[motor.motor_id] = "stopped"

    def _event(self, message: str) -> None:
        if not self.events or self.events[-1] != message:
            self.events.append(message)
            self.events = self.events[-30:]

    def apply(self, action: OperationAction) -> OperationSessionState:
        if action.action == "set_power":
            if action.value:
                self.tripped = False
                self.powered = True
                self._event("전원 ON")
            else:
                self.powered = False
                self.tripped = False
                self._event("전원 OFF")
                self._reset_outputs()
        elif action.action in {"press_control", "release_control", "toggle_control"}:
            definition = next((item for item in self.definition.controls if item.control_id == action.control_id), None)
            if definition is None:
                raise ValueError("존재하지 않는 입력기구입니다.")
            if action.action == "toggle_control":
                if definition.mode != "maintained":
                    raise ValueError("유지형 입력기구만 상태를 전환할 수 있습니다.")
                self.controls[definition.control_id] = not self.controls[definition.control_id]
            else:
                self.controls[definition.control_id] = action.action == "press_control"
            self._event(f"{definition.label} {'작동' if self.controls[definition.control_id] else '복귀'}")
        elif action.action == "advance_time":
            self.advance_time(action.milliseconds or 0)
            return self.state()
        self.resolve()
        return self.state()

    def advance_time(self, milliseconds: int) -> None:
        self.resolve()
        if self.powered and not self.tripped:
            self.elapsed_ms += milliseconds
            for definition in self.definition.timers:
                timer = self.timers[definition.timer_id]
                if timer.energized and not timer.completed:
                    before = timer.completed
                    timer.elapsed_ms = min(definition.delay_ms, timer.elapsed_ms + milliseconds)
                    timer.completed = timer.elapsed_ms >= definition.delay_ms
                    if timer.completed and not before:
                        self._event(f"{definition.label} 계시 완료")
        self.resolve()

    def _reset_outputs(self) -> None:
        self.coils = {key: False for key in self.coils}
        for timer in self.timers.values():
            timer.elapsed_ms = 0
            timer.completed = False
            timer.energized = False
        self.indicators = {key: "off" for key in self.indicators}
        self.motors = {key: "stopped" for key in self.motors}

    def reset(self) -> OperationSessionState:
        self.powered = False
        self.tripped = False
        self.elapsed_ms = 0
        self.controls = {item.control_id: item.initial_active for item in self.definition.controls}
        self.faults = []
        self.events = ["동작시험 초기화"]
        self._reset_outputs()
        self.resolve()
        return self.state()

    def state(self) -> OperationSessionState:
        timer_definitions = {item.timer_id: item for item in self.definition.timers}
        return OperationSessionState(
            session_id=self.session_id,
            problem_id=self.problem_id,
            wiring_attempt_id=self.wiring_attempt_id,
            powered=self.powered,
            power_state="tripped" if self.tripped else "on" if self.powered else "off",
            controls={
                item.control_id: ControlState(label=item.label, control_type=item.control_type, mode=item.mode, contact_type=item.contact_type, active=self.controls[item.control_id])
                for item in self.definition.controls
            },
            coils=dict(self.coils),
            contacts=dict(self.contacts),
            timers={
                timer_id: TimerState(
                    status="completed" if timer.completed else "timing" if timer.energized else "stopped",
                    elapsed_ms=timer.elapsed_ms,
                    delay_ms=timer_definitions[timer_id].delay_ms,
                )
                for timer_id, timer in self.timers.items()
            },
            indicators=dict(self.indicators),
            motors=dict(self.motors),
            faults=list(self.faults),
            stable=self.stable,
            elapsed_ms=self.elapsed_ms,
            events=list(self.events),
        )

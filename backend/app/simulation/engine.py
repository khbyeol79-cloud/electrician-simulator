from __future__ import annotations

from dataclasses import dataclass
from functools import wraps
from threading import RLock

from app.domain.operation_definition import (
    ControlState,
    FlasherState,
    FuseChannelState,
    InterlockState,
    LevelRelayState,
    OperationAction,
    OperationDefinition,
    OperationFault,
    OperationSessionState,
    ProtectionState,
    TimerState,
)
from app.domain.problem_definition import CircuitDefinition
from app.domain.wiring_attempt import WiringConnection

from .graph import ConductiveGraph


MAX_RESOLUTION_CYCLES = 50


class SimulationDefinitionError(ValueError):
    pass


def _serialized_action(method):
    @wraps(method)
    def synchronized(self, *args, **kwargs):
        with self._action_lock:
            return method(self, *args, **kwargs)
    return synchronized


@dataclass
class RuntimeTimer:
    elapsed_ms: int = 0
    completed: bool = False
    energized: bool = False


@dataclass
class RuntimeFlasher:
    elapsed_ms: int = 0
    phase_on: bool = False
    energized: bool = False


class OperationEngine:
    """승인 결선과 공개 문제 정의만 사용하는 결정적 논리 엔진."""

    def __init__(self, *, session_id: str, problem_id: str, wiring_attempt_id: int,
                 circuit: CircuitDefinition, definition: OperationDefinition,
                 connections: list[WiringConnection], terminal_aliases: dict[str, str] | None = None,
                 catalog_composed: bool = False,
                 composition_warnings: tuple[str, ...] | list[str] | None = None,
                 session_type: str = "verified_operation_session", workspace_id: str | None = None,
                 gradable: bool = True, safety_status: str = "not_checked",
                 power_permitted: bool = True, safety_issues: list | None = None):
        self._action_lock = RLock()
        self.session_id = session_id
        self.problem_id = problem_id
        self.wiring_attempt_id = wiring_attempt_id
        self.circuit = circuit
        self.definition = definition
        self.connections = connections
        self.terminal_aliases = terminal_aliases or {}
        self.catalog_composed = catalog_composed
        self.session_type = session_type
        self.workspace_id = workspace_id
        self.gradable = gradable
        self.safety_status = safety_status
        self.power_permitted = power_permitted
        self.safety_issues = list(safety_issues or [])
        self.definition_faults = [
            OperationFault(
                code=f"unverified_behavior_model:{index + 1}",
                message=message,
                severity="warning",
            )
            for index, message in enumerate(composition_warnings or [])
        ]
        self.powered = False
        self.tripped = False
        self.elapsed_ms = 0
        self.controls = {item.control_id: item.initial_active for item in definition.controls}
        self._transferring_selectors: set[str] = set()
        self.control_order = {item.control_id: 0 for item in definition.controls}
        self.event_sequence = 0
        self.coils = {item.coil_id: False for item in circuit.coils}
        self.contacts: dict[str, str] = {}
        self.timers = {item.timer_id: RuntimeTimer() for item in definition.timers}
        self.flashers = {item.flasher_id: RuntimeFlasher() for item in definition.flashers}
        self.level_inputs = {item.level_relay_id: False for item in definition.level_relays}
        self.level_outputs = {item.level_relay_id: False for item in definition.level_relays}
        self.level_powered = {item.level_relay_id: False for item in definition.level_relays}
        self.level_wiring_ready = {item.level_relay_id: False for item in definition.level_relays}
        self.indicators = {item.indicator_id: "off" for item in definition.indicators}
        self.audible_outputs = {item.output_id: "off" for item in definition.audible_outputs}
        self.motors = {item.motor_id: "stopped" for item in definition.motors}
        self.protection_status = {item.protection_device_id: "normal" for item in definition.protection_devices}
        self.protection_powered = {item.protection_device_id: False for item in definition.protection_devices}
        self.fuse_status = {item.channel_id: "normal" for item in definition.fuse_channels}
        self.interlock_runtime: dict[str, tuple[str, str | None]] = {
            item.interlock_id: ("ready", None) for item in definition.interlocks
        }
        self.faults: list[OperationFault] = []
        self.stable = True
        self.events: list[str] = ["동작시험 세션 시작"]
        self._validate_definition()
        self.resolve()

    def _validate_definition(self) -> None:
        coil_ids = set(self.coils)
        contact_ids = {item.contact_id for item in self.circuit.contacts}
        control_ids = set(self.controls)
        motor_ids = {item.motor_id for item in self.definition.motors}
        contactors = {item.contactor_id: item for item in self.definition.contactors}
        errors: list[str] = []
        for contact in self.circuit.contacts:
            if contact.controller_type == "coil" and contact.controller_id not in coil_ids:
                errors.append(f"접점 {contact.contact_id}의 코일 참조가 없습니다.")
            elif contact.controller_type == "timer" and contact.controller_id not in self.timers:
                errors.append(f"접점 {contact.contact_id}의 타이머 참조가 없습니다.")
            elif contact.controller_type == "flasher" and contact.controller_id not in self.flashers:
                errors.append(f"접점 {contact.contact_id}의 플리커 참조가 없습니다.")
            elif contact.controller_type == "level" and contact.controller_id not in self.level_outputs:
                errors.append(f"접점 {contact.contact_id}의 수위계전기 참조가 없습니다.")
            elif (
                contact.controller_type == "protection"
                and contact.controller_id not in self.protection_status
            ):
                errors.append(f"접점 {contact.contact_id}의 보호장치 참조가 없습니다.")
        for timer in self.definition.timers:
            if timer.coil_id not in coil_ids:
                errors.append(f"타이머 {timer.timer_id}의 코일 참조가 없습니다.")
            for contact_id in timer.timed_contact_ids:
                if contact_id not in contact_ids:
                    errors.append(f"타이머 접점 참조가 없습니다: {contact_id}")
        for flasher in self.definition.flashers:
            if flasher.coil_id not in coil_ids:
                errors.append(f"플리커 {flasher.flasher_id}의 코일 참조가 없습니다.")
            for contact_id in flasher.contact_ids:
                if contact_id not in contact_ids:
                    errors.append(f"플리커 접점 참조가 없습니다: {contact_id}")
        for level_relay in self.definition.level_relays:
            for contact_id in level_relay.contact_ids:
                if contact_id not in contact_ids:
                    errors.append(f"수위계전기 접점 참조가 없습니다: {contact_id}")
        for contactor in self.definition.contactors:
            if contactor.coil_id not in coil_ids:
                errors.append(f"전자접촉기 {contactor.contactor_id}의 코일 참조가 없습니다.")
            if contactor.start_control_id and contactor.start_control_id not in control_ids:
                errors.append(f"전자접촉기 {contactor.contactor_id}의 시작 입력 참조가 없습니다.")
            if contactor.motor_id and contactor.motor_id not in motor_ids:
                errors.append(f"전자접촉기 {contactor.contactor_id}의 모터 참조가 없습니다.")
        for interlock in self.definition.interlocks:
            for contactor_id in interlock.contactor_ids:
                if contactor_id not in contactors:
                    errors.append(f"인터록 대상 전자접촉기가 없습니다: {contactor_id}")
            for contact_id in interlock.contact_ids:
                if contact_id not in contact_ids:
                    errors.append(f"인터록 접점 참조가 없습니다: {contact_id}")
        for protection in self.definition.protection_devices:
            for coil_id in protection.protected_coil_ids:
                if coil_id not in coil_ids:
                    errors.append(f"보호 대상 코일이 없습니다: {coil_id}")
            for motor_id in protection.protected_motor_ids:
                if motor_id not in motor_ids:
                    errors.append(f"보호 대상 모터가 없습니다: {motor_id}")
        if len(control_ids) != len(self.definition.controls):
            errors.append("입력기구 ID가 중복되었습니다.")
        if len(contactors) != len(self.definition.contactors):
            errors.append("전자접촉기 ID가 중복되었습니다.")
        if errors:
            raise SimulationDefinitionError(" ".join(errors))

    def _timer_for_contact(self, contact_id: str) -> RuntimeTimer | None:
        for definition in self.definition.timers:
            if contact_id in definition.timed_contact_ids:
                return self.timers[definition.timer_id]
        return None

    def _contact_active(self, contact) -> bool:
        if contact.controller_type == "timer":
            return self.timers[contact.controller_id].completed
        if contact.controller_type == "flasher":
            flasher = self.flashers[contact.controller_id]
            return flasher.energized and flasher.phase_on
        if contact.controller_type == "level":
            return self.level_outputs[contact.controller_id]
        if contact.controller_type == "protection":
            return self.protection_status[contact.controller_id] != "normal"
        timer = self._timer_for_contact(contact.contact_id)
        return timer.completed if timer is not None else self.coils.get(contact.controller_id, False)

    def _conductive_graph(self) -> ConductiveGraph:
        graph = ConductiveGraph([(item.from_terminal, item.to) for item in self.connections])
        open_fuse_pairs = {
            frozenset((self._terminal(item.terminal_a_id), self._terminal(item.terminal_b_id)))
            for item in self.definition.fuse_channels
            if self.fuse_status.get(item.channel_id) == "open"
        }
        for item in self.definition.internal_connections:
            left, right = self._terminal(item.from_terminal), self._terminal(item.to)
            if frozenset((left, right)) not in open_fuse_pairs:
                graph.add(left, right)
        for control in self.definition.controls:
            if control.control_id in self._transferring_selectors:
                continue
            active = self.controls[control.control_id]
            if (
                control.control_type == "selector"
                and control.alternate_terminal_a_id
                and control.alternate_terminal_b_id
            ):
                if active:
                    graph.add(
                        self._terminal(control.terminal_a_id),
                        self._terminal(control.terminal_b_id),
                    )
                else:
                    graph.add(
                        self._terminal(control.alternate_terminal_a_id),
                        self._terminal(control.alternate_terminal_b_id),
                    )
                continue
            if active if control.contact_type == "NO" else not active:
                graph.add(self._terminal(control.terminal_a_id), self._terminal(control.terminal_b_id))
        for contact in self.circuit.contacts:
            active = self._contact_active(contact)
            if contact.contact_type == "CHANGEOVER":
                target = contact.no_terminal_id if active else contact.nc_terminal_id
                if target:
                    graph.add(self._terminal(contact.common_terminal_id), self._terminal(target))
            elif active if contact.contact_type == "NO" else not active:
                graph.add(self._terminal(contact.common_terminal_id), self._terminal(contact.switched_terminal_id))
        return graph

    def _terminal(self, terminal_id: str) -> str:
        return self.terminal_aliases.get(terminal_id, terminal_id)

    @staticmethod
    def _load_energized(graph: ConductiveGraph, line: str, returning: str,
                         terminal_a: str, terminal_b: str) -> bool:
        hot = graph.reachable(line)
        cold = graph.reachable(returning)
        return (terminal_a in hot and terminal_b in cold) or (terminal_b in hot and terminal_a in cold)

    def _detect_faults(self, graph: ConductiveGraph) -> list[OperationFault]:
        faults: list[OperationFault] = []
        power = self.definition.power
        if graph.connected(self._terminal(power.line_terminal_id), self._terminal(power.return_terminal_id)):
            faults.append(OperationFault(code="direct_short", message="전원과 복귀선의 직접 단락 경로가 감지되었습니다.", severity="danger", trip_required=True))
        phase_terminals = [self._terminal(item) for item in power.phase_terminal_ids]
        for index, first in enumerate(phase_terminals):
            for second in phase_terminals[index + 1:]:
                if graph.connected(first, second):
                    faults.append(OperationFault(code="phase_short", message="직접적인 상간 단락 경로가 감지되었습니다.", severity="danger", trip_required=True))
                    return faults
        return faults

    def _apply_interlocks(self, requested: dict[str, bool], previous: dict[str, bool]) -> dict[str, bool]:
        contactors = {item.contactor_id: item for item in self.definition.contactors}
        result = dict(requested)
        self.interlock_runtime = {item.interlock_id: ("ready", None) for item in self.definition.interlocks}
        for interlock in self.definition.interlocks:
            if (
                self.definition.simulation_mode == "actual_wiring"
                and interlock.type == "electrical"
            ):
                continue
            pair = [contactors[item] for item in interlock.contactor_ids if item in contactors]
            energized = [item for item in pair if result.get(item.coil_id, False)]
            if len(energized) < 2:
                continue
            previous_on = [item for item in pair if previous.get(item.coil_id, False)]
            keep = previous_on[0] if len(previous_on) == 1 else None
            if keep is None and self.definition.direction_change_policy in {"first_input_first", "current_direction_first"}:
                ordered = sorted(energized, key=lambda item: self.control_order.get(item.start_control_id or "", 0) or 10**12)
                if ordered and self.control_order.get(ordered[0].start_control_id or "", 0):
                    keep = ordered[0]
            blocked = "all"
            for item in energized:
                if keep is None or item.contactor_id != keep.contactor_id:
                    result[item.coil_id] = False
                    if keep is not None:
                        blocked = item.contactor_id
            self.interlock_runtime[interlock.interlock_id] = ("blocking", blocked)
            kind = "전기적" if interlock.type == "electrical" else "기계적"
            target = "동시 투입" if blocked == "all" else blocked
            self._event(f"{interlock.label}: {target}이 {kind} 인터록에 의해 차단되었습니다.")
        return result

    def _apply_protections(self, requested: dict[str, bool]) -> dict[str, bool]:
        result = dict(requested)
        if self.definition.simulation_mode == "actual_wiring":
            return result
        for protection in self.definition.protection_devices:
            if self.protection_status[protection.protection_device_id] != "normal":
                for coil_id in protection.protected_coil_ids:
                    result[coil_id] = False
        return result

    def _record_blocked_start(self, control_id: str) -> None:
        """기존 NC 접점이 먼저 차단한 시작 명령도 사용자 이벤트로 남긴다."""
        contactors = {item.contactor_id: item for item in self.definition.contactors}
        requested = next(
            (item for item in self.definition.contactors if item.start_control_id == control_id),
            None,
        )
        if requested is None or self.coils.get(requested.coil_id, False):
            return
        for interlock in self.definition.interlocks:
            if requested.contactor_id not in interlock.contactor_ids:
                continue
            other_active = any(
                contactor_id != requested.contactor_id
                and contactor_id in contactors
                and self.coils.get(contactors[contactor_id].coil_id, False)
                for contactor_id in interlock.contactor_ids
            )
            if not other_active:
                continue
            self.interlock_runtime[interlock.interlock_id] = ("blocking", requested.contactor_id)
            kind = "전기적" if interlock.type == "electrical" else "기계적"
            self._event(
                f"{interlock.label}: {requested.label}이(가) {kind} 인터록에 의해 차단되었습니다."
            )

    def _update_timer_energization(self) -> bool:
        timed_contact_changed = False
        for definition in self.definition.timers:
            timer = self.timers[definition.timer_id]
            energized = self.coils.get(definition.coil_id, False) and self.powered and not self.tripped
            if not energized and timer.energized and not definition.retentive:
                timed_contact_changed = timed_contact_changed or timer.completed
                timer.elapsed_ms = 0
                timer.completed = False
            timer.energized = energized
        return timed_contact_changed

    def _update_flasher_energization(self) -> bool:
        changed = False
        for definition in self.definition.flashers:
            flasher = self.flashers[definition.flasher_id]
            energized = self.coils.get(definition.coil_id, False) and self.powered and not self.tripped
            if energized != flasher.energized:
                changed = True
            if not energized:
                if flasher.elapsed_ms or flasher.phase_on:
                    changed = True
                flasher.elapsed_ms = 0
                flasher.phase_on = False
            flasher.energized = energized
        return changed

    def _update_level_relays(self, graph: ConductiveGraph) -> bool:
        changed = False
        line = self._terminal(self.definition.power.line_terminal_id)
        returning = self._terminal(self.definition.power.return_terminal_id)
        for definition in self.definition.level_relays:
            relay_id = definition.level_relay_id
            powered = bool(
                self.powered
                and not self.tripped
                and self._load_energized(
                    graph,
                    line,
                    returning,
                    self._terminal(definition.supply_terminal_a_id),
                    self._terminal(definition.supply_terminal_b_id),
                )
            )
            wiring_ready = all(
                graph.connected(self._terminal(internal), self._terminal(external))
                for internal, external in zip(
                    definition.electrode_terminal_ids,
                    definition.external_electrode_terminal_ids,
                    strict=True,
                )
            )
            detected = powered and wiring_ready and self.level_inputs[relay_id]
            if (
                powered != self.level_powered[relay_id]
                or wiring_ready != self.level_wiring_ready[relay_id]
                or detected != self.level_outputs[relay_id]
            ):
                changed = True
            self.level_powered[relay_id] = powered
            self.level_wiring_ready[relay_id] = wiring_ready
            self.level_outputs[relay_id] = detected
        return changed

    def resolve(self) -> None:
        initial = dict(self.coils)
        previous_iteration = dict(self.coils)
        seen: set[tuple[tuple[str, bool], ...]] = set()
        self.stable = True
        for _ in range(MAX_RESOLUTION_CYCLES):
            graph = self._conductive_graph()
            level_changed = self._update_level_relays(graph)
            if level_changed:
                graph = self._conductive_graph()
            immediate_faults = self._detect_faults(graph)
            if self.powered and any(item.trip_required for item in immediate_faults):
                self.tripped = True
                self.powered = False
            next_coils = {
                coil.coil_id: bool(
                    self.powered and not self.tripped and self._load_energized(
                        graph, self._terminal(self.definition.power.line_terminal_id),
                        self._terminal(self.definition.power.return_terminal_id),
                        self._terminal(coil.terminal_a_id), self._terminal(coil.terminal_b_id),
                    )
                ) for coil in self.circuit.coils
            }
            next_coils = self._apply_protections(next_coils)
            next_coils = self._apply_interlocks(next_coils, previous_iteration)
            signature = tuple(sorted(next_coils.items())) + tuple(
                (f"level:{key}", value) for key, value in sorted(self.level_outputs.items())
            )
            coils_changed = next_coils != self.coils
            if coils_changed:
                if signature in seen:
                    self.stable = False
                    self.faults = immediate_faults + [OperationFault(code="unstable_circuit", message="회로 상태가 안정되지 않았습니다. 결선 또는 회로 정의를 확인해 주세요.", severity="error", trip_required=True)]
                    self.powered = False
                    self.tripped = True
                    self.coils = {key: False for key in self.coils}
                    break
                seen.add(signature)
                previous_iteration = dict(self.coils)
                self.coils = next_coils
                continue
            flasher_changed = self._update_flasher_energization()
            if not level_changed and not flasher_changed:
                self.faults = immediate_faults
                break
        else:
            self.stable = False
            self.faults = [OperationFault(code="resolution_limit", message="회로 상태 계산의 최대 반복 횟수를 초과했습니다.", severity="error", trip_required=True)]
            self.powered = False
            self.tripped = True
            self.coils = {key: False for key in self.coils}
        if self._update_timer_energization():
            # 완료 접점이 복귀하면 해당 접점으로 여자된 코일까지 같은 사용자
            # 동작 사이클 안에서 다시 계산하여 실제 안정상태를 반환한다.
            self.resolve()
            return
        graph = self._conductive_graph()
        self._update_outputs(graph)
        self._update_contact_states()
        for coil_id, value in self.coils.items():
            if initial.get(coil_id) != value:
                self._event(f"{coil_id} {'여자' if value else '무여자'}")

    def _update_contact_states(self) -> None:
        for contact in self.circuit.contacts:
            active = self._contact_active(contact)
            closed = active if contact.contact_type == "NO" else not active if contact.contact_type == "NC" else True
            self.contacts[contact.contact_id] = "closed" if closed else "open"

    @staticmethod
    def _phase_parity(mapped: list[int], forward_order: list[int]) -> str:
        if len(mapped) != 3 or set(mapped) != {0, 1, 2}:
            return "invalid"
        relative = [forward_order.index(value) for value in mapped]
        inversions = sum(relative[i] > relative[j] for i in range(3) for j in range(i + 1, 3))
        return "forward" if inversions % 2 == 0 else "reverse"

    def _motor_is_protected(self, motor_id: str) -> bool:
        if self.definition.simulation_mode == "actual_wiring":
            return False
        return any(motor_id in item.protected_motor_ids and self.protection_status[item.protection_device_id] != "normal"
                   for item in self.definition.protection_devices)

    def _append_fault(self, fault: OperationFault) -> None:
        if not any(item.code == fault.code for item in self.faults):
            self.faults.append(fault)

    def _update_outputs(self, graph: ConductiveGraph) -> None:
        line = self._terminal(self.definition.power.line_terminal_id)
        returning = self._terminal(self.definition.power.return_terminal_id)
        for protection in self.definition.protection_devices:
            if protection.supply_terminal_a_id and protection.supply_terminal_b_id:
                supplied = bool(
                    self.powered and not self.tripped and self._load_energized(
                        graph, line, returning,
                        self._terminal(protection.supply_terminal_a_id),
                        self._terminal(protection.supply_terminal_b_id),
                    )
                )
            else:
                # Compatibility for reviewed training packages created before
                # protection supply terminals became explicit.
                supplied = bool(self.powered and not self.tripped)
            self.protection_powered[protection.protection_device_id] = supplied
        for item in self.definition.indicators:
            self.indicators[item.indicator_id] = "on" if self.powered and self._load_energized(graph, line, returning, self._terminal(item.terminal_a_id), self._terminal(item.terminal_b_id)) else "off"
        for item in self.definition.audible_outputs:
            self.audible_outputs[item.output_id] = "on" if self.powered and self._load_energized(graph, line, returning, self._terminal(item.terminal_a_id), self._terminal(item.terminal_b_id)) else "off"
        for motor in self.definition.motors:
            if self.definition.simulation_mode == "actual_wiring":
                self._update_actual_wiring_motor(graph, motor)
                continue
            forward = bool(motor.forward_coil_id and self.coils.get(motor.forward_coil_id))
            reverse = bool(motor.reverse_coil_id and self.coils.get(motor.reverse_coil_id))
            if self._motor_is_protected(motor.motor_id):
                self.motors[motor.motor_id] = "protection_trip"
                continue
            if forward and reverse:
                self.motors[motor.motor_id] = "simultaneous_fault"
                if not any(item.code == "simultaneous_contactor" for item in self.faults):
                    self.faults.append(OperationFault(code="simultaneous_contactor", message="정·역 전자접촉기가 동시에 여자되었습니다.", severity="danger", trip_required=True))
                continue
            mapped: list[int] = []
            if motor.phase_terminal_ids or motor.phase_source_terminal_ids:
                if len(motor.phase_terminal_ids) != 3 or len(motor.phase_source_terminal_ids) != 3:
                    self.motors[motor.motor_id] = "connection_error"
                    continue
                for terminal in motor.phase_terminal_ids:
                    matches = [index for index, source in enumerate(motor.phase_source_terminal_ids) if graph.connected(self._terminal(source), self._terminal(terminal))]
                    if len(matches) != 1:
                        mapped = []
                        break
                    mapped.append(matches[0])
            if (forward or reverse) and len(mapped) != 3:
                self.motors[motor.motor_id] = "phase_loss"
                code = f"motor_phase_loss:{motor.motor_id}"
                if not any(item.code == code for item in self.faults):
                    self.faults.append(OperationFault(code=code, message=f"{motor.label}의 결상 또는 상 연결 오류가 감지되었습니다.", severity="error"))
            elif forward or reverse:
                direction = self._phase_parity(mapped, motor.forward_phase_order)
                if direction == "invalid":
                    self.motors[motor.motor_id] = "phase_sequence_error"
                elif reverse:
                    self.motors[motor.motor_id] = "reverse" if direction == "forward" else "forward"
                else:
                    self.motors[motor.motor_id] = direction
            else:
                self.motors[motor.motor_id] = "stopped"
        if self.definition.simulation_mode == "actual_wiring":
            self._append_actual_wiring_diagnostics()

    def _phase_mapping(self, graph: ConductiveGraph, motor) -> tuple[list[int], bool]:
        if len(motor.phase_terminal_ids) != 3 or len(motor.phase_source_terminal_ids) != 3:
            return [], True
        mapped: list[int] = []
        ambiguous = False
        for terminal in motor.phase_terminal_ids:
            matches = [
                index
                for index, source in enumerate(motor.phase_source_terminal_ids)
                if graph.connected(self._terminal(source), self._terminal(terminal))
            ]
            if len(matches) > 1:
                ambiguous = True
            mapped.append(matches[0] if len(matches) == 1 else -1)
        return mapped, ambiguous

    def _update_actual_wiring_motor(self, graph: ConductiveGraph, motor) -> None:
        if not self.powered or self.tripped:
            self.motors[motor.motor_id] = "power_off"
            return
        mapped, ambiguous = self._phase_mapping(graph, motor)
        linked_contactors = [
            item for item in self.definition.contactors if item.motor_id == motor.motor_id
        ]
        energized = [item for item in linked_contactors if self.coils.get(item.coil_id, False)]
        if len(energized) > 1:
            self.motors[motor.motor_id] = "simultaneous_fault"
            self._append_fault(OperationFault(
                code="simultaneous_contactor",
                message="정·역 전자접촉기가 동시에 여자되었습니다.",
                severity="danger",
                trip_required=True,
            ))
            return
        if ambiguous:
            self.motors[motor.motor_id] = "connection_error"
            self._append_fault(OperationFault(
                code=f"motor_multiple_phases:{motor.motor_id}",
                message=f"{motor.label}의 한 단자에 둘 이상의 상이 연결되었습니다.",
                severity="danger",
                trip_required=True,
            ))
            return
        complete = len(mapped) == 3 and set(mapped) == {0, 1, 2}
        if complete:
            direction = self._phase_parity(mapped, motor.forward_phase_order)
            self.motors[motor.motor_id] = (
                direction if direction != "invalid" else "phase_sequence_error"
            )
            if linked_contactors and not energized:
                self._append_fault(OperationFault(
                    code=f"contactor_bypassed:{motor.motor_id}",
                    message=f"{motor.label}에 전자접촉기 주접점을 우회한 3상 경로가 있습니다.",
                    severity="danger",
                ))
            return
        if any(index >= 0 for index in mapped) or energized:
            self.motors[motor.motor_id] = "phase_loss"
            self._append_fault(OperationFault(
                code=f"motor_phase_loss:{motor.motor_id}",
                message=f"{motor.label}의 결상 또는 상 연결 오류가 감지되었습니다.",
                severity="error",
            ))
        elif self._motor_has_tripped_protection(motor.motor_id):
            self.motors[motor.motor_id] = "protection_trip"
        else:
            self.motors[motor.motor_id] = "stopped"

    def _motor_has_tripped_protection(self, motor_id: str) -> bool:
        return any(
            motor_id in item.protected_motor_ids
            and self.protection_status[item.protection_device_id] != "normal"
            for item in self.definition.protection_devices
        )

    def _append_actual_wiring_diagnostics(self) -> None:
        contactors = {item.contactor_id: item for item in self.definition.contactors}
        for interlock in self.definition.interlocks:
            if interlock.type != "electrical":
                continue
            pair = [contactors[item] for item in interlock.contactor_ids if item in contactors]
            energized = [item for item in pair if self.coils.get(item.coil_id, False)]
            if len(energized) > 1:
                self.interlock_runtime[interlock.interlock_id] = ("fault", "all")
                self._append_fault(OperationFault(
                    code=f"interlock_bypassed:{interlock.interlock_id}",
                    message=f"{interlock.label}의 NC 접점이 우회되어 두 접촉기가 동시에 여자되었습니다.",
                    severity="danger",
                    trip_required=True,
                ))
        for protection in self.definition.protection_devices:
            if self.protection_status[protection.protection_device_id] == "normal":
                continue
            coil_running = any(self.coils.get(coil_id, False) for coil_id in protection.protected_coil_ids)
            motor_running = any(
                self.motors.get(motor_id) in {"forward", "reverse"}
                for motor_id in protection.protected_motor_ids
            )
            if coil_running or motor_running:
                self._append_fault(OperationFault(
                    code=f"protection_bypassed:{protection.protection_device_id}",
                    message=f"{protection.label} 보호 접점을 우회한 운전 경로가 감지되었습니다.",
                    severity="danger",
                ))

    def _event(self, message: str) -> None:
        if not self.events or self.events[-1] != message:
            self.events.append(message)
            self.events = self.events[-50:]

    @_serialized_action
    def apply(self, action: OperationAction) -> OperationSessionState:
        pressed_control_id: str | None = None
        if action.action == "reset_operation":
            return self.reset()
        if action.action == "set_power":
            if action.value:
                if not self.power_permitted:
                    raise ValueError("차단 수준의 안전 문제가 있어 전원을 투입할 수 없습니다.")
                self.tripped = False
                self.powered = True
                self._event("전원을 투입했습니다.")
            else:
                self.powered = False
                self.tripped = False
                for protection in self.definition.protection_devices:
                    if protection.reset_mode == "automatic":
                        self.protection_status[protection.protection_device_id] = "normal"
                self._event("전원을 차단했습니다.")
                self._reset_outputs()
        elif action.action in {"press_control", "release_control", "toggle_control"}:
            definition = next((item for item in self.definition.controls if item.control_id == action.control_id), None)
            if definition is None:
                raise ValueError("존재하지 않는 입력기구입니다.")
            new_active = (
                not self.controls[definition.control_id]
                if action.action == "toggle_control" else action.action == "press_control"
            )
            if (
                definition.control_type == "selector"
                and definition.alternate_terminal_a_id
                and new_active != self.controls[definition.control_id]
            ):
                # Break-before-make: resolve the actual circuit with BOTH SS
                # paths open before closing the new path. Do not force coils
                # off: a real parallel/bypass supply must remain effective.
                self._transferring_selectors.add(definition.control_id)
                try:
                    self.resolve()
                finally:
                    self._transferring_selectors.remove(definition.control_id)
            if action.action == "toggle_control":
                if definition.mode != "maintained":
                    raise ValueError("유지형 입력기구만 상태를 전환할 수 있습니다.")
                self.controls[definition.control_id] = not self.controls[definition.control_id]
            else:
                self.controls[definition.control_id] = action.action == "press_control"
            if self.controls[definition.control_id]:
                self.event_sequence += 1
                self.control_order[definition.control_id] = self.event_sequence
                if action.action == "press_control":
                    pressed_control_id = definition.control_id
            self._event(f"{definition.label}을(를) {'눌렀습니다' if self.controls[definition.control_id] else '복귀했습니다'}.")
        elif action.action == "advance_time":
            self.advance_time(action.milliseconds or 0)
            return self.state()
        elif action.action == "trigger_fault":
            protection = next((item for item in self.definition.protection_devices if item.protection_device_id == action.target_id), None)
            if protection is None:
                raise ValueError("존재하지 않는 보호장치입니다.")
            if action.fault_type not in protection.allowed_fault_types:
                raise ValueError("현재 문제에서 허용되지 않은 고장 주입입니다.")
            if not self.protection_powered.get(protection.protection_device_id, False):
                raise ValueError("EOCR A1-A2에 전원이 공급되어야 과부하 시험을 할 수 있습니다.")
            if protection.protected_motor_ids and not any(
                self.motors.get(motor_id) in {"forward", "reverse"}
                for motor_id in protection.protected_motor_ids
            ):
                raise ValueError("전동기가 운전 중일 때만 EOCR 과부하 시험을 할 수 있습니다.")
            self.protection_status[protection.protection_device_id] = "reset_required" if protection.reset_mode in {"manual", "restart_required"} else "tripped"
            self._event(f"{protection.label}가 과부하로 트립되었습니다.")
        elif action.action == "reset_fault":
            protection = next((item for item in self.definition.protection_devices if item.protection_device_id == action.target_id), None)
            if protection is None:
                raise ValueError("존재하지 않는 보호장치입니다.")
            self.protection_status[protection.protection_device_id] = "normal"
            self._event(f"{protection.label}를 복귀했습니다.")
        elif action.action == "set_fuse_state":
            channel = next(
                (item for item in self.definition.fuse_channels if item.channel_id == action.target_id),
                None,
            )
            if channel is None:
                raise ValueError("존재하지 않는 FUSE 채널입니다.")
            self.fuse_status[channel.channel_id] = "normal" if action.value else "open"
            self._event(f"{channel.label}을(를) {'정상복구' if action.value else '단선'}했습니다.")
        elif action.action == "set_level":
            if action.target_id not in self.level_inputs:
                raise ValueError("존재하지 않는 수위계전기입니다.")
            self.level_inputs[action.target_id] = bool(action.value)
            self._event(
                f"{action.target_id} 수위 감지를 {'동작' if action.value else '해제'}했습니다."
            )
        self.resolve()
        if pressed_control_id is not None:
            self._record_blocked_start(pressed_control_id)
        return self.state()

    @_serialized_action
    def advance_time(self, milliseconds: int) -> None:
        if milliseconds < 0:
            raise ValueError("진행 시간은 음수일 수 없습니다.")
        self.resolve()
        remaining = milliseconds
        while remaining > 0 and self.powered and not self.tripped and self.stable:
            # Resolve every contact transition before advancing the next slice.
            # Otherwise a downstream timer misses time, and full flasher cycles
            # disappear when the caller advances more than one interval at once.
            deadlines = [remaining]
            for definition in self.definition.timers:
                timer = self.timers[definition.timer_id]
                if timer.energized and not timer.completed:
                    deadlines.append(definition.delay_ms - timer.elapsed_ms)
            for definition in self.definition.flashers:
                flasher = self.flashers[definition.flasher_id]
                if flasher.energized:
                    deadlines.append(definition.interval_ms - flasher.elapsed_ms)
            step = min(deadlines)
            self.elapsed_ms += step
            remaining -= step
            for definition in self.definition.timers:
                timer = self.timers[definition.timer_id]
                if timer.energized and not timer.completed:
                    before = timer.completed
                    timer.elapsed_ms = min(definition.delay_ms, timer.elapsed_ms + step)
                    timer.completed = timer.elapsed_ms >= definition.delay_ms
                    if timer.completed and not before:
                        self._event(f"{definition.label} 계시가 완료되었습니다.")
            for definition in self.definition.flashers:
                flasher = self.flashers[definition.flasher_id]
                if not flasher.energized:
                    continue
                total = flasher.elapsed_ms + step
                transitions, flasher.elapsed_ms = divmod(total, definition.interval_ms)
                if transitions % 2:
                    flasher.phase_on = not flasher.phase_on
                    self._event(
                        f"{definition.label} 출력이 {'ON' if flasher.phase_on else 'OFF'} 구간으로 전환되었습니다."
                    )
            self.resolve()
        self.resolve()

    def _reset_outputs(self) -> None:
        self.coils = {key: False for key in self.coils}
        for timer in self.timers.values():
            timer.elapsed_ms = 0
            timer.completed = False
            timer.energized = False
        for flasher in self.flashers.values():
            flasher.elapsed_ms = 0
            flasher.phase_on = False
            flasher.energized = False
        self.level_outputs = {key: False for key in self.level_outputs}
        self.level_powered = {key: False for key in self.level_powered}
        self.level_wiring_ready = {key: False for key in self.level_wiring_ready}
        self.indicators = {key: "off" for key in self.indicators}
        self.audible_outputs = {key: "off" for key in self.audible_outputs}
        self.motors = {key: "stopped" for key in self.motors}

    def reset(self) -> OperationSessionState:
        self.powered = False
        self.tripped = False
        self.elapsed_ms = 0
        self.controls = {item.control_id: item.initial_active for item in self.definition.controls}
        self.control_order = {item.control_id: 0 for item in self.definition.controls}
        self.protection_status = {item.protection_device_id: "normal" for item in self.definition.protection_devices}
        self.protection_powered = {item.protection_device_id: False for item in self.definition.protection_devices}
        self.fuse_status = {item.channel_id: "normal" for item in self.definition.fuse_channels}
        self.level_inputs = {item.level_relay_id: False for item in self.definition.level_relays}
        self.faults = []
        self.events = ["동작시험을 초기화했습니다."]
        self._reset_outputs()
        self.resolve()
        return self.state()

    @_serialized_action
    def state(self) -> OperationSessionState:
        timer_definitions = {item.timer_id: item for item in self.definition.timers}
        protections = {
            item.protection_device_id: ProtectionState(label=item.label, protection_type=item.protection_type,
                status=self.protection_status[item.protection_device_id], reset_mode=item.reset_mode,
                powered=self.protection_powered.get(item.protection_device_id, False),
                operating_state=(
                    "tripped" if self.protection_status[item.protection_device_id] != "normal"
                    else "powered_normal" if self.protection_powered.get(item.protection_device_id, False)
                    else "unpowered"
                ))
            for item in self.definition.protection_devices
        }
        fuses = {
            item.channel_id: FuseChannelState(
                label=item.label,
                status=self.fuse_status[item.channel_id],
                terminal_a_id=item.terminal_a_id,
                terminal_b_id=item.terminal_b_id,
            )
            for item in self.definition.fuse_channels
        }
        interlocks = {
            item.interlock_id: InterlockState(label=item.label, type=item.type,
                status=self.interlock_runtime.get(item.interlock_id, ("ready", None))[0],
                blocked_contactor_id=self.interlock_runtime.get(item.interlock_id, ("ready", None))[1])
            for item in self.definition.interlocks
        }
        return OperationSessionState(
            session_id=self.session_id, problem_id=self.problem_id, wiring_attempt_id=self.wiring_attempt_id,
            session_type=self.session_type,
            wiring_snapshot_id=self.wiring_attempt_id if self.session_type == "verified_operation_session" else None,
            workspace_id=self.workspace_id, gradable=self.gradable,
            safety_status=self.safety_status, power_permitted=self.power_permitted,
            safety_issues=self.safety_issues,
            simulation_mode=self.definition.simulation_mode,
            catalog_composed=self.catalog_composed,
            powered=self.powered, power_state="tripped" if self.tripped else "on" if self.powered else "off",
            controls={item.control_id: ControlState(label=item.label, control_type=item.control_type,
                mode=item.mode, contact_type=item.contact_type, active=self.controls[item.control_id])
                for item in self.definition.controls},
            coils=dict(self.coils), contacts=dict(self.contacts),
            changeover_positions={
                contact.contact_id: "no" if self._contact_active(contact) else "nc"
                for contact in self.circuit.contacts if contact.contact_type == "CHANGEOVER"
            },
            timers={timer_id: TimerState(status="completed" if timer.completed else "timing" if timer.energized else "stopped",
                elapsed_ms=timer.elapsed_ms, delay_ms=timer_definitions[timer_id].delay_ms)
                for timer_id, timer in self.timers.items()},
            flashers={
                item.flasher_id: FlasherState(
                    label=item.label,
                    status=(
                        "on" if self.flashers[item.flasher_id].phase_on
                        else "off" if self.flashers[item.flasher_id].energized
                        else "stopped"
                    ),
                    elapsed_ms=self.flashers[item.flasher_id].elapsed_ms,
                    interval_ms=item.interval_ms,
                )
                for item in self.definition.flashers
            },
            level_relays={
                item.level_relay_id: LevelRelayState(
                    label=item.label,
                    requested=self.level_inputs[item.level_relay_id],
                    powered=self.level_powered[item.level_relay_id],
                    wiring_ready=self.level_wiring_ready[item.level_relay_id],
                    detected=self.level_outputs[item.level_relay_id],
                )
                for item in self.definition.level_relays
            },
            indicators=dict(self.indicators), audible_outputs=dict(self.audible_outputs), motors=dict(self.motors), protections=protections,
            fuses=fuses,
            interlocks=interlocks,
            active_faults=[item.code for item in [*self.definition_faults, *self.faults]] + [key for key, value in self.protection_status.items() if value != "normal"],
            faults=[*self.definition_faults, *self.faults], stable=self.stable, elapsed_ms=self.elapsed_ms, events=list(self.events),
        )

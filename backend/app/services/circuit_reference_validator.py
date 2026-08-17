from __future__ import annotations

from collections import Counter
from typing import Iterable

from app.domain import AnswerDefinition, ProblemDefinition, ProblemValidationIssue
from app.services.catalog_service import CatalogService


class CircuitReferenceValidator:
    def __init__(self, catalog: CatalogService):
        self.catalog = catalog

    @staticmethod
    def _issue(code: str, message: str, field: str, problem_id: str):
        return ProblemValidationIssue(
            severity="error",
            code=code,
            message=message,
            file="problem.json" if not field.startswith("answer.") else "answer.json",
            field=field.removeprefix("answer."),
            problem_id=problem_id,
        )

    @staticmethod
    def _duplicates(values: Iterable[str]) -> set[str]:
        return {value for value, count in Counter(values).items() if count > 1}

    def validate(
        self, problem: ProblemDefinition, answer: AnswerDefinition
    ) -> list[ProblemValidationIssue]:
        issues: list[ProblemValidationIssue] = []
        problem_id = problem.problem_id
        circuit = problem.circuit

        id_groups = (
            ("duplicate_device_id", "장치 ID", "circuit.devices", [item.device_id for item in circuit.devices]),
            ("duplicate_terminal_id", "단자 ID", "circuit.terminals", [item.terminal_id for item in circuit.terminals]),
            ("duplicate_contact_id", "접점 ID", "circuit.contacts", [item.contact_id for item in circuit.contacts]),
            ("duplicate_coil_id", "코일 ID", "circuit.coils", [item.coil_id for item in circuit.coils]),
            ("duplicate_question_id", "질문 ID", "socket_questions", [item.question_id for item in problem.socket_questions]),
        )
        for code, label, field, values in id_groups:
            for duplicate in self._duplicates(values):
                issues.append(self._issue(code, f"{label}가 중복됩니다: {duplicate}", field, problem_id))

        devices = {item.device_id: item for item in circuit.devices}
        terminals = {item.terminal_id: item for item in circuit.terminals}
        external_terminal_ids = {
            terminal.terminal_id
            for device in (problem.wiring_semantics.external_devices if problem.wiring_semantics else [])
            for terminal in device.terminals
        }
        wiring_terminal_ids = {
            terminal
            for connection in answer.wiring_connections
            for terminal in (connection.from_terminal, connection.to)
        }
        contacts = {item.contact_id: item for item in circuit.contacts}
        coils = {item.coil_id: item for item in circuit.coils}
        questions = {item.question_id: item for item in problem.socket_questions}

        for index, device in enumerate(circuit.devices):
            field = f"circuit.devices.{index}"
            device_type = self.catalog.get_device_type(device.device_type_id)
            if device_type is None:
                issues.append(self._issue("unknown_device_type", f"존재하지 않는 장치 유형입니다: {device.device_type_id}", f"{field}.device_type_id", problem_id))
                continue
            if device.socket_type_id and self.catalog.get_socket_type(device.socket_type_id) is None:
                issues.append(self._issue("unknown_socket_type", f"존재하지 않는 소켓 유형입니다: {device.socket_type_id}", f"{field}.socket_type_id", problem_id))
            if device_type.socket_type_id != device.socket_type_id:
                issues.append(self._issue("incompatible_socket_type", f"장치 유형과 소켓 유형이 일치하지 않습니다: {device.device_id}", f"{field}.socket_type_id", problem_id))

        device_pin_pairs: list[tuple[str, int]] = []
        for index, terminal in enumerate(circuit.terminals):
            field = f"circuit.terminals.{index}"
            device = devices.get(terminal.device_id)
            if device is None:
                issues.append(self._issue("unknown_terminal_device", f"단자가 존재하지 않는 장치를 참조합니다: {terminal.device_id}", f"{field}.device_id", problem_id))
                continue
            if terminal.terminal_type == "socket_pin":
                if terminal.pin_number is None:
                    issues.append(self._issue("socket_pin_missing", "소켓 단자에는 핀 번호가 필요합니다.", f"{field}.pin_number", problem_id))
                else:
                    device_pin_pairs.append((terminal.device_id, terminal.pin_number))
                    socket = self.catalog.get_socket_type(device.socket_type_id or "")
                    if socket is None or terminal.pin_number not in socket.pins:
                        issues.append(self._issue("invalid_socket_pin", f"소켓에 존재하지 않는 핀 번호입니다: {terminal.pin_number}", f"{field}.pin_number", problem_id))
            elif terminal.pin_number is not None:
                issues.append(self._issue("unexpected_pin_number", "socket_pin이 아닌 단자에는 핀 번호를 지정할 수 없습니다.", f"{field}.pin_number", problem_id))
            if terminal.terminal_id == "PE" and terminal.electrical_role != "protective_earth":
                issues.append(self._issue("invalid_pe_role", "PE 단자는 protective_earth 역할이어야 합니다.", f"{field}.electrical_role", problem_id))
            if terminal.terminal_id in {"L1", "L2", "L3"} and terminal.electrical_role != "line":
                issues.append(self._issue("invalid_line_role", "L1·L2·L3 단자는 line 역할이어야 합니다.", f"{field}.electrical_role", problem_id))

        for device_id, pin in self._duplicates(device_pin_pairs):
            issues.append(self._issue("duplicate_device_pin", f"한 장치에서 핀 번호가 중복됩니다: {device_id}-{pin}", "circuit.terminals", problem_id))

        for index, coil in enumerate(circuit.coils):
            field = f"circuit.coils.{index}"
            if coil.owner_device_id not in devices:
                issues.append(self._issue("unknown_coil_owner", f"코일 소유 장치가 없습니다: {coil.owner_device_id}", f"{field}.owner_device_id", problem_id))
            for name, terminal_id in (("terminal_a_id", coil.terminal_a_id), ("terminal_b_id", coil.terminal_b_id)):
                if terminal_id not in terminals:
                    issues.append(self._issue("unknown_coil_terminal", f"코일 단자가 존재하지 않습니다: {terminal_id}", f"{field}.{name}", problem_id))
            if coil.terminal_a_id == coil.terminal_b_id:
                issues.append(self._issue("same_coil_terminals", "코일 양단은 서로 다른 단자여야 합니다.", field, problem_id))
            if coil.voltage_type == "AC" and coil.frequency is None:
                issues.append(self._issue("ac_frequency_missing", "AC 코일에는 주파수가 필요합니다.", f"{field}.frequency", problem_id))

        for index, contact in enumerate(circuit.contacts):
            field = f"circuit.contacts.{index}"
            if contact.owner_device_id not in devices:
                issues.append(self._issue("unknown_contact_owner", f"접점 소유 장치가 없습니다: {contact.owner_device_id}", f"{field}.owner_device_id", problem_id))
            referenced = [contact.common_terminal_id, contact.switched_terminal_id]
            referenced.extend(value for value in (contact.nc_terminal_id, contact.no_terminal_id) if value)
            for terminal_id in referenced:
                if terminal_id not in terminals:
                    issues.append(self._issue("unknown_contact_terminal", f"접점 단자가 존재하지 않습니다: {terminal_id}", field, problem_id))
            if contact.common_terminal_id == contact.switched_terminal_id:
                issues.append(self._issue("same_contact_terminals", "접점 양단은 서로 다른 단자여야 합니다.", field, problem_id))
            if contact.controlled_by_coil_id not in coils:
                issues.append(self._issue("unknown_contact_coil", f"접점을 제어하는 코일이 없습니다: {contact.controlled_by_coil_id}", f"{field}.controlled_by_coil_id", problem_id))
            expected_state = "open" if contact.contact_type == "NO" else "closed" if contact.contact_type == "NC" else None
            if expected_state and contact.normal_state != expected_state:
                issues.append(self._issue("invalid_contact_normal_state", f"{contact.contact_type} 접점의 기본 상태가 올바르지 않습니다.", f"{field}.normal_state", problem_id))

        for index, question in enumerate(problem.socket_questions):
            target = contacts if question.target_element_type == "contact" else coils
            if question.target_element_id not in target:
                issues.append(self._issue("unknown_question_target", f"질문 대상이 존재하지 않습니다: {question.target_element_id}", f"socket_questions.{index}.target_element_id", problem_id))
            slots = [slot.slot_id for slot in question.answer_slots]
            if self._duplicates(slots):
                issues.append(self._issue("duplicate_answer_slot", f"질문 슬롯 ID가 중복됩니다: {question.question_id}", f"socket_questions.{index}.answer_slots", problem_id))

        for question_id, slot_answers in answer.socket_pin_answers.items():
            question = questions.get(question_id)
            if question is None:
                issues.append(self._issue("unknown_answer_question", f"답안의 질문 ID가 문제에 없습니다: {question_id}", "answer.socket_pin_answers", problem_id))
                continue
            element = contacts.get(question.target_element_id) if question.target_element_type == "contact" else coils.get(question.target_element_id)
            owner_id = element.owner_device_id if element else None
            device = devices.get(owner_id or "")
            socket = self.catalog.get_socket_type(device.socket_type_id or "") if device else None
            valid_slots = {slot.slot_id for slot in question.answer_slots}
            for slot_id, pin in slot_answers.items():
                if slot_id not in valid_slots:
                    issues.append(self._issue("unknown_answer_slot", f"답안 슬롯이 문제에 없습니다: {question_id}.{slot_id}", "answer.socket_pin_answers", problem_id))
                if socket is None or pin not in socket.pins:
                    issues.append(self._issue("invalid_answer_pin", f"답안 핀 번호가 대상 소켓에 없습니다: {pin}", "answer.socket_pin_answers", problem_id))

        def check_terminal(terminal_id: str, code: str, field: str):
            if terminal_id not in terminals and terminal_id not in external_terminal_ids and terminal_id not in wiring_terminal_ids:
                issues.append(self._issue(code, f"답안이 존재하지 않는 단자를 참조합니다: {terminal_id}", f"answer.{field}", problem_id))

        for index, connection in enumerate(answer.required_connections):
            check_terminal(connection.from_terminal, "unknown_answer_terminal", f"required_connections.{index}.from")
            check_terminal(connection.to, "unknown_answer_terminal", f"required_connections.{index}.to")
        for index, net in enumerate(answer.expected_nets):
            for terminal_id in net.terminals:
                check_terminal(terminal_id, "unknown_expected_net_terminal", f"expected_nets.{index}.terminals")
                if terminal_id.startswith(("TB5-", "TB6-")):
                    issues.append(self._issue("free_junction_in_expected_net", "정답 네트워크에는 자유 TB 단자번호를 넣을 수 없습니다.", f"answer.expected_nets.{index}.terminals", problem_id))
        net_terminal_counts = Counter(terminal for net in answer.expected_nets for terminal in net.terminals)
        for terminal_id, count in net_terminal_counts.items():
            if count > 1:
                issues.append(self._issue("duplicate_expected_net_terminal", f"기능 단자가 여러 정답 네트워크에 중복됩니다: {terminal_id}", "answer.expected_nets", problem_id))
        if problem.wiring_semantics:
            external_ids = [
                terminal.terminal_id
                for device in problem.wiring_semantics.external_devices
                for terminal in device.terminals
            ]
            for duplicate in self._duplicates(external_ids):
                issues.append(self._issue("duplicate_external_terminal", f"외부 기구 단자 ID가 중복됩니다: {duplicate}", "wiring_semantics.external_devices", problem_id))
        for index, connection in enumerate(answer.forbidden_connections):
            check_terminal(connection.from_terminal, "unknown_forbidden_terminal", f"forbidden_connections.{index}.from")
            check_terminal(connection.to, "unknown_forbidden_terminal", f"forbidden_connections.{index}.to")

        operation = problem.operation
        if operation is not None:
            control_ids = {item.control_id for item in operation.controls}
            motor_ids = {item.motor_id for item in operation.motors}
            contactor_ids = {item.contactor_id for item in operation.contactors}
            protection_ids = {item.protection_device_id for item in operation.protection_devices}
            operation_id_groups = (
                ("duplicate_operation_control_id", "조작기구 ID", "operation.controls", [item.control_id for item in operation.controls]),
                ("duplicate_operation_motor_id", "모터 ID", "operation.motors", [item.motor_id for item in operation.motors]),
                ("duplicate_operation_contactor_id", "전자접촉기 ID", "operation.contactors", [item.contactor_id for item in operation.contactors]),
                ("duplicate_operation_interlock_id", "인터록 ID", "operation.interlocks", [item.interlock_id for item in operation.interlocks]),
                ("duplicate_operation_protection_id", "보호장치 ID", "operation.protection_devices", [item.protection_device_id for item in operation.protection_devices]),
            )
            for code, label, field, values in operation_id_groups:
                for duplicate in self._duplicates(values):
                    issues.append(self._issue(code, f"{label}가 중복됩니다: {duplicate}", field, problem_id))

            def check_operation_terminal(terminal_id: str, field: str):
                if terminal_id not in terminals:
                    issues.append(self._issue("unknown_operation_terminal", f"동작 정의가 존재하지 않는 단자를 참조합니다: {terminal_id}", field, problem_id))

            check_operation_terminal(operation.power.line_terminal_id, "operation.power.line_terminal_id")
            check_operation_terminal(operation.power.return_terminal_id, "operation.power.return_terminal_id")
            for terminal_id in operation.power.phase_terminal_ids:
                check_operation_terminal(terminal_id, "operation.power.phase_terminal_ids")
            for index, control in enumerate(operation.controls):
                check_operation_terminal(control.terminal_a_id, f"operation.controls.{index}.terminal_a_id")
                check_operation_terminal(control.terminal_b_id, f"operation.controls.{index}.terminal_b_id")
            for index, indicator in enumerate(operation.indicators):
                check_operation_terminal(indicator.terminal_a_id, f"operation.indicators.{index}.terminal_a_id")
                check_operation_terminal(indicator.terminal_b_id, f"operation.indicators.{index}.terminal_b_id")
            for index, motor in enumerate(operation.motors):
                for coil_id in (motor.forward_coil_id, motor.reverse_coil_id):
                    if coil_id and coil_id not in coils:
                        issues.append(self._issue("unknown_operation_motor_coil", f"모터가 존재하지 않는 코일을 참조합니다: {coil_id}", f"operation.motors.{index}", problem_id))
                for terminal_id in motor.phase_terminal_ids + motor.phase_source_terminal_ids:
                    check_operation_terminal(terminal_id, f"operation.motors.{index}")
            for index, pair in enumerate(operation.internal_connections):
                check_operation_terminal(pair.from_terminal, f"operation.internal_connections.{index}.from")
                check_operation_terminal(pair.to, f"operation.internal_connections.{index}.to")
            for index, contactor in enumerate(operation.contactors):
                if contactor.coil_id not in coils:
                    issues.append(self._issue("unknown_operation_contactor_coil", f"전자접촉기가 존재하지 않는 코일을 참조합니다: {contactor.coil_id}", f"operation.contactors.{index}.coil_id", problem_id))
                if contactor.start_control_id and contactor.start_control_id not in control_ids:
                    issues.append(self._issue("unknown_operation_start_control", f"전자접촉기가 존재하지 않는 시작 입력을 참조합니다: {contactor.start_control_id}", f"operation.contactors.{index}.start_control_id", problem_id))
                if contactor.motor_id and contactor.motor_id not in motor_ids:
                    issues.append(self._issue("unknown_operation_contactor_motor", f"전자접촉기가 존재하지 않는 모터를 참조합니다: {contactor.motor_id}", f"operation.contactors.{index}.motor_id", problem_id))
            for index, interlock in enumerate(operation.interlocks):
                for contactor_id in interlock.contactor_ids:
                    if contactor_id not in contactor_ids:
                        issues.append(self._issue("unknown_operation_interlock_contactor", f"인터록 대상 전자접촉기가 없습니다: {contactor_id}", f"operation.interlocks.{index}.contactor_ids", problem_id))
                for contact_id in interlock.contact_ids:
                    contact = contacts.get(contact_id)
                    if contact is None:
                        issues.append(self._issue("unknown_operation_interlock_contact", f"인터록 접점이 없습니다: {contact_id}", f"operation.interlocks.{index}.contact_ids", problem_id))
                    elif interlock.type == "electrical" and contact.contact_type != "NC":
                        issues.append(self._issue("invalid_electrical_interlock_contact", f"전기적 인터록 접점은 NC여야 합니다: {contact_id}", f"operation.interlocks.{index}.contact_ids", problem_id))
            for index, protection in enumerate(operation.protection_devices):
                for coil_id in protection.protected_coil_ids:
                    if coil_id not in coils:
                        issues.append(self._issue("unknown_operation_protected_coil", f"보호 대상 코일이 없습니다: {coil_id}", f"operation.protection_devices.{index}.protected_coil_ids", problem_id))
                for motor_id in protection.protected_motor_ids:
                    if motor_id not in motor_ids:
                        issues.append(self._issue("unknown_operation_protected_motor", f"보호 대상 모터가 없습니다: {motor_id}", f"operation.protection_devices.{index}.protected_motor_ids", problem_id))

            for test_index, test in enumerate(answer.operation_tests):
                for step_index, step in enumerate(test.get("steps", [])):
                    action = step.get("action")
                    if action in {"press_control", "release_control", "toggle_control"} and step.get("control_id") not in control_ids:
                        issues.append(self._issue("unknown_operation_test_control", f"자동시험 입력기구가 없습니다: {step.get('control_id')}", f"answer.operation_tests.{test_index}.steps.{step_index}", problem_id))
                    if action in {"trigger_fault", "reset_fault"} and step.get("target_id") not in protection_ids:
                        issues.append(self._issue("unknown_operation_test_protection", f"자동시험 보호장치가 없습니다: {step.get('target_id')}", f"answer.operation_tests.{test_index}.steps.{step_index}", problem_id))
        return issues

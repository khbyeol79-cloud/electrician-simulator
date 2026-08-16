from __future__ import annotations

from collections import Counter

from app.domain import ProblemDefinition, ProblemValidationIssue, SchematicDiagram


class DiagramReferenceValidator:
    @staticmethod
    def _issue(code: str, message: str, field: str, problem_id: str):
        return ProblemValidationIssue(
            severity="error", code=code, message=message, file="diagram.json",
            field=field, problem_id=problem_id,
        )

    def validate(self, problem: ProblemDefinition, diagram: SchematicDiagram):
        issues: list[ProblemValidationIssue] = []
        pid = problem.problem_id
        circuit = problem.circuit

        def duplicates(values):
            return {value for value, count in Counter(values).items() if count > 1}

        groups = (
            ("duplicate_section_id", "구역", [x.section_id for x in diagram.sections], "sections"),
            ("duplicate_diagram_element_id", "요소", [x.element_id for x in diagram.elements], "elements"),
            ("duplicate_conductor_id", "회로선", [x.conductor_id for x in diagram.conductors], "conductors"),
        )
        for code, label, values, field in groups:
            for value in duplicates(values):
                issues.append(self._issue(code, f"{label} ID가 중복됩니다: {value}", field, pid))

        view = diagram.view_box
        min_x, min_y = view.x, view.y
        max_x, max_y = view.x + view.width, view.y + view.height
        section_ids = {x.section_id for x in diagram.sections}
        refs = {
            "device": {x.device_id for x in circuit.devices},
            "terminal": {x.terminal_id for x in circuit.terminals},
            "contact": {x.contact_id for x in circuit.contacts},
            "coil": {x.coil_id for x in circuit.coils},
        }
        questions = {x.question_id: x for x in problem.socket_questions}
        question_elements: Counter[str] = Counter()

        def point_ok(x: float, y: float) -> bool:
            return min_x <= x <= max_x and min_y <= y <= max_y

        for index, section in enumerate(diagram.sections):
            b = section.bounds
            if not point_ok(b.x, b.y) or not point_ok(b.x + b.width, b.y + b.height):
                issues.append(self._issue("section_out_of_viewbox", "구역이 viewBox 범위를 벗어납니다.", f"sections.{index}.bounds", pid))

        for index, element in enumerate(diagram.elements):
            field = f"elements.{index}"
            if element.section_id not in section_ids:
                issues.append(self._issue("unknown_diagram_section", f"존재하지 않는 구역입니다: {element.section_id}", f"{field}.section_id", pid))
            if not point_ok(element.x, element.y) or not point_ok(element.x + element.width, element.y + element.height):
                issues.append(self._issue("element_out_of_viewbox", "회로 요소가 viewBox 범위를 벗어납니다.", field, pid))
            if bool(element.circuit_ref_type) != bool(element.circuit_ref_id):
                issues.append(self._issue("incomplete_circuit_reference", "회로 참조 유형과 ID를 함께 입력해야 합니다.", field, pid))
            elif element.circuit_ref_type and element.circuit_ref_id not in refs[element.circuit_ref_type]:
                issues.append(self._issue("unknown_diagram_reference", f"존재하지 않는 회로 요소 참조입니다: {element.circuit_ref_id}", f"{field}.circuit_ref_id", pid))
            if element.question_id:
                question_elements[element.question_id] += 1
                question = questions.get(element.question_id)
                if question is None:
                    issues.append(self._issue("unknown_diagram_question", f"존재하지 않는 질문입니다: {element.question_id}", f"{field}.question_id", pid))
                elif element.circuit_ref_id != question.target_element_id:
                    issues.append(self._issue("diagram_question_target_mismatch", "질문 대상과 SVG 요소 참조가 일치하지 않습니다.", field, pid))
            if element.interactive and not element.question_id:
                issues.append(self._issue("interactive_question_missing", "선택 가능한 요소에는 질문 ID가 필요합니다.", f"{field}.question_id", pid))

        for question_id in questions:
            count = question_elements[question_id]
            if count == 0:
                issues.append(self._issue("question_diagram_element_missing", f"질문 대상이 diagram에 없습니다: {question_id}", "elements", pid))
            elif count > 1:
                issues.append(self._issue("duplicate_question_diagram_element", f"한 질문이 여러 SVG 요소에 연결되었습니다: {question_id}", "elements", pid))

        for index, conductor in enumerate(diagram.conductors):
            field = f"conductors.{index}"
            if conductor.section_id not in section_ids:
                issues.append(self._issue("unknown_conductor_section", f"존재하지 않는 구역입니다: {conductor.section_id}", f"{field}.section_id", pid))
            for point_index, point in enumerate(conductor.points):
                if not point_ok(point.x, point.y):
                    issues.append(self._issue("conductor_out_of_viewbox", "회로선이 viewBox를 벗어납니다.", f"{field}.points.{point_index}", pid))
            for a, b in zip(conductor.points, conductor.points[1:]):
                if a.x != b.x and a.y != b.y:
                    issues.append(self._issue("diagonal_conductor", "회로선은 수평·수직 선분만 사용할 수 있습니다.", f"{field}.points", pid))
                    break
        return issues

from __future__ import annotations

from collections import Counter, defaultdict

from app.domain import CaptureConnection, StructuralWarning, WiringConnection
from app.services.practice_safety_service import PracticeSafetyService


class WiringCaptureService:
    """Answer-independent validation for saveable, user-owned wiring drafts."""

    def inspect(self, package, connections: list[CaptureConnection]) -> list[StructuralWarning]:
        pins = {pin.terminal_id: pin for item in package.board.items for pin in item.pins}
        external = {
            terminal.terminal_id: terminal
            for device in (package.problem.wiring_semantics.external_devices if package.problem.wiring_semantics else [])
            for terminal in device.terminals
        }
        terminals = pins | external
        warnings: list[StructuralWarning] = []
        valid_indexes: set[int] = set()
        endpoint_counts: Counter[str] = Counter()
        side_counts: dict[str, Counter[str]] = defaultdict(Counter)
        seen: dict[tuple[str, str], int] = {}

        for index, connection in enumerate(connections):
            endpoints = (connection.from_terminal, connection.to)
            missing = [terminal for terminal in endpoints if terminal not in terminals]
            if missing:
                warnings.append(StructuralWarning(
                    code="terminal_outside_problem",
                    message=f"현재 문제에 존재하지 않는 단자가 포함되어 있습니다: {', '.join(missing)}",
                    connection_indexes=[index],
                ))
                continue
            disabled = [terminal for terminal in endpoints if not getattr(terminals[terminal], "enabled", True)]
            if disabled:
                warnings.append(StructuralWarning(
                    code="disabled_terminal",
                    message=f"현재 문제에서 사용할 수 없는 단자가 포함되어 있습니다: {', '.join(disabled)}",
                    connection_indexes=[index],
                ))
            if connection.from_terminal == connection.to:
                warnings.append(StructuralWarning(
                    code="self_connection", message="같은 단자를 서로 연결한 전선이 있습니다.",
                    connection_indexes=[index],
                ))
                continue
            if connection.key in seen:
                warnings.append(StructuralWarning(
                    code="duplicate_connection", message="완전히 동일한 단자 연결이 중복되었습니다.",
                    connection_indexes=[seen[connection.key], index],
                ))
            else:
                seen[connection.key] = index
            valid_indexes.add(index)
            for terminal in endpoints:
                endpoint_counts[terminal] += 1
                if terminal in pins and pins[terminal].terminal_role == "free_junction":
                    other = endpoints[1] if terminal == endpoints[0] else endpoints[0]
                    side_counts[terminal]["external" if other in external else "internal"] += 1

        for terminal, count in endpoint_counts.items():
            pin = terminals[terminal]
            if terminal in side_counts:
                for side, side_count in side_counts[terminal].items():
                    if side_count > pin.max_connections:
                        side_label = "외부측" if side == "external" else "내부측"
                        warnings.append(StructuralWarning(
                            code="terminal_capacity_exceeded",
                            message=f"{terminal} 단자의 {side_label} 최대 연결 수({pin.max_connections})를 초과했습니다.",
                        ))
            elif count > pin.max_connections:
                warnings.append(StructuralWarning(
                    code="terminal_capacity_exceeded",
                    message=f"{terminal} 단자의 최대 연결 수({pin.max_connections})를 초과했습니다.",
                ))

        strict_connections = [
            WiringConnection.model_validate(connection.model_dump(by_alias=True, mode="json"))
            for index, connection in enumerate(connections)
            if index in valid_indexes and connection.from_terminal != connection.to
        ]
        _, safety_issues = PracticeSafetyService().inspect(package, strict_connections)
        warnings.extend(StructuralWarning(
            code=issue.code, message=issue.message, severity=issue.severity
        ) for issue in safety_issues)
        return warnings

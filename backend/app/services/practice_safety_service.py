from __future__ import annotations

from app.domain import PracticeSafetyIssue


class PracticeSafetyService:
    """Answer-independent sanity checks for an ungraded user-owned draft."""

    def inspect(self, package, connections, *, circuit=None, operation=None):
        parent: dict[str, str] = {}

        def find(item: str) -> str:
            parent.setdefault(item, item)
            if parent[item] != item:
                parent[item] = find(parent[item])
            return parent[item]

        def union(left: str, right: str):
            left_root, right_root = find(left), find(right)
            if left_root != right_root:
                parent[right_root] = left_root

        for connection in connections:
            union(*connection.key)
        linked = lambda left, right: left in parent and right in parent and find(left) == find(right)
        issues: list[PracticeSafetyIssue] = []
        operation = operation or package.problem.operation
        circuit = circuit or package.problem.circuit
        if operation:
            phases = operation.power.phase_terminal_ids
            for index, left in enumerate(phases):
                for right in phases[index + 1:]:
                    if linked(left, right):
                        issues.append(PracticeSafetyIssue(code="phase_short", severity="blocking", message=f"전원 상간 단락 가능성이 있습니다: {left}–{right}"))
            if linked(operation.power.line_terminal_id, operation.power.return_terminal_id):
                issues.append(PracticeSafetyIssue(code="line_return_short", severity="blocking", message="제어 전원 선간 직접 단락 가능성이 있습니다."))
            for control in operation.controls:
                if control.contact_type == "NC" and linked(control.terminal_a_id, control.terminal_b_id):
                    issues.append(PracticeSafetyIssue(code=f"control_bypass:{control.control_id}", severity="warning", message=f"{control.label} 접점 우회 가능성을 확인하세요."))
            for left, right in (("F-1", "F-2"), ("F-3", "F-4")):
                if linked(left, right):
                    issues.append(PracticeSafetyIssue(code=f"fuse_bypass:{left}:{right}", severity="warning", message=f"FUSE {left[-1]}–{right[-1]} 보호 경로 우회 가능성을 확인하세요."))
            interlock_contacts = {contact_id for item in operation.interlocks for contact_id in item.contact_ids}
            protection_contacts = {contact_id for item in operation.protection_devices for contact_id in item.protection_contact_ids}
            timed_contacts = {contact_id for item in operation.timers for contact_id in item.timed_contact_ids}
            for contact in circuit.contacts:
                terminals = [contact.common_terminal_id, contact.switched_terminal_id]
                if len(terminals) == 2 and linked(*terminals):
                    if contact.contact_id in protection_contacts:
                        label = "EOCR 보호접점"
                    elif contact.contact_id in timed_contacts:
                        label = "타이머 접점"
                    elif contact.contact_id in interlock_contacts:
                        label = "인터록 접점"
                    else:
                        continue
                    issues.append(PracticeSafetyIssue(code=f"contact_bypass:{contact.contact_id}", severity="warning", message=f"{label} 우회 가능성을 확인하세요: {contact.contact_id}"))
        if any(linked(left, right) for left in ("F-1", "F-2") for right in ("F-3", "F-4")):
            issues.append(PracticeSafetyIssue(code="dual_fuse_channel_merge", severity="blocking", message="FUSE 독립회로 1–2와 3–4가 서로 합쳐졌습니다."))
        if any(item.severity == "blocking" for item in issues):
            return "blocked", issues
        return ("attention" if issues else "safe"), issues

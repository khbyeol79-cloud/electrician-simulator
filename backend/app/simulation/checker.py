from __future__ import annotations

from app.domain.operation_definition import OperationAction, OperationDefinition, OperationSessionState
from app.domain.problem_definition import CircuitDefinition
from app.domain.wiring_attempt import WiringConnection

from .engine import OperationEngine, SimulationDefinitionError


def matches_expectation(state: OperationSessionState, expected: dict) -> bool:
    payload = state.model_dump(mode="json")
    for group, value in expected.items():
        actual = payload.get(group)
        if isinstance(value, dict):
            if not isinstance(actual, dict):
                return False
            for key, expected_value in value.items():
                actual_value = actual.get(key)
                if isinstance(expected_value, dict):
                    if not isinstance(actual_value, dict) or any(
                        actual_value.get(nested_key) != nested_value
                        for nested_key, nested_value in expected_value.items()
                    ):
                        return False
                elif actual_value != expected_value:
                    return False
        elif actual != value:
            return False
    return True


def passes_operation_requirements(
    *,
    circuit: CircuitDefinition,
    definition: OperationDefinition,
    connections: list[WiringConnection],
    tests: list[dict],
    terminal_aliases: dict[str, str] | None = None,
) -> bool:
    if not tests:
        return False
    for test in tests:
        try:
            engine = OperationEngine(
                session_id="structural-grade-check",
                problem_id="private-check",
                wiring_attempt_id=0,
                circuit=circuit,
                definition=definition,
                connections=connections,
                terminal_aliases=terminal_aliases,
            )
            for step in test.get("steps", []):
                action_payload = {key: value for key, value in step.items() if key != "expect"}
                state = engine.apply(OperationAction.model_validate(action_payload))
                if not matches_expectation(state, step.get("expect", {})):
                    return False
        except (ValueError, SimulationDefinitionError):
            return False
    return True

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "tests"))

from app.domain import OperationAction  # noqa: E402
from app.simulation import OperationEngine  # noqa: E402
from actual_wiring_test_utils import actual_connections, compose_actual  # noqa: E402


def make_engine(**options) -> OperationEngine:
    runtime = compose_actual()
    return OperationEngine(
        session_id="manual-demo",
        problem_id="free:manual-demo",
        wiring_attempt_id=0,
        circuit=runtime.circuit,
        definition=runtime.operation,
        connections=actual_connections(**options),
        catalog_composed=runtime.catalog_composed,
        composition_warnings=runtime.warnings,
    )


def start(engine: OperationEngine):
    engine.apply(OperationAction(action="set_power", value=True))
    engine.apply(OperationAction(action="press_control", control_id="PB1"))
    return engine.apply(OperationAction(action="release_control", control_id="PB1"))


def check(label: str, actual, expected) -> None:
    result = "통과" if actual == expected else "실패"
    print(f"[{result}] {label}: {actual} (예상: {expected})")
    if actual != expected:
        raise SystemExit(1)


def main() -> int:
    print("0.11.1 실제 결선 기반 동작 엔진 간단 시험")
    print("- 정답 데이터와 expected_nets를 사용하지 않습니다.\n")

    normal = make_engine()
    running = start(normal)
    check("MC1 자기유지", running.coils["MC1-COIL"], True)
    check("정상 상 순서", running.motors["M1"], "forward")
    stopped = normal.apply(OperationAction(action="press_control", control_id="PB0"))
    check("STOP PB", stopped.coils["MC1-COIL"], False)
    check("STOP 후 모터", stopped.motors["M1"], "stopped")

    swapped = start(make_engine(swap_phases=True))
    check("두 상 교환", swapped.motors["M1"], "reverse")

    missing = start(make_engine(missing_phase=True))
    check("한 상 누락", missing.motors["M1"], "phase_loss")

    protected = make_engine()
    start(protected)
    tripped = protected.apply(OperationAction(
        action="trigger_fault", target_id="EOCR", fault_type="overload"
    ))
    check("EOCR 95-96 직렬 보호", tripped.coils["MC1-COIL"], False)
    check("EOCR 97-98 경보 표시등", tripped.indicators["AL"], "on")
    check("EOCR 트립 후 모터", tripped.motors["M1"], "protection_trip")

    bypassed = make_engine(bypass_eocr=True)
    start(bypassed)
    unsafe = bypassed.apply(OperationAction(
        action="trigger_fault", target_id="EOCR", fault_type="overload"
    ))
    check("EOCR 우회 시 실제 코일 상태", unsafe.coils["MC1-COIL"], True)
    bypass_fault = any(
        code.startswith("protection_bypassed:EOCR") for code in unsafe.active_faults
    )
    check("EOCR 우회 위험 진단", bypass_fault, True)

    print("\n모든 간단 시험이 통과했습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

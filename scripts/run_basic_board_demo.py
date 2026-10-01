from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.api.free_circuit import _new_workspace_id, _workspace_from_template  # noqa: E402
from app.database import SQLiteDatabase  # noqa: E402
from app.domain import OperationAction, WiringConnection  # noqa: E402
from app.repositories import ProblemRepository  # noqa: E402
from app.repositories.free_circuit_repository import FreeCircuitRepository  # noqa: E402
from app.services import DeviceBehaviorRuntimeComposer  # noqa: E402
from app.services.free_circuit_template_service import (  # noqa: E402
    BASIC_BOARD_TEMPLATE_ID,
    FreeCircuitTemplateService,
)
from app.simulation import OperationEngine  # noqa: E402


def wire(left: str, right: str, color: str = "yellow") -> WiringConnection:
    return WiringConnection.model_validate({"from": left, "to": right, "wire_color": color})


def make_engine(runtime, pairs: list[tuple[str, str, str]]) -> OperationEngine:
    return OperationEngine(
        session_id="basic-board-demo",
        problem_id="free:basic-board-demo",
        wiring_attempt_id=0,
        circuit=runtime.circuit,
        definition=runtime.operation,
        connections=[wire(*item) for item in pairs],
        catalog_composed=runtime.catalog_composed,
        composition_warnings=runtime.warnings,
    )


def self_hold_connections(include_hold: bool = True) -> list[tuple[str, str, str]]:
    result = [
        ("PWR-L", "TB5-01", "brown"), ("PB0-1", "TB5-01", "yellow"),
        ("PB0-2", "TB5-02", "yellow"), ("PB1-1", "TB5-02", "yellow"),
        ("PB1-2", "TB5-03", "yellow"), ("X1-2", "TB5-03", "yellow"),
        ("X1-7", "TB6-01", "yellow"), ("PWR-N", "TB6-01", "black"),
    ]
    if include_hold:
        result += [("X1-1", "TB5-02", "yellow"), ("X1-3", "TB5-03", "yellow")]
    return result


def timer_connections() -> list[tuple[str, str, str]]:
    return [
        ("PWR-L", "TB5-01", "brown"), ("T1-2", "TB5-01", "yellow"),
        ("T1-8", "TB5-01", "yellow"), ("PWR-N", "TB6-01", "black"),
        ("GL-2", "TB6-01", "yellow"), ("T1-7", "TB6-01", "yellow"),
        ("T1-6", "TB6-02", "yellow"), ("GL-1", "TB6-02", "yellow"),
    ]


def motor_connections(*, swap: bool = False, missing: bool = False,
                      bypass_eocr: bool = False) -> list[tuple[str, str, str]]:
    phases = ["PWR-L1", "PWR-L3", "PWR-L2"] if swap else ["PWR-L1", "PWR-L2", "PWR-L3"]
    result = [
        ("PWR-L", "EOCR-95", "brown"), ("EOCR-96", "PB0-1", "yellow"),
        ("PB0-2", "PB1-1", "yellow"),
        ("PB1-2", "MC1-6", "yellow"), ("MC1-12", "PWR-N", "yellow"),
        ("PB1-1", "MC1-4", "yellow"),
        ("MC1-10", "PB1-2", "yellow"),
        ("EOCR-98", "RL-1", "yellow"), ("RL-2", "PWR-N", "yellow"),
        (phases[0], "MC1-1", "brown"), (phases[1], "MC1-2", "black"),
        (phases[2], "MC1-3", "gray"), ("MC1-7", "EOCR-L1", "brown"),
        ("MC1-8", "EOCR-L2", "black"), ("MC1-9", "EOCR-L3", "gray"),
        ("EOCR-U", "M1-U", "brown"), ("EOCR-V", "M1-V", "black"),
        ("EOCR-W", "M1-W", "gray"),
    ]
    if missing:
        result = [item for item in result if set(item[:2]) != {"MC1-9", "EOCR-L3"}]
    if bypass_eocr:
        result.append(("PWR-L", "PB0-1", "yellow"))
    return result


def interlock_connections(*, bypass: bool = False) -> list[tuple[str, str, str]]:
    result = [
        ("PWR-L", "PB1-1", "yellow"), ("PWR-L", "PB2-1", "yellow"),
        ("PB1-2", "MC2-5", "yellow"), ("MC2-11", "MC1-6", "yellow"),
        ("MC1-12", "PWR-N", "yellow"), ("PB1-1", "MC1-4", "yellow"),
        ("MC1-10", "PB1-2", "yellow"), ("PB2-2", "MC1-5", "yellow"),
        ("MC1-11", "MC2-6", "yellow"), ("MC2-12", "PWR-N", "yellow"),
        ("PB2-1", "MC2-4", "yellow"), ("MC2-10", "PB2-2", "yellow"),
    ]
    if bypass:
        result += [("PB1-2", "MC1-6", "yellow"), ("PB2-2", "MC2-6", "yellow")]
    return result


def power_and_start(engine: OperationEngine, control_id: str = "PB1"):
    engine.apply(OperationAction(action="set_power", value=True))
    engine.apply(OperationAction(action="press_control", control_id=control_id))
    return engine.apply(OperationAction(action="release_control", control_id=control_id))


def check(label: str, actual, expected) -> None:
    result = "통과" if actual == expected else "실패"
    print(f"[{result}] {label}: {actual} (예상: {expected})")
    if actual != expected:
        raise AssertionError(label)


def main() -> int:
    print("0.12.0 통합 기본보드 실제 결선 간단 시험")
    print("- Q-Net 답안과 expected_nets를 읽거나 사용하지 않습니다.\n")
    repository = ProblemRepository(PROJECT_ROOT / "problems", PROJECT_ROOT / "schemas", PROJECT_ROOT / "catalog")
    repository.reload()
    template = FreeCircuitTemplateService(repository, PROJECT_ROOT / "free_templates").get(BASIC_BOARD_TEMPLATE_ID)
    runtime = DeviceBehaviorRuntimeComposer(repository.catalog).compose(template.circuit, template.operation)

    try:
        with TemporaryDirectory() as temp:
            database = SQLiteDatabase(Path(temp) / "demo.db")
            database.initialize()
            workspaces = FreeCircuitRepository(database)
            first_id = _new_workspace_id(workspaces)
            created = workspaces.save(first_id, _workspace_from_template(template, "기본보드 간단 시험"))
            second_id = _new_workspace_id(workspaces)
            check("신규 workspace_id 자동 생성", first_id != second_id and first_id.startswith("fc_"), True)
            check("초기 전선 수", len(created.connections), 0)
            check("신규 템플릿", created.editor.template_id, BASIC_BOARD_TEMPLATE_ID)

        no_hold = make_engine(runtime, self_hold_connections(False))
        no_hold.apply(OperationAction(action="set_power", value=True))
        pressed = no_hold.apply(OperationAction(action="press_control", control_id="PB1"))
        check("X1 단독 여자", pressed.coils["X1-COIL"], True)
        released = no_hold.apply(OperationAction(action="release_control", control_id="PB1"))
        check("X1 단독 복귀", released.coils["X1-COIL"], False)

        held_engine = make_engine(runtime, self_hold_connections(True))
        held = power_and_start(held_engine)
        check("X1 실제 NO 자기유지", held.coils["X1-COIL"], True)
        stopped = held_engine.apply(OperationAction(action="press_control", control_id="PB0"))
        check("PB0 STOP", stopped.coils["X1-COIL"], False)

        timer = make_engine(runtime, timer_connections())
        initial_timer = timer.apply(OperationAction(action="set_power", value=True))
        check("T1 시간 전 GL", initial_timer.indicators["GL"], "off")
        completed = timer.apply(OperationAction(action="advance_time", milliseconds=1000))
        check("T1 시간 완료 후 GL", completed.indicators["GL"], "on")

        normal = make_engine(runtime, motor_connections())
        running = power_and_start(normal)
        check("MC1 정상 3상", running.motors["M1"], "forward")
        check("MC1 주접점 폐로", running.contacts["MC1-MAIN1"], "closed")
        check("두 상 교환", power_and_start(make_engine(runtime, motor_connections(swap=True))).motors["M1"], "reverse")
        check("한 상 누락", power_and_start(make_engine(runtime, motor_connections(missing=True))).motors["M1"], "phase_loss")

        interlocked = make_engine(runtime, interlock_connections())
        power_and_start(interlocked, "PB1")
        interlocked.apply(OperationAction(action="press_control", control_id="PB2"))
        check("실제 NC 전기적 인터록", interlocked.state().coils["MC2-COIL"], False)

        protected = make_engine(runtime, motor_connections())
        power_and_start(protected)
        tripped = protected.apply(OperationAction(action="trigger_fault", target_id="EOCR", fault_type="overload"))
        check("EOCR 95-96 트립", tripped.coils["MC1-COIL"], False)
        check("EOCR 97-98 RL 경보", tripped.indicators["RL"], "on")
        reset = protected.apply(OperationAction(action="reset_fault", target_id="EOCR"))
        check("EOCR 복귀 후 새 START 필요", reset.coils["MC1-COIL"], False)

        bypass = make_engine(runtime, motor_connections(bypass_eocr=True))
        power_and_start(bypass)
        unsafe = bypass.apply(OperationAction(action="trigger_fault", target_id="EOCR", fault_type="overload"))
        check("EOCR 우회 시 코일 강제 정지 없음", unsafe.coils["MC1-COIL"], True)
        check("EOCR 보호 우회 위험", any(code.startswith("protection_bypassed:EOCR") for code in unsafe.active_faults), True)
        check("정답 데이터 미참조", "answer" not in template.model_dump() and "expected_nets" not in template.model_dump(), True)
    except (AssertionError, Exception) as exc:
        print(f"\n기본보드 시험 실패: {exc}")
        return 1

    print("\n모든 기본보드 시험이 통과했습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
from pathlib import Path

PROBLEM_ID = "qnet_electrician_practical_010"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def find_model(catalog: dict, model_id: str) -> dict | None:
    return next((item for item in catalog.get("models", []) if item.get("model_id") == model_id), None)


def check(root: Path) -> tuple[list[str], list[str]]:
    passed: list[str] = []
    blocked: list[str] = []
    problem_dir = root / "problems" / PROBLEM_ID
    catalog = load_json(root / "catalog" / "device_behaviors.json")
    board = load_json(problem_dir / "board.json")
    manifest = load_json(problem_dir / "manifest.json")
    problem = load_json(problem_dir / "problem.json")
    answer = load_json(problem_dir / "answer.json")

    for model_id in (
        "auxiliary_relay_8p_training_partial",
        "timer_8p_on_delay_training_partial",
        "magnetic_contactor_12p_training",
        "eocr_12p_training",
    ):
        model = find_model(catalog, model_id)
        if model and model.get("definition_status") == "verified":
            passed.append(f"공통 기구 검증: {model_id}")
        else:
            blocked.append(f"공통 기구 미검증: {model_id}")

    items = {item.get("item_id"): item for item in board.get("items", [])}
    for device_id in ("EOCR", "MC1", "MC2"):
        pins = items.get(device_id, {}).get("pins", [])
        numbers = {pin.get("number") for pin in pins}
        if numbers == set(range(1, 13)) and all(pin.get("enabled") for pin in pins):
            passed.append(f"{device_id} 12P 보드 핀 1~12 활성")
        else:
            blocked.append(f"{device_id} 12P 보드 핀 정의 재검토 필요")

    for device_id in ("X1", "X2", "T1", "T2"):
        pins = items.get(device_id, {}).get("pins", [])
        numbers = {pin.get("number") for pin in pins}
        if numbers == set(range(1, 9)) and all(pin.get("enabled") for pin in pins):
            passed.append(f"{device_id} 8P 보드 핀 1~8 활성")
        else:
            blocked.append(f"{device_id} 8P 보드 핀 정의 재검토 필요")

    fuse = find_model(catalog, "fuse_dual_4terminal_training")
    if fuse:
        fuse_suffixes = {str(item.get("terminal_suffix")) for item in fuse.get("terminals", [])}
        fuse_pin_numbers = {item.get("pin_number") for item in fuse.get("terminals", [])}
        fuse_pairs = {
            frozenset((item.get("from_terminal_key"), item.get("to_terminal_key")))
            for item in fuse.get("intrinsic_connections", [])
        }
        expected_pairs = {
            frozenset(("channel_1_input", "channel_1_output")),
            frozenset(("channel_2_input", "channel_2_output")),
        }
        if fuse_suffixes == {"1", "2", "3", "4"} and fuse_pin_numbers == {None} and fuse_pairs == expected_pairs:
            passed.append("FUSE 공통 모델: 직접결선 4단자·1-2/3-4 독립 회로")
        else:
            blocked.append("FUSE 공통 모델의 4단자/2독립회로 정의 재검토 필요")
    else:
        blocked.append("FUSE 4단자 공통 모델이 없음")

    fuse_pins = items.get("F", {}).get("pins", [])
    fuse_pin_ids = {pin.get("terminal_id") for pin in fuse_pins}
    if fuse_pin_ids == {"F-1", "F-2", "F-3", "F-4"} and all(pin.get("enabled") for pin in fuse_pins):
        passed.append("010 보드 FUSE: F 1개에 F-1~F-4 결선점 활성")
    else:
        blocked.append(
            "010 FUSE 보드 표현 부족: F 1개에 F-1~F-4 네 결선점이 필요함"
        )

    circuit = problem.get("circuit") or {}
    if circuit.get("definition_status") not in {None, "structure_only"} and circuit.get("devices"):
        passed.append("010 구조화 회로 데이터 작성")
    else:
        blocked.append("010 circuit가 structure_only/비어 있음")

    if problem.get("operation"):
        passed.append("010 공개 동작 정의 작성")
    else:
        blocked.append("010 공개 operation 정의가 없음")

    if answer.get("expected_nets"):
        passed.append("010 expected_nets 작성")
    else:
        blocked.append("010 expected_nets가 비어 있음")

    if answer.get("operation_tests"):
        passed.append("010 operation_tests 작성")
    else:
        blocked.append("010 operation_tests가 비어 있음")

    verification = (answer.get("verification") or {}).get("status")
    if manifest.get("status") == "verified" and verification == "verified" and not blocked:
        passed.append("010 최종 verified 개방 조건 충족")
    else:
        blocked.append(
            f"010은 계속 차단해야 함: manifest={manifest.get('status')}, answer.verification={verification}"
        )
    return passed, blocked


def main() -> int:
    parser = argparse.ArgumentParser(description="Q-Net 공개문제 010 검증 준비도 점검")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--allow-blocked", action="store_true", help="차단 항목이 있어도 종료코드 0")
    args = parser.parse_args()
    passed, blocked = check(args.root)
    print("Q-Net 010 검증 준비도")
    for item in passed:
        print(f"[통과] {item}")
    for item in blocked:
        print(f"[차단] {item}")
    print(f"요약: 통과 {len(passed)}, 차단 {len(blocked)}")
    return 0 if not blocked or args.allow_blocked else 2


if __name__ == "__main__":
    raise SystemExit(main())

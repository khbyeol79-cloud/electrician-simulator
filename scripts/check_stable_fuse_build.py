from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services import CatalogService  # noqa: E402


def check(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)
    print(f"[통과] {label}")


def main() -> int:
    catalog = CatalogService(ROOT / "catalog", ROOT / "schemas")
    fuse = catalog.get_device_behavior("fuse_dual_4terminal_training")
    check(fuse is not None, "4단자 FUSE 공통 모델 로딩")
    assert fuse is not None
    check(fuse.compatible_socket_type_ids == [], "FUSE는 소켓 비사용")
    check([item.terminal_suffix for item in fuse.terminals] == ["1", "2", "3", "4"], "FUSE 단자 1~4")
    check(all(item.pin_number is None for item in fuse.terminals), "직접결선 단자는 pin_number 없음")
    pairs = {
        frozenset((item.from_terminal_key, item.to_terminal_key))
        for item in fuse.intrinsic_connections
    }
    check(
        pairs
        == {
            frozenset(("channel_1_input", "channel_1_output")),
            frozenset(("channel_2_input", "channel_2_output")),
        },
        "FUSE 내부 독립 회로 1-2 / 3-4",
    )

    package = ROOT / "problems" / "qnet_electrician_practical_010"
    board = json.loads((package / "board.json").read_text(encoding="utf-8"))
    fuse_items = [item for item in board["items"] if item["item_id"] == "F"]
    check(len(fuse_items) == 1, "010 보드 F 기구 1개")
    pins = {item["terminal_id"]: item for item in fuse_items[0]["pins"]}
    check(set(pins) == {"F-1", "F-2", "F-3", "F-4"}, "010 보드 F-1~F-4")
    check(pins["F-1"]["x"] == pins["F-2"]["x"] and pins["F-3"]["x"] == pins["F-4"]["x"], "두 세로 퓨즈열 좌표")
    check(pins["F-1"]["x"] < pins["F-3"]["x"], "왼쪽 1-2 / 오른쪽 3-4 배치")

    source = (ROOT / "frontend" / "src" / "features" / "wiring" / "components" / "WiringBoard.tsx").read_text(encoding="utf-8")
    styles = (ROOT / "frontend" / "src" / "styles" / "global.css").read_text(encoding="utf-8")
    check("isDualFuseBoardItem" in source and "dual-fuse-cartridge" in source, "원본 WiringBoard FUSE 전용 renderer")
    check(".dual-fuse-body .dual-fuse-holder" in styles, "원본 FUSE 스타일")

    js = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "frontend" / "dist" / "assets").glob("*.js"))
    css = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "frontend" / "dist" / "assets").glob("*.css"))
    check("dual-fuse-holder" in js and "dual-fuse-cartridge" in js, "실행용 JS bundle에 FUSE renderer 포함")
    check("dual-fuse-holder" in css and "dual-fuse-cartridge" in css, "실행용 CSS bundle에 FUSE 스타일 포함")

    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    answer = json.loads((package / "answer.json").read_text(encoding="utf-8"))
    problem = json.loads((package / "problem.json").read_text(encoding="utf-8"))
    check(manifest.get("status") == "draft", "010 manifest는 draft 유지")
    check(answer.get("verification", {}).get("status") == "unverified", "010 answer는 unverified 유지")
    check(answer.get("expected_nets") == [], "010 expected_nets 미작성 유지")
    check(answer.get("operation_tests") == [], "010 operation_tests 미작성 유지")
    check(problem.get("circuit", {}).get("definition_status") == "structure_only", "010 circuit structure_only 유지")

    print("\n안정화 + FUSE 디자인 검사가 모두 통과했습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

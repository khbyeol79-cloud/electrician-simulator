"""0.12.0 빈보드·팔레트·공통 엔진의 최소 API 연동 시험."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import Settings  # noqa: E402
from app.core.paths import AppPaths  # noqa: E402
from app.main import create_app  # noqa: E402


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="electrician-empty-board-") as directory:
        temporary = Path(directory)
        paths = AppPaths(
            project_root=PROJECT_ROOT, bundle_root=PROJECT_ROOT,
            frontend_dist=PROJECT_ROOT / "frontend" / "dist",
            problems_dir=PROJECT_ROOT / "problems", catalog_dir=PROJECT_ROOT / "catalog",
            writable_root=temporary, database_file=temporary / "demo.db",
            logs_dir=temporary / "logs", log_file=temporary / "logs" / "demo.log",
        )
        with TestClient(create_app(Settings(paths=paths))) as client:
            headers = {"X-User-Id": "empty_board_demo"}
            templates = client.get("/api/free-circuits/templates", headers=headers).json()
            palette = client.get("/api/free-circuits/palette", headers=headers).json()
            created = client.post(
                "/api/free-circuits/workspaces", headers=headers,
                json={"name": "0.12.0 빈보드 데모", "template_id": "empty_board_001"},
            ).json()
            workspace_id = created["workspace_id"]
            relay = client.post(
                f"/api/free-circuits/{workspace_id}/devices", headers=headers,
                json={"palette_id": "relay_8p", "placement": {"zone": "internal_upper", "row": 0, "column": 0}},
            )
            power = client.post(
                f"/api/free-circuits/{workspace_id}/devices", headers=headers,
                json={"palette_id": "power", "placement": {"zone": "external_top", "row": 0, "column": 0}},
            )
            session = client.post(f"/api/free-circuits/{workspace_id}/sessions", headers=headers)

            checks = [
                ("시작 보드 2종", [item["template_id"] for item in templates] == ["basic_board_001", "empty_board_001"]),
                ("팔레트 공개", len(palette["items"]) >= 10 and "expected_nets" not in str(palette)),
                ("TB5·TB6 빈보드", {item["item_id"] for item in created["board"]["items"]} == {"TB5", "TB6"}),
                ("릴레이 설치", relay.status_code == 201 and relay.json()["assembly"]["installed_devices"][0]["instance_id"] == "X1"),
                ("전원 설치", power.status_code == 201),
                ("공통 동작 엔진 진입", session.status_code == 201 and session.json()["catalog_composed"] is True),
            ]
            print("0.12.0 빈보드 공통 엔진 간단 시험")
            for label, passed in checks:
                print(f"[{'통과' if passed else '실패'}] {label}")
            if not all(passed for _, passed in checks):
                return 1
            print("\n모든 간단 시험이 통과했습니다.")
            print("실제 결선 시험은 docs/empty-board-manual-test-0.12.0.md를 따르세요.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

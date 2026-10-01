from __future__ import annotations

import shutil

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.paths import AppPaths
from app.main import create_app
from problem_test_utils import PROJECT_ROOT


def stage4_paths(tmp_path):
    bundle = tmp_path / "bundle"
    shutil.copytree(PROJECT_ROOT / "schemas", bundle / "schemas")
    shutil.copytree(PROJECT_ROOT / "catalog", bundle / "catalog")
    shutil.copytree(PROJECT_ROOT / "free_templates", bundle / "free_templates")
    for problem_id in ("practice_001", "training_socket_demo_001", "operation_demo_001"):
        shutil.copytree(PROJECT_ROOT / "problems" / problem_id, bundle / "problems" / problem_id)
    dist = bundle / "frontend" / "dist"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text("<html>test</html>", encoding="utf-8")
    return AppPaths(
        project_root=bundle, bundle_root=bundle, frontend_dist=dist,
        problems_dir=bundle / "problems", catalog_dir=bundle / "catalog",
        writable_root=tmp_path / "data", database_file=tmp_path / "data" / "test.db",
        logs_dir=tmp_path / "logs", log_file=tmp_path / "logs" / "test.log",
    )


def test_diagram_api_contains_no_answer_data(tmp_path):
    with TestClient(create_app(Settings(paths=stage4_paths(tmp_path)))) as client:
        detail = client.get("/api/problems/training_socket_demo_001")
        assert detail.status_code == 200
        assert detail.json()["socket_questions"][0]["question_id"] == "SQ-VR1-C1"
        response = client.get("/api/problems/training_socket_demo_001/diagram")
        assert response.status_code == 200
        assert response.json()["sections"][0]["label"] == "주회로"
        for forbidden in ("socket_pin_answers", "upper\":6", "lower\":3", "answer.json"):
            assert forbidden not in response.text.replace(" ", "")


def test_correct_wrong_unverified_and_progress(tmp_path):
    paths = stage4_paths(tmp_path)
    with TestClient(create_app(Settings(paths=paths))) as client:
        correct = client.post("/api/problems/training_socket_demo_001/circuit-attempts/submit", json={"problem_version": 1, "responses": {"SQ-VR1-C1": {"upper": 6, "lower": 3}}})
        assert correct.status_code == 200
        assert correct.json()["overall_correct"] is True
        assert "expected" not in correct.text

        wrong = client.post("/api/problems/training_socket_demo_001/circuit-attempts/submit", json={"problem_version": 1, "responses": {"SQ-VR1-C1": {"upper": 5, "lower": 4}}})
        assert wrong.status_code == 200
        assert wrong.json()["overall_correct"] is False

        unverified = client.post("/api/problems/practice_001/circuit-attempts/submit", json={"problem_version": 1, "responses": {}})
        assert unverified.status_code == 200
        assert unverified.json()["gradable"] is False
        assert unverified.json()["overall_correct"] is None

        progress = client.get("/api/problems/training_socket_demo_001/circuit-progress")
        assert progress.json()["attempt_count"] == 2
        with client.app.state.database.connect() as connection:
            assert connection.execute("SELECT COUNT(*) AS count FROM circuit_attempts").fetchone()["count"] == 3
            assert connection.execute("SELECT COUNT(*) AS count FROM circuit_attempt_responses").fetchone()["count"] == 4


def test_attempt_validation_errors(tmp_path):
    with TestClient(create_app(Settings(paths=stage4_paths(tmp_path)))) as client:
        cases = [
            ({"problem_version": 2, "responses": {}}, 409),
            ({"problem_version": 1, "responses": {"MISSING": {"upper": 1}}}, 422),
            ({"problem_version": 1, "responses": {"SQ-VR1-C1": {"missing": 1}}}, 422),
            ({"problem_version": 1, "responses": {"SQ-VR1-C1": {"upper": 9}}}, 422),
            ({"problem_version": 1, "responses": {"SQ-VR1-C1": {"upper": 1, "lower": 1}}}, 422),
        ]
        for payload, status in cases:
            response = client.post("/api/problems/training_socket_demo_001/circuit-attempts/submit", json=payload)
            assert response.status_code == status
        assert client.get("/api/problems/missing/diagram").status_code == 404
        assert client.get("/api/problems/missing/circuit-progress").status_code == 404


def test_analysis_draft_autosaves_per_user_without_answer_data(tmp_path):
    path = "/api/problems/training_socket_demo_001/analysis-draft"
    payload = {
        "problem_version": 1,
        "memo": "X1 자기유지와 T1 계시 접점을 확인",
        "selected_device_ids": ["X1", "T1"],
        "selected_socket_ids": ["socket_8p"],
        "selected_terminal_ids": ["X1-1", "T1-8"],
        "annotations": {"X1": "A접점"},
    }
    with TestClient(create_app(Settings(paths=stage4_paths(tmp_path)))) as client:
        saved = client.put(path, headers={"X-User-Id": "student_a"}, json=payload)
        assert saved.status_code == 200, saved.text
        assert saved.json()["memo"] == payload["memo"]
        assert client.get(path, headers={"X-User-Id": "student_b"}).json() is None
        restored = client.get(path, headers={"X-User-Id": "student_a"})
        assert restored.json()["selected_terminal_ids"] == ["X1-1", "T1-8"]
        for forbidden in ("answer", "expected", "correct", "score"):
            assert forbidden not in restored.text.lower()
        assert client.put(path, json={**payload, "problem_version": 99}).status_code == 409
        assert client.delete(path, headers={"X-User-Id": "student_a"}).status_code == 204
        assert client.get(path, headers={"X-User-Id": "student_a"}).json() is None

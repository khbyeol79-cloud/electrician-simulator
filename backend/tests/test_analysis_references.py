import hashlib
import json
import shutil

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.repositories import ProblemRepository
from problem_test_utils import PROJECT_ROOT
from test_problem_api import api_paths
from scripts.build_lan_release import release_files


def test_all_18_public_reference_pages_and_crops_are_bundled_and_intact():
    inventory = json.loads((PROJECT_ROOT / "catalog/qnet_analysis_references.json").read_text(encoding="utf-8"))
    sources = json.loads((PROJECT_ROOT / "catalog/qnet_public_sources.json").read_text(encoding="utf-8"))
    source_hashes = {row["problem_id"]: row["sha256"] for row in sources["records"]}
    repository = ProblemRepository(PROJECT_ROOT / "problems", PROJECT_ROOT / "schemas", PROJECT_ROOT / "catalog")
    repository.reload()
    packaged = set(release_files(PROJECT_ROOT))
    assert len(inventory) == 18
    for problem_id, record in inventory.items():
        assert record["source_sha256"] == source_hashes[problem_id]
        expected = {"operation", "internal", "mc", "eocr", "timer", "relay", "socket8", "socket12"}
        if int(problem_id[-3:]) <= 9:
            expected |= {"fr", "fls", "ss"}
        assert set(record["references"]) == expected
        for name, metadata in record["references"].items():
            path = repository.get_analysis_reference_path(problem_id, name)
            assert path in packaged, (problem_id, name)
            data = path.read_bytes()
            assert data.startswith(b"\x89PNG\r\n\x1a\n")
            assert hashlib.sha256(data).hexdigest() == metadata["sha256"]
            assert metadata["page"] == (8 if name == "operation" else 9)
            assert metadata["width"] > 300 and metadata["height"] > 200


def test_reference_route_only_serves_allowlisted_public_pngs(tmp_path):
    paths = api_paths(tmp_path)
    for n in (1, 10):
        pid = f"qnet_electrician_practical_{n:03d}"
        shutil.copytree(PROJECT_ROOT / "problems" / pid, paths.problems_dir / pid)
    with TestClient(create_app(Settings(paths=paths))) as client:
        for pid, names in (("001", ["operation", "internal", "eocr", "relay", "fr", "fls", "ss"]),
                           ("010", ["operation", "internal", "relay", "mc", "timer"])):
            for name in names:
                response = client.get(f"/api/problems/qnet_electrician_practical_{pid}/analysis-reference/{name}")
                assert response.status_code == 200
                assert response.headers["content-type"] == "image/png"
        for path in ("qnet_electrician_practical_001/analysis-reference/answer.json",
                     "qnet_electrician_practical_001/analysis-reference/%2e%2e%2fanswer",
                     "qnet_electrician_practical_010/analysis-reference/fr",
                     "missing/analysis-reference/internal"):
            assert client.get("/api/problems/" + path).status_code == 404


def test_audited_symbol_device_map_covers_stable_hotspots_without_changing_answers():
    folder = PROJECT_ROOT / "frontend/src/features/circuit"
    raw = (folder / "contactHotspots.json").read_bytes()
    # Index-based labels must be re-reviewed if the geometry generator changes.
    normalized = raw.replace(b"\r\n", b"\n")
    original = json.loads(raw)
    order = json.loads((folder / "contactDeviceOrder.json").read_text())
    assert set(order) == {f"{i:03d}" for i in range(1, 19)}
    assert sum(len(rows) for rows in original.values()) == 643
    for pid, rows in original.items():
        names = order[pid[-3:]].split()
        assert len(names) == len(rows)
        problem = json.loads((PROJECT_ROOT / "problems" / pid / "problem.json").read_text(encoding="utf-8"))
        known = {d["device_id"] for d in problem["available_devices"] + problem["circuit"]["devices"]}
        known |= {d["device_id"] for d in problem["wiring_semantics"]["external_devices"]}
        assert set(names) <= known
    assert hashlib.sha256(normalized).hexdigest() == "3bec40252517c7ed7b87d2b6e288ab9362a1224b20ca8ed0488a5a4bcf79ec99"

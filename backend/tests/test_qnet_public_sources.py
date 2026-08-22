from __future__ import annotations

import json

from app.repositories import ProblemRepository
from problem_test_utils import PROJECT_ROOT


def test_qnet_source_inventory_and_packages_are_exactly_001_through_018():
    registry = json.loads((PROJECT_ROOT / "catalog" / "qnet_public_sources.json").read_text(encoding="utf-8"))
    records = registry["records"]
    assert [item["number"] for item in records] == [f"{index:03d}" for index in range(1, 19)]
    assert len({item["sha256"] for item in records}) == 18
    assert all(len(item["sha256"]) == 64 for item in records)

    repository = ProblemRepository(PROJECT_ROOT / "problems", PROJECT_ROOT / "schemas", PROJECT_ROOT / "catalog")
    stats = repository.reload()
    official = [item for item in repository.list_summaries() if item.problem_type == "official" and item.source_type == "official"]
    assert stats.excluded == 0
    assert len(official) == 18
    assert {item.problem_id for item in official} == {item["problem_id"] for item in records}
    assert {item.status for item in official} == {"draft"}


def test_qnet_drafts_expose_sources_but_not_private_answers():
    repository = ProblemRepository(PROJECT_ROOT / "problems", PROJECT_ROOT / "schemas", PROJECT_ROOT / "catalog")
    repository.reload()
    for number in ("001", "009", "010", "018"):
        problem_id = f"qnet_electrician_practical_{number}"
        package = repository._get_package_internal(problem_id)
        public = repository.get_public(problem_id)
        assert package is not None and public is not None
        assert package.answer.verification.status == "unverified"
        assert not package.answer.expected_nets
        assert public.operation is None
        assert len(public.wiring_semantics["external_devices"]) >= 10
        serialized = public.model_dump_json()
        for forbidden in ("expected_nets", "wiring_connections", "operation_tests", "answer.json"):
            assert forbidden not in serialized


def test_qnet_schematic_assets_are_embedded_original_page_renders():
    repository = ProblemRepository(PROJECT_ROOT / "problems", PROJECT_ROOT / "schemas", PROJECT_ROOT / "catalog")
    repository.reload()
    for number in ("001", "018"):
        path = repository.get_schematic_path(f"qnet_electrician_practical_{number}")
        assert path is not None
        content = path.read_text(encoding="utf-8")
        assert content.startswith("<svg")
        assert "data:image/png;base64," in content
        assert path.stat().st_size < 5 * 1024 * 1024

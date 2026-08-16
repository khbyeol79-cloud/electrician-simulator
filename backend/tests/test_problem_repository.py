from __future__ import annotations

from app.repositories import AnswerRepository, ProblemRepository
from problem_test_utils import copy_problem, copy_schemas, update_json


def _set_status(package, status: str):
    def manifest_update(data):
        data["status"] = status
        data["title"] = f"{status} 문제"
        if status == "verified":
            data["source"]["verified_date"] = "2026-08-16"

    def answer_update(data):
        data["verification"]["status"] = "verified" if status == "verified" else "reviewed"
        if status == "verified":
            data["verification"]["verified_by"] = "test"
            data["verification"]["verified_at"] = "2026-08-16T00:00:00+09:00"

    update_json(package / "manifest.json", manifest_update)
    update_json(package / "answer.json", answer_update)


def test_repository_sorting_and_internal_answer_access(tmp_path):
    schemas = copy_schemas(tmp_path)
    problems = tmp_path / "problems"
    draft = copy_problem(problems, "draft_001")
    reviewed = copy_problem(problems, "reviewed_001")
    verified = copy_problem(problems, "verified_001")
    _set_status(draft, "draft")
    _set_status(reviewed, "reviewed")
    _set_status(verified, "verified")

    repository = ProblemRepository(problems, schemas)
    stats = repository.reload()
    assert stats.loaded == 3
    assert [item.status for item in repository.list_summaries()] == [
        "verified", "reviewed", "draft"
    ]
    answer = AnswerRepository(repository).get_internal("verified_001")
    assert answer is not None
    assert answer.verification.status == "verified"


def test_duplicate_ids_exclude_every_copy(tmp_path):
    schemas = copy_schemas(tmp_path)
    problems = tmp_path / "problems"
    copy_problem(problems, "duplicate_001")
    second = copy_problem(problems, "duplicate_002")
    update_json(second / "manifest.json", lambda data: data.update(problem_id="duplicate_001"))
    update_json(second / "problem.json", lambda data: data.update(problem_id="duplicate_001"))
    update_json(second / "answer.json", lambda data: data.update(problem_id="duplicate_001"))

    repository = ProblemRepository(problems, schemas)
    stats = repository.reload()
    assert stats.loaded == 0
    assert any(issue.code == "duplicate_problem_id" for issue in repository.issues())


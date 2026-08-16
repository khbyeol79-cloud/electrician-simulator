from __future__ import annotations

import json

from app.services import ProblemPackageValidator
from problem_test_utils import PROJECT_ROOT, copy_problem, copy_schemas, update_json


def test_sample_problem_is_valid_with_unverified_warning():
    result = ProblemPackageValidator(PROJECT_ROOT / "schemas").validate(
        PROJECT_ROOT / "problems" / "practice_001"
    )
    assert result.is_valid is True
    assert {issue.code for issue in result.issues} == {"answer_unverified"}


def test_invalid_json_is_excluded(tmp_path):
    schemas = copy_schemas(tmp_path)
    package = copy_problem(tmp_path / "problems")
    (package / "problem.json").write_text("{broken", encoding="utf-8")
    result = ProblemPackageValidator(schemas).validate(package)
    assert result.is_valid is False
    assert "invalid_json" in {issue.code for issue in result.issues}


def test_missing_file_and_id_mismatch(tmp_path):
    schemas = copy_schemas(tmp_path)
    package = copy_problem(tmp_path / "problems")
    (package / "schematic.svg").unlink()
    update_json(package / "answer.json", lambda data: data.update(problem_id="other_001"))
    result = ProblemPackageValidator(schemas).validate(package)
    codes = {issue.code for issue in result.issues}
    assert result.is_valid is False
    assert "missing_schematic" in codes
    assert "problem_id_mismatch" in codes


def test_unsafe_path_is_rejected(tmp_path):
    schemas = copy_schemas(tmp_path)
    package = copy_problem(tmp_path / "problems")
    update_json(
        package / "manifest.json",
        lambda data: data["files"].update(problem="../outside.json"),
    )
    result = ProblemPackageValidator(schemas).validate(package)
    assert result.is_valid is False
    assert any(issue.code == "schema_error" for issue in result.issues)


def test_unknown_status_is_rejected(tmp_path):
    schemas = copy_schemas(tmp_path)
    package = copy_problem(tmp_path / "problems")
    update_json(package / "manifest.json", lambda data: data.update(status="published"))
    result = ProblemPackageValidator(schemas).validate(package)
    assert result.is_valid is False
    assert any(issue.code == "schema_error" for issue in result.issues)


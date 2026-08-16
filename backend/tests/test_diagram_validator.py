from __future__ import annotations

import json
import shutil

import pytest

from app.services import ProblemPackageValidator
from problem_test_utils import PROJECT_ROOT, copy_schemas


def copy_training(tmp_path):
    package = tmp_path / "problems" / "training_socket_demo_001"
    package.parent.mkdir(parents=True)
    shutil.copytree(PROJECT_ROOT / "problems" / "training_socket_demo_001", package)
    return package


def mutate_diagram(package, updater):
    path = package / "diagram.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    updater(data)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def element_by_id(data, element_id):
    return next(item for item in data["elements"] if item["element_id"] == element_id)


def test_training_diagram_is_valid():
    result = ProblemPackageValidator(PROJECT_ROOT / "schemas").validate(PROJECT_ROOT / "problems" / "training_socket_demo_001")
    assert result.is_valid is True
    assert result.diagram is not None


@pytest.mark.parametrize(
    "updater,code",
    [
        (lambda d: d["sections"].append(dict(d["sections"][0])), "duplicate_section_id"),
        (lambda d: d["elements"].append(dict(d["elements"][0])), "duplicate_diagram_element_id"),
        (lambda d: d["elements"][0].update(section_id="missing"), "unknown_diagram_section"),
        (lambda d: element_by_id(d, "diagram_vr1_c1").update(circuit_ref_id="MISSING"), "unknown_diagram_reference"),
        (lambda d: element_by_id(d, "diagram_vr1_c1").update(x=1700), "element_out_of_viewbox"),
        (lambda d: d["conductors"][0]["points"].append({"x": 250, "y": 700}), "diagonal_conductor"),
        (lambda d: element_by_id(d, "diagram_vr1_c1").update(question_id=None), "interactive_question_missing"),
    ],
)
def test_invalid_diagram_references_exclude_problem(tmp_path, updater, code):
    schemas = copy_schemas(tmp_path)
    package = copy_training(tmp_path)
    mutate_diagram(package, updater)
    result = ProblemPackageValidator(schemas).validate(package)
    assert result.is_valid is False
    assert code in {issue.code for issue in result.issues}

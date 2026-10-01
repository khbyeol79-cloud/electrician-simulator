"""Independent PDF pin-topology observations, including all runtime adapters."""
import importlib.util
from pathlib import Path


def test_all_pdf_component_observations_and_cascaded_time_are_correct():
    path = Path(__file__).resolve().parents[2] / "scripts/audit_qnet_engine_against_pdf.py"
    spec = importlib.util.spec_from_file_location("pdf_audit", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    report = module.run()
    failures = [r for r in report["results"] if not r["passed"]]
    assert not failures, failures
    assert report["total"] >= 937

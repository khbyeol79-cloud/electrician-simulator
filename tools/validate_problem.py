from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.repositories import ProblemRepository
from app.services import ProblemPackageValidator


def _print_issue(issue) -> None:
    label = "오류" if issue.severity == "error" else "경고"
    location = issue.file or "문제 패키지"
    if issue.field:
        location += f" ({issue.field})"
    print(f"[{label}] {location}: {issue.message}")


def validate_one(package_dir: Path) -> int:
    validator = ProblemPackageValidator(PROJECT_ROOT / "schemas")
    result = validator.validate(package_dir)
    problem_id = result.manifest.problem_id if result.manifest else package_dir.name
    if result.is_valid:
        print(f"[정상] {problem_id}")
    for issue in result.issues:
        _print_issue(issue)
    errors = sum(issue.severity == "error" for issue in result.issues)
    warnings = sum(issue.severity == "warning" for issue in result.issues)
    print(f"검사 결과: 오류 {errors}개, 경고 {warnings}개")
    return 1 if errors else 0


def validate_all() -> int:
    repository = ProblemRepository(PROJECT_ROOT / "problems", PROJECT_ROOT / "schemas")
    statistics = repository.reload()
    summaries = repository.list_summaries()
    for summary in summaries:
        print(f"[정상] {summary.problem_id}")
    for issue in repository.issues():
        _print_issue(issue)
    errors = sum(issue.severity == "error" for issue in repository.issues())
    qnet_count = sum(
        summary.problem_type == "official" and summary.source_type == "official"
        for summary in summaries
    )
    if qnet_count == 0:
        print("[정책 경고] 검증된 Q-Net 공개문제 데이터가 없습니다: 0/18")
    elif qnet_count != 18:
        print(f"[정책 오류] Q-Net 공개문제는 18개 묶음이어야 합니다: {qnet_count}/18")
        errors += 1
    else:
        print("[정책 정상] Q-Net 공개문제 18/18")
    registry_path = PROJECT_ROOT / "catalog" / "qnet_public_sources.json"
    if not registry_path.is_file():
        print("[정책 오류] Q-Net 원본 추적 목록이 없습니다: catalog/qnet_public_sources.json")
        errors += 1
    else:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        records = registry.get("records", [])
        numbers = [record.get("number") for record in records]
        expected_numbers = [f"{index:03d}" for index in range(1, 19)]
        if numbers != expected_numbers:
            print(f"[정책 오류] Q-Net 원본 번호가 001~018 연속이 아닙니다: {numbers}")
            errors += 1
        if len({record.get("sha256") for record in records}) != 18:
            print("[정책 오류] Q-Net 원본 SHA-256이 누락되거나 중복됩니다.")
            errors += 1
        summary_ids = {summary.problem_id for summary in summaries}
        for record in records:
            problem_id = record.get("problem_id")
            if problem_id not in summary_ids:
                print(f"[정책 오류] 원본 목록의 문제 패키지가 로딩되지 않았습니다: {record.get('problem_id')}")
                errors += 1
                continue
            package = repository._get_package_internal(problem_id)
            reference = package.manifest.source.reference or ""
            if record.get("source_file") not in reference or record.get("sha256") not in reference:
                print(f"[정책 오류] 문제 원본 파일명·해시 참조가 manifest와 다릅니다: {problem_id}")
                errors += 1
            if record.get("page_count") != 11 or record.get("evidence_pages") != [6, 7, 8, 9]:
                print(f"[정책 오류] PDF 페이지 수 또는 근거 페이지가 올바르지 않습니다: {problem_id}")
                errors += 1
            if package.manifest.status != record.get("status"):
                print(f"[정책 오류] 조사표와 문제 검증 상태가 다릅니다: {problem_id}")
                errors += 1
        if len(records) == 18 and numbers == expected_numbers:
            print("[근거 정상] PDF 인벤토리 18개, 번호·해시·문제 ID 확인")
    verified_qnet = sum(
        summary.problem_type == "official" and summary.source_type == "official" and summary.status == "verified"
        for summary in summaries
    )
    print(f"[검증 상태] 원본 조사 {qnet_count}/18, 채점 검증 완료 {verified_qnet}/18")
    print(
        f"전체 검사: 정상 {statistics.loaded}개, 제외 {statistics.excluded}개, "
        f"오류 {errors}개, 경고 {statistics.warnings}개"
    )
    return 1 if errors else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="전기기능사 시뮬레이터 문제 검증")
    parser.add_argument("path", nargs="?", help="검사할 문제 폴더")
    parser.add_argument("--all", action="store_true", help="problems 폴더 전체 검사")
    arguments = parser.parse_args(argv)

    if arguments.all:
        return validate_all()
    if not arguments.path:
        parser.error("문제 폴더 또는 --all을 지정하세요.")
    package_dir = Path(arguments.path)
    if not package_dir.is_absolute():
        package_dir = (Path.cwd() / package_dir).resolve()
    if not package_dir.is_dir():
        print(f"[오류] 문제 폴더가 없습니다: {arguments.path}")
        return 1
    return validate_one(package_dir)


if __name__ == "__main__":
    raise SystemExit(main())

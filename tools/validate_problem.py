from __future__ import annotations

import argparse
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

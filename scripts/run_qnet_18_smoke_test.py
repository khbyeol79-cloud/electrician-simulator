"""0.13.0 Q-Net 18개 원본·패키지·8P 핀 근거 간단 시험."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.repositories import ProblemRepository
from app.services.catalog_service import CatalogService


def check(label: str, actual, expected) -> None:
    if actual != expected:
        raise AssertionError(f"{label}: {actual!r} (예상: {expected!r})")
    print(f"[통과] {label}: {actual}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--problem", choices=[f"{index:03d}" for index in range(1, 19)])
    args = parser.parse_args()
    repository = ProblemRepository(ROOT / "problems", ROOT / "schemas", ROOT / "catalog")
    stats = repository.reload()
    official = [item for item in repository.list_summaries() if item.problem_type == "official" and item.source_type == "official"]
    registry = json.loads((ROOT / "catalog" / "qnet_public_sources.json").read_text(encoding="utf-8"))["records"]
    catalog = CatalogService(ROOT / "catalog", ROOT / "schemas")
    relay = catalog.get_device_behavior("auxiliary_relay_8p_training_partial")
    timer = catalog.get_device_behavior("timer_8p_on_delay_training_partial")

    print("0.13.0 Q-Net 공개문제 조사·로딩 간단 시험")
    check("문제 저장소 제외", stats.excluded, 0)
    check("공식 원본 인벤토리", len(registry), 18)
    check("공식 문제 패키지", len(official), 18)
    check("001~018 연속 번호", [item["number"] for item in registry], [f"{i:03d}" for i in range(1, 19)])
    check("현재 검증 대기 상태", {item.status for item in official}, {"draft"})
    check("8P 릴레이 활성 핀", sorted(item.pin_number for item in relay.terminals), list(range(1, 9)))
    check("8P 타이머 활성 핀", sorted(item.pin_number for item in timer.terminals), list(range(1, 9)))
    check("8P 릴레이 전환접점", len(relay.contacts), 2)
    check("8P 타이머 계시 전환접점", len(timer.contacts), 2)

    if args.problem:
        problem_id = f"qnet_electrician_practical_{args.problem}"
        package = repository._get_package_internal(problem_id)
        print(f"\n선택 문제: {package.manifest.title}")
        print(f"원본: {package.manifest.source.reference}")
        print(f"상태: {package.manifest.status} / {package.answer.verification.status}")
        print("현재는 원본 회로도 검토만 가능하며 결선 채점·동작시험은 차단됩니다.")
    print("\n모든 간단 시험이 통과했습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

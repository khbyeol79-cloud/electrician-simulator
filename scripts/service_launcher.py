"""Double-click helpers use this local controller; no network shutdown API."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import sys

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from scripts.run_service import check_service, load_service
from scripts.service_lifecycle import serve_and_backup, stop_and_wait


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["start", "stop"])
    parser.add_argument("--env-file", type=Path, default=PROJECT / "service-config/service.env")
    parser.add_argument("--backup-dir", type=Path, default=PROJECT / "user-data-backups")
    parser.add_argument("--cert", type=Path)
    parser.add_argument("--key", type=Path)
    parser.add_argument("--confirm-saved", action="store_true")
    parser.add_argument("--open-backup", action="store_true")
    args = parser.parse_args()
    if args.command == "start" and not args.env_file.exists():
        # Only the standard first-run file may be initialized automatically.
        if args.env_file != PROJECT / "service-config/service.env":
            raise ValueError("설정 파일을 찾지 못했습니다.")
        args.env_file.parent.mkdir(parents=True, exist_ok=True)
        with args.env_file.open("xb") as target, (PROJECT / "deploy/lan.env.example").open("rb") as sample:
            shutil.copyfileobj(sample, target)
    settings = load_service(args.env_file, args.cert, args.key)
    if args.command == "start":
        check_service(settings, args.cert)
        serve_and_backup(settings, args.backup_dir, args.cert, args.key)
    else:
        if not args.confirm_saved:
            print("먼저 사용자에게 종료를 알리고 '저장됨' 확인 및 로그아웃을 요청하세요.")
            if input("서버를 종료하고 사용자 자료를 백업할까요? (Y/N): ").strip().lower() != "y":
                print("취소했습니다. 서버는 계속 실행됩니다.")
                return
        print("진행 중 요청의 완료와 백업을 기다립니다. 이 창과 서버 창을 닫지 마세요.", flush=True)
        archive = stop_and_wait(settings.paths.writable_root)
        print(f"서버 종료 및 백업 완료: {archive}\n이 ZIP 파일 하나를 USB에 복사하세요.")
        if args.open_backup and os.name == "nt":
            try:
                os.startfile(str(archive.parent))
            except OSError:
                print(f"폴더 자동 열기 실패. 직접 열어주세요: {archive.parent}")


if __name__ == "__main__":
    try:
        main()
    except (Exception, KeyboardInterrupt) as exc:
        print(f"완료하지 못했습니다: {exc}\n원본 자료는 삭제하지 않았습니다. 오류를 확인하세요.", file=sys.stderr)
        sys.exit(1)

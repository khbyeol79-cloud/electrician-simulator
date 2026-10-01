"""Verify a backup into a NEW local folder, then select it for the next start."""
from __future__ import annotations

import argparse
from datetime import datetime
import os
from pathlib import Path
import sys
import uuid

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from scripts.service_data import restore
from scripts.service_lifecycle import ServiceLease


def restore_and_select(project: Path, source: Path) -> Path:
    project = project.resolve(strict=True)
    source = source.resolve(strict=True)
    config = project / "service-config/service.env"
    original = config.read_bytes() if config.exists() else None
    text = (original.decode("utf-8-sig") if original is not None else
            (project / "deploy/lan.env.example").read_text(encoding="utf-8-sig"))
    values = dict(line.strip().split("=", 1) for line in text.splitlines()
                  if line.strip() and not line.lstrip().startswith("#") and "=" in line)
    current = Path(values.get("ELECTRICIAN_DATA_DIR", "user-data").strip())
    if not current.is_absolute():
        current = project / current
    # The same lease is held by both supported server launchers until backup ends.
    # Neither the running process nor the previous data is modified.
    with ServiceLease(current):
        destination = project / "restored-data" / (datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8])
        destination.parent.mkdir(exist_ok=True)
        restore(source, destination)
        sys.path.insert(0, str(PROJECT / "backend"))
        from app.core.auth import AuthStore
        if not (destination / "accounts.db").is_file():
            raise ValueError("계정 DB가 없는 백업입니다. 설정은 변경하지 않았습니다.")
        # A fixed address from the previous PC would prevent startup here.
        # Only the restored COPY loses its network override; other options stay.
        store = AuthStore(destination / "accounts.db")
        store.initialize()
        store.clear_network_option()
        replacement = "ELECTRICIAN_DATA_DIR=" + destination.relative_to(project).as_posix()
        lines = [line for line in text.splitlines()
                 if not line.strip().startswith("ELECTRICIAN_DATA_DIR=")]
        updated = ("\n".join(lines) + "\n" + replacement + "\n").encode("utf-8")
        config.parent.mkdir(exist_ok=True)
        # Avoid overwriting another operator's configuration change.
        if (config.read_bytes() if config.exists() else None) != original:
            raise RuntimeError("복원 중 설정이 변경되었습니다. 복원 자료는 보존했으며 자동 선택은 취소했습니다.")
        if original is not None:
            with config.with_name("service.env.before-restore-" + destination.name).open("xb") as backup:
                backup.write(original)
        staged = config.with_name("service.env." + uuid.uuid4().hex + ".tmp")
        with staged.open("xb") as output:
            output.write(updated)
            output.flush()
            os.fsync(output.fileno())
        os.replace(staged, config)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backup", type=Path)
    args = parser.parse_args()
    print("먼저 이 PC의 서버를 '서버_종료_백업.bat'로 종료하세요.")
    print(f"복원할 백업: {args.backup.resolve()}\n기존 자료는 덮어쓰지 않으며, 복원한 자료를 다음 실행에서 사용합니다.")
    if input("서버가 종료되었고 이 백업으로 전환할까요? (Y/N): ").strip().lower() != "y":
        print("취소했습니다.")
        return
    destination = restore_and_select(PROJECT, args.backup)
    print(f"검증 및 복원 완료: {destination}")
    print("서버_시작.bat를 실행하고 기존 아이디/비밀번호로 다시 로그인하세요.")
    print("이전 PC의 관리자 IP 설정은 해제했습니다. service-config/service.env의 주소·포트를 사용합니다.")


if __name__ == "__main__":
    try:
        main()
    except (Exception, KeyboardInterrupt) as exc:
        print(f"복원을 완료하지 못했습니다: {exc}\n기존 자료와 백업 ZIP은 삭제하지 않았습니다.", file=sys.stderr)
        sys.exit(1)

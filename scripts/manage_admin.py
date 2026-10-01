"""Designate an EXISTING account as administrator, locally on the server only."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data_dir", type=Path)
    parser.add_argument("username", nargs="?")
    parser.add_argument("--revoke", action="store_true")
    parser.add_argument("--clear-network", action="store_true")
    parser.add_argument("--server-stopped", action="store_true", required=True)
    args = parser.parse_args()
    if args.clear_network and (args.username or args.revoke):
        parser.error("--clear-network는 아이디/--revoke와 함께 사용할 수 없습니다.")
    if not args.clear_network and not args.username:
        parser.error("관리자로 지정할 가입 아이디를 입력하세요.")
    path = args.data_dir.resolve(strict=True) / "accounts.db"
    if not path.is_file():
        raise ValueError("accounts.db가 없습니다. 실제 서비스의 데이터 폴더를 지정하세요.")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
    from app.core.auth import AuthStore
    store = AuthStore(path)
    store.initialize()
    if args.clear_network:
        store.clear_network_option()
        print("저장된 네트워크 설정만 해제했습니다. 다음 실행에는 env 파일의 주소·포트를 사용합니다.")
        return
    store.set_admin(args.username.strip().lower(), not args.revoke)
    print("관리자 권한을 변경했습니다. 서버를 켜고 다시 로그인하세요. 학습 기록은 유지됩니다.")


if __name__ == "__main__":
    main()

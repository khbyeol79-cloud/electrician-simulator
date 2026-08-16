from __future__ import annotations

import logging
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import load_settings
from app.core.logging_config import configure_logging
from desktop.local_server import LocalServer, find_free_port


def show_startup_error(message: str) -> None:
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.user32.MessageBoxW(
                0,
                message,
                "전기기능사 시뮬레이터 실행 오류",
                0x10,
            )
            return
        except Exception:
            pass
    print(message, file=sys.stderr)


def main() -> int:
    os.environ["APP_MODE"] = "desktop"
    settings = load_settings()
    settings = settings.model_copy(
        update={"app_mode": "desktop", "host": "127.0.0.1", "port": find_free_port()}
    )
    logger = configure_logging(settings.paths, settings.debug)

    if not (settings.resolved_static_dir / "index.html").is_file():
        show_startup_error(
            "프런트엔드 빌드 파일이 없습니다. setup_windows.bat를 먼저 실행해 주세요."
        )
        return 1

    server = LocalServer(settings)
    try:
        server.start()
        server.wait_until_ready()
        try:
            import webview
        except ImportError as exc:
            raise RuntimeError(
                "pywebview가 설치되지 않았습니다. setup_windows.bat를 실행해 주세요."
            ) from exc

        webview.create_window(
            settings.app_name,
            server.url,
            width=1440,
            height=900,
            min_size=(1200, 720),
            resizable=True,
        )
        webview.start(debug=settings.debug)
        return 0
    except Exception as exc:
        logger.exception("데스크톱 프로그램 시작 실패")
        show_startup_error(
            "프로그램을 시작할 수 없습니다. Windows WebView2 설치 상태와 app.log를 확인해 주세요.\n\n"
            f"원인: {exc}"
        )
        return 1
    finally:
        server.stop()


if __name__ == "__main__":
    raise SystemExit(main())


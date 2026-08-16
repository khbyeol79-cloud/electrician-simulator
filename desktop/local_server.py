from __future__ import annotations

import logging
import socket
import threading
import time
import urllib.error
import urllib.request
import uvicorn

from app.core.config import Settings
from app.main import create_app


def find_free_port(host: str = "127.0.0.1") -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


class LocalServer:
    def __init__(self, settings: Settings):
        port = settings.port or find_free_port(settings.host)
        self.settings = settings.model_copy(update={"port": port})
        self.url = f"http://{self.settings.host}:{self.settings.port}"
        self._server: uvicorn.Server | None = None
        self._thread: threading.Thread | None = None
        self._logger = logging.getLogger("electrician_simulator")

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(self) -> None:
        if self.running:
            return
        app = create_app(self.settings)
        config = uvicorn.Config(
            app,
            host=self.settings.host,
            port=self.settings.port,
            log_level="debug" if self.settings.debug else "warning",
            access_log=self.settings.debug,
        )
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(
            target=self._server.run,
            name="electrician-local-server",
            daemon=True,
        )
        self._thread.start()
        self._logger.info("데스크톱 로컬 서버 시작 | url=%s", self.url)

    def wait_until_ready(self, timeout: float = 15.0) -> None:
        deadline = time.monotonic() + timeout
        health_url = f"{self.url}/api/health"
        while time.monotonic() < deadline:
            if self._thread and not self._thread.is_alive():
                raise RuntimeError("로컬 서버가 준비되기 전에 종료되었습니다.")
            try:
                with urllib.request.urlopen(health_url, timeout=0.5) as response:
                    if response.status == 200:
                        return
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                time.sleep(0.1)
        raise TimeoutError("로컬 서버 준비 시간이 초과되었습니다.")

    def stop(self, timeout: float = 5.0) -> None:
        if self._server:
            self._server.should_exit = True
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        self._logger.info("데스크톱 로컬 서버 종료")

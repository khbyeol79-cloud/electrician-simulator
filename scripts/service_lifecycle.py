"""Local-only graceful stop and verified USB-ready backups (no PID killing)."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import time
import uuid
import zipfile


def runtime_dir(data_dir):
    return Path(data_dir).resolve() / ".service-runtime"


class ServiceLease:
    """OS-released exclusive lease. Keep held until backup is published."""

    def __init__(self, data_dir):
        self.directory = runtime_dir(data_dir)
        self.file = None

    def __enter__(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        self.file = (self.directory / "service.lock").open("a+b")
        self.file.seek(0, 2)
        if self.file.tell() == 0:
            self.file.write(b"0")
            self.file.flush()
        self.file.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self.file.close()
            self.file = None
            raise RuntimeError("같은 자료 폴더의 서버가 실행 또는 백업 중입니다. 중복 실행하지 마세요.") from exc
        return self

    def __exit__(self, *_):
        if self.file:
            if os.name == "nt":
                import msvcrt
                self.file.seek(0)
                msvcrt.locking(self.file.fileno(), msvcrt.LK_UNLCK, 1)
            self.file.close()
            self.file = None


def lease_held(data_dir):
    try:
        with ServiceLease(data_dir):
            return False
    except RuntimeError:
        return True


def read_json(path):
    try:
        value = path.read_text(encoding="utf-8")
        result = json.loads(value)
        return result if isinstance(result, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def atomic_json(path, value):
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    with temporary.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def write_state(directory, value):
    atomic_json(directory / "status.json", {**value, "updated_at": datetime.now().isoformat(timespec="seconds")})


def verified_backup(data_dir, backup_dir):
    from scripts.service_data import backup

    directory = Path(backup_dir).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    name = f"electrician-users-{datetime.now():%Y-%m-%d_%H-%M-%S}-{uuid.uuid4().hex[:8]}"
    partial = directory / (name + ".partial.zip")
    final = directory / (name + ".zip")
    manifest = backup(data_dir, partial)
    with zipfile.ZipFile(partial) as archive:
        if archive.testzip() is not None:
            raise ValueError("ZIP 무결성 검사 실패. 원본 자료는 유지됩니다.")
        if json.loads(archive.read("manifest.json")) != manifest:
            raise ValueError("백업 목록 검사 실패")
        for entry, checksum in manifest["files"].items():
            if hashlib.sha256(archive.read(entry)).hexdigest() != checksum:
                raise ValueError("백업 체크섬 검사 실패")
    # Windows rename is exclusive and supports FAT/exFAT as well as NTFS.
    # POSIX rename would replace existing files; use an exclusive link there.
    if os.name == "nt":
        partial.rename(final)
    else:
        os.link(partial, final)
        partial.unlink()
    return final


def serve_and_backup(settings, backup_dir, cert=None, key=None):
    import uvicorn
    from app.main import create_app

    root = settings.paths.writable_root
    directory = runtime_dir(root)
    run_id = uuid.uuid4().hex
    state = {"run_id": run_id, "state": "starting", "backup": None}

    class ManagedServer(uvicorn.Server):
        clean_shutdown = False

        # Uvicorn re-raises SIGTERM after shutdown, which would skip backup.
        # Own these signal handlers until the run returns instead.
        @contextmanager
        def capture_signals(self):
            signals = [signal.SIGINT, signal.SIGTERM]
            if hasattr(signal, "SIGBREAK"):
                signals.append(signal.SIGBREAK)
            def request_exit(_sig, _frame):
                self.should_exit = True  # Never force-cancel in-flight saves.
            handlers = {s: signal.signal(s, request_exit) for s in signals}
            try:
                yield
            finally:
                for sig, handler in handlers.items():
                    signal.signal(sig, handler)

        async def startup(self, sockets=None):
            await super().startup(sockets)
            if self.started:
                state["state"] = "running"
                write_state(directory, state)
                print("서버 실행 중. 종료할 때는 서버_종료_백업.bat를 실행하세요.", flush=True)

        async def on_tick(self, counter):
            request = read_json(directory / "stop.json")
            if request.get("run_id") == run_id:
                self.should_exit = True
            return await super().on_tick(counter)

        async def shutdown(self, sockets=None):
            state["state"] = "stopping"
            write_state(directory, state)
            await super().shutdown(sockets)
            self.clean_shutdown = not self.force_exit and not getattr(self.lifespan, "shutdown_failed", True)

    with ServiceLease(root):
        write_state(directory, state)
        try:
            server = ManagedServer(uvicorn.Config(
                create_app(settings), host=settings.host, port=settings.port,
                # Windows Proactor transports can leave wait_closed pending
                # after a browser resets a socket (observed on Python 3.14).
                # Use the selector loop; keep graceful request draining intact.
                loop="asyncio:SelectorEventLoop" if os.name == "nt" else "auto",
                workers=1, proxy_headers=False, timeout_graceful_shutdown=None,
                ssl_certfile=str(cert) if cert else None, ssl_keyfile=str(key) if key else None,
            ))
            server.run()
            if not server.clean_shutdown:
                raise RuntimeError("정상 종료를 확인하지 못했습니다. 백업 완료로 처리하지 않습니다.")
            state["state"] = "backing_up"
            write_state(directory, state)
            print("서버 종료 완료. 계정·사용자 자료 백업 및 무결성 검사 중…", flush=True)
            archive = verified_backup(root, backup_dir)
            state.update(state="complete", backup=str(archive))
            write_state(directory, state)
            print(f"백업 완료: {archive}\n이 ZIP 파일을 USB에 복사하세요.", flush=True)
            return archive
        except BaseException as exc:
            state.update(state="failed", error=str(exc) or type(exc).__name__)
            write_state(directory, state)
            raise


def stop_and_wait(data_dir, timeout=180):
    directory = runtime_dir(data_dir)
    status_path = directory / "status.json"
    current = read_json(status_path)
    run_id = current.get("run_id")
    if not lease_held(data_dir) or not run_id or current.get("state") not in {"starting", "running", "stopping", "backing_up"}:
        raise RuntimeError("종료할 관리 서버를 찾지 못했습니다. 기존 수동 실행 서버는 직접 종료하고 서버_시작.bat로 실행하세요.")
    atomic_json(directory / "stop.json", {"run_id": run_id})
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        current = read_json(status_path)
        if current.get("run_id") != run_id:
            raise RuntimeError("서버 실행이 변경됐습니다. 강제 종료하지 않았습니다.")
        if current.get("state") == "complete":
            archive = Path(current["backup"])
            if not archive.is_file():
                raise RuntimeError("완료한 백업 파일을 찾지 못했습니다.")
            return archive
        if current.get("state") == "failed":
            raise RuntimeError("종료/백업 실패: " + current.get("error", "서버 창을 확인하세요."))
        if not lease_held(data_dir):
            # Re-read on the next loop, as result may have been published
            # between reading status and probing the lease.
            latest = read_json(status_path)
            if latest.get("state") not in {"complete", "failed"} or latest.get("run_id") != run_id:
                raise RuntimeError("서버가 예기치 않게 끝났습니다. 백업 완료를 확인하지 못했습니다.")
        time.sleep(0.25)
    raise TimeoutError("종료/백업 대기 시간을 초과했습니다. 강제 종료하지 않았습니다. 서버 창을 확인하세요.")

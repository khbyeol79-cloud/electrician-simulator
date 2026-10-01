from __future__ import annotations

import re
from threading import RLock

from fastapi import HTTPException, Request

from app.database import SQLiteDatabase


USER_ID_HEADER = "X-User-Id"
DEFAULT_USER_ID = "default"
_USER_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class UserDatabasePool:
    """기존 로컬 DB를 보존하면서 LAN 사용자의 SQLite 파일을 분리한다."""

    def __init__(self, default_database: SQLiteDatabase):
        self.default_database = default_database
        self.users_root = default_database.database_file.parent / "users"
        self._databases: dict[str, SQLiteDatabase] = {}
        self._lock = RLock()

    def get(self, user_id: str) -> SQLiteDatabase:
        if user_id == DEFAULT_USER_ID:
            return self.default_database
        with self._lock:
            database = self._databases.get(user_id)
            if database is None:
                database = SQLiteDatabase(self.users_root / f"{user_id}.db")
                database.initialize()
                self._databases[user_id] = database
            return database


def request_user_id(request: Request) -> str:
    if request.app.state.settings.auth_required:
        account = getattr(request.state, "account", None)
        if account is None:
            raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
        return account["user_id"]
    value = request.headers.get(USER_ID_HEADER, DEFAULT_USER_ID).strip() or DEFAULT_USER_ID
    if not _USER_ID_PATTERN.fullmatch(value):
        raise HTTPException(status_code=400, detail="사용자 식별자가 올바르지 않습니다.")
    return value


def request_database(request: Request) -> SQLiteDatabase:
    pool = getattr(request.app.state, "user_databases", None)
    if pool is None:
        return request.app.state.database
    return pool.get(request_user_id(request))

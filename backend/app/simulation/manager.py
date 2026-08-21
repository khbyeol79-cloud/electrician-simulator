from __future__ import annotations

from threading import RLock

from .engine import OperationEngine


class OperationSessionNotFound(KeyError):
    pass


class OperationSessionManager:
    def __init__(self):
        self._sessions: dict[str, tuple[str, OperationEngine]] = {}
        self._lock = RLock()

    def add(self, engine: OperationEngine, owner_id: str = "default") -> OperationEngine:
        with self._lock:
            self._sessions[engine.session_id] = (owner_id, engine)
        return engine

    def get(self, session_id: str, owner_id: str = "default") -> OperationEngine:
        with self._lock:
            entry = self._sessions.get(session_id)
        if entry is None or entry[0] != owner_id:
            raise OperationSessionNotFound(session_id)
        return entry[1]

    def delete(self, session_id: str, owner_id: str = "default") -> None:
        with self._lock:
            entry = self._sessions.get(session_id)
            if entry is None or entry[0] != owner_id:
                raise OperationSessionNotFound(session_id)
            self._sessions.pop(session_id)

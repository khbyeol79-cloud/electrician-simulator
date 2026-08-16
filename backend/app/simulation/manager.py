from __future__ import annotations

from threading import RLock

from .engine import OperationEngine


class OperationSessionNotFound(KeyError):
    pass


class OperationSessionManager:
    def __init__(self):
        self._sessions: dict[str, OperationEngine] = {}
        self._lock = RLock()

    def add(self, engine: OperationEngine) -> OperationEngine:
        with self._lock:
            self._sessions[engine.session_id] = engine
        return engine

    def get(self, session_id: str) -> OperationEngine:
        with self._lock:
            engine = self._sessions.get(session_id)
        if engine is None:
            raise OperationSessionNotFound(session_id)
        return engine

    def delete(self, session_id: str) -> None:
        with self._lock:
            if self._sessions.pop(session_id, None) is None:
                raise OperationSessionNotFound(session_id)

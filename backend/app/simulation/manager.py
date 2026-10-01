from __future__ import annotations

from threading import RLock
from time import monotonic

from .engine import OperationEngine


class OperationSessionNotFound(KeyError):
    pass


class OperationSessionManager:
    def __init__(self, *, idle_seconds=7200, per_user_limit=8, clock=monotonic):
        self._sessions: dict[str, tuple[str, OperationEngine]] = {}
        self._lock = RLock()
        self._seen: dict[str, float] = {}
        self._clock, self._idle_seconds, self._per_user_limit = clock, idle_seconds, per_user_limit

    def _expire(self):
        for session_id, seen in list(self._seen.items()):
            if self._clock() - seen >= self._idle_seconds:
                self._sessions.pop(session_id, None)
                self._seen.pop(session_id, None)

    def add(self, engine: OperationEngine, owner_id: str = "default") -> OperationEngine:
        with self._lock:
            self._expire()
            owned = sorted((sid for sid, (owner, _) in self._sessions.items() if owner == owner_id), key=self._seen.get)
            while len(owned) >= self._per_user_limit:
                oldest = owned.pop(0)
                self._sessions.pop(oldest)
                self._seen.pop(oldest)
            self._sessions[engine.session_id] = (owner_id, engine)
            self._seen[engine.session_id] = self._clock()
        return engine

    def get(self, session_id: str, owner_id: str = "default") -> OperationEngine:
        with self._lock:
            self._expire()
            entry = self._sessions.get(session_id)
            if entry is None or entry[0] != owner_id:
                raise OperationSessionNotFound(session_id)
            self._seen[session_id] = self._clock()
        return entry[1]

    def delete(self, session_id: str, owner_id: str = "default") -> None:
        with self._lock:
            entry = self._sessions.get(session_id)
            if entry is None or entry[0] != owner_id:
                raise OperationSessionNotFound(session_id)
            self._sessions.pop(session_id)
            self._seen.pop(session_id, None)

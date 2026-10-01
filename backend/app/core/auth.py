"""LAN account authentication. Legacy study databases are never claimed by nickname.

Passwords use OWASP's scrypt N=2**15/r=8/p=3 profile. Cookies contain only a
random secret; only its hash is persisted. No caller-provided user ID is trusted.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import hmac
import json
from pathlib import Path
import secrets
import sqlite3
from threading import BoundedSemaphore
import time

from fastapi import HTTPException

COOKIE_NAME = "electrician_session"
MIN_PASSWORD_LENGTH = 6
MAX_PASSWORD_LENGTH = 128
_HASH_SLOTS = BoundedSemaphore(2)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def password_hash(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    with _HASH_SLOTS:
        key = hashlib.scrypt(password.encode("utf-8"), salt=bytes.fromhex(salt),
                             n=32768, r=8, p=3, maxmem=64 * 1024 * 1024, dklen=32)
    return f"scrypt32768r8p3${salt}${key.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, salt, _ = encoded.split("$")
        return algorithm == "scrypt32768r8p3" and hmac.compare_digest(password_hash(password, salt), encoded)
    except (ValueError, TypeError):
        return False


class AuthStore:
    def __init__(self, path: Path, *, idle_seconds=1800, lifetime_seconds=36000, clock=time.time):
        self.path = path
        self.idle_seconds = idle_seconds
        self.lifetime_seconds = lifetime_seconds
        self.clock = clock
        self._dummy_hash = password_hash(secrets.token_urlsafe(24))

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS accounts (
                    user_id TEXT PRIMARY KEY, username TEXT NOT NULL UNIQUE,
                    nickname TEXT NOT NULL, password_hash TEXT NOT NULL, created_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS auth_sessions (
                    token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL,
                    csrf TEXT NOT NULL, created_at REAL NOT NULL, last_seen REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS auth_sessions_user ON auth_sessions(user_id);
                CREATE TABLE IF NOT EXISTS auth_limits (
                    bucket TEXT PRIMARY KEY, started_at REAL NOT NULL, attempts INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS account_admins (user_id TEXT PRIMARY KEY);
                CREATE TABLE IF NOT EXISTS service_options (name TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS admin_audit (
                    id INTEGER PRIMARY KEY, actor TEXT NOT NULL, action TEXT NOT NULL,
                    target TEXT NOT NULL, created_at REAL NOT NULL
                );
            """)

    def rate_limit(self, bucket: str, limit: int, window=900):
        now = self.clock()
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("DELETE FROM auth_limits WHERE started_at < ?", (now - window,))
            db.execute("INSERT INTO auth_limits VALUES (?, ?, 1) ON CONFLICT(bucket) DO UPDATE SET attempts=attempts+1",
                       (digest(bucket), now))
            attempts = db.execute("SELECT attempts FROM auth_limits WHERE bucket=?", (digest(bucket),)).fetchone()[0]
        if attempts > limit:
            raise HTTPException(429, "시도가 너무 많습니다. 15분 뒤 다시 시도하세요.", headers={"Retry-After": "900"})

    def register(self, username: str, nickname: str, password: str):
        user_id = "acct_" + secrets.token_hex(16)
        encoded = password_hash(password)
        try:
            with self.connection() as db:
                db.execute("INSERT INTO accounts VALUES (?, ?, ?, ?, ?)",
                           (user_id, username, nickname, encoded, self.clock()))
        except sqlite3.IntegrityError as exc:
            raise HTTPException(409, "사용할 수 없는 아이디입니다.") from exc
        return {"user_id": user_id, "username": username, "nickname": nickname}

    def login(self, username: str, password: str):
        with self.connection() as db:
            account = db.execute("SELECT * FROM accounts WHERE username=?", (username,)).fetchone()
        valid = verify_password(password, account["password_hash"] if account else self._dummy_hash)
        if not valid or account is None:
            raise HTTPException(401, "아이디 또는 비밀번호를 확인하세요.")
        return {key: account[key] for key in ("user_id", "username", "nickname")}

    def create_session(self, user_id: str, old_token: str | None = None):
        token, csrf, now = secrets.token_urlsafe(32), secrets.token_urlsafe(32), self.clock()
        with self.connection() as db:
            db.execute("DELETE FROM auth_sessions WHERE last_seen < ? OR created_at < ?",
                       (now - self.idle_seconds, now - self.lifetime_seconds))
            if old_token:
                db.execute("DELETE FROM auth_sessions WHERE token_hash=?", (digest(old_token),))
            # Bound forgotten browser sessions without affecting unrelated accounts.
            db.execute("DELETE FROM auth_sessions WHERE user_id=? AND token_hash NOT IN "
                       "(SELECT token_hash FROM auth_sessions WHERE user_id=? ORDER BY created_at DESC LIMIT 4)",
                       (user_id, user_id))
            db.execute("INSERT INTO auth_sessions VALUES (?, ?, ?, ?, ?)", (digest(token), user_id, csrf, now, now))
        return token, csrf

    def authenticate(self, token: str | None):
        if not token or len(token) > 128:
            return None
        now = self.clock()
        with self.connection() as db:
            row = db.execute("SELECT s.*, a.username, a.nickname FROM auth_sessions s "
                             "JOIN accounts a ON a.user_id=s.user_id WHERE token_hash=?", (digest(token),)).fetchone()
            if row is None:
                return None
            if now - row["last_seen"] >= self.idle_seconds or now - row["created_at"] >= self.lifetime_seconds:
                db.execute("DELETE FROM auth_sessions WHERE token_hash=?", (digest(token),))
                return None
            if now - row["last_seen"] >= 60:
                db.execute("UPDATE auth_sessions SET last_seen=? WHERE token_hash=?", (now, digest(token)))
        return {key: row[key] for key in ("user_id", "username", "nickname", "csrf")}

    def logout(self, token: str | None):
        if token:
            with self.connection() as db:
                db.execute("DELETE FROM auth_sessions WHERE token_hash=?", (digest(token),))

    def reset_password(self, username: str, password: str):
        encoded = password_hash(password)
        with self.connection() as db:
            row = db.execute("SELECT user_id FROM accounts WHERE username=?", (username,)).fetchone()
            if row is None:
                raise ValueError("계정을 찾을 수 없습니다.")
            db.execute("UPDATE accounts SET password_hash=? WHERE username=?", (encoded, username))
            db.execute("DELETE FROM auth_sessions WHERE user_id=?", (row["user_id"],))

    def admin_reset_password(self, user_id, new_password, actor_id, actor_password):
        self.rate_limit("admin-password-reset:" + actor_id, 10)
        with self.connection() as db:
            actor = db.execute("SELECT username,password_hash FROM accounts WHERE user_id=?", (actor_id,)).fetchone()
        if actor is None or not verify_password(actor_password, actor["password_hash"]):
            raise HTTPException(403, "관리자 비밀번호를 확인하세요.")
        encoded = password_hash(new_password)
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            # Check again inside the write transaction after expensive hashing.
            valid_actor = db.execute("SELECT 1 FROM accounts a JOIN account_admins m ON m.user_id=a.user_id "
                                     "WHERE a.user_id=? AND a.password_hash=?", (actor_id, actor["password_hash"])).fetchone()
            if not valid_actor:
                raise HTTPException(403, "관리자 권한 또는 비밀번호가 변경됐습니다. 다시 로그인하세요.")
            target = db.execute("SELECT username FROM accounts WHERE user_id=?", (user_id,)).fetchone()
            if target is None:
                raise HTTPException(404, "계정을 찾을 수 없습니다.")
            db.execute("UPDATE accounts SET password_hash=? WHERE user_id=?", (encoded, user_id))
            db.execute("DELETE FROM auth_sessions WHERE user_id=?", (user_id,))
            self._audit(db, actor["username"], "reset-password", target["username"])

    def is_admin(self, user_id: str) -> bool:
        with self.connection() as db:
            return db.execute("SELECT 1 FROM account_admins WHERE user_id=?", (user_id,)).fetchone() is not None

    def set_admin(self, username: str, enabled: bool):
        """Local operator command only. Never exposed through registration or HTTP."""
        with self.connection() as db:
            row = db.execute("SELECT user_id FROM accounts WHERE username=?", (username,)).fetchone()
            if row is None:
                raise ValueError("계정을 찾을 수 없습니다. 먼저 일반 회원가입을 해 주세요.")
            if enabled:
                db.execute("INSERT OR IGNORE INTO account_admins VALUES (?)", (row["user_id"],))
            else:
                db.execute("DELETE FROM account_admins WHERE user_id=?", (row["user_id"],))
            # A pre-existing browser session must not acquire a new privilege.
            db.execute("DELETE FROM auth_sessions WHERE user_id=?", (row["user_id"],))
            self._audit(db, "local-operator", "grant-admin" if enabled else "revoke-admin", username)

    def _audit(self, db, actor, action, target):
        db.execute("INSERT INTO admin_audit(actor, action, target, created_at) VALUES (?, ?, ?, ?)",
                   (actor, action, target, self.clock()))

    def service_option(self, name, default=None):
        with self.connection() as db:
            row = db.execute("SELECT value FROM service_options WHERE name=?", (name,)).fetchone()
        return json.loads(row[0]) if row else default

    def save_service_option(self, name, value, actor):
        with self.connection() as db:
            db.execute("INSERT INTO service_options VALUES (?, ?) ON CONFLICT(name) DO UPDATE SET value=excluded.value",
                       (name, json.dumps(value)))
            self._audit(db, actor, "update-" + name, json.dumps(value))

    def clear_network_option(self):
        with self.connection() as db:
            db.execute("DELETE FROM service_options WHERE name='network'")
            self._audit(db, "local-operator", "clear-network", "env-file")

    def managed_accounts(self):
        now = self.clock()
        with self.connection() as db:
            rows = db.execute("""
                SELECT a.user_id, a.username, a.nickname, a.created_at,
                    EXISTS(SELECT 1 FROM account_admins m WHERE m.user_id=a.user_id) AS is_admin,
                    COUNT(s.token_hash) AS active_sessions, MAX(s.last_seen) AS last_seen
                FROM accounts a LEFT JOIN auth_sessions s ON s.user_id=a.user_id
                    AND s.last_seen > ? AND s.created_at > ?
                GROUP BY a.user_id ORDER BY a.created_at DESC, a.username
            """, (now - self.idle_seconds, now - self.lifetime_seconds)).fetchall()
        return [{**dict(row), "is_admin": bool(row["is_admin"])} for row in rows]

    def revoke_user_sessions(self, user_id, actor):
        with self.connection() as db:
            account = db.execute("SELECT username FROM accounts WHERE user_id=?", (user_id,)).fetchone()
            if account is None:
                raise HTTPException(404, "계정을 찾을 수 없습니다.")
            db.execute("DELETE FROM auth_sessions WHERE user_id=?", (user_id,))
            self._audit(db, actor, "logout-account", account["username"])

    def audit_events(self):
        with self.connection() as db:
            return [dict(row) for row in db.execute(
                "SELECT actor, action, target, created_at FROM admin_audit ORDER BY id DESC LIMIT 30")]

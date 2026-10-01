"""Small LAN service settings, independent of study data and circuit engines."""
from __future__ import annotations

from contextlib import closing
from ipaddress import IPv4Address, IPv4Network
import json
import socket
import sqlite3

from pydantic import BaseModel, ConfigDict, Field, field_validator

LAN_NETWORKS = tuple(IPv4Network(value) for value in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"))


def is_lan_ipv4(value: str) -> bool:
    try:
        address = IPv4Address(value)
        return any(address in network for network in LAN_NETWORKS)
    except ValueError:
        return False


class NetworkOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    host: str
    port: int = Field(ge=1024, le=65535, strict=True)

    @field_validator("host")
    @classmethod
    def validate_host(cls, value):
        if value not in {"127.0.0.1", "0.0.0.0"} and not is_lan_ipv4(value):
            raise ValueError("127.0.0.1, 0.0.0.0 또는 사설 IPv4 주소만 지정할 수 있습니다.")
        return value


def apply_saved_network(settings):
    """Only the managed launcher may change the bind socket, never a web request.

    Read-only lookup works before lifespan/schema initialization and never
    creates or migrates a user's database during settings discovery.
    """
    path = settings.paths.writable_root / "accounts.db"
    saved = None
    if path.is_file():
        with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
            if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='service_options'").fetchone():
                row = db.execute("SELECT value FROM service_options WHERE name='network'").fetchone()
                saved = NetworkOptions.model_validate(json.loads(row[0])) if row else None
    values = settings.model_dump()
    values["paths"] = settings.paths
    values["service_managed"] = True
    if saved:
        values.update(host=saved.host, port=saved.port, allow_lan=saved.host != "127.0.0.1")
    return type(settings)(**values)


def lan_addresses():
    try:
        return sorted({entry[4][0] for entry in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
                       if is_lan_ipv4(entry[4][0])})
    except OSError:
        return []


def registration_open(request):
    settings = request.app.state.settings
    if not settings.auth_required:
        return False
    return request.app.state.auth_store.service_option("registration_open", settings.registration_open)

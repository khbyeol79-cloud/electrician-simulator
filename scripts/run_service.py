"""Portable single-process web service. Does not change firewall/router settings."""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import sys


def load_service(env_file, cert=None, key=None):
    allowed = {"APP_MODE", "APP_ENV", "APP_DEBUG", "ALLOW_LAN", "AUTH_REQUIRED", "APP_HOST", "APP_PORT",
               "ELECTRICIAN_DATA_DIR", "REGISTRATION_OPEN", "AUTH_COOKIE_SECURE", "AUTH_IDLE_SECONDS",
               "AUTH_LIFETIME_SECONDS", "ALLOWED_ORIGINS"}
    for line in env_file.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        env_key, separator, value = line.partition("=")
        if not separator or env_key not in allowed:
            raise ValueError("Unsupported service configuration field")
        os.environ[env_key] = value.strip()
    os.environ["AUTH_REQUIRED"] = "true"
    os.environ["APP_MODE"] = "web"
    os.environ["APP_DEBUG"] = "false"
    if bool(cert) != bool(key):
        raise ValueError("Both --cert and --key are required for TLS")
    if cert:
        os.environ["AUTH_COOKIE_SECURE"] = "true"
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
    from app.core.config import load_settings
    from app.core.service_admin import apply_saved_network
    settings = apply_saved_network(load_settings())
    return settings


def check_service(settings, cert=None):
    print(f"Account/study data directory: {settings.paths.writable_root}")
    print(f"Listening address: {settings.host}:{settings.port} (saved admin settings take priority)")
    if not settings.resolved_static_dir.joinpath("index.html").exists():
        raise ValueError("Build frontend first: npm ci && npm run build")
    if not cert:
        print("WARNING: HTTP does not encrypt passwords. Use institution-approved HTTPS before real account enrollment.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--cert", type=Path)
    parser.add_argument("--key", type=Path)
    args = parser.parse_args()
    settings = load_service(args.env_file, args.cert, args.key)
    check_service(settings, args.cert)
    import uvicorn
    from app.main import create_app
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.service_lifecycle import ServiceLease, runtime_dir, write_state
    # In-memory operation sessions require one worker. Do not enable reload.
    with ServiceLease(settings.paths.writable_root):
        write_state(runtime_dir(settings.paths.writable_root), {"state": "manual"})
        uvicorn.run(create_app(settings), host=settings.host, port=settings.port, workers=1,
                    loop="asyncio:SelectorEventLoop" if os.name == "nt" else "auto",
                    proxy_headers=False, ssl_certfile=str(args.cert) if args.cert else None,
                    ssl_keyfile=str(args.key) if args.key else None)


if __name__ == "__main__":
    main()

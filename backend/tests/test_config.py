from app.core.config import Settings


def test_web_lan_host_requires_explicit_permission():
    assert Settings(host="0.0.0.0", allow_lan=False).host == "127.0.0.1"
    assert Settings(host="0.0.0.0", allow_lan=True).host == "0.0.0.0"


def test_desktop_is_always_bound_to_loopback():
    settings = Settings(app_mode="desktop", host="0.0.0.0", allow_lan=True)
    assert settings.host == "127.0.0.1"


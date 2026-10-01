from types import SimpleNamespace

from desktop.launcher import configure_webview_downloads


def test_desktop_webview_allows_attachment_downloads():
    webview = SimpleNamespace(settings={"ALLOW_DOWNLOADS": False})

    configure_webview_downloads(webview)

    assert webview.settings["ALLOW_DOWNLOADS"] is True

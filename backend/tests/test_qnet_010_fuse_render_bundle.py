from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_source_wiring_board_contains_dual_fuse_renderer():
    source = (PROJECT_ROOT / "frontend" / "src" / "features" / "wiring" / "components" / "WiringBoard.tsx").read_text(encoding="utf-8")
    styles = (PROJECT_ROOT / "frontend" / "src" / "styles" / "global.css").read_text(encoding="utf-8")
    assert "isDualFuseBoardItem" in source
    assert "dual-fuse-holder" in source
    assert "dual-fuse-cartridge" in source
    assert ".dual-fuse-body .dual-fuse-holder" in styles

from __future__ import annotations

import json
import shutil

import pytest

from app.services import CatalogError, CatalogService
from problem_test_utils import PROJECT_ROOT


def test_socket_catalog_has_exact_physical_base_layouts():
    catalog = CatalogService(PROJECT_ROOT / "catalog", PROJECT_ROOT / "schemas")
    socket_8p = catalog.get_socket_type("socket_8p_base")
    socket_12p = catalog.get_socket_type("socket_12p_base")
    assert socket_8p is not None and socket_12p is not None
    assert socket_8p.pin_count == 8
    assert socket_8p.rows[0].pins == [6, 5, 4, 3]
    assert socket_8p.rows[1].pins == [7, 8, 1, 2]
    assert socket_8p.pins == set(range(1, 9))
    assert socket_12p.pin_count == 12
    assert socket_12p.rows[0].pins == [1, 2, 3, 4, 5, 6]
    assert socket_12p.rows[1].pins == [7, 8, 9, 10, 11, 12]
    assert socket_12p.pins == set(range(1, 13))
    assert socket_8p.center.symmetric is True
    assert socket_12p.center.symmetric is True


@pytest.mark.parametrize(
    "pins",
    ([6, 5, 4, 4], [6, 5, 4]),
)
def test_socket_catalog_rejects_duplicate_or_missing_pin(tmp_path, pins):
    catalog_dir = tmp_path / "catalog"
    shutil.copytree(PROJECT_ROOT / "catalog", catalog_dir)
    data_path = catalog_dir / "socket_types.json"
    data = json.loads(data_path.read_text(encoding="utf-8"))
    data["socket_types"][0]["rows"][0]["pins"] = pins
    data_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(CatalogError):
        CatalogService(catalog_dir, PROJECT_ROOT / "schemas")

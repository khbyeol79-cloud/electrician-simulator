from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from app.domain.catalog import DeviceCatalog, DeviceType, SocketCatalog, SocketType


class CatalogError(ValueError):
    """공통 카탈로그가 손상되었을 때 발생하는 사용자 데이터 오류."""


class CatalogService:
    def __init__(self, catalog_dir: Path, schemas_dir: Path):
        self.catalog_dir = catalog_dir.resolve()
        self.schemas_dir = schemas_dir.resolve()
        self.socket_catalog = self._load(
            "socket_types.json", "socket-catalog.schema.json", SocketCatalog
        )
        self.device_catalog = self._load(
            "device_types.json", "device-catalog.schema.json", DeviceCatalog
        )
        self._socket_types = self._unique_by_id(
            self.socket_catalog.socket_types, "socket_type_id"
        )
        self._device_types = self._unique_by_id(
            self.device_catalog.device_types, "device_type_id"
        )
        self._validate_socket_rules()
        self._validate_device_references()

    def _load(self, data_name: str, schema_name: str, model):
        try:
            data = json.loads((self.catalog_dir / data_name).read_text(encoding="utf-8"))
            schema = json.loads((self.schemas_dir / schema_name).read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise CatalogError(f"카탈로그 파일을 읽을 수 없습니다: {data_name}: {exc}") from exc
        errors = sorted(
            Draft202012Validator(schema).iter_errors(data),
            key=lambda error: list(error.absolute_path),
        )
        if errors:
            error = errors[0]
            path = ".".join(str(part) for part in error.absolute_path) or "root"
            raise CatalogError(f"카탈로그 형식 오류: {data_name}:{path}: {error.message}")
        return model.model_validate(data)

    @staticmethod
    def _unique_by_id(items: list[Any], field: str) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for item in items:
            item_id = getattr(item, field)
            if item_id in result:
                raise CatalogError(f"카탈로그 ID가 중복됩니다: {item_id}")
            result[item_id] = item
        return result

    def _validate_socket_rules(self) -> None:
        required = {
            "socket_8p_base": ([6, 5, 4, 3], [7, 8, 1, 2]),
            "socket_12p_base": ([1, 2, 3, 4, 5, 6], [7, 8, 9, 10, 11, 12]),
        }
        for socket_id, (expected_top, expected_bottom) in required.items():
            socket = self._socket_types.get(socket_id)
            if socket is None:
                raise CatalogError(f"필수 소켓 규격이 없습니다: {socket_id}")
            rows = {row.row_id: row.pins for row in socket.rows}
            if rows.get("top") != expected_top or rows.get("bottom") != expected_bottom:
                raise CatalogError(f"{socket_id}의 실제 베이스 핀 배열이 올바르지 않습니다.")
            all_pins = [pin for row in socket.rows for pin in row.pins]
            if len(all_pins) != socket.pin_count or set(all_pins) != set(
                range(1, socket.pin_count + 1)
            ):
                raise CatalogError(f"{socket_id}에 중복되거나 누락된 핀이 있습니다.")
            if not socket.center.symmetric:
                raise CatalogError(f"{socket_id} 중앙 대칭 설정이 필요합니다.")

    def _validate_device_references(self) -> None:
        for device in self.device_catalog.device_types:
            if device.socket_type_id and device.socket_type_id not in self._socket_types:
                raise CatalogError(
                    f"{device.device_type_id}가 존재하지 않는 소켓을 참조합니다."
                )

    def socket_types(self) -> list[SocketType]:
        return list(self.socket_catalog.socket_types)

    def device_types(self) -> list[DeviceType]:
        return list(self.device_catalog.device_types)

    def get_socket_type(self, socket_type_id: str) -> SocketType | None:
        return self._socket_types.get(socket_type_id)

    def get_device_type(self, device_type_id: str) -> DeviceType | None:
        return self._device_types.get(device_type_id)

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from app.domain.catalog import DeviceCatalog, DeviceType, SocketCatalog, SocketType
from app.domain.device_behavior import (
    BehaviorConfigurableProperty,
    DeviceBehaviorCatalog,
    DeviceBehaviorModel,
)


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
        self.device_behavior_catalog = self._load(
            "device_behaviors.json",
            "device-behavior-catalog.schema.json",
            DeviceBehaviorCatalog,
        )
        self._socket_types = self._unique_by_id(
            self.socket_catalog.socket_types, "socket_type_id"
        )
        self._device_types = self._unique_by_id(
            self.device_catalog.device_types, "device_type_id"
        )
        self._device_behaviors = self._unique_by_id(
            self.device_behavior_catalog.models, "model_id"
        )
        self._validate_socket_rules()
        self._validate_device_references()
        self._validate_behavior_models()

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

    @staticmethod
    def _behavior_error(index: int, model_id: str, field: str, message: str) -> CatalogError:
        return CatalogError(
            f"device_behaviors.json: models[{index}].{field}: "
            f"모델 {model_id}: {message}"
        )

    @staticmethod
    def _setting_matches(value: object, definition: BehaviorConfigurableProperty) -> bool:
        if definition.value_type == "boolean":
            return isinstance(value, bool)
        if definition.value_type == "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        if definition.value_type == "number":
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        if definition.value_type == "voltage_type":
            return value in {"AC", "DC"}
        if definition.value_type == "color":
            return value in {"red", "green", "yellow", "white"}
        return isinstance(value, str)

    @staticmethod
    def _duplicates(values: list[object]) -> set[object]:
        seen: set[object] = set()
        return {value for value in values if value in seen or seen.add(value)}

    def _validate_behavior_models(self) -> None:
        for index, model in enumerate(self.device_behavior_catalog.models):
            self._validate_behavior_model(index, model)

    def _validate_behavior_model(self, index: int, model: DeviceBehaviorModel) -> None:
        fail = lambda field, message: self._behavior_error(index, model.model_id, field, message)
        if model.device_type_id not in self._device_types:
            raise fail("device_type_id", f"존재하지 않는 기구 종류 {model.device_type_id}를 참조합니다.")
        if self._duplicates(list(model.compatible_socket_type_ids)):
            raise fail("compatible_socket_type_ids", "호환 소켓 ID가 중복됩니다.")
        if self._duplicates(list(model.capabilities)):
            raise fail("capabilities", "capability가 중복됩니다.")
        for socket_index, socket_id in enumerate(model.compatible_socket_type_ids):
            if socket_id not in self._socket_types:
                raise fail(
                    f"compatible_socket_type_ids[{socket_index}]",
                    f"존재하지 않는 소켓 {socket_id}를 참조합니다.",
                )

        terminal_keys = [item.terminal_key for item in model.terminals]
        terminal_suffixes = [item.terminal_suffix for item in model.terminals]
        pin_numbers = [item.pin_number for item in model.terminals if item.pin_number is not None]
        for field, values, label in (
            ("terminals", terminal_keys, "terminal_key"),
            ("terminals", terminal_suffixes, "terminal_suffix"),
            ("terminals", pin_numbers, "pin_number"),
        ):
            duplicates = self._duplicates(values)
            if duplicates:
                raise fail(field, f"{label}가 중복됩니다: {sorted(duplicates, key=str)[0]}")
        terminals = set(terminal_keys)
        for terminal_index, terminal in enumerate(model.terminals):
            if terminal.pin_number is None:
                continue
            if not model.compatible_socket_type_ids:
                raise fail(
                    f"terminals[{terminal_index}].pin_number",
                    "핀 번호가 있는 모델에는 호환 소켓이 필요합니다.",
                )
            if not any(
                terminal.pin_number in self._socket_types[socket_id].pins
                for socket_id in model.compatible_socket_type_ids
            ):
                raise fail(
                    f"terminals[{terminal_index}].pin_number",
                    f"핀 {terminal.pin_number}이 호환 소켓 범위를 벗어납니다.",
                )

        properties = [item.property_key for item in model.configurable_properties]
        duplicate_properties = self._duplicates(properties)
        if duplicate_properties:
            raise fail("configurable_properties", f"설정 키가 중복됩니다: {next(iter(duplicate_properties))}")
        property_map = {item.property_key: item for item in model.configurable_properties}
        for property_index, definition in enumerate(model.configurable_properties):
            path = f"configurable_properties[{property_index}]"
            if definition.minimum is not None and definition.maximum is not None and definition.minimum > definition.maximum:
                raise fail(path, "minimum이 maximum보다 큽니다.")
            if definition.required and definition.default is None:
                continue
            if definition.default is None:
                continue
            if not self._setting_matches(definition.default, definition):
                raise fail(f"{path}.default", "기본값의 타입이 value_type과 일치하지 않습니다.")
            if definition.choices and definition.default not in definition.choices:
                raise fail(f"{path}.default", "기본값이 choices에 포함되지 않습니다.")
            if isinstance(definition.default, (int, float)) and not isinstance(definition.default, bool):
                if definition.minimum is not None and definition.default < definition.minimum:
                    raise fail(f"{path}.default", "기본값이 minimum보다 작습니다.")
                if definition.maximum is not None and definition.default > definition.maximum:
                    raise fail(f"{path}.default", "기본값이 maximum보다 큽니다.")

        coil_keys = [item.coil_key for item in model.coils]
        if self._duplicates(coil_keys):
            raise fail("coils", "coil_key가 중복됩니다.")
        coil_map = {item.coil_key: item for item in model.coils}
        for coil_index, coil in enumerate(model.coils):
            for field_name in ("terminal_a_key", "terminal_b_key"):
                key = getattr(coil, field_name)
                if key not in terminals:
                    raise fail(f"coils[{coil_index}].{field_name}", f"존재하지 않는 단자 키 {key}를 참조합니다.")
            if coil.terminal_a_key == coil.terminal_b_key:
                raise fail(f"coils[{coil_index}]", "코일의 두 단자는 서로 달라야 합니다.")
            required_property_types = {
                coil.rated_voltage_property_key: {"integer", "number"},
                coil.voltage_type_property_key: {"voltage_type"},
            }
            if coil.frequency_property_key:
                required_property_types[coil.frequency_property_key] = {"integer", "number"}
            for key, allowed_types in required_property_types.items():
                definition = property_map.get(key)
                if definition is None or definition.value_type not in allowed_types:
                    raise fail(f"coils[{coil_index}]", f"코일 설정 키 {key}의 정의 또는 타입이 올바르지 않습니다.")

        contact_keys = [item.contact_key for item in model.contacts]
        if self._duplicates(contact_keys):
            raise fail("contacts", "contact_key가 중복됩니다.")
        generated_suffixes = terminal_suffixes + [item.id_suffix for item in model.coils] + [
            item.id_suffix for item in model.contacts
        ]
        if model.timer:
            generated_suffixes.append(model.timer.id_suffix)
        duplicate_suffixes = self._duplicates(generated_suffixes)
        if duplicate_suffixes:
            raise fail(
                "terminals/coils/contacts",
                f"인스턴스에서 충돌하는 ID suffix가 있습니다: {next(iter(duplicate_suffixes))}",
            )
        contact_map = {item.contact_key: item for item in model.contacts}
        for contact_index, contact in enumerate(model.contacts):
            referenced = [contact.common_terminal_key, contact.switched_terminal_key]
            referenced.extend(key for key in (contact.nc_terminal_key, contact.no_terminal_key) if key)
            for key in referenced:
                if key not in terminals:
                    raise fail(f"contacts[{contact_index}]", f"존재하지 않는 단자 키 {key}를 참조합니다.")
            expected_state = "open" if contact.contact_type == "NO" else "closed" if contact.contact_type == "NC" else None
            if expected_state and contact.normal_state != expected_state:
                raise fail(f"contacts[{contact_index}].normal_state", "접점 종류와 기본 상태가 모순됩니다.")
            if contact.contact_type == "CHANGEOVER" and (not contact.nc_terminal_key or not contact.no_terminal_key):
                raise fail(f"contacts[{contact_index}]", "CHANGEOVER 접점에는 NC·NO 단자 키가 모두 필요합니다.")
            if contact.contact_type != "CHANGEOVER" and (contact.nc_terminal_key or contact.no_terminal_key):
                raise fail(f"contacts[{contact_index}]", "NO·NC 접점에는 CHANGEOVER 전용 단자를 지정할 수 없습니다.")
            if contact.actuation == "coil" and contact.controlled_by_key not in coil_map:
                raise fail(f"contacts[{contact_index}].controlled_by_key", f"존재하지 않는 코일 키 {contact.controlled_by_key}를 참조합니다.")
            if contact.actuation == "timer" and model.timer is None:
                raise fail(f"contacts[{contact_index}].actuation", "계시 접점에 타이머 정의가 없습니다.")
            if contact.actuation == "manual" and model.control is None:
                raise fail(f"contacts[{contact_index}].actuation", "수동 접점에 control 정의가 없습니다.")
            if contact.actuation == "protection" and model.protection is None:
                raise fail(f"contacts[{contact_index}].actuation", "보호 접점에 protection 정의가 없습니다.")

        connection_pairs: set[tuple[str, str]] = set()
        for connection_index, connection in enumerate(model.intrinsic_connections):
            for field_name in ("from_terminal_key", "to_terminal_key"):
                key = getattr(connection, field_name)
                if key not in terminals:
                    raise fail(f"intrinsic_connections[{connection_index}].{field_name}", f"존재하지 않는 단자 키 {key}를 참조합니다.")
            if connection.from_terminal_key == connection.to_terminal_key:
                raise fail(f"intrinsic_connections[{connection_index}]", "같은 단자끼리 내부 연결할 수 없습니다.")
            pair = tuple(sorted((connection.from_terminal_key, connection.to_terminal_key)))
            if pair in connection_pairs:
                raise fail(f"intrinsic_connections[{connection_index}]", "내부 연결이 중복됩니다.")
            connection_pairs.add(pair)

        if model.control:
            contact = contact_map.get(model.control.contact_key)
            if contact is None or contact.actuation != "manual":
                raise fail("control.contact_key", "수동 조작 접점을 참조해야 합니다.")
        if model.timer:
            if model.timer.coil_key not in coil_map:
                raise fail("timer.coil_key", "존재하지 않는 타이머 코일을 참조합니다.")
            delay = property_map.get(model.timer.delay_property_key)
            if delay is None or delay.value_type != "integer":
                raise fail("timer.delay_property_key", "정수형 지연시간 설정을 참조해야 합니다.")
            for timed_index, key in enumerate(model.timer.timed_contact_keys):
                contact = contact_map.get(key)
                if contact is None or contact.actuation != "timer" or contact.controlled_by_key != model.timer.timer_key:
                    raise fail(f"timer.timed_contact_keys[{timed_index}]", "올바른 계시 접점을 참조하지 않습니다.")
        if model.indicator:
            for field_name in ("terminal_a_key", "terminal_b_key"):
                if getattr(model.indicator, field_name) not in terminals:
                    raise fail(f"indicator.{field_name}", "존재하지 않는 표시등 단자를 참조합니다.")
            color = property_map.get(model.indicator.display_color_property_key)
            if color is None or color.value_type != "color":
                raise fail("indicator.display_color_property_key", "색상 설정을 참조해야 합니다.")
        if model.motor:
            for key in model.motor.phase_terminal_keys:
                if key not in terminals:
                    raise fail("motor.phase_terminal_keys", f"존재하지 않는 모터 단자 키 {key}를 참조합니다.")
        if model.protection:
            if model.protection.default_reset_mode not in model.protection.reset_modes:
                raise fail("protection.default_reset_mode", "기본 복귀 방식이 허용 목록에 없습니다.")
            for key in model.protection.contact_keys:
                contact = contact_map.get(key)
                if contact is None or contact.actuation != "protection":
                    raise fail("protection.contact_keys", f"올바른 보호 접점 {key}를 참조하지 않습니다.")

        capability_checks = {
            "coil": bool(model.coils),
            "relay_contacts": any(item.actuation == "coil" for item in model.contacts),
            "timed_contacts": model.timer is not None,
            "manual_control": bool(
                model.control and model.control.control_type in {"pushbutton", "selector"}
            ),
            "limit_control": bool(
                model.control and model.control.control_type == "limit_switch"
            ),
            "indicator": model.indicator is not None,
            "three_phase_load": model.motor is not None,
            "overload_protection": model.protection is not None,
        }
        for capability, present in capability_checks.items():
            if capability in model.capabilities and not present:
                raise fail("capabilities", f"{capability} capability에 필요한 동작 정의가 없습니다.")
            if present and capability not in model.capabilities:
                raise fail("capabilities", f"{capability} 동작 정의에 해당 capability가 필요합니다.")
        if model.coils and "coil" not in model.capabilities:
            raise fail("capabilities", "코일이 있는 모델에는 coil capability가 필요합니다.")
        if "contactor" in model.capabilities and (not model.coils or not model.contacts):
            raise fail("capabilities", "contactor capability에는 코일과 접점 정의가 필요합니다.")

        serialized = model.model_dump(mode="json")
        banned_keys = {"expected_nets", "answer", "problem_id", "wiring_connections"}
        def walk(value: object, path: str = "") -> None:
            if isinstance(value, dict):
                for key, item in value.items():
                    if key in banned_keys:
                        raise fail(path or "root", f"문제·정답 전용 필드 {key}를 포함할 수 없습니다.")
                    walk(item, f"{path}.{key}" if path else key)
            elif isinstance(value, list):
                for item_index, item in enumerate(value):
                    walk(item, f"{path}[{item_index}]")
            elif isinstance(value, str) and ("TB5-" in value or "TB6-" in value):
                raise fail(path, "특정 자유 TB 번호를 기구 모델에 포함할 수 없습니다.")
        walk(serialized)

    def socket_types(self) -> list[SocketType]:
        return list(self.socket_catalog.socket_types)

    def device_types(self) -> list[DeviceType]:
        return list(self.device_catalog.device_types)

    def device_behaviors(self) -> list[DeviceBehaviorModel]:
        return list(self.device_behavior_catalog.models)

    def get_socket_type(self, socket_type_id: str) -> SocketType | None:
        return self._socket_types.get(socket_type_id)

    def get_device_type(self, device_type_id: str) -> DeviceType | None:
        return self._device_types.get(device_type_id)

    def get_device_behavior(self, model_id: str) -> DeviceBehaviorModel | None:
        return self._device_behaviors.get(model_id)

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SocketRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    row_id: Literal["top", "bottom"]
    pins: list[int]


class SocketCenter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    shape: Literal["octal", "circular"]
    symmetric: bool
    label_area: bool = True


class SocketType(BaseModel):
    model_config = ConfigDict(extra="forbid")

    socket_type_id: str = Field(pattern=r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
    name: str = Field(min_length=1, max_length=120)
    pin_count: Literal[8, 12]
    view_side: Literal["wiring_base_front"]
    rows: list[SocketRow] = Field(min_length=2, max_length=2)
    center: SocketCenter

    @property
    def pins(self) -> set[int]:
        return {pin for row in self.rows for pin in row.pins}


class SocketCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"]
    socket_types: list[SocketType]


DeviceCategory = Literal[
    "terminal_block",
    "mccb",
    "fuse",
    "eocr",
    "magnetic_contactor",
    "auxiliary_relay",
    "timer",
    "flasher_relay",
    "level_relay",
    "push_button",
    "selector_switch",
    "buzzer",
    "limit_switch",
    "indicator_lamp",
    "motor",
    "power_source",
    "socket_base",
]


class DeviceType(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device_type_id: str = Field(pattern=r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
    name: str = Field(min_length=1, max_length=120)
    category: DeviceCategory
    socket_type_id: str | None = None
    mounting: Literal["fixed", "plug_in", "panel", "external"]
    electrical_definition_status: Literal["unverified", "reviewed", "verified"]


class DeviceCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"]
    device_types: list[DeviceType]

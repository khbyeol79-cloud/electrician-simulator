from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class BoardRect(BaseModel):
    model_config = ConfigDict(extra="forbid")
    x: float
    y: float
    width: float = Field(gt=0)
    height: float = Field(gt=0)


class BoardPin(BaseModel):
    model_config = ConfigDict(extra="forbid")
    terminal_id: str = Field(pattern=r"^[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*$")
    label: str
    role_label: str | None = None
    number: int | None = Field(default=None, ge=1)
    side: Literal["top", "bottom"]
    x: float
    y: float
    max_connections: int = Field(default=2, ge=1, le=10)
    enabled: bool = True


class BoardItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    item_id: str = Field(pattern=r"^[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*$")
    label: str
    item_type: Literal["socket_8p", "socket_12p", "terminal_block", "component"]
    socket_type_id: str | None = None
    row: int = Field(ge=0)
    x: float
    y: float
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    pins: list[BoardPin] = Field(min_length=1)
    label_area: BoardRect


class RoutingChannel(BoardRect):
    channel_id: str
    channel_type: Literal["horizontal", "left_outer", "right_outer"]


class ForbiddenArea(BoardRect):
    area_id: str


class BoardDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0"]
    board_id: str
    layout_mode: Literal["auto_rows", "fixed"] = "auto_rows"
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    routing_margin: float = Field(ge=0)
    items: list[BoardItem] = Field(min_length=1)
    routing_channels: list[RoutingChannel]
    forbidden_areas: list[ForbiddenArea]

    @property
    def terminal_ids(self) -> set[str]:
        return {pin.terminal_id for item in self.items for pin in item.pins}

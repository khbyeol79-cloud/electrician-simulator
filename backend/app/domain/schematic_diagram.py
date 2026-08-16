from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DiagramPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    x: float
    y: float


class DiagramBox(DiagramPoint):
    width: float = Field(gt=0)
    height: float = Field(gt=0)


class DiagramViewBox(DiagramBox):
    pass


class DiagramSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    section_id: str
    label: str
    bounds: DiagramBox


ElementType = Literal[
    "terminal", "contact_no", "contact_nc", "contact_changeover", "coil",
    "push_button_no", "push_button_nc", "limit_switch_no", "limit_switch_nc",
    "timer_contact", "magnetic_contactor", "eocr", "fuse", "mccb",
    "indicator_lamp", "motor", "junction", "text", "power_label", "ground",
]


class DiagramElement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    element_id: str
    element_type: ElementType
    section_id: str
    circuit_ref_type: Literal["device", "terminal", "contact", "coil"] | None = None
    circuit_ref_id: str | None = None
    question_id: str | None = None
    x: float
    y: float
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    orientation: Literal["horizontal", "vertical"] = "vertical"
    label: str = ""
    interactive: bool = False


class DiagramConductor(BaseModel):
    model_config = ConfigDict(extra="forbid")
    conductor_id: str
    section_id: str
    points: list[DiagramPoint] = Field(min_length=2)
    line_style: Literal[
        "power_l1", "power_l2", "power_l3",
        "control", "neutral", "reference",
    ]
    junctions: list[DiagramPoint] = Field(default_factory=list)


class SchematicDiagram(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0"]
    view_box: DiagramViewBox
    sections: list[DiagramSection]
    elements: list[DiagramElement]
    conductors: list[DiagramConductor]

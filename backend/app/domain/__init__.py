"""Problem package and public circuit domain models."""

from .answer_definition import AnswerDefinition
from .board_definition import BoardDefinition
from .catalog import DeviceCatalog, DeviceType, SocketCatalog, SocketType
from .device_behavior import (
    DeviceBehaviorCatalog,
    DeviceBehaviorModel,
    DeviceInstanceCreate,
    DeviceInstanceDefinition,
)
from .circuit_attempt import CircuitAttemptResult, CircuitAttemptSubmit, CircuitProgress, CircuitQuestionResult
from .circuit_analysis_draft import CircuitAnalysisDraftResponse, CircuitAnalysisDraftUpdate
from .problem_definition import ProblemDefinition
from .problem_manifest import ProblemCapabilities, ProblemManifest
from .free_circuit import (
    FreeCircuitAssembly,
    FreeCircuitDevicePlacement,
    FreeCircuitInstalledDevice,
    FreeCircuitMountingSlot,
    FreeCircuitPaletteItem,
    FreeCircuitPaletteResponse,
    FreeCircuitTemplate,
    FreeCircuitWorkspaceResponse,
    FreeCircuitWorkspaceSummary,
    FreeCircuitWorkspaceUpdate,
)
from .schematic_diagram import SchematicDiagram
from .mounting_attempt import (
    MountDevice, MountTarget, MountingAnswerPlacement, MountingAttemptResult,
    MountingAttemptSubmit, MountingDefinition, MountingDraftResponse,
    MountingDraftUpdate, MountingPlacement, MountingProgress,
    WrongMountingPlacement,
)
from .operation_setup import AcceptedWiringSnapshot, DeviceLayoutDefinition, FixedDevicePlacement, OperationSetupResponse
from .operation_definition import (
    BehaviorRequirementItem, BehaviorRequirementResult, BehaviorRequirementSummary, BehaviorScenarioItem,
    ControlState, OperationAction, OperationCheckItem, OperationCheckResult,
    OperationDefinition, OperationFault, OperationProgress, OperationSessionCreate, PracticeOperationSessionCreate,
    OperationSessionState, TimerState,
)
from .wiring_attempt import (
    PracticeSafetyIssue, PracticeWiringDraftResponse, WiringAttemptResult, WiringAttemptSubmit,
    WiringConnection, WiringDraftResponse, WiringDraftUpdate, WiringProgress,
)
from .wiring_capture import (
    CaptureConnection, StructuralWarning, WiringCaptureDraftResponse, WiringCaptureExport,
    WiringCaptureImport, WiringCaptureUpdate, WiringSnapshotCreate, WiringSnapshotResponse,
    WiringWorkspaceCreate, WiringWorkspaceSummary,
)
from .problem_package import (
    ProblemPackage,
    CircuitSummary,
    ProblemSummary,
    ProblemValidationIssue,
    ProblemValidationResult,
    PublicProblemDetail,
)

__all__ = [
    "AnswerDefinition",
    "BoardDefinition",
    "DeviceCatalog",
    "DeviceType",
    "DeviceBehaviorCatalog",
    "DeviceBehaviorModel",
    "DeviceInstanceCreate",
    "DeviceInstanceDefinition",
    "ProblemDefinition",
    "ProblemManifest",
    "ProblemCapabilities",
    "FreeCircuitWorkspaceResponse",
    "FreeCircuitWorkspaceSummary",
    "FreeCircuitTemplate",
    "FreeCircuitWorkspaceUpdate",
    "FreeCircuitAssembly",
    "FreeCircuitDevicePlacement",
    "FreeCircuitInstalledDevice",
    "FreeCircuitMountingSlot",
    "FreeCircuitPaletteItem",
    "FreeCircuitPaletteResponse",
    "ProblemPackage",
    "CircuitSummary",
    "CircuitAttemptResult",
    "CircuitAttemptSubmit",
    "CircuitProgress",
    "CircuitQuestionResult",
    "CircuitAnalysisDraftResponse",
    "CircuitAnalysisDraftUpdate",
    "ProblemSummary",
    "ProblemValidationIssue",
    "ProblemValidationResult",
    "PublicProblemDetail",
    "SocketCatalog",
    "SocketType",
    "SchematicDiagram",
    "MountDevice",
    "MountTarget",
    "MountingAnswerPlacement",
    "MountingAttemptResult",
    "MountingAttemptSubmit",
    "MountingDefinition",
    "MountingDraftResponse",
    "MountingDraftUpdate",
    "MountingPlacement",
    "MountingProgress",
    "WrongMountingPlacement",
    "DeviceLayoutDefinition",
    "FixedDevicePlacement",
    "OperationSetupResponse",
    "WiringAttemptResult",
    "WiringAttemptSubmit",
    "WiringConnection",
    "WiringDraftResponse",
    "WiringDraftUpdate",
    "WiringProgress",
    "PracticeSafetyIssue",
    "PracticeWiringDraftResponse",
    "CaptureConnection",
    "StructuralWarning",
    "WiringCaptureDraftResponse",
    "WiringCaptureExport",
    "WiringCaptureImport",
    "WiringCaptureUpdate",
    "WiringSnapshotCreate",
    "WiringSnapshotResponse",
    "WiringWorkspaceCreate",
    "WiringWorkspaceSummary",
    "PracticeOperationSessionCreate",
    "OperationSessionState",
    "OperationSessionCreate",
    "OperationAction",
    "OperationCheckResult",
    "BehaviorRequirementItem",
    "BehaviorRequirementResult",
    "BehaviorRequirementSummary",
    "BehaviorScenarioItem",
    "OperationCheckItem",
    "OperationProgress",
]

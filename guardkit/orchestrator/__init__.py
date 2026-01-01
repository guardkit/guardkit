"""Orchestrator components for GuardKit AutoBuild feature."""

from guardkit.orchestrator.agent_invoker import AgentInvoker, AgentInvocationResult
from guardkit.orchestrator.autobuild import (
    AutoBuildOrchestrator,
    OrchestrationResult,
    TurnRecord,
    PreLoopPhaseError,
)
from guardkit.orchestrator.exceptions import (
    AgentInvokerError,
    AgentInvocationError,
    PlayerReportNotFoundError,
    PlayerReportInvalidError,
    CoachDecisionNotFoundError,
    CoachDecisionInvalidError,
    SDKTimeoutError,
    OrchestrationError,
    SetupPhaseError,
    LoopPhaseError,
    FinalizePhaseError,
)
from guardkit.orchestrator.feature_loader import (
    Feature,
    FeatureTask,
    FeatureOrchestration,
    FeatureExecution,
    FeatureLoader,
    FeatureNotFoundError,
    FeatureParseError,
    FeatureValidationError,
)
from guardkit.orchestrator.feature_orchestrator import (
    FeatureOrchestrator,
    FeatureOrchestrationResult,
    FeatureOrchestrationError,
    TaskExecutionResult,
    WaveExecutionResult,
)
from guardkit.orchestrator.progress import ProgressDisplay
from guardkit.orchestrator.protocol import OrchestratorProtocol

# Import quality gates module
from guardkit.orchestrator.quality_gates import (
    PreLoopQualityGates,
    TaskWorkInterface,
    QualityGateError,
    QualityGateBlocked,
    DesignPhaseError,
    CheckpointRejectedError,
)

__all__ = [
    # Agent invocation
    "AgentInvoker",
    "AgentInvocationResult",
    # AutoBuild orchestration
    "AutoBuildOrchestrator",
    "OrchestrationResult",
    "TurnRecord",
    # Feature orchestration
    "Feature",
    "FeatureTask",
    "FeatureOrchestration",
    "FeatureExecution",
    "FeatureLoader",
    "FeatureOrchestrator",
    "FeatureOrchestrationResult",
    "TaskExecutionResult",
    "WaveExecutionResult",
    # Protocol
    "OrchestratorProtocol",
    # Quality Gates
    "PreLoopQualityGates",
    "TaskWorkInterface",
    # Exceptions - AgentInvoker
    "AgentInvokerError",
    "AgentInvocationError",
    "PlayerReportNotFoundError",
    "PlayerReportInvalidError",
    "CoachDecisionNotFoundError",
    "CoachDecisionInvalidError",
    "SDKTimeoutError",
    # Exceptions - Orchestration
    "OrchestrationError",
    "SetupPhaseError",
    "PreLoopPhaseError",
    "LoopPhaseError",
    "FinalizePhaseError",
    # Exceptions - Feature Orchestration
    "FeatureNotFoundError",
    "FeatureParseError",
    "FeatureValidationError",
    "FeatureOrchestrationError",
    # Exceptions - Quality Gates
    "QualityGateError",
    "QualityGateBlocked",
    "DesignPhaseError",
    "CheckpointRejectedError",
    # Progress display
    "ProgressDisplay",
]

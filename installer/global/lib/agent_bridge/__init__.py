"""
Agent Bridge Infrastructure

File-based IPC for Python↔Claude agent invocation using checkpoint-resume pattern.
Enables Python orchestrator to request Claude agent invocations via exit code 42.
"""

from lib.agent_bridge.invoker import (
    AgentBridgeInvoker,
    AgentInvocationError,
    AgentRequest,
    AgentResponse,
)
from lib.agent_bridge.state_manager import (
    StateManager,
    TemplateCreateState,
)

__all__ = [
    "AgentBridgeInvoker",
    "AgentInvocationError",
    "AgentRequest",
    "AgentResponse",
    "StateManager",
    "TemplateCreateState",
]

__version__ = "1.0.0"

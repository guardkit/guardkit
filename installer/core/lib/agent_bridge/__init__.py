"""
Agent Bridge Infrastructure

File-based IPC for Python↔Claude agent invocation using checkpoint-resume pattern.
Enables Python orchestrator to request Claude agent invocations via exit code 42.
"""

import importlib

# Import using importlib to avoid 'global' keyword issue
_invoker_module = importlib.import_module('installer.core.lib.agent_bridge.invoker')
_state_manager_module = importlib.import_module('installer.core.lib.agent_bridge.state_manager')

AgentBridgeInvoker = _invoker_module.AgentBridgeInvoker
AgentInvocationError = _invoker_module.AgentInvocationError
AgentRequest = _invoker_module.AgentRequest
AgentResponse = _invoker_module.AgentResponse

StateManager = _state_manager_module.StateManager
TemplateCreateState = _state_manager_module.TemplateCreateState

__all__ = [
    "AgentBridgeInvoker",
    "AgentInvocationError",
    "AgentRequest",
    "AgentResponse",
    "StateManager",
    "TemplateCreateState",
]

__version__ = "1.0.0"

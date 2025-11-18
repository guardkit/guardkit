# Agent Bridge Data Schemas

**Date**: 2025-11-18
**Status**: SPECIFICATION
**Purpose**: Define JSON schemas for agent bridge communication
**Related**: AI-PROMPTS-SPECIFICATION.md, TASK-AGENT-BRIDGE-COMPLETE.md

---

## Overview

This document defines the data contracts for the agent bridge checkpoint-resume pattern. These schemas ensure consistent communication between the orchestrator and AI agents.

---

## File Schemas

### 1. Agent Request File (`.agent-request.json`)

Written by orchestrator before checkpoint exit (code 42).

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "AgentRequest",
  "description": "Request for AI agent invocation during template creation",
  "type": "object",
  "required": ["request_id", "version", "phase", "phase_name", "agent_name", "prompt", "created_at"],
  "properties": {
    "request_id": {
      "type": "string",
      "format": "uuid",
      "description": "Unique identifier for this request"
    },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+$",
      "description": "Schema version (e.g., '1.0')",
      "default": "1.0"
    },
    "phase": {
      "type": "integer",
      "minimum": 1,
      "maximum": 9,
      "description": "Phase number in template creation workflow"
    },
    "phase_name": {
      "type": "string",
      "enum": ["codebase_analysis", "agent_creation", "agent_enhancement"],
      "description": "Human-readable phase name"
    },
    "agent_name": {
      "type": "string",
      "enum": ["architectural-reviewer", "agent-content-enhancer"],
      "description": "Name of agent to invoke"
    },
    "prompt": {
      "type": "string",
      "minLength": 100,
      "description": "Complete prompt text for the agent"
    },
    "context": {
      "type": "object",
      "description": "Additional context for the agent",
      "properties": {
        "project_path": {
          "type": "string",
          "description": "Path to project being analyzed"
        },
        "output_path": {
          "type": "string",
          "description": "Path where template is being created"
        },
        "template_name": {
          "type": "string",
          "description": "Name of template being created"
        }
      }
    },
    "timeout_seconds": {
      "type": "integer",
      "minimum": 30,
      "maximum": 600,
      "default": 120,
      "description": "Maximum time to wait for agent response"
    },
    "created_at": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 timestamp when request was created"
    },
    "retry_count": {
      "type": "integer",
      "minimum": 0,
      "default": 0,
      "description": "Number of times this request has been retried"
    }
  },
  "additionalProperties": false
}
```

#### Example Request

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "version": "1.0",
  "phase": 1,
  "phase_name": "codebase_analysis",
  "agent_name": "architectural-reviewer",
  "prompt": "# Codebase Analysis Request\n\nYou are analyzing a codebase...",
  "context": {
    "project_path": "/Users/dev/MyProject",
    "output_path": "/Users/dev/.agentecflow/templates/my-template",
    "template_name": "my-template"
  },
  "timeout_seconds": 120,
  "created_at": "2025-11-18T10:30:00Z",
  "retry_count": 0
}
```

---

### 2. Agent Response File (`.agent-response.json`)

Written by external agent invocation handler after agent completes.

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "AgentResponse",
  "description": "Response from AI agent invocation",
  "type": "object",
  "required": ["request_id", "version", "status", "created_at"],
  "properties": {
    "request_id": {
      "type": "string",
      "format": "uuid",
      "description": "Must match the request_id from AgentRequest"
    },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+$",
      "description": "Schema version"
    },
    "status": {
      "type": "string",
      "enum": ["success", "error", "timeout", "cancelled"],
      "description": "Result status of agent invocation"
    },
    "response": {
      "type": "string",
      "description": "Agent response content (typically JSON string)"
    },
    "error_message": {
      "type": "string",
      "description": "Error description if status is not 'success'"
    },
    "error_type": {
      "type": "string",
      "enum": [
        "AGENT_NOT_FOUND",
        "INVOCATION_FAILED",
        "TIMEOUT",
        "PARSE_ERROR",
        "VALIDATION_ERROR",
        "UNKNOWN"
      ],
      "description": "Categorized error type"
    },
    "created_at": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 timestamp when response was created"
    },
    "duration_seconds": {
      "type": "number",
      "minimum": 0,
      "description": "Time taken to generate response"
    },
    "metadata": {
      "type": "object",
      "description": "Additional metadata about the invocation",
      "properties": {
        "model": {
          "type": "string",
          "description": "AI model used (e.g., 'claude-sonnet-4-5-20250929')"
        },
        "tokens_used": {
          "type": "integer",
          "description": "Total tokens consumed"
        },
        "confidence": {
          "type": "number",
          "minimum": 0,
          "maximum": 1,
          "description": "Overall confidence score from response"
        }
      }
    }
  },
  "additionalProperties": false
}
```

#### Example Success Response

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "version": "1.0",
  "status": "success",
  "response": "{\"technology_stack\":{\"primary_language\":\"C#\",\"confidence\":0.95},...}",
  "created_at": "2025-11-18T10:31:45Z",
  "duration_seconds": 105.3,
  "metadata": {
    "model": "claude-sonnet-4-5-20250929",
    "tokens_used": 4523,
    "confidence": 0.92
  }
}
```

#### Example Error Response

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "version": "1.0",
  "status": "error",
  "error_message": "Agent response could not be parsed as JSON",
  "error_type": "PARSE_ERROR",
  "created_at": "2025-11-18T10:31:45Z",
  "duration_seconds": 95.1,
  "metadata": {
    "model": "claude-sonnet-4-5-20250929",
    "tokens_used": 3200
  }
}
```

---

### 3. Checkpoint State File (`.template-create-state.json`)

Tracks orchestration state for resume capability.

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "TemplateCreateState",
  "description": "Checkpoint state for template creation workflow",
  "type": "object",
  "required": ["version", "phase", "phase_name", "checkpoint_name", "created_at", "output_path"],
  "properties": {
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+$",
      "description": "Schema version"
    },
    "phase": {
      "type": "integer",
      "minimum": 1,
      "maximum": 9,
      "description": "Current phase number"
    },
    "phase_name": {
      "type": "string",
      "description": "Human-readable phase name"
    },
    "checkpoint_name": {
      "type": "string",
      "description": "Specific checkpoint within phase (e.g., 'before_agent_invocation')"
    },
    "created_at": {
      "type": "string",
      "format": "date-time",
      "description": "When checkpoint was created"
    },
    "output_path": {
      "type": "string",
      "description": "Path to template output directory"
    },
    "project_path": {
      "type": "string",
      "description": "Path to source project"
    },
    "template_name": {
      "type": "string",
      "description": "Name of template being created"
    },
    "phase_data": {
      "type": "object",
      "description": "Phase-specific serialized data",
      "additionalProperties": true
    },
    "completed_phases": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "phase": {"type": "integer"},
          "phase_name": {"type": "string"},
          "completed_at": {"type": "string", "format": "date-time"},
          "result_summary": {"type": "string"}
        }
      },
      "description": "List of successfully completed phases"
    },
    "agent_requests": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "request_id": {"type": "string"},
          "agent_name": {"type": "string"},
          "phase": {"type": "integer"},
          "status": {"type": "string"}
        }
      },
      "description": "History of agent requests made"
    }
  },
  "additionalProperties": false
}
```

#### Example State File

```json
{
  "version": "1.0",
  "phase": 5,
  "phase_name": "agent_recommendation",
  "checkpoint_name": "before_agent_invocation",
  "created_at": "2025-11-18T10:30:00Z",
  "output_path": "/Users/dev/.agentecflow/templates/my-template",
  "project_path": "/Users/dev/MyProject",
  "template_name": "my-template",
  "phase_data": {
    "codebase_analysis": {
      "primary_language": "C#",
      "framework": ".NET MAUI",
      "patterns": ["MVVM", "ErrorOr", "Repository"]
    },
    "manifest": {
      "name": "my-template",
      "language": "C#",
      "framework": ".NET MAUI"
    },
    "existing_agents": {
      "user_custom": [],
      "template": [],
      "global": ["architectural-reviewer", "code-reviewer", "test-verifier"]
    }
  },
  "completed_phases": [
    {
      "phase": 1,
      "phase_name": "codebase_analysis",
      "completed_at": "2025-11-18T10:25:00Z",
      "result_summary": "Analyzed 30 files, confidence 0.92"
    },
    {
      "phase": 2,
      "phase_name": "manifest_generation",
      "completed_at": "2025-11-18T10:26:00Z",
      "result_summary": "Generated manifest.json"
    }
  ],
  "agent_requests": [
    {
      "request_id": "550e8400-e29b-41d4-a716-446655440000",
      "agent_name": "architectural-reviewer",
      "phase": 1,
      "status": "completed"
    }
  ]
}
```

---

## Error Codes

### Error Types

| Code | Description | Recovery Action |
|------|-------------|-----------------|
| `AGENT_NOT_FOUND` | Specified agent does not exist | Check agent name spelling |
| `INVOCATION_FAILED` | Agent invocation threw exception | Retry with increased timeout |
| `TIMEOUT` | Agent did not respond in time | Retry or use fallback |
| `PARSE_ERROR` | Response is not valid JSON | Use fallback heuristics |
| `VALIDATION_ERROR` | Response doesn't match schema | Use fallback |
| `UNKNOWN` | Unexpected error | Log and use fallback |

### Exit Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 0 | SUCCESS | Template creation completed successfully |
| 1 | ERROR | Unrecoverable error occurred |
| 42 | CHECKPOINT | Paused for external agent invocation |

---

## Python Dataclass Definitions

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
import uuid

class AgentName(Enum):
    ARCHITECTURAL_REVIEWER = "architectural-reviewer"
    AGENT_CONTENT_ENHANCER = "agent-content-enhancer"

class RequestStatus(Enum):
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"

class ErrorType(Enum):
    AGENT_NOT_FOUND = "AGENT_NOT_FOUND"
    INVOCATION_FAILED = "INVOCATION_FAILED"
    TIMEOUT = "TIMEOUT"
    PARSE_ERROR = "PARSE_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNKNOWN = "UNKNOWN"

@dataclass
class AgentRequest:
    """Request for AI agent invocation."""
    phase: int
    phase_name: str
    agent_name: str
    prompt: str
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    version: str = "1.0"
    context: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 120
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    retry_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "version": self.version,
            "phase": self.phase,
            "phase_name": self.phase_name,
            "agent_name": self.agent_name,
            "prompt": self.prompt,
            "context": self.context,
            "timeout_seconds": self.timeout_seconds,
            "created_at": self.created_at,
            "retry_count": self.retry_count
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentRequest":
        return cls(
            request_id=data["request_id"],
            version=data.get("version", "1.0"),
            phase=data["phase"],
            phase_name=data["phase_name"],
            agent_name=data["agent_name"],
            prompt=data["prompt"],
            context=data.get("context", {}),
            timeout_seconds=data.get("timeout_seconds", 120),
            created_at=data["created_at"],
            retry_count=data.get("retry_count", 0)
        )

@dataclass
class ResponseMetadata:
    """Metadata about agent invocation."""
    model: Optional[str] = None
    tokens_used: Optional[int] = None
    confidence: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {}
        if self.model:
            result["model"] = self.model
        if self.tokens_used:
            result["tokens_used"] = self.tokens_used
        if self.confidence is not None:
            result["confidence"] = self.confidence
        return result

@dataclass
class AgentResponse:
    """Response from AI agent invocation."""
    request_id: str
    status: str
    version: str = "1.0"
    response: Optional[str] = None
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    duration_seconds: Optional[float] = None
    metadata: ResponseMetadata = field(default_factory=ResponseMetadata)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "request_id": self.request_id,
            "version": self.version,
            "status": self.status,
            "created_at": self.created_at
        }
        if self.response:
            result["response"] = self.response
        if self.error_message:
            result["error_message"] = self.error_message
        if self.error_type:
            result["error_type"] = self.error_type
        if self.duration_seconds is not None:
            result["duration_seconds"] = self.duration_seconds
        if self.metadata:
            result["metadata"] = self.metadata.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentResponse":
        metadata = ResponseMetadata()
        if "metadata" in data:
            metadata = ResponseMetadata(
                model=data["metadata"].get("model"),
                tokens_used=data["metadata"].get("tokens_used"),
                confidence=data["metadata"].get("confidence")
            )
        return cls(
            request_id=data["request_id"],
            version=data.get("version", "1.0"),
            status=data["status"],
            response=data.get("response"),
            error_message=data.get("error_message"),
            error_type=data.get("error_type"),
            created_at=data["created_at"],
            duration_seconds=data.get("duration_seconds"),
            metadata=metadata
        )

    def is_success(self) -> bool:
        return self.status == "success"

    def get_confidence(self) -> float:
        """Get confidence score, defaulting to 0.0 if not available."""
        return self.metadata.confidence if self.metadata.confidence else 0.0

@dataclass
class CompletedPhase:
    """Record of a completed phase."""
    phase: int
    phase_name: str
    completed_at: str
    result_summary: str

@dataclass
class TemplateCreateState:
    """Checkpoint state for template creation."""
    phase: int
    phase_name: str
    checkpoint_name: str
    output_path: str
    version: str = "1.0"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    project_path: Optional[str] = None
    template_name: Optional[str] = None
    phase_data: Dict[str, Any] = field(default_factory=dict)
    completed_phases: List[CompletedPhase] = field(default_factory=list)
    agent_requests: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "phase": self.phase,
            "phase_name": self.phase_name,
            "checkpoint_name": self.checkpoint_name,
            "created_at": self.created_at,
            "output_path": self.output_path,
            "project_path": self.project_path,
            "template_name": self.template_name,
            "phase_data": self.phase_data,
            "completed_phases": [
                {
                    "phase": p.phase,
                    "phase_name": p.phase_name,
                    "completed_at": p.completed_at,
                    "result_summary": p.result_summary
                }
                for p in self.completed_phases
            ],
            "agent_requests": self.agent_requests
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TemplateCreateState":
        completed = [
            CompletedPhase(
                phase=p["phase"],
                phase_name=p["phase_name"],
                completed_at=p["completed_at"],
                result_summary=p["result_summary"]
            )
            for p in data.get("completed_phases", [])
        ]
        return cls(
            version=data.get("version", "1.0"),
            phase=data["phase"],
            phase_name=data["phase_name"],
            checkpoint_name=data["checkpoint_name"],
            created_at=data["created_at"],
            output_path=data["output_path"],
            project_path=data.get("project_path"),
            template_name=data.get("template_name"),
            phase_data=data.get("phase_data", {}),
            completed_phases=completed,
            agent_requests=data.get("agent_requests", [])
        )
```

---

## Mock Agent Invoker (For Testing)

```python
from typing import Dict, Callable, Any
import json

class MockAgentInvoker:
    """Mock agent invoker for testing without real AI calls."""

    def __init__(self, responses: Dict[str, str] = None):
        """
        Initialize with canned responses.

        Args:
            responses: Map of agent_name -> response content (JSON string)
        """
        self.responses = responses or {}
        self.invocations: List[Dict[str, Any]] = []

    def add_response(self, agent_name: str, response: str) -> None:
        """Add a canned response for an agent."""
        self.responses[agent_name] = response

    def add_response_from_dict(self, agent_name: str, response_dict: Dict) -> None:
        """Add a canned response from a dictionary."""
        self.responses[agent_name] = json.dumps(response_dict)

    def invoke(
        self,
        agent_name: str,
        prompt: str,
        timeout_seconds: int = 120,
        **kwargs
    ) -> str:
        """
        Mock invoke an agent.

        Args:
            agent_name: Name of agent to invoke
            prompt: Prompt text
            timeout_seconds: Timeout (ignored in mock)

        Returns:
            Canned response for the agent

        Raises:
            AgentInvocationError: If no response configured for agent
        """
        # Record invocation
        self.invocations.append({
            "agent_name": agent_name,
            "prompt": prompt,
            "timeout_seconds": timeout_seconds,
            "kwargs": kwargs
        })

        # Return canned response
        if agent_name in self.responses:
            return self.responses[agent_name]

        raise AgentInvocationError(
            f"No mock response configured for agent: {agent_name}"
        )

    def get_invocations(self, agent_name: str = None) -> List[Dict]:
        """Get recorded invocations, optionally filtered by agent."""
        if agent_name:
            return [i for i in self.invocations if i["agent_name"] == agent_name]
        return self.invocations

    def reset(self) -> None:
        """Reset invocation history."""
        self.invocations = []

class AgentInvocationError(Exception):
    """Raised when agent invocation fails."""
    pass
```

### Usage Example

```python
def test_phase_1_checkpoint():
    # Setup mock
    mock = MockAgentInvoker()
    mock.add_response_from_dict("architectural-reviewer", {
        "technology_stack": {
            "primary_language": "C#",
            "confidence": 0.95
        },
        "overall_confidence": 0.92
    })

    # Inject mock
    orchestrator = TemplateCreateOrchestrator(agent_invoker=mock)

    # Run phase
    result = orchestrator._phase1_ai_analysis(samples)

    # Verify
    assert result.primary_language == "C#"
    assert mock.get_invocations("architectural-reviewer") == 1
```

---

## File Locations

| File | Location | Created By | Read By |
|------|----------|------------|---------|
| `.agent-request.json` | Project root | Orchestrator | External handler |
| `.agent-response.json` | Project root | External handler | Orchestrator |
| `.template-create-state.json` | Project root | Orchestrator | Orchestrator |

---

## Cleanup Protocol

After successful template creation or on error:

```python
def _cleanup_checkpoint_files(self):
    """Remove checkpoint files after workflow completes."""
    files_to_remove = [
        ".agent-request.json",
        ".agent-response.json",
        ".template-create-state.json"
    ]
    for filename in files_to_remove:
        filepath = Path(filename)
        if filepath.exists():
            filepath.unlink()
            self.logger.debug(f"Removed checkpoint file: {filename}")
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-18 | Initial specification |

---

**Created**: 2025-11-18
**Author**: architectural-reviewer, code-reviewer
**Status**: Ready for implementation

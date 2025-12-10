# Python↔Claude Agent Bridge - Technical Specification

**Date**: 2025-01-11
**Architecture**: File-Based IPC with Checkpoint Resume (Option 1)
**Status**: DETAILED SPECIFICATION
**Estimated Effort**: 6-8 hours

---

## Table of Contents

1. [Overview](#overview)
2. [File Structure](#file-structure)
3. [Exit Codes](#exit-codes)
4. [Request/Response Protocol](#requestresponse-protocol)
5. [State Management](#state-management)
6. [Component Specifications](#component-specifications)
7. [Integration Points](#integration-points)
8. [Error Handling](#error-handling)
9. [Testing Strategy](#testing-strategy)
10. [Migration Guide](#migration-guide)

---

## Overview

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  /template-create (Claude Code Command)                     │
│                                                               │
│  while not complete:                                         │
│    exit_code = run_python_orchestrator(args)                │
│    if exit_code == 42:  # NEED_AGENT                        │
│      ├─ request = read_agent_request()                      │
│      ├─ response = invoke_agent(request)                    │
│      ├─ write_agent_response(response)                      │
│      └─ args = add_resume_flag(args)                        │
│    else if exit_code == 0:  # SUCCESS                       │
│      └─ break                                                │
│    else:  # ERROR                                            │
│      └─ handle_error(exit_code)                             │
└─────────────────────────────────────────────────────────────┘
                           ↕
┌─────────────────────────────────────────────────────────────┐
│  Python Orchestrator (template_create_orchestrator.py)      │
│                                                               │
│  if --resume:                                                │
│    ├─ state = load_state()                                  │
│    └─ response = load_agent_response()                      │
│  else:                                                       │
│    └─ run_phases_1_to_5()                                   │
│                                                               │
│  # Phase 6: Agent Generation                                │
│  if ai_invoker.needs_invocation():                          │
│    ├─ save_state()                                          │
│    ├─ write_agent_request()                                 │
│    └─ exit(42)  # NEED_AGENT                                │
│  else:                                                       │
│    └─ use_cached_response()                                 │
│                                                               │
│  run_phases_7_to_8()                                         │
│  exit(0)  # SUCCESS                                          │
└─────────────────────────────────────────────────────────────┘
```

---

## File Structure

### Working Directory Files

All state files are written to the current working directory (where `/template-create` is invoked):

```
./
├── .template-create-state.json      # Orchestrator state (Phase 1-8)
├── .agent-request.json               # Agent invocation request
└── .agent-response.json              # Agent invocation response
```

### File Lifecycle

| File | Created By | Read By | Deleted By | When |
|------|-----------|---------|-----------|------|
| `.template-create-state.json` | Python | Python | Python | On successful completion |
| `.agent-request.json` | Python | Claude | Claude | After agent invocation |
| `.agent-response.json` | Claude | Python | Python | After reading response |

---

## Exit Codes

### Standard Exit Codes

| Code | Name | Meaning | Handler Action |
|------|------|---------|----------------|
| 0 | SUCCESS | Template created successfully | Display results, cleanup |
| 1 | USER_CANCELLED | User cancelled during Q&A | Display cancellation message |
| 2 | CODEBASE_NOT_FOUND | Codebase path invalid | Display error, exit |
| 3 | ANALYSIS_FAILED | AI analysis failed completely | Display error, exit |
| 4 | GENERATION_FAILED | Component generation failed | Display error, exit |
| 5 | VALIDATION_FAILED | Validation checks failed | Display error, exit |
| 6 | SAVE_FAILED | File I/O error during save | Display error, exit |
| 42 | **NEED_AGENT** | **Requesting agent invocation** | **Invoke agent, re-run** |
| 130 | INTERRUPTED | User pressed Ctrl+C | Save session, exit |

### Exit Code 42 - Special Handling

```python
# Python side - Exit with code 42
if ai_invoker.needs_invocation():
    save_state()
    write_agent_request()
    sys.exit(42)  # NEED_AGENT

# Claude side - Detect and handle
exit_code = run_orchestrator()
if exit_code == 42:
    handle_agent_request()
    exit_code = run_orchestrator(resume=True)
```

---

## Request/Response Protocol

### Agent Request Format

**File**: `.agent-request.json`

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "version": "1.0",
  "phase": 6,
  "phase_name": "agent_generation",
  "agent_name": "architectural-reviewer",
  "prompt": "Analyze this codebase and identify ALL specialized AI agents...",
  "timeout_seconds": 120,
  "created_at": "2025-01-11T10:30:00.000Z",
  "context": {
    "template_name": "dotnet-maui-clean-mvvm",
    "language": "C#",
    "framework": ".NET MAUI"
  }
}
```

**Field Specifications**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `request_id` | UUID | Yes | Unique request identifier |
| `version` | String | Yes | Protocol version (semantic versioning) |
| `phase` | Integer | Yes | Current phase number (1-8) |
| `phase_name` | String | Yes | Human-readable phase name |
| `agent_name` | String | Yes | Agent to invoke |
| `prompt` | String | Yes | Complete prompt text |
| `timeout_seconds` | Integer | Yes | Maximum wait time |
| `created_at` | ISO 8601 | Yes | Request timestamp |
| `context` | Object | No | Additional context for debugging |

### Agent Response Format

**File**: `.agent-response.json`

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "version": "1.0",
  "status": "success",
  "response": "[\n  {\n    \"name\": \"mvvm-viewmodel-specialist\",\n    ...\n  }\n]",
  "error_message": null,
  "error_type": null,
  "created_at": "2025-01-11T10:30:05.234Z",
  "duration_seconds": 5.234,
  "metadata": {
    "agent_name": "architectural-reviewer",
    "model": "claude-sonnet-4-5",
    "tokens_used": 4521
  }
}
```

**Status Values**:

| Status | Meaning | Python Action |
|--------|---------|---------------|
| `success` | Agent returned valid response | Parse and continue |
| `error` | Agent invocation failed | Fall back to hard-coded |
| `timeout` | Agent exceeded timeout | Fall back to hard-coded |
| `invalid_request` | Request file malformed | Log error, fall back |

---

## State Management

### State File Format

**File**: `.template-create-state.json`

```json
{
  "version": "1.0",
  "checkpoint": "agent_generation_pending",
  "phase": 6,
  "created_at": "2025-01-11T10:30:00.000Z",
  "updated_at": "2025-01-11T10:30:00.123Z",

  "config": {
    "codebase_path": "/path/to/codebase",
    "output_location": "global",
    "skip_qa": false,
    "max_templates": null,
    "no_agents": false,
    "verbose": false
  },

  "phase_data": {
    "qa_answers": {
      "template_name": "dotnet-maui-clean-mvvm",
      "primary_language": "C#",
      "framework": ".NET MAUI",
      ...
    },

    "analysis": {
      "language": "C#",
      "architecture_pattern": "MVVM",
      "frameworks": [".NET MAUI", "CommunityToolkit.Mvvm"],
      "layers": [...],
      "patterns": [...],
      ...
    },

    "manifest": {
      "name": "dotnet-maui-clean-mvvm",
      "version": "1.0.0",
      ...
    },

    "settings": {
      "naming_conventions": {...},
      ...
    },

    "templates": [
      {
        "source_path": "ViewModels/HomeViewModel.cs",
        "template_path": "ViewModels/EntityViewModel.cs.template",
        ...
      },
      ...
    ],

    "agent_inventory": {
      "global_agents": [...],
      "local_agents": []
    }
  },

  "agent_request_pending": {
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "created_at": "2025-01-11T10:30:00.123Z"
  }
}
```

### Checkpoint States

| Checkpoint | Phase | Meaning | Resume Action |
|-----------|-------|---------|---------------|
| `analysis_complete` | 2 | Phases 1-2 done | Continue to Phase 3 |
| `templates_generated` | 5 | Phases 1-5 done | Continue to Phase 6 |
| `agent_generation_pending` | 6 | Waiting for AI | Load response, continue Phase 6 |
| `agents_generated` | 6 | Phase 6 done | Continue to Phase 7 |
| `complete` | 8 | All phases done | Display results |

---

## Component Specifications

### Component 1: AgentBridgeInvoker (Python)

**File**: `installer/core/lib/agent_bridge/invoker.py` (NEW)

```python
"""
Agent Bridge Invoker

Implements file-based IPC for Python→Claude agent invocation.
Uses exit code 42 to signal agent request, enabling checkpoint-resume pattern.
"""

import json
import sys
from pathlib import Path
from typing import Protocol, Optional
from dataclasses import dataclass
from datetime import datetime
import uuid


class AgentInvoker(Protocol):
    """Protocol for agent invocation (DIP)"""
    def invoke(self, agent_name: str, prompt: str) -> str:
        """Invoke an agent with a prompt"""
        ...


@dataclass
class AgentRequest:
    """Agent invocation request"""
    request_id: str
    version: str
    phase: int
    phase_name: str
    agent_name: str
    prompt: str
    timeout_seconds: int
    created_at: str
    context: dict


@dataclass
class AgentResponse:
    """Agent invocation response"""
    request_id: str
    version: str
    status: str  # success | error | timeout
    response: Optional[str]
    error_message: Optional[str]
    error_type: Optional[str]
    created_at: str
    duration_seconds: float
    metadata: dict


class AgentBridgeInvoker:
    """
    Bridge invoker using file-based IPC with checkpoint-resume pattern.

    When agent invocation is needed:
    1. Write request to .agent-request.json
    2. Save orchestrator state to .template-create-state.json
    3. Exit with code 42 (NEED_AGENT)
    4. Claude detects exit code, invokes agent, writes response
    5. Claude re-runs Python with --resume flag
    6. Python loads state and response, continues execution
    """

    def __init__(
        self,
        request_file: Path = Path(".agent-request.json"),
        response_file: Path = Path(".agent-response.json"),
        phase: int = 6,
        phase_name: str = "agent_generation"
    ):
        """
        Initialize bridge invoker.

        Args:
            request_file: Path to write request (default: ./.agent-request.json)
            response_file: Path to read response (default: ./.agent-response.json)
            phase: Current phase number
            phase_name: Human-readable phase name
        """
        self.request_file = request_file
        self.response_file = response_file
        self.phase = phase
        self.phase_name = phase_name
        self._cached_response: Optional[str] = None

    def invoke(
        self,
        agent_name: str,
        prompt: str,
        timeout_seconds: int = 120,
        context: Optional[dict] = None
    ) -> str:
        """
        Request agent invocation via checkpoint-resume pattern.

        If response already cached (from --resume run), return it immediately.
        Otherwise, write request and exit with code 42.

        Args:
            agent_name: Agent to invoke (e.g., "architectural-reviewer")
            prompt: Complete prompt text
            timeout_seconds: Maximum wait time for agent response
            context: Optional context for debugging

        Returns:
            Agent response text

        Raises:
            AgentInvocationError: If response indicates error
        """
        # If we already have a cached response (from --resume), use it
        if self._cached_response is not None:
            return self._cached_response

        # Create request
        request = AgentRequest(
            request_id=str(uuid.uuid4()),
            version="1.0",
            phase=self.phase,
            phase_name=self.phase_name,
            agent_name=agent_name,
            prompt=prompt,
            timeout_seconds=timeout_seconds,
            created_at=datetime.utcnow().isoformat() + "Z",
            context=context or {}
        )

        # Write request file
        self.request_file.write_text(
            json.dumps(request.__dict__, indent=2),
            encoding="utf-8"
        )

        print(f"  ⏸️  Requesting agent invocation: {agent_name}")
        print(f"  📝 Request written to: {self.request_file}")
        print(f"  🔄 Checkpoint: Orchestrator will resume after agent responds")

        # Exit with code 42 to signal NEED_AGENT
        # NOTE: Orchestrator must save state before calling invoke()
        sys.exit(42)

    def load_response(self) -> str:
        """
        Load agent response from file (called during --resume).

        Returns:
            Agent response text

        Raises:
            FileNotFoundError: If response file doesn't exist
            AgentInvocationError: If response indicates error
        """
        if not self.response_file.exists():
            raise FileNotFoundError(
                f"Agent response file not found: {self.response_file}\n"
                "This should only be called during --resume after agent invocation."
            )

        # Parse response
        response_data = json.loads(self.response_file.read_text(encoding="utf-8"))
        response = AgentResponse(**response_data)

        # Check status
        if response.status == "success":
            self._cached_response = response.response
            print(f"  ✓ Agent response loaded ({response.duration_seconds:.1f}s)")

            # Cleanup response file
            self.response_file.unlink(missing_ok=True)

            return response.response

        elif response.status == "timeout":
            raise AgentInvocationError(
                f"Agent invocation timed out after {response.duration_seconds:.1f}s"
            )

        else:  # error
            raise AgentInvocationError(
                f"Agent invocation failed: {response.error_message}\n"
                f"Error type: {response.error_type}"
            )

    def has_pending_request(self) -> bool:
        """Check if agent request file exists"""
        return self.request_file.exists()

    def has_response(self) -> bool:
        """Check if agent response file exists"""
        return self.response_file.exists()


class AgentInvocationError(Exception):
    """Raised when agent invocation fails"""
    pass
```

### Component 2: State Manager (Python)

**File**: `installer/core/lib/agent_bridge/state_manager.py` (NEW)

```python
"""
Template Create State Manager

Handles state persistence for checkpoint-resume pattern.
"""

import json
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class TemplateCreateState:
    """Complete orchestrator state"""
    version: str
    checkpoint: str
    phase: int
    created_at: str
    updated_at: str
    config: dict
    phase_data: dict
    agent_request_pending: Optional[dict] = None


class StateManager:
    """Manages orchestrator state for checkpoint-resume"""

    def __init__(self, state_file: Path = Path(".template-create-state.json")):
        """
        Initialize state manager.

        Args:
            state_file: Path to state file (default: ./.template-create-state.json)
        """
        self.state_file = state_file

    def save_state(
        self,
        checkpoint: str,
        phase: int,
        config: dict,
        phase_data: dict,
        agent_request_pending: Optional[dict] = None
    ) -> None:
        """
        Save orchestrator state to file.

        Args:
            checkpoint: Current checkpoint name
            phase: Current phase number
            config: Orchestrator configuration
            phase_data: Results from completed phases
            agent_request_pending: Agent request metadata (if waiting)
        """
        # Load existing state or create new
        if self.state_file.exists():
            existing = json.loads(self.state_file.read_text(encoding="utf-8"))
            created_at = existing.get("created_at")
        else:
            created_at = datetime.utcnow().isoformat() + "Z"

        # Create state object
        state = TemplateCreateState(
            version="1.0",
            checkpoint=checkpoint,
            phase=phase,
            created_at=created_at,
            updated_at=datetime.utcnow().isoformat() + "Z",
            config=config,
            phase_data=phase_data,
            agent_request_pending=agent_request_pending
        )

        # Write to file
        self.state_file.write_text(
            json.dumps(asdict(state), indent=2),
            encoding="utf-8"
        )

    def load_state(self) -> TemplateCreateState:
        """
        Load orchestrator state from file.

        Returns:
            TemplateCreateState object

        Raises:
            FileNotFoundError: If state file doesn't exist
        """
        if not self.state_file.exists():
            raise FileNotFoundError(
                f"State file not found: {self.state_file}\n"
                "Cannot resume - no saved state."
            )

        data = json.loads(self.state_file.read_text(encoding="utf-8"))
        return TemplateCreateState(**data)

    def has_state(self) -> bool:
        """Check if state file exists"""
        return self.state_file.exists()

    def cleanup(self) -> None:
        """Delete state file (called on successful completion)"""
        self.state_file.unlink(missing_ok=True)
```

### Component 3: Orchestrator Integration

**File**: `installer/core/commands/lib/template_create_orchestrator.py` (MODIFY)

**Changes Required**:

1. Add `--resume` flag support
2. Integrate `StateManager` for checkpoint/restore
3. Pass `AgentBridgeInvoker` to `AIAgentGenerator`
4. Save state before agent invocation

```python
# Add imports
from installer.core.lib.agent_bridge.invoker import AgentBridgeInvoker
from installer.core.lib.agent_bridge.state_manager import StateManager, TemplateCreateState

class TemplateCreateOrchestrator:
    def __init__(self, config: OrchestrationConfig, resume: bool = False):
        """
        Initialize orchestrator.

        Args:
            config: Orchestration configuration
            resume: Whether this is a resume run (after agent invocation)
        """
        self.config = config
        self.resume = resume
        self.state_manager = StateManager()
        self.agent_invoker = AgentBridgeInvoker(phase=6, phase_name="agent_generation")

        # If resuming, load state
        if self.resume:
            self._resume_from_checkpoint()

    def _resume_from_checkpoint(self) -> None:
        """Restore state from checkpoint"""
        print("\n🔄 Resuming from checkpoint...")

        state = self.state_manager.load_state()
        print(f"  Checkpoint: {state.checkpoint}")
        print(f"  Phase: {state.phase}")

        # Restore configuration
        self.config = OrchestrationConfig(**state.config)

        # Restore phase data
        self.qa_answers = state.phase_data.get("qa_answers")
        self.analysis = state.phase_data.get("analysis")  # Need to deserialize
        self.manifest = state.phase_data.get("manifest")
        self.settings = state.phase_data.get("settings")
        self.templates = state.phase_data.get("templates")
        self.agent_inventory = state.phase_data.get("agent_inventory")

        # Load agent response
        try:
            response = self.agent_invoker.load_response()
            print(f"  ✓ Agent response loaded successfully")
        except Exception as e:
            print(f"  ⚠️  Failed to load agent response: {e}")
            print(f"  → Will fall back to hard-coded detection")

    def run(self) -> OrchestrationResult:
        """Execute orchestration workflow"""

        # If resuming, skip to Phase 6
        if self.resume:
            return self._run_from_phase_6()

        # Normal execution: Phases 1-8
        return self._run_all_phases()

    def _run_all_phases(self) -> OrchestrationResult:
        """Execute phases 1-8"""

        # Phase 1: Q&A
        self.qa_answers = self._phase1_qa_session()
        if not self.qa_answers:
            return self._create_error_result("Q&A cancelled")

        # Phase 2: AI Analysis
        self.analysis = self._phase2_ai_analysis(self.qa_answers)
        if not self.analysis:
            return self._create_error_result("Analysis failed")

        # Phase 3: Manifest
        self.manifest = self._phase3_manifest_generation(self.analysis, self.qa_answers)
        if not self.manifest:
            return self._create_error_result("Manifest generation failed")

        # Phase 4: Settings
        self.settings = self._phase4_settings_generation(self.analysis)
        if not self.settings:
            return self._create_error_result("Settings generation failed")

        # Phase 5: Templates
        self.templates = self._phase5_template_generation(self.analysis)
        if not self.templates:
            return self._create_error_result("Template generation failed")

        # Save state before Phase 6 (agent invocation may trigger exit)
        self._save_checkpoint("templates_generated", phase=5)

        # Phase 6: Agents (may exit with code 42)
        self.agents = self._phase6_agent_recommendation(self.analysis)

        # Phase 7: CLAUDE.md
        self.claude_md = self._phase7_claude_md_generation(self.analysis, self.agents)

        # Phase 8: Assembly
        result = self._phase8_assembly(...)

        # Cleanup state on success
        self.state_manager.cleanup()

        return result

    def _run_from_phase_6(self) -> OrchestrationResult:
        """Continue from Phase 6 after agent invocation"""

        # Phase 6: Complete agent generation with loaded response
        self.agents = self._phase6_agent_recommendation(self.analysis)

        # Phase 7: CLAUDE.md
        self.claude_md = self._phase7_claude_md_generation(self.analysis, self.agents)

        # Phase 8: Assembly
        result = self._phase8_assembly(...)

        # Cleanup state on success
        self.state_manager.cleanup()

        return result

    def _phase6_agent_recommendation(self, analysis: Any) -> List[Any]:
        """
        Phase 6: Agent Recommendation (MODIFIED for bridge integration)
        """
        self._print_phase_header("Phase 6: Agent Recommendation")

        try:
            from installer.core.lib.agent_scanner import scan_agents

            inventory = scan_agents()

            # IMPORTANT: Pass AgentBridgeInvoker to generator
            generator = AIAgentGenerator(
                inventory,
                ai_invoker=self.agent_invoker  # ← BRIDGE INTEGRATION
            )

            # This may exit with code 42 if agent invocation needed
            agents = generator.generate(analysis)

            if agents:
                self._print_info(f"  Generated {len(agents)} custom agents")
            else:
                self._print_info("  All capabilities covered by existing agents")

            return agents

        except Exception as e:
            self._print_warning(f"Agent generation failed: {e}")
            return []

    def _save_checkpoint(self, checkpoint: str, phase: int) -> None:
        """Save current state to checkpoint"""

        # Gather all phase data
        phase_data = {
            "qa_answers": self.qa_answers,
            "analysis": self.analysis.__dict__ if hasattr(self.analysis, '__dict__') else self.analysis,
            "manifest": self.manifest.__dict__ if hasattr(self.manifest, '__dict__') else self.manifest,
            "settings": self.settings.__dict__ if hasattr(self.settings, '__dict__') else self.settings,
            "templates": [t.__dict__ if hasattr(t, '__dict__') else t for t in (self.templates or [])],
            "agent_inventory": self.agent_inventory
        }

        # Save state
        self.state_manager.save_state(
            checkpoint=checkpoint,
            phase=phase,
            config=self.config.__dict__,
            phase_data=phase_data
        )
```

---

## Integration Points

### Integration 1: `/template-create` Command (Markdown)

**File**: `installer/core/commands/template-create.md` (MODIFY)

Add execution loop at the end of the file:

```markdown
## Execution

When user invokes `/template-create`, execute this workflow with checkpoint-resume support:

### Step 1: Parse Arguments

Extract arguments from user input:
- `--path`: Codebase path
- `--output-location`: Where to save (global | repo)
- `--skip-qa`: Skip Q&A session
- `--dry-run`: Analysis only
- `--validate`: Extended validation
- `--max-templates`: Limit template count

### Step 2: Initial Run

Run orchestrator:

```bash
cd <codebase-path>
python3 -m installer.core.commands.lib.template_create_orchestrator \
  --path "." \
  --output-location global \
  [other args...]
```

Capture exit code.

### Step 3: Handle Exit Code

**If exit code = 0 (SUCCESS)**:
- Display completion message
- Show template location
- Exit

**If exit code = 42 (NEED_AGENT)**:
1. Read agent request from `.agent-request.json`
2. Invoke agent using Task tool:
   - Extract `agent_name` and `prompt` from request
   - Launch agent via Task tool
   - Capture response
3. Write agent response to `.agent-response.json`:
   - Include status, response text, duration
   - Add metadata (model, tokens)
4. Re-run orchestrator with `--resume` flag:
   ```bash
   python3 -m installer.core.commands.lib.template_create_orchestrator \
     --resume \
     [original args...]
   ```
5. Capture new exit code
6. If exit code = 42 again, repeat (handle multiple agent requests)
7. If exit code = 0, display success
8. If exit code = other, display error

**If exit code = other**:
- Display error message based on exit code
- Exit

### Step 4: Cleanup

On successful completion:
- Delete `.agent-request.json` (if exists)
- Delete `.agent-response.json` (if exists)
- Delete `.template-create-state.json` (if exists)

### Example Execution Flow

```
User: /template-create
  ↓
Run Python orchestrator
  ↓
Exit code 42 (NEED_AGENT)
  ↓
Read .agent-request.json
  ↓
Invoke architectural-reviewer agent
  ↓
Write .agent-response.json
  ↓
Re-run Python with --resume
  ↓
Exit code 0 (SUCCESS)
  ↓
Display results
  ↓
Cleanup temp files
```

### Detailed Implementation

Use the Bash tool to execute orchestrator and handle checkpoint-resume loop:

```python
import json
from pathlib import Path

# Step 1: Parse args
args = parse_template_create_args(user_input)

# Step 2: Build command
cmd_parts = [
    "python3", "-m",
    "installer.core.commands.lib.template_create_orchestrator"
]
for key, value in args.items():
    if value is True:
        cmd_parts.append(f"--{key}")
    elif value not in [False, None]:
        cmd_parts.extend([f"--{key}", str(value)])

# Step 3: Execution loop
max_iterations = 5  # Prevent infinite loops
iteration = 0

while iteration < max_iterations:
    iteration += 1

    # Run orchestrator
    result = run_bash_command(" ".join(cmd_parts))
    exit_code = result.exit_code

    # Handle exit code
    if exit_code == 0:
        # Success
        print("✅ Template created successfully!")
        cleanup_temp_files()
        break

    elif exit_code == 42:
        # Agent request
        print(f"\n🔄 Agent invocation required (iteration {iteration})...")

        # Read request
        request_file = Path(".agent-request.json")
        if not request_file.exists():
            print("❌ ERROR: Agent request file not found")
            break

        request = json.loads(request_file.read_text())
        agent_name = request["agent_name"]
        prompt = request["prompt"]

        print(f"  Agent: {agent_name}")
        print(f"  Invoking via Task tool...")

        # Invoke agent
        response = invoke_agent_via_task_tool(agent_name, prompt)

        # Write response
        response_data = {
            "request_id": request["request_id"],
            "version": "1.0",
            "status": "success",
            "response": response,
            "error_message": None,
            "error_type": None,
            "created_at": current_timestamp(),
            "duration_seconds": agent_duration,
            "metadata": {
                "agent_name": agent_name,
                "model": "claude-sonnet-4-5"
            }
        }

        response_file = Path(".agent-response.json")
        response_file.write_text(json.dumps(response_data, indent=2))

        # Cleanup request file
        request_file.unlink()

        print(f"  ✓ Response written")
        print(f"  🔄 Resuming orchestrator...\n")

        # Add --resume flag for next iteration
        if "--resume" not in cmd_parts:
            cmd_parts.append("--resume")

    else:
        # Error
        print(f"❌ Template creation failed (exit code {exit_code})")
        break

cleanup_temp_files()
```
```

---

## Error Handling

### Error Scenarios

| Scenario | Detection | Handling |
|----------|-----------|----------|
| Agent request file missing | Claude checks file exists | Error message, exit |
| Agent request malformed JSON | Claude JSON parse fails | Error message, exit |
| Agent invocation fails | Task tool returns error | Write error response, Python falls back |
| Agent timeout | Task tool timeout | Write timeout response, Python falls back |
| State file missing on resume | Python checks file exists | Error message, exit 3 |
| State file malformed JSON | Python JSON parse fails | Error message, exit 3 |
| Response file missing | Python checks file exists | Error message, exit 3 |

### Fallback Strategy

```python
# In AIAgentGenerator._identify_capability_needs()
try:
    # Try AI-powered detection
    needs = self._ai_identify_all_agents(analysis)
    if needs:
        return needs
except AgentInvocationError as e:
    print(f"  ⚠️  AI detection failed: {e}")
    print(f"  → Falling back to hard-coded detection")
except Exception as e:
    print(f"  ⚠️  Unexpected error: {e}")
    print(f"  → Falling back to hard-coded detection")

# Fallback to hard-coded
return self._fallback_to_hardcoded(analysis)
```

---

## Testing Strategy

### Unit Tests

#### Test: AgentBridgeInvoker.invoke()
```python
def test_agent_bridge_invoker_writes_request_and_exits():
    """Test that invoke() writes request file and exits with code 42"""
    invoker = AgentBridgeInvoker()

    with pytest.raises(SystemExit) as exc_info:
        invoker.invoke("architectural-reviewer", "Test prompt")

    assert exc_info.value.code == 42
    assert Path(".agent-request.json").exists()

    request = json.loads(Path(".agent-request.json").read_text())
    assert request["agent_name"] == "architectural-reviewer"
    assert request["prompt"] == "Test prompt"
```

#### Test: AgentBridgeInvoker.load_response()
```python
def test_agent_bridge_invoker_loads_success_response():
    """Test that load_response() reads and caches response"""
    # Setup
    response_data = {
        "request_id": "test-123",
        "version": "1.0",
        "status": "success",
        "response": "Test agent response",
        "error_message": None,
        "error_type": None,
        "created_at": "2025-01-11T10:00:00Z",
        "duration_seconds": 5.0,
        "metadata": {}
    }
    Path(".agent-response.json").write_text(json.dumps(response_data))

    # Test
    invoker = AgentBridgeInvoker()
    response = invoker.load_response()

    assert response == "Test agent response"
    assert not Path(".agent-response.json").exists()  # Cleanup
```

#### Test: StateManager.save_state() / load_state()
```python
def test_state_manager_round_trip():
    """Test that state can be saved and loaded"""
    manager = StateManager()

    # Save
    manager.save_state(
        checkpoint="test_checkpoint",
        phase=6,
        config={"test": "config"},
        phase_data={"test": "data"}
    )

    # Load
    state = manager.load_state()

    assert state.checkpoint == "test_checkpoint"
    assert state.phase == 6
    assert state.config == {"test": "config"}
    assert state.phase_data == {"test": "data"}
```

### Integration Tests

#### Test: End-to-End Checkpoint-Resume
```python
def test_template_create_checkpoint_resume():
    """Test complete checkpoint-resume flow"""
    # Run orchestrator (will exit with code 42)
    result = subprocess.run(
        ["python3", "-m", "installer.core.commands.lib.template_create_orchestrator",
         "--path", "test_codebase"],
        capture_output=True
    )

    assert result.returncode == 42
    assert Path(".agent-request.json").exists()
    assert Path(".template-create-state.json").exists()

    # Simulate agent invocation
    request = json.loads(Path(".agent-request.json").read_text())
    mock_response = create_mock_agent_response(request)
    Path(".agent-response.json").write_text(json.dumps(mock_response))

    # Resume orchestrator
    result = subprocess.run(
        ["python3", "-m", "installer.core.commands.lib.template_create_orchestrator",
         "--resume"],
        capture_output=True
    )

    assert result.returncode == 0
    assert not Path(".template-create-state.json").exists()  # Cleanup
```

---

## Migration Guide

### For Existing Codebases

1. **No changes required** - Fallback to hard-coded detection still works
2. **Agent invocation optional** - System degrades gracefully if bridge fails
3. **Backward compatible** - Old behavior preserved

### For Future Enhancements

This bridge architecture can support:
- Multiple agent invocations per phase
- Parallel agent requests
- Long-running agents (hours)
- Agent streaming responses
- Agent cancellation

---

## Performance Characteristics

### Overhead Analysis

| Component | Time | Notes |
|-----------|------|-------|
| State serialization | ~20-50ms | JSON encoding |
| State file write | ~10-20ms | SSD |
| State file read | ~10-20ms | SSD |
| Request file write | ~5-10ms | Small JSON |
| Response file read | ~5-10ms | Small JSON |
| Python restart | ~200-500ms | Python interpreter startup |
| **Total overhead** | **~250-620ms** | **Per agent invocation** |

### Agent Invocation Time

- Typical: 5-30 seconds (depends on prompt complexity)
- Overhead: <1 second (<3% of total time)
- **Acceptable** for template creation use case

---

## Appendix: File Examples

### Example .agent-request.json
```json
{
  "request_id": "a1b2c3d4-e5f6-7890-ab12-3456789abcde",
  "version": "1.0",
  "phase": 6,
  "phase_name": "agent_generation",
  "agent_name": "architectural-reviewer",
  "prompt": "Analyze this codebase and identify ALL specialized AI agents needed for template creation.\n\n**Project Context:**\n- Language: C#\n- Architecture: MVVM\n- Frameworks: .NET MAUI, CommunityToolkit.Mvvm\n...",
  "timeout_seconds": 120,
  "created_at": "2025-01-11T10:30:00.000Z",
  "context": {
    "template_name": "dotnet-maui-clean-mvvm",
    "language": "C#",
    "framework": ".NET MAUI",
    "architecture": "MVVM"
  }
}
```

### Example .agent-response.json (Success)
```json
{
  "request_id": "a1b2c3d4-e5f6-7890-ab12-3456789abcde",
  "version": "1.0",
  "status": "success",
  "response": "[\n  {\n    \"name\": \"mvvm-viewmodel-specialist\",\n    \"description\": \"MVVM ViewModel patterns with INotifyPropertyChanged\",\n    \"reason\": \"Project has 8 ViewModels following MVVM pattern\",\n    \"technologies\": [\"C#\", \"MVVM\", \".NET MAUI\"],\n    \"example_files\": [\"ViewModels/HomeViewModel.cs\"],\n    \"priority\": 9\n  },\n  ...\n]",
  "error_message": null,
  "error_type": null,
  "created_at": "2025-01-11T10:30:12.345Z",
  "duration_seconds": 12.345,
  "metadata": {
    "agent_name": "architectural-reviewer",
    "model": "claude-sonnet-4-5",
    "tokens_used": 4521
  }
}
```

### Example .agent-response.json (Error)
```json
{
  "request_id": "a1b2c3d4-e5f6-7890-ab12-3456789abcde",
  "version": "1.0",
  "status": "error",
  "response": null,
  "error_message": "Agent invocation failed: Rate limit exceeded",
  "error_type": "RateLimitError",
  "created_at": "2025-01-11T10:30:05.123Z",
  "duration_seconds": 5.123,
  "metadata": {
    "agent_name": "architectural-reviewer"
  }
}
```

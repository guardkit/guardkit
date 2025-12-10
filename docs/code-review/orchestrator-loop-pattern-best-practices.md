# Orchestrator Loop Pattern: Best Practices & Recommendations

**Review Date**: 2025-11-24
**Reviewer**: Code Review Specialist
**Scope**: Comparison of `/template-create` and `/agent-enhance` orchestrator patterns
**Focus**: Checkpoint-resume implementation, error handling, state management

---

## Executive Summary

Analysis of `/template-create`'s checkpoint-resume orchestrator pattern reveals robust architectural choices that successfully prevented the infinite loop bug that affected `/agent-enhance`. The `/template-create` implementation demonstrates production-ready patterns for agent invocation, state management, and error recovery.

**Key Finding**: The infinite loop in `/agent-enhance` (TASK-FIX-D4E5) was caused by **missing checkpoint detection logic**, not architectural issues. The fix was correctly scoped to 9 lines of code checking for response files before invocation.

---

## Architecture Overview

### Checkpoint-Resume Pattern Components

```
┌────────────────────────────────────────────────────────────┐
│                   Orchestrator Loop                        │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  1. AgentBridgeInvoker                                    │
│     ├─ Request file: .agent-request.json                 │
│     ├─ Response file: .agent-response.json               │
│     ├─ has_response() → checks for response file         │
│     ├─ load_response() → caches response internally      │
│     └─ invoke() → writes request, exits with code 42     │
│                                                            │
│  2. StateManager                                          │
│     ├─ State file: .template-create-state.json           │
│     ├─ save_state() → persists orchestrator state        │
│     ├─ load_state() → restores state on --resume         │
│     └─ cleanup() → removes temp files on success         │
│                                                            │
│  3. Orchestrator Command Loop (Claude Code)               │
│     ├─ Executes Python orchestrator                       │
│     ├─ Detects exit code 42 → invokes agent              │
│     ├─ Writes .agent-response.json                        │
│     └─ Re-runs orchestrator with --resume flag           │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## Best Practices from `/template-create`

### 1. Code Organization & Separation of Concerns

#### ✅ GOOD: Layered Architecture

**Pattern**: `/template-create` uses three distinct layers:

```python
# Layer 1: Orchestrator (workflow coordination)
class TemplateCreateOrchestrator:
    def run(self) -> OrchestrationResult:
        return self._run_all_phases()

    def _run_all_phases(self) -> OrchestrationResult:
        # Phase 1-9 execution
        pass

# Layer 2: Agent Bridge (agent invocation abstraction)
class AgentBridgeInvoker:
    def invoke(self, agent_name: str, prompt: str) -> str:
        # Write request, exit 42
        pass

    def load_response(self) -> str:
        # Read response, cache, return
        pass

# Layer 3: State Manager (persistence abstraction)
class StateManager:
    def save_state(self, checkpoint: str, phase: int, ...) -> None:
        # Persist to .template-create-state.json
        pass

    def load_state(self) -> TemplateCreateState:
        # Restore from file
        pass
```

**Benefits**:
- **Single Responsibility**: Each layer has one clear purpose
- **Testability**: Can mock AgentBridgeInvoker for unit tests
- **Reusability**: StateManager can be used by any orchestrator
- **Maintainability**: Changes to agent invocation don't affect state logic

**Location**:
- `/template-create`: `installer/core/commands/lib/template_create_orchestrator.py`
- `/agent-enhance`: `installer/core/lib/agent_enhancement/enhancer.py`

---

#### ✅ GOOD: Checkpoint-Before-Invocation Pattern

**Pattern**: Always save state BEFORE calling agent:

```python
# template_create_orchestrator.py (line 280-284)

# IMPORTANT: Save state before Phase 5
# (Phase 5 may exit with code 42 to request agent invocation)
self._save_checkpoint("templates_generated", phase=WorkflowPhase.PHASE_4)

# Phase 5: Agent Recommendation (may exit with code 42)
self.agents = []
if not self.config.no_agents:
    self.agents = self._phase5_agent_recommendation(self.analysis)
```

**Why This Works**:
1. **Atomicity**: State is saved BEFORE side effects
2. **Recovery**: On resume, state is intact and consistent
3. **No Data Loss**: Exit code 42 doesn't lose work-in-progress

**Comparison with `/agent-enhance`**:
- `/agent-enhance` doesn't need state saving (single-phase command)
- BUT it still needs response detection (TASK-FIX-D4E5 fix)

---

#### ✅ GOOD: Response Detection Before Invocation

**Pattern**: Check for cached response before invoking:

```python
# template_create_orchestrator.py (line 1768-1777)

# Load agent response if available
try:
    response = self.agent_invoker.load_response()
    print(f"  ✓ Agent response loaded successfully")
except FileNotFoundError:
    print(f"  ⚠️  No agent response found")
    # Falls back to alternative approach
```

**Why This Works**:
1. **Idempotency**: Multiple runs don't re-invoke unnecessarily
2. **Fast Resume**: Cached response returns immediately
3. **Graceful Fallback**: FileNotFoundError is expected on first run

**This Was Missing in `/agent-enhance`** (TASK-FIX-D4E5):

```python
# BEFORE FIX (agent-enhance, line 271) - ❌ BROKEN
result_text = invoker.invoke(  # Always invokes, never checks cache
    agent_name="agent-content-enhancer",
    prompt=prompt
)

# AFTER FIX (agent-enhance, line 269-280) - ✅ WORKING
if invoker.has_response():
    # Response file exists - load cached response
    result_text = invoker.load_response()
    if self.verbose:
        logger.info("  ✓ Loaded agent response from checkpoint")
else:
    # No response yet - invoke agent (will exit with code 42)
    result_text = invoker.invoke(
        agent_name="agent-content-enhancer",
        prompt=prompt
    )
```

**Key Lesson**: **ALWAYS check `has_response()` before `invoke()`**

---

### 2. Error Handling & Retry Logic

#### ✅ GOOD: Explicit Error Type Handling

**Pattern**: Handle different error types with appropriate strategies:

```python
# template_create_orchestrator.py (line 1770-1777)

try:
    response = self.agent_invoker.load_response()
    print(f"  ✓ Agent response loaded successfully")
except FileNotFoundError:
    # Expected on first run - not an error
    print(f"  ⚠️  No agent response found")
    print(f"  → Will fall back to hard-coded detection")
except Exception as e:
    # Unexpected errors - log and fallback
    print(f"  ⚠️  Failed to load agent response: {e}")
    print(f"  → Will fall back to hard-coded detection")
```

**Error Categories**:
1. **Expected Errors** (FileNotFoundError): First-run scenario, log as info
2. **Validation Errors** (ValueError, TypeError): Malformed response, log as error
3. **Unexpected Errors** (Exception): Unknown failures, log with traceback

**Comparison with `/agent-enhance` Error Handling**:

```python
# agent_enhancement/enhancer.py (line 348-368)

except TimeoutError as e:
    duration = time.time() - start_time
    logger.warning(f"AI enhancement timed out after {duration:.2f}s: {e}")
    raise  # Propagates to retry logic or hybrid fallback

except json.JSONDecodeError as e:
    duration = time.time() - start_time
    logger.error(f"AI response parsing failed after {duration:.2f}s: {e}")
    logger.error(f"  Invalid response (first 200 chars): {result_text[:200]}")
    raise ValidationError(f"Invalid JSON response: {e}")

except ValidationError as e:
    duration = time.time() - start_time
    logger.error(f"AI returned invalid enhancement structure after {duration:.2f}s: {e}")
    raise  # Don't retry validation errors

except Exception as e:
    duration = time.time() - start_time
    logger.error(f"AI enhancement failed after {duration:.2f}s: {e}")
    logger.exception("Full traceback:")
    raise
```

**Best Practice**: `/agent-enhance` uses **granular error handling** with specific exception types and appropriate propagation strategies.

---

#### ✅ GOOD: Exponential Backoff Retry with Failure Discrimination

**Pattern**: Retry transient failures, fail fast on permanent failures:

```python
# agent_enhancement/enhancer.py (line 370-434)

def _ai_enhancement_with_retry(
    self,
    agent_metadata: dict,
    templates: List[Path],
    template_dir: Path,
    max_retries: int = 2  # 3 total attempts (0, 1, 2)
) -> dict:
    """
    AI enhancement with exponential backoff retry logic.

    Retries on transient failures (TimeoutError, network errors).
    Does NOT retry on ValidationError (permanent failures).
    """
    for attempt in range(max_retries + 1):
        try:
            # Log retry attempt
            if attempt > 0:
                backoff_seconds = 2 ** (attempt - 1)  # 1s (2^0), 2s (2^1)
                logger.info(f"Retry attempt {attempt}/{max_retries} after {backoff_seconds}s")
                time.sleep(backoff_seconds)

            # Attempt AI enhancement
            return self._ai_enhancement(agent_metadata, templates, template_dir)

        except ValidationError as e:
            # Don't retry validation errors (permanent failures)
            logger.warning(f"Validation error (no retry): {e}")
            raise

        except TimeoutError as e:
            if attempt < max_retries:
                logger.warning(f"Attempt {attempt + 1} timed out. Retrying...")
                continue
            else:
                logger.error(f"All {max_retries + 1} attempts timed out")
                raise

        except Exception as e:
            if attempt < max_retries:
                logger.warning(f"Attempt {attempt + 1} failed. Retrying...")
                continue
            else:
                logger.error(f"All {max_retries + 1} attempts failed: {e}")
                raise
```

**Retry Strategy**:
- **Transient Failures**: Retry with exponential backoff (1s, 2s, 4s)
- **Permanent Failures**: Fail fast, no retry (ValidationError, schema errors)
- **Max Attempts**: 3 total (initial + 2 retries)

**Backoff Calculation**:
```
Attempt 0 (initial): No delay
Attempt 1 (retry 1): 2^0 = 1 second delay
Attempt 2 (retry 2): 2^1 = 2 seconds delay
```

**Best Practice**: This pattern prevents infinite retries while giving transient failures multiple chances to succeed.

---

#### ❌ ANTI-PATTERN: Retrying on Validation Errors

**Problem**: Retrying schema/format errors wastes time and resources:

```python
# ❌ BAD - Retries permanent failures
for attempt in range(max_retries):
    try:
        result = invoke_agent()
        validate(result)  # Always fails if schema wrong
        return result
    except Exception:
        # Retries even when schema is fundamentally wrong
        continue
```

**Why Bad**:
- Validation errors are **permanent** (won't fix themselves)
- Wastes API calls and time
- Delays error feedback to user

**Correct Approach** (from `/agent-enhance`):

```python
# ✅ GOOD - Fail fast on permanent failures
except ValidationError as e:
    # Don't retry validation errors (permanent failures)
    logger.warning(f"Validation error (no retry): {e}")
    raise  # Immediate failure
```

---

### 3. State Management During Checkpoint-Resume

#### ✅ GOOD: Complete State Serialization

**Pattern**: Capture ALL orchestrator state for perfect resume:

```python
# template_create_orchestrator.py (line 1779-1812)

def _save_checkpoint(self, checkpoint_name: str, phase: int) -> None:
    """Save orchestrator state for checkpoint-resume."""

    # Serialize phase data (all completed phases)
    phase_data = {
        "qa_answers": self.qa_answers,
        "analysis": self._serialize_analysis(self.analysis),
        "manifest": self._serialize_manifest(self.manifest),
        "settings": self._serialize_settings(self.settings),
        "templates": self._serialize_templates(self.templates),
        "agent_inventory": self.agent_inventory,
        "agents": self._serialize_agents(self.agents)
    }

    # Serialize config
    config = {
        "codebase_path": str(self.config.codebase_path) if self.config.codebase_path else None,
        "output_path": str(self.config.output_path) if self.config.output_path else None,
        "output_location": self.config.output_location,
        "max_templates": self.config.max_templates,
        "dry_run": self.config.dry_run,
        "no_agents": self.config.no_agents,
        "verbose": self.config.verbose
    }

    # Save to state file
    self.state_manager.save_state(
        checkpoint=checkpoint_name,
        phase=phase,
        config=config,
        phase_data=phase_data
    )
```

**State Completeness Checklist**:
- ✅ All phase results (analysis, manifest, settings, templates, agents)
- ✅ All configuration options (paths, flags, settings)
- ✅ Current phase number and checkpoint name
- ✅ Timestamps (created_at, updated_at)

**Benefits**:
1. **Perfect Resume**: Orchestrator can continue exactly where it left off
2. **No Data Loss**: All work-in-progress is preserved
3. **Debugging**: State file shows exactly what was done
4. **Idempotency**: Multiple resumes reach same final state

---

#### ✅ GOOD: State Deserialization with Validation

**Pattern**: Validate state during load, fail fast on corruption:

```python
# state_manager.py (line 124-146)

def load_state(self) -> TemplateCreateState:
    """Load orchestrator state from file."""
    if not self.state_file.exists():
        raise FileNotFoundError(
            f"State file not found: {self.state_file}\n"
            "Cannot resume - no saved state exists."
        )

    try:
        data = json.loads(self.state_file.read_text(encoding="utf-8"))
        return TemplateCreateState(**data)  # Dataclass validation
    except json.JSONDecodeError as e:
        raise ValueError(f"Malformed state file: {e}")
    except TypeError as e:
        raise ValueError(f"Invalid state format: {e}")
```

**Validation Layers**:
1. **File Existence**: FileNotFoundError if missing
2. **JSON Syntax**: JSONDecodeError if malformed
3. **Schema Validation**: TypeError if wrong fields/types (dataclass __init__)

**Recovery Options**:
- Corrupted state → Clear and start fresh
- Missing state → Normal run (not resume)
- Schema mismatch → Show clear error with field names

---

#### ✅ GOOD: Timestamp Preservation Across Updates

**Pattern**: Preserve `created_at`, update `updated_at`:

```python
# state_manager.py (line 95-104)

# Load existing state to preserve created_at, or create new timestamp
if self.state_file.exists():
    try:
        existing = json.loads(self.state_file.read_text(encoding="utf-8"))
        created_at = existing.get("created_at", datetime.now(timezone.utc).isoformat())
    except (json.JSONDecodeError, OSError):
        # If existing state is corrupted, create new timestamp
        created_at = datetime.now(timezone.utc).isoformat()
else:
    created_at = datetime.now(timezone.utc).isoformat()
```

**Why Important**:
- **Debugging**: Shows when workflow started vs when it resumed
- **Audit Trail**: Tracks workflow duration across multiple runs
- **Timeout Detection**: Can detect stale checkpoints (e.g., >10 minutes old)

**State Timestamps**:
- `created_at`: Workflow start time (preserved across updates)
- `updated_at`: Last checkpoint time (always current)

---

### 4. Exit Code Handling

#### ✅ GOOD: Semantic Exit Codes with Dispatch Table

**Pattern**: Use meaningful exit codes with clear handling:

```python
# template-create.md command wrapper (lines 1244-1257)

EXIT_MESSAGES = {
    0: ("✅ Template created successfully!", True, True),
    1: ("⚠️  Template creation cancelled by user", True, True),
    2: ("❌ ERROR: Codebase not found or inaccessible", True, True),
    3: ("❌ ERROR: AI analysis failed", True, True),
    4: ("❌ ERROR: Component generation failed", True, True),
    5: ("❌ ERROR: Validation failed", True, True),
    6: ("❌ ERROR: Save failed (check permissions)", True, True),
    130: ("⚠️  Template creation interrupted (Ctrl+C)", False, True),
    # 42: Special case handled separately (NEED_AGENT)
}
```

**Exit Code Semantics**:
- **0**: Success (cleanup + break)
- **1-6**: User/validation errors (cleanup + break)
- **42**: Agent invocation needed (NO cleanup + continue loop)
- **130**: User interrupt (NO cleanup + break, preserves session)

**Dispatch Pattern**:

```python
# template-create.md (lines 1300-1310)

if exit_code in EXIT_MESSAGES:
    message, should_cleanup, should_break = EXIT_MESSAGES[exit_code]
    print(f"\n{message}")
    if should_cleanup:
        cleanup_all_temp_files()
    if should_break:
        break
```

**Benefits**:
1. **Self-Documenting**: Exit codes have clear meanings
2. **DRY**: Single source of truth for exit code handling
3. **Testability**: Easy to test each exit code path
4. **Extensibility**: Add new codes without modifying logic

---

#### ✅ GOOD: Exit Code 42 Special Handling

**Pattern**: Treat exit code 42 as "continuation signal", not error:

```python
# template-create.md (lines 1312-1493)

elif exit_code == 42:
    # NEED_AGENT - Handle agent invocation
    print(f"\n🔄 Agent invocation required...\n")

    # Read agent request
    request_file = Path(".agent-request.json")
    if not request_file.exists():
        print("❌ ERROR: Agent request file not found")
        cleanup_all_temp_files()
        break

    # Parse agent request
    try:
        request_data = json.loads(request_file.read_text())
    except json.JSONDecodeError as e:
        print(f"❌ ERROR: Malformed agent request file: {e}")
        cleanup_request_file()
        break

    # Invoke agent via Task tool
    try:
        agent_response = await invoke_agent_subagent(
            agent_name=request_data["agent_name"],
            prompt=request_data["prompt"],
            timeout_seconds=request_data.get("timeout_seconds", 120)
        )
        status = "success"
    except Exception as e:
        agent_response = None
        status = "error"
        error_message = str(e)

    # Write response file
    response_data = {
        "request_id": request_data["request_id"],
        "version": "1.0",
        "status": status,
        "response": agent_response,
        "error_message": error_message,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "duration_seconds": duration
    }

    response_file = Path(".agent-response.json")
    response_file.write_text(json.dumps(response_data, indent=2))

    # Cleanup request file
    request_file.unlink()

    # Set resume flag for next iteration
    resume_flag = True

    # Continue loop (don't break!)
```

**Key Aspects**:
1. **No Cleanup**: Preserve state files for resume
2. **No Break**: Continue loop to resume orchestrator
3. **Request Processing**: Read, invoke agent, write response
4. **Error Handling**: Write error response if agent fails
5. **Resume Flag**: Add `--resume` to next invocation

**Comparison with Other Exit Codes**:
- Exit 0-6: Cleanup + Break (workflow ends)
- Exit 42: No cleanup + Continue (workflow resumes)
- Exit 130: No cleanup + Break (user can resume manually)

---

### 5. User Experience Considerations

#### ✅ GOOD: Progressive Feedback with Clear Status Messages

**Pattern**: Show user exactly what's happening at each step:

```python
# template-create.md (lines 1284-1300)

print("🚀 Starting template creation...\n")

# Execution loop
while iteration < max_iterations:
    iteration += 1
    print(f"📍 Iteration {iteration}: Running orchestrator...")

    result = await bash(cmd, timeout=ORCHESTRATOR_TIMEOUT_MS)
    exit_code = result.exit_code

    if exit_code == 42:
        print(f"\n🔄 Agent invocation required...\n")
        print(f"  Agent: {agent_name}")
        print(f"  Timeout: {timeout_seconds}s")
        print(f"  Invoking agent...\n")

        # ... invoke agent ...

        print(f"  ✓ Response written ({duration:.1f}s)")
        print(f"  🔄 Resuming orchestrator...\n")
```

**Feedback Principles**:
1. **Progress Indicators**: Show iteration number, phase name
2. **Time Information**: Show duration, timeouts
3. **Status Symbols**: ✅ success, ❌ error, ⚠️ warning, 🔄 retry
4. **Contextual Info**: Show what's happening and why

**Benefits**:
- User knows workflow isn't frozen
- User can diagnose issues from logs
- User sees progress toward completion
- User learns about workflow structure

---

#### ✅ GOOD: Verbose Mode for Debugging

**Pattern**: Optional verbose flag shows internal details:

```python
# agent_enhancement/enhancer.py (line 250-254)

if self.verbose:
    logger.info(f"AI Enhancement Started:")
    logger.info(f"  Agent: {agent_name}")
    logger.info(f"  Templates: {len(templates)}")
    logger.info(f"  Prompt size: {len(prompt)} chars")
```

**When Verbose is Useful**:
- Debugging infinite loops or hangs
- Understanding which phase failed
- Verifying checkpoint-resume behavior
- Troubleshooting agent invocations

**Best Practice**: Log at multiple levels:
- **INFO**: Always shown (success, failure, warnings)
- **DEBUG**: Only shown in verbose mode (internal state, decisions)

---

#### ✅ GOOD: Infinite Loop Prevention with Max Iterations

**Pattern**: Detect runaway loops and exit gracefully:

```python
# template-create.md (lines 1151-1159, 1500-1505)

DEFAULT_MAX_ITERATIONS = 5

max_iterations = DEFAULT_MAX_ITERATIONS
iteration = 0

while iteration < max_iterations:
    iteration += 1
    # ... execute orchestrator ...

# After loop
if iteration >= max_iterations:
    print(f"\n❌ ERROR: Maximum iterations ({max_iterations}) reached")
    print("   This may indicate a bug - please report it")
    cleanup_all_temp_files()
```

**Why 5 Iterations?**:
- Normal workflow: 2 iterations (initial + 1 resume)
- With errors: 3-4 iterations (retry agent invocation)
- 5 is safety margin to prevent infinite loops

**Alternative Approaches**:
- Time-based limit (e.g., max 30 minutes)
- Exponential backoff with increasing delays
- User confirmation after N iterations

---

#### ❌ ANTI-PATTERN: Silent Failures

**Problem**: User doesn't know why workflow failed:

```python
# ❌ BAD - Silent failure
try:
    result = invoke_agent()
except Exception:
    pass  # Silently fails, user confused
```

**Why Bad**:
- User sees no error message
- User doesn't know if retry would help
- Debugging is impossible without logs

**Correct Approach**:

```python
# ✅ GOOD - Clear error message
try:
    result = invoke_agent()
except TimeoutError as e:
    print(f"❌ ERROR: Agent timeout after {timeout}s")
    print(f"   You can retry with increased timeout")
    print(f"   Or use --static strategy for faster results")
    raise
except Exception as e:
    print(f"❌ ERROR: Agent invocation failed: {e}")
    print(f"   Check logs for details")
    logger.exception("Full traceback:")
    raise
```

---

## Anti-Patterns to Avoid

### 1. Missing Response Check Before Invocation

**The Bug**: `/agent-enhance` infinite loop (TASK-FIX-D4E5)

```python
# ❌ ANTI-PATTERN - Always invokes, never checks cache
invoker = AgentBridgeInvoker(phase=8, phase_name="agent_enhancement")

# Missing: if invoker.has_response(): load_response()

result_text = invoker.invoke(  # Writes new request EVERY TIME
    agent_name="agent-content-enhancer",
    prompt=prompt
)
```

**Why Bad**:
1. **First run**: Writes `.agent-request.json`, exits 42 ✓
2. **Second run**: Ignores `.agent-response.json`, writes new request ✗
3. **Third run**: Overwrites `.agent-response.json` again ✗
4. **Infinite loop**: Repeats forever ✗

**Fix** (TASK-FIX-D4E5):

```python
# ✅ CORRECT - Check response before invocation
invoker = AgentBridgeInvoker(phase=8, phase_name="agent_enhancement")

if invoker.has_response():
    # Response exists - load cached response
    result_text = invoker.load_response()
    if self.verbose:
        logger.info("✓ Loaded agent response from checkpoint")
else:
    # No response yet - invoke agent
    result_text = invoker.invoke(
        agent_name="agent-content-enhancer",
        prompt=prompt
    )
```

**Prevention**:
- ✅ Always check `has_response()` before `invoke()`
- ✅ Add integration test for checkpoint-resume cycle
- ✅ Document pattern in code review checklist
- ✅ Use `/template-create` as reference implementation

---

### 2. Incorrect Response Format (Field Name/Type Mismatch)

**The Bug**: Claude Code generating wrong response format (TASK-FIX-267C)

```json
// ❌ ANTI-PATTERN - Wrong field name and type
{
  "request_id": "...",
  "status": "success",
  "result": {  // ❌ Should be "response" (field name)
    "sections": [...]  // ❌ Should be JSON string (data type)
  }
}
```

**Why Bad**:
1. **Field Name**: Python unpacks `result=...` but `AgentResponse` has `response` parameter
2. **Data Type**: `AgentResponse.response` is `str`, not `dict`
3. **Error**: `TypeError: AgentResponse.__init__() got an unexpected keyword argument 'result'`

**Fix** (TASK-FIX-267C):

```json
// ✅ CORRECT - Right field name and JSON string
{
  "request_id": "...",
  "version": "1.0",
  "status": "success",
  "response": "{\"sections\": [...]}",  // ✅ JSON-encoded string
  "error_message": null,
  "error_type": null,
  "created_at": "2025-11-24T14:22:45.123456+00:00",
  "duration_seconds": 1.0,
  "metadata": {}
}
```

**Prevention**:
- ✅ Reference format specification (docs/reference/agent-response-format.md)
- ✅ Use validation script before writing response
- ✅ Follow two-level JSON parsing design
- ✅ Include all required fields with correct types

---

### 3. Cleanup on Checkpoint Exit (Exit Code 42)

**Problem**: Cleaning up temp files when workflow needs to resume:

```python
# ❌ ANTI-PATTERN - Cleanup on exit 42
if exit_code == 42:
    cleanup_all_temp_files()  # ❌ Deletes state needed for resume
    break
```

**Why Bad**:
- Deletes `.agent-request.json` (Claude Code needs this)
- Deletes `.template-create-state.json` (orchestrator needs this)
- Resume attempt fails because state is missing

**Correct Approach**:

```python
# ✅ CORRECT - No cleanup on exit 42
EXIT_MESSAGES = {
    0: ("Success", True, True),  # cleanup=True, break=True
    42: None,  # Special handling, no cleanup, continue loop
    130: ("Interrupted", False, True),  # cleanup=False, break=True
}

if exit_code == 42:
    # ... handle agent invocation ...
    # NO cleanup_all_temp_files()
    resume_flag = True  # Continue loop
```

**Cleanup Strategy**:
- Exit 0-6: Cleanup (workflow completed/failed)
- Exit 42: NO cleanup (workflow resuming)
- Exit 130: NO cleanup (user may resume manually)

---

### 4. Missing Timeout Handling in Agent Invocation

**Problem**: Agent invocation hangs indefinitely:

```python
# ❌ ANTI-PATTERN - No timeout
try:
    response = await invoke_agent(agent_name, prompt)
    # Hangs forever if agent doesn't respond
except Exception as e:
    pass
```

**Why Bad**:
- User waits indefinitely
- No way to detect stuck agents
- Workflow never completes

**Correct Approach**:

```python
# ✅ CORRECT - Timeout with fallback
timeout_seconds = request_data.get("timeout_seconds", 120)

try:
    response = await invoke_agent_subagent(
        agent_name=agent_name,
        prompt=prompt,
        timeout_seconds=timeout_seconds
    )
    status = "success"
except TimeoutError as e:
    logger.warning(f"Agent timeout after {timeout_seconds}s")
    response = None
    status = "timeout"
    error_message = f"Agent timeout after {timeout_seconds} seconds"
```

**Timeout Recommendations**:
- Quick operations: 30s
- Normal operations: 120s (2 minutes)
- Complex operations: 300s (5 minutes)
- Always write timeout to error response

---

### 5. State File Corruption Without Recovery

**Problem**: State file gets corrupted, workflow can't resume:

```python
# ❌ ANTI-PATTERN - No corruption handling
with open(".template-create-state.json", "r") as f:
    state = json.load(f)  # Fails if malformed
    return TemplateCreateState(**state)
```

**Why Bad**:
- One syntax error breaks entire workflow
- User loses all work-in-progress
- No way to recover partial state

**Correct Approach**:

```python
# ✅ CORRECT - Corruption detection and recovery
try:
    data = json.loads(self.state_file.read_text(encoding="utf-8"))
    return TemplateCreateState(**data)
except json.JSONDecodeError as e:
    print(f"❌ State file corrupted: {e}")
    print(f"   Removing corrupted state and starting fresh")
    self.state_file.unlink(missing_ok=True)
    raise ValueError(f"Malformed state file: {e}")
except TypeError as e:
    print(f"❌ State schema mismatch: {e}")
    print(f"   State file may be from older version")
    self.state_file.unlink(missing_ok=True)
    raise ValueError(f"Invalid state format: {e}")
```

**Recovery Options**:
1. Delete corrupted state, start fresh
2. Show clear error message to user
3. Log details for debugging
4. Optionally backup corrupted file for analysis

---

## Code Quality Recommendations

### 1. Use Type Hints for Clarity

```python
# ✅ GOOD - Clear types
def _ai_enhancement(
    self,
    agent_metadata: dict,
    templates: List[Path],
    template_dir: Path
) -> dict:
    """Generate enhancement using AI."""
    pass

# ❌ BAD - No types
def _ai_enhancement(self, agent_metadata, templates, template_dir):
    """Generate enhancement using AI."""
    pass
```

**Benefits**:
- IDE autocomplete works
- Type checkers catch errors
- Self-documenting code
- Easier refactoring

---

### 2. Document Complex Logic with Comments

```python
# ✅ GOOD - Clear explanation
# Check for existing response from previous invocation (checkpoint-resume pattern)
if invoker.has_response():
    # Response file exists - load cached response
    result_text = invoker.load_response()
else:
    # No response yet - invoke agent (will exit with code 42)
    result_text = invoker.invoke(agent_name="...", prompt=prompt)

# ❌ BAD - No explanation
if invoker.has_response():
    result_text = invoker.load_response()
else:
    result_text = invoker.invoke(agent_name="...", prompt=prompt)
```

**When to Comment**:
- Non-obvious behavior (checkpoint-resume pattern)
- Exit code magic numbers (42, 130)
- Why alternative approaches weren't used
- Edge cases and gotchas

---

### 3. Extract Magic Numbers to Named Constants

```python
# ✅ GOOD - Named constants
DEFAULT_MAX_ITERATIONS = 5
DEFAULT_AGENT_TIMEOUT_SECONDS = 120
MAX_REQUEST_SIZE_BYTES = 1024 * 1024  # 1 MB

if iteration >= DEFAULT_MAX_ITERATIONS:
    print(f"Max iterations ({DEFAULT_MAX_ITERATIONS}) reached")

# ❌ BAD - Magic numbers
if iteration >= 5:
    print("Max iterations (5) reached")
```

**Benefits**:
- Self-documenting (name explains purpose)
- Easy to adjust (single source of truth)
- Testable (can mock constants)
- Searchable (find all uses)

---

### 4. Use Dataclasses for Structured Data

```python
# ✅ GOOD - Dataclass with validation
@dataclass
class AgentResponse:
    request_id: str
    version: str
    status: str
    response: Optional[str]
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    created_at: str
    duration_seconds: float
    metadata: dict

# Validation happens in __init__
response = AgentResponse(**response_data)  # TypeError if wrong fields

# ❌ BAD - Plain dict with no validation
response_data = {
    "request_id": "...",
    "status": "success",
    "result": "..."  # Wrong field name, no error until runtime
}
```

**Benefits**:
- Type checking at creation time
- IDE autocomplete for fields
- Automatic __repr__, __eq__
- asdict() for serialization

---

### 5. Separate Concerns with Helper Methods

```python
# ✅ GOOD - Separated concerns
def _ai_enhancement_with_retry(self, ...):
    """Retry logic wrapper."""
    for attempt in range(max_retries):
        try:
            return self._ai_enhancement(...)  # Actual logic
        except ValidationError:
            raise  # No retry
        except Exception:
            if attempt < max_retries:
                continue  # Retry
            raise

def _ai_enhancement(self, ...):
    """Core AI enhancement logic."""
    prompt = self.prompt_builder.build(...)
    result = self.agent_invoker.invoke(...)
    enhancement = self.parser.parse(result)
    return enhancement

# ❌ BAD - Mixed concerns
def _ai_enhancement(self, ...):
    """AI enhancement with retry."""
    for attempt in range(max_retries):
        try:
            prompt = self.prompt_builder.build(...)
            result = self.agent_invoker.invoke(...)
            enhancement = self.parser.parse(result)
            return enhancement
        except ValidationError:
            raise
        except Exception:
            if attempt < max_retries:
                continue
            raise
```

**Benefits**:
- Single Responsibility Principle
- Easier to test in isolation
- Retry logic reusable
- Core logic clearer

---

## Testing Strategy

### 1. Unit Tests for Core Logic

**What to Test**:
- Response detection logic
- Error handling for each exception type
- State serialization/deserialization
- Validation logic

**Example Test**:

```python
def test_response_detection_before_invocation():
    """Test that enhancer checks for response before invoking."""
    # Setup
    enhancer = SingleAgentEnhancer(strategy="ai")
    agent_file = Path("agent.md")
    template_dir = Path("template/")

    # Mock invoker with cached response
    mock_invoker = Mock()
    mock_invoker.has_response.return_value = True
    mock_invoker.load_response.return_value = '{"sections": ["boundaries"]}'

    # Replace invoker
    enhancer.agent_invoker = mock_invoker

    # Execute
    result = enhancer.enhance(agent_file, template_dir)

    # Verify
    assert mock_invoker.has_response.called
    assert mock_invoker.load_response.called
    assert not mock_invoker.invoke.called  # Should NOT invoke
```

---

### 2. Integration Tests for Checkpoint-Resume Cycle

**What to Test**:
- Full checkpoint-resume cycle
- Response file format validation
- State file preservation
- Cleanup behavior

**Example Test**:

```python
def test_checkpoint_resume_cycle():
    """Test complete checkpoint-resume workflow."""
    # First invocation - should create request and exit 42
    result = subprocess.run(
        ["python3", "orchestrator.py", "--path", "codebase/"],
        capture_output=True
    )
    assert result.returncode == 42  # NEED_AGENT
    assert Path(".agent-request.json").exists()
    assert Path(".template-create-state.json").exists()

    # Simulate agent response
    response_data = {
        "request_id": "test",
        "version": "1.0",
        "status": "success",
        "response": '{"sections": ["boundaries"]}',
        "error_message": None,
        "error_type": None,
        "created_at": datetime.now().isoformat(),
        "duration_seconds": 1.0,
        "metadata": {}
    }
    Path(".agent-response.json").write_text(json.dumps(response_data))

    # Second invocation - should resume and complete
    result = subprocess.run(
        ["python3", "orchestrator.py", "--resume"],
        capture_output=True
    )
    assert result.returncode == 0  # Success
    assert not Path(".agent-request.json").exists()  # Cleaned up
    assert not Path(".agent-response.json").exists()  # Cleaned up
    assert not Path(".template-create-state.json").exists()  # Cleaned up
```

---

### 3. Error Scenario Tests

**What to Test**:
- Malformed response files
- Missing state files
- Timeout handling
- Infinite loop prevention

**Example Test**:

```python
def test_corrupted_response_handling():
    """Test that corrupted response files are handled gracefully."""
    # Setup - create corrupted response file
    Path(".agent-response.json").write_text("INVALID JSON{}")

    # Execute
    invoker = AgentBridgeInvoker()

    with pytest.raises(ValueError, match="Malformed response file"):
        invoker.load_response()

    # Verify cleanup
    assert not Path(".agent-response.json").exists()
```

---

### 4. Regression Tests for Fixed Bugs

**What to Test**:
- TASK-FIX-D4E5: Checkpoint-resume infinite loop
- TASK-FIX-267C: Response format validation

**Example Test**:

```python
def test_no_infinite_loop_on_missing_response_check():
    """
    Regression test for TASK-FIX-D4E5.

    Verify that enhancer checks for response before invoking,
    preventing infinite checkpoint-resume loop.
    """
    # Setup
    enhancer = SingleAgentEnhancer(strategy="ai")

    # Create response file (simulates previous invocation)
    response_data = {
        "request_id": "test",
        "version": "1.0",
        "status": "success",
        "response": '{"sections": ["boundaries"]}',
        "error_message": None,
        "error_type": None,
        "created_at": datetime.now().isoformat(),
        "duration_seconds": 1.0,
        "metadata": {}
    }
    Path(".agent-response.json").write_text(json.dumps(response_data))

    # Execute - should load cached response, NOT write new request
    result = enhancer.enhance(agent_file, template_dir)

    # Verify
    assert result.success
    assert not Path(".agent-request.json").exists()  # Should NOT create new request
```

---

## Regression Prevention Measures

### 1. Code Review Checklist

When reviewing checkpoint-resume code:

- [ ] Does it check `has_response()` before `invoke()`?
- [ ] Does it call `load_response()` when response exists?
- [ ] Does it save state BEFORE calling `invoke()`?
- [ ] Does response format match `AgentResponse` schema?
- [ ] Does it handle exit code 42 without cleanup?
- [ ] Does it have max iterations limit?
- [ ] Does it have clear error messages?
- [ ] Does it log progress for debugging?
- [ ] Does it validate state on load?
- [ ] Does it clean up on success?

---

### 2. Automated Validation

Add pre-commit hooks:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: checkpoint-resume-pattern-check
        name: Check checkpoint-resume pattern
        entry: python scripts/validate_checkpoint_resume.py
        language: system
        files: '.*orchestrator\.py$'
```

Validation script checks:
- `has_response()` called before `invoke()`
- State saved before agent invocation
- Exit code 42 handled correctly
- Response format matches schema

---

### 3. Documentation Standards

**Required Documentation**:
1. Checkpoint-resume pattern explanation
2. Exit code meanings and handling
3. Response format specification
4. State file schema
5. Error recovery procedures

**Example Comment**:

```python
def _ai_enhancement(self, ...):
    """
    Generate enhancement using AI agent.

    Checkpoint-Resume Pattern:
    - First run: Checks has_response() → False → invoke() → exit 42
    - Second run: Checks has_response() → True → load_response() → continue

    Exit Codes:
    - 42: Agent invocation needed (orchestrator handles this)
    - 0: Success
    - Other: Error (propagates to caller)

    See: docs/reference/agent-response-format.md for response schema
    """
```

---

### 4. Reference Implementation

Use `/template-create` as reference for checkpoint-resume pattern:

```python
# Always reference working implementation
# See: installer/core/commands/lib/template_create_orchestrator.py
# Lines 1768-1777: Response detection pattern
# Lines 280-284: State saving before agent invocation
# Lines 1244-1257: Exit code handling dispatch table
```

---

## Summary of Key Takeaways

### Critical Patterns to Follow

1. **Always check `has_response()` before `invoke()`**
   - Prevents infinite loops
   - Enables idempotent operations
   - Fast resume from checkpoint

2. **Save state BEFORE agent invocation**
   - Ensures atomicity
   - Enables perfect resume
   - No work lost on exit 42

3. **Use semantic exit codes with dispatch table**
   - Self-documenting behavior
   - DRY error handling
   - Easy to extend

4. **Validate response format on load**
   - Fail fast on schema errors
   - Clear error messages
   - Reference specification

5. **Handle errors with appropriate strategies**
   - Retry transient failures (timeout, network)
   - Fail fast on permanent failures (validation, schema)
   - Log with context for debugging

---

### Anti-Patterns to Avoid

1. **Invoking without checking response cache**
   - Causes infinite loops
   - Wastes API calls
   - Ignores checkpoint mechanism

2. **Using wrong response format**
   - Field name must be `response` (not `result`)
   - Data type must be JSON string (not object)
   - All required fields must be present

3. **Cleaning up on exit code 42**
   - Breaks checkpoint-resume
   - Loses work-in-progress
   - Forces restart from scratch

4. **Silent failures without logging**
   - User confused about failures
   - Debugging impossible
   - Can't distinguish error types

5. **Missing max iterations check**
   - Infinite loops on bugs
   - No timeout protection
   - User waits forever

---

### Implementation Checklist

When implementing checkpoint-resume pattern:

- [ ] Use `AgentBridgeInvoker` for agent invocation
- [ ] Use `StateManager` for state persistence
- [ ] Check `has_response()` before `invoke()`
- [ ] Save state before calling `invoke()`
- [ ] Handle exit code 42 separately (no cleanup)
- [ ] Use semantic exit codes with dispatch table
- [ ] Implement max iterations limit
- [ ] Add exponential backoff retry for transient failures
- [ ] Validate response format on load
- [ ] Clean up temp files on success
- [ ] Preserve timestamps in state
- [ ] Log progress for debugging
- [ ] Document checkpoint-resume behavior
- [ ] Add integration tests for full cycle
- [ ] Reference format specification

---

## References

### Code Locations

**Working Implementation** (`/template-create`):
- Orchestrator: `installer/core/commands/lib/template_create_orchestrator.py`
- Agent Bridge: `installer/core/lib/agent_bridge/invoker.py`
- State Manager: `installer/core/lib/agent_bridge/state_manager.py`
- Command Wrapper: `installer/core/commands/template-create.md` (lines 1060-1595)

**Fixed Implementation** (`/agent-enhance`):
- Enhancer: `installer/core/lib/agent_enhancement/enhancer.py`
- Fix Location: Lines 269-280 (response detection logic)
- Bug Task: `tasks/completed/TASK-FIX-D4E5/TASK-FIX-D4E5.md`

**Documentation**:
- Response Format: `docs/reference/agent-response-format.md`
- Validation Script: `docs/validation/agent-response-format-test.py`

### Related Tasks

- **TASK-FIX-D4E5**: Fixed checkpoint-resume infinite loop in `/agent-enhance`
- **TASK-FIX-267C**: Fixed response format validation errors
- **TASK-FIX-A7D3**: Fixed Python import scoping (unrelated)
- **TASK-BRIDGE-002**: Agent bridge integration
- **TASK-PHASE-8-INCREMENTAL**: Incremental agent enhancement workflow

---

## Conclusion

The `/template-create` orchestrator demonstrates production-ready checkpoint-resume patterns with:
- ✅ Robust error handling (exponential backoff, failure discrimination)
- ✅ Complete state management (serialization, validation, recovery)
- ✅ Clear user experience (progressive feedback, verbose mode)
- ✅ Maintainable code (separation of concerns, type hints, documentation)
- ✅ Comprehensive testing (unit, integration, regression)

The `/agent-enhance` infinite loop bug was caused by **missing response detection logic** (9 lines), not architectural issues. The fix correctly added `has_response()` check before `invoke()`, bringing it into alignment with the `/template-create` reference implementation.

**Key Lesson**: When implementing checkpoint-resume patterns, **ALWAYS** reference the working `/template-create` implementation and follow the documented best practices to avoid similar bugs.

---

**Document Version**: 1.0
**Last Updated**: 2025-11-24
**Maintenance**: Update when checkpoint-resume pattern evolves or new best practices emerge

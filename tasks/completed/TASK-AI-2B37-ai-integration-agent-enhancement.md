# TASK-AI-2B37: AI Integration for Agent Enhancement

**Task ID**: TASK-AI-2B37
**Priority**: HIGH
**Complexity**: 7/10 (Complex)
**Estimated Duration**: 2-3 days
**Status**: BACKLOG
**Created**: 2025-11-20
**Dependencies**: TASK-TEST-87F4 (should be in progress, not blocking)

---

## Overview

Implement AI integration for the agent enhancement workflow, replacing the placeholder AI strategy with actual Claude Code Task tool invocation to the `agent-content-enhancer` agent.

**CRITICAL IMPLEMENTATION NOTE**:
🚨 **DO NOT USE AgentBridgeInvoker** - This pattern was removed in Phase 7.5 due to 0% success rate. See `docs/reviews/task-ai-2b37-implementation-review.md` for detailed analysis of why AgentBridgeInvoker causes failures.

**Scope**:
- Connect AI strategy to `agent-content-enhancer` agent
- Implement synchronous Task tool invocation with 300s timeout (using `anthropic_sdk.task` API)
- Handle AI response parsing and error cases
- Implement retry logic for transient failures
- Integration with hybrid fallback strategy

**Out of Scope**:
- Testing suite (TASK-TEST-87F4)
- Documentation updates (TASK-DOC-XXX)
- End-to-end testing (TASK-E2E-XXX)

**Required Approach**:
✅ Use direct `anthropic_sdk.task()` API call (see AC1 implementation below)
❌ Do NOT use `AgentBridgeInvoker` (exit code 42 pattern causes 100% failure rate)

---

## Acceptance Criteria

### AC1: Task Tool Integration

- [ ] **AC1.1**: Replace placeholder in `_ai_enhancement()` method with actual Task tool invocation
- [ ] **AC1.2**: Use synchronous API: `from anthropic_sdk import task` (NOT AgentBridgeInvoker)
- [ ] **AC1.3**: Configure 300-second timeout (5 minutes)
- [ ] **AC1.4**: Pass `agent="agent-content-enhancer"` parameter
- [ ] **AC1.5**: Include full prompt with agent metadata and template context
- [ ] **AC1.6**: Verify NO `sys.exit()` calls in implementation
- [ ] **AC1.7**: Verify NO `.agent-request.json` or `.agent-response.json` files created
- [ ] **AC1.8**: Verify NO `AgentBridgeInvoker` imports

**CRITICAL REQUIREMENT**:
🚨 The implementation MUST use `anthropic_sdk.task()` API directly, NOT `AgentBridgeInvoker`.

**Why**: AgentBridgeInvoker uses exit code 42 checkpoint-resume pattern that:
- Terminates the Python process with `sys.exit(42)`
- Creates file-based IPC (`.agent-request.json`)
- Requires orchestrator state persistence
- Has 0% success rate in Phase 7.5 (removed for this reason)

See `docs/reviews/task-ai-2b37-implementation-review.md` for full analysis.

**Implementation** (OPTION A - Direct API - REQUIRED):

```python
def _ai_enhancement(
    self,
    agent_metadata: dict,
    templates: List[Path],
    template_dir: Path
) -> dict:
    """AI-powered enhancement using agent-content-enhancer."""

    # Build prompt using shared prompt builder
    prompt = self.prompt_builder.build(
        agent_metadata,
        templates,
        template_dir
    )

    # Invoke AI with synchronous Task tool API
    from anthropic_sdk import task

    try:
        result = task(
            agent="agent-content-enhancer",
            prompt=prompt,
            timeout=300  # 5 minutes - explicit timeout prevents hanging
        )

        # Parse response using shared parser
        enhancement = self.parser.parse(result)

        # Validate enhancement structure
        self._validate_enhancement(enhancement)

        return enhancement

    except TimeoutError as e:
        logger.warning(f"AI enhancement timed out after 300s: {e}")
        raise
    except Exception as e:
        logger.error(f"AI enhancement failed: {e}")
        raise
```

### AC2: Error Handling

- [ ] **AC2.1**: Handle `TimeoutError` after 300 seconds
- [ ] **AC2.2**: Handle AI response parsing errors (malformed JSON)
- [ ] **AC2.3**: Handle `ValidationError` for invalid enhancement structure
- [ ] **AC2.4**: Log errors with appropriate severity levels
- [ ] **AC2.5**: Propagate exceptions to hybrid strategy fallback

**Error Scenarios**:

```python
# Timeout handling
try:
    result = task(agent="agent-content-enhancer", prompt=prompt, timeout=300)
except TimeoutError:
    logger.warning("AI enhancement timed out, hybrid will fallback to static")
    raise

# Parsing errors
try:
    enhancement = self.parser.parse(result)
except json.JSONDecodeError as e:
    logger.error(f"Failed to parse AI response as JSON: {e}")
    raise ValidationError(f"Invalid JSON response: {e}")

# Validation errors
try:
    self._validate_enhancement(enhancement)
except ValidationError as e:
    logger.error(f"AI returned invalid enhancement structure: {e}")
    raise
```

### AC3: Retry Logic

- [ ] **AC3.1**: Implement retry on transient failures (max 2 retries)
- [ ] **AC3.2**: Exponential backoff between retries (2s, 4s)
- [ ] **AC3.3**: Don't retry on validation errors (permanent failures)
- [ ] **AC3.4**: Log retry attempts with context

**Implementation**:

```python
def _ai_enhancement_with_retry(
    self,
    agent_metadata: dict,
    templates: List[Path],
    template_dir: Path,
    max_retries: int = 2
) -> dict:
    """AI enhancement with retry logic for transient failures."""

    for attempt in range(max_retries + 1):
        try:
            return self._ai_enhancement(agent_metadata, templates, template_dir)

        except TimeoutError:
            if attempt < max_retries:
                wait_time = 2 ** attempt  # 2s, 4s
                logger.warning(f"Attempt {attempt + 1} timed out, retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"AI enhancement failed after {max_retries + 1} attempts")
                raise

        except ValidationError:
            # Don't retry validation errors (permanent)
            logger.error("AI returned invalid response, not retrying")
            raise

        except Exception as e:
            if attempt < max_retries:
                wait_time = 2 ** attempt
                logger.warning(f"Attempt {attempt + 1} failed: {e}, retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"AI enhancement failed after {max_retries + 1} attempts: {e}")
                raise
```

### AC4: Hybrid Strategy Integration

- [ ] **AC4.1**: Hybrid strategy catches AI exceptions and falls back to static
- [ ] **AC4.2**: Log fallback events with reason
- [ ] **AC4.3**: Enhancement result includes `strategy_used` field
- [ ] **AC4.4**: Fallback to static after 3 failed AI attempts

**Current hybrid implementation** (verify fallback works):

```python
def enhance(self, agent_file: Path, template_dir: Path) -> EnhancementResult:
    """Enhance agent file with template-specific content."""

    if self.strategy == "hybrid":
        # Try AI, fallback to static
        try:
            enhancement = self._ai_enhancement_with_retry(
                agent_metadata,
                templates,
                template_dir
            )
            strategy_used = "ai"

        except Exception as e:
            logger.warning(f"AI enhancement failed, falling back to static: {e}")
            enhancement = self._static_enhancement(agent_metadata, templates)
            strategy_used = "static"
```

### AC5: Response Format Validation

- [ ] **AC5.1**: Verify AI response contains required keys: `sections`
- [ ] **AC5.2**: Verify `sections` is a list
- [ ] **AC5.3**: Verify section content matches expected format
- [ ] **AC5.4**: Handle partial responses gracefully

**Validation** (from Clarification #4):

```python
def _validate_enhancement(self, enhancement: dict) -> None:
    """Validate enhancement structure."""

    required_keys = ["sections"]
    for key in required_keys:
        if key not in enhancement:
            raise ValidationError(f"Missing required key: {key}")

    if not isinstance(enhancement["sections"], list):
        raise ValidationError("'sections' must be a list")

    # Verify sections have corresponding content
    for section in enhancement["sections"]:
        if section not in enhancement:
            logger.warning(f"Section '{section}' listed but no content provided")
```

---

## ⚠️ ANTI-PATTERNS TO AVOID

**DO NOT implement using these patterns** (Phase 7.5 failures):

### ❌ WRONG: Using AgentBridgeInvoker

```python
# DO NOT DO THIS - This causes 100% failure rate
from installer.core.lib.agent_bridge.invoker import AgentBridgeInvoker

def _ai_enhancement(...) -> dict:
    invoker = AgentBridgeInvoker(phase=1, phase_name="agent_enhancement")

    # This exits the process with sys.exit(42) - NEVER RETURNS
    result = invoker.invoke("agent-content-enhancer", prompt, timeout_seconds=300)
    # Code after this line NEVER executes
```

**Why This Fails**:
1. `invoker.invoke()` calls `sys.exit(42)` and terminates the process
2. All in-memory state is lost
3. No orchestrator exists to resume execution
4. Results in 100% failure rate (Phase 7.5 experience)

### ✅ CORRECT: Using Direct Task API

```python
# DO THIS - Direct synchronous API call
from anthropic_sdk import task

def _ai_enhancement(...) -> dict:
    start_time = time.time()

    try:
        # Direct API call - blocks until complete, then returns result
        result_text = task(
            agent="agent-content-enhancer",
            prompt=prompt,
            timeout=300
        )

        duration = time.time() - start_time
        logger.info(f"AI response received in {duration:.2f}s")

        enhancement = self.parser.parse(result_text)
        self._validate_enhancement(enhancement)

        return enhancement

    except TimeoutError as e:
        logger.warning(f"AI timed out after 300s: {e}")
        raise  # Propagates to hybrid fallback

    except Exception as e:
        logger.error(f"AI enhancement failed: {e}")
        raise  # Propagates to hybrid fallback
```

**Why This Works**:
1. `task()` is a synchronous function that blocks and returns a value
2. No process exit - execution continues normally
3. Exceptions propagate to hybrid fallback strategy
4. Simple, testable, maintainable

---

## Implementation Plan

### Step 0: Verify Current Implementation (15 minutes) 🚨 NEW

**IMPORTANT**: If you implemented TASK-AI-2B37 previously, verify it doesn't use AgentBridgeInvoker:

```bash
# Check for AgentBridgeInvoker usage
cd installer/core/lib/agent_enhancement
grep -n "AgentBridgeInvoker" enhancer.py

# Check for sys.exit calls
grep -n "sys.exit" enhancer.py

# Check for file-based IPC
grep -n "agent-request" enhancer.py
grep -n "agent-response" enhancer.py
```

**If any of the above return matches**: Implementation is WRONG and must be rewritten (see Step 1A).

**If no matches**: Proceed to Step 1.

### Step 1A: Remove Wrong Implementation (30 minutes) 🚨 IF NEEDED

**Only if AgentBridgeInvoker was used** - DELETE these sections:

```python
# DELETE: AgentBridgeInvoker import (around line 243-246)
_bridge_module = importlib.import_module('installer.core.lib.agent_bridge.invoker')
self._AgentBridgeInvoker = _bridge_module.AgentBridgeInvoker

# DELETE: AgentBridgeInvoker instantiation (around line 278-287)
invoker = self._AgentBridgeInvoker(
    phase=1,
    phase_name="agent_enhancement"
)

# DELETE: invoke() call (around line 289-298)
result_text = invoker.invoke(
    agent_name="agent-content-enhancer",
    prompt=prompt,
    timeout_seconds=300,
    context={...}
)
```

Then proceed to Step 1 below.

### Step 1: Implement Direct Task API (30 minutes)

**File**: `installer/core/lib/agent_enhancement/enhancer.py`

**Find the `_ai_enhancement` method (around line 210-243)**

**Current code (TO REPLACE)**:
```python
def _ai_enhancement(
    self,
    agent_metadata: dict,
    templates: List[Path],
    template_dir: Path
) -> dict:
    """AI-powered enhancement using agent-content-enhancer."""

    # Build prompt
    prompt = self.prompt_builder.build(
        agent_metadata,
        templates,
        template_dir
    )

    # TODO: Implement actual AI invocation via Task tool
    # For now, return placeholder response
    logger.warning("AI enhancement not yet fully implemented - using placeholder")

    # Placeholder implementation
    return {
        "sections": ["related_templates", "examples"],
        "related_templates": "## Related Templates\n\n...",
        "examples": "## Code Examples\n\n(AI-generated examples would go here)",
        "best_practices": ""
    }
```

**NEW CODE (COPY THIS EXACTLY)**:
```python
def _ai_enhancement(
    self,
    agent_metadata: dict,
    templates: List[Path],
    template_dir: Path
) -> dict:
    """
    AI-powered enhancement using agent-content-enhancer.

    Uses direct Task tool API (NOT AgentBridgeInvoker) for synchronous invocation.
    Timeout: 300 seconds. Exceptions propagate to hybrid fallback.

    Args:
        agent_metadata: Agent metadata from frontmatter
        templates: List of relevant template files
        template_dir: Template root directory

    Returns:
        Enhancement dict with sections and content

    Raises:
        TimeoutError: If AI invocation exceeds 300s
        ValidationError: If response structure is invalid
        Exception: For other AI failures
    """
    import time
    import json

    start_time = time.time()
    agent_name = agent_metadata.get('name', 'unknown')

    # Build prompt using shared prompt builder
    prompt = self.prompt_builder.build(
        agent_metadata,
        templates,
        template_dir
    )

    if self.verbose:
        logger.info(f"AI Enhancement Started:")
        logger.info(f"  Agent: {agent_name}")
        logger.info(f"  Templates: {len(templates)}")
        logger.info(f"  Prompt size: {len(prompt)} chars")

    try:
        # DIRECT TASK TOOL INVOCATION (no AgentBridgeInvoker, no sys.exit)
        from anthropic_sdk import task

        result_text = task(
            agent="agent-content-enhancer",
            prompt=prompt,
            timeout=300  # 5 minutes
        )

        duration = time.time() - start_time

        if self.verbose:
            logger.info(f"AI Response Received:")
            logger.info(f"  Duration: {duration:.2f}s")
            logger.info(f"  Response size: {len(result_text)} chars")

        # Parse response using shared parser
        enhancement = self.parser.parse(result_text)

        # Validate enhancement structure
        self._validate_enhancement(enhancement)

        if self.verbose:
            sections = enhancement.get('sections', [])
            logger.info(f"Enhancement Validated:")
            logger.info(f"  Sections: {', '.join(sections)}")

        return enhancement

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

**CRITICAL**: Make sure you:
- ✅ Import `from anthropic_sdk import task` (line 50)
- ✅ Call `task()` function, NOT AgentBridgeInvoker
- ✅ NO `sys.exit()` anywhere
- ✅ Include all logging statements
- ✅ Handle TimeoutError, JSONDecodeError, ValidationError separately

### Step 2: Implement Retry Logic (1 hour)

**Add NEW method after `_ai_enhancement` (around line 300)**

**NEW METHOD (COPY THIS EXACTLY)**:
```python
def _ai_enhancement_with_retry(
    self,
    agent_metadata: dict,
    templates: List[Path],
    template_dir: Path,
    max_retries: int = 2
) -> dict:
    """
    AI enhancement with exponential backoff retry logic.

    Retries on transient failures (TimeoutError, network errors).
    Does NOT retry on ValidationError (permanent failures).

    Args:
        agent_metadata: Agent metadata from frontmatter
        templates: List of relevant template files
        template_dir: Template root directory
        max_retries: Maximum retry attempts (default: 2)

    Returns:
        Enhancement dict from successful attempt

    Raises:
        ValidationError: If AI returns invalid structure (no retry)
        TimeoutError: If all retry attempts timeout
        Exception: If all retry attempts fail
    """
    import time

    agent_name = agent_metadata.get('name', 'unknown')

    for attempt in range(max_retries + 1):  # 0, 1, 2 = 3 total attempts
        try:
            # Log retry attempt
            if attempt > 0:
                backoff_seconds = 2 ** (attempt - 1)  # 1s (2^0), 2s (2^1)
                logger.info(f"Retry attempt {attempt}/{max_retries} for {agent_name} after {backoff_seconds}s backoff")
                time.sleep(backoff_seconds)
            else:
                logger.info(f"Initial attempt for {agent_name}")

            # Attempt AI enhancement
            return self._ai_enhancement(agent_metadata, templates, template_dir)

        except ValidationError as e:
            # Don't retry validation errors (permanent failures)
            logger.warning(f"Validation error for {agent_name} (no retry): {e}")
            raise

        except TimeoutError as e:
            if attempt < max_retries:
                logger.warning(f"Attempt {attempt + 1} timed out for {agent_name}: {e}. Retrying...")
                continue  # Retry
            else:
                logger.error(f"All {max_retries + 1} attempts timed out for {agent_name}")
                raise

        except Exception as e:
            if attempt < max_retries:
                logger.warning(f"Attempt {attempt + 1} failed for {agent_name}: {e}. Retrying...")
                continue  # Retry
            else:
                logger.error(f"All {max_retries + 1} attempts failed for {agent_name}: {e}")
                raise
```

### Step 3: Update Hybrid Strategy (30 minutes)

**Find the `_generate_enhancement` method (around line 190-210)**

**Current code**:
```python
elif self.strategy == "hybrid":
    # Try AI, fallback to static
    try:
        enhancement = self._ai_enhancement(
            agent_metadata,
            templates,
            template_dir
        )
        strategy_used = "ai"
    except Exception as e:
        logger.warning(f"AI enhancement failed, falling back to static: {e}")
        enhancement = self._static_enhancement(agent_metadata, templates)
        strategy_used = "static"
```

**UPDATE TO (find and replace)**:
```python
elif self.strategy == "hybrid":
    # Try AI with retry, fallback to static
    try:
        enhancement = self._ai_enhancement_with_retry(  # ← Changed from _ai_enhancement
            agent_metadata,
            templates,
            template_dir
        )
        strategy_used = "ai"
    except Exception as e:
        logger.warning(f"AI enhancement failed after retries, falling back to static: {e}")
        enhancement = self._static_enhancement(agent_metadata, templates)
        strategy_used = "static"
```

**Also update the "ai" strategy case** (around line 181):
```python
if self.strategy == "ai":
    enhancement = self._ai_enhancement_with_retry(  # ← Changed from _ai_enhancement
        agent_metadata,
        templates,
        template_dir
    )
    strategy_used = "ai"
```

### Step 4: Add Imports at Top of File (5 minutes)

**Find the imports section** (top of `enhancer.py`, around lines 1-20)

**ADD these imports if not present**:
```python
import time
import json
import logging
from typing import List, Optional
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)
```

### Step 5: Verify No Breaking Changes (10 minutes)

**Check that EnhancementResult dataclass has strategy_used field** (around line 30-40):

**Should look like this**:
```python
@dataclass
class EnhancementResult:
    """Result of agent enhancement operation."""
    success: bool
    agent_name: str
    sections: List[str]
    templates: List[Path]
    diff: str
    strategy_used: str = "unknown"  # ← This field should exist
    error: Optional[str] = None
```

If `strategy_used` field is missing, ADD it (default value: "unknown")

### Step 5: Integration Testing (2 hours)

Manual testing:
1. Test successful AI enhancement
2. Test timeout scenario (mock long-running AI)
3. Test parsing error scenario (mock malformed response)
4. Test validation error scenario (mock invalid structure)
5. Test retry logic (mock transient failure)
6. Test hybrid fallback (mock AI failure → static success)

### Step 6: Update Tests (2 hours)

Update `tests/unit/lib/agent_enhancement/test_enhancer.py`:
- Mock Task tool API
- Test retry logic
- Test error handling
- Test hybrid fallback

---

## Testing Strategy

### Unit Tests (with Mocking)

```python
import pytest
from unittest.mock import Mock, patch

def test_ai_enhancement_success():
    """Test successful AI enhancement."""
    with patch('anthropic_sdk.task') as mock_task:
        mock_task.return_value = '{"sections": ["examples"], "examples": "..."}'

        enhancer = SingleAgentEnhancer(strategy="ai")
        result = enhancer.enhance(agent_file, template_dir)

        assert result.success
        assert result.strategy_used == "ai"
        mock_task.assert_called_once_with(
            agent="agent-content-enhancer",
            prompt=ANY,
            timeout=300
        )

def test_ai_enhancement_timeout():
    """Test AI enhancement timeout and retry."""
    with patch('anthropic_sdk.task') as mock_task:
        mock_task.side_effect = TimeoutError("AI timed out")

        enhancer = SingleAgentEnhancer(strategy="ai")

        with pytest.raises(TimeoutError):
            enhancer.enhance(agent_file, template_dir)

        # Should retry twice (3 total attempts)
        assert mock_task.call_count == 3

def test_hybrid_fallback_on_ai_failure():
    """Test hybrid strategy falls back to static on AI failure."""
    with patch('anthropic_sdk.task') as mock_task:
        mock_task.side_effect = Exception("AI failed")

        enhancer = SingleAgentEnhancer(strategy="hybrid")
        result = enhancer.enhance(agent_file, template_dir)

        # Should fallback to static strategy
        assert result.success
        assert result.strategy_used == "static"
```

### Integration Tests (Real AI Invocation)

**File**: `tests/integration/test_ai_enhancement_real.py`

```python
@pytest.mark.integration
@pytest.mark.slow
def test_real_ai_enhancement():
    """Test real AI enhancement (requires agent-content-enhancer)."""

    # Create test agent file
    agent_file = create_test_agent()
    template_dir = create_test_templates()

    enhancer = SingleAgentEnhancer(strategy="ai", verbose=True)
    result = enhancer.enhance(agent_file, template_dir)

    assert result.success
    assert result.strategy_used == "ai"
    assert len(result.sections) > 0
    assert len(result.templates) > 0
```

---

## Error Scenarios

| Scenario | Expected Behavior | Test Coverage |
|----------|------------------|---------------|
| AI timeout (>300s) | Retry 2x with backoff, then raise TimeoutError | Unit + Integration |
| Malformed JSON | Raise ValidationError, don't retry | Unit |
| Missing 'sections' key | Raise ValidationError, don't retry | Unit |
| Empty sections list | Log warning, proceed | Unit |
| Network error | Retry 2x with backoff, then raise | Unit |
| Hybrid fallback | Switch to static strategy, log reason | Unit + Integration |

---

## Performance Considerations

### Timeout Budget

- AI invocation: 300s max
- Retry backoff: 2s + 4s = 6s overhead
- **Total worst case**: 906s (15 minutes) for 3 attempts

### Optimization Strategies

1. **Prompt Size**: Keep prompts concise (<2000 tokens)
2. **Template Selection**: Limit to 10 most relevant templates
3. **Caching**: Cache AI responses for identical prompts (future enhancement)
4. **Async**: Consider async API for parallel enhancements (future)

---

## Dependencies

**Blocks**:
- TASK-E2E-XXX (E2E testing requires working AI)

**Depends On**:
- TASK-PHASE-8-INCREMENTAL (✅ completed)
- TASK-TEST-87F4 (⏳ should be in progress, but not blocking)

**Related**:
- TASK-DOC-XXX (documentation should reference AI integration)

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| AI responses inconsistent | HIGH | MEDIUM | Retry logic + hybrid fallback |
| Timeout too short | MEDIUM | LOW | Configurable timeout parameter (future) |
| Rate limiting | LOW | MEDIUM | Exponential backoff, respect rate limits |
| Response format changes | LOW | HIGH | Strict validation, fail fast with clear errors |

---

## Success Metrics

### Quantitative

- ✅ AI strategy success rate ≥80% (with retries)
- ✅ Hybrid fallback rate <10%
- ✅ Average AI response time <30 seconds
- ✅ 0% permanent failures (hybrid always succeeds)

### Qualitative

- ✅ Clear error messages for all failure scenarios
- ✅ Detailed logging for debugging
- ✅ Graceful degradation (hybrid fallback)
- ✅ Predictable timeout behavior

---

## Deliverables

1. ✅ Updated `installer/core/lib/agent_enhancement/enhancer.py` with real AI integration
2. ✅ Retry logic with exponential backoff
3. ✅ Comprehensive error handling
4. ✅ Updated unit tests with mocking
5. ✅ Integration tests with real AI invocation
6. ✅ Performance logging and metrics

---

## Next Steps

After task creation:

```bash
# Review task details
cat tasks/backlog/TASK-AI-2B37-ai-integration-agent-enhancement.md

# When ready to implement
/task-work TASK-AI-2B37

# Track progress
/task-status TASK-AI-2B37

# Complete after review
/task-complete TASK-AI-2B37
```

---

## ✅ Pre-Merge Verification Checklist

Before merging your implementation, verify ALL of the following:

### Code Verification

```bash
cd installer/core/lib/agent_enhancement

# 1. Verify NO AgentBridgeInvoker usage
grep -n "AgentBridgeInvoker" enhancer.py
# Expected: No matches

# 2. Verify NO sys.exit calls
grep -n "sys.exit" enhancer.py
# Expected: No matches

# 3. Verify NO file-based IPC
grep -n ".agent-request" enhancer.py
grep -n ".agent-response" enhancer.py
# Expected: No matches for both

# 4. Verify anthropic_sdk.task is used
grep -n "from anthropic_sdk import task" enhancer.py
# Expected: At least one match

# 5. Verify timeout is set
grep -n "timeout=300" enhancer.py
# Expected: At least one match
```

### Test Verification

```bash
# 1. Run unit tests
pytest tests/unit/lib/agent_enhancement/test_enhancer.py -v

# Expected: All tests pass (10/10 or more)

# 2. Verify tests mock anthropic_sdk.task (not AgentBridgeInvoker)
grep -n "AgentBridgeInvoker" tests/unit/lib/agent_enhancement/test_enhancer.py
# Expected: No matches

grep -n "anthropic_sdk.task" tests/unit/lib/agent_enhancement/test_enhancer.py
# Expected: Multiple matches (in patches)
```

### Integration Verification

```bash
# 1. Test dry-run (should not crash)
/agent-enhance test-template/test-agent.md --dry-run --verbose
echo "Exit code: $?"  # Should be 0, NOT 42

# 2. Check for leftover state files
ls -la .agent-*.json 2>&1
# Expected: "No such file or directory"

# 3. Run actual enhancement
/agent-enhance test-template/test-agent.md --verbose
# Expected: Success message, no process exit
```

### Final Checklist

- [ ] No `AgentBridgeInvoker` imports in code
- [ ] No `sys.exit()` calls in enhancement flow
- [ ] Uses `anthropic_sdk.task()` API
- [ ] All unit tests pass
- [ ] Tests mock correct API (not AgentBridgeInvoker)
- [ ] Integration test succeeds without exit code 42
- [ ] No `.agent-request.json` or `.agent-response.json` files created
- [ ] Error messages are clear and helpful
- [ ] Logs show AI invocation start/end timestamps
- [ ] Hybrid fallback works on AI failure

**If ALL items above are checked**: ✅ Safe to merge

**If ANY item fails**: ❌ Review `docs/reviews/task-ai-2b37-implementation-review.md` and fix before merging

---

## 📚 Reference Documents

1. **Implementation Review**: `docs/reviews/task-ai-2b37-implementation-review.md`
   - Detailed analysis of AgentBridgeInvoker failures
   - Why Phase 7.5 pattern must be avoided
   - Step-by-step rewrite instructions

2. **Phase 8 Design Review**: `docs/reviews/phase-8-implementation-review.md`
   - Phase 8 design principles
   - Comparison to Phase 7.5
   - Architectural decisions

3. **Implementation Guide**: `docs/guides/template-create-implementation-guide.md`
   - Overall roadmap
   - Task dependencies
   - Success criteria

---

## 🚀 Quick Start Checklist (Copy-Paste Guide)

Use this checklist when implementing TASK-AI-2B37 (third time's the charm!):

### Before You Start

```bash
# 1. Create new branch
git checkout -b ai-integration-attempt-3
git branch -D ai-agent-enhancement  # Delete old failed branch

# 2. Verify clean state
cd /Users/richardwoollcott/Projects/appmilla_github/taskwright
grep -n "AgentBridgeInvoker" installer/core/lib/agent_enhancement/enhancer.py
# Expected: No output (clean)
```

### Implementation Steps

**Step 1**: Open `installer/core/lib/agent_enhancement/enhancer.py`

**Step 2**: Find line ~210-243 (the `_ai_enhancement` method with TODO comment)

**Step 3**: **DELETE** the entire method (lines 210-243)

**Step 4**: **COPY-PASTE** the new `_ai_enhancement` method from Step 1 above (lines 397-492 in this task spec)

**Step 5**: Find line ~244 (after the method you just replaced)

**Step 6**: **INSERT** the `_ai_enhancement_with_retry` method from Step 2 above (lines 507-571 in this task spec)

**Step 7**: Find the `_generate_enhancement` method (around line 190-210)

**Step 8**: **FIND AND REPLACE**:
- Find: `self._ai_enhancement(`
- Replace with: `self._ai_enhancement_with_retry(`
- Should appear in 2 places: "ai" strategy and "hybrid" strategy

**Step 9**: Verify imports at top of file include:
```python
import time
import json
import logging
```

**Step 10**: Verify `EnhancementResult` dataclass has `strategy_used` field

### Verification (MUST DO)

```bash
# Run ALL verification commands

cd /Users/richardwoollcott/Projects/appmilla_github/taskwright/installer/core/lib/agent_enhancement

# 1. NO AgentBridgeInvoker
grep -n "AgentBridgeInvoker" enhancer.py
# Expected: No matches ✅

# 2. NO sys.exit
grep -n "sys.exit" enhancer.py
# Expected: No matches ✅

# 3. NO file-based IPC
grep -n "agent-request" enhancer.py
grep -n "agent-response" enhancer.py
# Expected: No matches for both ✅

# 4. YES anthropic_sdk.task
grep -n "from anthropic_sdk import task" enhancer.py
# Expected: 1 match around line 443 ✅

# 5. YES timeout
grep -n "timeout=300" enhancer.py
# Expected: 1 match around line 448 ✅

# 6. NO TODO comments
grep -n "TODO.*AI" enhancer.py
# Expected: No matches ✅

# 7. NO placeholder warnings
grep -n "not yet fully implemented" enhancer.py
# Expected: No matches ✅
```

### Success Criteria

All of these MUST be true before committing:

- [ ] Deleted old `_ai_enhancement` method with TODO
- [ ] Added new `_ai_enhancement` method with direct Task API
- [ ] Added new `_ai_enhancement_with_retry` method
- [ ] Updated `_generate_enhancement` to call `_with_retry` version
- [ ] All 7 verification commands pass ✅
- [ ] No `AgentBridgeInvoker` anywhere
- [ ] No `sys.exit()` anywhere
- [ ] No `.agent-request.json` or `.agent-response.json` references
- [ ] Uses `anthropic_sdk.task()` API
- [ ] Has 300-second timeout
- [ ] Has exponential backoff retry (2^0=1s, 2^1=2s)
- [ ] Validates enhancement structure
- [ ] Comprehensive error logging

### Commit and Test

```bash
# If ALL checks pass:
git add installer/core/lib/agent_enhancement/enhancer.py
git commit -m "feat(TASK-AI-2B37): Implement AI integration with direct Task API

- Replace placeholder with anthropic_sdk.task() invocation
- Add retry logic with exponential backoff (1s, 2s)
- Update hybrid strategy to use retry version
- Comprehensive error handling and logging
- NO AgentBridgeInvoker (Phase 8 compliance)

Acceptance Criteria:
✅ AC1: Direct Task tool integration
✅ AC2: Error handling (timeout, parsing, validation)
✅ AC3: Retry logic (max 2 retries, no retry on ValidationError)
✅ AC4: Hybrid strategy integration
✅ AC5: Response format validation

See: docs/reviews/task-ai-2b37-implementation-review.md"

# Push to new branch
git push origin ai-integration-attempt-3

# Run basic test
python3 -c "
from installer.core.lib.agent_enhancement.enhancer import SingleAgentEnhancer
print('✅ Import successful - no syntax errors')
"
```

### If Something Goes Wrong

**Problem**: Import error or syntax error

**Solution**:
1. Check you copied the ENTIRE method (opening def to final raise)
2. Check indentation is consistent (4 spaces)
3. Check all quotes are matching

**Problem**: "anthropic_sdk not found"

**Solution**: This is expected - the actual Task tool will be available at runtime via Claude Code, not in standalone Python

**Problem**: Still see TODO or placeholder warning

**Solution**: You didn't delete the old method completely. Search for "TODO" and "placeholder" and delete those sections.

---

## 📋 Final Pre-Merge Checklist

Before running `/task-complete TASK-AI-2B37`:

- [ ] All acceptance criteria met (AC1-AC5)
- [ ] All 7 verification commands pass
- [ ] Code committed to branch
- [ ] Implementation matches specification exactly
- [ ] No AgentBridgeInvoker usage
- [ ] No sys.exit calls
- [ ] No file-based IPC
- [ ] Direct Task API used
- [ ] Retry logic implemented
- [ ] Hybrid strategy updated
- [ ] Error handling comprehensive
- [ ] Logging detailed

**If ANY item unchecked**: Do NOT complete task - fix issues first

**If ALL items checked**: ✅ Ready to complete!

---

**Created**: 2025-11-20
**Updated**: 2025-11-21 (added comprehensive copy-paste implementation guide)
**Status**: BACKLOG
**Ready for Implementation**: YES (with step-by-step code snippets)

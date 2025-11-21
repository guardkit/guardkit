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

**Scope**:
- Connect AI strategy to `agent-content-enhancer` agent
- Implement synchronous Task tool invocation with 300s timeout
- Handle AI response parsing and error cases
- Implement retry logic for transient failures
- Integration with hybrid fallback strategy

**Out of Scope**:
- Testing suite (TASK-TEST-87F4)
- Documentation updates (TASK-DOC-XXX)
- End-to-end testing (TASK-E2E-XXX)

---

## Acceptance Criteria

### AC1: Task Tool Integration

- [ ] **AC1.1**: Replace placeholder in `_ai_enhancement()` method with actual Task tool invocation
- [ ] **AC1.2**: Use synchronous API: `from anthropic_sdk import task`
- [ ] **AC1.3**: Configure 300-second timeout (5 minutes)
- [ ] **AC1.4**: Pass `agent="agent-content-enhancer"` parameter
- [ ] **AC1.5**: Include full prompt with agent metadata and template context

**Implementation** (from Architectural Review Clarification #1):

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

## Implementation Plan

### Step 1: Remove Placeholder (30 minutes)

**File**: `installer/global/lib/agent_enhancement/enhancer.py`

Current placeholder:

```python
def _ai_enhancement(
    self,
    agent_metadata: dict,
    templates: List[Path],
    template_dir: Path
) -> dict:
    """AI-powered enhancement."""

    # Build prompt using shared prompt builder
    prompt = self.prompt_builder.build(
        agent_metadata,
        templates,
        template_dir
    )

    # Invoke AI (direct Task tool invocation)
    from anthropic_sdk import task
    result = task(
        agent="agent-content-enhancer",
        prompt=prompt,
        timeout=300
    )

    # Parse response using shared parser
    enhancement = self.parser.parse(result)

    return enhancement
```

Replace with full implementation including error handling and retry logic.

### Step 2: Implement Retry Logic (1 hour)

Add `_ai_enhancement_with_retry()` method with:
- Exponential backoff (2s, 4s)
- Max 2 retries (3 total attempts)
- Skip retry on ValidationError
- Detailed logging

### Step 3: Update Hybrid Strategy (30 minutes)

Ensure hybrid strategy calls `_ai_enhancement_with_retry()` instead of `_ai_enhancement()`.

Add `strategy_used` tracking to EnhancementResult.

### Step 4: Enhance Error Logging (30 minutes)

Add structured logging:
- AI invocation start/end timestamps
- Prompt size (character count)
- Response size
- Parsing success/failure
- Retry attempts

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

1. ✅ Updated `installer/global/lib/agent_enhancement/enhancer.py` with real AI integration
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

**Created**: 2025-11-20
**Status**: BACKLOG
**Ready for Implementation**: YES

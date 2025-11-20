# TASK-PHASE-7.5-SIMPLE: Simplified Sequential Agent Enhancement

**Task ID**: TASK-PHASE-7.5-SIMPLE
**Priority**: HIGH
**Complexity**: 4/10 (Simple Task)
**Estimated Duration**: 3-5 days
**Status**: Specification Complete - Ready for Implementation

---

## Overview

Replace the failed Phase 7.5 agent enhancement system (1,468 lines, 0% success rate) with a simplified sequential enhancement approach (~50 lines, proven direct Task invocation pattern).

**Key Changes**:
- ❌ Remove: Agent bridge pattern (exit code 42, checkpoint-resume, file-based IPC)
- ✅ Add: Simple sequential loop with direct Task tool invocation
- ✅ Add: Per-agent error handling (failures isolated)
- ✅ Result: 97% code reduction (1,468 → 50 lines)

---

## Acceptance Criteria

### 1. Code Implementation

- [ ] **AC1.1**: `agent_enhancer.py` (1,468 lines) deleted completely
- [ ] **AC1.2**: Agent bridge invocation removed from orchestrator
- [ ] **AC1.3**: New method `_run_phase_7_5_agent_enhancement_simple` added to orchestrator
- [ ] **AC1.4**: Method is async and uses direct `await task(...)` invocation
- [ ] **AC1.5**: Sequential processing (one agent at a time, for loop)
- [ ] **AC1.6**: Per-agent error handling (try/except per iteration)

### 2. Error Handling

- [ ] **AC2.1**: `TimeoutError` caught → skip agent, log warning, continue
- [ ] **AC2.2**: `json.JSONDecodeError` caught → skip agent, log response snippet, continue
- [ ] **AC2.3**: `PermissionError` caught → raise `PhaseError` (CRITICAL, block workflow)
- [ ] **AC2.4**: Generic `Exception` caught → skip agent, log full traceback, continue
- [ ] **AC2.5**: Error aggregation by category (summary at end)
- [ ] **AC2.6**: No silent failures (all errors explicitly logged)

### 3. Result Reporting

- [ ] **AC3.1**: Returns `PhaseResult` with `enhanced_count` and `skipped_count`
- [ ] **AC3.2**: Includes error list with structured `EnhancementError` objects
- [ ] **AC3.3**: Success message: "✓ All N agents enhanced successfully"
- [ ] **AC3.4**: Warning message: "N/M succeeded, M-N skipped"
- [ ] **AC3.5**: Error summary by category logged at end

### 4. Helper Methods

- [ ] **AC4.1**: `_build_enhancement_prompt(agent_file, templates, template_dir)` implemented
- [ ] **AC4.2**: Prompt includes agent metadata, template list, code samples, JSON schema
- [ ] **AC4.3**: `_validate_enhancement(enhancement)` checks required keys and types
- [ ] **AC4.4**: `_apply_enhancement(agent_file, enhancement)` appends sections to file
- [ ] **AC4.5**: All helper methods have comprehensive docstrings

### 5. Testing

- [ ] **AC5.1**: 8 unit tests passing (100% pass rate)
- [ ] **AC5.2**: 3 integration tests passing (100% pass rate)
- [ ] **AC5.3**: Test coverage ≥85% for new code
- [ ] **AC5.4**: All error paths tested (timeout, JSON parse, permission)
- [ ] **AC5.5**: Mock AI invocation in unit tests (no real API calls)

### 6. Documentation

- [ ] **AC6.1**: Method docstrings complete (purpose, args, returns, errors)
- [ ] **AC6.2**: Error handling strategy documented
- [ ] **AC6.3**: Integration points documented
- [ ] **AC6.4**: CLAUDE.md updated (remove agent bridge references)

---

## Implementation Specification

### File Changes

**Delete**:
- `installer/global/lib/template_creation/agent_enhancer.py` (1,468 lines)
- `tests/unit/lib/template_creation/test_agent_enhancer.py` (22 tests, all mocking)

**Modify**:
- `installer/global/commands/lib/template_create_orchestrator.py`:
  - Remove imports (lines ~36-40, 61-63): `AgentBridgeInvoker`, `StateManager`, `AgentEnhancer`
  - Remove checkpoint logic (lines ~879-943): `_run_from_phase_7`
  - Add new method: `_run_phase_7_5_agent_enhancement_simple` (~50 lines)
  - Add helper methods: `_build_enhancement_prompt`, `_validate_enhancement`, `_apply_enhancement`
  - Update phase dispatcher (line ~500): Call new method instead of bridge

**Add**:
- `tests/unit/lib/template_creation/test_simple_enhancement.py` (8 tests, ~200 lines)
- `tests/integration/test_template_create_simple_enhancement.py` (3 tests, ~150 lines)

### Net Code Change

- **Removed**: ~1,668 lines (1,468 enhancer + 200 orchestrator bridge code)
- **Added**: ~400 lines (50 orchestrator + 150 helpers + 200 docstrings)
- **Net Reduction**: ~1,268 lines (76% reduction)

---

## Code Implementation

### Main Method

```python
# File: installer/global/commands/lib/template_create_orchestrator.py

async def _run_phase_7_5_agent_enhancement_simple(
    self,
    state: TemplateCreateState
) -> PhaseResult:
    """
    Simplified agent enhancement using direct Task tool invocation.

    Architecture:
    - Sequential processing (no batch complexity)
    - Direct Task tool invocation (no agent bridge)
    - Per-agent error handling (failures isolated)
    - Result aggregation (partial success supported)

    Error Handling:
    - AI timeout: Skip agent, log warning, continue
    - JSON parse: Skip agent, log response snippet, continue
    - Permission error: Raise PhaseError (critical)
    - Unknown error: Skip agent, log traceback, continue

    Args:
        state: Current template creation state

    Returns:
        PhaseResult with enhanced_count, skipped_count, and error details

    Raises:
        PhaseError: If critical errors occur (file permissions, disk full)
    """

    template_dir = state.output_path
    agent_files = list((template_dir / "agents").glob("*.md"))
    all_templates = list((template_dir / "templates").rglob("*.template"))

    if not agent_files:
        logger.warning("No agent files found to enhance")
        return PhaseResult(success=True, enhanced_count=0)

    logger.info(f"Enhancing {len(agent_files)} agents...")

    results = []
    errors = []

    for agent_file in agent_files:
        try:
            # 1. Build enhancement prompt
            prompt = self._build_enhancement_prompt(
                agent_file,
                all_templates,
                template_dir
            )

            # 2. Invoke AI (direct Task tool, NO bridge)
            from anthropic_sdk import task
            result = await task(
                agent="agent-content-enhancer",
                prompt=prompt,
                timeout=300  # 5 minutes per agent
            )

            # 3. Parse response
            enhancement = json.loads(result)

            # 4. Validate enhancement
            self._validate_enhancement(enhancement)

            # 5. Apply to agent file
            self._apply_enhancement(agent_file, enhancement)

            # 6. Record success
            results.append({
                "agent": agent_file.stem,
                "status": "success",
                "sections_added": len(enhancement.get("sections", []))
            })

            logger.info(f"  ✓ Enhanced {agent_file.stem}")

        except TimeoutError as e:
            error = EnhancementError(
                agent_name=agent_file.stem,
                category=ErrorCategory.AI_TIMEOUT,
                message="AI enhancement timed out after 5 minutes",
                context={"agent_file": str(agent_file)},
                recoverable=True
            )
            errors.append(error)
            logger.warning(f"  ⚠ {error.message} for {agent_file.stem}")
            results.append({"status": "skipped", "error": error})

        except json.JSONDecodeError as e:
            error = EnhancementError(
                agent_name=agent_file.stem,
                category=ErrorCategory.JSON_PARSE,
                message="Invalid JSON response from AI",
                context={
                    "agent_file": str(agent_file),
                    "response_snippet": result[:200] if 'result' in locals() else None,
                    "json_error": str(e)
                },
                recoverable=True
            )
            errors.append(error)
            logger.warning(f"  ⚠ {error.message} for {agent_file.stem}")
            logger.debug(f"    Response snippet: {error.context['response_snippet']}")
            results.append({"status": "skipped", "error": error})

        except PermissionError as e:
            # CRITICAL: Cannot write files
            error = EnhancementError(
                agent_name=agent_file.stem,
                category=ErrorCategory.FILE_PERMISSION,
                message=f"Cannot write to agent file: {e}",
                context={"agent_file": str(agent_file)},
                recoverable=False
            )
            logger.error(f"  ✗ CRITICAL: {error.message}")
            raise PhaseError(
                phase="7.5",
                message="Cannot write to agent files - check permissions",
                errors=[error]
            ) from e

        except Exception as e:
            error = EnhancementError(
                agent_name=agent_file.stem,
                category=ErrorCategory.UNEXPECTED,
                message=f"Unexpected error: {type(e).__name__}",
                context={
                    "agent_file": str(agent_file),
                    "exception_type": type(e).__name__,
                    "exception_message": str(e)
                },
                recoverable=True
            )
            errors.append(error)
            logger.exception(f"  ⚠ Unexpected error enhancing {agent_file.stem}")
            results.append({"status": "skipped", "error": error})

    # Summarize results
    success_count = sum(1 for r in results if r.get("status") == "success")
    skipped_count = len(results) - success_count

    if skipped_count > 0:
        logger.warning(
            f"Agent enhancement: {success_count}/{len(results)} succeeded, "
            f"{skipped_count} skipped"
        )

        # Report errors by category
        error_summary = {}
        for error in errors:
            category = error.category.value
            error_summary[category] = error_summary.get(category, 0) + 1

        logger.warning("Errors by category:")
        for category, count in error_summary.items():
            logger.warning(f"  {category}: {count} agent(s)")
    else:
        logger.info(f"✓ All {success_count} agents enhanced successfully")

    return PhaseResult(
        success=True,  # Phase succeeds even if some agents skipped
        enhanced_count=success_count,
        skipped_count=skipped_count,
        errors=errors,
        results=results
    )
```

### Helper Methods

```python
def _build_enhancement_prompt(
    self,
    agent_file: Path,
    all_templates: List[Path],
    template_dir: Path
) -> str:
    """
    Build enhancement prompt for single agent.

    Includes:
    - Agent metadata (name, description, technologies)
    - Available templates with paths
    - Code samples from relevant templates
    - Expected output format (JSON schema)

    Args:
        agent_file: Path to agent file to enhance
        all_templates: List of all template files in template directory
        template_dir: Root template directory

    Returns:
        Formatted prompt string for AI
    """

    # Load agent metadata
    import frontmatter
    agent_content = agent_file.read_text()
    agent_doc = frontmatter.loads(agent_content)
    metadata = agent_doc.metadata

    # Format template list
    template_list = self._format_template_list(all_templates, template_dir)

    # Build prompt
    prompt = f"""
Enhance the following agent with template-specific content.

AGENT INFORMATION:
- Name: {metadata.get('name', agent_file.stem)}
- Description: {metadata.get('description', 'N/A')}
- Technologies: {metadata.get('technologies', [])}
- Priority: {metadata.get('priority', 'medium')}

AVAILABLE TEMPLATES ({len(all_templates)} total):
{template_list}

YOUR TASK:
1. Identify templates relevant to this agent (based on name, technologies, patterns)
2. Read code from relevant templates to understand patterns
3. Generate enhancement sections:
   - Related templates (paths and descriptions)
   - Code examples (from templates, demonstrating patterns)
   - Best practices (stack-specific, drawn from templates)
   - Anti-patterns to avoid (if applicable)

OUTPUT FORMAT (JSON):
{{
    "sections": ["related_templates", "examples", "best_practices"],
    "related_templates": "## Related Templates\\n\\n...",
    "examples": "## Code Examples\\n\\n...",
    "best_practices": "## Best Practices\\n\\n...",
    "anti_patterns": "## Anti-Patterns\\n\\n..." // optional
}}

IMPORTANT:
- Return ONLY valid JSON (no markdown wrappers)
- Include actual code snippets from templates
- Keep examples concise (10-30 lines each)
- Focus on patterns this agent would use
"""

    return prompt


def _format_template_list(
    self,
    templates: List[Path],
    template_dir: Path
) -> str:
    """
    Format template list for prompt.

    Args:
        templates: List of template file paths
        template_dir: Root template directory

    Returns:
        Formatted list string (numbered, relative paths)
    """

    lines = []
    for i, template in enumerate(templates[:50], 1):  # Limit to 50 templates
        rel_path = template.relative_to(template_dir)
        lines.append(f"{i}. {rel_path}")

    if len(templates) > 50:
        lines.append(f"... and {len(templates) - 50} more")

    return "\n".join(lines)


def _validate_enhancement(self, enhancement: dict) -> None:
    """
    Validate enhancement structure.

    Args:
        enhancement: Parsed enhancement dictionary

    Raises:
        ValidationError: If enhancement structure is invalid
    """

    required_keys = ["sections"]
    for key in required_keys:
        if key not in enhancement:
            raise ValidationError(f"Missing required key: {key}")

    if not isinstance(enhancement["sections"], list):
        raise ValidationError("'sections' must be a list")

    for section in enhancement["sections"]:
        if section not in enhancement:
            raise ValidationError(
                f"Declared section '{section}' not found in enhancement"
            )


def _apply_enhancement(
    self,
    agent_file: Path,
    enhancement: dict
) -> None:
    """
    Apply enhancement to agent file.

    Appends enhancement sections to existing agent content.

    Args:
        agent_file: Path to agent file
        enhancement: Enhancement dictionary with sections

    Raises:
        PermissionError: If cannot write to agent file
        IOError: If file operations fail
    """

    # Read existing content
    current_content = agent_file.read_text()

    # Build enhancement content
    enhancement_content = "\n\n"
    for section in enhancement.get("sections", []):
        section_content = enhancement.get(section, "")
        if section_content:
            enhancement_content += section_content + "\n\n"

    # Write enhanced content
    enhanced_content = current_content + enhancement_content
    agent_file.write_text(enhanced_content)
```

### Error Types

```python
# Add to orchestrator imports or separate module

from enum import Enum
from dataclasses import dataclass
from typing import Optional

class ErrorCategory(Enum):
    """Error categories for agent enhancement."""
    AI_TIMEOUT = "ai_timeout"
    AI_ERROR = "ai_error"
    JSON_PARSE = "json_parse_error"
    VALIDATION = "validation_error"
    FILE_PERMISSION = "file_permission"
    FILE_NOT_FOUND = "file_not_found"
    UNEXPECTED = "unexpected_error"

@dataclass
class EnhancementError:
    """Structured error information for agent enhancement."""
    agent_name: str
    category: ErrorCategory
    message: str
    context: Optional[dict] = None
    recoverable: bool = True
```

---

## Test Specifications

### Unit Tests (8 tests, ~200 lines)

```python
# File: tests/unit/lib/template_creation/test_simple_enhancement.py

import pytest
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path
import json

class TestSimpleEnhancement:
    """Unit tests for simplified agent enhancement."""

    @pytest.mark.asyncio
    async def test_enhance_single_agent_success(self):
        """Test successful enhancement of single agent."""
        # Arrange
        agent_file = Path("agent.md")
        templates = [Path("template1.cs"), Path("template2.cs")]
        mock_task = AsyncMock(return_value='{"sections": ["related_templates"]}')

        orchestrator = TemplateCreateOrchestrator()

        # Act
        with patch('anthropic_sdk.task', mock_task):
            result = await orchestrator._run_phase_7_5_agent_enhancement_simple(state)

        # Assert
        assert result.success is True
        assert result.enhanced_count == 1
        assert result.skipped_count == 0
        mock_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_enhance_handles_json_parse_error(self):
        """Test handling of invalid JSON response."""
        # Arrange
        mock_task = AsyncMock(return_value='Invalid JSON {]')
        orchestrator = TemplateCreateOrchestrator()

        # Act
        with patch('anthropic_sdk.task', mock_task):
            result = await orchestrator._run_phase_7_5_agent_enhancement_simple(state)

        # Assert
        assert result.success is True  # Phase continues
        assert result.enhanced_count == 0
        assert result.skipped_count == 1
        assert result.errors[0].category == ErrorCategory.JSON_PARSE

    @pytest.mark.asyncio
    async def test_enhance_handles_timeout(self):
        """Test handling of AI timeout."""
        # Arrange
        mock_task = AsyncMock(side_effect=TimeoutError("Timed out"))
        orchestrator = TemplateCreateOrchestrator()

        # Act
        with patch('anthropic_sdk.task', mock_task):
            result = await orchestrator._run_phase_7_5_agent_enhancement_simple(state)

        # Assert
        assert result.success is True  # Phase continues
        assert result.skipped_count == 1
        assert result.errors[0].category == ErrorCategory.AI_TIMEOUT

    @pytest.mark.asyncio
    async def test_enhance_raises_on_permission_error(self):
        """Test that permission errors raise PhaseError."""
        # Arrange
        mock_task = AsyncMock(return_value='{"sections": []}')
        mock_write = Mock(side_effect=PermissionError("Cannot write"))

        orchestrator = TemplateCreateOrchestrator()

        # Act & Assert
        with patch('anthropic_sdk.task', mock_task):
            with patch('pathlib.Path.write_text', mock_write):
                with pytest.raises(PhaseError) as exc_info:
                    await orchestrator._run_phase_7_5_agent_enhancement_simple(state)

                assert "Cannot write to agent files" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_enhance_all_agents_continues_on_failure(self):
        """Test that enhancement continues when one agent fails."""
        # Arrange
        agent_files = [Path("agent1.md"), Path("agent2.md"), Path("agent3.md")]

        call_count = [0]
        async def mock_task_varied(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:  # Second agent fails
                raise TimeoutError("Timed out")
            return '{"sections": ["related"]}'

        orchestrator = TemplateCreateOrchestrator()

        # Act
        with patch('anthropic_sdk.task', mock_task_varied):
            result = await orchestrator._run_phase_7_5_agent_enhancement_simple(state)

        # Assert
        assert result.enhanced_count == 2  # 2/3 succeeded
        assert result.skipped_count == 1
        assert len(result.errors) == 1

    def test_build_enhancement_prompt_includes_context(self):
        """Test that prompt includes agent and template context."""
        # Arrange
        agent_file = Path("repository-pattern-specialist.md")
        templates = [Path("Repository.cs.template")]
        template_dir = Path("template")

        orchestrator = TemplateCreateOrchestrator()

        # Act
        prompt = orchestrator._build_enhancement_prompt(
            agent_file, templates, template_dir
        )

        # Assert
        assert "repository-pattern-specialist" in prompt
        assert "Repository.cs" in prompt
        assert "templates" in prompt.lower()
        assert "JSON" in prompt  # Output format specified

    def test_apply_enhancement_writes_to_file(self, tmp_path):
        """Test that enhancement is correctly written to file."""
        # Arrange
        agent_file = tmp_path / "agent.md"
        agent_file.write_text("# Agent\n\nOriginal content")
        enhancement = {
            "sections": ["related_templates"],
            "related_templates": "## Related Templates\n- Template1"
        }

        orchestrator = TemplateCreateOrchestrator()

        # Act
        orchestrator._apply_enhancement(agent_file, enhancement)

        # Assert
        content = agent_file.read_text()
        assert "## Related Templates" in content
        assert "Template1" in content
        assert "Original content" in content  # Preserved

    def test_error_aggregation_by_category(self):
        """Test that errors are correctly aggregated by category."""
        # Arrange
        errors = [
            EnhancementError(
                agent_name="agent1",
                category=ErrorCategory.AI_TIMEOUT,
                message="Timeout"
            ),
            EnhancementError(
                agent_name="agent2",
                category=ErrorCategory.AI_TIMEOUT,
                message="Timeout"
            ),
            EnhancementError(
                agent_name="agent3",
                category=ErrorCategory.JSON_PARSE,
                message="Parse error"
            ),
        ]

        # Act
        summary = {}
        for error in errors:
            category = error.category.value
            summary[category] = summary.get(category, 0) + 1

        # Assert
        assert summary[ErrorCategory.AI_TIMEOUT.value] == 2
        assert summary[ErrorCategory.JSON_PARSE.value] == 1
```

### Integration Tests (3 tests, ~150 lines)

```python
# File: tests/integration/test_template_create_simple_enhancement.py

import pytest
from pathlib import Path
import shutil

class TestTemplateCreateSimpleEnhancement:
    """Integration tests for Phase 7.5 simplified enhancement."""

    @pytest.fixture
    def template_fixture(self, tmp_path):
        """Create test template structure."""
        template_dir = tmp_path / "test-template"
        (template_dir / "agents").mkdir(parents=True)
        (template_dir / "templates" / "domain").mkdir(parents=True)

        # Create 3 basic agent files
        for i in range(3):
            agent_file = template_dir / "agents" / f"agent-{i}.md"
            agent_file.write_text(f"# Agent {i}\n\nBasic agent")

        # Create 5 template files
        for i in range(5):
            template_file = template_dir / "templates" / "domain" / f"Template{i}.cs.template"
            template_file.write_text(f"public class Template{i} {{}}")

        return template_dir

    @pytest.mark.asyncio
    async def test_enhance_all_agents_integration(self, template_fixture):
        """Test full enhancement workflow with real file I/O."""
        # Arrange
        orchestrator = TemplateCreateOrchestrator()
        state = TemplateCreateState(output_path=template_fixture)

        # Act
        result = await orchestrator._run_phase_7_5_agent_enhancement_simple(state)

        # Assert
        assert result.success is True
        assert result.enhanced_count == 3  # All 3 agents enhanced
        assert result.skipped_count == 0

        # Verify agent files were modified
        for i in range(3):
            agent_file = template_fixture / "agents" / f"agent-{i}.md"
            content = agent_file.read_text()
            assert len(content) > 50  # Enhanced (was ~30 chars)

    @pytest.mark.asyncio
    async def test_enhance_with_ai_failure(self, template_fixture, monkeypatch):
        """Test enhancement continues when AI fails for some agents."""
        # Arrange
        call_count = [0]

        async def mock_task(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:  # Second agent fails
                raise TimeoutError("Timed out")
            return '{"sections": ["related"]}'

        monkeypatch.setattr('anthropic_sdk.task', mock_task)
        orchestrator = TemplateCreateOrchestrator()
        state = TemplateCreateState(output_path=template_fixture)

        # Act
        result = await orchestrator._run_phase_7_5_agent_enhancement_simple(state)

        # Assert
        assert result.success is True
        assert result.enhanced_count == 2  # 2/3 succeeded
        assert result.skipped_count == 1
        assert len(result.errors) == 1
        assert result.errors[0].category == ErrorCategory.AI_TIMEOUT

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_enhance_regenerates_existing_template(self):
        """Test that enhancement works on real reference template."""
        # Arrange
        template_path = Path("installer/global/templates/react-typescript")
        if not template_path.exists():
            pytest.skip("Reference template not available")

        # Backup original agents
        backup_dir = template_path.parent / "react-typescript-backup"
        shutil.copytree(template_path / "agents", backup_dir, dirs_exist_ok=True)

        try:
            orchestrator = TemplateCreateOrchestrator()
            state = TemplateCreateState(output_path=template_path)

            # Act
            result = await orchestrator._run_phase_7_5_agent_enhancement_simple(state)

            # Assert
            assert result.success is True
            assert result.enhanced_count >= 5  # At least 5 agents
            assert result.skipped_count == 0

        finally:
            # Restore original agents
            shutil.rmtree(template_path / "agents")
            shutil.copytree(backup_dir, template_path / "agents")
            shutil.rmtree(backup_dir)
```

---

## Edge Cases to Handle

### 1. Empty Agent Files
- **Scenario**: Agent file exists but has no frontmatter
- **Expected**: Skip agent, log warning, continue
- **Test**: `test_enhance_handles_missing_frontmatter`

### 2. Large Template Sets
- **Scenario**: 200+ template files
- **Expected**: Limit prompt to first 50 templates, indicate truncation
- **Test**: `test_build_prompt_limits_template_list`

### 3. AI Returns Markdown-Wrapped JSON
- **Scenario**: AI returns `` ```json\n{...}\n``` ``
- **Expected**: Strip markdown wrapper before parsing
- **Enhancement**: Add markdown stripping to `_apply_enhancement`

### 4. Concurrent File Access
- **Scenario**: Another process modifies agent file during enhancement
- **Expected**: Retry write once, then fail with clear error
- **Not in initial implementation**: Accept for now (low probability)

### 5. Disk Full
- **Scenario**: No space left on device
- **Expected**: Raise `PhaseError`, block workflow
- **Test**: `test_enhance_handles_disk_full`

---

## Performance Characteristics

### Expected Performance

**Sequential Processing**:
- 5 minutes per agent (AI invocation timeout)
- 7 agents × 5 min = **35 minutes maximum**
- Typical: 2-3 min per agent = **14-21 minutes for 7 agents**

**Comparison to Failed Implementation**:
- Failed implementation: 10 days debugging, 0% success
- New implementation: 14-35 min, ≥70% success expected

**Acceptable?**: ✅ YES
- Total template creation: ~1-2 hours (Phases 1-7.5)
- Enhancement is 25-50% of total time
- Fast enough for infrequent operation (creating templates)
- Can optimize later if needed (parallel processing)

### Memory Usage

**Estimate**:
- Agent file: ~1 KB (33 lines)
- Template files: ~200 KB (100 templates × 2 KB each)
- Prompt: ~50 KB (agent + templates + instructions)
- AI response: ~10 KB (150 lines of enhancement)
- **Total per agent**: ~261 KB
- **Peak usage**: ~2 MB (sequential, low memory pressure)

**Acceptable?**: ✅ YES
- Memory usage negligible
- No caching required
- Sequential processing keeps memory low

---

## Risk Assessment

### High-Confidence Risks (>50% likelihood)

**Risk 1: AI Returns Invalid JSON** (60% likelihood)
- **Impact**: Medium (agent skipped)
- **Mitigation**: Structured error handling, log response snippet
- **Fallback**: Skip agent, continue with others
- **Test**: `test_enhance_handles_json_parse_error`

**Risk 2: Users Want Per-Agent Control** (60% likelihood)
- **Impact**: Medium (feature request)
- **Mitigation**: Implement Option 2 (incremental workflow) if requested
- **Fallback**: Current automation is baseline
- **Action**: Monitor user feedback

### Medium-Confidence Risks (25-50% likelihood)

**Risk 3: Enhancement Quality Lower Than Expected** (40% likelihood)
- **Impact**: Medium (requires prompt iteration)
- **Mitigation**: Comprehensive prompt with examples, clear output format
- **Fallback**: Iterate on prompt based on results
- **Test**: Manual review of enhanced agents

**Risk 4: AI Timeout Frequency Higher Than Expected** (30% likelihood)
- **Impact**: Low (agents skipped but workflow continues)
- **Mitigation**: 5-minute timeout per agent (generous)
- **Fallback**: Increase timeout if needed
- **Test**: `test_enhance_handles_timeout`

### Low-Confidence Risks (<25% likelihood)

**Risk 5: Performance Degradation** (15% likelihood)
- **Impact**: Low (35 min acceptable)
- **Mitigation**: Sequential processing is simple and reliable
- **Fallback**: Parallelize if truly needed (future)
- **Test**: Integration test measures duration

**Risk 6: File Permission Issues** (10% likelihood)
- **Impact**: High (blocks workflow)
- **Mitigation**: Raise `PhaseError`, clear error message
- **Fallback**: User fixes permissions, re-runs
- **Test**: `test_enhance_raises_on_permission_error`

---

## Success Metrics

### Code Quality Targets

- **Cyclomatic Complexity**: <5 per method (currently: 8.5 in failed implementation)
- **Lines per Method**: <50 lines (currently: 49 average in failed implementation)
- **Test Coverage**: ≥85% line coverage
- **Documentation**: 100% public methods documented

### Functional Targets

- **Success Rate**: ≥70% agents enhanced (vs 0% currently)
- **Failure Isolation**: 100% (one agent fails, others continue)
- **Error Visibility**: 0 silent failures (vs 8 silent failure points currently)
- **Performance**: ≤5 min per agent average

### User Experience Targets

- **Clear Feedback**: Success count, skip count, error summary
- **Actionable Errors**: Error messages explain what happened and why
- **Progress Visibility**: Log messages for each agent (✓ Enhanced, ⚠ Skipped)
- **Partial Success**: "N/M succeeded" instead of all-or-nothing

---

## Implementation Checklist

### Pre-Implementation (Day 0)

- [ ] Backup current implementation to branch
- [ ] Review architectural analysis (TASK-09E9)
- [ ] Review this task specification
- [ ] Set up test fixtures (template structure)

### Day 1: Remove Failed Implementation

- [ ] Delete `agent_enhancer.py` (1,468 lines)
- [ ] Remove agent bridge imports from orchestrator
- [ ] Remove checkpoint logic from orchestrator
- [ ] Update phase dispatcher
- [ ] Commit: "refactor: Remove failed Phase 7.5 implementation"

### Day 2: Implement Core Method

- [ ] Add `_run_phase_7_5_agent_enhancement_simple` method
- [ ] Add error types (`ErrorCategory`, `EnhancementError`)
- [ ] Add result aggregation logic
- [ ] Add error summary logging
- [ ] Commit: "feat: Add simplified Phase 7.5 implementation"

### Day 3: Implement Helper Methods

- [ ] Add `_build_enhancement_prompt` method
- [ ] Add `_format_template_list` helper
- [ ] Add `_validate_enhancement` method
- [ ] Add `_apply_enhancement` method
- [ ] Commit: "feat: Add Phase 7.5 helper methods"

### Day 4: Write Tests

- [ ] Write 8 unit tests
- [ ] Write 3 integration tests
- [ ] Verify ≥85% coverage
- [ ] All tests passing
- [ ] Commit: "test: Add comprehensive tests for Phase 7.5"

### Day 5: Documentation & Integration

- [ ] Update method docstrings
- [ ] Update CLAUDE.md (remove bridge references)
- [ ] Test on existing reference template
- [ ] Verify quality maintained (9+/10)
- [ ] Commit: "docs: Update Phase 7.5 documentation"

### Post-Implementation

- [ ] Deploy to production
- [ ] Monitor success rate
- [ ] Collect user feedback
- [ ] Iterate on prompt if needed

---

## Dependencies

### Required Before Starting

- ✅ Architectural review complete (TASK-09E9)
- ✅ Path forward documented
- ✅ This specification reviewed and approved

### Blocking Dependencies

- None (can start immediately)

### Dependent Tasks

- **TASK-PHASE-8-INCREMENTAL**: Incremental workflow (optional, based on feedback)
- **TASK-ORCHESTRATOR-SIMPLIFY**: Remove agent bridge from all phases (optional, future)

---

## Related Documents

- [TASK-09E9 Architectural Review](../reviews/TASK-09E9-phase-7-5-architectural-review.md) - Why Phase 7.5 failed
- [Template-Create Path Forward](../reviews/template-create-path-forward.md) - Strategic direction
- [Phase 7.5 Replacement Architectural Review](../reviews/phase-7-5-replacement-architectural-review.md) - Design specs

---

**Document Status**: READY FOR IMPLEMENTATION
**Last Updated**: 2025-11-20
**Estimated Start Date**: Immediate
**Estimated Completion**: 3-5 days from start

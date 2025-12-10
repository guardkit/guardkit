# TASK-51B2: Revert to AI-Native Template Creation

**Created**: 2025-01-12
**Priority**: High
**Type**: Refactor
**Status**: backlog
**Complexity**: 6/10 (Medium)
**Estimated Effort**: 3-5 hours
**Reference**: [Architectural Review](../../docs/research/template-create-architectural-review.md)

---

## Problem Statement

Between November 2024 (TASK-042, 058, 059) and January 2025 (TASK-9038/9039), we diverged from an AI-native template generation approach and over-engineered a Python-based detection system.

**Current Issues**:
- 1,045 LOC of pattern-matching code that duplicates AI capabilities
- Q&A session creates friction and breaks in CI/CD
- Detection code requires maintenance for every new framework
- Violates core principle: "AI does heavy lifting, humans make decisions"

**Goal**: Remove detector code, eliminate Q&A, and let AI analyze codebases directly.

---

## Context

### The Original Vision (TASK-042, 058, 059)

AI-native template creation worked like this:
1. AI reads codebase files directly
2. AI understands language (sees `.py`, `.ts`, `.cs` files)
3. AI understands framework (reads `package.json`, `requirements.txt`)
4. AI understands architecture (analyzes folder structure)
5. AI generates template artifacts (manifest, settings, CLAUDE.md, templates, agents)

**No Q&A. No detector code. Just AI analysis.**

### What Went Wrong (TASK-9038/9039)

Built unnecessary infrastructure:
- `smart_defaults_detector.py` (531 LOC) - pattern matching for languages/frameworks
- `test_smart_defaults_detector.py` (514 LOC) - tests for detector
- Modified orchestrator to use detector instead of Q&A
- Created `/template-qa` command as workaround

**The fundamental mistake**: Built code to help AI understand code, when AI is designed to understand code naturally.

### Reference Commit

Commit `eb2e94c64d470da5eea9dddd932fd3d92685df8b` represents the last "good" state before the over-engineering began.

---

## Objectives

### Primary Objective
Revert to AI-native template creation by removing detector code and Q&A session, letting AI analyze codebases directly.

### Success Criteria
- [ ] Detector code deleted (`smart_defaults_detector.py` + tests = 1,045 LOC)
- [ ] Phase 1 Q&A removed from orchestrator
- [ ] AI analysis phase receives `codebase_path` directly (no Q&A answers)
- [ ] `/template-create` works without any user interaction
- [ ] AI infers language, framework, architecture from codebase analysis
- [ ] All existing tests pass (excluding deleted detector tests)
- [ ] Integration test: Generate template from sample projects (React, FastAPI, Next.js)
- [ ] Command interface simplified (remove `--skip-qa` flag - now default behavior)
- [ ] Documentation updated to reflect AI-native approach

---

## Implementation Plan

### Step 1: Delete Detector Code

**Files to Delete**:
```bash
# Detector implementation
installer/core/commands/lib/smart_defaults_detector.py  # 531 LOC

# Detector tests
tests/unit/test_smart_defaults_detector.py  # 514 LOC

# Total: 1,045 LOC removed
```

**Verification**:
```bash
# Ensure no imports remain
grep -r "smart_defaults_detector" installer/ tests/
# Should return no results
```

### Step 2: Remove Phase 1 Q&A from Orchestrator

**File**: `installer/core/commands/lib/template_create_orchestrator.py`

**Changes**:

1. **Remove imports** (lines ~17):
   ```python
   # DELETE THIS:
   from installer.core.commands.lib.template_qa_session import TemplateQASession
   ```

2. **Remove Q&A from config** (lines ~68):
   ```python
   # DELETE THIS:
   skip_qa: bool = False  # DEPRECATED
   ```

3. **Remove Phase 1 method** (lines ~350-390):
   ```python
   # DELETE ENTIRE METHOD:
   def _phase1_configuration_resolution(self) -> Optional[Dict[str, Any]]:
       """Phase 1: Configuration Resolution..."""
   ```

4. **Remove old Q&A method** if it still exists:
   ```python
   # DELETE ENTIRE METHOD:
   def _phase1_qa_session(self) -> Optional[Dict[str, Any]]:
       """Phase 1: Run Q&A session..."""
   ```

### Step 3: Simplify Orchestrator Run Method

**File**: `installer/core/commands/lib/template_create_orchestrator.py`

**Current flow** (lines ~160-180):
```python
def run(self) -> OrchestrationResult:
    # Phase 1: Configuration Resolution (with detector)
    qa_answers = self._phase1_configuration_resolution()
    if not qa_answers:
        return self._create_error_result("Configuration resolution failed")

    # Phase 2: AI Analysis (receives Q&A answers)
    analysis = self._phase2_ai_analysis(qa_answers)
```

**New flow** (AI-native):
```python
def run(self) -> OrchestrationResult:
    """Execute AI-native template creation workflow"""
    try:
        self._print_header()

        # Get codebase path
        codebase_path = self.config.codebase_path or Path.cwd()
        if not codebase_path.exists():
            return self._create_error_result(f"Codebase path does not exist: {codebase_path}")

        # Phase 1: AI analyzes codebase directly
        self._print_phase_header("Phase 1: AI Codebase Analysis")
        analysis = self._phase1_ai_analysis(codebase_path)
        if not analysis:
            return self._create_error_result("AI analysis failed")

        # Save analysis if requested
        if self.config.save_analysis:
            self._save_analysis_json(analysis)

        # Phase 2: Manifest Generation (from AI analysis)
        manifest = self._phase2_manifest_generation(analysis)
        if not manifest:
            return self._create_error_result("Manifest generation failed")

        # Phase 3: Settings Generation
        settings = self._phase3_settings_generation(analysis)
        if not settings:
            return self._create_error_result("Settings generation failed")

        # Phase 4: Template File Generation
        templates = self._phase4_template_generation(analysis)
        if not templates:
            self.warnings.append("No template files generated")

        # Phase 4.5: Completeness Validation (if enabled)
        if not self.config.skip_validation and templates:
            templates = self._phase4_5_completeness_validation(templates, analysis)

        # Phase 5: Agent Recommendation
        agents = []
        if not self.config.no_agents:
            agents = self._phase5_agent_recommendation(analysis)

        # Phase 6: CLAUDE.md Generation (agents exist now)
        claude_md = self._phase6_claude_md_generation(analysis, agents)
        if not claude_md:
            return self._create_error_result("CLAUDE.md generation failed")

        # Phase 7: Package Assembly
        if self.config.dry_run:
            self._print_dry_run_summary(manifest, settings, templates, agents)
            return self._create_dry_run_result(manifest, len(templates.templates if templates else []), len(agents))

        output_path = self._phase7_package_assembly(
            manifest=manifest,
            settings=settings,
            claude_md=claude_md,
            templates=templates,
            agents=agents
        )

        if not output_path:
            return self._create_error_result("Package assembly failed")

        # Phase 7.5: Extended Validation (if enabled)
        validation_report_path = None
        exit_code = 0
        if self.config.validate and templates:
            validation_report_path, exit_code = self._phase7_5_extended_validation(
                templates=templates,
                manifest=manifest,
                settings=settings,
                claude_md_path=output_path / "CLAUDE.md",
                agents=agents,
                output_path=output_path
            )

        # Success!
        location_type = "personal" if self.config.output_location == 'global' else "distribution"
        self._print_success(output_path, manifest, templates, agents, location_type, validation_report_path)

        return OrchestrationResult(
            success=True,
            template_name=manifest.name,
            output_path=output_path,
            manifest_path=output_path / "manifest.json",
            settings_path=output_path / "settings.json",
            claude_md_path=output_path / "CLAUDE.md",
            template_count=len(templates.templates) if templates else 0,
            agent_count=len(agents),
            confidence_score=manifest.confidence_score,
            errors=self.errors,
            warnings=self.warnings,
            validation_report_path=validation_report_path,
            exit_code=exit_code
        )

    except Exception as e:
        self._print_error(f"Template creation failed: {e}")
        logger.exception("Orchestration error")
        return self._create_error_result(str(e))
```

### Step 4: Rename and Enhance AI Analysis Phase

**Create new method**: `_phase1_ai_analysis(codebase_path: Path) -> Optional[Any]`

This method should:
1. Receive codebase path directly (no Q&A answers)
2. Invoke AI agent to analyze codebase
3. AI returns structured analysis with inferred metadata:
   - Language (from file extensions, config files)
   - Framework (from dependencies)
   - Architecture (from folder structure)
   - Patterns (from code analysis)
   - Testing framework (from test files)
   - Template name (suggested from project)

**Enhanced AI prompt** (in codebase analyzer):
```markdown
You are analyzing a codebase to generate a Taskwright template.

**Your Task**:
Analyze the codebase at {codebase_path} and infer ALL template metadata.

**What to Detect**:
1. **Language**: Analyze file extensions (.py, .ts, .cs, .go, .rs)
   - Look for: setup.py, pyproject.toml, package.json, tsconfig.json, *.csproj, go.mod, Cargo.toml

2. **Framework**: Analyze dependencies and imports
   - Python: Read requirements.txt, pyproject.toml, Pipfile
   - TypeScript: Read package.json dependencies
   - .NET: Read *.csproj PackageReference
   - Go: Read go.mod
   - Common frameworks: FastAPI, Flask, Django, React, Next.js, Vue, Angular, ASP.NET

3. **Architecture**: Analyze folder structure
   - Look for patterns: api/, models/, services/, controllers/, views/, components/
   - Identify: Layered, MVC, MVVM, Clean Architecture, Hexagonal, Microservices

4. **Testing**: Analyze test files
   - Python: pytest, unittest
   - TypeScript: Jest, Vitest, Mocha
   - .NET: xUnit, NUnit, MSTest

5. **Template Name**: Suggest based on language + framework
   - Examples: "fastapi-python", "react-typescript", "nextjs-fullstack"

**Output Format** (JSON):
{
  "primary_language": "Python",
  "framework": "FastAPI",
  "framework_version": "0.104.0",
  "architecture_pattern": "Layered (API routes + CRUD + models)",
  "testing_framework": "pytest",
  "template_name": "fastapi-python",
  "template_type": "Backend API",
  "confidence_score": 95,
  "analysis": {
    "file_count": 42,
    "primary_patterns": ["REST API", "Dependency Injection", "Pydantic validation"],
    "folder_structure": ["api/", "crud/", "models/", "schemas/", "tests/"],
    "key_dependencies": ["fastapi", "sqlalchemy", "pydantic"],
    "suggested_agents": ["fastapi-specialist", "database-specialist", "testing-specialist"]
  }
}

**CRITICAL**: Infer everything from the codebase itself. Do not ask questions. Do not use external detection code.
```

### Step 5: Remove Q&A Dependencies

**Check for remaining Q&A references**:
```bash
grep -r "TemplateQASession" installer/ tests/
grep -r "qa_session" installer/ tests/
grep -r "skip_qa" installer/ tests/
```

**Files to update**:
- `installer/core/commands/template-create.md` - Remove `--skip-qa` flag documentation
- `installer/core/commands/lib/template_create_cli.py` - Remove `--skip-qa` argument parser

### Step 6: Simplify Command Interface

**File**: `installer/core/commands/template-create.md`

**Current usage**:
```bash
/template-create --skip-qa --validate --output-location=repo
```

**New usage** (simplified):
```bash
/template-create --validate --output-location=repo

# Even simpler (uses defaults):
/template-create
```

**Remove from documentation**:
- `--skip-qa` flag (now default behavior)
- Q&A session description
- All references to interactive mode

**Add to documentation**:
- AI-native analysis description
- How AI infers metadata
- Examples of what AI detects

### Step 7: Update Tests

**Integration test** (new file: `tests/integration/test_ai_native_template_creation.py`):
```python
"""
Integration test for AI-native template creation.

Tests that /template-create works without Q&A or detector code.
"""
import pytest
from pathlib import Path
from installer.core.commands.lib.template_create_orchestrator import (
    TemplateCreateOrchestrator,
    OrchestrationConfig
)

def test_ai_native_react_typescript(tmp_path):
    """Test AI-native template creation for React TypeScript project"""
    # Create sample React project structure
    project_path = tmp_path / "sample-react"
    project_path.mkdir()

    # package.json
    (project_path / "package.json").write_text('''{
      "dependencies": {
        "react": "^18.2.0",
        "@types/react": "^18.0.0"
      }
    }''')

    # tsconfig.json
    (project_path / "tsconfig.json").write_text('{}')

    # src/ structure
    (project_path / "src").mkdir()
    (project_path / "src" / "components").mkdir()
    (project_path / "src" / "components" / "Button.tsx").write_text(
        'export function Button() { return <button>Click</button>; }'
    )

    # Configure orchestrator (no Q&A, no detector)
    config = OrchestrationConfig(
        codebase_path=project_path,
        output_location='global',
        dry_run=False
    )

    orchestrator = TemplateCreateOrchestrator(config)
    result = orchestrator.run()

    # Verify success
    assert result.success
    assert result.template_name.startswith("react")
    assert "typescript" in result.template_name.lower()
    assert result.template_count > 0
    assert result.agent_count > 0

def test_ai_native_fastapi_python(tmp_path):
    """Test AI-native template creation for FastAPI project"""
    # Similar test for FastAPI...
    pass

def test_ai_native_nextjs_fullstack(tmp_path):
    """Test AI-native template creation for Next.js project"""
    # Similar test for Next.js...
    pass
```

**Update existing tests**:
- Remove detector-related imports
- Remove Q&A session mocks
- Focus on end-to-end behavior

### Step 8: Update Documentation

**Files to update**:

1. **CLAUDE.md** (project root):
   - Remove references to Q&A session
   - Add AI-native template creation explanation
   - Update command examples

2. **installer/core/commands/template-create.md**:
   - Remove `--skip-qa` flag
   - Add "AI-Native Analysis" section
   - Update usage examples

3. **docs/guides/template-philosophy.md**:
   - Add section on AI-native approach
   - Explain why detector code was removed

4. **docs/research/template-create-architectural-review.md** (already exists):
   - Reference this task as the implementation

---

## Acceptance Criteria

### Functional Requirements
- [ ] All detector code deleted (1,045 LOC removed)
- [ ] Phase 1 Q&A removed from orchestrator
- [ ] AI analysis receives `codebase_path` directly (no Q&A answers)
- [ ] `/template-create` generates templates without user interaction
- [ ] Command works in CI/CD environments (no hanging)
- [ ] Integration tests pass for React, FastAPI, Next.js projects

### Quality Requirements
- [ ] All existing tests pass (excluding deleted detector tests)
- [ ] No references to `smart_defaults_detector` remain
- [ ] No references to `TemplateQASession` in orchestrator
- [ ] Code compiles without errors
- [ ] Test coverage maintained (excluding deleted detector tests)

### Documentation Requirements
- [ ] CLAUDE.md updated to reflect AI-native approach
- [ ] Command specification updated (remove `--skip-qa`)
- [ ] Template philosophy guide updated
- [ ] Architectural review document linked

---

## Testing Requirements

### Unit Tests
```bash
# All existing tests should pass (excluding detector tests)
pytest tests/unit/ -v --ignore=tests/unit/test_smart_defaults_detector.py

# Expected: 100% pass rate
```

### Integration Tests
```bash
# New AI-native integration tests
pytest tests/integration/test_ai_native_template_creation.py -v

# Test actual template generation from sample projects
# Expected: Templates generated successfully for React, FastAPI, Next.js
```

### Manual Testing
```bash
# Test 1: React TypeScript project
cd /tmp/sample-react-project
/template-create --validate
# Expected: Template created, language=TypeScript, framework=React

# Test 2: FastAPI Python project
cd /tmp/sample-fastapi-project
/template-create --validate
# Expected: Template created, language=Python, framework=FastAPI

# Test 3: Next.js full-stack project
cd /tmp/sample-nextjs-project
/template-create --validate
# Expected: Template created, language=TypeScript, framework=Next.js

# Test 4: CI/CD environment (non-interactive)
cd /tmp/sample-project
TERM=dumb /template-create --output-location=repo
# Expected: No hanging, template created successfully
```

---

## Risk Mitigation

### Risk 1: AI Inference Less Reliable Than Detector

**Likelihood**: Low
**Impact**: Medium

**Mitigation**:
- Enhanced AI prompt with specific detection instructions
- Confidence score in analysis output
- Fallback to sensible defaults if confidence <50%
- Integration tests verify accuracy

**Contingency**:
- If AI fails to detect correctly, user can provide explicit config file:
  ```bash
  /template-create --config=template-config.json
  ```

### Risk 2: Breaking Existing Templates

**Likelihood**: Low
**Impact**: High

**Mitigation**:
- Existing templates in `installer/core/templates/` are not affected
- Only creation process changes, not template format
- Integration tests verify template generation works

**Contingency**:
- Revert to commit `eb2e94c` if critical issues found
- Gradual rollout with feature flag

### Risk 3: Test Coverage Drops

**Likelihood**: Medium
**Impact**: Low

**Mitigation**:
- Remove only detector tests (514 LOC)
- Add new integration tests for AI-native flow
- Maintain coverage for orchestrator, manifest, settings, etc.

**Contingency**:
- Write additional unit tests for AI analysis phase if needed

---

## Implementation Notes

### Phase Renumbering

After removing Phase 1 Q&A, renumber phases:

**Current**:
- Phase 1: Q&A Session (DELETE)
- Phase 2: AI Analysis
- Phase 3: Manifest Generation
- Phase 4: Settings Generation
- Phase 5: Template Generation
- Phase 6: Agent Recommendation
- Phase 7: CLAUDE.md Generation
- Phase 8: Package Assembly

**New**:
- Phase 1: AI Codebase Analysis (was Phase 2)
- Phase 2: Manifest Generation (was Phase 3)
- Phase 3: Settings Generation (was Phase 4)
- Phase 4: Template Generation (was Phase 5)
- Phase 4.5: Completeness Validation (was Phase 5.5)
- Phase 5: Agent Recommendation (was Phase 6)
- Phase 6: CLAUDE.md Generation (was Phase 7)
- Phase 7: Package Assembly (was Phase 8)
- Phase 7.5: Extended Validation (was Phase 5.7)

### Codebase Analyzer Enhancement

The `CodebaseAnalyzer` (in `installer/core/lib/codebase_analyzer/ai_analyzer.py`) already exists. Enhance it to:
1. Accept `codebase_path` directly (no Q&A answers)
2. Return structured analysis with inferred metadata
3. Use enhanced AI prompt for detection

### Configuration File Support (Optional)

For edge cases where AI inference fails, support explicit config:
```bash
/template-create --config=.templaterc.json
```

**Example `.templaterc.json`**:
```json
{
  "template_name": "my-custom-template",
  "primary_language": "Python",
  "framework": "FastAPI",
  "architecture_pattern": "Clean Architecture",
  "testing_framework": "pytest"
}
```

This provides override capability without requiring Q&A.

---

## Success Metrics

**Quantitative**:
- LOC removed: 1,045 (detector + tests)
- Command complexity reduced: No `--skip-qa` flag needed
- Test pass rate: 100% (excluding deleted detector tests)
- Integration test coverage: 3 major stacks (React, FastAPI, Next.js)
- CI/CD success: No hanging in non-interactive environments

**Qualitative**:
- Simpler workflow: `/template-create` just works
- Aligns with philosophy: "AI does heavy lifting"
- Maintainable: No framework detection code to update
- Flexible: AI learns new frameworks from training data

---

## Related Tasks

**Prerequisites**:
- None (can start immediately)

**Blockers**:
- TASK-9039B: Integration work (no longer needed - can close)

**Related**:
- TASK-042: Enhanced AI Prompting (original AI-native approach)
- TASK-058: Create FastAPI Template (used AI-native flow)
- TASK-059: Create Next.js Template (used `--skip-qa` successfully)
- TASK-9038: Create Q&A command (over-engineered, being reverted)
- TASK-9039: Remove Q&A (incomplete, being replaced by this task)

**Follow-up** (optional):
- TASK-9041: Add explicit config file support (`.templaterc.json`)
- TASK-9042: Enhance AI analysis with pattern detection examples

---

## References

- [Architectural Review](../../docs/research/template-create-architectural-review.md)
- [Template Philosophy](../../docs/guides/template-philosophy.md)
- [TASK-042: Enhanced AI Prompting](../../tasks/completed/TASK-042-implement-enhanced-ai-prompting.md)
- [TASK-058: FastAPI Template](../../tasks/completed/TASK-058/TASK-058.md)
- [TASK-059: Next.js Template](../../tasks/completed/TASK-059/TASK-059-create-nextjs-reference-template.md)
- Commit `eb2e94c64d470da5eea9dddd932fd3d92685df8b` (last good state)

---

**Document Status**: Ready for Implementation
**Created**: 2025-01-12
**Priority**: High
**Estimated Effort**: 3-5 hours
**Complexity**: 6/10 (Medium - significant refactor but clear path)

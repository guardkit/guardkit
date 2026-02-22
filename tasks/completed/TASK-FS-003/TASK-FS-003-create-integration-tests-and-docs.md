---
id: TASK-FS-003
title: "Create integration tests and user documentation"
status: completed
completed: 2026-02-22T12:35:00Z
task_type: testing
parent_review: TASK-REV-F445
feature_id: FEAT-FS01
created: 2026-02-22T12:00:00Z
updated: 2026-02-22T12:00:00Z
priority: high
tags: [feature-spec, testing, integration, documentation, e2e, multi-language]
complexity: 4
wave: 2
implementation_mode: task-work
dependencies:
  - TASK-FS-001
  - TASK-FS-002
test_results:
  status: passed
  tests_total: 47
  tests_passed: 47
  tests_failed: 0
  coverage: null
  last_run: 2026-02-22T12:30:00Z
---

# Task: Create integration tests and user documentation

## Description

Create end-to-end tests proving the `/feature-spec` pipeline works across stacks, and user-facing documentation explaining the command, methodology, and output format.

## Files to Create

1. `tests/integration/test_feature_spec_e2e.py` (new)
2. `docs/commands/feature-spec.md` (new)

## Files NOT to Touch

- Any source files in `guardkit/` (read-only access for understanding patterns)
- Any existing test files
- Any existing documentation files

## Integration Test Specification

### Test Fixtures

Use temporary directories with minimal fake codebases for each stack:

```python
@pytest.fixture
def python_project(tmp_path):
    """Fake Python project with pyproject.toml."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("# app module\n")
    return tmp_path

@pytest.fixture
def typescript_project(tmp_path):
    """Fake TypeScript project with package.json only."""
    (tmp_path / "package.json").write_text('{"name": "test"}\n')
    return tmp_path

@pytest.fixture
def polyglot_project(tmp_path):
    """Fake polyglot project with both pyproject.toml and package.json."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
    (tmp_path / "package.json").write_text('{"name": "test"}\n')
    return tmp_path

@pytest.fixture
def go_project(tmp_path):
    """Fake Go project with go.mod."""
    (tmp_path / "go.mod").write_text("module example.com/test\n")
    return tmp_path

@pytest.fixture
def generic_project(tmp_path):
    """Project with no detectable stack."""
    (tmp_path / "README.md").write_text("# Project\n")
    return tmp_path
```

### Required Test Scenarios

1. **Stack detection priority**:
   - Python project (`pyproject.toml` only) -> stack = "python"
   - Polyglot project (`pyproject.toml` + `package.json`) -> stack = "python" (Python wins)
   - TypeScript project (`package.json` only, no Python signals) -> stack = "typescript"
   - Go project (`go.mod`) -> stack = "go"
   - No signals -> stack = "generic"

2. **File output**:
   - `write_outputs()` creates correct directory structure
   - `.feature` file is valid UTF-8
   - `_assumptions.yaml` is valid YAML (parse with `yaml.safe_load()`)
   - `_summary.md` contains expected sections (scenario coverage, assumptions, components)

3. **Gherkin quality** (domain language check):
   - Generated scenarios use domain language ("upload should succeed")
   - NOT implementation-specific terms ("return 201", "INSERT INTO")

4. **Graphiti seeding**:
   - `seed_to_graphiti()` does not raise when Graphiti unavailable
   - Seeds individual scenarios (test mock verifies multiple `add_episode` calls)

5. **Input handling**:
   - Multiple `--from` inputs concatenated correctly
   - Empty input handled gracefully (error message, not crash)

### Test Conventions

Follow existing integration test patterns:
- Module docstring with coverage target
- Class-based test organisation
- `@pytest.mark.integration` marker
- Descriptive test names and docstrings

## Documentation Specification

### Required Sections for `docs/commands/feature-spec.md`

1. **Purpose** -- what the command does and why
2. **The Propose-Review Methodology** -- the 6-phase cycle explained for users
3. **Usage Examples** -- at least 5 examples showing different input modes
4. **Flag Descriptions** -- table of all flags with defaults
5. **Output Format** -- what files are created and their structure
6. **Multi-Stack Support** -- which stacks are detected and how
7. **Assumptions Manifest Format** -- YAML schema with example
8. **Worked Example** -- full input -> output showing the propose-review cycle
9. **Migration from /generate-bdd** -- notes for users coming from the deprecated command
10. **Integration with /feature-plan** -- how the summary feeds into task decomposition

### Documentation size target: > 2000 bytes

## Acceptance Criteria

- [ ] File exists: `tests/integration/test_feature_spec_e2e.py`
- [ ] E2E test: Python stack detection correct
- [ ] E2E test: Polyglot detection (Python wins over TypeScript)
- [ ] E2E test: TypeScript-only detection
- [ ] E2E test: Generic/unknown stack -> Gherkin only
- [ ] E2E test: output files created with correct structure and valid content
- [ ] E2E test: assumptions YAML is valid
- [ ] E2E test: Graphiti seeding non-blocking on unavailable connection
- [ ] File exists: `docs/commands/feature-spec.md`
- [ ] Documentation includes: purpose, methodology, usage examples, flags, output format, multi-stack support, assumptions format, worked examples
- [ ] Documentation size > 2000 bytes
- [ ] Tests pass: `pytest tests/integration/test_feature_spec_e2e.py -v`

## Coach Validation Commands

```bash
pytest tests/integration/test_feature_spec_e2e.py -v
python -c "
import os
size = os.path.getsize('docs/commands/feature-spec.md')
assert size > 2000, f'Documentation too short ({size} bytes)'
print(f'Docs OK: {size} bytes')
"
```

## Player Constraints

- Do not modify any source files -- read-only access to `guardkit/` for understanding patterns
- Do not modify any existing test files
- Do not modify any existing documentation

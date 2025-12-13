# Feature: Self-Template Enhancement

## Problem Statement

**REVISED**: Investigation revealed GuardKit is a **Python library/CLI tool**, NOT a FastAPI application.

### GuardKit's Actual Python Code
- **575 Python files** total
- **Core libraries** in `installer/core/lib/` (137 files)
  - `id_generator.py` - Hash-based task IDs with SHA-256
  - `template_creation/` - Template manifest models, constants
  - `agent_enhancement/` - Agent orchestrator, parser, models
  - `template_validation/` - 16-section comprehensive audit
  - `codebase_analyzer/` - Stratified sampling, response parsing
  - `mcp/` - MCP client integration
- **Tests** in `tests/` (277 files) - pytest patterns
- **Uses**: Pydantic models, dataclasses, pathlib, typing, async patterns

### What Python Guidance Exists
- ❌ **No Python library specialist agent** (only FastAPI specialists in templates)
- ❌ **No CLI tool development patterns**
- ❌ **No rules structure** in GuardKit `.claude/`
- ✅ **Generic agents**: code-reviewer, test-orchestrator, debugging-specialist
- ✅ **Python stack config**: `.claude/stacks/python/config.json` (but FastAPI-focused)
- ✅ **Default template**: Language-agnostic rules (code-style, workflow, quality-gates)

### The Gap
GuardKit development uses patterns NOT covered by existing guidance:
1. **Python library patterns** (not API endpoints)
2. **Pydantic v2 models** for data validation
3. **Dataclasses** for internal state
4. **pytest fixtures** with complex mocking
5. **Module organization** for CLI tools
6. **Type hints** with strict mypy

## Solution Approach (REVISED)

Apply the **Hybrid Workflow** but focus on **library development patterns**:

1. **Wave 1**: Run dry-run analysis on GuardKit to understand what patterns it needs
2. **Wave 2**: Create Python library specialist guidance (NOT FastAPI enhancement)
3. **Wave 3**: Add GuardKit-specific rules structure
4. **Wave 4**: Validate with actual GuardKit development task

**FastAPI enhancement (TASK-STE-003/004/005) is deferred** - those templates are for users creating FastAPI apps, not for GuardKit development itself.

## Subtasks (REVISED)

| ID | Title | Mode | Wave | Status |
|----|-------|------|------|--------|
| TASK-STE-001 | Run template-create --dry-run on GuardKit | direct | 1 | pending |
| TASK-STE-002 | Analyze GuardKit Python patterns for guidance gaps | direct | 1 | pending |
| TASK-STE-003 | ~~Enhance fastapi-specialist~~ | ~~task-work~~ | ~~2~~ | **DEFERRED** |
| TASK-STE-004 | ~~Enhance fastapi-testing-specialist~~ | ~~task-work~~ | ~~2~~ | **DEFERRED** |
| TASK-STE-005 | ~~Enhance fastapi-database-specialist~~ | ~~task-work~~ | ~~2~~ | **DEFERRED** |
| TASK-STE-006 | ~~Add rules to fastapi-python~~ | ~~task-work~~ | ~~3~~ | **DEFERRED** |
| TASK-STE-007 | Add rules structure to GuardKit .claude/ | task-work | 2 | pending |
| TASK-STE-008 | Validate improvements with GuardKit dev task | task-work | 3 | pending |

### New Tasks (to be created)
| ID | Title | Mode | Wave | Status |
|----|-------|------|------|--------|
| TASK-STE-009 | Create python-library-specialist guidance | task-work | 2 | pending |
| TASK-STE-010 | Create pytest-patterns guidance for library testing | task-work | 2 | pending |

## Key Insight

**FastAPI templates are for USERS**, not for developing GuardKit itself.
- When a user creates a FastAPI app with `guardkit init fastapi-python`, they get FastAPI agents
- When WE develop GuardKit, we need **library development patterns** (Pydantic models, dataclasses, pytest mocking, module organization)

This is the critical distinction the original plan missed.

## Related Tasks

- TASK-REV-1DDD: Original review task (parent)
- TASK-REV-PD01: Progressive disclosure review
- TASK-TC-DEFAULT-FLAGS: Template create default flags

## Success Criteria (REVISED)

- [ ] Analysis complete for GuardKit's actual Python patterns
- [ ] Python library development guidance created
- [ ] pytest patterns guidance created
- [ ] Rules structure added to GuardKit .claude/
- [ ] Python library workflow validated with actual dev task
- [ ] (DEFERRED) FastAPI template enhancement (separate initiative)

# Review Report: TASK-CRS-014

## Agent-Enhance Command Rules Structure Support

**Review Mode**: Architectural
**Review Depth**: Standard
**Reviewer**: architectural-reviewer agent
**Date**: 2025-12-11
**Status**: COMPLETE

---

## Executive Summary

The `/agent-enhance` command requires **moderate modifications** to support the new Claude Code rules structure. The existing codebase has strong foundations with the `PathPatternInferrer` class already implemented for CRS-004, and the `RulesStructureGenerator` from CRS-002 handles agent rule file generation. The main work involves:

1. **Output path routing** - Switch between `agents/` and `rules/agents/` based on context
2. **Frontmatter generation** - Add `paths:` frontmatter to enhanced agents
3. **Template structure detection** - Auto-detect if template uses rules structure
4. **Progressive disclosure compatibility** - Ensure split files work in both modes

**Recommendation**: Implement as a single focused task (not split into subtasks) with complexity 4/10.

---

## Current State Analysis

### Current Agent-Enhance Behavior

| Aspect | Current Implementation |
|--------|----------------------|
| Output directory | `agents/` (hardcoded in path resolution) |
| Frontmatter | Discovery metadata only (`stack`, `phase`, `capabilities`, `keywords`) |
| Progressive disclosure | Creates `{agent}.md` + `{agent}-ext.md` in same directory |
| Path patterns | None in agent frontmatter |
| Template detection | None - always uses legacy structure |

### Key Files Analyzed

| File | Lines | Responsibility |
|------|-------|---------------|
| [agent-enhance.py](installer/core/commands/agent-enhance.py) | 365 | Command entry point, path resolution |
| [enhancer.py](installer/core/lib/agent_enhancement/enhancer.py) | ~250 | Core enhancement logic |
| [orchestrator.py](installer/core/lib/agent_enhancement/orchestrator.py) | ~420 | AI invocation coordination |
| [applier.py](installer/core/lib/agent_enhancement/applier.py) | ~700 | File writing, split logic |
| [rules_structure_generator.py](installer/core/lib/template_generator/rules_structure_generator.py) | 507 | Rules structure generation (CRS-002) |
| [path_pattern_inferrer.py](installer/core/lib/template_generator/path_pattern_inferrer.py) | 262 | Path pattern inference (CRS-004) |

---

## Required Changes

### 1. Output Path Routing

**Current**: `resolve_paths()` in `agent-enhance.py` always outputs to `agents/` directory.

**Required**: Add conditional logic based on:
- Explicit `--use-rules-structure` flag (override)
- Auto-detection of `rules/` directory in template

```python
# Proposed changes to resolve_paths()
def resolve_paths(agent_path_str: str, use_rules_structure: bool = None) -> Tuple[Path, Path]:
    # ... existing resolution logic ...

    # Determine output directory
    if use_rules_structure is None:
        # Auto-detect from template structure
        use_rules_structure = (template_dir / "rules").exists()

    if use_rules_structure:
        output_dir = template_dir / "rules" / "agents"
    else:
        output_dir = template_dir / "agents"

    return (agent_file, template_dir, output_dir)
```

**Impact**: Low - Single function modification

### 2. Paths Frontmatter Generation

**Current**: `applier.py` only writes discovery metadata (`stack`, `phase`, etc.)

**Required**: Add `paths:` frontmatter field using `PathPatternInferrer`.

```python
# Integration with PathPatternInferrer in applier.py
from installer.core.lib.template_generator.path_pattern_inferrer import PathPatternInferrer

def _generate_paths_frontmatter(agent_name: str, technologies: List[str], analysis: CodebaseAnalysis) -> str:
    inferrer = PathPatternInferrer(analysis)
    paths = inferrer.infer_for_agent(agent_name, technologies)
    return f"paths: {paths}" if paths else ""
```

**Integration point**: The `PathPatternInferrer` class from CRS-004 is already implemented and tested.

**Impact**: Medium - Requires coordination with CRS-004 and codebase analysis loading

### 3. Template Structure Detection

**Required**: Add utility function to detect if template uses rules structure.

```python
def uses_rules_structure(template_dir: Path) -> bool:
    """Detect if template uses rules structure based on directory presence."""
    rules_dir = template_dir / "rules"
    legacy_agents = template_dir / "agents"

    # Prefer rules structure if rules/ exists
    if rules_dir.exists():
        return True

    # Check for .claude/rules pattern
    claude_rules = template_dir / ".claude" / "rules"
    if claude_rules.exists():
        return True

    return False
```

**Impact**: Low - Simple directory check

### 4. Progressive Disclosure in Rules Structure

**Current**: Creates `agent.md` + `agent-ext.md` in same directory.

**Required**: Maintain same split behavior in `rules/agents/`:
- Core file: `rules/agents/{agent}.md` (with `paths:` frontmatter)
- Extended file: `rules/agents/{agent}-ext.md` (no `paths:` needed)

**Note**: Extended files don't need `paths:` frontmatter - they're loaded explicitly via the core file's "Extended Reference" link.

**Impact**: None - Existing split logic works unchanged

---

## Integration Points

### CRS-002: RulesStructureGenerator

The `RulesStructureGenerator.generate()` method already creates agent rules files:

```python
# rules_structure_generator.py:95-98
for agent in self.agents:
    agent_slug = self._slugify(agent.name)
    rules[f"rules/agents/{agent_slug}.md"] = self._generate_agent_rules(agent)
```

**Integration Strategy**:
- `/template-create --use-rules-structure` uses `RulesStructureGenerator` for initial agent stubs
- `/agent-enhance` enhances those stubs in-place with the same output path

### CRS-004: PathPatternInferrer

Already fully implemented with:
- Layer-based matching from architecture analysis
- Technology-specific patterns (FastAPI, React, etc.)
- Fallback to name-based heuristics

**Integration Strategy**:
- Import `PathPatternInferrer` in `agent-enhance.py` or `applier.py`
- Use `infer_for_agent()` method to generate `paths:` frontmatter

---

## Design Decisions

### Q1: Auto-detect vs explicit flag?

**Recommendation**: Auto-detect with flag override.

| Approach | Pros | Cons |
|----------|------|------|
| Auto-detect only | Zero friction | Can't force behavior |
| Flag only | Explicit control | Extra typing |
| **Auto-detect + flag** | Best of both | Minor complexity |

Implementation:
- Default: Auto-detect from `rules/` directory presence
- `--use-rules-structure`: Force rules output
- `--no-rules-structure`: Force legacy output

### Q2: Path pattern inference from agent metadata?

**Recommendation**: Use existing `PathPatternInferrer` with technology list from frontmatter.

```python
# In agent enhancement flow:
technologies = agent_metadata.get('technologies', [])
paths = inferrer.infer_for_agent(agent_name, technologies)
```

The `PathPatternInferrer` already handles:
- Technology-based patterns (e.g., `FastAPI` → `**/router*.py, **/api/**`)
- Layer-based patterns from codebase analysis
- Fallback to name-based heuristics

### Q3: Migrate existing `agents/` to `rules/agents/`?

**Recommendation**: No automatic migration. Keep as manual operation.

Reasons:
1. Migration changes template structure (breaking for users)
2. Templates may have custom agent content worth preserving
3. `/template-create --use-rules-structure` handles new templates
4. Existing templates (Wave 4 tasks) will be manually refactored

### Q4: Extended files in rules structure?

**Recommendation**: Same pattern as legacy (`{agent}-ext.md`), no `paths:` needed.

Rules:
- Core file (`agent.md`) has `paths:` for conditional loading
- Extended file (`agent-ext.md`) is explicitly loaded via core file link
- Both files live in `rules/agents/` when using rules structure

### Q5: Template validation interaction?

**Recommendation**: Add validation check for consistent agent locations.

- If `rules/agents/` exists, all agents should be there
- If `agents/` exists without `rules/`, use legacy structure
- Mixed state is a validation warning

---

## Architecture Scoring

| Principle | Score | Notes |
|-----------|-------|-------|
| **Single Responsibility** | 9/10 | Clear separation between detection, inference, and file writing |
| **Open/Closed** | 8/10 | PathPatternInferrer extensible via tech_patterns dict |
| **Liskov Substitution** | 9/10 | Output path abstraction works for both modes |
| **Interface Segregation** | 8/10 | Clean separation of concerns |
| **Dependency Inversion** | 7/10 | Direct import of PathPatternInferrer (acceptable for utility) |
| **DRY** | 8/10 | Reuses existing PathPatternInferrer, no duplication |
| **YAGNI** | 9/10 | Only adding what's needed for rules structure |

**Overall Score**: 82/100 (Solid architecture, minor integration work needed)

---

## Implementation Plan

### Recommended Approach: Single Implementation Task

Based on the analysis, this should be implemented as a **single task** (not split):
- Complexity: 4/10 (moderate)
- Estimated hours: 3-4 hours
- All changes are tightly coupled and test together

### Implementation Steps

1. **Add CLI flags** (30 min)
   - Add `--use-rules-structure` and `--no-rules-structure` flags
   - Update `resolve_paths()` to return output directory

2. **Add template detection** (30 min)
   - Implement `uses_rules_structure()` utility
   - Integrate into path resolution

3. **Add paths frontmatter generation** (1 hour)
   - Import `PathPatternInferrer`
   - Generate `paths:` in frontmatter during enhancement
   - Handle codebase analysis loading (may require lazy loading)

4. **Update applier for rules structure** (1 hour)
   - Ensure `apply_with_split()` works with `rules/agents/` output
   - Validate extended file placement

5. **Add tests** (1 hour)
   - Test auto-detection logic
   - Test paths frontmatter generation
   - Test progressive disclosure in rules structure

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| PathPatternInferrer coupling | Low | Medium | PathPatternInferrer is stable (CRS-004 complete) |
| Codebase analysis unavailable | Medium | Low | Fall back to name-based inference |
| Breaking existing templates | Low | High | Auto-detect preserves legacy behavior |
| Extended file path issues | Low | Low | Existing split logic handles paths correctly |

---

## Backward Compatibility

| Scenario | Behavior |
|----------|----------|
| Template with `agents/` only | Legacy behavior (auto-detect) |
| Template with `rules/agents/` | Rules structure (auto-detect) |
| `--use-rules-structure` flag | Force rules output |
| `--no-rules-structure` flag | Force legacy output |
| Mixed `agents/` + `rules/agents/` | Warning, prefer rules structure |

**No breaking changes to existing usage patterns.**

---

## Recommendations

### Primary Recommendation: Implement as Single Task

**Create implementation subtask**: TASK-CRS-014.1

**Scope**:
1. Add `--use-rules-structure` / `--no-rules-structure` flags
2. Implement template structure auto-detection
3. Integrate `PathPatternInferrer` for `paths:` frontmatter
4. Update path resolution for rules structure output
5. Add comprehensive tests

**Why single task**:
- All components are tightly coupled
- Changes test together (can't test detection without path changes)
- Total effort is 3-4 hours (appropriate for single task)
- No parallelization opportunity within this work

### Secondary Recommendations

1. **Document the behavior change** in `agent-enhance.md` command spec
2. **Add validation warning** for mixed `agents/` + `rules/agents/` templates
3. **Consider lazy loading** of `PathPatternInferrer` to avoid import overhead

---

## Appendix: Example Output

### Rules Structure Agent (Target State)

```markdown
---
paths: **/router*.py, **/api/**/*.py
stack: [python]
phase: implementation
capabilities:
  - FastAPI endpoint implementation
  - Async patterns with asyncio
keywords: [fastapi, api, async, pydantic]
---

# FastAPI Specialist

## Quick Start
...

## Boundaries
### ALWAYS
- ✅ Use async/await for all endpoints
...

## Extended Reference
For detailed examples, load:
\`\`\`bash
cat rules/agents/fastapi-specialist-ext.md
\`\`\`
```

### Directory Structure Comparison

**Legacy Structure**:
```
template/
├── agents/
│   ├── fastapi-specialist.md
│   └── fastapi-specialist-ext.md
└── CLAUDE.md
```

**Rules Structure**:
```
template/
├── .claude/
│   ├── CLAUDE.md
│   └── rules/
│       └── agents/
│           ├── fastapi-specialist.md      # Has paths: frontmatter
│           └── fastapi-specialist-ext.md  # No paths: (loaded explicitly)
```

---

## Decision Checkpoint

Review results:
- Architecture Score: 82/100
- Findings: 5 key areas analyzed
- Recommendations: 1 implementation subtask

**Options**:
- **[A]ccept** - Approve findings, no implementation needed
- **[R]evise** - Request deeper analysis on specific areas
- **[I]mplement** - Create implementation subtask (TASK-CRS-014.1)
- **[C]ancel** - Discard review

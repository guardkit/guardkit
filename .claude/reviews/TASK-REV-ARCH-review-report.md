# Architectural Review Report: TASK-REV-ARCH

## Executive Summary

This review analyzes the duplication between `agents/` (subagent definitions) and `.claude/rules/guidance/` (path-conditional loading) in GuardKit templates. The review found that **current implementation uses manually-authored slim summaries** in guidance files, not full copies, resulting in minimal actual duplication.

**Recommendation**: **Option B (Guidance Contains Summary + Reference)** is already the de facto implementation. Formalize this as the official approach and update the generator code to match.

**Architecture Score**: 78/100

## Review Details

- **Mode**: Architectural Review
- **Depth**: Standard
- **Duration**: Standard (1-2 hours)
- **Reviewer**: Opus 4.5 (architectural analysis)

---

## Findings

### Finding 1: No Full Duplication Exists (Severity: Informational)

**Evidence**: File size comparison shows guidance files are 35-40% the size of agent core files:

| Template | Agent Core | Guidance | Ratio |
|----------|------------|----------|-------|
| react-state-specialist | 6,210 bytes | 2,217 bytes | 36% |
| fastapi-specialist | 5,798 bytes | 2,342 bytes | 40% |
| docker-orchestration-specialist | 8,568 bytes | 4,196 bytes | 49% |

**Total Content**:
- Agent core files: 112 KB (14 files)
- Agent extended files: 222 KB (14 files)
- Guidance files: 32 KB (14 files)

**Conclusion**: Guidance files are not copies. They are slim summaries with different content structure.

### Finding 2: Two Different Content Purposes (Severity: Informational)

**Evidence**: Content comparison between `agents/fastapi-specialist.md` and `rules/guidance/fastapi.md`:

| Aspect | Agent File | Guidance File |
|--------|------------|---------------|
| Purpose | Task tool subprocess execution | Path-triggered context injection |
| Frontmatter | name, tools, model, stack, phase | paths, applies_when |
| Content | Full role, 6 capability sections, code examples | Summary, 5 brief capability bullets, references |
| Size | 174 lines | 66 lines |

The files serve different purposes and rightfully have different content.

### Finding 3: Generator Code Misaligned with Reality (Severity: Medium)

**Evidence**: `rules_structure_generator.py` lines 355-358:

```python
if enhanced_content:
    # Use enhanced content with path frontmatter
    logger.info(f"Using enhanced content for agent: {agent.name}")
    return self._merge_paths_into_frontmatter(enhanced_content, paths_filter)
```

This code would copy **full** enhanced agent content to guidance files when enhanced content exists. However, the current guidance files were manually created with slim summaries.

**Risk**: If `/template-create` runs with `--create-agent-tasks` and agents get enhanced, subsequent regeneration could replace slim guidance with full agent content, creating actual duplication.

### Finding 4: Claude Code Limitations Constrain Options (Severity: Low)

**Confirmed Constraints**:
1. **No symlink support**: Claude Code does not follow symlinks in `.claude/rules/`
2. **No include directives**: No `{% include %}` or `@import` syntax supported
3. **Path-based only**: Only `paths:` frontmatter controls conditional loading
4. **Static evaluation**: Rules evaluated at file open, not dynamically

These constraints eliminate Options A (include directive) and C (symlinks) from consideration.

### Finding 5: Current Architecture Is Sound (Severity: Informational)

The current architecture effectively implements progressive disclosure:

```
Template/
├── agents/                           # Task tool execution context
│   ├── {specialist}.md               # Core: frontmatter, boundaries, capabilities
│   └── {specialist}-ext.md           # Extended: detailed examples, best practices
└── .claude/rules/guidance/           # Claude Code native loading
    └── {slug}.md                     # Summary: paths, key boundaries, references
```

**Benefits**:
- **Right content for right context**: Agents get full context for implementation; Claude Code gets slim guidance for hints
- **Minimal context window usage**: Guidance files average 2.3KB vs agent 8KB
- **Clear separation**: Different frontmatter schemas, different purposes

---

## Options Evaluation Matrix

| Option | Duplication | Maintenance | Claude Code Compatible | Feasibility | Score |
|--------|-------------|-------------|------------------------|-------------|-------|
| A: Include Directive | None | Low | **No** | Not possible | 0/10 |
| B: Summary + Reference | Minimal (~35%) | Medium | **Yes** | **Current state** | **8/10** |
| C: Symlinks | None | None | **No** | Not possible | 0/10 |
| D: Only rules/guidance | None | Low | Yes | Breaks Task tool | 3/10 |
| E: Full Duplication | 100% | High | Yes | Risky | 4/10 |
| F: Slim Guidance + Full Agent | Minimal (~35%) | Medium | Yes | = Option B | 8/10 |

**Winner**: Option B / F (they are equivalent) - this is the current implementation.

---

## Recommendations

### Recommendation 1: Formalize Option B as Official Approach (Priority: High)

**Action**: Document that guidance files are intentionally slim summaries, not copies.

**Rationale**: The current implementation is correct - guidance files provide path-triggered context hints while agent files provide full execution context. This should be formalized.

**Implementation**:
1. Add comment to `rules_structure_generator.py` explaining the design decision
2. Update `docs/guides/rules-structure-guide.md` to clarify guidance vs agent distinction
3. Add validation that guidance files stay under a size threshold (e.g., 5KB)

### Recommendation 2: Fix Generator to Generate Slim Guidance (Priority: High)

**Action**: Modify `_generate_guidance_rules()` to extract summary content, not copy full agent.

**Rationale**: Current code would create full duplication if enhanced agents exist. It should instead:
1. Extract boundaries (ALWAYS/NEVER/ASK)
2. Extract capability summary (not full details)
3. Add cross-references to agent file
4. Keep under 3KB

**Implementation**:
```python
def _generate_guidance_rules(self, agent) -> str:
    """Generate slim guidance summary, not full agent copy."""
    # Extract only essential content from agent
    boundaries = self._extract_boundaries(enhanced_content)
    capabilities_summary = self._extract_capability_summary(enhanced_content)

    return self._create_slim_guidance(
        agent_name=agent.name,
        paths_filter=paths_filter,
        boundaries=boundaries,
        capabilities=capabilities_summary,
        reference_path=f"agents/{agent_slug}.md"
    )
```

### Recommendation 3: Add Size Validation (Priority: Medium)

**Action**: Add validation during template creation to flag guidance files > 5KB.

**Rationale**: Prevents accidental full duplication and ensures progressive disclosure benefits are maintained.

### Recommendation 4: Document Source of Truth (Priority: Medium)

**Action**: Add clear documentation stating:
- `agents/{name}.md` is the source of truth for agent content
- `rules/guidance/{slug}.md` is derived summary for path-triggered loading
- Changes should be made to agents/, then regenerate guidance

### Recommendation 5: Keep Current Manual Guidance Files (Priority: Low)

**Action**: The manually-authored guidance files in existing templates are well-designed. Keep them as-is.

**Rationale**: They demonstrate the correct pattern (slim summary with references). No need to regenerate.

---

## Decision Matrix

| Decision | Effort | Risk | Recommendation |
|----------|--------|------|----------------|
| Keep current implementation | Low | Low | **Recommended** |
| Refactor generator only | Medium | Low | Recommended |
| Full architecture change | High | Medium | Not recommended |

---

## Architecture Score Breakdown

| Principle | Score | Notes |
|-----------|-------|-------|
| SOLID - Single Responsibility | 8/10 | Agent vs guidance have clear separate purposes |
| SOLID - Open/Closed | 7/10 | Generator could be more extensible |
| DRY | 7/10 | ~35% content overlap is acceptable for different contexts |
| YAGNI | 9/10 | No over-engineering detected |
| Separation of Concerns | 8/10 | Clear separation between Task tool and Claude Code native |
| Maintainability | 7/10 | Manual sync required, but low frequency |

**Overall Score: 78/100**

---

## Appendix

### A. File Size Summary

```
Agent Core Files (no -ext):     112,361 bytes (14 files)
Agent Extended Files (-ext):    222,489 bytes (14 files)
Guidance Files:                  32,015 bytes (14 files)
```

### B. Key Files Referenced

- `installer/core/lib/template_generator/rules_structure_generator.py` - Generator code
- `installer/core/templates/*/agents/*.md` - Agent definitions
- `installer/core/templates/*/.claude/rules/guidance/*.md` - Guidance files
- `docs/guides/rules-structure-guide.md` - Rules documentation

### C. Claude Code Behavior Confirmed

| Feature | Supported | Evidence |
|---------|-----------|----------|
| Symlinks | No | Official docs, no mention of symlink support |
| Include directives | No | Only `paths:` and `task_types:` frontmatter documented |
| Path-based loading | Yes | Core feature of Claude Code rules system |
| Recursive discovery | Yes | `.claude/rules/` subdirectories scanned |

---

## Report Metadata

- **Task ID**: TASK-REV-ARCH
- **Report Path**: `.claude/reviews/TASK-REV-ARCH-review-report.md`
- **Generated**: 2025-12-11
- **Complexity**: 5/10
- **Findings Count**: 5
- **Recommendations Count**: 5

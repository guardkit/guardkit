# Review Report: TASK-REV-3666

## Executive Summary

The `/template-create --name mydrive` command completed successfully but bypassed progressive disclosure (split CLAUDE.md) due to a **missing CLI flag implementation**. The `--claude-md-size-limit` flag was documented and partially implemented but **never added to argparse**, causing the workaround `--no-split-claude-md` to be used instead.

**Key Finding**: This is a **bug** (incomplete implementation of TASK-ENH-SIZE-LIMIT), not intentional behavior based on existing agents.

## Review Details

| Field | Value |
|-------|-------|
| **Mode** | Decision Analysis |
| **Depth** | Standard |
| **Duration** | ~15 minutes |
| **Reviewer** | Claude Opus 4.5 |

---

## Root Cause Analysis

### Question 1: Why did progressive disclosure (split) fail?

**Answer**: The split failed because the generated core content was **34.68KB**, which exceeds the hard-coded **15KB limit** in `models.py`.

```
ERROR: Size validation failed: Core content exceeds 15KB limit: 34.68KB.
```

**Technical Details**:
- `validate_size_constraints()` in `models.py` has a hard-coded `warning_size = 15 * 1024` (15KB)
- Any content exceeding 15KB triggers a hard failure, regardless of `max_core_size` parameter
- The `max_core_size` parameter (default 10KB) only affects warnings, not failures

### Question 2: Why didn't `--claude-md-size-limit 50KB` work?

**Answer**: **BUG** - The flag was never added to argparse.

**Evidence**:
- TASK-ENH-SIZE-LIMIT marked as `completed` on 2025-12-10
- Config dataclass updated: `claude_md_size_limit: int = 10 * 1024`
- `parse_size_limit()` static method was added
- **BUT**: No `add_argument("--claude-md-size-limit", ...)` in the argparse section

**What was implemented**:
1. ✅ Config field `claude_md_size_limit` added
2. ✅ `parse_size_limit()` function added
3. ✅ Documentation mentions the flag
4. ✅ Error messages reference the flag
5. ❌ **argparse argument NOT added**
6. ❌ **Flag value never passed to run_template_create()**

### Question 3: Was `--no-split-claude-md` the right workaround?

**Answer**: **Yes**, given the bug, this was the correct workaround.

**Rationale**:
- The 48.4KB CLAUDE.md is usable (within context window limits)
- Template functionality is complete (20 template files, manifest, settings)
- All 8 required agents were already present in the target project
- Progressive disclosure benefits are minimal when agents exist

### Question 4: Were existing agents relevant to the split decision?

**Answer**: **No**, existing agents did NOT affect the split decision.

**Clarification**:
- The split failed due to **size limits**, not agent presence
- Agent discovery happens in Phase 5 (after CLAUDE.md generation)
- The "All capabilities covered by existing agents" message is separate from split logic

---

## Findings

### Finding 1: Incomplete Implementation of TASK-ENH-SIZE-LIMIT

**Severity**: High
**Type**: Bug

The `--claude-md-size-limit` flag was partially implemented but never wired up to argparse, making it unusable from the command line.

**Impact**:
- Users cannot override the 15KB limit
- Documentation suggests a flag that doesn't work
- Error messages reference a non-functional flag

### Finding 2: Hard-coded 15KB Limit in models.py

**Severity**: Medium
**Type**: Design Issue

The `validate_size_constraints()` method has a hard-coded 15KB threshold that overrides any configurable limit.

```python
warning_size = 15 * 1024  # 15KB warning threshold

if core_size > warning_size:
    return False, (...)  # Hard failure
```

**Impact**:
- Even if `--claude-md-size-limit 50KB` worked, it would still fail at 15KB
- The configurable limit only affects warnings (10-15KB range), not hard failures

### Finding 3: Template Creation Succeeded

**Severity**: None (Positive)
**Type**: Observation

Despite the split failure, the template was created successfully:
- 48.4KB single CLAUDE.md (1,235 lines)
- 20 template files across all architectural layers
- Complete manifest.json and settings.json
- All 8 agents matched from existing `.claude/agents/`

---

## Recommendations

### Recommendation 1: Complete TASK-ENH-SIZE-LIMIT (High Priority)

Add the missing argparse argument and wire it to `run_template_create()`:

```python
# In argparse section (~line 2788)
parser.add_argument("--claude-md-size-limit", type=str,
                    help="Maximum size for core CLAUDE.md (e.g., 50KB, 1MB)")

# In run_template_create call (~line 2791)
claude_md_size_limit = (
    TemplateCreateOrchestrator.parse_size_limit(args.claude_md_size_limit)
    if args.claude_md_size_limit else 10 * 1024
)
```

### Recommendation 2: Fix Hard-coded 15KB Limit (Medium Priority)

Make the 15KB threshold configurable or remove it:

```python
def validate_size_constraints(self, max_core_size: int = 10 * 1024) -> tuple[bool, Optional[str]]:
    core_size = self.get_core_size()

    if core_size > max_core_size:
        return False, (
            f"Core content exceeds {max_core_size / 1024:.0f}KB limit: "
            f"{core_size / 1024:.2f}KB. Use --claude-md-size-limit to override."
        )

    return True, None
```

### Recommendation 3: Reopen TASK-ENH-SIZE-LIMIT (High Priority)

The task was incorrectly marked as completed. It should be:
1. Reopened with status `in_progress`
2. Updated acceptance criteria to include argparse verification
3. Add a test case that verifies the flag works end-to-end

---

## Decision Matrix

| Option | Effort | Risk | Benefit | Recommendation |
|--------|--------|------|---------|----------------|
| A: Do nothing | None | Low | None | Not recommended |
| B: Fix argparse only | Low (30 min) | Low | High | **Recommended** |
| C: Fix argparse + 15KB limit | Medium (1-2h) | Low | High | Recommended |
| D: Redesign split logic | High (4-8h) | Medium | Medium | Not now |

---

## Appendix

### Files Analyzed

| File | Purpose |
|------|---------|
| `docs/reviews/progressive-disclosure/template-create-output.md` | Command execution log |
| `docs/reviews/progressive-disclosure/mydrive/CLAUDE.md` | Generated template (48.4KB) |
| `installer/core/commands/lib/template_create_orchestrator.py` | Orchestrator with missing flag |
| `installer/core/lib/template_generator/models.py` | Hard-coded 15KB limit |
| `tasks/completed/.../TASK-ENH-SIZE-LIMIT.md` | Incomplete implementation |

### Metrics

| Metric | Value |
|--------|-------|
| Generated CLAUDE.md size | 48.4 KB (49,565 bytes) |
| CLAUDE.md lines | 1,235 |
| Template files | 20 |
| Agents matched | 8/8 |
| Hard-coded limit | 15 KB |
| Configured limit | 10 KB |
| Content that failed split | 34.68 KB |

---

## Conclusion

The template-create output shows **correct behavior given a bug**. The split was bypassed because the `--claude-md-size-limit` flag wasn't actually implemented, not because of any intelligent decision about existing agents.

**Recommended Action**: Fix the bug (Recommendation 1) and reopen TASK-ENH-SIZE-LIMIT.

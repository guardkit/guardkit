# Implementation Guide: Preamble Overhead Fix

## Execution Strategy

### Wave 1: Quick Wins (Parallel, ~1 hour)

| Task | Description | Method | Files |
|------|-------------|--------|-------|
| TASK-POF-001 | `--autobuild-mode` composite flag | direct | task-work spec, task_work_interface.py |
| TASK-POF-002 | Expand direct mode auto-detection | direct | agent_invoker.py |

**Verification**: After Wave 1, measure preamble duration on a canary task. Expected: ~1,500s (from ~1,800s).

### Wave 2: Main Fix (Parallel, ~4 hours)

| Task | Description | Method | Files |
|------|-------------|--------|-------|
| TASK-POF-003 | Inline design phase protocol | task-work | task_work_interface.py |
| TASK-POF-004 | Inline implement phase protocol | task-work | agent_invoker.py |

**Dependency**: Both depend on TASK-POF-001 (the `--autobuild-mode` flag is used in the inline protocol).

**Verification**: After Wave 2, measure preamble duration. Expected: ~600s (from ~1,500s).

## Key Architecture Decision

### Why Inline Instead of Slim Skill?

**Option A** (Rejected): Create a slim `/task-work-autobuild` skill with just the phases needed
- Still requires `setting_sources=["user"]` to load the skill
- Still loads all 26 user commands (~839KB) just to find the one skill

**Option B** (Chosen): Inline the execution protocol in the Python prompt builder
- Prompt is constructed in Python, no skill resolution needed
- `setting_sources=["project"]` sufficient (~78KB)
- Protocol can be tailored per invocation (design vs implement)
- No new files needed in `~/.claude/commands/`

## Data Flow (After Fix)

```
BEFORE (current):
  Python → SDK(setting_sources=["user","project"]) → Load 1MB → Find /task-work skill → Expand 165KB → Execute

AFTER (Wave 2):
  Python → SDK(setting_sources=["project"]) → Load 78KB → Execute inline protocol → Done
```

## Risk Mitigations

1. **Inline protocol drift**: The inline protocol may diverge from the full task-work spec over time. Mitigate by adding a comment in both locations referencing each other.

2. **Coach validation compatibility**: The Player inline protocol must still produce `task_work_results.json` in the expected format. Test against Coach validation.

3. **Non-autobuild paths unaffected**: These changes only affect the autobuild code paths in `task_work_interface.py` and `agent_invoker.py`. Manual `/task-work` usage continues to use the full skill.

## Verification Checklist

- [ ] Wave 1 canary: preamble ≤ 1,500s
- [ ] Wave 2 canary: preamble ≤ 800s
- [ ] Coach validation still passes after TASK-POF-004
- [ ] Manual `/task-work` usage unaffected
- [ ] Direct mode correctly routes complexity ≤3 tasks after TASK-POF-002

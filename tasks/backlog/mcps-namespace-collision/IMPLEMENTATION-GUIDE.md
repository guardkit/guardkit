# FEAT-MCPS — Implementation Guide

**Feature**: MCP Namespace Collision Fix
**Parent review**: [TASK-REV-MCPS](../TASK-REV-MCPS-mcp-namespace-collision-diagnostic-and-fix-plan.md)
**Strategy**: Minimal-then-complete
**Expected total effort**: 80-95 minutes across two waves
**Blocks downstream**: TASK-COH-RUN1 Phase 2

## Execution strategy at a glance

```
Wave 1 (parallel — ~30 min elapsed; Conductor recommended)
  ├── TASK-FIX-MCPS.1  (sys.path.insert rewrite — 2 files)
  └── TASK-FIX-MCPS.2  (SDK preflight diagnostics)

  ⇣ Gate: full pytest green on main, AutoBuild unblocked

Wave 2 (sequential — ~45 min)
  └── TASK-FIX-MCPS.3  (rename installer/core/lib/mcp/ → context7/)

  ⇣ Gate: full pytest green, mcp import resolves to site-packages,
         Graphiti post-flight episode written

  → Feature complete → TASK-COH-RUN1 Phase 2 unblocked
```

## Wave 1 — Parallel execution

TASK-FIX-MCPS.1 and TASK-FIX-MCPS.2 touch **disjoint files** and can be executed in parallel Conductor workspaces.

### TASK-FIX-MCPS.1 files
- `installer/core/commands/lib/greenfield_qa_session.py` (lines 26-39)
- `installer/core/commands/lib/spec_drift_detector.py` (lines 21-25)

### TASK-FIX-MCPS.2 files
- `guardkit/cli/autobuild.py` (lines 58-103)
- Any test fixtures that assert on `_check_sdk_available` return type.

**Conductor launch**:
```bash
# Terminal A
conductor workspace create mcps-namespace-collision-wave1-syspath
/task-work TASK-FIX-MCPS.1 --mode=standard

# Terminal B (parallel)
conductor workspace create mcps-namespace-collision-wave1-diagnostics
/task-work TASK-FIX-MCPS.2 --mode=standard
```

**Merge order**: either first; the two commits are independent.

### Wave 1 gate (before proceeding to Wave 2)

Run locally on main after both Wave 1 commits land:

```bash
# 1. Full pytest green
pytest tests/ -v

# 2. AutoBuild preflight works
python -c "from guardkit.cli.autobuild import _check_sdk_available; print(_check_sdk_available())"
# Expected: (True, None)

# 3. No more shadowing
python -c "import guardkit.cli.autobuild; import mcp; print(mcp.__file__)"
# Expected: /site-packages/mcp/__init__.py (NOT installer/core/lib/mcp/)

# 4. AutoBuild CLI smoke
guardkit autobuild --help
guardkit autobuild feature --help
```

If all four pass → Wave 1 complete, proceed to Wave 2.

## Wave 2 — Sequential

TASK-FIX-MCPS.3 moves the `installer/core/lib/mcp/` directory, which is a git-level rename. Must run after Wave 1 for clean baseline.

**Conductor launch**:
```bash
conductor workspace create mcps-namespace-collision-wave2-rename
/task-work TASK-FIX-MCPS.3 --mode=standard
```

### Grep audit sequence (to run inside the subtask)

```bash
# 1. Find any callers of installer.core.lib.mcp
rg "installer\.core\.lib\.mcp" --type py
rg "from \.mcp" installer/core/lib/ --type py
rg "from \.\.mcp" installer/core/ --type py

# 2. Find string-based dynamic imports
rg '"installer\.core\.lib\.mcp"|"mcp\.context7"' --type py

# 3. Find doc references
rg "installer/core/lib/mcp" docs/ .claude/

# All four should return zero after the rename.
```

### Wave 2 gate

```bash
pytest tests/ -v
python -c "from installer.core.lib.context7 import Context7Client; print('ok')"
python -c "import sys; sys.path.insert(0, 'installer/core/lib'); import mcp; assert '/site-packages/' in mcp.__file__"
# Third check confirms that even if someone accidentally re-introduces the
# sys.path.insert anti-pattern, `mcp` can no longer be shadowed.
```

## Post-implementation: Graphiti post-flight

After TASK-FIX-MCPS.3 merges, add an episode to `guardkit__task_outcomes` recording the rename as an executed instance of the namespace-hygiene rule. This closes the evidentiary loop — the rule now has both a prior incident (2026-04-18), a codified node (seeded 2026-04-24), and a completed remediation (this rename).

Example MCP episode:

```
mcp__graphiti__add_memory(
  group_id="guardkit__task_outcomes",
  name="TASK-FIX-MCPS.3 rename complete — namespace-hygiene rule applied",
  content="Renamed installer/core/lib/mcp/ → installer/core/lib/context7/. Zero external callers. AutoBuild unblocked. Collision class eliminated. References namespace-hygiene rule seeded 2026-04-24 from TASK-REV-MCPS."
)
```

## Cross-cutting test matrix

| Test | Wave 1 expected | Wave 2 expected |
|---|---|---|
| `pytest tests/` | Pass | Pass |
| `_check_sdk_available()` returns `(True, None)` | ✓ | ✓ |
| `import mcp; mcp.__file__` → site-packages | ✓ | ✓ |
| `installer.core.lib.mcp` importable | ✓ (still) | ✗ (renamed) |
| `installer.core.lib.context7` importable | — | ✓ |
| `guardkit autobuild --help` smoke | ✓ | ✓ |
| Grep for `installer.core.lib.mcp` hits | may exist in tests | zero |

## Rollback plan

- Wave 1 only: `git revert <wave1-commit-1> <wave1-commit-2>`. No schema / state migration. Very low risk.
- Wave 2: `git revert <wave2-commit>` reinstates `installer/core/lib/mcp/`. Zero external callers means no downstream break either way.

## Observed vs expected runtime

| Phase | Expected | Notes |
|---|---|---|
| Wave 1 (parallel) | ~30 min wall clock | Limited by the slower of the two (likely MCPS.1, which touches 2 files). |
| Wave 1 gate | ~5 min | Just the four gate checks + pytest. |
| Wave 2 | ~45 min | Dominated by grep audit + pytest. |
| Graphiti post-flight | ~2 min | MCP call. |
| **Total** | **~80-85 min** | |

If TASK-COH-RUN1 Phase 0 is ready to advance, Phase 2 can kick off immediately after Wave 1 gate passes — TASK-FIX-MCPS.3 is not on that critical path.

## See also

- Review report: [docs/reviews/TASK-REV-MCPS-namespace-collision-review.md](../../../docs/reviews/TASK-REV-MCPS-namespace-collision-review.md)
- Graphiti preamble: [docs/reviews/TASK-REV-MCPS-graphiti-preamble.md](../../../docs/reviews/TASK-REV-MCPS-graphiti-preamble.md)
- Rule: [.claude/rules/namespace-hygiene.md](../../../.claude/rules/namespace-hygiene.md)
- README: [README.md](README.md)

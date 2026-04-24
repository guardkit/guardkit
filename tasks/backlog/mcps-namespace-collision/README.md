# MCP Namespace Collision — Fix Feature

**Feature ID**: FEAT-MCPS
**Parent review**: [TASK-REV-MCPS](../TASK-REV-MCPS-mcp-namespace-collision-diagnostic-and-fix-plan.md)
**Review report**: [docs/reviews/TASK-REV-MCPS-namespace-collision-review.md](../../../docs/reviews/TASK-REV-MCPS-namespace-collision-review.md)
**Blocks**: [TASK-COH-RUN1](../r2-pipeline-closure-and-forge-cohort/TASK-COH-RUN1-forge-and-study-tutor-cohort-run.md) Phase 2
**Strategy**: Minimal-then-complete (per review §5)

## Problem

AutoBuild is reporting "Claude Agent SDK not available" despite `claude-agent-sdk` v0.1.37 being installed and importable from fresh subprocesses. The real failure is a **namespace collision + misleading error message**:

1. `installer/core/commands/lib/greenfield_qa_session.py:29-39` unconditionally runs `sys.path.insert(0, installer/core/lib)` (its "production" branch targets `commands/lib/state_paths.py`, which has never existed — the fallback always fires).
2. A second unconditional call site exists at `installer/core/commands/lib/spec_drift_detector.py:22-25`.
3. With `installer/core/lib` at `sys.path[0]`, GuardKit's internal `installer/core/lib/mcp/` (a Context7 client) wins the `import mcp` race against Anthropic's PyPI `mcp` package (a transitive dep of `claude-agent-sdk`).
4. `guardkit/cli/autobuild.py:58-103` swallows the real `ModuleNotFoundError: No module named 'mcp.types'` and re-prints a hard-coded SDK banner.

**The bug is one instance of a recurring class** — Graphiti fact `cced8d00` records the same mechanism on 2026-04-18 (editable-install `lib/` shadowing a rendered template's `lib/`) with no design rule seeded. This feature closes both the instance and the class.

## Solution Approach

Three fixes, two waves:

**Wave 1 (ship same commit):**
- `TASK-FIX-MCPS.1` — rewrite the two `sys.path.insert` fallbacks to fully-qualified structural imports (`from installer.core.lib.X import ...`). Validated by Graphiti fact `f868769a` (editable install exposes repo root on `sys.path`).
- `TASK-FIX-MCPS.2` — surface the real `ImportError` in `_check_sdk_available` / `_require_sdk`. Future namespace-shadowing symptoms diagnose in seconds rather than hours.

**Wave 2 (same-day follow-on):**
- `TASK-FIX-MCPS.3` — rename `installer/core/lib/mcp/` → `installer/core/lib/context7/`. Zero external callers found in the review's sweep, so this is essentially cost-free and eliminates the collision class entirely.

Companion artefacts (already committed on review acceptance):
- `.claude/rules/namespace-hygiene.md` — human-readable rule.
- Graphiti design-rule node in `guardkit__project_decisions`: *"GuardKit internal module names must not shadow PyPI packages"*.

## Subtasks

| Task | Title | Wave | Effort | Risk | Workspace |
|---|---|---|---|---|---|
| [TASK-FIX-MCPS.1](TASK-FIX-MCPS.1-rewrite-syspath-fallbacks.md) | Rewrite sys.path.insert fallbacks (greenfield_qa_session + spec_drift_detector) | 1 | 30 min | very low | `mcps-namespace-collision-wave1-syspath` |
| [TASK-FIX-MCPS.2](TASK-FIX-MCPS.2-sdk-preflight-diagnostics.md) | Surface real ImportError in `_check_sdk_available` / `_require_sdk` | 1 | 20 min | very low | `mcps-namespace-collision-wave1-diagnostics` |
| [TASK-FIX-MCPS.3](TASK-FIX-MCPS.3-rename-internal-mcp-to-context7.md) | Rename `installer/core/lib/mcp/` → `installer/core/lib/context7/` | 2 | 30-45 min | low | `mcps-namespace-collision-wave2-rename` |

## Acceptance of this feature

Feature is considered complete when:
- All three subtasks are merged.
- `python -c "import guardkit.cli.autobuild; import mcp; assert '/site-packages/' in mcp.__file__"` passes.
- `guardkit autobuild feature --help` works without the false "SDK not available" banner.
- Graphiti updated with the post-flight episode for the rename (completed instance of the namespace-hygiene rule).
- TASK-COH-RUN1 Phase 2 unblocked for the forge / study-tutor cohort run.

## See also

- [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md) — execution strategy, wave sequencing, test matrix.
- [.claude/rules/namespace-hygiene.md](../../../.claude/rules/namespace-hygiene.md)
- Sibling review: [TASK-REV-STKB](../TASK-REV-STKB-stack-blindness-audit-and-bdd-plugin-architecture.md) — same meta-rule, different surface.

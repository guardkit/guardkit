# HMIG Pre-Canary Fixes

> **Origin**: TASK-REV-HM09 (2026-05-27)
> **Feature ID**: `hmig-pre-canary-fixes` (part of FEAT-HMIG)
> **Deadline**: 2026-06-15 (Wave-4 LangGraph cutover)

## Problem

The TASK-HMIG-009 canary pilot surfaced two architectural gaps that block the canary from producing meaningful SDK-vs-LangGraph comparative data:

1. **F1 — Pre-loop bypasses the harness adapter.** Every `autobuild task --pre-loop` invocation silently uses claude-agent-sdk for the design phase regardless of `GUARDKIT_HARNESS`. HMIG-006's adapter migration only covered the Player-Coach loop.
2. **F4 — `WorktreeManager.create()` ignores cwd HEAD.** `autobuild task`/`autobuild feature` branch the inner worktree from main HEAD regardless of where invoked from. Defeats fixture-branch isolation and breaks parallel feature-build use cases.

Both have implications beyond the canary itself.

A third pilot finding (**F2 — "local Qwen fails marker contract"**) was originally framed as a llama-swap parser-config defect. On 2026-05-27 it was reframed as a **model-swap incident**: the canary had silently been pointing at `qwen3-coder-30b` post-2026-04-29 instead of `qwen-coder-next` (the operator's documented and proven AutoBuild Player model). The canary-set.json was edited in-place to revert the swap; no separate task tracks this.

## Solution

**Path 2 — Partial close** (recommended by [TASK-REV-HM09 §8](../../../.claude/reviews/TASK-REV-HM09-review-report.md#8-ac-008--one-page-operator-decision-brief)). Four tasks:

1. **TASK-HMIG-006.4** — Migrate the pre-loop's `TaskWorkInterface._execute_via_sdk` through `HarnessAdapter` (closes F1).
2. **TASK-FIX-WTBC** — Honour cwd HEAD in `autobuild task`/`autobuild feature` CLI (closes F4).
3. **TASK-HMIG-009A** — Partial canary execution, post-F1. Preflight ACs (001A–001D) confirm `qwen-coder-next` works end-to-end before committing to full 12-run compute; main run produces the cutover-decision signal.
4. **TASK-HMIG-009B** — Full canary (original spec), post-all. Optional polish if 009A signal is ambiguous.

### Removed from original task list (2026-05-27)

- ~~**TASK-OPS-LSPC**~~ — originally filed as a parser-config audit task; reframed as a ~1h model swap. The canary-set.json edit was done inline on 2026-05-27. End-to-end verification folded into TASK-HMIG-009A's preflight ACs (001A–001D). Documentation + Graphiti capture folded into 009A's closing ACs (007, 008). See `model_choice_correction` block in [.guardkit/autobuild/TASK-REV-HMIG-canary-set.json](../../../.guardkit/autobuild/TASK-REV-HMIG-canary-set.json) for the audit trail.

## Subtask summary

| Task | Wave | Effort | Mode | Status |
|---|---|---|---|---|
| [TASK-HMIG-006.4](./TASK-HMIG-006.4-migrate-preloop-task-work-interface.md) | 1 | 5–7h | task-work | backlog |
| [TASK-FIX-WTBC](./TASK-FIX-WTBC-honour-cwd-head-in-autobuild-cli.md) | 1 | 3–4h | task-work | **in_review** (landed 2026-05-27) |
| [TASK-HMIG-009A](./TASK-HMIG-009A-partial-canary-no-preloop-backlog-tasks.md) | 2 | ~10h compute | manual | backlog |
| [TASK-HMIG-009B](./TASK-HMIG-009B-full-canary-original-spec-optional.md) | 3 | ~40h compute | manual (optional) | backlog |

**Total dev effort**: ~10h focused + ~10–50h GB10 canary compute.

## How to start

Read **[IMPLEMENTATION-GUIDE.md](./IMPLEMENTATION-GUIDE.md)** first — it covers:

- Wave-by-wave execution strategy (Wave 1 fully parallel)
- Recommended timeline against 2026-06-15 cutover
- Decision points after each gate
- Out-of-scope items

Then start Wave 1:

```bash
# Wave 1 — TASK-FIX-WTBC already landed (in_review). One remaining dev task:
guardkit autobuild task TASK-HMIG-006.4
```

## References

- **Review report**: [.claude/reviews/TASK-REV-HM09-review-report.md](../../../.claude/reviews/TASK-REV-HM09-review-report.md) (includes correction addendum re: model choice framing)
- **Pilot evidence**: [docs/state/TASK-REV-HMIG/canary-analysis.md](../../../docs/state/TASK-REV-HMIG/canary-analysis.md) (read with 2026-05-27 correction in mind — F2's interpretation has been revised)
- **Canary set (post-model-swap)**: [.guardkit/autobuild/TASK-REV-HMIG-canary-set.json](../../../.guardkit/autobuild/TASK-REV-HMIG-canary-set.json) — see `model_choice_correction` block
- **Source of truth for model choice**: [docs/research/dgx-spark/gb10-model-requirements-matrix.md](../../../docs/research/dgx-spark/gb10-model-requirements-matrix.md)
- **Originating review task**: [TASK-REV-HM09](../autobuild-harness-migration/TASK-REV-HM09-pilot-findings-preloop-and-worktree-gaps.md)
- **Parent migration review**: [TASK-REV-HMIG](../../../.claude/reviews/TASK-REV-HMIG-review-report.md)

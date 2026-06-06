# HMIG Pre-Canary Fixes

> **Origin**: TASK-REV-HM09 (2026-05-27)
> **Feature ID**: `hmig-pre-canary-fixes` (part of FEAT-HMIG)
> **Deadline**: 2026-06-15 (Wave-4 LangGraph cutover)

## Problem

The TASK-HMIG-009 canary pilot surfaced two architectural gaps that block the canary from producing meaningful SDK-vs-LangGraph comparative data:

1. **F1 — Pre-loop bypasses the harness adapter.** Every `autobuild task --pre-loop` invocation silently uses claude-agent-sdk for the design phase regardless of `GUARDKIT_HARNESS`. HMIG-006's adapter migration only covered the Player-Coach loop.
2. **F4 — `WorktreeManager.create()` ignores cwd HEAD.** `autobuild task`/`autobuild feature` branch the inner worktree from main HEAD regardless of where invoked from. Defeats fixture-branch isolation and breaks parallel feature-build use cases.

Both have implications beyond the canary itself.

A third pilot finding (**F2 — "local Qwen fails marker contract"**) has gone through two reframes:

- **2026-05-27 (v1)**: Reframed from parser-config defect to model-swap incident — the canary had silently been pointing at `qwen3-coder-30b` instead of `qwen-coder-next`. Canary-set edited to revert; preflight ACs added.
- **2026-06-02 (v2)**: Preflight AC-001A surfaced that `qwen-coder-next` was documented but **not actually deployed** on the live GB10 llama-swap. After ~1 week of operator llama-swap reconfiguration work + benchmark/forum research, the operator selected `qwen36-workhorse` (Qwen3.6-35B-A3B) as the AutoBuild Player — it's LIVE on the GB10, shared across `jarvis-reasoner, forge, autobuild, dataset-factory` per [`gb10-memory-budget-and-macbook-offload.md:37`](../../../docs/research/dgx-spark/gb10-memory-budget-and-macbook-offload.md#L37), and identified as the strongest deployable agentic-coding model. Canary-set updated with `model_choice_correction_v2`; no new task; 009A preflight AC-001A/B will re-verify against the post-reconfig workhorse.

No separate task tracks F2 — see `model_choice_correction_v2` block in [.guardkit/autobuild/TASK-REV-HMIG-canary-set.json](../../../.guardkit/autobuild/TASK-REV-HMIG-canary-set.json) for full audit trail.

## Solution

**Path 2 — Partial close** (recommended by [TASK-REV-HM09 §8](../../../.claude/reviews/TASK-REV-HM09-review-report.md#8-ac-008--one-page-operator-decision-brief)). Four tasks:

1. **TASK-HMIG-006.4** — Migrate the pre-loop's `TaskWorkInterface._execute_via_sdk` through `HarnessAdapter` (closes F1).
2. **TASK-FIX-WTBC** — Honour cwd HEAD in `autobuild task`/`autobuild feature` CLI (closes F4).
3. **TASK-HMIG-009A** — Partial canary execution, post-F1. Preflight ACs (001A–001D) confirm `qwen36-workhorse` works end-to-end on the post-reconfig llama-swap before committing to full 12-run compute; main run produces the cutover-decision signal.
4. **TASK-HMIG-009B** — Full canary (original spec), post-all. Optional polish if 009A signal is ambiguous.

### Removed from original task list (2026-05-27)

- ~~**TASK-OPS-LSPC**~~ — originally filed as a parser-config audit task; reframed as a ~1h model swap. The canary-set.json edit was done inline on 2026-05-27. End-to-end verification folded into TASK-HMIG-009A's preflight ACs (001A–001D). Documentation + Graphiti capture folded into 009A's closing ACs (007, 008). See `model_choice_correction` block in [.guardkit/autobuild/TASK-REV-HMIG-canary-set.json](../../../.guardkit/autobuild/TASK-REV-HMIG-canary-set.json) for the audit trail.

## Subtask summary

| Task | Wave | Effort | Mode | Status |
|---|---|---|---|---|
| [TASK-HMIG-006.4](./TASK-HMIG-006.4-migrate-preloop-task-work-interface.md) | 1 | 5–7h | task-work | **landed** (commit `f2c240a7`) |
| [TASK-FIX-WTBC](./TASK-FIX-WTBC-honour-cwd-head-in-autobuild-cli.md) | 1 | 3–4h | task-work | **in_review** (landed 2026-05-27) |
| [TASK-FIX-MODELPLUMB](../../completed/2026-06/TASK-FIX-MODELPLUMB-thread-cli-model-through-harness.md) | pre-canary | 0.5h | manual | **landed** 2026-06-02 |
| [TASK-FIX-LGTOOLS](../../completed/2026-06/TASK-FIX-LGTOOLS-langgraph-harness-drop-sdk-tools.md) | pre-canary | 0.5h | manual | **landed** 2026-06-03 (guardkitfactory) |
| ~~TASK-HMIG-002R~~ | — | — | — | **DUPLICATE — deleted 2026-06-03.** Already complete in `../guardkitfactory/tasks/completed/TASK-HMIG-002R/` since 2026-05-20. |
| [TASK-FIX-002R-CONSUME](../autobuild-harness-migration/TASK-FIX-002R-CONSUME-wire-guardkitfactory-backend-permissions-into-selector.md) | 1 | ~1h | task-work | **landed** 2026-06-03 — wired guardkitfactory's factories into guardkit's selector |
| ~~TASK-HMIG-002R-PROMPT~~ | — | — | — | **DELETED 2026-06-03.** Closing criterion (run 6 succeeds end-to-end) met; DeepAgents' runtime tool advertisement was sufficient — no prompt adaptation needed. |
| Cross-repo: TASK-HMIG-002R-NOPERMS | — | ~30min | manual | **landed** 2026-06-03 in `../guardkitfactory/tasks/completed/` |
| Cross-repo: TASK-HMIG-002R-NOVMODE | — | ~30min | manual | **landed** 2026-06-03 in `../guardkitfactory/` |
| [TASK-HMIG-009A](./TASK-HMIG-009A-partial-canary-no-preloop-backlog-tasks.md) | 2 | ~10h compute | manual | **backlog** (unblocked 2026-06-03 — AC-001D ✅ run 6 APPROVED; ready for 12-run batch) |
| [TASK-HMIG-009B](./TASK-HMIG-009B-full-canary-original-spec-optional.md) | 3 | ~40h compute | manual (optional) | backlog |

**Total dev effort**: ~10h focused + ~10–50h GB10 canary compute.

## How to start

Read **[IMPLEMENTATION-GUIDE.md](./IMPLEMENTATION-GUIDE.md)** first — it covers:

- Wave-by-wave execution strategy (Wave 1 fully parallel)
- Recommended timeline against 2026-06-15 cutover
- Decision points after each gate
- Out-of-scope items

### Current state (2026-06-04, post-AC-003 batch + cutover-ceremony task filed)

**Critical-path chain to cutover** (Option (a) sequencing chosen 2026-06-04):

```
TASK-HMIG-006.2 (~5h, plan-ready)
      ↓
TASK-HMIG-006.3 (~4h)
      ↓
TASK-HMIG-006.1 (~5h)
      ↓
TASK-HMIG-010 (~8h — real-world feature validation)
      ↓
TASK-HMIG-011 (~2h flip + docs + announce; ~5d observation)
      ↓
2026-06-15: Anthropic API-key validation enforcement begins
```

**Cutover-decision context**: canary-analysis §8.6 documents three readings of the 5/6+5/6 batch result. Reading 2 (GO with F6 substrate caveat) is the working assumption for Option (a) sequencing. Reading 1 (HALT) or Reading 3 (run 009B for larger-N) would gate TASK-HMIG-011 differently.

---

### Current state (2026-06-03, post-AC-001D-run-6 SUCCESS)

**SDK side**: ✅ FULLY VALIDATED. AC-001C APPROVED in 1 turn (3/16/1, honesty 1.00).
**LangGraph side**: ✅ **FULLY VALIDATED.** AC-001D run 6 APPROVED in 1 turn (4/16/2, honesty 0.96, ~13.5min — ~35% faster end-to-end than SDK).

**6-run discovery journey** — each run unblocked exactly one layer:
1. ✅ Model plumbing (MODELPLUMB, guardkit) — landed 2026-06-02
2. ✅ tools=[strings] crash (LGTOOLS, guardkitfactory) — landed 2026-06-03
3. ✅ Consumer-side backend wiring (002R-CONSUME, guardkit) — landed 2026-06-03
4. ✅ DeepAgents permissions+execute incompatible (NOPERMS, guardkitfactory) — landed 2026-06-03
5. ✅ virtual_mode path-doubling (NOVMODE, guardkitfactory) — landed 2026-06-03
6. ✅ Predicted 6th layer (prompt/tool-name mismatch) DISSOLVED — DeepAgents runtime advertisement sufficed; 002R-PROMPT deleted

**Recommended next steps**:

1. **Review the run-6 Player diff** in `.guardkit/worktrees/TASK-FIX-A7D3/` to spot-check the LLM Coach's approval against the honesty oracle's flagged must-fix discrepancy (line 194: `gather_evidence: honesty produced 1 must_fix issue(s)`). Confirm it was genuinely minor.
2. **Run the 12-run batch**: `python scripts/canary_validation_runner.py --variant 009a` (~10h GB10 compute). Then `--variant 009a --aggregate`.
3. **Aggregate analysis** in canary-analysis §8 + verdict against the cutover bar.
4. **Cutover decision** → TASK-HMIG-010.

**Quality signals to watch across the batch** (per guardkitfactory run-6 review):
- LLM-Coach-overrides-honesty-oracle pattern (line 194/218) — track frequency; expected on both harnesses
- `Criteria Progress 0/1 verified (0%)` with Coach approval — LLM-Coach-as-fallback shape; compare SDK vs LangGraph
- `/v1/responses` retries — transient under qwen36-workhorse; if >2 of 12 runs retry, check vLLM queue depth

**Cutover-deadline outlook**: comfortable. ~10h compute + aggregate + decision against 12-day window.

## References

- **Review report**: [.claude/reviews/TASK-REV-HM09-review-report.md](../../../.claude/reviews/TASK-REV-HM09-review-report.md) (includes correction addendum re: model choice framing)
- **Pilot evidence**: [docs/state/TASK-REV-HMIG/canary-analysis.md](../../../docs/state/TASK-REV-HMIG/canary-analysis.md) (read with 2026-05-27 correction in mind — F2's interpretation has been revised)
- **Canary set (post-model-swap)**: [.guardkit/autobuild/TASK-REV-HMIG-canary-set.json](../../../.guardkit/autobuild/TASK-REV-HMIG-canary-set.json) — see `model_choice_correction` block
- **Source of truth for model choice**: [docs/research/dgx-spark/gb10-model-requirements-matrix.md](../../../docs/research/dgx-spark/gb10-model-requirements-matrix.md)
- **Originating review task**: [TASK-REV-HM09](../autobuild-harness-migration/TASK-REV-HM09-pilot-findings-preloop-and-worktree-gaps.md)
- **Parent migration review**: [TASK-REV-HMIG](../../../.claude/reviews/TASK-REV-HMIG-review-report.md)

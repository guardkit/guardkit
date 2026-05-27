# Feature: HMIG Pre-Canary Fixes — Implementation Guide

> **Origin**: [TASK-REV-HM09 review report](../../../.claude/reviews/TASK-REV-HM09-review-report.md) (2026-05-27)
> **Parent feature**: FEAT-HMIG (autobuild-harness-migration)
> **Cutover deadline**: 2026-06-15 (Wave-4 LangGraph cutover, TASK-HMIG-010)
> **Recommended path**: Path 2 — Partial close ([§8](../../../.claude/reviews/TASK-REV-HM09-review-report.md#8-ac-008--one-page-operator-decision-brief))

---

## 1. Why this feature folder exists

The TASK-HMIG-009 canary pilot surfaced two architectural gaps (F1 + F4) that block the canary from producing meaningful comparative data **and** have broader implications than the canary itself:

- **F1**: The pre-loop design phase silently bypasses the harness adapter — HMIG-006's "agent_invoker through HarnessAdapter" completion claim is partially contested.
- **F4**: `WorktreeManager.create()` ignores cwd HEAD — `autobuild task` and `autobuild feature` both branch from main HEAD regardless of where they're invoked from. Breaks the canary's fixture-baseline strategy and any caller running autobuild from a non-main branch.

A third pilot finding (**F2** — "local Qwen fails marker contract") was originally framed as a parser-config defect. On 2026-05-27 it was reframed as a **model-swap incident**: the canary had silently been pointing at `qwen3-coder-30b` post-2026-04-29 instead of `qwen-coder-next` (the operator's documented and proven AutoBuild Player model). The canary-set.json was edited in-place on 2026-05-27 to revert the swap; no separate task tracks this. See `model_choice_correction` block in [.guardkit/autobuild/TASK-REV-HMIG-canary-set.json](../../../.guardkit/autobuild/TASK-REV-HMIG-canary-set.json) for the audit trail.

The four tasks in this folder close F1 + F4 and replace the original TASK-HMIG-009 with a scope-revised pair (009A + 009B) that produces canary signal in stages as fixes land.

---

## 2. Task list

| Task | Title | Wave | Effort | Mode | Status |
|---|---|---|---|---|---|
| [TASK-HMIG-006.4](./TASK-HMIG-006.4-migrate-preloop-task-work-interface.md) | Migrate `TaskWorkInterface._execute_via_sdk` through HarnessAdapter (F1 fix) | 1 | 5–7h | task-work | backlog |
| [TASK-FIX-WTBC](./TASK-FIX-WTBC-honour-cwd-head-in-autobuild-cli.md) | Honour cwd HEAD in autobuild task/feature CLI (F4 fix) | 1 | 3–4h | task-work | **in_review** (landed 2026-05-27) |
| [TASK-HMIG-009A](./TASK-HMIG-009A-partial-canary-no-preloop-backlog-tasks.md) | Partial canary — backlog tasks, no pre-loop, no fixture isolation (post-F1). Preflight ACs (001A–001D) confirm `qwen-coder-next` works end-to-end before committing to the 12-run execution. | 2 | ~10h compute | manual | backlog |
| [TASK-HMIG-009B](./TASK-HMIG-009B-full-canary-original-spec-optional.md) | Full canary — original 18-rep spec (optional polish, post-all) | 3 | ~40h compute | manual | backlog |

### Removed from the original task list (2026-05-27)

- ~~**TASK-OPS-LSPC**~~ — originally filed as a parser-config audit task; reframed as a ~1h model swap. The canary-set.json edit was done inline on 2026-05-27. End-to-end verification folded into TASK-HMIG-009A's preflight ACs (001A–001D). Documentation + Graphiti capture folded into 009A's closing ACs (007, 008).

---

## 3. Execution strategy — wave breakdown

### Wave 1 — Parallel dev tasks (no file overlap)

| Task | Touches | Conductor workspace |
|---|---|---|
| TASK-HMIG-006.4 | `task_work_interface.py`, `harness/selector.py`, `harness/README.md`, new tests under `tests/orchestrator/quality_gates/` and `tests/orchestrator/harness/` | `hmig-pre-canary-fixes-wave1-1` |
| TASK-FIX-WTBC | `cli/autobuild.py`, new tests under `tests/unit/test_cli_autobuild.py` | `hmig-pre-canary-fixes-wave1-2` (**already landed; in_review**) |

**Parallel execution**: TASK-FIX-WTBC has already landed on 2026-05-27. Only TASK-HMIG-006.4 remains for Wave 1.

### Wave 2 — Sequential (gated by Wave 1)

| Task | Depends on | Reason |
|---|---|---|
| TASK-HMIG-009A | TASK-HMIG-006.4 | Without F1 fix the canary cannot produce SDK-vs-LangGraph comparison signal. Model swap already applied via canary-set edit on 2026-05-27. F4 fix not required because 009A's scope (no fixture isolation) sidesteps it; the WTBC fix is a nice-to-have, not a blocker. 009A's preflight ACs (001A–001D) confirm `qwen-coder-next` produces tool_use blocks before committing to the 12-run execution. |

### Wave 3 — Optional (gated by Wave 2 + remaining Wave 1)

| Task | Depends on | Reason |
|---|---|---|
| TASK-HMIG-009B | TASK-HMIG-006.4 + TASK-FIX-WTBC + TASK-HMIG-009A | Original 18-rep canary spec needs both code fixes landed plus 009A's preflight to have empirically validated the model choice end-to-end. Runs only if 009A signal is ambiguous. |

---

## 4. Recommended timeline

Against the 2026-06-15 Wave-4 cutover deadline, with start on 2026-05-28:

| Date | Milestone |
|---|---|
| 2026-05-27 | TASK-FIX-WTBC landed (`in_review`). Canary-set model-swap applied. ✅ |
| 2026-05-28 → 2026-05-30 | TASK-HMIG-006.4 lands (~6h focused dev). |
| 2026-05-31 | TASK-HMIG-009A preflight (ACs 001A–001D, <30min) confirms `qwen-coder-next` works end-to-end on both harnesses. |
| 2026-05-31 → 2026-06-02 | TASK-HMIG-009A main execution (~10h GB10 compute). |
| 2026-06-03 | TASK-HMIG-009A verdict documented; TASK-HMIG-010 (cutover) decision made. |
| 2026-06-04 → 2026-06-10 | Optional: TASK-HMIG-009B executes if 009A ambiguous (~40h compute, parallel with cutover prep). |
| 2026-06-15 | Wave-4 cutover (TASK-HMIG-010). |

Margin against deadline: ~12 days. Comfortable; F2 reframe shortened the critical path significantly.

---

## 5. Decision points

### After TASK-HMIG-006.4 lands

**Gate**: Does the falsifier pass? (`autobuild task --pre-loop` with `GUARDKIT_HARNESS=langgraph` produces zero `claude_agent_sdk.subprocess_cli` log lines.)

- **Pass**: Proceed to TASK-HMIG-009A.
- **Fail**: Re-open TASK-HMIG-006.4 with specific failure mode; escalate.

### After TASK-HMIG-009A preflight (ACs 001A–001D)

**Gate**: Does `qwen-coder-next` produce well-formed `tool_use` blocks end-to-end on both harnesses?

- **Pass** (expected per prior proof): proceed to AC-003 (12-run execution).
- **Fail** (unexpected — contradicts the operator's prior empirical validation): halt and file a follow-up parser-config investigation against `qwen-coder-next` specifically. F2 was not what we thought; new diagnosis needed.

### After TASK-HMIG-009A main execution

**Gate**: Aggregate LangGraph first-pass-success rate across 6 LangGraph runs.

- **≥75% with classified failure modes**: Cutover proceeds on schedule. Skip TASK-HMIG-009B.
- **<75% but failure modes are addressable**: Decide whether to (a) defer cutover and run 009B for additional evidence, or (b) ship cutover with documented limitations.
- **Ambiguous / null result**: Run TASK-HMIG-009B for stricter conditions.

### After TASK-HMIG-009B (if run)

**Gate**: Does 009B verdict reinforce or contradict 009A?

- **Reinforce**: Cutover proceeds with high confidence.
- **Contradict**: Escalate — document hypothesis for divergence (substrate variance, pre-loop interaction, fixture-isolation effect).

---

## 6. Out of scope (for this feature)

The following are **explicitly out of scope** for the HMIG pre-canary fixes feature:

- **F6 (Player honesty failure rate on local Qwen)** — substrate quality finding; not actionable within this feature. Tracked as a documentation note in TASK-HMIG-009A's methodology section. Re-evaluate after qwen-coder-next runs land (F6's evidence base was qwen3-coder-30b runs, which were the wrong model — the honesty failure rate may differ on the correct model).
- **TASK-REV-PL01 (whether to keep pre-loop at all)** — a deeper architectural question that this feature deliberately does not foreclose. F1's fix (option (i)) preserves the pre-loop; PL01 remains open as a separate decision.
- **TASK-HMIG-006.1, .2, .3** — three other SDK call sites already filed as separate follow-ups to HMIG-006. Independent of this feature.
- **Broader `--base-branch` flag rollout** to other commands beyond `autobuild task`/`autobuild feature`. TASK-FIX-WTBC's scope is limited to the two CLI surfaces where F4 was observed.
- **Parser-config audit for `qwen3-coder-30b` / `qwen36-workhorse`** — these are not AutoBuild Player models. If a user later wants to add them as additional Player options, file as a separate task.

---

## 7. Cross-references

- **Originating review**: [TASK-REV-HM09 review report](../../../.claude/reviews/TASK-REV-HM09-review-report.md) (includes correction addendum re: model choice framing)
- **Canary set (post-model-swap)**: [.guardkit/autobuild/TASK-REV-HMIG-canary-set.json](../../../.guardkit/autobuild/TASK-REV-HMIG-canary-set.json) — see `model_choice_correction` block
- **Source of truth for model choice**: [`docs/research/dgx-spark/gb10-model-requirements-matrix.md`](../../../docs/research/dgx-spark/gb10-model-requirements-matrix.md), [`docs/research/dgx-spark/llama-swap-config.yaml`](../../../docs/research/dgx-spark/llama-swap-config.yaml), [`docs/research/dev-pipeline-system/ships-computer-system-arch-intent.md`](../../../docs/research/dev-pipeline-system/ships-computer-system-arch-intent.md)
- **Pilot evidence**: [`docs/state/TASK-REV-HMIG/canary-analysis.md`](../../../docs/state/TASK-REV-HMIG/canary-analysis.md) §3 (F1–F8 findings — F2's interpretation has been revised; read with 2026-05-27 correction in mind)
- **Parent migration review**: [TASK-REV-HMIG review report](../../../.claude/reviews/TASK-REV-HMIG-review-report.md)
- **Original canary task** (now superseded): [TASK-HMIG-009 (blocked)](../../blocked/TASK-HMIG-009-canary-validation.md)
- **Wave-4 cutover** (gated by this feature): TASK-HMIG-010
- **Sibling HMIG-006 follow-ups**:
  - [TASK-HMIG-006.1](../autobuild-harness-migration/TASK-HMIG-006.1-migrate-direct-mode-sdk-dispatch.md) — direct-mode TaskWork dispatch
  - [TASK-HMIG-006.2](../autobuild-harness-migration/TASK-HMIG-006.2-migrate-helpers-to-harness-event-dispatch.md) — downstream helpers
  - [TASK-HMIG-006.3](../autobuild-harness-migration/TASK-HMIG-006.3-migrate-coach-independent-sdk-invocation.md) — Coach independent SDK

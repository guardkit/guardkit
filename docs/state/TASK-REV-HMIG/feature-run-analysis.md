# Feature-run analysis — TASK-HMIG-010

> Companion to
> [`.guardkit/autobuild/TASK-REV-HMIG-feature-results.json`](../../../.guardkit/autobuild/TASK-REV-HMIG-feature-results.json)
> and [`.guardkit/autobuild/TASK-REV-HMIG-feature-target.json`](../../../.guardkit/autobuild/TASK-REV-HMIG-feature-target.json).
> Separate from [`canary-analysis.md`](canary-analysis.md) for clarity (per AC-009).
> This file is the **human-authored audit narrative** capturing *why*
> the feature run produced the verdict it did and what follow-up work it triggers.

## 0. Status (2026-06-04, post-run-1)

- [x] Scaffolded by `/task-work TASK-HMIG-010` (2026-06-04)
- [x] AC-001 — Feature target picked: FEAT-AOF (autobuild-observability-fixes, all 3 tasks)
- [⛔] AC-002 — Feature run end-to-end **BLOCKED**: run 1 aborted after 28s at Player turn 1 of Wave 1 / TASK-FIX-IA03 with LangGraphHarnessError (auth). See §6 / I-001 (F9).
- [〜] AC-003 — Run 1 recorded in feature-results.json:task_outcomes (1 entry, non_recoverable=true). No substrate-quality data yet.
- [ ] AC-004 — First-pass-success rate: not computable from run 1 (CLI-plumbing fail, not substrate fail).
- [ ] AC-005 — No `--resume` attempted: same auth error would fire every turn until LGFM lands.
- [x] AC-006 — F9 documented in [feature-run-incidents.md](feature-run-incidents.md) as I-001 (severity: high).
- [ ] AC-007 — Merge not reached.
- [ ] AC-008 — Falsifier verdict deferred until LGFM lands and a clean run 2 produces data.
- [〜] AC-009 — This analysis document carries the run-1 narrative (§§0, 6); §§1-5, 7-8 pending real data.

## Status header (2026-06-04T20:30Z)

**TASK-HMIG-010 BLOCKED on TASK-FIX-LGFM.** Run 1 surfaced F9 (feature
subcommand doesn't thread `--model` to LangGraph harness — sibling-of-F1).
After LGFM lands, re-run with `--fresh` and resume the AC checklist
from AC-002.

## 1. Executive verdict

_Pending run 2 (post-LGFM-fix). Run 1 produced no substrate-quality
data — the failure was a CLI-plumbing gap, not a model/Coach/Player
behaviour finding._

## 2. Methodology actually executed

| Aspect | Spec intent | Actual |
|---|---|---|
| Target feature | ≥3 tasks, ≥2 waves, BDD-gated, state-bridge, ≤8h | _pending operator pick_ |
| Harness | langgraph | _pending_ |
| Model | qwen36-workhorse (same as 009A) | _pending_ |
| First-pass attempt | per-task | _pending_ |
| Resume policy | on any first-pass failure | _pending_ |
| Merge attempt | `guardkit autobuild complete` | _pending_ |

## 3. Findings — per-task summary

_Table to be filled task-by-task from `feature-results.json:task_outcomes`._

| Task | Wave | First-pass | Resume needed | Final | Turns | Wall-clock | Notes |
|---|---|---|---|---|---|---|---|
| _TBD_ | | | | | | | |

## 4. Aggregate metrics + 009A baseline comparison

_To be computed once `feature-results.json:aggregate_metrics` is filled._

| Metric | This run (010) | 009A baseline | Delta | Significance |
|---|---|---|---|---|
| First-pass success rate | _pending_ | 67% | | AC-004 threshold: >10pp drop = investigate |
| Approval rate (incl. resume) | _pending_ | 83.3% | | |
| Mean turns to approve | _pending_ | ~1.5 | | |
| Mean wall-clock per task | _pending_ | ~21min | | |

## 5. Falsifier evaluation (AC-008)

Threshold: ≥80% first-pass-success AND zero non-recoverable failures → proceed to Wave 4 cutover.

_Verdict: pending data._

## 6. Substrate-level findings worth recording

_The canary-analysis.md F1–F8 numbering continues here. F9 is recorded
below; F10+ will be appended after run 2 (post-LGFM)._

### F9 (2026-06-04): `guardkit autobuild feature` doesn't thread `--model` to the LangGraph harness

**Where**: `guardkit/cli/autobuild.py` — the `feature` subcommand
(definition starting at line 813) has no `--model` click option and
its function signature does not accept a `model` parameter. By
contrast, the sibling `task` subcommand at line 196 does (`--model`
option at line 206, parameter at line 334, threaded to
`AutoBuildOrchestrator` at line 555 with the load-bearing
TASK-FIX-MODELPLUMB comment).

**Evidence**: TASK-HMIG-010 run 1 stdout
[`docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-1.md`](../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-1.md)
line 134:

```
LangGraphHarness: agent.ainvoke failed for role='player' model=None:
"Could not resolve authentication method. Expected either api_key
or auth_token to be set..."
```

Traceback resolves to `langchain_anthropic/chat_models.py:1532` →
`anthropic._base_client._build_headers._validate_headers`. So with
`model=None` reaching the LangGraph harness, DeepAgents instantiates
its default provider (Anthropic), which demands `ANTHROPIC_API_KEY`
— but the operator's env was `OPENAI_BASE_URL` + `OPENAI_API_KEY`
for llama-swap routing.

**Class-of-defect**: sibling-of-F1. F1 was *pre-loop bypasses harness
adapter*: the migration closed the Player-Coach-loop entry point but
missed the pre-loop entry point. F9 is *task subcommand migrated, feature
subcommand missed*: the same sibling-entry-point oversight, one layer up
in the CLI surface.

**Implication**: 009A's clean GO verdict was real — but it only
exercised `guardkit autobuild task` (via the canary runner). The
feature subcommand had never been exercised under LangGraph until
2026-06-04. The cutover GO was based on a substrate that's verified
for the task path only; the feature path needs LGFM before parity is
restored.

**Resolution path**: [TASK-FIX-LGFM](../../../tasks/backlog/autobuild-harness-migration/TASK-FIX-LGFM-feature-subcommand-model-threading.md)
filed 2026-06-04. ~1h fix. Mirrors TASK-HMIG-006.4's pattern for F1
(code edit + regression test asserting the falsifier).

**Cutover-deadline impact**: minimal. ~1h fix + ~1h re-run = ~2h.
Deadline 2026-06-15, current date 2026-06-04. Comfortable.

### F2, F5, F6, F7 (canary-analysis.md) at feature scale

_Pending data from run 2 (post-LGFM). Run 1 did not reach the
Player-LLM step, so no substrate-quality finding could be observed._

## 7. Recommendation

_To be filled. Two shapes possible:_

- **PROCEED to Wave 4 cutover** (TASK-HMIG-011): falsifier passed. Document any caveats from §6.
- **HALT Wave 4 cutover**: falsifier failed. Document the failure modes and the operator's decision (extend validation, revert, pivot).

## 8. Follow-up tasks

- _Any TASK-FIX-* tasks filed for issues discovered during the run._
- _Any TASK-REV-* tasks if the orchestrator surfaces a class-of-defect worth a review._

## 9. References

- Parent task: [TASK-HMIG-010](../../../tasks/in_progress/TASK-HMIG-010-full-feature-autobuild-validation.md)
- Parent review: [TASK-REV-HMIG](../../../.claude/reviews/TASK-REV-HMIG-review-report.md) §11 (falsifier), §7.3 (Wave 3 sequencing), §5.10 (failure-rate asymmetry)
- Canary precedent: [TASK-HMIG-009A](../../../tasks/completed/TASK-HMIG-009A-partial-canary-no-preloop-backlog-tasks.md), [canary-analysis.md](canary-analysis.md) §8
- Feature-target picks: [`.guardkit/autobuild/TASK-REV-HMIG-feature-target.json`](../../../.guardkit/autobuild/TASK-REV-HMIG-feature-target.json)
- Per-task results: [`.guardkit/autobuild/TASK-REV-HMIG-feature-results.json`](../../../.guardkit/autobuild/TASK-REV-HMIG-feature-results.json)
- Incidents log: [feature-run-incidents.md](feature-run-incidents.md)

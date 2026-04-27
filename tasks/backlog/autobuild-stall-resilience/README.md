# autobuild-stall-resilience (FEAT-ABSR-9C6E)

**Parent review**: [TASK-REV-FA04](../../../.claude/reviews/TASK-REV-FA04-report.md)
**Origin incident**: Jarvis FEAT-J004-702C / TASK-J004-004 `unrecoverable_stall` (2026-04-27)
**Hash signature of the failing-feedback loop**: `9c6e2dee` (referenced in feature_id)
**Tight deadline**: DDD South West.

## Problem (one-paragraph summary)

`guardkit autobuild feature FEAT-J004-702C` against the Jarvis repo terminated with `UNRECOVERABLE_STALL` after Wave 1 of 7. Three of four Wave-1 tasks ran in `direct` mode and succeeded in 1 turn each; **TASK-J004-004** (`task_type=declarative`, `implementation_mode=task-work`, Pydantic routing-history schema) ran 3 Player+Coach turns producing identical Coach feedback — the same `failure_classification=infrastructure / failure_confidence=ambiguous` signature each turn — and was killed by the feedback-stall detector after 33 minutes. The actual cause was an environment mismatch (`/usr/local/bin/python3` is 3.14 on the user's Mac; Jarvis's `pyproject.toml` declares `requires-python='>=3.12,<3.13'`). Bootstrap silently continued past the mismatch (`bootstrap_failure_mode` defaults to `warn`), Wave 1 ran on a broken environment, and `import jarvis` failed in Coach's independent test verification. The Player had no actionable path because no code change can fix `import jarvis` when there's no editable install. The post-loop hint suggested "Review task_type classification" — the wrong diagnosis entirely.

The same broken bootstrap had been silent for every Mac-side Jarvis run since 3.14 became default; FEAT-J002 succeeded only because **all** its tasks ran in `direct` mode (which bypasses the Coach independent-test gate). FEAT-J004-702C is the **first** Jarvis feature to mix `direct` + `task-work`, and TASK-J004-004 is the **first** task to combine `task_type=declarative` + `implementation_mode=task-work` + a regression test that does `subprocess.run([python, "-c", "import jarvis"])`. That four-way intersection opened the trapdoor.

## Solution Approach (in one paragraph)

Close the incident class with **two complementary safety nets** scoped to GuardKit:

1. **Preflight prevention** (TASK-ABSR-A1B2 + TASK-ABSR-C3D4): smart-default `bootstrap_failure_mode` to `block` when any manifest declares `requires-python`, and replace the misleading stall hint with an environment-aware diagnostic naming the actual interpreter, the manifest constraint, and the `uv`/`pyenv`/`conda` remediation. After this, doomed runs abort at preflight with one minute of wall time, not 33 minutes.

2. **In-loop fallback** (TASK-ABSR-2468): if the user explicitly opts into `bootstrap_failure_mode: warn`, the Coach gains a narrow conditional-approval branch for `infrastructure/ambiguous + all-gates-passed + bootstrap-known-broken` so that Player work that is correct gets approved with an environment flag rather than trapped in a feedback stall.

Plus three quality-of-life improvements: standardise the LangChain DeepAgents template `requires-python` to `>=3.11` (open upper bound, matching forge/study-tutor/agentic-dataset-factory/specialist-agent — Jarvis is the lone outlier today) and document the portfolio pinning guide (TASK-ABSR-E5F6); investigate why Player tests passed when Coach's identical pytest command failed (TASK-ABSR-7890); and stop firing the agent-invocations Phase-3 advisory on declarative tasks where no Phase-3 specialist is meaningful (TASK-ABSR-1357).

## Subtasks (6 tasks across 2 waves)

| Wave | ID | Title | Mode | Complexity |
|---|---|---|---|---|
| 1 | [TASK-ABSR-A1B2](TASK-ABSR-A1B2-bootstrap-block-smart-default.md) | Smart-default `bootstrap_failure_mode` to `block` when `requires-python` declared | task-work | 4 |
| 1 | [TASK-ABSR-C3D4](TASK-ABSR-C3D4-environment-stall-subtype.md) | Add `environment_stall` sub-type with env-aware diagnostic | task-work | 5 |
| 1 | [TASK-ABSR-E5F6](TASK-ABSR-E5F6-template-pin-portfolio-standardisation.md) | Standardise DeepAgents template `requires-python` + portfolio guide | direct | 2 |
| 1 | [TASK-ABSR-7890](TASK-ABSR-7890-investigate-player-coach-test-divergence.md) | Investigate Player↔Coach test divergence (review) | direct | 3 |
| 2 | [TASK-ABSR-2468](TASK-ABSR-2468-coach-env-conditional-approval.md) | Coach conditional-approval for environment-class infra failures | task-work | 6 |
| 2 | [TASK-ABSR-1357](TASK-ABSR-1357-suppress-declarative-phase3-advisory.md) | Suppress declarative-task Phase-3 advisory | task-work | 3 |

## Out-of-scope reminder

Per the TASK-REV-FA04 task brief, no changes to the Jarvis repo are filed here. The recommendation to align Jarvis's `requires-python` to `>=3.11` (matching the rest of the portfolio) has been **verified actionable as of 2026-04-27** — `nats-core` PyPI now declares `>=3.10`, so the original Jarvis tight-pin rationale is obsolete. See [IMPLEMENTATION-GUIDE.md → Out-of-Scope: Jarvis-side pin alignment](IMPLEMENTATION-GUIDE.md#out-of-scope-jarvis-side-pin-alignment-consumer-recommendation--verified-2026-04-27) for the exact diff and verification recipe.

## Quick links

- [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md) — wave plan, dependencies, test strategy, replay recipe
- [TASK-REV-FA04 review report](../../../.claude/reviews/TASK-REV-FA04-report.md) — full diagnostic with C4 diagrams, sequence trace, regression analysis

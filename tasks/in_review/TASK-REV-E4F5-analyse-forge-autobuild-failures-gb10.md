---
id: TASK-REV-E4F5
title: Analyse forge FEAT-FORGE-002 autobuild failures on GB10 post-BDD-wireup
status: review_complete
task_type: review
review_mode: architectural
review_depth: standard
created: 2026-04-24T00:00:00Z
updated: 2026-04-24T12:50:00Z
priority: high
tags: [autobuild, review, sdk, claude-agent-sdk, feedback-stall, environment-bootstrap, gb10, bdd-acceptance]
complexity: 0
review_artifacts:
  - docs/reviews/bdd-acceptance-wired-up/forge-run-1.md
  - docs/reviews/bdd-acceptance-wired-up/forge-run-2.md
review_results:
  mode: architectural
  depth: standard
  score: 68
  findings_count: 9
  recommendations_count: 7
  decision: infrastructure_plus_defensive_fix
  report_path: .claude/reviews/TASK-REV-E4F5-review-report.md
  completed_at: 2026-04-24T12:50:00Z
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Analyse forge FEAT-FORGE-002 autobuild failures on GB10 post-BDD-wireup

## Description

Two consecutive `guardkit autobuild feature FEAT-FORGE-002` runs on the **GB10 host** (`promaxgb10-41b1`) both terminated in `UNRECOVERABLE_STALL` after 3 turns on Wave 1 (`TASK-NFI-001`, `TASK-NFI-002`). The same GuardKit orchestrator is simultaneously running **FEAT-J002 (jarvis repo) cleanly on the user's macbook** — so the failure is specific to this host / this repo / this point-in-time build, not a general regression.

Context:
- GB10 was freshly updated: latest `guardkit` main pulled, `./installer/scripts/install.sh` re-run.
- BDD acceptance-test wire-up was merged recently; Wave 1 of FEAT-FORGE-002 runs against that changed surface.
- Between Run 1 and Run 2 the user started Claude Code interactively and logged in — so Run 1 and Run 2 exercise **different SDK auth/version states**.

Primary goal: determine whether the failure mode is (a) environmental on GB10, (b) a regression from the BDD acceptance wire-up, (c) a `claude-agent-sdk` version/auth problem, or (d) a gap in AutoBuild's handling of persistent Player-invocation errors — and recommend remediation.

## Review Artifacts

- `docs/reviews/bdd-acceptance-wired-up/forge-run-1.md` (754 lines — pre-login run)
- `docs/reviews/bdd-acceptance-wired-up/forge-run-2.md` (741 lines — post-login run)

## Observed Failure Signatures

### Run 1 — `authentication_failed`

Every Player turn (1, 2, 3) on both parallel tasks failed with:

```
Player failed: Unexpected error: SDK invocation failed for player:
Agent player received API error: authentication_failed
```

→ consistent with the user's note that **Claude Code was not yet logged in** on GB10 at the time of this run.

### Run 2 — `Unknown message type: rate_limit_event`

After interactive `claude` login, every Player turn failed with a **different** error:

```
Player failed: Unexpected error: SDK invocation failed for player:
Unknown message type: rate_limit_event
```

This is an SDK-side parse failure on a message type the API now emits but the installed `claude-agent-sdk` build on GB10 doesn't recognise. This is **not** an auth problem and is independent of whether credentials are valid.

### Shared downstream mechanism (both runs)

In both runs the same AutoBuild codepath produces the stall:

1. Player errors → no player report → `State recovery succeeded via player_report: 0 files, 0 tests (failing)`.
2. `[Turn N] Building synthetic report: 0 files created, 0 files modified, 0 tests. Generating git-analysis promises for declarative task.`
3. `Synthetic report has no completion_promises — all criteria marked unmet`.
4. Coach emits identical feedback (same signature) 3 turns running, 0/8 or 0/7 criteria verified.
5. `Feedback stall: identical feedback (sig=...) for 3 turns with 0 criteria passing` → `UNRECOVERABLE_STALL`.

The feedback-stall detector **is doing the right thing** (not burning turns on an unrecoverable Player) but the termination message (`Suggested action: Review task_type classification and acceptance criteria.`) **misattributes the root cause** — the task is fine; the Player never actually ran.

### Secondary signal — environment bootstrap

Both runs also show:

```
WARNING:guardkit.orchestrator.environment_bootstrap:PEP 668 retry failed for python (pyproject.toml) with exit code 1:
ERROR: Ignored the following versions that require a different python version:
       0.1.0 Requires-Python >=3.13; 0.2.0 Requires-Python >=3.13
ERROR: Could not find a version that satisfies the requirement nats-core<0.3,>=0.2.0
⚠ Environment bootstrap partial: 0/1 succeeded
```

`forge` requires Python ≥3.13 (per `nats-core`) but bootstrap resolves to `/usr/bin/python3` on GB10 which is older. Execution continues despite the bootstrap being effectively a no-op. Worth assessing whether this is a contributing factor or just noise — in principle Player failure happens before the venv would be exercised, so this is likely orthogonal but should be explicitly confirmed.

## Review Questions

1. **Is Run 2's `rate_limit_event` error a known `claude-agent-sdk` version-skew issue?** The macbook works — what SDK version is installed there vs. GB10? Does `./installer/scripts/install.sh` pin the SDK, or does it resolve to whatever `pip` finds on that host? Is an SDK upgrade on GB10 the fix?
2. **Does the `agent_invoker` / Player codepath handle unknown SDK message types gracefully?** Currently an unknown message type aborts the whole turn with a generic "SDK invocation failed" string, which then triggers the synthetic-report / feedback-stall cascade. Should the SDK client drop unknown messages with a warning instead of raising?
3. **Is the BDD acceptance wire-up a contributing factor?** Wave 1 tasks (`TASK-NFI-001` extending `forge.yaml` config, `TASK-NFI-002` defining `FORGE_MANIFEST`) themselves are not BDD-specific — they're declarative tasks. But confirm the recent change doesn't alter the Player prompt or tool manifest in a way that pushes a borderline SDK build into this error.
4. **Feedback-stall exit path diagnostics.** When `UNRECOVERABLE_STALL` is caused by 3 × Player-error (not 3 × Coach-rejection), the user-facing message is misleading. Should the stall summary distinguish `player_invocation_stall` vs. `coach_feedback_stall` and surface the raw SDK error at the top of the summary?
5. **GB10-specific install path.** Anything in `./installer/scripts/install.sh` that behaves differently on ARM / Ubuntu / an existing install being updated in place? Is there residual state on GB10 (`~/.claude/`, cached SDK, stale venv) that would survive `install.sh` and cause the divergence from macbook?
6. **Python 3.13 bootstrap gap.** Should `guardkit.orchestrator.environment_bootstrap` hard-fail (or at least loudly warn at the top-of-run summary) when `Environment bootstrap partial: 0/N succeeded` rather than silently proceeding to the Player loop?

## Acceptance Criteria

- [ ] Root cause identified for Run 1 (`authentication_failed`) — confirmed to be pre-login state and reproducibly fixed by `claude` login, OR identified as a deeper auth-path issue.
- [ ] Root cause identified for Run 2 (`rate_limit_event`) — with the specific `claude-agent-sdk` version on GB10 vs. macbook noted, and a concrete remediation (upgrade / pin / patch) recommended.
- [ ] Assessment of whether the BDD acceptance wire-up contributes to either failure (likely no — confirm or refute).
- [ ] Assessment of whether the Python 3.13 environment-bootstrap failure is causal, contributory, or orthogonal.
- [ ] Recommendation on whether the SDK message-type unknown case should be handled defensively (drop + warn) rather than raising to the orchestrator.
- [ ] Recommendation on whether `UNRECOVERABLE_STALL` diagnostics should distinguish Player-invocation-stall from Coach-feedback-stall.
- [ ] Recommendation on whether `environment_bootstrap` should gate Player execution when 0/N installs succeed.
- [ ] Concrete next-step tasks proposed (and prefix-tagged) for any fixes the review recommends implementing.

## Key Data Points

| Metric | Run 1 | Run 2 |
|---|---|---|
| Host | GB10 (`promaxgb10-41b1`) | GB10 (`promaxgb10-41b1`) |
| Feature | FEAT-FORGE-002 "NATS Fleet Integration" | FEAT-FORGE-002 "NATS Fleet Integration" |
| Wave 1 tasks | TASK-NFI-001, TASK-NFI-002 (parallel=2) | TASK-NFI-001, TASK-NFI-002 (parallel=2) |
| Duration | 3s | 31s |
| Total turns | 6 | 6 |
| Clean executions | 0/2 | 0/2 |
| State recoveries | 2/2 (100%) | 2/2 (100%) |
| Player error | `authentication_failed` | `Unknown message type: rate_limit_event` |
| Terminal decision | `UNRECOVERABLE_STALL` ×2 | `UNRECOVERABLE_STALL` ×2 |
| Env bootstrap | Partial 0/1 (Python 3.13 missing) | Partial 0/1 (Python 3.13 missing) |
| FalkorDB preflight | Passed | Passed |
| Graphiti context load | OK (RecursionError warnings in edge_fulltext_search) | OK |

**Reference (working baseline):** autobuild run for `jarvis` repo, `FEAT-J002`, on macbook — runs cleanly with the same GuardKit main.

## Out of Scope

- Fixing the issues. This is a review/analysis task only — it terminates at `/task-review` checkpoint and produces a report plus a recommended implementation task (to be created separately if the [I]mplement decision is taken).
- Re-running autobuild on GB10. Evidence is the two captured transcripts; no new runs are to be triggered as part of the review.

## Notes

- Review this with `/task-review TASK-REV-E4F5 --mode=architectural --depth=standard`.
- Paired Graphiti context groups: `product_knowledge`, `command_workflows`, `architecture_decisions`, `guardkit__project_architecture`, `guardkit__project_decisions`, `guardkit__task_outcomes`. Search for prior autobuild stall reviews (TASK-REV-50E1, TASK-REV-8A08, TASK-REV-8B3A) — several cover related feedback-stall / synthetic-report territory and may already answer question 4.

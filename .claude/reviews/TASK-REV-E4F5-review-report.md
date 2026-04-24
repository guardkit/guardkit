---
review_id: TASK-REV-E4F5
title: Forge FEAT-FORGE-002 AutoBuild failures on GB10 post-BDD-wireup
mode: architectural
depth: standard
date: 2026-04-24
score: 68
findings_count: 9
recommendations_count: 7
decision: infrastructure_plus_defensive_fix
artifacts:
  - docs/reviews/bdd-acceptance-wired-up/forge-run-1.md
  - docs/reviews/bdd-acceptance-wired-up/forge-run-2.md
prior_art:
  - TASK-REV-8A08  # FEAT-486D stall, same class-of-defect (5 turns, "SDK stream error: unknown")
  - TASK-REV-50E1  # separate: async teardown
  - TASK-REV-8B3A  # separate: Graphiti OpenAI rate-limit
related_rules:
  - .claude/rules/namespace-hygiene.md
  - "runner-without-producer anti-pattern (Graphiti uuid 184731b0-...)"
---

# Review: Forge FEAT-FORGE-002 AutoBuild failures on GB10 post-BDD-wireup

## Executive Summary

Two consecutive `guardkit autobuild feature FEAT-FORGE-002` runs on GB10 both ended in
`UNRECOVERABLE_STALL` after 3 turns on Wave 1 (`TASK-NFI-001`, `TASK-NFI-002`). The
Player never ran — every turn aborted inside the SDK layer before any implementation
work was attempted. The feedback-stall detector then correctly refused to burn more
turns, but the user-facing summary blamed the task ("Review task_type classification
and acceptance criteria"), which is wrong: the task was fine.

Root causes, ranked:

1. **Run 1 — pre-login auth state on GB10.** Confirmed by the user's own report that
   `claude` was not yet logged in on that host. Reproducibly fixed by the interactive
   login between Run 1 and Run 2.
2. **Run 2 — `claude-agent-sdk` version skew.** The installed SDK on GB10 cannot parse
   the `rate_limit_event` message type that the API now streams. This is an
   SDK-upstream issue, not a guardkit bug, but guardkit's unpinned `>=0.1.0`
   constraint made it possible. A fresh/re-run of `install.sh` does **not** upgrade
   an already-installed SDK (no `--upgrade` flag), so GB10 is left with whatever
   SDK version it happened to resolve to at first install, which is out of step with
   the API.
3. **Diagnostics gap — amplifier.** AutoBuild *has* the signal it needs to say
   "3× Player-invocation error" vs. "3× Coach-rejection," but the final summary
   only inspects Coach feedback strings for `"SDK API error"` — which never appears
   in this failure mode because the Coach saw synthetic zero-file reports with
   regular acceptance-criteria misses. So the summary falls through to the
   task-blaming hint.
4. **BDD wire-up is not a contributing factor.** Wave 1 is two declarative tasks
   (`extend forge.yaml`, `define FORGE_MANIFEST`) — no BDD surface, no agent-prompt
   changes visible in the transcripts, no path by which this would push a borderline
   SDK into the `rate_limit_event` case.
5. **Python 3.13 bootstrap failure is orthogonal to this incident but is a latent
   foot-gun.** Player never ran, so the venv-that-wasn't was never exercised. But
   Coach runs `pytest` against whatever `python3` is on PATH with zero awareness of
   bootstrap state — so had Player succeeded, Coach would have verified against the
   wrong interpreter (3.12 instead of 3.13). This is the same class-of-defect as
   [`namespace-hygiene.md`](../../.claude/rules/namespace-hygiene.md): a local
   decision silently coupled to an externally-defined namespace (here, the Python
   executable on PATH). Worth a dedicated fix *independent of this incident*.

Score: 68/100. The failure-handling cascade (agent_invoker → state_recovery →
synthetic_report → feedback_stall) is architecturally sound on the happy path, but
three specific weaknesses compounded into a user experience that misattributes the
root cause.

## Review Details

- **Mode**: architectural
- **Depth**: standard
- **Scope**: error-translation layer (`agent_invoker.py`), stall classification
  (`autobuild.py` final summary), environment bootstrap, SDK version pinning
- **Out of scope**: running new autobuild attempts, fixing the issues (this is
  a review task only)

---

## Findings

### F1 — SDK version is loose-pinned across all three declarations

Three sites declare `claude-agent-sdk>=0.1.0` with no upper bound:

- [pyproject.toml:43](../../pyproject.toml#L43) (`[autobuild]` extra)
- [pyproject.toml:62](../../pyproject.toml#L62) (`[all]` extra)
- [requirements.txt:14](../../requirements.txt#L14)

The installer ([installer/scripts/install.sh:466](../../installer/scripts/install.sh#L466))
runs `pip install -e "$repo_root[autobuild]"` **without `--upgrade`**. On an existing
install that means the SDK version does not change on subsequent `install.sh` runs —
it's whatever the first install resolved. On GB10 that resolved SDK predates the
introduction of `rate_limit_event` on the API; on the macbook it post-dates it.

There is no runtime version logging — grep finds no uses of
`claude_agent_sdk.__version__` or `importlib.metadata.version("claude-agent-sdk")`.
The only audit-trail artifact is [docs/research/player-agent-sdk-audit-v0.1.36.md](../../docs/research/player-agent-sdk-audit-v0.1.36.md),
which was frozen against v0.1.36 (2026-02-13).

**Severity**: High. This is the direct cause of Run 2.

### F2 — The Player-error translation is a catch-all that swallows exception type

In [agent_invoker.py:2303-2319](../../guardkit/orchestrator/agent_invoker.py#L2303-L2319)
(approximate — verified by exploration agent), the exception cascade is:

```
except asyncio.TimeoutError  → SDKTimeoutError
except CLINotFoundError      → AgentInvocationError("CLI not found ...")
except ProcessError          → AgentInvocationError(specific)
except CLIJSONDecodeError    → AgentInvocationError(specific)
except Exception as e        → AgentInvocationError(f"SDK invocation failed for {agent_type}: {e}")
```

Run 2's `Unknown message type: rate_limit_event` is raised from the SDK's streaming
message parser (it's a `ValueError` or similar), hits the blanket `except Exception`,
and loses its exception *type* — only `str(e)` survives. Downstream classification
(feedback-stall hint logic) inspects only the error string, not the exception type
or a stable error code. This is what lets Run 1 and Run 2 look identical to the
stall detector even though their causes are unrelated (auth vs. message-parse).

**Severity**: Medium. The orchestrator *has* the text of the underlying error — it
just doesn't preserve structured category information that the final-summary code
could pattern-match on.

### F3 — Stall classification matches on Coach-feedback text, not on Player-error class

In `autobuild.py` (lines ~4538–4561 per exploration), the stall-summary hint is
chosen by:

```python
if recent_feedback and all("SDK API error" in fb for fb in recent_feedback[-3:]):
    stall_hint = "Stall caused by SDK API errors — check ANTHROPIC_BASE_URL..."
else:
    stall_hint = "Review task_type classification and acceptance criteria."
```

In the FEAT-FORGE-002 runs, the Coach's feedback string is the **acceptance-criteria
miss list** (because the synthetic zero-file report fails every AC), not the string
`"SDK API error"`. So the branch falls through to the task-blaming hint even though
every Player turn on the summary table clearly shows `Player failed: ... SDK
invocation failed for player: ...`.

The orchestrator records the Player error in both the turn record and the
synthetic report's `implementation_notes` and `concerns` fields (exploration
confirmed `original_error` is captured and stored), and `player_result.error` is
non-None when Player invocation failed. So the *information* to detect a
`player_invocation_stall` is present upstream; it's just not consulted at the
final-summary decision point.

**Severity**: Medium. Misdiagnosis at the summary level is exactly the issue
raised in the review task's question 4.

### F4 — Prior art (TASK-REV-8A08) identifies the same class-of-defect

`TASK-REV-8A08` (FEAT-486D / TASK-AD-004 stall, 2026-04-13) was also a Player-never-ran
stall: 5 turns, all `"SDK stream error: unknown"`, all `asyncio` cancel-scope
cancellations. That review decision was `infrastructure_issue` with 6 recommendations.
At that time the current "check `ANTHROPIC_BASE_URL`" hint apparently *did* fire
for that incident because the Coach feedback included the `"SDK API error"`
substring, so the branch worked. In FEAT-FORGE-002 it doesn't, because the failure
mode is "Player can't even start a stream" → synthetic report → Coach feedback is
AC-miss text.

This is the second incident of the class "Player invocation systematically errored
and the orchestrator misnamed the problem at the summary level." One-off was
infrastructure; two-offs justifies a structural fix in the orchestrator.

**Severity**: Medium. Elevates F3 from "nice to have" to "structural pattern."

### F5 — No SDK version logged at startup

Confirmed by exploration: no `__version__` log, no doctor-time version check. When
a failure like Run 2 hits, the user has no in-log signal of which SDK is installed;
they must leave the shell, `pip show claude-agent-sdk`, and cross-reference.

**Severity**: Low-medium. A one-line log would have made Run 2 self-diagnosing.

### F6 — Bootstrap reports failure but never gates

[feature_orchestrator.py:713-726](../../guardkit/orchestrator/feature_orchestrator.py#L713-L726)
and the inter-wave call at [feature_orchestrator.py:1330-1360](../../guardkit/orchestrator/feature_orchestrator.py#L1330-L1360)
both call `self._bootstrap_environment(worktree)` and **discard the return value**.
The only effect of `0/N succeeded` is a yellow-`⚠` console line. There is no
config knob (`strict_bootstrap`, `bootstrap_required`, etc.) — confirmed by grep.

For the FEAT-FORGE-002 incident this is not causal (Player failed before the venv
was exercised), but it is a latent foot-gun: the forge project is declared with
Python ≥3.13, bootstrap cannot satisfy that, yet the run proceeds.

**Severity**: Low for *this* incident. High as a latent hazard independent of
this review (class-of-defect match to namespace-hygiene rule — local decision
coupled to externally-defined namespace, here the Python interpreter).

### F7 — Coach runs pytest against PATH, not against bootstrap venv

[coach_verification.py:~260-299](../../guardkit/orchestrator/coach_verification.py)
invokes `subprocess.run(["pytest", ...], cwd=worktree_path, ...)`. There is no
wiring from `EnvironmentBootstrapper.venv_python` / `.guardkit/bootstrap_state.json`
into the test command. If bootstrap created `.guardkit/venv/bin/python` with the
right interpreter and packages, Coach ignores it.

This is adjacent to F6: even if F6 were "bootstrap warns but proceeds is fine,"
Coach still silently validates against the wrong environment when the worktree's
PATH Python differs from the bootstrap-intended one.

**Severity**: Medium as a latent hazard; not causal for this incident.

### F8 — SDK namespace hygiene already fixed (TASK-REV-MCPS closed)

Recent commit `3ccd067c refactor(autobuild): rename installer/core/lib/mcp/ →
context7/` (2026-04-24) removed the `mcp`-namespace shadow that was breaking
AutoBuild per [.claude/rules/namespace-hygiene.md](../../.claude/rules/namespace-hygiene.md).
Confirmed by the Run 1/Run 2 logs: the Player *does* reach the SDK streaming
loop — i.e. the import succeeds — and fails *inside* streaming, not at
import. So this is not a namespace-shadow regression; namespace-hygiene rule is
not triggered for F1–F3.

**Severity**: N/A (confirms a null result).

### F9 — BDD acceptance wire-up not implicated

Wave 1 tasks TASK-NFI-001 (extend `forge.yaml`) and TASK-NFI-002 (define
`FORGE_MANIFEST`) are declarative config tasks. Their frontmatter sets
`implementation_mode: direct` and Coach quality-gate profile `declarative`
(both visible in Run 1 line 171–173, 183–185; Run 1 line 239). Neither loads a
BDD runner nor modifies the Player prompt surface. The synthetic-report path
and the AC-miss list are identical in structure to prior declarative-task
failures (e.g. TASK-REV-8A08's TASK-AD-004). No evidence in the transcripts
that the recent BDD wire-up touches this codepath.

**Severity**: N/A (confirms a null result).

---

## Answers to the Task's Review Questions

| # | Question | Answer |
|---|----------|--------|
| 1 | Is Run 2's `rate_limit_event` a known SDK version-skew issue? | Almost certainly. Guardkit pins `>=0.1.0` only; installer doesn't `--upgrade`. Macbook has a newer SDK than GB10. Fix on GB10: `pip install -U claude-agent-sdk` inside the same Python env the `guardkit` CLI uses. Structural fix: F1 recommendations below. |
| 2 | Does `agent_invoker` handle unknown SDK message types gracefully? | No. Blanket `except Exception` wraps the parse error as an opaque "SDK invocation failed." See F2. |
| 3 | Is the BDD acceptance wire-up a contributing factor? | No. See F9. |
| 4 | Should stall diagnostics distinguish player-invocation vs. coach-feedback stalls? | Yes, and the signal is already captured — just not consulted at summary-time. See F3 + F4. |
| 5 | GB10-specific install path divergence? | No platform-specific install logic. The divergence is "first-install resolution freeze" + no `--upgrade` on re-install. See F1. |
| 6 | Should `environment_bootstrap` hard-fail on 0/N succeeded? | Yes, with a config knob (default still warn for backwards compat). See F6 + F7. |

---

## Recommendations

Prioritized by impact / risk. Each is proposed as a concrete task; tags in `[ ]`.

### R1 — Pin `claude-agent-sdk` to a known-good band; log the version at startup  `[TASK-FIX]`

Ranked: **highest**. Directly addresses Run 2.

- Move `claude-agent-sdk>=0.1.0` → `claude-agent-sdk>=0.1.X,<0.2` (or the current
  compatibility floor that parses `rate_limit_event`), in all three declarations
  (F1). Exact lower bound TBD by checking upstream release notes — likely the
  first release that added `rate_limit_event` handling. If upstream has not yet
  added it, raise an issue on `anthropics/claude-agent-sdk-python`.
- Add `installer/scripts/install.sh` support for `--upgrade` on re-runs (flag or
  always-upgrade for the `[autobuild]` extra).
- Emit the installed SDK version in `AutoBuildOrchestrator.__init__`:
  `importlib.metadata.version("claude-agent-sdk")`, alongside the existing
  repo/max_turns/mode line. One log line, self-diagnoses F5.

Acceptance: on GB10, a fresh `./installer/scripts/install.sh --upgrade` lifts the
SDK to a version the macbook also has; autobuild startup logs print the version;
a rerun of FEAT-FORGE-002 no longer emits `Unknown message type: rate_limit_event`.

### R2 — Classify stalls at the final-summary layer `[TASK-FIX]`

Ranked: **high**. Directly addresses review question 4, F3, F4.

- At end-of-loop, count player-invocation errors across the last N turns
  (signal is already available via turn records / `player_result.error` /
  synthetic-report `recovery_metadata.detection_method`). If all 3 recent turns
  are `player_invocation_error`, emit decision label
  `player_invocation_stall` (not `unrecoverable_stall`), with hint:
  "Player failed 3× at the SDK layer before producing any work. Underlying
  error (turn N): {quoted first-turn error}. Suggested checks:
  (a) `claude` is logged in on this host, (b) `pip show claude-agent-sdk`
  matches the working environment."
- Keep the existing `coach_feedback_stall` branch (it's correct for the
  case it matches).
- Fall through to today's generic hint only when neither branch applies.

Acceptance: reprocessing the two saved transcripts from this review produces
`player_invocation_stall` (Run 1: auth; Run 2: message-parse) instead of
`unrecoverable_stall (suggested: review task_type)`.

### R3 — Handle unknown SDK message types defensively in the streaming loop  `[TASK-FIX]`

Ranked: **medium**.

- In `agent_invoker._invoke_with_role`, wrap the `async for message in gen`
  iteration with an explicit per-message try/except that, on parse errors,
  **logs-and-drops** unknown message types rather than raising. Trade-off: a
  truly malformed stream that persistently emits unknown types would still
  produce 0-content results, and the R2 classification would label that a
  `player_invocation_stall`. Net effect: a one-off unknown type no longer
  kills the whole turn.
- Add a specific `except ValueError as e` above the blanket `except Exception`
  at line 2316 (preserve `ValueError`'s type in the `AgentInvocationError`
  subclass / metadata). Similarly for any SDK-specific parse exception type
  if the SDK exposes one (`check claude_agent_sdk.__all__`).

Acceptance: with the SDK downgraded one minor (or patched to emit an unknown
message type), Player turn still completes with whatever messages *did* parse;
if nothing parses, classification falls through to R2's `player_invocation_stall`.

### R4 — Make bootstrap a gate when essential stacks fail; wire venv to Coach  `[TASK-FIX]`

Ranked: **medium**. Addresses F6 + F7. Two sub-tasks.

- **R4a**: Add `bootstrap_failure_mode: "block" | "warn"` (default `"warn"` for
  backwards-compat) on `FeatureOrchestrator`. In `_bootstrap_environment`
  callers (feature_orchestrator.py:713-726 and :1330-1360), inspect
  `BootstrapResult.success`; when `block` and `installs_failed > 0` and
  `installs_attempted > 0`, raise `FeatureOrchestrationError` with a summary
  that includes the PEP-668 stderr and the required `requires-python`.
- **R4b**: Pass `BootstrapResult.venv_python` (or read
  `.guardkit/bootstrap_state.json`) into Coach's `_run_tests()` as an
  explicit interpreter; `subprocess.run(["<venv>/bin/python", "-m", "pytest",
  ...])` instead of relying on PATH.

Acceptance: with `bootstrap_failure_mode: "block"` set in `forge`'s
`.guardkit/config.yaml`, a 0/N bootstrap on GB10 (missing Python 3.13) halts
*before* Wave 1 and prints the requires-python diagnostic; the user knows to
install Python 3.13 on the host. With R4b, Coach's pytest uses the bootstrap
venv so test runs are not silently running the wrong interpreter even if a
global `pytest` is on PATH.

### R5 — Runbook note: "If autobuild stalls immediately, check SDK auth + SDK version"  `[TASK-DOC]`

Ranked: low, but cheap. Add to `docs/guides/autobuild-instrumentation-guide.md`
a 3-line preflight table matching R2's two top causes (auth, SDK version skew).
Cross-link from the stall-hint text R2 emits.

### R6 — Seed the class-of-defect into the knowledge graph  `[TASK-DOC]`

Ranked: low. Align with prior `namespace-hygiene.md` / `runner-without-producer`
precedent. Add to `guardkit__project_decisions`:

> "Player-invocation stall (3× SDK error before any work) must be classified
> distinctly from coach-feedback stall at the final-summary layer. Observed
> twice: TASK-REV-8A08 (FEAT-486D, SDK stream timeout) and TASK-REV-E4F5
> (FEAT-FORGE-002, SDK auth + version skew). The orchestrator captures the
> signal in `player_result.error` / synthetic-report `recovery_metadata`
> but does not consult it at summary-time."

Keeps future reviews of similar symptoms from re-deriving the distinction.

### R7 — Consider upstream issue on `claude-agent-sdk` for `rate_limit_event`  `[TASK-DOC]`

Ranked: low. If current PyPI-latest still lacks `rate_limit_event` parsing, file
an issue on `anthropics/claude-agent-sdk-python`. Evidence from the Run 2
transcript (quoted error string, approximate SDK version from `pip show` on
GB10). Out of GuardKit's control, but a cross-link keeps the trail warm.

---

## Decision Matrix

| Option | Speed | Quality | Coverage of root causes | Risk | Recommendation |
|---|---|---|---|---|---|
| A. Just upgrade SDK on GB10 | Fast | Low | Run 2 only | Recurs on next skew | Interim unblock — do this now |
| B. Pin SDK + log version (R1) | Fast | Medium | Run 2 structural | Low | Yes |
| C. B + stall classification (R1+R2) | Medium | High | Run 1 + Run 2 + diagnostics | Low | **Recommended core** |
| D. C + defensive message handling (R1+R2+R3) | Medium | High | All primary + resilience | Low-medium (behaviour change in streaming) | Recommended if SDK upstream is slow |
| E. D + bootstrap gate (R1+R2+R3+R4) | Slow | Highest | All + latent hazards (F6/F7) | Medium (API surface change) | Recommended, but split R4 into a separate feature — it's independent |

**Recommendation**: Option **C** as the implementation target of *this* review
(R1 + R2), with R3 as a stretch goal. R4 should be lifted into its own
follow-up review/task — it is a latent hazard unrelated to this incident's
root cause, and bundling it here dilutes scope.

R5 + R6 are ≤1-hour doc tasks; bundle them with R2.

---

## Implementation Task Proposal (for [I]mplement decision)

If the user chooses `[I]mplement` at checkpoint, the suggested sub-task
breakdown (Wave 1 all parallelisable — they touch disjoint files):

- **Wave 1** (parallel):
  - `TASK-FIX-{hash}` — Pin SDK + version-log at startup (R1)
    — files: `pyproject.toml`, `requirements.txt`, `installer/scripts/install.sh`,
    `guardkit/orchestrator/autobuild.py`
  - `TASK-FIX-{hash}` — Player-invocation-stall classification (R2)
    — file: `guardkit/orchestrator/autobuild.py` (final-summary block ~4538)
  - `TASK-FIX-{hash}` — Defensive SDK message handling + specific
    `except ValueError` above blanket catch (R3) — file:
    `guardkit/orchestrator/agent_invoker.py` (~2303-2319)
- **Wave 2** (sequential — depends on R2 shape):
  - `TASK-DOC-{hash}` — Runbook entry + graph seed (R5 + R6)

`R4` / `R7` deliberately out of scope for the implementation flow from this
review — they should be separate reviews/tasks.

---

## Acceptance Criteria — Task Completion

| AC | Status |
|---|---|
| Root cause Run 1 (`authentication_failed`) identified | ✓ Pre-login state on GB10, confirmed by the user's own note and fixed by the interactive `claude` login between Run 1 and Run 2 |
| Root cause Run 2 (`rate_limit_event`) identified, SDK version recommendation | ✓ Loose-pin SDK + first-install resolution freeze + no `--upgrade` on re-install. Remediation: pin a compatibility band, add `--upgrade`, log version at startup (R1) |
| BDD acceptance wire-up assessment | ✓ Not contributory (F9) |
| Python 3.13 bootstrap assessment | ✓ Orthogonal to this incident but latent foot-gun (F6 + F7) |
| SDK unknown-message-type defensive handling recommendation | ✓ Log-and-drop per-message, add typed catch above blanket (R3) |
| Player-vs-Coach stall distinction recommendation | ✓ Classify at summary layer using `player_result.error` / synthetic `recovery_metadata` (R2) |
| Bootstrap gating recommendation | ✓ Add `bootstrap_failure_mode: block\|warn` + wire venv into Coach (R4) |
| Concrete next-step tasks proposed + tagged | ✓ See Implementation Task Proposal |

---

## Context Used (from exploration)

- **Architecture-layer files inspected**: `guardkit/orchestrator/agent_invoker.py`
  (lines ~2126-2319), `guardkit/orchestrator/autobuild.py` (stall detector
  ~3238-3318, final-summary hint ~4538-4561, synthetic-report builder
  ~2809-2892, state-recovery ~2623-2729), `guardkit/orchestrator/
  environment_bootstrap.py` (full), `guardkit/orchestrator/feature_orchestrator.py`
  (lines 713-726 + 1330-1360 + 978-994), `guardkit/orchestrator/
  coach_verification.py` (`_run_tests` ~239-320), `guardkit/cli/autobuild.py`
  (`_check_sdk_available` 58-79), `installer/scripts/install.sh` (460-516).
- **Dependency declarations**: `pyproject.toml:43,62`, `requirements.txt:14`.
- **Existing audit artifact**: `docs/research/player-agent-sdk-audit-v0.1.36.md`
  (frozen 2026-02-13).
- **Namespace-hygiene**: verified not triggered (Player reaches streaming;
  install.sh rename `mcp/ → context7/` is recent and resolved the previous
  incident).
- **Prior reviews cross-referenced**: TASK-REV-8A08 (closest prior art — same
  class-of-defect), TASK-REV-50E1 (unrelated — async teardown), TASK-REV-8B3A
  (unrelated — Graphiti OpenAI rate-limit).

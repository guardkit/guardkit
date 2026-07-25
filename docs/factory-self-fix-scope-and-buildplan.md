# Factory self-fix — three verification-layer bugs, fixed by the factory · Scope + Build Plan
## For: /feature-spec --auto → /feature-plan → guardkit autobuild (shadow watching)
## Status: ACTIVE 2026-07-25 · Rich's go: "proceed with the build (three fixes)"
## Measurables: M4 integrity (fix A) · M3 spread beyond Python (fix B) · M1 + the no-topology-workarounds law (fix C)

## 1. What and why (one minute)

Three defects found during the 2026-07-25 FEAT-8737 build, each with receipts, each small:
**(A)** shadow receipts are lost when a build run ends right after a verdict — the
fire-and-forget thread dies with the process (SMOKE-001 turn 1 and SMOKE-003 turn 2 receipts
survived only in the queue sink). **(B)** the behavioural-oracle runner only fires on a
Python file convention (`tests/acceptance/*_roundtrip.py` + venv-pytest) — non-Python repos
get NO runtime verification; the cure (`behavioural_oracle.command`, an arbitrary shell
command declared in feature/task YAML) is promised in the guard's docstring and unimplemented.
**(C)** task-work coach evidence bundles reached 109,634 tokens and overflowed the normal
checker seat's crash-tested 98,304 window — the per-tool-result gather cap (12k chars) exists
but the synthesis prompt has NO overall budget; the wrong workaround (swapping the coach
model) is now banned, so the input must fit the seat.

## 2. Deliverables (all in this repo)

**Fix A — durable shadow receipts** (`guardkit/qa/qav_shadow.py` + the seam in
`guardkit/orchestrator/autobuild.py`): the receipt write must survive the process ending
immediately after a verdict. Direction: make the shadow thread non-daemon (its existing 60s
seat timeout is the natural bound) OR a bounded join at orchestration finalize — the Player
picks the smaller honest change. Laws preserved verbatim: flag-OFF = provable no-op; never
raises; never blocks or delays the VERDICT itself; absent-not-fail.

**Fix B — `behavioural_oracle.command`** (`guardkit/orchestrator/quality_gates/coach_validator.py`,
producer `_produce_behavioural_oracle`): when NO `tests/acceptance/*_roundtrip.py` artefact
exists in the worktree AND the feature/task YAML declares `behavioural_oracle.command`, run
that command via shell in the worktree root under the existing `GUARDKIT_ORACLE_TIMEOUT`
budget and produce the exact same result shape (`status: ran`, `passed` = exit 0, exit_code,
duration, timed_out, output_tail, provenance naming the command and its YAML origin). The
file-glob path is unchanged and takes precedence. A command from committed YAML is operator
policy — never `not_independent`. This is the stack-agnosticism cure: the command can be
`go test ./...`, `npm run smoke`, anything.

**Fix C — a synthesis-prompt budget for task-work bundles** (`guardkit/orchestrator/agent_invoker.py`,
the coach synthesis prompt build): FIRST investigate where the 109k came from (the receipt:
api_test FEAT-8737 TASK-SMOKE-002 turn-1 coach 400, `n_prompt_tokens: 109634` — which bundle
fields carried the bulk), THEN enforce an overall character budget on the rendered synthesis
prompt — env-tunable (`GUARDKIT_COACH_SYNTHESIS_MAX_CHARS`), default sized to fit the 98,304
seat with real margin (≈300,000 chars). Truncation must be LOUD, never silent: a visible
truncation notice inside the prompt naming what was cut, plus a WARNING log
(absence-of-failure-is-not-success law).

## 3. Binding constraints

- Normal coach topology only: this build runs Player `qwen36-workhorse` + Coach
  `gemma4-coach`. No model swaps for any reason — if a bundle overflows mid-build, that
  failure is honest evidence for fix C and the turn retries after C lands.
- No behavioural change to any verdict path beyond the three fixes; every existing lane test
  stays green; zero net-new suite failures vs main.
- Every fix ships with hermetic tests (no docker, no network, no live seats): A — a slow fake
  seat + immediate-return simulation proves the receipt still lands; B — fake commands
  (exit 0 / exit 1 / sleep-past-timeout) prove ran/failed/timed-out shapes; C — an oversized
  synthetic bundle proves the rendered prompt respects the budget and carries the notice.
- All modified files pass project-configured lint with zero errors.

## 4. Command playbook

```
/feature-spec "Factory self-fix: durable shadow receipts (non-daemon/bounded-join), behavioural_oracle.command for non-Python repos (same result shape, file-glob precedence, loud timeout), and a loud env-tunable synthesis-prompt budget so task-work bundles fit the 98304 coach seat, per docs/factory-self-fix-scope-and-buildplan.md §2-§3" \
  --context docs/factory-self-fix-scope-and-buildplan.md --auto

/feature-plan "Factory self-fix (three verification-layer bugs)" \
  --context features/<slug>/<slug>_summary.md \
  --context docs/factory-self-fix-scope-and-buildplan.md

OPENAI_BASE_URL=http://localhost:9000/v1 OPENAI_API_KEY=dummy \
GUARDKIT_COACH_GATHER_MAX_TOOL_RESULT_CHARS=6000 \
guardkit autobuild feature FEAT-XXXX --verbose --max-turns 30 \
  --model qwen36-workhorse --coach-model gemma4-coach
```

(The tightened gather env var for THIS run is an operator dial on the input, not a topology
change — the permanent fix is C itself.)

## 5. Done means

All three fixes merged with: lane suites green (`tests/qa/test_qav_shadow.py`,
`tests/orchestrator/test_behavioural_oracle_guard.py`, `test_behavioural_oracle_producer.py`
+ new tests), zero net-new failures on the full suite vs main by the coordinator's own
re-drive, and fix B additionally proven by hand: a scratch worktree with a YAML-declared
command produces a populated `behavioural_oracle` with no Python test file present.

## Status Log

| step | status | date | commit |
|---|---|---|---|
| scope+buildplan | ACTIVE | 2026-07-25 | — |

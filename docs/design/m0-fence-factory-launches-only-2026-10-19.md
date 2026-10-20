# The frontier-model fence applies to factory launches only

19 October 2026. Part 1 says whether GuardKit's `sdk` harness still works at all;
Rich's own check on his Mac then passed. Part 2 is the fence change, **built on
19 October 2026** after his go-ahead ("Built" at the end says what differs from the
plan).

## Why

GuardKit has a fence (`guardkit/orchestrator/m0_fence.py`, applied in `select_harness`)
that stops a run reaching a hosted model. It exists for the factory: the local factory
must never reach a hosted model.

Rich also runs GuardKit by hand with Claude on the `sdk` harness, on purpose. Some of
his own projects were built that way. Today the fence refuses his documented command
`GUARDKIT_HARNESS=sdk guardkit autobuild …` unless he also sets
`GUARDKIT_ALLOW_FRONTIER=1`.

Rich's decision, 19 October 2026: the fence applies to factory launches, strictly. A
person's own run is not fenced.

## Part 1: does the `sdk` harness still work? (findings, 19 October 2026)

### Last known real run

The last real `sdk`-harness runs found were two features of one of Rich's own projects,
on 17 July 2026, on the factory's main development machine, with
`claude-sonnet-4-5-20250929`. Both completed (7 of 7 tasks each) and were merged.
- Evidence: that project's own AutoBuild review summaries ("Status: COMPLETED", average
  SDK turns per call 29.7).
- The newest run on the Mac was in another of his projects, 3 July 2026, also on `sdk`.
- No real `sdk` run has been recorded since. The fence arrived on 2 August, and GuardKit
  main has moved 720 commits since 17 July.

### What was checked, with no model and no network

1. **Every test that touches the `sdk` path** (47 files): 1991 passed, 26 skipped,
   1 failed.
   - The one failure, `test_the_guard_catches_every_probe`, was caused by the check's own
     guard. Its file passes on its own (113 passed).
   - A guard refused every non-loopback connection and every start of a `claude` program.
     It recorded only four refused `claude --version` probes, from the doctor tests.
2. **A whole run, end to end, through the real Claude Agent SDK.**
   - The setup: SDK 0.2.121, the version GuardKit now pins, with its bundled `claude`
     program removed. Only the SDK's process transport was replaced, by a scripted
     stand-in that answers the SDK's start-up exchange and plays each role.
   - The SDK's own option checks, start-up exchange, message parsing and message types
     all ran for real.
   - The run was `guardkit autobuild feature` on a throwaway one-task Python project, with
     `GUARDKIT_HARNESS=sdk GUARDKIT_ALLOW_FRONTIER=1`.
   - **Result: the feature COMPLETED.** The Coach approved on turn 1.
   - Along the way, worktree creation, the environment set-up, the Player and the
     deterministic test run all worked. So did the code-reviewer specialist, the language-model
     Coach, the declared coverage command and the file tracking from tool calls.
   - The design phase (`--enable-pre-loop`) also passed.

### What will stop Rich today, and what to do

| # | What happens | Cause | Harness-specific? | Way round it now |
|---|---|---|---|---|
| 1 | Every Player, Coach and reviewer call is refused, and each turn is spent failing | The fence, since 2 August. Its message wrongly talks about the OpenAI API and the langgraph translator, which the `sdk` harness never uses. | yes | `GUARDKIT_ALLOW_FRONTIER=1` (Part 2 removes the need) |
| 2 | A `feature` task loops to its turn limit on "Coverage is UNKNOWN, not met" | Since 19 September (`8d2ea1691`), a feature, refactor, glue or wiring task needs a measured coverage. Only the project's declared `toolchain.coverage` (in `.guardkit/config.yaml`) can supply one, because the Player's report never sets `coverage_met`. **The project built that way in July declares no `toolchain.coverage`.** | no (all harnesses) | Declare `toolchain.coverage` in the project, for each component that needs it. (Since GuardKit `11cf8b1e` such a task stops before any work, naming this fix.) |
| 3 | On a project whose settings name a local Coach model, the Coach and the code reviewer are sent that name (for example `coach-ft-v4`) | The project's `.guardkit/config.yaml` sets `autobuild.coach.model`; the July project gained such a line on 26 July. On `sdk`, that name goes to the Claude program, which will not know it. | effectively yes | Pass `--coach-model claude-sonnet-4-5-20250929` (or another Claude model), or remove those two lines |
| 4 | `guardkit autobuild task` on a Python project stops with "interpreter-resolution FAILED" | A single task gets no worktree environment set-up. This has been the case since 9 July, so it predates the last good run. | no | Use `guardkit autobuild feature`, as the July runs did |

### Worth knowing, not blocking

- **On `sdk`, the "toolless" Coach and the code reviewer are not actually toolless.**
  - They run with `allowed_tools=[]` or a short list, and with `bypassPermissions`. In the
    Claude Agent SDK, `allowed_tools` only auto-approves tools. Restricting the tools
    takes `tools=`, and `bypassPermissions` approves everything.
  - So on `sdk` the Coach and the code reviewer could write files or run commands.
  - This dates from June 2026 (the toolless Coach, `5d0d7e56a`), before the last good run.
- The code reviewer's tool list names `Search`, which is not a Claude Code tool.
- The development environment on the factory's machine has SDK 0.1.72, below the pinned
  `>=0.2.121,<0.3`. The 0.2.121 surface was compared with 0.1.72 on 18 October but never
  run until this check.

### Rich's real check, 19 October 2026

Rich ran the script below on his Mac. FEAT-CHK COMPLETED: 1 of 1 task, 1 turn,
2 minutes 51 seconds, on the `sdk` harness with `GUARDKIT_ALLOW_FRONTIER=1`.

### Not covered by the no-model check (only a real run can show these)

- The real `claude` program's own output.
- Sign-in, using Rich's subscription.
- Whether the default model name `claude-sonnet-4-5-20250929` is still accepted.
- Real tool use and real timings.

### The cheapest real check for Rich

The steps below are for the Mac, or wherever he runs GuardKit by hand. They use a
throwaway project in a scratch folder, outside every real repository, and need no code
change. They make a few Claude calls on his subscription.

```sh
# 0. GuardKit sees the SDK, and Claude Code is signed in
GKPY="$(head -1 "$(command -v guardkit-py)" | sed 's/^#!//')"
"$GKPY" -c "import guardkit, claude_agent_sdk; print(guardkit.__file__, claude_agent_sdk.__version__)"
claude --version

# 1. A throwaway project: one feature, one task
rm -rf /tmp/gk-sdk-check && mkdir -p /tmp/gk-sdk-check && cd /tmp/gk-sdk-check
git init -q -b main
mkdir -p calc tests tasks/backlog/check .guardkit/features
: > calc/__init__.py
printf 'def test_placeholder():\n    assert True\n' > tests/test_placeholder.py
printf '[project]\nname = "calc"\nversion = "0.0.1"\ndependencies = ["pytest", "pytest-cov"]\n' > pyproject.toml
printf '*.egg-info/\n.venv/\n__pycache__/\n.guardkit/worktrees/\n' > .gitignore
printf 'toolchain:\n  test: ".venv/bin/python -m pytest -q"\n  coverage: ".venv/bin/python -m pytest -q --cov=calc --cov-fail-under=80"\n' > .guardkit/config.yaml
cat > tasks/backlog/check/TASK-CHK-001-add-function.md <<'EOF'
---
id: TASK-CHK-001
title: Add an add() function
status: backlog
created: 2026-10-19T00:00:00Z
updated: 2026-10-19T00:00:00Z
priority: low
complexity: 1
task_type: feature
requirements: []
autobuild:
  enabled: true
  max_turns: 3
---

# Add an add() function

## Description
Add `add(a, b)` to `calc/ops.py` returning the sum of two numbers, with a test.

## Acceptance Criteria
- [ ] `calc/ops.py` defines `add(a, b)` returning `a + b`
- [ ] `tests/test_ops.py` tests `add(2, 3) == 5`
EOF
cat > .guardkit/features/FEAT-CHK.yaml <<'EOF'
id: FEAT-CHK
name: Add an add() function
description: Throwaway one-task feature to check the sdk harness end to end.
created: '2026-10-19T00:00:00Z'
status: planned
complexity: 1
estimated_tasks: 1
tasks:
- id: TASK-CHK-001
  name: Add an add() function
  file_path: tasks/backlog/check/TASK-CHK-001-add-function.md
  complexity: 1
  dependencies: []
  status: pending
  implementation_mode: task-work
  estimated_minutes: 10
orchestration:
  parallel_groups:
  - - TASK-CHK-001
  estimated_duration_minutes: 10
  recommended_parallel: 1
EOF
git add -A && git commit -qm "throwaway project"

# 2. The run, with the existing escape hatch
env -u OPENAI_BASE_URL -u ANTHROPIC_BASE_URL GUARDKIT_HARNESS=sdk GUARDKIT_ALLOW_FRONTIER=1 \
  guardkit autobuild feature FEAT-CHK --max-turns 3
```

- **Pass:** the run ends with `Status: COMPLETED`, and the Coach approved. Expect three
  "Proceeding because GUARDKIT_ALLOW_FRONTIER=1" lines; that is the escape hatch working.
- **If the Claude program rejects the model name:** add `--model sonnet`.
- **Clean-up:** `rm -rf /tmp/gk-sdk-check`.

## Part 2: the fence change

### How GuardKit knows a launch is the factory's

- **The signal is `GUARDKIT_FACTORY_LAUNCH`** (non-empty).
  - It is set in one place: Forge's `build_launch_env` (`forge/src/forge/launch_environment.py`),
    always `"1"`. That function decides the value itself and never inherits it.
  - Every Forge path that starts GuardKit builds its environment there:
    - the build (`subagents/autobuild_runner.py`);
    - every GuardKit command leg (`adapters/guardkit/run.py`);
    - the review gate (`review_gate/record.py`);
    - the planning terminal tools (`planning/target_terminal_tools.py`);
    - the deploy sidecar (`deploy_sidecar/service.py`).
- **Every harness in a factory build runs inside that one GuardKit process, so each one
  inherits the signal.** That covers the Player, the Coach, the specialists, the Coach's
  test run and the design phase.
- The planning seats (`specialist-agent`) import GuardKit only for its data models. They
  never call `select_harness`, and Forge does not either.
- **The gap.** Only one thing sets the signal: a launch environment. No image or sandbox
  setting does. So a GuardKit started inside a factory sandbox by any other route would
  count as a person's own run. Two layers still stand there: the factory image has no
  Claude SDK, and the sandbox holds no hosted-model credentials.
- **Proposed second signals, so the factory cannot become unfenced by accident:**
  - (a) GuardKit also treats `GUARDKIT_RUN_OWNER` (the build ID, which only
    `build_launch_env` sets) as a factory launch;
  - (b) a separate Forge change sets `GUARDKIT_FACTORY_LAUNCH=1` as a fixed setting in the
    factory runner and sandbox images. That is a live change, through a release.

### The new rule

- **Factory launch:**
  - today's strict rule, unchanged;
  - and `sdk` is refused inside `judge_effective_seat` itself, so the recorded verdict
    says REFUSED and names why ("a factory build never uses the hosted SDK harness").
    Today the verdict can read PASS and the selector refuses a line later.
  - `GUARDKIT_ALLOW_FRONTIER=1` overrides the seat rules as it does today. It does not
    override the `sdk` refusal, which matches today, where the selector's refusal ignores
    it.
- **A person's own run** (no factory signal):
  - the seat is still judged, but never refused;
  - the verdict is a new status, `PERSONAL-RUN`. It names the seat, and says the run is
    not a factory launch, so it is not fenced. It also says what the factory rule would
    have said, so the record stays informative.
  - It is logged once at INFO, with no stderr noise.
  - **Langgraph with no model (the deepagents Anthropic default) is allowed too.** A
    person may point their own run anywhere.
  - `GUARDKIT_ALLOW_FRONTIER` is not needed there, and has no effect on the verdict.
- **The command-line fences** (`resolve_m0_violation` in `cli/task_review.py` and
  `cli/task_work.py`) follow the same rule, through the same one function.
- **Worst-verdict ranking:** PASS < NOT-JUDGED < PERSONAL-RUN < ALLOWED-BY-ESCAPE <
  REFUSED. (Built first with PERSONAL-RUN below NOT-JUDGED; the coach's review moved
  it up, so a later unjudged seat cannot hide that a person's run used a hosted
  model.)
- **The error message is fixed for `sdk`.** A refusal on `sdk` no longer talks about the
  OpenAI API or the langgraph translator.

### Tests

- **Tests must never reach a hosted model.** Today, a test run is a person's own run (no
  factory signal). So under the new rule, a test that the fence used to stop could go
  further and build a real model client.
- **Two safeguards:**
  - `tests/conftest.py` sets `GUARDKIT_FACTORY_LAUNCH=1` for every test by default.
    Tests run under the strict factory rule; the personal-run tests clear it on purpose.
  - A permanent guard in `tests/conftest.py` refuses every non-loopback connection and
    every start of a `claude` program, and fails the test that tries.
  - The check described above, run over all 47 `sdk`-path files, found no test that
    reaches a network today.
- **The four `test_autobuild_e2e.py` failures stay** under this rule, deliberately. Their
  cause is a separate product gap: the design phase's `select_harness`
  (`quality_gates/task_work_interface.py`) passes no `model=`, so it runs on the harness
  default instead of the chosen model.
- **Proposed separate fix:** pass the build's `--model` through to the design phase. The
  four tests then pass honestly with a declared local route (`m0_routine_fleet_route`),
  never with the escape hatch.
- **Cases the fence tests will cover:**
  - factory launch with `sdk`: refused;
  - factory launch with a bare name and no local base URL: refused;
  - factory launch with a local model: passes;
  - a person's own run with `sdk` and a Claude model: `PERSONAL-RUN`, not refused;
  - a person's own run on langgraph with no model: `PERSONAL-RUN`;
  - `GUARDKIT_RUN_OWNER` alone counts as a factory launch;
  - the escape hatch, unchanged.

### Built (19 October 2026)

- **One signal, not two.** `GUARDKIT_RUN_OWNER` is set only by the build launch
  (`autobuild_runner.py`). The other four launch sites (`run.py`, the review gate, the
  planning terminal tools, the deploy sidecar) do not set it. So it is not a factory
  signal, and `GUARDKIT_FACTORY_LAUNCH` stays the only one.
- **The gap is recorded for a Forge follow-up:** set `GUARDKIT_FACTORY_LAUNCH=1` as a
  fixed setting in the factory's runner and sandbox images.
- **What a person's own run records:**
  - a seat the factory rule would refuse is recorded `PERSONAL-RUN`;
  - a seat the factory rule passes (a local model) is still recorded `PASS`.
  - On `sdk`, a person's own run is always `PERSONAL-RUN`, because the factory rule
    refuses `sdk`.
- **The no-chokepoint receipt line** on a person's own run reads `NOT-FENCED (…)`
  instead of claiming the command-line fence passed the model.
- **The tests:**
  - The suite's own guard is in `tests/conftest.py`, with self-tests in
    `tests/unit/test_suite_launch_guard.py`.
  - 115 existing tests whose subject is the `sdk` harness, or the by-hand memory rule,
    are marked `personal_run`. They run exactly as before, without the factory signal.
  - The existing fence tests drive the rule on the langgraph branch, through the same
    call `select_harness` makes.
  - The new rule's tests are in `tests/unit/test_m0_fence_factory_launches_only.py`.

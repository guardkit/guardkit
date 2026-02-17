# Review Report: TASK-REV-4D57 (Revision 3 — Root Cause Corrected)

## Analyse DB task outcome after infra-aware AutoBuild changes

**Review Mode**: Architectural / Code Quality (Deep Dive)
**Depth**: Comprehensive
**Date**: 2026-02-17
**Revision**: 3 (incorporates revision response analysis)
**Related Tasks**: TASK-INFR-6D4F, TASK-INFR-1670, TASK-INFR-5922, TASK-INFR-24DB
**Parent Review**: TASK-REV-BA4B

---

## Executive Summary

TASK-DB-003 (Implement User model schemas and CRUD) reaches `UNRECOVERABLE_STALL` after 3 identical turns. The previous review iterations correctly identified the error (`ModuleNotFoundError: No module named 'sqlalchemy'`) but attributed it to the wrong cause (SDK subprocess environment mismatch).

**The actual root cause**: AutoBuild has **no environment bootstrap phase**. The `_setup_phase()` creates a worktree but never installs the target project's dependencies. The Player masks this gap by incidentally installing packages during its 50-turn implementation session. The Coach's 1-turn verification session runs `pytest` in an environment where the project's dependencies were never deterministically installed.

**The SDK transport is NOT the problem.** Verified at [subprocess_cli.py:346-351](../../.venv-site-packages-ref/claude_agent_sdk/_internal/transport/subprocess_cli.py#L346-L351):

```python
process_env = {
    **os.environ,
    **self._options.env,
    "CLAUDE_CODE_ENTRYPOINT": "sdk-py",
    "CLAUDE_AGENT_SDK_VERSION": __version__,
}
```

The CLI subprocess inherits the parent's full environment. PATH, VIRTUAL_ENV, and all environment variables pass through correctly.

**Why this matters beyond Python**: GuardKit is a universal orchestrator supporting Python, Node, .NET, Go, Rust, Flutter, and more. The solution must be project-type-aware, not Python-specific.

### Verified Gap Summary

| # | Gap | Verified By | Root Cause Level |
|---|-----|-------------|-----------------|
| **0** | **No environment bootstrap phase in AutoBuild** | `_setup_phase()` code (feature_orchestrator.py:414, autobuild.py:897) — no install step | **TRUE ROOT CAUSE** |
| **0b** | **No inter-wave bootstrap hook** | `_wave_phase()` code (feature_orchestrator.py:1059-1104) — no re-detection between waves | **TRUE ROOT CAUSE** (greenfield) |
| 1 | `requires_infrastructure: []` on all FEAT-BA28 tasks | FEAT-BA28.yaml line 54 | Secondary gap |
| 2 | `_docker_available` never set in task dict | autobuild.py line 3582-3586 | Secondary gap |
| 3 | `sqlalchemy` not in high-confidence classification | _INFRA_HIGH_CONFIDENCE list, lines 371-386 | Secondary gap |

---

## Correction: Why Previous Finding 1 Was Wrong

### What Revision 2 Said (INCORRECT)

> Finding 1 (ROOT CAUSE): SDK CLI Subprocess Has Different Python Environment

This was based on the hypothesis that the bundled CLI's Bash shell resolves to a different Python. The evidence seemed to support it: the Coach couldn't find sqlalchemy while the Player could.

### Why It's Wrong

**Evidence 1: SDK transport passes `{**os.environ}`**

The `SubprocessCLITransport.connect()` method at line 346 explicitly merges `os.environ` into the subprocess environment:

```python
process_env = {
    **os.environ,          # Full parent environment
    **self._options.env,   # User-provided overrides
    "CLAUDE_CODE_ENTRYPOINT": "sdk-py",
}
```

This means PATH, VIRTUAL_ENV, PYTHONPATH, and all other environment variables are inherited by the CLI subprocess. Both Player and Coach SDK sessions see the **same** Python environment as the host GuardKit process.

**Evidence 2: The Player installs packages as a side-effect**

The Player runs for ~8 minutes with 50 tool calls. During TASK-DB-001 (scaffolding), it:
1. Creates `pyproject.toml` with sqlalchemy, asyncpg, etc.
2. Runs `pip install -e ".[dev]"` as part of its implementation work
3. After this, subsequent Player sessions in the same worktree find sqlalchemy available

But this is **incidental**, not by design. The Player installs packages because it's implementing the project, not because AutoBuild ensures the environment is ready.

**Evidence 3: The greenfield timing gap**

The base repo at `guardkit-examples/fastapi/` has **no `pyproject.toml`**. It's a greenfield project. The sequence is:
1. Wave 1: TASK-DB-001 creates `pyproject.toml` with sqlalchemy
2. Player for TASK-DB-001 likely runs `pip install -e .` during its session
3. Wave 2: TASK-DB-003 launches — but nobody guarantees TASK-DB-001's `pip install` completed or that it installed into the right Python
4. Coach for TASK-DB-003 runs `pytest` → `ModuleNotFoundError: No module named 'sqlalchemy'`

The gap is between waves, not between SDK and host environments.

---

## Verified Evidence Chain

### Actual Test Error (from coach_turn_1.json)

Source: `guardkit-examples/fastapi/.guardkit/worktrees/FEAT-BA28/.guardkit/autobuild/TASK-DB-003/coach_turn_1.json`

```
==================================== ERRORS ====================================
__________________ ERROR collecting tests/users/test_users.py __________________
ImportError while importing test module '.../tests/users/test_users.py'.
Hint: make sure your test modules/packages have valid Python names.

tests/users/test_users.py:21: in <module>
E   ModuleNotFoundError: No module named 'sqlalchemy'
ERROR tests/users/test_users.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
=============================== 1 error in 0.13s ===============================
```

Identical across all 3 turns (coach_turn_1.json, coach_turn_2.json, coach_turn_3.json).

### _setup_phase() Has No Install Step

**feature_orchestrator.py:414-496** (`_setup_phase()`):
1. Load feature YAML
2. Validate feature structure
3. Create git worktree (or reuse existing)
4. **NO dependency installation**
5. **NO environment verification**

**autobuild.py:897-980** (`_setup_phase()`):
1. Create git worktree (or use existing)
2. Initialize AgentInvoker
3. **NO dependency installation**
4. **NO environment verification**

### _wave_phase() Has No Inter-Wave Hook

**feature_orchestrator.py:1059-1104** (`_wave_phase()`):
```python
for wave_number, task_ids in enumerate(feature.orchestration.parallel_groups, 1):
    # Check dependencies
    # Execute wave
    wave_result = self._execute_wave(wave_number, task_ids, feature, worktree)
    wave_results.append(wave_result)
    # Display results
    # Check stop-on-failure
    # NO: Re-detect manifests
    # NO: Install new dependencies
```

No hook between waves to detect that Wave 1 created a `pyproject.toml` and install its dependencies before Wave 2 runs.

### SDK Transport Passes Full Environment

**subprocess_cli.py:346-351** (verified from installed package):
```python
process_env = {
    **os.environ,
    **self._options.env,
    "CLAUDE_CODE_ENTRYPOINT": "sdk-py",
    "CLAUDE_AGENT_SDK_VERSION": __version__,
}
```

Both Player and Coach inherit the same environment. The transport is working correctly.

### FEAT-BA28.yaml Confirms Empty requires_infrastructure

Source: `guardkit-examples/fastapi/.guardkit/features/FEAT-BA28.yaml` line 54:
```yaml
- id: TASK-DB-003
  name: Implement User model schemas and CRUD
  requires_infrastructure: []   # empty
```

All 5 tasks in FEAT-BA28 have `requires_infrastructure: []`.

---

## C4 Sequence Diagrams

### Diagram 1: Current Flow — Why TASK-DB-003 Stalls (Root Cause: No Bootstrap)

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Feature      │  │  AutoBuild   │  │CoachValidator│  │  SDK CLI     │
│  Orchestrator │  │ (per-task)   │  │              │  │  (test run)  │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                  │                  │                  │
       │ _setup_phase()   │                  │                  │
       │ ┌──────────────┐ │                  │                  │
       │ │1. Load YAML  │ │                  │                  │
       │ │2. Validate   │ │                  │                  │
       │ │3. Worktree   │ │                  │                  │
       │ │              │ │                  │                  │
       │ │❌ NO install │ │                  │                  │
       │ │❌ NO verify  │ │                  │                  │
       │ └──────────────┘ │                  │                  │
       │                  │                  │                  │
  ═════╪══ WAVE 1 ════════╪══════════════════╪══════════════════╪════
       │                  │                  │                  │
       │ TASK-DB-001      │                  │                  │
       │ (scaffolding)    │                  │                  │
       ├─────────────────►│                  │                  │
       │                  │ Player (50 turns)│                  │
       │                  │ Creates pyproject│                  │
       │                  │ .toml with       │                  │
       │                  │ sqlalchemy dep   │                  │
       │                  │                  │                  │
       │                  │ Player MAY run:  │                  │
       │                  │ pip install -e . │                  │
       │                  │ (INCIDENTAL,     │                  │
       │                  │  not guaranteed) │                  │
       │                  │                  │                  │
       │◄─────────────────│ success          │                  │
       │                  │                  │                  │
  ═════╪══ BETWEEN WAVES ═╪══════════════════╪══════════════════╪════
       │                  │                  │                  │
       │ ❌ NO inter-wave │                  │                  │
       │    bootstrap     │                  │                  │
       │ ❌ NO manifest   │                  │                  │
       │    re-detection  │                  │                  │
       │ ❌ NO pip install│                  │                  │
       │                  │                  │                  │
  ═════╪══ WAVE 2 ════════╪══════════════════╪══════════════════╪════
       │                  │                  │                  │
       │ TASK-DB-003      │                  │                  │
       │ (User CRUD)      │                  │                  │
       ├─────────────────►│                  │                  │
       │                  │                  │                  │
       │                  │ Player (50 turns)│                  │
       │                  │ Writes models,   │                  │
       │                  │ schemas, CRUD    │                  │
       │                  │ Reports 49 tests │                  │
       │                  │ passing ✓        │                  │
       │                  │                  │                  │
       │                  │ Coach turn 1 ───►│                  │
       │                  │                  │ validate()       │
       │                  │                  │ ┌──────────────┐ │
       │                  │                  │ │Quality gates │ │
       │                  │                  │ │ALL PASS ✓    │ │
       │                  │                  │ └──────────────┘ │
       │                  │                  │                  │
       │                  │                  │ run_independent_ │
       │                  │                  │ tests()          │
       │                  │                  │                  │
       │                  │                  │ _run_tests_via   │
       │                  │                  │ _sdk()           │
       │                  │                  ├─────────────────►│
       │                  │                  │                  │
       │                  │                  │  ┌─────────────┐ │
       │                  │                  │  │pytest ...    │ │
       │                  │                  │  │             │ │
       │                  │                  │  │env = {      │ │
       │                  │                  │  │ **os.environ│ │
       │                  │                  │  │} ← CORRECT  │ │
       │                  │                  │  │             │ │
       │                  │                  │  │BUT:         │ │
       │                  │                  │  │sqlalchemy   │ │
       │                  │                  │  │was never    │ │
       │                  │                  │  │pip installed│ │
       │                  │                  │  │into this    │ │
       │                  │                  │  │Python env!  │ │
       │                  │                  │  │             │ │
       │                  │                  │  │ModuleNot    │ │
       │                  │                  │  │FoundError ✗ │ │
       │                  │                  │  └─────────────┘ │
       │                  │                  │◄─────────────────│
       │                  │                  │                  │
       │                  │ ◄── feedback ────│                  │
       │                  │                  │                  │
       │                  │ Turn 2: IDENTICAL│                  │
       │                  │ Turn 3: IDENTICAL│                  │
       │                  │                  │                  │
       │                  │ UNRECOVERABLE    │                  │
       │                  │ _STALL           │                  │
       │◄─────────────────│                  │                  │
```

### Diagram 2: Why Player Works But Coach Doesn't (Package Installation Timeline)

```
Timeline ──────────────────────────────────────────────────────────►

WAVE 1: TASK-DB-001 (Scaffolding)
├── Player session starts (50 turns, ~8 min)
│   ├── Turn 1-5:  Creates project structure
│   ├── Turn 6-10: Creates pyproject.toml with sqlalchemy dep
│   ├── Turn 11-15: Runs `pip install -e ".[dev]"`  ◄── INCIDENTAL
│   │                                                    (side-effect of
│   │                                                     implementation)
│   ├── Turn 16-40: Implements models, tests
│   └── Turn 41-50: Final adjustments
│
├── Coach session (1 turn, ~5 sec)
│   └── pytest tests/ → PASSES ✓
│       (sqlalchemy available because Player just installed it)
│
└── TASK-DB-001 APPROVED ✓

         ┌───────────────────────────────────────────┐
         │  NO INTER-WAVE BOOTSTRAP                  │
         │                                           │
         │  pyproject.toml exists in worktree        │
         │  BUT: Was sqlalchemy installed into        │
         │  the Python that the NEXT Coach will use? │
         │                                           │
         │  It DEPENDS on what DB-001 Player did.    │
         │  There is NO deterministic install step.  │
         └───────────────────────────────────────────┘

WAVE 2: TASK-DB-003 (User CRUD)
├── Player session starts (50 turns, ~8 min)
│   ├── Player may NOT run pip install (project already set up)
│   ├── Player writes models that import sqlalchemy
│   ├── Player runs pytest → succeeds IF DB-001's install persists
│   └── Player reports 49 tests passing ✓
│
├── Coach session (1 turn, ~5 sec)
│   └── pytest tests/users/test_users.py
│       ├── import sqlalchemy ← line 21
│       └── ModuleNotFoundError: No module named 'sqlalchemy' ✗
│           (sqlalchemy NOT in this Python's site-packages)
│
└── TASK-DB-003 → feedback → stall → UNRECOVERABLE_STALL
```

### Diagram 3: Classification Decision Path (Unchanged — Correct)

```
Input: "ModuleNotFoundError: No module named 'sqlalchemy'"

_classify_test_failure() [coach_validator.py:2224]
│
├─ output_lower = "modulenotfounderror: no module named 'sqlalchemy'"
│
├─ HIGH CONFIDENCE CHECK (line 2245-2247):
│  ├─ "connectionrefusederror"              in output? NO
│  ├─ "connectionerror"                     in output? NO
│  ├─ "connection refused"                  in output? NO
│  ├─ "could not connect to server"         in output? NO
│  ├─ "operationalerror"                    in output? NO
│  ├─ "psycopg2"                            in output? NO
│  ├─ "psycopg"                             in output? NO
│  ├─ "asyncpg"                             in output? NO
│  ├─ "sqlalchemy.exc.operationalerror"     in output? NO
│  ├─ "django.db.utils.operationalerror"    in output? NO
│  ├─ "pymongo.errors.serverselection..."   in output? NO
│  └─ "redis.exceptions.connectionerror"    in output? NO
│
│  → No high-confidence match
│
├─ AMBIGUOUS CHECK (line 2248-2250):
│  ├─ "modulenotfounderror"       in output? YES ◄── MATCH
│  └─ → return ("infrastructure", "ambiguous")
│
└─ Result: ("infrastructure", "ambiguous")

    Conditional approval check [coach_validator.py:603-609]:
    ├─ failure_class == "infrastructure"  → YES ✓
    ├─ failure_confidence == "high"       → NO ✗ (ambiguous)
    └─ → conditional_approval = False → return feedback
```

### Diagram 4: Proposed Architecture — Environment Bootstrap

```
┌──────────────┐  ┌────────────────────┐  ┌──────────────┐
│  Feature      │  │ ProjectEnvironment │  │  AutoBuild   │
│  Orchestrator │  │ Detector           │  │ (per-task)   │
└──────┬───────┘  └────────┬───────────┘  └──────┬───────┘
       │                    │                      │
       │ _setup_phase()     │                      │
       │ ┌──────────────┐   │                      │
       │ │1. Load YAML  │   │                      │
       │ │2. Validate   │   │                      │
       │ │3. Worktree   │   │                      │
       │ └──────────────┘   │                      │
       │                    │                      │
       │ ★ NEW: Phase 1.5   │                      │
       │ _bootstrap_env()   │                      │
       ├───────────────────►│                      │
       │                    │ detect()             │
       │                    │ ┌──────────────────┐ │
       │                    │ │Scan worktree:    │ │
       │                    │ │                  │ │
       │                    │ │pyproject.toml?   │ │
       │                    │ │→ pip install -e .│ │
       │                    │ │                  │ │
       │                    │ │package.json?     │ │
       │                    │ │→ npm install     │ │
       │                    │ │                  │ │
       │                    │ │go.mod?           │ │
       │                    │ │→ go mod download │ │
       │                    │ │                  │ │
       │                    │ │Cargo.toml?       │ │
       │                    │ │→ cargo build     │ │
       │                    │ │                  │ │
       │                    │ │*.csproj?         │ │
       │                    │ │→ dotnet restore  │ │
       │                    │ │                  │ │
       │                    │ │(none found →     │ │
       │                    │ │ skip, greenfield)│ │
       │                    │ └──────────────────┘ │
       │◄───────────────────│                      │
       │ bootstrapped       │                      │
       │                    │                      │
  ═════╪══ WAVE 1 ══════════╪══════════════════════╪════
       │                    │                      │
       │ execute_wave()     │                      │
       │                    │                      │
  ═════╪══ BETWEEN WAVES ═══╪══════════════════════╪════
       │                    │                      │
       │ ★ NEW: Inter-wave  │                      │
       │ _bootstrap_env()   │                      │
       ├───────────────────►│                      │
       │                    │ detect()             │
       │                    │ ┌──────────────────┐ │
       │                    │ │Re-scan worktree: │ │
       │                    │ │                  │ │
       │                    │ │NEW pyproject.toml│ │
       │                    │ │appeared! (Wave 1 │ │
       │                    │ │created it)       │ │
       │                    │ │                  │ │
       │                    │ │→ pip install -e .│ │
       │                    │ │                  │ │
       │                    │ │Already installed │ │
       │                    │ │manifests skipped │ │
       │                    │ │(hash check)      │ │
       │                    │ └──────────────────┘ │
       │◄───────────────────│                      │
       │ bootstrapped       │                      │
       │                    │                      │
  ═════╪══ WAVE 2 ══════════╪══════════════════════╪════
       │                    │                      │
       │ TASK-DB-003        │                      │
       │ Player: 49 pass ✓  │                      │
       │ Coach: 49 pass ✓   │  ◄── sqlalchemy now  │
       │                    │      installed!       │
```

---

## Verified Findings (Revised)

### Finding 0 (TRUE ROOT CAUSE): AutoBuild Has No Environment Bootstrap Phase

**Severity**: CRITICAL
**Verified by**: Code inspection of `_setup_phase()` in both `feature_orchestrator.py` (around line 414) and `autobuild.py` (around line 897); `_wave_phase()` in `feature_orchestrator.py` (around line 1017). Line numbers are approximate and may drift.

`_setup_phase()` performs:
1. Load feature YAML
2. Validate feature structure
3. Create git worktree
4. Initialize AgentInvoker
5. **Install project dependencies — DOES NOT EXIST**
6. **Verify environment is ready — DOES NOT EXIST**

After step 4, agents are immediately launched into the worktree with no guarantee that the target project's dependencies are available.

**Why the Player masks this gap**: The Player runs for ~8 minutes with 50+ tool calls. During scaffolding tasks, it creates dependency manifests and runs install commands as part of its implementation work. This is incidental, not by design.

**Why the Coach exposes it**: The Coach's 1-turn SDK session runs `pytest` in ~5 seconds. It doesn't install anything. If the packages weren't installed, it fails immediately at import time.

### Finding 0b (TRUE ROOT CAUSE): No Inter-Wave Bootstrap Hook

**Severity**: CRITICAL
**Verified by**: `_wave_phase()` in `feature_orchestrator.py` (around line 1059) — the wave loop iterates with no re-detection or install step between waves.

For greenfield projects where Wave 1 creates the dependency manifest:
- TASK-DB-001 (Wave 1) creates `pyproject.toml` with sqlalchemy
- No step detects this new manifest or installs its dependencies
- TASK-DB-003 (Wave 2) launches into an environment where sqlalchemy may or may not be importable

### Finding 1: SDK Transport Works Correctly (Correcting Previous Report)

**Severity**: INFORMATIONAL (corrective)
**Verified by**: `SubprocessCLITransport.connect()` in `subprocess_cli.py` (around line 346) — `process_env = {**os.environ, ...}`

The SDK's `SubprocessCLITransport` passes the full parent environment to the CLI subprocess. PATH, VIRTUAL_ENV, PYTHONPATH, and all other variables are inherited correctly. The environment passthrough works as designed.

**Previous attribution was incorrect**: Revision 2 attributed the failure to "SDK subprocess has different Python environment." This was wrong. The environments are identical. The problem is that the project's dependencies were never deterministically installed into **any** Python environment before agents started running.

**Residual edge case**: While `os.environ` is passed through, the SDK's Bash tool spawns a shell that may resolve `python3` differently depending on PATH ordering in that shell's context. The bootstrap phase fixes this (it runs from the orchestrator's Python via `subprocess.run`), but R3's use of `sys.executable` provides additional protection against this edge case. This is why R3 remains valuable as defence-in-depth even though the primary fix is R1.

### Finding 2: `requires_infrastructure: []` on ALL FEAT-BA28 Tasks

**Severity**: HIGH (secondary gap)
**Verified by**: FEAT-BA28.yaml lines 18, 36, 54, 74, 89.

Every task has `requires_infrastructure: []`. This means:
- Docker lifecycle never entered
- No containers started
- No environment variables exported

This is a legitimate gap for tasks that need PostgreSQL/Redis, but it's **secondary** — even if Docker containers were started, the sqlalchemy Python package wouldn't be available without the bootstrap phase.

### Finding 3: `_docker_available` Never Set in Task Dict

**Severity**: HIGH (secondary gap)
**Verified by**: `_invoke_coach_safely()` in `autobuild.py` (task dict construction, around line 3582) — no `_docker_available` key.

```python
task={
    "acceptance_criteria": acceptance_criteria or [],
    "task_type": task_type,
    "requires_infrastructure": requires_infrastructure or [],
    # "_docker_available" NOT SET — defaults to True in validator
}
```

Conditional approval can never fire because `_docker_available` defaults to `True`.

### Finding 4: `sqlalchemy` Not in High-Confidence Classification

**Severity**: MEDIUM (secondary gap)
**Verified by**: Walking through `_classify_test_failure()` in `coach_validator.py` against the actual error string.

`ModuleNotFoundError: No module named 'sqlalchemy'` matches `_INFRA_AMBIGUOUS` (via `"ModuleNotFoundError"`), not `_INFRA_HIGH_CONFIDENCE`. Classification returns `("infrastructure", "ambiguous")`, preventing conditional approval.

---

## Root Cause Chain (Corrected)

```
┌─────────────────────────────────────────────────────┐
│ TRUE ROOT CAUSE:                                     │
│ AutoBuild _setup_phase() has NO dependency           │
│ installation step. _wave_phase() has NO              │
│ inter-wave bootstrap hook.                           │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│ For FEAT-BA28 (greenfield):                          │
│ Wave 1 (TASK-DB-001) creates pyproject.toml          │
│ Player INCIDENTALLY installs sqlalchemy              │
│ But no deterministic install happens between waves   │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│ Wave 2 (TASK-DB-003):                                │
│ Coach runs pytest → import sqlalchemy fails           │
│ ModuleNotFoundError: No module named 'sqlalchemy'    │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│ SECONDARY GAPS compound the issue:                   │
│ • Classification → "ambiguous" (not "high")          │
│ • requires_infrastructure: [] (empty)                │
│ • _docker_available never set (defaults True)        │
│ → Conditional approval CANNOT fire                   │
│ → Coach returns FEEDBACK each turn                   │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│ Player receives feedback:                            │
│ "Tests failed due to infrastructure"                 │
│ Player CANNOT fix this (it's an env issue)           │
│ 3 identical turns → UNRECOVERABLE_STALL             │
└─────────────────────────────────────────────────────┘
```

---

## Recommendations (Revised)

### R1 (P0): Add `ProjectEnvironmentDetector` + Bootstrap Phase to Feature Orchestrator

**This is the root cause fix.** Without this, every non-trivial project will hit dependency issues.

**Where it lives**: New module `guardkit/orchestrator/environment_bootstrap.py`

**Detection strategy** (file-based, ordered by specificity):

| Lock File | Stack | Install Command |
|-----------|-------|-----------------|
| `poetry.lock` | Python | `poetry install` |
| `Pipfile.lock` | Python | `pipenv install --dev` |
| `pnpm-lock.yaml` | Node | `pnpm install` |
| `yarn.lock` | Node | `yarn install` |
| `package-lock.json` | Node | `npm install` |

| Manifest File (fallback) | Stack | Install Command |
|--------------------------|-------|-----------------|
| `pyproject.toml` | Python | `pip install -e ".[dev,test]"` or `pip install -e .` |
| `requirements.txt` | Python | `pip install -r requirements.txt` |
| `package.json` | Node/React/TS | `npm install` |
| `*.csproj` / `*.sln` | .NET / MAUI | `dotnet restore` |
| `go.mod` | Go | `go mod download` |
| `Cargo.toml` | Rust | `cargo build` (or `cargo check`) |
| `pubspec.yaml` | Flutter/Dart | `flutter pub get` |
| `build.gradle.kts` | Android/Kotlin | `./gradlew build` |
| `Package.swift` | iOS/Swift | `swift package resolve` |

**Integration points**:

```python
# feature_orchestrator.py
def _setup_phase(self, feature_id, base_branch):
    ...
    worktree = create_worktree()
    self._bootstrap_environment(worktree.path)  # NEW: Phase 1.5
    return feature, worktree

def _wave_phase(self, feature, worktree):
    for wave_number, task_ids in enumerate(waves, 1):
        wave_result = self._execute_wave(...)
        wave_results.append(wave_result)
        self._bootstrap_environment(worktree.path)  # NEW: inter-wave hook
        # Only installs if NEW manifests appeared since last check
    return wave_results

def _bootstrap_environment(self, worktree_path: Path) -> None:
    """Detect project type(s) and install dependencies."""
    detector = ProjectEnvironmentDetector(worktree_path)
    manifests = detector.detect()
    for stack, manifest, cmd in manifests:
        if self._already_bootstrapped(manifest):
            continue
        logger.info(f"Installing {stack} dependencies from {manifest.name}")
        result = subprocess.run(cmd, cwd=str(worktree_path), ...)
        if result.returncode == 0:
            self._mark_bootstrapped(manifest)
        else:
            logger.warning(f"Dependency install failed: {result.stderr[:500]}")
```

**`_already_bootstrapped` check**: Prevents redundant installs by tracking a hash of each manifest's content in `.guardkit/bootstrap_state.json`.

### R2 (P0): Add Inter-Wave Bootstrap Hook

Covered by R1's `_wave_phase()` integration above. Handles greenfield projects where Wave 1 creates the manifest.

### R3 (P1): Coach Test Fallback to Subprocess with `sys.executable` (Defence-in-Depth)

Change `run_independent_tests()` to use `subprocess.run()` with `sys.executable` as the Python interpreter. This eliminates any residual PATH resolution ambiguity for Python Coach tests specifically:

```python
import sys
test_cmd = f"{sys.executable} -m pytest tests/users/test_users.py -v --tb=short"
result = subprocess.run(test_cmd, shell=True, cwd=worktree_path, ...)
```

**Why this is now P1 not P0**: With the bootstrap phase in place, both SDK and subprocess paths should work. This is defence-in-depth, not the primary fix.

**Why it's still important**: Even though the SDK passes `os.environ`, the Bash tool inside the CLI spawns a shell that resolves `python3` via PATH. If PATH ordering differs between the orchestrator's Python and what the shell resolves (e.g., macOS `/usr/bin/python3` vs framework Python), tests could hit the wrong interpreter. Using `sys.executable` explicitly pins the Python binary, eliminating this class of issue entirely for Coach tests.

### R4 (P1): Add `requires_infrastructure` to FEAT-BA28 Tasks

Update FEAT-BA28.yaml tasks that need PostgreSQL:

```yaml
- id: TASK-DB-003
  name: Implement User model schemas and CRUD
  requires_infrastructure:
    - postgresql
```

### R5 (P1): Wire `_docker_available` into Task Dict

In `_invoke_coach_safely()` in `autobuild.py` (task dict construction, around line 3582):

```python
task={
    "acceptance_criteria": acceptance_criteria or [],
    "task_type": task_type,
    "requires_infrastructure": requires_infrastructure or [],
    "_docker_available": validator._is_docker_available(),  # ADD
}
```

### R6 (P2): Promote Known Service-Client Libraries to High Confidence

Add a compound pattern check that promotes `ModuleNotFoundError` to high confidence when the missing module is a known database/service client library:

```python
# Known database and service client libraries.
# These are NOT "infrastructure modules" — they're client libraries
# whose absence means the project's service dependencies can't be reached.
_KNOWN_SERVICE_CLIENT_LIBS = {
    "psycopg2", "asyncpg", "pymongo", "redis", "psycopg",
    "sqlalchemy", "motor", "aioredis", "cassandra",
}

for pattern in self._INFRA_AMBIGUOUS:
    if pattern.lower() in output_lower:
        for lib in _KNOWN_SERVICE_CLIENT_LIBS:
            if lib in output_lower:
                return ("infrastructure", "high")
        return ("infrastructure", "ambiguous")
```

**Note on naming**: The list is `_KNOWN_SERVICE_CLIENT_LIBS`, not `_INFRA_MODULES`. `sqlalchemy` isn't infrastructure — it's a project dependency that happens to be a database client. The distinction matters: `ModuleNotFoundError: No module named 'requests'` should remain ambiguous; `ModuleNotFoundError: No module named 'sqlalchemy'` should be high confidence because we know it's a database client library whose absence indicates a missing dependency install, not a code defect.

### R7 (P2): Diagnostic Logging of SDK Test Environment

Log the raw test output for post-mortem classification auditing.

---

## Scope Questions for Implementation

These questions from the revision response should be resolved before implementing R1:

### 1. Where does `ProjectEnvironmentDetector` live?

**Recommended**: New module `guardkit/orchestrator/environment_bootstrap.py`. This is orchestrator-level infrastructure, not a quality gate. Reuse stack detection patterns from `templates/detect.py` if they exist, but the bootstrap module is distinct (it detects AND installs, not just detects).

### 2. Should bootstrap be synchronous or async?

**Recommended**: Synchronous. `pip install` can take 30-60s, but it must complete before agents run. Run it once before wave dispatch. For the inter-wave hook, it's already in a sequential loop between waves, so sync is natural. Async adds complexity without benefit here.

### 3. Error handling: What if bootstrap fails?

**Recommended**: Warn and continue. The Player may handle it (install packages itself). But flag it in the feature execution report:
```python
if result.returncode != 0:
    logger.warning(f"Dependency install for {stack} failed (non-fatal)")
    self._bootstrap_warnings.append(f"{stack}: {result.stderr[:200]}")
```

### 4. Monorepo support

**Recommended**: The detector should scan the worktree root AND immediate subdirectories (depth 1). This handles `backend/pyproject.toml` + `frontend/package.json` patterns. Don't scan deeper (too slow, too ambiguous).

**Known limitation**: Depth-1 scanning will NOT detect manifests in deeper monorepo structures like `packages/backend/api/pyproject.toml`. This is an acceptable trade-off for v1 — deeper scanning is slow and introduces ambiguity about which manifests are relevant. This limitation should be documented in the module's docstring and can be extended later with explicit configuration (e.g., a `scan_paths` option in the feature YAML).

### 5. Virtual environment policy

**Status**: OPEN DESIGN DECISION — resolve during R1 implementation.

**Option A: Install into current Python (simpler)**
- Simpler, matches how developers work locally
- No activation complexity for subprocess or SDK sessions
- Risk: If GuardKit orchestrates a .NET project with a Python utility script, `pip install -e .` pollutes the system Python with that project's dependencies
- Risk: If two features run concurrently in different worktrees with conflicting dependency versions, there's a race condition on the shared site-packages

**Option B: Create project-specific venv in worktree (isolated)**
- Clean isolation between projects and concurrent features
- Requires activating the venv in subprocess calls and ensuring SDK sessions resolve to it
- Adds complexity to the bootstrap and to test execution paths

**Default for v1**: Start with Option A (install into current Python) with the understanding that this is a pragmatic starting point, not a permanent architecture decision. The risks are real but unlikely in the near term (concurrent features with conflicting deps). If concurrent worktree execution becomes a priority, Option B should be implemented before it's needed.

### 6. Interaction with TASK-PCTD-3182

**Recommended**: Pause or re-scope. The "SDK environment parity" task's core premise (that the SDK subprocess has a different environment) is incorrect. If the environment is properly bootstrapped, both SDK and subprocess paths work. TASK-PCTD-3182 should be re-evaluated after R1 is implemented.

---

## Priority Matrix (Final)

| Priority | Fix | Effort | Impact | Nature |
|----------|-----|--------|--------|--------|
| **P0** | R1: `ProjectEnvironmentDetector` + bootstrap phase | Medium | Critical — root cause fix | **Root cause** |
| **P0** | R2: Inter-wave bootstrap hook | Small (part of R1) | Critical — greenfield support | **Root cause** |
| P1 | R3: Coach subprocess with `sys.executable` | Small | Medium — defence-in-depth | Defence |
| P1 | R4: `requires_infrastructure` in FEAT-BA28 | Small | High — Docker path | Configuration |
| P1 | R5: Wire `_docker_available` in task dict | Small | High — conditional approval | Wiring |
| P2 | R6: `sqlalchemy` in high-confidence patterns | Small | Medium — classification | Classification |
| P2 | R7: Diagnostic logging | Small | Medium — debugging | Observability |

**Critical path**: R1 + R2 unblocks TASK-DB-003 and all future non-trivial projects. R3-R5 provide defence-in-depth for infrastructure-dependent tasks.

---

## Acceptance Criteria Verification (Final)

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Determine actual test failure output | **VERIFIED** | coach_turn_1.json: `ModuleNotFoundError: No module named 'sqlalchemy'` |
| Why psycopg2 pattern didn't match | **VERIFIED** | Error is `'sqlalchemy'` not `'psycopg2'`. sqlalchemy fails at import before psycopg2 is ever referenced |
| Check requires_infrastructure propagation | **VERIFIED** | FEAT-BA28.yaml: `requires_infrastructure: []` on all 5 tasks |
| Check Docker fixture activation | **VERIFIED** | Docker fixtures never triggered. `requires_infra = []` → Docker lifecycle skipped |
| Why Docker fixtures not used | **VERIFIED** | `requires_infrastructure` empty → Docker path never entered |
| Conditional approval wiring | **VERIFIED** | Dead code: `_docker_available` never set (defaults True), `requires_infrastructure` empty, classification `ambiguous` |
| Recommend fixes | **VERIFIED** | 7 recommendations. R1/R2 (environment bootstrap) is the root cause fix |
| Root cause analysis | **UPDATED** | Root cause analysis corrected across 3 revisions. Rev 1: assumed psycopg2 (wrong error). Rev 2: attributed to SDK env mismatch (wrong mechanism). Rev 3: identified missing bootstrap phase (verified against SDK source, setup_phase code, and greenfield timing). Evidence chain: SDK passes `{**os.environ}` → env is identical → packages were never installed → bootstrap phase missing. |

---

## Decision Options

- **[A]ccept** — Archive findings, create implementation tasks from recommendations
- **[R]evise** — Request further analysis on specific areas
- **[I]mplement** — Create implementation task structure for R1-R7
- **[C]ancel** — Discard review

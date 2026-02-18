# Review Report: TASK-REV-C9E5 (Revision 3)

## Executive Summary

The FEAT-BA28 (PostgreSQL Database Integration) re-run after environment bootstrap implementation reveals **two verified root causes** that combine to produce the same UNRECOVERABLE_STALL on TASK-DB-003. One previously suspected issue (`sys.executable`) is confirmed NOT a defect.

**Root Cause 1 — Propagation gap (Critical)**: `requires_infrastructure` is defined in the feature YAML but the `AutoBuildOrchestrator` reads it from task `.md` frontmatter. The two are separate data sources with no synchronisation path. This blocks both (a) Docker container lifecycle for infrastructure-dependent tests and (b) the conditional approval fallback.

**Root Cause 2 — Install-before-ready (High)**: The bootstrap runs editable install against an incomplete project structure (manifest exists but source directory does not). This is a general greenfield timing problem — not specific to any one build system — where a dependency manifest is created before the project source tree it references.

**Critical insight (Revision 3)**: R1 alone is **necessary but not sufficient** for TASK-DB-003 to pass. Fixing the propagation gap unblocks the Docker path and conditional approval, but (a) the Docker lifecycle path has never been exercised in a real run and represents untested territory, and (b) without R2 (dependency install for incomplete projects), tests still fail with `ModuleNotFoundError`. R1 alone changes the outcome from "stall" to "conditional approval (skipping the test)" — it doesn't make the tests pass. Both R1 and R2 are required for actual test execution success.

**Architecture Score**: 62/100 (revised down — untested Docker path and misleading feedback loop are additional concerns)

---

## Review Details

- **Mode**: Architectural Review (Revision 3 — incorporating reviewer feedback)
- **Depth**: Comprehensive
- **Task**: TASK-REV-C9E5 — Analyse DB failure after environment bootstrap implementation
- **Evidence**: `docs/reviews/autobuild-fixes/db_failed_after_env_changes.md` (859 lines)
- **Related Tasks**: TASK-BOOT-{E3C0, 3CAF, 43DE, 6D85, 214B, F9C4, 7369}
- **Parent Review**: TASK-REV-4D57

### Revision 3 Changes

Changes from Revision 2 based on reviewer feedback:

1. **R1 insufficiency flagged**: R1 unblocks the Docker path but that path is untested. Added Finding 8 (Docker path untested) and risk assessment to R1.
2. **R2 reframed**: Changed from "fallback strategy" to "primary strategy for incomplete projects". Detection-first approach: check source tree completeness before choosing install strategy.
3. **R3 revised**: Simple "don't persist on failure" causes infinite retries when manifest content is static. Replaced with state-aware hash persistence that stores outcome alongside hash, with worktree structure change detection.
4. **Finding 8 added**: Coach feedback is misleading — tells Player "add mocks" when the actual issue is missing packages. Player cannot resolve this. Noted that even with R1, if R2 is not also implemented, the feedback loop persists.
5. **Finding 7 upgraded**: Diagnostic logging invisibility explained — `subprocess.run(capture_output=True)` captures subprocess output; Python logger messages emit to the orchestrator's logger, not the subprocess. Bootstrap uses `logging.getLogger(__name__)` but never sets level or propagates it to child processes.
6. **R1 and R2 dependency made explicit**: Both are required for TASK-DB-003 tests to actually execute. R1 alone just triggers conditional approval (test skipping).

---

## C4 Sequence Diagrams

### Diagram 1: requires_infrastructure Propagation — Current (Broken) Flow

This diagram traces the actual code path from feature YAML through to Coach validation, showing exactly where the propagation breaks.

```
┌─────────────┐  ┌──────────────────┐  ┌────────────────────┐  ┌──────────────────┐  ┌────────────────┐
│ FEAT-BA28   │  │ FeatureOrchestrator│  │ AutoBuild          │  │ TaskLoader       │  │ CoachValidator │
│ .yaml       │  │                    │  │ Orchestrator       │  │                  │  │                │
└──────┬──────┘  └────────┬───────────┘  └─────────┬──────────┘  └────────┬─────────┘  └───────┬────────┘
       │                  │                         │                      │                    │
       │  load_feature()  │                         │                      │                    │
       │─────────────────>│                         │                      │                    │
       │                  │                         │                      │                    │
       │  FeatureTask {   │                         │                      │                    │
       │   requires_infra:│                         │                      │                    │
       │   [postgresql]   │                         │                      │                    │
       │  }               │                         │                      │                    │
       │<─────────────────│                         │                      │                    │
       │                  │                         │                      │                    │
       │                  │  _execute_task(task)     │                      │                    │
       │                  │  FeatureTask has         │                      │                    │
       │                  │  requires_infra=         │                      │                    │
       │                  │  [postgresql]            │                      │                    │
       │                  │────────────────────────> │                      │                    │
       │                  │                         │                      │                    │
       │                  │  orchestrate(            │                      │                    │
       │                  │   task_id,               │                      │                    │
       │                  │   requirements,          │                      │                    │
       │                  │   acceptance_criteria,   │                      │                    │
       │                  │   task_file_path         │                      │                    │
       │                  │  )                       │                      │                    │
       │                  │  ┌──────────────────┐    │                      │                    │
       │                  │  │ NOTE: No          │    │                      │                    │
       │                  │  │ requires_infra    │    │                      │                    │
       │                  │  │ parameter passed! │    │                      │                    │
       │                  │  └──────────────────┘    │                      │                    │
       │                  │                         │                      │                    │
       │                  │                         │  load_task(task_id)   │                    │
       │                  │                         │─────────────────────>│                    │
       │                  │                         │                      │                    │
       │                  │                         │  frontmatter:        │                    │
       │                  │                         │  {id, title, ...}    │                    │
       │                  │                         │  NO requires_infra   │                    │
       │                  │                         │  field in .md file   │                    │
       │                  │                         │<─────────────────────│                    │
       │                  │                         │                      │                    │
       │                  │                         │  ri = frontmatter.   │                    │
       │                  │                         │    get("requires_    │                    │
       │                  │                         │    infrastructure")  │                    │
       │                  │                         │  → None              │                    │
       │                  │                         │  requires_infra =    │                    │
       │                  │                         │  None                │                    │
       │                  │                         │                      │                    │
       │                  │                         │         _invoke_coach_safely(             │
       │                  │                         │          requires_infrastructure=None)     │
       │                  │                         │─────────────────────────────────────────> │
       │                  │                         │                      │                    │
       │                  │                         │  task={              │                    │
       │                  │                         │   "requires_infra":  │                    │
       │                  │                         │   None or [] → []    │                    │
       │                  │                         │   "_docker_available"│                    │
       │                  │                         │   : True/False       │                    │
       │                  │                         │  }                   │                    │
       │                  │                         │                      │  validate(task)    │
       │                  │                         │                      │                    │
       │                  │                         │                      │  bool([]) = False  │
       │                  │                         │                      │  ──────────────────│
       │                  │                         │                      │  conditional_      │
       │                  │                         │                      │  approval = False  │
       │                  │                         │                      │                    │
       │                  │                         │                      │  → feedback        │
       │                  │                         │<─────────────────────────────────────────│
```

**Key breakpoint**: `FeatureOrchestrator._execute_task()` at [feature_orchestrator.py:1521](guardkit/orchestrator/feature_orchestrator.py#L1521) calls `orchestrate()` WITHOUT passing `requires_infrastructure`. The `orchestrate()` method signature at [autobuild.py:676](guardkit/orchestrator/autobuild.py#L676) does not accept it as a parameter. Instead, `orchestrate()` reads it independently from the task `.md` frontmatter at [autobuild.py:747](guardkit/orchestrator/autobuild.py#L747), which lacks the field.

**Verification**: Confirmed by reading every line in the chain:
- [feature_orchestrator.py:1521-1526](guardkit/orchestrator/feature_orchestrator.py#L1521-L1526) — `orchestrate()` call, no `requires_infrastructure` argument
- [autobuild.py:676-683](guardkit/orchestrator/autobuild.py#L676-L683) — `orchestrate()` signature, no `requires_infrastructure` parameter
- [autobuild.py:738-750](guardkit/orchestrator/autobuild.py#L738-L750) — loads `requires_infrastructure` from task `.md` frontmatter
- [autobuild.py:3582-3586](guardkit/orchestrator/autobuild.py#L3582-L3586) — constructs task dict for Coach with `requires_infrastructure or []`
- [coach_validator.py:617](guardkit/orchestrator/quality_gates/coach_validator.py#L617) — `task.get("requires_infrastructure", [])` evaluates to `[]`
- [coach_validator.py:620-626](guardkit/orchestrator/quality_gates/coach_validator.py#L620-L626) — `bool([])` is `False`, short-circuits conditional approval

---

### Diagram 2: requires_infrastructure Propagation — SECOND Impact (Docker Lifecycle)

The propagation gap has a **dual impact**. Not only does it block conditional approval, it also prevents Docker containers from being started for independent test verification.

```
┌────────────────┐                    ┌─────────────────┐
│ CoachValidator │                    │ Docker Daemon   │
│ .validate()    │                    │                 │
└───────┬────────┘                    └────────┬────────┘
        │                                      │
        │  run_independent_tests(task)          │
        │──────────────────────────────>        │
        │                                      │
        │  requires_infra = task.get(          │
        │    "requires_infrastructure")         │
        │  → []  (propagation gap!)            │
        │                                      │
        │  if requires_infra:  ← FALSE         │
        │  ┌────────────────────┐              │
        │  │ SKIPPED:           │              │
        │  │ _is_docker_avail() │              │
        │  │ _start_containers()│              │
        │  └────────────────────┘              │
        │                                      │
        │  Run tests WITHOUT infrastructure    │
        │  pytest tests/users/test_users.py    │
        │  → ModuleNotFoundError: asyncpg      │
        │  OR ConnectionRefusedError           │
        │                                      │
        │  classify → (infrastructure, high)   │
        │                                      │
        │  conditional_approval check:         │
        │    bool([]) = False                  │
        │  → feedback (not approve)            │
        │                                      │
```

**Verification**: [coach_validator.py:1164-1182](guardkit/orchestrator/quality_gates/coach_validator.py#L1164-L1182) — the `requires_infra` guard at line 1172 prevents Docker container startup. The evidence confirms: zero Docker-related log lines in the entire 859-line output.

---

### Diagram 3: Bootstrap Execution — Install-Before-Ready Pattern

```
┌───────────────────┐  ┌──────────────────────┐  ┌───────────────────┐  ┌────────────────┐
│ FeatureOrchestrator│  │ ProjectEnvironment   │  │ Environment       │  │ Build System   │
│                    │  │ Detector             │  │ Bootstrapper      │  │ (pip/npm/etc)  │
└────────┬───────────┘  └──────────┬───────────┘  └─────────┬─────────┘  └───────┬────────┘
         │                         │                         │                    │
  [Phase 1.5: After worktree created, before Wave 1]        │                    │
         │                         │                         │                    │
         │  _bootstrap_environment │                         │                    │
         │────────────────────────>│                         │                    │
         │                         │                         │                    │
         │                         │  detect()               │                    │
         │                         │  Scan root + depth-1    │                    │
         │                         │  Finds: pyproject.toml  │                    │
         │                         │  (created by Wave 1     │                    │
         │                         │   of a PREVIOUS run     │                    │
         │                         │   or pre-existing)      │                    │
         │                         │                         │                    │
         │                         │  DetectedManifest{      │                    │
         │                         │   stack="python",       │                    │
         │                         │   install_cmd=          │                    │
         │                         │   [sys.executable,      │                    │
         │                         │    "-m","pip",          │                    │
         │                         │    "install","-e","."]  │                    │
         │                         │  }                      │                    │
         │                         │                         │                    │
         │                         │  bootstrap(manifests)   │                    │
         │                         │────────────────────────>│                    │
         │                         │                         │                    │
         │                         │                         │  _run_install()    │
         │                         │                         │  subprocess.run(   │
         │                         │                         │   cmd, cwd=root)   │
         │                         │                         │───────────────────>│
         │                         │                         │                    │
         │                         │                         │                    │  Build system
         │                         │                         │                    │  looks for
         │                         │                         │                    │  source dir
         │                         │                         │                    │  matching
         │                         │                         │                    │  project name
         │                         │                         │                    │  → NOT FOUND
         │                         │                         │                    │
         │                         │                         │  returncode=1      │
         │                         │                         │<───────────────────│
         │                         │                         │                    │
         │                         │                         │  _save_state(hash) │
         │                         │                         │  (saves even on    │
         │                         │                         │   failure)         │
         │                         │                         │                    │
         │  BootstrapResult{       │                         │                    │
         │   success=False,        │                         │                    │
         │   installs_failed=1     │                         │                    │
         │  }                      │                         │                    │
         │<────────────────────────│                         │                    │
         │                         │                         │                    │
  [NON-BLOCKING: continues to Wave execution]                │                    │
         │                         │                         │                    │
  ────── │ ─── Wave 1 executes (creates source files) ───── │ ──────────────────│──
         │                         │                         │                    │
  [Inter-wave bootstrap between Wave 1 and Wave 2]          │                    │
         │                         │                         │                    │
         │  _bootstrap_environment │                         │                    │
         │────────────────────────>│                         │                    │
         │                         │  detect() →             │                    │
         │                         │  pyproject.toml         │                    │
         │                         │  (may be modified       │                    │
         │                         │   by Wave 1)            │                    │
         │                         │                         │                    │
         │                         │  bootstrap(manifests)   │                    │
         │                         │────────────────────────>│                    │
         │                         │                         │                    │
         │                         │                         │  content hash !=   │
         │                         │                         │  saved hash        │
         │                         │                         │  (file modified)   │
         │                         │                         │                    │
         │                         │                         │  _run_install()    │
         │                         │                         │───────────────────>│
         │                         │                         │                    │  SAME FAILURE
         │                         │                         │                    │  Source dir
         │                         │                         │                    │  still missing
         │                         │                         │  returncode=1      │
         │                         │                         │<───────────────────│
```

**Why this is stack-agnostic**: The pattern "manifest exists but source tree doesn't" can occur in ANY stack:
- **Python**: `pyproject.toml` exists, `fastapi_health_app/` does not → build system fails
- **Node**: `package.json` references local workspace paths that don't exist yet
- **.NET**: `*.csproj` references project references not yet created
- **Go**: `go.mod` exists but package directories are empty
- **Rust**: `Cargo.toml` exists but `src/` directory is missing

**Verification**: The evidence at lines 82-86 shows the build system error explicitly:
```
ValueError: Unable to determine which files to ship inside the wheel
The most likely cause is that there is no directory that matches the name
of your project (fastapi_health_app).
```

The build system (`hatchling` in this case) cannot find a source directory matching the declared project name. Wave 1 created `pyproject.toml` with `name = "fastapi_health_app"` but only created `src/db/` — the `fastapi_health_app/` package directory was not created.

---

### Diagram 4: TASK-DB-003 Stall Loop — Complete Turn Cycle (with Feedback Analysis)

```
┌───────────┐  ┌──────────────┐  ┌────────────────┐  ┌─────────────────┐
│ AutoBuild │  │ Player (SDK) │  │ CoachValidator │  │ Stall Detector  │
│ Loop      │  │              │  │                │  │                 │
└─────┬─────┘  └──────┬───────┘  └───────┬────────┘  └───────┬─────────┘
      │               │                  │                    │
  [Turn 1]            │                  │                    │
      │  invoke       │                  │                    │
      │──────────────>│                  │                    │
      │               │  implement       │                    │
      │               │  (creates code,  │                    │
      │               │   tests pass     │                    │
      │               │   within Player  │                    │
      │               │   sandbox)       │                    │
      │  report       │                  │                    │
      │<──────────────│                  │                    │
      │               │                  │                    │
      │  validate(task)                  │                    │
      │─────────────────────────────────>│                    │
      │               │                  │                    │
      │               │                  │  1. Quality gates: │
      │               │                  │     ALL PASSED     │
      │               │                  │                    │
      │               │                  │  2. Independent    │
      │               │                  │     test:          │
      │               │                  │     pytest via SDK │
      │               │                  │     → FAIL         │
      │               │                  │   ModuleNotFoundError│
      │               │                  │   (missing package,│
      │               │                  │    NOT missing DB) │
      │               │                  │                    │
      │               │                  │  3. classify →     │
      │               │                  │   (infra, high)    │
      │               │                  │                    │
      │               │                  │  4. Conditional    │
      │               │                  │     approval:      │
      │               │                  │     requires_infra │
      │               │                  │     = [] → SKIP    │
      │               │                  │                    │
      │               │                  │  5. → feedback:    │
      │               │                  │     "infra issue,  │
      │               │                  │      add mocks"    │
      │               │                  │  ┌────────────────────┐
      │               │                  │  │ MISLEADING: Player │
      │               │                  │  │ told "add mocks"   │
      │               │                  │  │ but issue is       │
      │               │                  │  │ missing package    │
      │               │                  │  │ (ModuleNotFound),  │
      │               │                  │  │ not missing DB.    │
      │               │                  │  │ Even adding mocks  │
      │               │                  │  │ can't fix an       │
      │               │                  │  │ import error.      │
      │               │                  │  └────────────────────┘
      │  feedback(sig=7e914c9e)          │                    │
      │<─────────────────────────────────│                    │
      │               │                  │                    │
      │  record sig                      │                    │
      │──────────────────────────────────────────────────────>│
      │               │                  │                    │  sig count: 1
      │               │                  │                    │
  [Turn 2: IDENTICAL — same feedback sig]                     │
      │  ...same flow...                 │                    │
      │  feedback(sig=7e914c9e)          │                    │
      │<─────────────────────────────────│                    │
      │──────────────────────────────────────────────────────>│
      │               │                  │                    │  sig count: 2
      │               │                  │                    │
  [Turn 3: IDENTICAL — same feedback sig]                     │
      │  ...same flow...                 │                    │
      │  feedback(sig=7e914c9e)          │                    │
      │<─────────────────────────────────│                    │
      │──────────────────────────────────────────────────────>│
      │               │                  │                    │  sig count: 3
      │               │                  │                    │  → STALL!
      │  UNRECOVERABLE_STALL             │                    │
      │<──────────────────────────────────────────────────────│
```

**Verification**: Evidence confirms exact values at each turn:
- Turn 1 (line 639): `classification=infrastructure, confidence=high` → feedback
- Turn 2 (line 703): `classification=infrastructure, confidence=high` → feedback
- Turn 3 (line 765): `classification=infrastructure, confidence=high` → feedback
- Line 775: `Feedback stall: identical feedback (sig=7e914c9e) for 3 turns with 0 criteria passing`

---

## Verified Findings

### Finding 1: sys.executable — NOT A DEFECT

**Severity**: None (resolved/not-a-bug)
**Evidence**: Line 33 — `/usr/local/bin/python3 -m pip install -e .`
**Code**: [environment_bootstrap.py:252](guardkit/orchestrator/environment_bootstrap.py#L252) — `install_command=[sys.executable, "-m", "pip", "install", "-e", "."]`

**Verification method**: Direct source code inspection confirms `sys.executable` is used. The `/usr/local/bin/python3` value in the evidence IS `sys.executable` in the orchestrator's process context. The different path (`/Library/Frameworks/Python.framework/Versions/3.14/...`) appearing in pip's build isolation output is pip's expected behaviour — it creates an isolated build environment.

**Verdict**: TASK-BOOT-E3C0 correctly implemented. No action needed.

---

### Finding 2: Install-Before-Ready Pattern — ROOT CAUSE OF BOOTSTRAP FAILURE

**Severity**: High
**Evidence**: Lines 34-102 (initial), Lines 373-443 (inter-wave)
**Code**: [environment_bootstrap.py:246-266](guardkit/orchestrator/environment_bootstrap.py#L246-L266)

**Root Cause (stack-agnostic framing)**: The bootstrap detects a dependency manifest and attempts installation before the project source tree is complete. This is a **timing problem inherent to greenfield wave-based execution**: Wave 1 creates the manifest (e.g., `pyproject.toml`, `package.json`), but the source directories it references don't exist until later waves create them.

**The install command itself is correct** — editable install is the right command for a project with a build manifest. The issue is that it runs too early, before the source tree is complete.

**Hash persistence clarification** (corrected from Revision 1): The hash IS saved after failure ([environment_bootstrap.py:503](guardkit/orchestrator/environment_bootstrap.py#L503)), but the inter-wave bootstrap at line 373 re-executes because Wave 1 modified `pyproject.toml`, changing the content hash. The inter-wave re-execution is correct behaviour — the hash-save-on-failure does NOT prevent retries when content changes. However, if content does NOT change between waves, the failed state is cached and retries are suppressed, which is a secondary concern (see R3 for nuanced fix).

**Impact on TASK-DB-003**: The bootstrap failure means project dependencies are never installed into the worktree environment. When Coach runs independent tests via SDK, the SDK process inherits the orchestrator's environment which lacks these dependencies. Tests fail with `ModuleNotFoundError` (or `ConnectionRefusedError` if the import succeeds but the database server isn't running).

---

### Finding 3: requires_infrastructure Propagation Gap — ROOT CAUSE OF STALL

**Severity**: Critical
**Evidence**: Lines 639, 703, 765 — `classification=infrastructure, confidence=high` but no conditional approval
**Code**: See Diagram 1 above for complete trace

**Root Cause**: Two data sources exist for `requires_infrastructure`:

| Source | Where defined | Who reads it | Value for TASK-DB-003 |
|--------|--------------|-------------|----------------------|
| Feature YAML (`FEAT-BA28.yaml`) | TASK-BOOT-214B updated this | `FeatureLoader` → `FeatureTask` model | `[postgresql]` |
| Task `.md` frontmatter | Never updated | `TaskLoader.load_task()` → `AutoBuildOrchestrator` | **absent (→ None → [])** |

The `orchestrate()` method at [autobuild.py:676](guardkit/orchestrator/autobuild.py#L676) does not accept `requires_infrastructure` as a parameter. It always reads from the task file at [autobuild.py:747](guardkit/orchestrator/autobuild.py#L747). The `FeatureOrchestrator._execute_task()` at [feature_orchestrator.py:1521](guardkit/orchestrator/feature_orchestrator.py#L1521) has the `FeatureTask` with `requires_infrastructure=[postgresql]` in memory but has no way to pass it through.

**Dual impact verified**:
1. **Docker lifecycle blocked**: `requires_infra` at [coach_validator.py:1167-1172](guardkit/orchestrator/quality_gates/coach_validator.py#L1167-L1172) is `[]`, so `if requires_infra:` is False, Docker containers are never started
2. **Conditional approval blocked**: `requires_infra` at [coach_validator.py:617-623](guardkit/orchestrator/quality_gates/coach_validator.py#L617-L623) is `[]`, so `bool(requires_infra)` is False, conditional approval cannot fire

**Verification**: Zero Docker-related log lines in 859-line evidence output. No `_is_docker_available`, no `Starting Docker container`, no `requires_infrastructure=... declared but Docker is unavailable`. The Docker lifecycle was never entered.

---

### Finding 4: Identical Feedback Stall — CONSEQUENCE of Finding 3

**Severity**: High (symptom, not root cause)
**Evidence**: Line 775 — `Feedback stall: identical feedback (sig=7e914c9e) for 3 turns`

The stall is a direct consequence of Finding 3. With conditional approval blocked, the Coach returns identical infrastructure-failure feedback every turn. The Player cannot resolve infrastructure failures (it can't start Docker containers or install missing dependencies). The stall detector correctly identifies this as unrecoverable.

---

### Finding 5: Inter-Wave Bootstrap — WORKING AS DESIGNED

**Severity**: Low (informational)
**Evidence**: Lines 372-444

Verified: The inter-wave hook fires correctly ([feature_orchestrator.py:1120-1123](guardkit/orchestrator/feature_orchestrator.py#L1120-L1123)). It re-detects the manifest, re-computes the hash (different because Wave 1 modified the file), and re-executes the install command. The install fails again because the source directory still doesn't exist. This is expected behaviour — the hook is correct, the install-before-ready problem is the issue.

---

### Finding 6: TASK-BOOT-F9C4 (Confidence Promotion) — VERIFIED WORKING

**Severity**: Informational
**Evidence**: Lines 639, 703, 765 — `confidence=high`
**Code**: [coach_validator.py:2294-2300](guardkit/orchestrator/quality_gates/coach_validator.py#L2294-L2300)

The `ModuleNotFoundError` for service-client libraries in `_KNOWN_SERVICE_CLIENT_LIBS` ([coach_validator.py:400-410](guardkit/orchestrator/quality_gates/coach_validator.py#L400-L410)) is promoted to `confidence=high`. Verified working.

---

### Finding 7: TASK-BOOT-7369 (Diagnostic Logging) — NOT VISIBLE (Root Cause Identified)

**Severity**: Medium (upgraded from Low — diagnostic visibility is essential for debugging)
**Evidence**: No DEBUG-level environment_bootstrap lines visible in 859-line output

**Root Cause**: The bootstrap module uses `logging.getLogger(__name__)` ([environment_bootstrap.py:46](guardkit/orchestrator/environment_bootstrap.py#L46)) for its log messages. However, the install subprocess is invoked with `subprocess.run(cmd, capture_output=True)` ([environment_bootstrap.py:621-624](guardkit/orchestrator/environment_bootstrap.py#L621-L624)). This means:

1. **Python logger messages** (e.g., `logger.info("Running install for %s...")`) go to the orchestrator's logging system — their visibility depends on the root logger's level and handler configuration, not `GUARDKIT_LOG_LEVEL` in the environment.
2. **Subprocess output** (`pip install` stdout/stderr) is captured into `proc.stdout`/`proc.stderr` and only logged on failure via `logger.warning()` at [environment_bootstrap.py:634-639](guardkit/orchestrator/environment_bootstrap.py#L634-L639).
3. **No environment propagation**: The `subprocess.run()` call does not pass `env=` with any logging configuration. Even if `GUARDKIT_LOG_LEVEL=DEBUG` is set in the parent process's environment, it is inherited by the child process, but the child process (pip) doesn't read that variable.

**Impact**: If TASK-BOOT-7369's diagnostic logging had been visible, the propagation gap (F3) would have been identified from the first failed run rather than requiring line-by-line code tracing. This is not merely "inconclusive" — it's a diagnostic blind spot.

---

### Finding 8: Misleading Coach Feedback — Player Cannot Resolve (NEW in Revision 3)

**Severity**: Medium
**Evidence**: Truncated feedback message at evidence line ~640: "Tests failed due to infrastructure/environment issues (not code defects). Reme..."

**Analysis**: The Coach correctly classifies the failure as `infrastructure, confidence=high`. But the feedback message tells the Player to "add mocks" for infrastructure dependencies. This is misleading because:

1. The actual failure is `ModuleNotFoundError: No module named 'sqlalchemy'` (or `asyncpg`) — a **missing package**, not a missing database server
2. Even if the Player adds mocks for the database connection, the `import sqlalchemy` statement fires before any mock can intercept it
3. The Player cannot install packages — it can only modify source code
4. The feedback creates an impossible loop: Player is told to fix something it has no mechanism to fix

**Interaction with R1 and R2**: This finding has important implications for the fix strategy:
- **With only R1 (propagation fix)**: `requires_infrastructure=[postgresql]` reaches the Coach. If Docker is available, containers start and set `DATABASE_URL`. But `ModuleNotFoundError` still fires because the package isn't installed. If Docker is NOT available, conditional approval fires and skips the test. The stall is resolved but the test doesn't actually pass.
- **With R1 + R2 (propagation + dependency install)**: Dependencies are installed, Docker containers provide the database, tests can actually execute.
- **With only R2 (dependency install, no R1)**: Dependencies install, but no Docker container starts (propagation gap), so tests fail with `ConnectionRefusedError` instead of `ModuleNotFoundError`. The stall persists.

**Conclusion**: R1 and R2 are co-dependent for actual test success. R1 alone resolves the stall (via conditional approval) but doesn't make tests pass.

---

### Finding 9: Docker Lifecycle Path — UNTESTED (NEW in Revision 3)

**Severity**: Medium (risk)
**Evidence**: Zero Docker-related log lines in all evidence; Docker lifecycle has never been exercised in a real autobuild run

**Analysis**: The Docker lifecycle code at [coach_validator.py:1295-1362](guardkit/orchestrator/quality_gates/coach_validator.py#L1295-L1362) exists and has unit tests ([test_docker_fixtures.py](tests/unit/test_docker_fixtures.py)), including tests for `_start_infrastructure_containers`, `_is_docker_available`, and the integration with `run_independent_tests`. The `docker_fixtures.py` module defines recipes for PostgreSQL, Redis, and MongoDB with non-standard ports, readiness checks, and environment variable exports.

However, this entire path has **never been exercised in a real autobuild run**. The unit tests mock `subprocess.run` — they don't actually start Docker containers. The questions that remain untested:

1. **Is Docker available on the machine?** `_is_docker_available()` runs `docker info` with a 5-second timeout. If Docker Desktop isn't running, this returns False and the code falls back to the warning path at [coach_validator.py:1177-1182](guardkit/orchestrator/quality_gates/coach_validator.py#L1177-L1182).
2. **Do the Docker recipes work?** `get_start_commands("postgresql")` generates `docker run` commands. Are the images pullable? Do the port mappings conflict with existing services?
3. **Does the readiness check work?** PostgreSQL uses `until docker exec guardkit-test-pg pg_isready; do sleep 1; done`. Does this shell command work on the target platform (macOS)?
4. **Is there a docker-compose.yml?** The current approach uses raw `docker run` commands, not docker-compose. If the project has a `docker-compose.yml`, it's ignored.

**Risk assessment**: R1 unblocks the Docker path, but the path itself may fail at any of these points. The impact is mitigated by the conditional approval fallback (if Docker isn't available, the test is skipped with conditional approval), but this means the test is never actually validated against real infrastructure.

---

## BOOT Task Implementation Status

| Task ID | Title | Code Correct? | Effective in FEAT-BA28 run? | Why? |
|---------|-------|:---:|:---:|------|
| TASK-BOOT-E3C0 | Bootstrap phase integration | YES | YES | Fires at line 32 |
| TASK-BOOT-3CAF | Inter-wave bootstrap hook | YES | YES | Fires at line 372 |
| TASK-BOOT-43DE | Coach subprocess sys.executable | YES | YES | [coach_validator.py:1215-1217](guardkit/orchestrator/quality_gates/coach_validator.py#L1215-L1217) |
| TASK-BOOT-214B | requires_infrastructure in FEAT-BA28 | YES | **NO** | YAML updated but `.md` files not — propagation gap |
| TASK-BOOT-6D85 | Wire _docker_available in task dict | YES | **NO** | Correctly wired but never reached (requires_infra=[]) |
| TASK-BOOT-F9C4 | Confidence promotion | YES | YES | Lines 639, 703, 765 |
| TASK-BOOT-7369 | Diagnostic logging | YES | **NO** | Implemented but not visible (capture_output=True, no env propagation) |

---

## Architecture Assessment: 62/100

### SOLID Compliance

| Principle | Score | Notes |
|-----------|:-----:|-------|
| Single Responsibility | 8/10 | Good separation: detector, bootstrapper, coach validator are distinct |
| Open/Closed | 6/10 | Adding new stack support requires modifying `_scan_directory` directly |
| Liskov Substitution | 8/10 | Data models well-behaved |
| Interface Segregation | 7/10 | Bootstrap API clean; coach validator interface growing |
| Dependency Inversion | 4/10 | **Critical**: `AutoBuildOrchestrator` internally loads `requires_infrastructure` from `TaskLoader` instead of accepting it from its caller. The caller (`FeatureOrchestrator`) has the correct value but can't pass it. This violates DI: the high-level orchestrator should inject dependencies, not let the lower-level component resolve them independently. |

### DRY Adherence: 5/10
- `requires_infrastructure` has two sources of truth (YAML and `.md`) with no synchronisation
- `orchestrate()` internally loads data that its caller already has
- Bootstrap state only tracks content hash, not outcome — incomplete state model

### YAGNI Compliance: 8/10
- Bootstrap supports 6 stacks — appropriate
- No over-engineering detected

---

## Recommendations (Technology-Agnostic)

### R1: Fix requires_infrastructure propagation

**Problem**: `orchestrate()` does not accept `requires_infrastructure` as a parameter, forcing it to load from task `.md` frontmatter independently.

**Fix**: Add `requires_infrastructure` as an optional parameter to `orchestrate()` with precedence: explicit parameter > frontmatter > empty list.

```
orchestrate() signature change:
  BEFORE: orchestrate(task_id, requirements, acceptance_criteria, base_branch, task_file_path)
  AFTER:  orchestrate(task_id, requirements, acceptance_criteria, base_branch, task_file_path, requires_infrastructure=None)

Precedence logic inside orchestrate():
  IF requires_infrastructure parameter is provided:
      use it (caller knows best — feature YAML)
  ELSE IF frontmatter has requires_infrastructure:
      use it (single-task mode)
  ELSE:
      use []
```

This is stack-agnostic — `requires_infrastructure` is a list of service names (e.g., `["postgresql"]`, `["redis"]`, `["mongodb"]`) with no technology-specific logic.

**Risk (Revision 3)**: R1 unblocks the Docker lifecycle path, but this path has never been exercised in a real run (Finding 9). Fixing the propagation gap may surface new failures in Docker container startup, readiness checks, or environment variable propagation. This risk is mitigated by the conditional approval fallback: if Docker isn't available, the test is conditionally approved rather than stalling. However, it means the test is skipped, not validated. **R1 alone changes the outcome from "stall" to "conditional approval (skip)" — not to "tests pass".**

**R1 + R2 together**: For TASK-DB-003 tests to actually execute and pass, both R1 (Docker/infrastructure path) and R2 (dependency installation) are required. R1 without R2 still results in `ModuleNotFoundError`. R2 without R1 still has no infrastructure.

**Effort**: 3/10 | **Impact**: Unblocks both Docker lifecycle AND conditional approval

---

### R2: Dependency-only install as primary strategy for incomplete projects

**Problem**: When a dependency manifest exists but the project source tree is incomplete (greenfield timing gap), the bootstrap attempts a full project install that fails. Dependencies needed by later waves are never installed.

**Fix (reframed from Revision 2)**: This is NOT a "fallback" — it should be the **primary strategy** for incomplete projects. The detection logic is simple: does the declared source directory exist?

```
Detection (stack-agnostic):
  IF manifest declares a project/package name:
      check if corresponding source directory exists
  IF source directory does NOT exist:
      → incomplete project, use dependency-only install
  IF source directory EXISTS:
      → complete project, use full install (editable or standard)

Strategy selection on DetectedManifest:
  - New method: is_project_complete() -> bool
      Checks if the source tree required for a full install exists
  - New method: get_dependency_install_commands() -> List[List[str]]
      Returns commands to install declared dependencies individually
  - Existing: install_command (used only when is_project_complete() is True)

Stack-agnostic interface:
  The EnvironmentBootstrapper calls manifest.is_project_complete().
  If False, calls manifest.get_dependency_install_commands().
  If True, uses manifest.install_command as today.

Per-stack is_project_complete() implementations:
  Python (pyproject.toml):  project name dir or src/ layout exists
  Node (package.json):      main/module entry point file exists
  .NET (*.csproj):          always True (dotnet restore doesn't need source)
  Go (go.mod):              always True (go mod download doesn't need source)
  Rust (Cargo.toml):        src/ directory exists
  Flutter (pubspec.yaml):   lib/ directory exists

Per-stack get_dependency_install_commands():
  Python: parse [project.dependencies], return pip install commands
  Node: parse dependencies object, return npm install commands
  .NET: return [dotnet restore] (always works)
  Go: return [go mod download] (always works)
  Rust: return [cargo fetch] (always works)
  Flutter: return [flutter pub get] (always works)
```

**Key design change from Revision 2**: This is framed as detection-first (check completeness, choose strategy) rather than try-fail-fallback. The try-fail approach wastes time on the doomed full install and risks side effects from partial execution.

**Parsing complexity note**: Parsing dependency specifiers from `pyproject.toml` or `package.json` is non-trivial (version constraints, extras, optional dependencies). The implementation should use the simplest possible parser — extract package names and version pins, skip complex specifiers. For Python, `tomllib` (stdlib in 3.11+) can read `[project.dependencies]` which uses PEP 508 format. This doesn't need to handle every edge case — it needs to install `sqlalchemy`, `asyncpg`, `fastapi` etc.

**Effort**: 5/10 | **Impact**: Dependencies installed for incomplete projects

---

### R3: State-aware hash persistence with outcome tracking

**Problem**: `_save_state()` at [environment_bootstrap.py:503](guardkit/orchestrator/environment_bootstrap.py#L503) persists only the content hash, with no record of success or failure. The current state file is `{"content_hash": "<hex>"}`.

**Why "just don't persist on failure" is insufficient** (Revision 3 correction): If the hash isn't saved on failure and the manifest content doesn't change between waves (e.g., manifest was correct from the start, only the source tree was incomplete), the bootstrap will retry and fail identically every inter-wave invocation. In the current FEAT-BA28 case this is moot (Wave 1 modifies the manifest), but it's a real concern for scenarios where the manifest is pre-existing and correct.

**Fix**: Store the outcome alongside the hash, and add a secondary trigger for retry based on worktree structure changes.

```
State file change:
  BEFORE: {"content_hash": "<hex>"}
  AFTER:  {"content_hash": "<hex>", "success": true/false, "source_tree_hash": "<hex>"}

source_tree_hash: SHA-256 of sorted directory listing at the manifest's
  root level (just directory names, not file contents — cheap to compute).
  Captures when new directories are created by waves.

Retry logic:
  IF content_hash differs from saved:
      retry (manifest changed)
  ELSE IF success was True:
      skip (nothing to do)
  ELSE IF source_tree_hash differs from saved:
      retry (worktree structure changed — e.g., new package dir created)
  ELSE:
      skip (same manifest, same tree, same failure — don't retry)
```

**Effort**: 3/10 (increased from 1/10 — requires state model change, not just a line move) | **Impact**: Prevents both stale cache and infinite retries

---

### R4: Structured diagnostic logging for bootstrap and conditional approval

**Problem**: Two diagnostic blind spots exist:
1. **Conditional approval**: When it doesn't fire, there's no log showing which of the 5 conditions failed. This made the propagation gap invisible.
2. **Bootstrap subprocess**: Output is captured but not logged at appropriate levels. TASK-BOOT-7369's diagnostic logging exists but isn't visible because the Python logger configuration doesn't propagate to subprocess output.

**Fix**: Two changes:

```
1. Conditional approval evaluation log (coach_validator.py):
   Add debug log BEFORE the conditional_approval evaluation showing all 5 values:
     failure_class={}, confidence={}, requires_infra={},
     docker_available={}, all_gates_passed={}
   → Makes it immediately obvious which condition blocks approval

2. Bootstrap subprocess output visibility (environment_bootstrap.py):
   On failure, log subprocess stderr at INFO level (not just WARNING).
   On success in verbose mode, log subprocess stdout at DEBUG level.
   This doesn't require environment propagation — just ensures the
   captured output is visible in the orchestrator's log stream.
```

**Effort**: 2/10 | **Impact**: Makes propagation gaps and bootstrap failures immediately visible in future runs

---

### R5: Integration test for cross-component propagation

**Problem**: Unit tests verify individual components but no test exercises the full `FeatureOrchestrator` → `AutoBuildOrchestrator` → `CoachValidator` chain with `requires_infrastructure` flowing through. Existing Docker tests ([test_docker_fixtures.py](tests/unit/test_docker_fixtures.py)) mock `subprocess.run` — they don't exercise the end-to-end flow.

**Fix**: Add an integration test that:
1. Creates a mock feature YAML with `requires_infrastructure: [some-service]`
2. Mocks the `TaskLoader` to return a task without `requires_infrastructure` in frontmatter
3. Verifies that the Coach receives `requires_infrastructure=[some-service]` (after R1 is implemented)
4. Verifies that Docker lifecycle is attempted (mock `_is_docker_available`, verify `_start_infrastructure_containers` is called with the service list)

This test would have caught the propagation gap. It's stack-agnostic — it uses a generic service name.

**Note**: Consider also adding a smoke test that actually runs `_is_docker_available()` (not mocked) to verify Docker is reachable in the CI/test environment. This doesn't need to start containers — just confirm the Docker path can be entered.

**Effort**: 4/10 | **Impact**: Prevents regression of propagation gaps

---

## Recommendation Priority and Dependencies

| # | Recommendation | Fixes Stall? | Fixes Bootstrap? | Tests Pass? | Effort | Risk |
|---|---------------|:---:|:---:|:---:|:---:|:---:|
| R1 | Fix requires_infrastructure propagation | YES (conditional approval) | No | No (skip only) | 3/10 | Medium* |
| R2 | Dependency-only install for incomplete projects | No | YES | Partial | 5/10 | Low |
| R1+R2 | Both together | YES | YES | **YES** | 8/10 | Medium* |
| R4 | Structured diagnostic logging | No (diagnostic) | No | No | 2/10 | None |
| R3 | State-aware hash persistence | No | Defensive | No | 3/10 | None |
| R5 | Integration test for propagation | No (regression) | No | No | 4/10 | None |

*Medium risk on R1: unblocks Docker path that has never been exercised in a real run (Finding 9). May surface new issues.

### Co-dependency Analysis

```
For TASK-DB-003 to STALL-RESOLVE (conditional approval, test skipped):
  R1 alone is sufficient

For TASK-DB-003 tests to ACTUALLY PASS:
  R1 + R2 are both required
  R1 provides: requires_infrastructure=[postgresql] → Docker containers → DATABASE_URL
  R2 provides: sqlalchemy, asyncpg, fastapi installed → import succeeds

For DIAGNOSTIC VISIBILITY:
  R4 alone is sufficient

For CACHE CORRECTNESS:
  R3 alone is sufficient
```

---

## Confidence Assessment

| Finding | Confidence | Verification Method |
|---------|:---:|------|
| sys.executable is correct | **100%** | Direct source inspection: `sys.executable` at line 252 |
| Propagation gap is root cause of stall | **100%** | Traced every code line in chain; `orchestrate()` has no `requires_infrastructure` param |
| Install-before-ready is root cause of bootstrap failure | **100%** | Evidence lines 82-86 show exact error; code confirms editable install for build manifest |
| Docker lifecycle never entered | **100%** | Zero Docker log lines in 859-line evidence; code guard at line 1172 confirms |
| Conditional approval blocked by `bool([])` | **100%** | Short-circuit evaluation at line 623; requires_infra can only be [] given the propagation gap |
| Inter-wave bootstrap works correctly | **95%** | Evidence shows re-execution; hash invalidation inferred (content likely changed) |
| Docker path untested in real runs | **95%** | Zero Docker lines in any evidence; unit tests all mock subprocess; no integration test exercises real Docker |
| Coach feedback misleads Player | **100%** | Feedback says "add mocks" but failure is ModuleNotFoundError — mocks can't fix import errors |
| Diagnostic logging invisible due to capture_output | **90%** | `subprocess.run(capture_output=True)` confirmed at line 624; logger at line 46 uses `getLogger(__name__)` with no explicit handler config |

---

## Recommended Implementation Order

```
Wave 1 (co-dependent, implement together):
  R1 (propagation fix) ───┐
                           ├──> R5 (integration test — validates both R1 and R2)
  R2 (dependency install) ─┘

Wave 2 (independent, can be parallel):
  R4 (diagnostic logging)
  R3 (state-aware hash persistence)
```

**Minimum viable fix**: R1 + R4 (resolves stall via conditional approval, adds diagnostic visibility)
**Full fix for test execution**: R1 + R2 + R4 (dependencies installed, Docker path unblocked, diagnostics visible)
**Complete**: R1 + R2 + R3 + R4 + R5 (all of the above + cache correctness + regression test)

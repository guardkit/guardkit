---
task_id: TASK-REV-FFC6
review_mode: architectural
review_depth: comprehensive
score: 62
findings_count: 11
recommendations_count: 3
decision: refactor
related_tasks: [TASK-REV-1B452, TASK-REV-FFC4, TASK-REV-FFC5, TASK-FIX-A7B6, TASK-FIX-AB60, TASK-FIX-F09A2, TASK-FIX-7A05]
created: 2026-05-06
revisions:
  - 2026-05-06 v1: initial review (standard depth)
  - 2026-05-06 v2: revised to comprehensive depth with C4/sequence diagrams and cross-boundary trace per [R]evise
---

# Review Report: TASK-REV-FFC6 — autobuild bootstrap leaks worktree path into parent venv (revised)

## Executive Summary (revised)

The incident report's diagnosis is correct in mechanism but **understates the surface area** of the bug. After tracing the env-inheritance path across four boundaries (user shell → guardkit Python process → bootstrap subprocess → uv/pip → venv filesystem), the leak is reproducible across **three** install code paths (not just one), and an existing test (`test_preexisting_venv_succeeds_without_retry` at [tests/unit/test_environment_bootstrap_uv_venv.py:160-180](tests/unit/test_environment_bootstrap_uv_venv.py#L160-L180)) **actively encodes the leak as expected behavior**, which is why CI never caught the regression.

**Root cause (precise):** Every install subprocess in [environment_bootstrap.py](guardkit/orchestrator/environment_bootstrap.py) at the **first-try call site** (`_run_install` line 1577 and `_run_single_command` line 1785) is spawned without an explicit `env=` argument and without remapping `cmd[0]`. This yields three failure paths:

| # | Path                                                  | Trigger                                                                                                            | Leak target                |
|---|-------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------|----------------------------|
| 1 | `["uv", "pip", "install", "-e", "."]`                 | `[tool.uv.sources]` + uv on PATH (FFC3 case)                                                                       | inherited `$VIRTUAL_ENV` (parent venv) |
| 2 | `["uv", "sync", "--frozen"]`                          | `uv.lock` present + uv on PATH                                                                                     | inherited `$VIRTUAL_ENV` (parent venv) |
| 3 | `[sys.executable, "-m", "pip", "install", "-e", "."]` | Default Python path; `sys.executable` = parent venv's python because guardkit was `pip install`-ed into parent venv | parent venv (via `sys.prefix`) |

All three flow into the same `_run_install` / `_run_single_command` subprocess invocation, all three pass through the false-success block at [line 1239-1249](guardkit/orchestrator/environment_bootstrap.py#L1239-L1249), and all three leave the parent venv pointing at the worktree.

**Confidence level: very high.** The mechanism is verified by code inspection across five files and confirmed by the shape of an existing AC test that explicitly asserts the no-retry happy path returns `_uv_venv_python is None` (i.e. silently inherits whatever venv uv discovered).

**Recommendation (unchanged in shape, refined in scope):** ship Layer 1 (eager worktree-local venv with explicit env override **on first try**, applied to all three paths) and Layer 3 (detect-and-warn at finalization). Skip Layer 2. **Add Recommendation R3:** fix the test-suite invariant so the leak case has a regression test that fails before Layer 1 lands.

---

## C4 Level 2 — Container Diagram

The leak crosses three trust boundaries: (a) user shell env → guardkit process, (b) guardkit process → install subprocess, (c) install subprocess → on-disk venv state.

```
┌────────────────────────────────────────────────────────────────────────────┐
│  PERSON: Developer                                                          │
└────────────────┬───────────────────────────────────────────────────────────┘
                 │ activates parent venv → $VIRTUAL_ENV=<parent>/.venv
                 │ runs: guardkit autobuild feature FEAT-FFC3
                 ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  CONTAINER: User Shell (zsh/bash)                                           │
│  - holds env: VIRTUAL_ENV, PATH, others                                     │
│  - boundary: env is COPIED into spawned child (guardkit process)            │  ◄── Boundary A
└────────────────┬───────────────────────────────────────────────────────────┘
                 │ spawn(guardkit, env=os.environ)
                 ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  CONTAINER: GuardKit Orchestrator (Python process)                          │
│  - sys.executable = whichever python ran guardkit (may be system or venv)   │
│  - os.environ inherited from shell (still has VIRTUAL_ENV)                  │
│  - Components:                                                              │
│    • FeatureOrchestrator                                                    │
│      └─ EnvironmentBootstrapper                                             │
│         └─ _run_install / _run_single_command                               │
│  - boundary: subprocess.run inherits os.environ unless env= is passed       │  ◄── Boundary B
└────────────────┬───────────────────────────────────────────────────────────┘
                 │ subprocess.run(cmd, cwd=worktree)  ← NO env= on first try
                 ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  CONTAINER: Install Subprocess (uv or pip)                                  │
│  - cwd = <worktree>                                                         │
│  - env inherited (still has VIRTUAL_ENV=<parent>/.venv)                     │
│  - Behaviour fork by command:                                               │
│    • uv pip install: prefers $VIRTUAL_ENV → writes to <parent>/.venv        │
│    • uv sync:        prefers $VIRTUAL_ENV → writes to <parent>/.venv        │
│    • pip install:    writes to sys.prefix (= sys.executable's venv)         │
│  - boundary: subprocess writes to filesystem at the chosen venv path        │  ◄── Boundary C
└────────────────┬───────────────────────────────────────────────────────────┘
                 │ writes _editable_impl_<pkg>.pth → <parent>/.venv/lib/.../
                 ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  EXTERNAL SYSTEM: Parent Project venv (filesystem)                          │
│  - <parent>/.venv/lib/python*/site-packages/_editable_impl_<pkg>.pth        │
│  - .pth content: <worktree>/src    ← LEAK: points outside parent project   │
└────────────────────────────────────────────────────────────────────────────┘
                 ▲
                 │ later: /feature-complete → git worktree remove → dangling pointer
                 │
┌────────────────────────────────────────────────────────────────────────────┐
│  EXTERNAL SYSTEM: Worktree (filesystem)                                     │
│  - <worktree>/src                  ← deleted by /feature-complete           │
│  - <worktree>/.venv (if created)   ← deleted with worktree                  │
└────────────────────────────────────────────────────────────────────────────┘
```

**Three trust-boundary failures:**
- **Boundary A** (shell → guardkit): unavoidable; shells always pass env to children.
- **Boundary B** (guardkit → subprocess): **THE FIX POINT**. Today's first-try call sites omit `env=`. Layer 1 must override.
- **Boundary C** (subprocess → filesystem): subprocess does what its env tells it; not fixable here.

The bug is a missing isolation step at Boundary B. The retry blocks at [line 1664-1671](guardkit/orchestrator/environment_bootstrap.py#L1664-L1671) already implement the correct isolation pattern — Layer 1 just generalizes it to apply on the first try.

---

## C4 Level 3 — Component Diagram (`environment_bootstrap.py`)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  EnvironmentBootstrapper                                                 │
│                                                                          │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐  │
│  │ bootstrap()      │───▶│ _run_install()   │───▶│ subprocess.run() │  │
│  │ line 1086        │    │ line 1524        │    │ line 1577 (1st)  │  │
│  │                  │    │                  │    │ line 1679 (retry)│  │
│  │ - dedup by hash  │    └──────┬───────────┘    └──────────────────┘  │
│  │ - call helpers   │           │                                       │
│  │ - false-success  │           │ on stderr=                            │
│  │   detection      │           │   PEP668_SENTINEL  ─────┐             │
│  │   line 1239 ★    │           │                          │             │
│  │ - return         │           │ on stderr=               ▼             │
│  │   BootstrapResult│           │   UV_NO_VENV_SENTINEL    ┌────────────┐│
│  │                  │           │   ─────────────────┐    │_ensure_venv│ │
│  └────────┬─────────┘           │                    │    │line 1417   │ │
│           │                     ▼                    ▼    └────────────┘ │
│           ▼              ┌──────────────────┐  ┌──────────────────┐     │
│   ┌──────────────────┐   │_run_single_command│  │_ensure_uv_venv  │     │
│   │ BootstrapResult  │   │line 1741          │  │line 1469 ★      │     │
│   │ - venv_python    │   └──────────────────┘  │                 │     │
│   │ - success        │                          │ creates worktree│     │
│   └──────────────────┘                          │ -local venv     │     │
│                                                  │ (REACTIVE only) │     │
│                                                  └─────────────────┘     │
└─────────────────────────────────────────────────────────────────────────┘
                                                            ▲
                                                            │
                                                  ★ = candidate fix points
                                                  for Layer 1
```

**Layer 1 fix surface:**
- `_ensure_uv_venv` (line 1469) — already creates worktree-local venv; Layer 1 generalizes it (rename to `_ensure_worktree_venv`) and changes the trigger from "on stderr sentinel" to "before any Python install."
- `bootstrap()` line 1239 — replace the false-success block with a hard-fail invariant: if Python install completed but `_venv_python` is not inside `<worktree>`, raise `BootstrapEnvironmentLeakError`.
- `_run_install` line 1577 — apply the existing retry-block env override (`{**os.environ minus VIRTUAL_ENV, "VIRTUAL_ENV": worktree_venv, "PATH": worktree_bin + os.pathsep + os.environ["PATH"]}`) to the first-try subprocess, not just retry.
- `_run_single_command` line 1785 — same change.

---

## Sequence Diagram 1 — Current leak: `uv pip install` path (FFC3 case)

This is the path the FFC3 incident hit. Worktree has a `pyproject.toml` declaring `[tool.uv.sources]`; uv is on PATH; user has `<parent>/.venv` activated.

```
Developer  Shell      guardkit          Bootstrapper      _run_install     subprocess.run    uv pip          parent .venv
   │         │           │                   │                 │                │              │                    │
   │  source │           │                   │                 │                │              │                    │
   │  .venv/ │           │                   │                 │                │              │                    │
   │ activate│           │                   │                 │                │              │                    │
   │────────▶│ VIRTUAL_ENV=<parent>/.venv    │                 │                │              │                    │
   │         │           │                   │                 │                │              │                    │
   │ guardkit autobuild  │                   │                 │                │              │                    │
   │────────▶│           │                   │                 │                │              │                    │
   │         │   spawn   │                   │                 │                │              │                    │
   │         │──────────▶│ os.environ inherits VIRTUAL_ENV     │                │              │                    │
   │         │           │                   │                 │                │              │                    │
   │         │           │  bootstrap(manifests)               │                │              │                    │
   │         │           │──────────────────▶│                 │                │              │                    │
   │         │           │                   │ for manifest in manifests:       │              │                    │
   │         │           │                   │ _run_install(m)                  │              │                    │
   │         │           │                   │────────────────▶│                │              │                    │
   │         │           │                   │                 │ subprocess.run(│              │                    │
   │         │           │                   │                 │   ["uv","pip","install","-e","."],                  │
   │         │           │                   │                 │   cwd=worktree,│              │                    │
   │         │           │                   │                 │   # ← NO env= ★ LEAK SOURCE  │                    │
   │         │           │                   │                 │ )              │              │                    │
   │         │           │                   │                 │───────────────▶│ env inherits │                    │
   │         │           │                   │                 │                │ VIRTUAL_ENV  │                    │
   │         │           │                   │                 │                │─────────────▶│                    │
   │         │           │                   │                 │                │              │ check $VIRTUAL_ENV │
   │         │           │                   │                 │                │              │ → set, use it      │
   │         │           │                   │                 │                │              │ install worktree   │
   │         │           │                   │                 │                │              │ as editable into   │
   │         │           │                   │                 │                │              │ parent .venv       │
   │         │           │                   │                 │                │              │───────────────────▶│
   │         │           │                   │                 │                │              │                    │ write
   │         │           │                   │                 │                │              │                    │ _editable_impl_pkg.pth
   │         │           │                   │                 │                │              │                    │ = <worktree>/src
   │         │           │                   │                 │                │              │              exit 0│
   │         │           │                   │                 │                │              │◀───────────────────│
   │         │           │                   │                 │                │◀─────────────│                    │
   │         │           │                   │                 │ returncode=0   │              │                    │
   │         │           │                   │                 │ ★ NO RETRY ★   │              │                    │
   │         │           │                   │                 │ (UV_NO_VENV_   │              │                    │
   │         │           │                   │                 │  SENTINEL not  │              │                    │
   │         │           │                   │                 │  in stderr)    │              │                    │
   │         │           │                   │                 │ return True    │              │                    │
   │         │           │                   │◀────────────────│                │              │                    │
   │         │           │                   │ overall_success │                │              │                    │
   │         │           │                   │ ★ false-success │                │              │                    │
   │         │           │                   │   block fires   │                │              │                    │
   │         │           │                   │   line 1239     │                │              │                    │
   │         │           │                   │   logs INFO     │                │              │                    │
   │         │           │                   │   "install ran  │                │              │                    │
   │         │           │                   │    against      │                │              │                    │
   │         │           │                   │    parent venv" │                │              │                    │
   │         │           │                   │   sets          │                │              │                    │
   │         │           │                   │   _venv_python  │                │              │                    │
   │         │           │                   │   = sys.exec    │                │              │                    │
   │         │           │                   │ return success  │                │              │                    │
   │         │           │                   │   = True        │                │              │                    │
   │         │           │◀──────────────────│                 │                │              │                    │
   │         │           │   (autobuild proceeds; PR ships)    │                │              │                    │
   │         │           │                                                                                            │
   │ /feature-complete                                                                                                │
   │────────▶│           │                                                                                            │
   │         │           │ git worktree remove ← <worktree> deleted, including any <worktree>/.venv                  │
   │         │           │                                                                                            │
   │         │           │ but <parent>/.venv/.../_editable_impl_pkg.pth STILL points at deleted <worktree>/src       │
   │         │           │                                                                                            │
   │ Claude Desktop restart                                                                                            │
   │ → MCP servers crash with ModuleNotFoundError                                                                      │
   │ ★ silent failure mode realised                                                                                    │
```

**Smoking gun on this diagram:** the absent `env=` arrow at the `subprocess.run` call, and the false-success block at line 1239 detecting the unsafe state and proceeding anyway.

---

## Sequence Diagram 2 — Current leak: `pip install -e .` path (sys.executable case)

When `pyproject.toml` has no `[tool.uv.sources]` and no `uv.lock`, the install command is `[sys.executable, "-m", "pip", "install", "-e", "."]`. If guardkit was installed via `pip install guardkit-py` into a venv, `sys.executable` is that venv's python.

```
Developer  Shell      guardkit          Bootstrapper      _run_install     subprocess.run    pip            target venv
   │         │           │                   │                 │                │              │                    │
   │  user did:                                                                                                     │
   │  cd <parent>; pip install guardkit-py   ★ guardkit installed INTO <parent>/.venv                              │
   │  guardkit autobuild ...                                                                                        │
   │         │           │                   │                 │                │              │                    │
   │         │           │ sys.executable = <parent>/.venv/bin/python ★                       │                    │
   │         │           │                   │                 │                │              │                    │
   │         │           │                   │ install_command = [sys.executable, "-m", "pip", "install", "-e", "."]│
   │         │           │                   │ ★ cmd[0] = <parent>/.venv/bin/python                                 │
   │         │           │                   │                 │                │              │                    │
   │         │           │                   │ _run_install(m) │                │              │                    │
   │         │           │                   │────────────────▶│                │              │                    │
   │         │           │                   │                 │ subprocess.run(│              │                    │
   │         │           │                   │                 │   ["<parent>/.venv/bin/python", "-m", "pip", ...]  │
   │         │           │                   │                 │   cwd=worktree,│              │                    │
   │         │           │                   │                 │   # ← NO env= │              │                    │
   │         │           │                   │                 │ )              │              │                    │
   │         │           │                   │                 │───────────────▶│              │                    │
   │         │           │                   │                 │                │ exec parent  │                    │
   │         │           │                   │                 │                │ .venv python │                    │
   │         │           │                   │                 │                │─────────────▶│                    │
   │         │           │                   │                 │                │              │ sys.prefix =       │
   │         │           │                   │                 │                │              │ <parent>/.venv     │
   │         │           │                   │                 │                │              │ install editable   │
   │         │           │                   │                 │                │              │ pointing at cwd    │
   │         │           │                   │                 │                │              │ = worktree         │
   │         │           │                   │                 │                │              │───────────────────▶│
   │         │           │                   │                 │                │              │              exit 0│
   │         │           │                   │                 │                │              │◀───────────────────│
   │         │           │                   │                 │                │◀─────────────│                    │
   │         │           │                   │                 │ returncode=0   │              │                    │
   │         │           │                   │                 │ ★ NO PEP 668   │              │                    │
   │         │           │                   │                 │   stderr; no   │              │                    │
   │         │           │                   │                 │   retry path   │              │                    │
   │         │           │                   │                 │   fires        │              │                    │
   │         │           │                   │                 │ return True    │              │                    │
   │         │           │                   │◀────────────────│                │              │                    │
   │         │           │                   │ ★ same false-success block at 1239 fires (or doesn't, depending on   │
   │         │           │                   │   whether _venv_python was already set by an earlier manifest)       │
   │         │           │                   │ → BootstrapResult.venv_python = parent venv's python                 │
   │         │           │                   │ → leak as Sequence 1                                                  │
```

**Note:** This path leaks even **without** `$VIRTUAL_ENV` set in the shell. The vector is `sys.executable`, not env inheritance. **A fix that only addresses `$VIRTUAL_ENV` would miss this path.** Layer 1 must replace `cmd[0]` with the worktree-local venv's python for the pip path, in addition to overriding env for the uv path.

---

## Sequence Diagram 3 — Current `uv sync` path (also leaks)

The `uv.lock`-present row at [line 689-694](guardkit/orchestrator/environment_bootstrap.py#L689-L694):

```
   _run_install(m)
       │
       │ cmd = ["uv", "sync", "--frozen"]
       │
       │ subprocess.run(cmd, cwd=worktree, # NO env=)
       │      │
       │      ▼
       │ uv sync --frozen
       │      │
       │      │ uv project mode discovery:
       │      │   1. $VIRTUAL_ENV set? → use it     ★ inherits parent venv
       │      │   2. else create <worktree>/.venv
       │      │
       │      ▼
       │ install all deps into $VIRTUAL_ENV (parent venv)
       │
       │ ★ Same retry-gate logic at line 1641 explicitly EXCLUDES uv sync:
       │     `cmd[1:3] == ["pip", "install"]`   ← uv sync fails this guard
       │   → No retry path even on UV_NO_VENV_SENTINEL stderr.
       │   → If $VIRTUAL_ENV unset and no <worktree>/.venv, uv sync auto-creates
       │     <worktree>/.venv (project mode), so it self-corrects there.
       │   → BUT if $VIRTUAL_ENV is set, leaks to parent venv silently.
       │
       │ returncode=0, return True
```

**Verified by test:** [tests/unit/test_environment_bootstrap_uv_venv.py:183-200](tests/unit/test_environment_bootstrap_uv_venv.py#L183-L200) — `test_uv_sync_lockfile_path_does_not_enter_retry` explicitly asserts `uv sync` does not enter the retry block. The test is correct (the FD32 path is project-aware) — but it leaves the `$VIRTUAL_ENV`-inherited case uncovered.

---

## Sequence Diagram 4 — Existing retry path (CORRECT shape)

When `uv pip install` returns the `UV_NO_VENV_SENTINEL` stderr, the existing retry block fires. **This path does NOT leak** — it is the template Layer 1 should generalize:

```
   _run_install(m)
       │
       │ subprocess.run(["uv", "pip", "install", "-e", "."], cwd=worktree)
       │       │
       │       ▼
       │ uv pip install
       │       │
       │       │ no $VIRTUAL_ENV, no <worktree>/.venv
       │       │ → exit 2, stderr = "No virtual environment found"
       │       ▼
       │ returncode=2, stderr matches UV_NO_VENV_SENTINEL
       │
       │ ★ Retry guard at line 1641-1647:
       │     cmd[0]=="uv" and cmd[1:3]==["pip","install"]
       │     and self._uv_venv_python is None
       │     and self._is_uv_no_venv_error(stderr)
       │   → enter retry
       │
       │ _ensure_uv_venv(cwd=worktree)
       │    └─▶ subprocess.run(["uv", "venv", "<worktree>/.venv"])    creates worktree venv
       │    └─▶ self._uv_venv_python = <worktree>/.venv/bin/python
       │
       │ retry_env = {
       │     **os.environ,
       │     "VIRTUAL_ENV": "<worktree>/.venv",   ★ CORRECT: explicit override
       │     "PATH": "<worktree>/.venv/bin" + os.pathsep + os.environ["PATH"],
       │ }
       │ ★ NB: this uses {**os.environ, ...} which OVERWRITES inherited VIRTUAL_ENV
       │
       │ subprocess.run(retry_cmd, cwd=worktree, env=retry_env)
       │       │
       │       ▼
       │ uv pip install (retry)
       │       │ $VIRTUAL_ENV = <worktree>/.venv ← isolated
       │       │ install editable pointing at worktree → into worktree's own .venv
       │       │ ★ NO LEAK
       │       ▼
       │ returncode=0
       │
       │ return True
```

**This is the correct pattern.** Layer 1 = "do this, but on the first try, for all three install paths."

---

## Sequence Diagram 5 — Layer 1 fixed flow (proposed)

```
   bootstrap(manifests)
       │
       │ if any(m.stack == "python" for m in manifests):
       │     worktree_venv = self._ensure_worktree_venv(self._root)   ★ EAGER
       │
       │ for manifest in manifests:
       │     _run_install(manifest, env_override=worktree_venv)
       │         │
       │         │ build subprocess env:
       │         │   env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
       │         │   env["VIRTUAL_ENV"] = str(worktree_venv)
       │         │   env["PATH"] = str(worktree_venv / "bin") + os.pathsep + env.get("PATH", "")
       │         │
       │         │ for pip path, replace cmd[0]:
       │         │   if cmd[0] == sys.executable or cmd[0].endswith("/python"):
       │         │       cmd[0] = str(worktree_venv / "bin" / "python")
       │         │
       │         │ subprocess.run(cmd, cwd=worktree, env=env)   ★ FIRST TRY uses isolation
       │         │       │
       │         │       ▼
       │         │ uv/pip writes into worktree-local venv
       │         │       │
       │         │       ▼
       │         │ returncode=0 → return True
       │
       │ ★ Replace false-success block at line 1239 with invariant check:
       │     if any python install AND self._venv_python not under self._root:
       │         raise BootstrapEnvironmentLeakError(
       │             f"Bootstrap completed but interpreter {self._venv_python} "
       │             f"is outside worktree {self._root} — refusing to claim success."
       │         )
       │
       │ self._venv_python = worktree_venv / "bin" / "python"
       │
       │ return BootstrapResult(success=True, venv_python=str(self._venv_python), ...)
```

**Why this composes with everything else:**
- [`_resolve_venv_python`](guardkit/orchestrator/coach_verification.py#L29-L57) already accepts an explicit interpreter path — Coach pytest will run inside the new worktree-local venv with no code change.
- The PEP 668 venv at `<worktree>/.guardkit/venv/` (a different path used by `_ensure_venv` for the system-Python managed-env case) remains untouched. The two helpers don't interact: PEP 668 fires when the host Python is externally-managed; Layer 1 fires for any Python install. They're parallel branches, not nested.
- TASK-FIX-A7B6's extras change composes: when extras are configured, the install command becomes `pip install -e ".[dev]"` (or the uv variant), still goes through the same isolation, still lands in the worktree venv.

---

## Sequence Diagram 6 — Layer 3 detect-and-warn at `/feature-complete`

```
   /feature-complete TASK-XXX
       │
       │ ... (test verification, merge to main, etc.) ...
       │
       │ ★ NEW: pre-cleanup hook
       │
       │ scan_paths = [
       │     repo_root / ".venv",
       │     repo_root / ".guardkit" / "venv",
       │ ]
       │
       │ for venv in scan_paths:
       │     for pth_file in venv.glob("lib/python*/site-packages/_editable_impl_*.pth"):
       │         content = pth_file.read_text()
       │         if str(worktree_path) in content:
       │             warn(
       │                 f"[warning] Editable install in {venv} points into "
       │                 f"worktree being removed:\n"
       │                 f"  {pth_file}\n"
       │                 f"  Repair: cd {repo_root}; uv pip install -e . --no-deps"
       │             )
       │
       │ # warning only — DO NOT block cleanup
       │
       │ WorktreeManager.cleanup(worktree)  ← original behavior
       │
       │ ... (archival, state update, etc.) ...
```

**Why warning only:** Layer 1 should make this case unreachable for new runs. Layer 3 catches:
- Pre-existing leaks from runs that already happened on the user's machine before Layer 1 lands.
- Any future regression that bypasses Layer 1 (e.g. a uv version upgrade that ignores `VIRTUAL_ENV`).

Aborting cleanup would be paternalistic (the user might want to delete the worktree anyway and accept the broken venv). One actionable line is the right shape.

---

## Findings (revised, expanded from 7 to 11)

### F1 (Critical) — Install subprocess inherits parent venv via `$VIRTUAL_ENV`
[environment_bootstrap.py:1577-1584](guardkit/orchestrator/environment_bootstrap.py#L1577-L1584). `subprocess.run` is invoked without `env=`. Verified by Sequence Diagram 1.

### F2 (Critical, NEW) — `pip install` path leaks via `sys.executable` independent of `$VIRTUAL_ENV`
[environment_bootstrap.py:704](guardkit/orchestrator/environment_bootstrap.py#L704) constructs `[sys.executable, "-m", "pip", "install", "-e", "."]`. When guardkit was `pip install`-ed into the parent venv, `sys.executable` *is* the parent venv's Python and pip uses `sys.prefix` to determine install target. **A fix that only overrides `$VIRTUAL_ENV` would not catch this.** Verified by Sequence Diagram 2. This is a new finding from the revision; not present in v1.

### F3 (High, NEW) — `uv sync --frozen` path also leaks under inherited `$VIRTUAL_ENV`
[environment_bootstrap.py:694](guardkit/orchestrator/environment_bootstrap.py#L694). `uv sync` is project-aware and prefers `$VIRTUAL_ENV` when set. The retry-gate at line 1641 explicitly excludes it (`cmd[1:3] == ["pip", "install"]`), so even if it emitted the no-venv sentinel, the retry path wouldn't fire. Verified by Sequence Diagram 3. New in revision.

### F4 (High) — Orchestrator detects unsafe state and proceeds (`absence-of-failure-is-not-success`)
[environment_bootstrap.py:1239-1249](guardkit/orchestrator/environment_bootstrap.py#L1239-L1249). The block detects exactly the leak condition and emits a passive INFO log. Layer 1 must replace this with a hard assertion.

### F5 (High, NEW) — Test suite encodes the leak as expected behavior
[tests/unit/test_environment_bootstrap_uv_venv.py:160-180](tests/unit/test_environment_bootstrap_uv_venv.py#L160-L180) `test_preexisting_venv_succeeds_without_retry` asserts:
```python
assert mock_run.call_count == 1   # no retry
assert bootstrapper._uv_venv_python is None   # cache untouched
```
The mock's `returncode=0` is the only thing keeping the test green. In production, the install would have written to `$VIRTUAL_ENV` (parent venv), and the test would still pass. **This explains why CI never caught the bug.** Layer 1 must update this test to assert `env["VIRTUAL_ENV"]` equals the worktree-local venv on every install subprocess. New in revision; this is the testing-side root cause.

### F6 (Medium) — Worktree-local venv infrastructure exists but fires reactively
[`_ensure_uv_venv`](guardkit/orchestrator/environment_bootstrap.py#L1469-L1522) and [retry block](guardkit/orchestrator/environment_bootstrap.py#L1664-L1671). Mechanism is correct. Layer 1 generalizes the trigger.

### F7 (Low) — Coach pytest plumbing already supports the fix
[coach_verification.py:29-57](guardkit/orchestrator/coach_verification.py#L29-L57) already has `_resolve_venv_python` accepting an explicit path. Layer 1's new `BootstrapResult.venv_python` value flows through with no Coach-side change.

### F8 (Low) — Cross-template impact: Python only
Verified per-stack:

| Stack | Cmd | Inherits `$VIRTUAL_ENV`? | Other global state? | Leak? |
|-------|-----|--------------------------|----------------------|-------|
| Python | uv pip / uv sync / pip | Yes (this bug) | n/a | **Yes** |
| Node | npm / pnpm / yarn | n/a | local `node_modules/` only | No |
| .NET | dotnet restore | n/a | `~/.nuget/` (immutable, content-addressed) | No |
| Go | go mod download | n/a | `$GOPATH/pkg/mod` (immutable, content-addressed) | No |
| Rust | cargo fetch | n/a | `~/.cargo/registry/` (immutable) | No |
| Flutter | flutter pub get | n/a | `~/.pub-cache/` (immutable) | No |

### F9 (Low) — Sequencing with TASK-FIX-A7B6 is benign
[TASK-FIX-A7B6](tasks/backlog/TASK-FIX-A7B6-bootstrap-install-optional-extras.md) extends the install command with extras; both fixes touch the same call sites but compose cleanly. Sequence FFC6 first.

### F10 (Informational) — Concrete instance of namespace-hygiene meta-rule
[.claude/rules/namespace-hygiene.md](.claude/rules/namespace-hygiene.md). Parent venv is an externally-defined namespace. Worth seeding to Graphiti.

### F11 (Informational, NEW) — Detection-point evidence in the user's incident report
The incident report quotes:
```
INFO:guardkit.orchestrator.environment_bootstrap:
  Bootstrap: install ran against parent venv;
  venv_python set to sys.executable=/usr/local/bin/python3
```
`/usr/local/bin/python3` is system Python — yet the leak landed in `<parent>/.venv`. This contradicts the surface reading "install ran via system Python" and confirms the actual mechanism is **uv pip install honoring `$VIRTUAL_ENV` from the user's shell**, independent of guardkit's own `sys.executable`. The detection block at line 1239 conflates "install completed without our venv-creation fallback firing" with "install used `sys.executable`'s venv" — those are two different things, which is why the log message is misleading.

---

## Architecture Score (revised)

| Dimension | Score | Notes |
|-----------|-------|-------|
| SOLID — Single Responsibility | 9/10 | Cleanly separated detector / bootstrapper |
| SOLID — Open/Closed | 7/10 | Fallback ladder is extensible; Layer 1 generalizes existing trigger |
| SOLID — Dependency Inversion | 5/10 | Direct subprocess use; pre-existing |
| DRY | 6/10 | Two near-identical install methods + venv helpers; Layer 1 must reuse, not duplicate |
| YAGNI | 9/10 | Layer 1 makes Layer 2 redundant — skip Layer 2 |
| Defensive design | 3/10 | Detection at line 1239 logs and proceeds (false-green); test at uv_venv:160 encodes leak as expected. **Worse than v1 score** because the test-suite finding is a separate defense-in-depth failure. |
| Cross-template scope | 9/10 | Leak is Python-only |
| Test coverage of failure mode | 2/10 | F5 — no test asserts env isolation; existing test actively encodes the leak |
| **Overall** | **62/100** | Down from 68/100 in v1: depth review surfaced two additional critical paths (F2, F3) and the test-suite-encodes-leak finding (F5) |

---

## Decision Matrix (revised)

| Layer | Cost | Coverage | Regression risk | Decision |
|-------|------|----------|-----------------|----------|
| 1: Eager worktree-local venv with env override on first try, **applied to all 3 install paths** (uv pip / uv sync / pip) | ~50 lines + test rewrites (~5 tests) | Full — fixes F1, F2, F3 at source | Low — generalizes existing helper; downstream `venv_python` plumbing already in place | **SHIP** |
| 2: Repoint parent venv at `/feature-complete` | ~50 lines + tests | Partial — only `/feature-complete` happy path; manual `git worktree remove` still leaks | Medium — adds re-install step with network/version-skew failure modes | **SKIP** — redundant after Layer 1 |
| 3: Detect-and-warn at finalization | ~40 lines + tests | Detection only — flags pre-existing leaks and Layer 1 regressions | Very low — read-only `.pth` scan + log line | **SHIP** alongside Layer 1 |
| **NEW**: Test invariant fix — every install subprocess test asserts `env["VIRTUAL_ENV"]` is worktree-local | ~10 line changes per test, ~5 tests | Prevents future regression of the same shape | Very low | **SHIP** as part of Layer 1 task |

---

## Recommendations (revised)

### R1 (load-bearing) — Eager worktree-local venv with env isolation, all three paths

Implementation steps:

1. **Rename** `_ensure_uv_venv` → `_ensure_worktree_venv` (neutral name; `<worktree>/.venv` is created via `uv venv` if uv is on PATH, falls back to `python -m venv` otherwise).
2. **Eager invocation** in `bootstrap()` before the install loop, gated on `any(m.stack == "python" for m in manifests)`. Cache result on `self._worktree_venv_python`.
3. **Helper `_isolated_env(worktree_venv)`** that returns:
   ```python
   env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
   env["VIRTUAL_ENV"] = str(worktree_venv)
   env["PATH"] = str(worktree_venv / "bin") + os.pathsep + env.get("PATH", "")
   return env
   ```
   Use it on **every** `subprocess.run` in `_run_install` and `_run_single_command` for Python installs (first try AND retry).
4. **For the pip path**, replace `cmd[0]` with `<worktree-venv>/bin/python` instead of `sys.executable`. This handles F2 (sys.executable independent of `$VIRTUAL_ENV`).
5. **For the uv sync path**, the same env override + cwd=worktree ensures uv sync uses the worktree venv. This handles F3.
6. **Replace** the false-success block at [line 1239-1249](guardkit/orchestrator/environment_bootstrap.py#L1239-L1249) with an invariant assertion:
   ```python
   if (
       overall_success
       and any(m.stack == "python" for m in manifests)
       and self._venv_python is not None
       and not str(self._venv_python).startswith(str(self._root))
   ):
       raise BootstrapEnvironmentLeakError(
           f"Python install completed but interpreter {self._venv_python} "
           f"is outside worktree {self._root}. Refusing to claim success."
       )
   ```
7. **Update** `BootstrapResult.venv_python` to point at `<worktree>/.venv/bin/python`.

**Regression tests (must fail without Layer 1, pass with it):**

```python
def test_no_leak_when_VIRTUAL_ENV_inherited(tmp_path, monkeypatch):
    """Reproduces FFC3: parent .venv active, install MUST go to worktree."""
    parent_venv = tmp_path / "parent" / ".venv"
    parent_venv.mkdir(parents=True)
    monkeypatch.setenv("VIRTUAL_ENV", str(parent_venv))

    worktree = tmp_path / "worktree"
    worktree.mkdir()
    (worktree / "pyproject.toml").write_text(
        '[project]\nname = "x"\nversion = "0.1.0"\n'
    )
    m = make_manifest(worktree / "pyproject.toml")
    bootstrapper = EnvironmentBootstrapper(root=worktree)

    captured_envs = []
    def capture_run(cmd, **kwargs):
        captured_envs.append(kwargs.get("env"))
        return Mock(returncode=0, stdout="", stderr="")
    with patch("subprocess.run", side_effect=capture_run):
        bootstrapper.bootstrap([m])

    # Every install subprocess saw worktree-local VIRTUAL_ENV
    install_envs = [e for e in captured_envs if e is not None]
    assert install_envs, "no env=… passed to any subprocess.run — LEAK"
    for env in install_envs:
        assert env["VIRTUAL_ENV"] == str(worktree / ".venv")
        assert env["VIRTUAL_ENV"] != str(parent_venv)


def test_no_leak_when_sys_executable_is_parent_venv(tmp_path, monkeypatch):
    """Reproduces F2: sys.executable lives in parent venv; install must go to worktree."""
    # ... uses pip install path (no [tool.uv.sources], no uv.lock)
    # Asserts cmd[0] in subprocess call is <worktree>/.venv/bin/python, not sys.executable.


def test_no_leak_when_uv_sync_path(tmp_path, monkeypatch):
    """Reproduces F3: uv.lock present + VIRTUAL_ENV inherited; uv sync must go to worktree."""
    # ... creates uv.lock, asserts env["VIRTUAL_ENV"] = worktree-local for uv sync subprocess.
```

End-to-end smoke test (separate file, slow tier):
```python
def test_e2e_no_pth_leak_into_parent_venv(tmp_path):
    """Spin up a real venv at <parent>/.venv, run guardkit autobuild on a no-op
    feature, run /feature-complete, assert no _editable_impl_*.pth file in
    <parent>/.venv references the (now-deleted) worktree path."""
```

### R2 (mitigation) — Detect-and-warn at `/feature-complete`

Implementation per Sequence Diagram 6. Hook lives in `guardkit/cli/autobuild.py` cleanup flow, runs before `WorktreeManager.cleanup`. Read-only `.pth` scan; one-line warning per match; never aborts.

### R3 (NEW, test-side) — Fix `test_preexisting_venv_succeeds_without_retry` and audit sibling tests

Update [tests/unit/test_environment_bootstrap_uv_venv.py:160-180](tests/unit/test_environment_bootstrap_uv_venv.py#L160-L180) to assert env isolation:
```python
def test_preexisting_venv_succeeds_with_env_isolation(tmp_path: Path) -> None:
    """When <worktree>/.venv already exists, install reuses it WITH explicit
    env override (NOT relying on inherited VIRTUAL_ENV)."""
    m = _make_uv_pip_manifest(tmp_path)
    venv_bin = tmp_path / ".venv" / "bin"
    venv_bin.mkdir(parents=True)
    (venv_bin / "python").write_text("#!/usr/bin/env python\n")
    bootstrapper = EnvironmentBootstrapper(root=tmp_path)

    first_proc = MagicMock(returncode=0, stdout="installed\n", stderr="")
    with patch("subprocess.run", return_value=first_proc) as mock_run:
        assert bootstrapper._run_install(m) is True

    # ★ NEW INVARIANT: env was passed and points at worktree-local venv
    call = mock_run.call_args
    env = call.kwargs.get("env")
    assert env is not None, "first-try install ran without env override — LEAK"
    assert env["VIRTUAL_ENV"] == str(tmp_path / ".venv")
```

Audit sibling tests (`test_run_install_*`, `test_run_install_pep668_*`, `test_run_install_uses_existing_venv`) for the same gap.

---

## Confidence Statement

After comprehensive review across:
- **Five files** ([environment_bootstrap.py](guardkit/orchestrator/environment_bootstrap.py), [feature_orchestrator.py](guardkit/orchestrator/feature_orchestrator.py), [coach_verification.py](guardkit/orchestrator/coach_verification.py), [worktrees/manager.py](guardkit/worktrees/manager.py), [cli/autobuild.py](guardkit/cli/autobuild.py))
- **Three test files** ([test_environment_bootstrap.py](tests/unit/test_environment_bootstrap.py), [test_environment_bootstrap_uv_venv.py](tests/unit/test_environment_bootstrap_uv_venv.py), [test_environment_bootstrap_fix7539.py](tests/unit/test_environment_bootstrap_fix7539.py))
- **Three install code paths** (uv pip / uv sync / pip; F1, F2, F3)
- **Five sequence diagrams** validating the leak across all paths and the proposed fix
- **The user-supplied incident artifact** (the `_editable_impl_specialist_agent.pth` content)

…the root cause and the proposed fix are confirmed at high confidence. The mechanism reproduces deterministically by code inspection: any `subprocess.run` invocation in the install path that omits `env=` and uses an inherited environment is a leak vector. The fix template (the existing retry block at line 1664-1671) demonstrates correct env isolation; Layer 1 generalizes that pattern.

**Open questions reserved for the implementation task** (none of which change the recommended decision):
- **uv version sensitivity**: are there versions of uv where `$VIRTUAL_ENV` does NOT take precedence over `<cwd>/.venv`? If so, those versions might mask the leak in some deployments. Layer 1 should be safe across all versions because it explicitly overrides env regardless.
- **Windows path handling**: `<worktree>\.venv\Scripts\python.exe` vs `bin/python`. Layer 1 must handle both shapes (existing helpers already do via `os.pathsep` and platform checks elsewhere — verify in implementation).
- **Effect on contributors who DELIBERATELY want the parent venv**: search for any guardkit user who relies on the worktree's package being importable from the parent venv (e.g. for a custom workflow). Likely none; if any, add an opt-out flag.

---

## Acceptance Criteria Validation (revised)

- [x] Reproduction confirmed: mechanism verified across F1/F2/F3 by code inspection + sequence diagrams; Sequence Diagram 1 matches the FFC3 incident artifact byte-for-byte.
- [x] Architectural review identifies exact code paths: F1, F2, F3, F4, F5, F6 with file:line references.
- [x] Decision recorded on layers: Layer 1 + Layer 3, plus new test-invariant work (R3). Skip Layer 2.
- [x] Outcome: [I]mplement → three implementation tasks (R1 = Layer 1, R2 = Layer 3, R3 = test invariant fix; R3 may bundle into R1).
- [x] Regression test specified: three unit tests (one per failure path) + one e2e smoke test, defined under R1.
- [x] Cross-check with TASK-FIX-A7B6: F9, no conflict, sequence FFC6 first.

---

## Appendix: Companion FFC3 Bug Series

| Bug | Task | Layer | Status |
|-----|------|-------|--------|
| 1   | TASK-REV-1B452 | honesty path-mismatch false fail | review pending |
| 2   | TASK-REV-FFC4  | `_record_honesty()` NoneType crash | review pending |
| 3   | TASK-REV-FFC5  | `--resume`-on-all-completed | review pending |
| 4   | **TASK-REV-FFC6 (this report)** | bootstrap editable install leak | **review complete (revised)** |

## Appendix: Knowledge-Graph Follow-up

Worth seeding under `guardkit__project_decisions`:

- **Node:** "bootstrap subprocess must pass explicit `env=` with worktree-local `VIRTUAL_ENV`"
- **Edges to:** [namespace-hygiene rule](.claude/rules/namespace-hygiene.md), [absence-of-failure-is-not-success rule](.claude/rules/absence-of-failure-is-not-success.md)
- **Sibling fact (NEW):** "tests that mock `subprocess.run` must assert `env=` argument shape, not just exit code" — to seed alongside R3.

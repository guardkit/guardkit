# Revision Request for TASK-REV-4D57

## Why This Needs Further Revision

The review correctly identified `ModuleNotFoundError: No module named 'sqlalchemy'` as the actual error and correctly traced the SDK subprocess environment mismatch. However, **the review stops one level too early in the root cause chain** and proposes a workaround (R1: switch to subprocess) rather than the actual fix.

The review also scopes the problem as Python-specific. GuardKit is a universal orchestrator that works across .NET, Python, React, TypeScript, Node, Go, Rust, Flutter, and more. The root cause and solution must be project-type-aware.

---

## The Actual Root Cause: AutoBuild Has No Environment Bootstrap Phase

### What _setup_phase() Currently Does

`feature_orchestrator.py:_setup_phase()` (line 414) performs:

1. ✅ Load feature YAML
2. ✅ Validate feature structure
3. ✅ Create git worktree
4. ✅ Copy task files to worktree
5. ❌ **Install project dependencies — DOES NOT EXIST**
6. ❌ **Verify environment is ready — DOES NOT EXIST**

After step 4, agents are immediately launched into the worktree. There is no step that ensures the target project's dependencies are available in the environment where tests will be executed.

### Why the Player Masks This Gap

The Player runs for 50+ turns over ~8 minutes. During TASK-DB-001 (scaffolding), it:
- Creates `pyproject.toml` with sqlalchemy, asyncpg, etc.
- Likely runs `pip install -e .[dev]` as part of its implementation work
- By the time subsequent tasks run, the packages happen to be installed

But this is **incidental**, not by design. The Player installs packages as a side-effect of implementation, not because AutoBuild ensures the environment is ready.

### Why the Coach Exposes It

The Coach's 1-turn SDK session runs `pytest tests/users/test_users.py` in ~5 seconds. It doesn't install anything. If the packages weren't installed into the Python that the SDK subprocess resolves to, it fails immediately at import time.

### Evidence: The Fastapi Example Project

The base repo at `guardkit-examples/fastapi/` has **no `pyproject.toml` at all**. It's a greenfield project. The `pyproject.toml` in the worktree was created by the Player during TASK-DB-001. This means:
- There's nothing to bootstrap at worktree creation time (no dependency file exists yet)
- After Wave 1 completes (TASK-DB-001 scaffolds the project), the dependencies exist but nobody installs them
- Wave 2 launches TASK-DB-003 into an environment where `sqlalchemy` may or may not be importable depending on what the Player for DB-001 happened to do

### The SDK Transport Is NOT the Problem

From GitHub Issue #55 and #480, the SDK's `SubprocessCLITransport` passes `env={**os.environ, "CLAUDE_CODE_ENTRYPOINT": "sdk-py"}` to the CLI process. The CLI inherits the parent's environment. The environment passthrough works correctly.

The problem is that **the project's dependencies were never deterministically installed into any Python environment** before agents started running.

---

## Why R1 (Switch to Subprocess) Is a Workaround, Not a Fix

R1 proposes changing Coach test execution from SDK to `subprocess.run()`. This happens to work for this specific case because the GuardKit Python process has sqlalchemy installed (it's a GuardKit dependency or was installed during a previous run). But:

1. It doesn't fix the environment for any OTHER project's dependencies
2. It doesn't help if the target project uses packages that aren't in GuardKit's Python
3. It doesn't help for non-Python projects (Node modules, NuGet packages, Go modules, etc.)
4. It masks the real gap — the next non-trivial project will hit the same issue with different packages

R1 is worth doing as a defence-in-depth measure, but it's not the root cause fix.

---

## The Solution Must Be Project-Type-Aware

GuardKit is a universal orchestrator. The environment bootstrap must handle:

| Manifest File | Stack | Install Command |
|--------------|-------|-----------------|
| `pyproject.toml` | Python | `pip install -e ".[dev,test]"` or `pip install -e .` |
| `requirements.txt` | Python | `pip install -r requirements.txt` |
| `Pipfile` | Python | `pipenv install --dev` |
| `poetry.lock` | Python | `poetry install` |
| `package.json` | Node/React/TS | `npm install` or `yarn install` or `pnpm install` |
| `*.csproj` / `*.sln` | .NET / MAUI | `dotnet restore` |
| `go.mod` | Go | `go mod download` |
| `Cargo.toml` | Rust | `cargo build` (or `cargo check`) |
| `pubspec.yaml` | Flutter/Dart | `flutter pub get` |
| `build.gradle.kts` | Android/Kotlin | `./gradlew build` |
| `Package.swift` | iOS/Swift | `swift package resolve` |

### Detection Strategy

File-based detection in the worktree, ordered by specificity:
1. Check for lock files first (more specific: `poetry.lock` → `poetry install`, `pnpm-lock.yaml` → `pnpm install`)
2. Fall back to manifest files (`pyproject.toml`, `package.json`, etc.)
3. Multiple manifests are possible (e.g., Python backend + React frontend in monorepo)

GuardKit already has stack detection infrastructure in the AutoBuild product spec (`templates/detect.py`, `autobuild init --stack`). This should be reused.

### When to Bootstrap

This is the subtle part. There are **two bootstrap points**:

**Bootstrap Point 1: After worktree creation (Phase 1.5)**
- For existing projects with dependencies already defined
- Run detection + install immediately after worktree is created
- Handles the common case: feature is adding to an existing codebase

**Bootstrap Point 2: After scaffolding wave completes (inter-wave hook)**
- For greenfield projects where Wave 1 creates the dependency manifest
- After each wave completes, re-detect and install if new manifests appeared
- The FEAT-BA28 case: TASK-DB-001 creates `pyproject.toml`, dependencies should be installed before Wave 2 launches TASK-DB-003

Both points need the same detection + install logic, just triggered at different moments.

### Proposed Architecture

```
feature_orchestrator.py:

    def _setup_phase():
        ...
        worktree = create_worktree()
        copy_task_files()
        self._bootstrap_environment(worktree.path)  # NEW: Phase 1.5
        return feature, worktree

    def _execute_waves():
        for wave in waves:
            results = execute_wave(wave)
            self._bootstrap_environment(worktree.path)  # NEW: inter-wave hook
            # Only installs if new manifests appeared

    def _bootstrap_environment(self, worktree_path: Path) -> None:
        """Detect project type(s) and install dependencies."""
        detector = ProjectEnvironmentDetector(worktree_path)
        manifests = detector.detect()  # Returns list of (stack, manifest_path, install_cmd)

        for stack, manifest, cmd in manifests:
            if self._already_bootstrapped(manifest):
                continue
            logger.info(f"Installing {stack} dependencies from {manifest.name}")
            result = subprocess.run(cmd, cwd=str(worktree_path), ...)
            if result.returncode == 0:
                self._mark_bootstrapped(manifest)
            else:
                logger.warning(f"Dependency install for {stack} failed: {result.stderr[:500]}")
```

The `_already_bootstrapped` check prevents redundant installs on each wave by tracking which manifests have been processed (e.g., via a hash of the manifest content stored in `.guardkit/bootstrap_state.json`).

### Feature YAML Enhancement

The feature YAML should optionally declare the stack for explicit control:

```yaml
id: FEAT-BA28
name: PostgreSQL Database Integration
stack: python  # Optional — auto-detected if omitted
```

This aligns with the existing `autobuild init --stack` pattern in the AutoBuild product spec.

---

## Revised Recommendation Priority

| Priority | Fix | Why |
|----------|-----|-----|
| **P0** | Add `ProjectEnvironmentDetector` + bootstrap phase to feature orchestrator | **Root cause fix**. Without this, every non-trivial project will hit dependency issues |
| **P0** | Add inter-wave bootstrap hook | Handles greenfield projects where Wave 1 creates the manifest |
| P1 | R1 from original review: Coach test fallback to subprocess with `sys.executable` | Defence-in-depth for Python — eliminates PATH resolution ambiguity for Coach tests specifically |
| P1 | R2: Add `requires_infrastructure` to FEAT-BA28 tasks | Still needed for Docker service dependencies (PostgreSQL, Redis) |
| P1 | R3: Wire `_docker_available` into task dict | Still needed for conditional approval |
| P2 | R4: Add sqlalchemy to high-confidence classification patterns | Still valid |
| P2 | R5: Diagnostic logging of SDK test environment | Still valid |

---

## Scope Clarification for Review

The review should evaluate:

1. **Where does `ProjectEnvironmentDetector` live?** Options: new module in `guardkit/orchestrator/`, or extension of existing stack detection in `templates/detect.py`
2. **Should bootstrap be synchronous or async?** `pip install` can take 30-60 seconds. For parallel waves, this blocks. Consider running it once before wave dispatch.
3. **Error handling**: What happens if bootstrap fails? Suggested: warn and continue (the Player may handle it), but flag it in the feature execution report.
4. **Monorepo support**: Projects with multiple stacks (e.g., `backend/pyproject.toml` + `frontend/package.json`). The detector should handle subdirectories.
5. **Virtual environment policy**: Should AutoBuild create a project-specific venv in the worktree, or install into the current Python? Creating a venv is cleaner but adds complexity; installing into the current Python is simpler and matches how developers actually work.
6. **Interaction with TASK-PCTD-3182**: The "SDK environment parity" task's core premise is now questionable. If the environment is properly bootstrapped, both SDK and subprocess paths should work. TASK-PCTD-3182 should be re-scoped or paused.

---

## Decision Options

- **[A]ccept** — Archive findings as-is
- **[R]evise** — Incorporate this analysis and create implementation tasks for the bootstrap phase
- **[I]mplement** — Create tasks from the revised recommendations
- **[C]ancel** — Discard review

# `[tool.uv.sources]` Bootstrap Behaviour

GuardKit's environment bootstrap detects projects that pin a sibling source
override via `[tool.uv.sources]` (or carry a `uv.lock`) and prefers `uv`
over `pip` when `uv` is available. This page documents the resolved install
command per project layout and the cross-repo conventions consuming repos
should follow.

## Why this exists

`pip install -e .` does **not** honour `[tool.uv.sources]`. A project that
pins a private wheel via that block (forge / jarvis are the canonical case)
will silently install a broken environment when bootstrapped with plain pip.
Before TASK-FIX-F09A2 the bootstrap shipped a hardcoded
`[sys.executable, "-m", "pip", "install", "-e", "."]` for every Python
manifest, so each consuming repo had to ship a `.guardkit/preflight.sh` that
pre-installed siblings under their explicit name.

GuardKit now checks the manifest itself and picks the right tool.

## Behaviour matrix

`environment_bootstrap.ProjectEnvironmentDetector` applies this matrix when
a directory contains `pyproject.toml`. `poetry.lock` and `requirements.txt`
detection are unchanged — those layouts don't use uv-sources.

| pyproject `[tool.uv.sources]` | `uv.lock` present | `uv` on PATH | Install command chosen |
|-------------------------------|-------------------|--------------|-------------------------------|
| absent                        | absent            | any          | `python -m pip install -e .`  (unchanged) |
| absent                        | present           | yes          | `uv pip sync uv.lock`         (full lockfile fidelity) |
| absent                        | present           | no           | `python -m pip install -e .`  (+ warning log) |
| present                       | any               | yes          | `uv pip install -e .`         |
| present                       | any               | no           | **Hard-fail** (`UvSourcesRequireUvError`) |

The hard-fail row raises before any pip work runs and surfaces an error
that names the offending pyproject and the two acceptable fixes (install
uv, or remove the `[tool.uv.sources]` block). It deliberately does **not**
hint at `bootstrap_failure_mode: warn` — warn-mode is the wrong escape
hatch for an install-system mismatch and would silently produce the broken
environment the detection exists to prevent.

## Symlink coordination — operator-side preflight

GuardKit's worktree creation copies task files into the worktree but does
**not** orchestrate sibling-source layout (e.g. ensuring `../sibling-pkg`
resolves from inside `.guardkit/worktrees/FEAT-XXX/`). This is the
consuming repo's responsibility:

- For repos that pin `[tool.uv.sources]` to a sibling path, ship a
  `.guardkit/preflight.sh` that creates the symlink (or copies the source)
  before bootstrap runs. The script is idempotent — running it under the
  uv-aware bootstrap is harmless.
- The runbook for the parent repo should document the preflight script as
  a one-time setup step and point at this guide for the rationale.

This is the deliberate choice of "option (b)" from the task acceptance
criteria: GuardKit does not provide a pre-bootstrap hook API. The win from
having one is small (one less file in each consuming repo) and the cost is
non-trivial (a new public hook surface to support across releases).
Operator-side preflight scripts solve the problem with zero GuardKit
surface change and remain idempotent under the new uv-aware bootstrap.

## CI / dev image: install `uv`

For the new `uv pip install -e .` and `uv pip sync uv.lock` branches to be
exercised, `uv` must be on PATH in CI and in the developer image:

```bash
# Stand-alone
pip install uv

# Or via the upstream installer (https://astral.sh/uv)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Repos whose `pyproject.toml` declares `[tool.uv.sources]` should treat
`uv` as a hard dev/CI dependency — the bootstrap raises
`UvSourcesRequireUvError` when it isn't present, and that's a structural
hard-fail (pip cannot honour the override).

## Migration: existing forge `.guardkit/preflight.sh`

After the uv-aware bootstrap lands, forge's `.guardkit/preflight.sh` (the
TASK-FIX-F09A1 ship-now workaround) becomes unnecessary for the
sibling-source install — `uv pip install -e .` will resolve the
`[tool.uv.sources]` pin natively. The preflight script can stay in place
for a transition window (it's idempotent) and be removed in a follow-up
task once the new bootstrap is verified green by `guardkit autobuild
feature FEAT-FORGE-009`.

## Implementation pointer

- Helpers: `_uv_on_path`, `_pyproject_has_uv_sources`,
  `_resolve_python_pyproject_install_command`
  in `guardkit/orchestrator/environment_bootstrap.py`.
- Hard-fail propagation: `feature_orchestrator._run_environment_bootstrap`
  catches `UvSourcesRequireUvError` and re-raises as
  `FeatureOrchestrationError` so the orchestrator stops before Wave 1
  (rather than swallowing in the generic `except Exception`).
- Tests: `TestPyprojectUvSourcesDetection` in
  `tests/unit/test_environment_bootstrap.py`.

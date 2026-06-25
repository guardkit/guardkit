# `[tool.uv.sources]` must survive every install path, not just the editable one

> **Source**: Seeded by TASK-FIX-UVSRCDEP01 (2026-06-25, commit `ff4b63ce`) from
> the FEAT-HARV wave-1 autobuild failure. Pair with the Graphiti design-rule node
> *"uv-sources must survive every install path (per-dep fallback ignored it →
> PyPI namespace collision)"* under `guardkit__project_decisions`. Direct child /
> install-path instance of
> [`namespace-hygiene.md`](namespace-hygiene.md) (a local decision touching an
> externally-defined namespace — the PyPI distribution-name namespace — must be
> audited against it). Shares the "a contract honoured at one layer but dropped at
> a parallel layer" shape with
> [`absence-must-survive-every-reconciliation-layer.md`](absence-must-survive-every-reconciliation-layer.md).
> Its downstream effect (a Player self-mocking the missing dep → tests against a
> mock) is the
> [`per-task-green-is-not-feature-green.md`](per-task-green-is-not-feature-green.md)
> /
> [`absence-of-failure-is-not-success.md`](absence-of-failure-is-not-success.md)
> family.

## The rule

When a Python project declares a `[tool.uv.sources]` override that redirects a
dependency to a **local sibling checkout** (`name = { path = "../sibling",
editable = true }`), that override is an externally-defined contract that the
autobuild environment bootstrap MUST honour on **every** install path it has —
not just the editable `uv pip install -e .` path. `[tool.uv.sources]` is a
**uv-only** mechanism: plain `pip install <name><spec>` does not read it and
resolves the name from **PyPI** instead. So any bootstrap install path that
shells `python -m pip install <name><spec>` for a uv-sources-pinned dependency
silently bypasses the redirect and resolves the wrong package — catastrophically
so when an **unrelated public PyPI package shares the name** (a namespace
collision): pip installs the wrong distribution, or fails the version spec, and
the sibling never lands in the worktree venv.

GuardKit's bootstrap has **two** Python install paths:

1. **Editable path** — `_resolve_python_pyproject_install_command`
   ([`environment_bootstrap.py:860`](../../guardkit/orchestrator/environment_bootstrap.py#L860)):
   emits `uv pip install -e .[extras]` when `[tool.uv.sources]` is present. This
   path **already honoured** uv-sources (it shells `uv`, not `pip`).
2. **Per-dependency fallback** — `_python_dep_commands`
   ([`environment_bootstrap.py:251`](../../guardkit/orchestrator/environment_bootstrap.py#L251)):
   taken when the project is detected **incomplete**
   (`_python_pyproject_is_complete`,
   [`:205`](../../guardkit/orchestrator/environment_bootstrap.py#L205) — its
   distribution name does not match its package dir, e.g. `guardkit-py` vs the
   `guardkit/` dir). This path emitted one plain `pip install <pep508>` per
   declared dependency (base + requested extras) and **ignored uv-sources**.

The contract was honoured on path 1 and dropped on path 2. The fix makes path 2
honour it too: a dependency whose normalised name matches a path-typed
`[tool.uv.sources]` entry is installed via `pip install -e <resolved sibling>`
(through the worktree bridge symlink), fail-open to plain pip when the sibling
path does not resolve.

## Why this rule exists

1. **2026-06-25** — FEAT-HARV wave-1 false-blocker. The `memory` extra declared
   `nats-core>=0.4,<1`, redirected by `[tool.uv.sources]` to the editable sibling
   `../nats-core` (version `0.4.0`, `requires-python>=3.11`). Because guardkit-py
   is detected incomplete (`guardkit-py` != `guardkit/`), the bootstrap took the
   per-dependency fallback and ran:

   ```
   .venv/bin/python -m pip install nats-core>=0.4,<1
   ERROR: Could not find a version that satisfies the requirement nats-core<1,>=0.4
          (from versions: 0.0.0)
   ERROR: Ignored versions requiring a different python: 0.1.0/0.2.0 (>=3.13)
   ```

   A **different, unrelated public `nats-core` on PyPI** (only 0.0.0/0.1.0/0.2.0)
   shadowed the private sibling and failed the spec → `nats_core` never installed
   in the worktree venv. The Player then **masked** the missing dependency by
   self-mocking `nats_core` in `sys.modules` so its module could import — the
   tests ran against a `MagicMock` (absent integration evidence,
   `per-task-green-is-not-feature-green`), and the task stalled on a genuinely
   broken mock-capture test rather than on the real cause. The deliverable would
   also have `ModuleNotFoundError`d at the wave-3 smoke gate
   (`python -m guardkit.cli.main memory harvest --dry-run`), which runs the real
   entry point with no pytest `sys.path` help.

   The defect surfaced only because a feature finally depended on a uv-sources
   sibling *through the incomplete-project per-dep path*. Any purely-PyPI feature,
   or any project whose name matches its package dir (taking the editable path),
   would never hit it.

## Symptom

- An autobuild feature whose deliverable imports a sibling package
  (`import nats_core`, `import guardkitfactory`, …) stalls or fails wave-1, and
  the worktree venv is missing that package
  (`.guardkit/worktrees/<FEAT>/.venv/bin/python -c "import <mod>"` →
  `ModuleNotFoundError`), even though the sibling is checked out alongside and
  declared in `[tool.uv.sources]`.
- The bootstrap log shows a plain
  `… python -m pip install <name><spec>` for the sibling (not
  `pip install -e <path>`), followed by
  `ERROR: No matching distribution` / `Could not find a version that satisfies`
  — typically because a **same-named public PyPI package** exists at unrelated
  versions.
- "Environment bootstrap partial: N-1/N succeeded" where the one failure is the
  sibling dep (not a benign non-Python skip like `dotnet`).
- Downstream: the Player's test file defensively mocks the missing module into
  `sys.modules` (the `try: import X / except ImportError: sys.modules['X'] =
  MagicMock()` idiom), so per-task pytest is green against a mock while the real
  seam is never exercised.

## Detection recipe

```bash
# 1. Every bootstrap install path that shells plain `pip install <name>` for a
#    declared dependency. Each is a candidate uv-sources bypass.
rg -n "pip\", \"install\", dep|pip install <name>|\"-m\", \"pip\", \"install\"" \
   guardkit/orchestrator/environment_bootstrap.py

# 2. Confirm the per-dependency path consults [tool.uv.sources] before emitting
#    a plain `pip install`. MUST MATCH (absence = the bypass is back).
rg -n "_uv_sources_editable_targets|_requirement_dist_name" \
   guardkit/orchestrator/environment_bootstrap.py

# 3. The two install paths — confirm BOTH honour uv-sources (path 1 via `uv`,
#    path 2 via the editable-target redirect).
rg -n "uv\", \"pip\", \"install\", \"-e\"|install\", \"-e\", editable_target" \
   guardkit/orchestrator/environment_bootstrap.py

# 4. The incomplete-project trigger that routes guardkit-py to the per-dep path.
rg -n "_python_pyproject_is_complete|import_name = project_name" \
   guardkit/orchestrator/environment_bootstrap.py

# 5. Audit every [tool.uv.sources] path entry's name against PyPI (namespace
#    collision check — namespace-hygiene). For each, `pip index versions <name>`
#    or check https://pypi.org/project/<name>/ ; a public package at unrelated
#    versions is a live collision hazard if any install path bypasses uv.
rg -n "^\[tool.uv.sources\]" -A 30 pyproject.toml | rg "path ="

# 6. Player-side masking: a test that mocks a first-party sibling into sys.modules
#    is a tell that the dep didn't install.
rg -n "sys.modules\[.(nats_core|guardkitfactory)" tests/ -g '!**/test_environment_bootstrap*'

# 7. Cross-check the rule family.
rg "uv-sources-must-survive|namespace-hygiene|per-task-green-is-not-feature-green" .claude/rules/
```

## Remediation recipe

1. **Honour the contract on every install path.** Audit each bootstrap install
   path (`_resolve_python_pyproject_install_command` editable path,
   `_python_dep_commands` per-dependency path, any future requirements.txt /
   lockfile path) and confirm each either shells `uv` (which reads uv-sources) or
   explicitly redirects path-typed uv-sources deps to `pip install -e <path>`.
   Honouring it on one path and not the parallel one is the defect.
2. **Centralise the uv-sources parse (single source of truth).** The redirect
   resolver (`_uv_sources_editable_targets`,
   [`:629`](../../guardkit/orchestrator/environment_bootstrap.py#L629)) mirrors
   the canonical detection / symlink resolution
   (`_pyproject_has_uv_sources` [`:587`](../../guardkit/orchestrator/environment_bootstrap.py#L587),
   `_resolve_uv_sources_symlinks`) so producer and consumer cannot drift — the
   `namespace-hygiene` lesson. Resolve relative to the pyproject's own directory
   (uv's rule) through the worktree bridge symlink the orchestrator pre-creates.
3. **Normalise names PEP 503-style** (`_normalise_dist_name`,
   [`:611`](../../guardkit/orchestrator/environment_bootstrap.py#L611)) on both
   sides so `nats_core` (dep) matches `nats-core` (uv-source key).
4. **Fail-open, never fail-broken.** When a uv-sources path does not resolve
   (sibling not checked out / bridge symlink absent), fall back to plain pip —
   the pre-existing behaviour — rather than emitting a guaranteed-broken
   `-e <missing>` target. (Per the fail-open posture of
   `path-string-mismatch-is-not-dishonesty` / `evidence-boundary-narrower`.)
5. **Audit sibling names against PyPI before merging** (the namespace-hygiene
   meta-rule). A private editable sibling whose distribution name also exists on
   PyPI is a latent collision: it is only safe while *every* install path routes
   through uv-sources. Prefer a name with no public PyPI collision; if a
   collision is unavoidable, the every-path invariant above is load-bearing.
6. **Verify standalone, not just under pytest.** After bootstrap, confirm the dep
   imports from the worktree venv directly
   (`.venv/bin/python -c "import <mod>"`) — pytest can shadow a missing module via
   `sys.path` or an in-test `sys.modules` mock, hiding the gap until the real
   runtime / smoke gate (the `namespace-hygiene` / `smoke-gate` arm-b lineage).

## Grep-able signature (for next agent)

```bash
# Fixed-state fingerprint (POST-FIX, commit ff4b63ce): the per-dep path consults
# uv-sources and redirects to an editable target. MUST MATCH; absence = regression.
rg -n "editable_target = uv_sources.get\(_requirement_dist_name" \
   guardkit/orchestrator/environment_bootstrap.py            # -> 307
rg -n "install\", \"-e\", editable_target" \
   guardkit/orchestrator/environment_bootstrap.py            # -> 310
rg -n "def _uv_sources_editable_targets" \
   guardkit/orchestrator/environment_bootstrap.py            # -> 629

# Regression fingerprint: the OLD unconditional plain-pip comprehension. MUST be
# NO MATCH on current main; any hit means the uv-sources bypass has returned.
rg -n 'return \[\[sys.executable, "-m", "pip", "install", dep\] for dep in deps\]' \
   guardkit/orchestrator/environment_bootstrap.py            # -> (no match)

# Editable path (already-correct path 1) — confirm it still shells uv.
rg -n '"uv", "pip", "install", "-e"' \
   guardkit/orchestrator/environment_bootstrap.py

# Sibling-rule lookup (this rule + the family).
rg "uv-sources-must-survive|namespace-hygiene|per-task-green-is-not-feature-green|absence-must-survive" .claude/rules/
```

## Meta-frame

This rule sits at the intersection of two existing meta-frames:

- **Namespace-hygiene** (its parent): a *local decision* (install a dependency by
  its name) that touches an *externally-defined namespace* (the PyPI
  distribution-name space) must be audited against that namespace. The
  `[tool.uv.sources]` override is the local-dev redirect away from PyPI; an
  install path that ignores it re-enters the PyPI namespace and collides.
- **Contract-must-survive-every-layer** (shared with
  `absence-must-survive-every-reconciliation-layer`): a contract honoured at one
  layer is *not sufficient* if a parallel layer drops it. There, the contract is
  "absence stays `None`" across reconciliation layers; here it is "uv-sources
  redirect is honoured" across install paths. Both fail when one of several
  parallel code paths silently doesn't implement the invariant.

The downstream blast radius is the low-fidelity-oracle family: the Player's
`sys.modules` self-mock turns the missing dependency into **absent integration
evidence** (`per-task-green-is-not-feature-green`), and pytest's green-against-a-mock
is the `absence-of-failure` / tests-pass-production-fails shape.

## Prior art

- **Parent rule (externally-defined namespace)**:
  [`namespace-hygiene.md`](namespace-hygiene.md) — its broader meta-rule
  ("local design decisions that touch externally-defined namespaces … must be
  audited against those external namespaces before merging") names *PyPI* and
  *filesystem locations* explicitly; this is a PyPI-namespace instance at the
  bootstrap install boundary.
- **Same "survive every layer" shape**:
  [`absence-must-survive-every-reconciliation-layer.md`](absence-must-survive-every-reconciliation-layer.md).
- **Downstream effect**:
  [`per-task-green-is-not-feature-green.md`](per-task-green-is-not-feature-green.md)
  (mocked first-party seam = absent integration evidence),
  [`absence-of-failure-is-not-success.md`](absence-of-failure-is-not-success.md),
  and [`smoke-gate-is-feedback-not-terminator.md`](smoke-gate-is-feedback-not-terminator.md)
  arm b (pytest `sys.path` shadow vs standalone run).
- **Pair fact in Graphiti** (`guardkit__project_decisions`): node *"uv-sources
  must survive every install path (per-dep fallback ignored it → PyPI namespace
  collision)"*.
- **Originating defect**: FEAT-HARV wave-1, run 1 (2026-06-25). The `memory`
  extra's `nats-core` sibling vs the public PyPI `nats-core`.
- **Originating fix**: TASK-FIX-UVSRCDEP01 (commit `ff4b63ce`, 2026-06-25).
  Helpers `_uv_sources_editable_targets` / `_requirement_dist_name` /
  `_normalise_dist_name`; the redirect in `_python_dep_commands`
  ([`environment_bootstrap.py:307-315`](../../guardkit/orchestrator/environment_bootstrap.py#L307)).
  Reproducer: `tests/unit/test_environment_bootstrap_uv_sources_extra.py`
  (18 tests, incl. the FEAT-HARV reproducer + fail-open + PEP 503 normalisation).
- **Pre-wiring context** (the feature that hit it):
  `.guardkit/features/FEAT-HARV.yaml` (`bootstrap_extras: [dev, memory]`),
  `pyproject.toml` `[tool.uv.sources] nats-core = { path = "../nats-core" }`.

## When this rule triggers

- Before adding or modifying any Python install path in
  `environment_bootstrap.py` (`_python_dep_commands`,
  `_resolve_python_pyproject_install_command`, requirements.txt / lockfile
  handling) — confirm it honours `[tool.uv.sources]`.
- Before adding a new `[tool.uv.sources]` path entry (a new editable sibling) to
  any pyproject autobuild bootstraps — audit the name against PyPI for a
  collision, and confirm the sibling is checked out alongside on the build
  machine.
- Before authoring a feature whose deliverable imports a sibling package
  resolved via uv-sources (FEAT-HARV-like) — verify the dep installs editably in
  the worktree venv and imports standalone, not just under pytest.
- During Phase 2.5 architectural review for anything touching the bootstrap
  install paths or the worktree uv-sources symlink bridge.
- During any diagnostic session investigating a "the worktree venv is missing a
  dependency that's declared and checked out" report, or a Player that
  `sys.modules`-mocks a first-party module.

## What the rule does NOT cover

- **Non-path uv-sources entries** (`git`, `index`, `workspace`, `url`). The
  redirect only covers path-typed editable siblings; other source kinds are left
  to uv / plain pip.
- **A genuinely-PyPI dependency with no uv-source.** Plain `pip install <name>`
  is correct for those; the redirect only fires for names declared in
  `[tool.uv.sources]` with a `path`.
- **Sibling-not-checked-out.** When the path does not resolve, the rule mandates
  fail-open to plain pip (preserving prior behaviour), not a new hard failure —
  surfacing the missing sibling is the operator's responsibility (the build
  machine must have it).
- **The editable `uv pip install -e .` path's own uv requirement.** When
  `[tool.uv.sources]` is present but `uv` is absent from PATH, that path raises
  `UvSourcesRequireUvError` by design (a separate, pre-existing guard); this rule
  governs the per-dependency fallback that runs when the project is incomplete.
- **Coverage of the public-name choice itself.** Renaming a sibling to avoid the
  PyPI collision is a `namespace-hygiene` remediation; this rule makes the
  every-path invariant load-bearing so a collision is survivable, but does not
  mandate the rename.

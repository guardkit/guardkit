# Namespace Hygiene

> **Source**: Seeded by TASK-REV-MCPS (2026-04-24). Paired with Graphiti design-rule node *"GuardKit internal module names must not shadow PyPI packages"* (group `guardkit__project_decisions`). Sibling of `runner without producer anti-pattern` (Graphiti uuid `184731b0-3cb6-4eb2-a310-883421767dbf`).

## The rule

GuardKit internal module names must not shadow PyPI packages, especially dependencies-of-dependencies. Local design decisions that touch externally-defined namespaces (Python modules, shell PATH, HTTP paths, filesystem locations, environment variables) must be audited against those external namespaces before merging.

## Why this rule exists

The class-of-defect recurs:

1. **2026-04-18** — GuardKit's editable-install `lib/` shadowed a rendered template's `lib/` namespace package in the render-and-import smoke test. Local fix: a smoke-test `sys.path` filter. No rule seeded. [Graphiti fact `cced8d00`]
2. **2026-04-24** — GuardKit's internal `installer/core/lib/mcp/` shadowed Anthropic's `mcp` PyPI package (transitive dep of `claude-agent-sdk`), breaking AutoBuild with a misleading "SDK not available" message. [TASK-REV-MCPS]

Both incidents share a mechanism: **an internal directory name that overlaps with an external namespace, combined with a `sys.path.insert(0, ...)` that puts the internal parent ahead of `site-packages`**. Both slipped through because no design rule captured the constraint at the knowledge-graph level.

## Symptom

- CLI reports "dependency not available" or "SDK missing" despite the named dependency being pip-installed and importable from a fresh subprocess.
- `ImportError` surfaces name a *submodule* of a known PyPI package (e.g., `No module named 'mcp.types'`), not the package itself.
- `sys.path` inspection shows an `installer/core/*` or `guardkit/*` directory at position 0.
- Production tests pass, production runs fail — because the test-suite import graph differs from the CLI-entry import graph.

## Detection recipe

```bash
# 1. Grep for position-0 sys.path inserts touching GuardKit-internal dirs
rg "sys\.path\.insert\(0," -t py

# 2. For each match, determine the inserted directory.
# 3. For each directory, enumerate its top-level subpackage names.
# 4. Cross-check each name against PyPI top-level package names.
#    A hit is a hazard:
#      - Active hazard: the insert always runs at import time
#      - Latent hazard: the insert is guarded but the guard might silently fail
# 5. Independently enumerate subpackage names under:
#      installer/core/lib/
#      installer/core/commands/lib/
#      guardkit/
#    Any name that collides with a PyPI package is a latent hazard
#    regardless of current sys.path state.
```

## Remediation recipe

1. **Prefer structural imports** over `sys.path.insert`. The editable install of `guardkit-py` places the repo root on `sys.path` (Graphiti fact `f868769a`), so `from installer.core.lib.X import ...` resolves naturally with no manipulation.
2. **If `sys.path` manipulation is unavoidable** (bootstrap scripts, non-editable installs, test fixtures on legacy layouts), insert at the end (`sys.path.append`) rather than position 0, and scope the insert as narrowly as possible with immediate cleanup.
3. **Rename colliding internal directories** proactively, even if no current import chain activates shadowing. Latent hazards activate silently when import graphs change. Structural immunity is cheaper than every future diagnostic round-trip.
4. **Avoid "production / dev fallback" `try/except ImportError` idioms** unless the production branch is verified to resolve in the production deployment path. A silently-always-failing production branch is itself an anti-pattern — it means the fallback always runs and the "production" code is dead.
5. **When modifying `_check_sdk_available`-style preflight checks**, capture and surface the underlying `ImportError.__str__`. An opaque "not available" message costs diagnosis time at every future incident.

## Grep-able signature (for next agent)

```bash
# Active-hazard fingerprint
rg "sys\.path\.insert\(0, [^)]*installer/core/lib" -t py

# Anti-pattern idiom fingerprint
rg -A 8 "try:.*\n.*from \.[a-z_]+ import.*\n.*except ImportError:.*\n.*sys\.path\.insert" -t py --multiline

# Internal-name-vs-PyPI fingerprint (manual; list internal subpackage names then grep PyPI)
ls installer/core/lib/
ls installer/core/commands/lib/
ls guardkit/
```

## Prior art

- **Sibling rule**: *"runner without producer anti-pattern"* — group `guardkit__project_decisions`, uuid `184731b0-3cb6-4eb2-a310-883421767dbf`. Same shape (symptom + detection recipe + remediation recipe + grep signature). Same meta-class-of-defect (local decisions touching externally-defined contracts).
- **Sibling rule (pending)**: *"stack-assumption must be isolated in named plugin"* — to be seeded by TASK-REV-STKB Workstream D. Another instance of the broader meta-rule below.
- **Broader meta-rule** (to be seeded separately, cross-linked from this rule and the two siblings above): *"Local design decisions that touch externally-defined namespaces (Python modules, shell PATH, HTTP paths, filesystem locations, environment variables) must be audited against those external namespaces before merging."*

## When this rule triggers

- Before introducing a new subpackage under `installer/core/lib/`, `installer/core/commands/lib/`, or `guardkit/`.
- Before adding any `sys.path.insert(...)` statement in runtime (non-test) code.
- During Phase 2.5 architectural review for any task that touches `sys.path` or adds a new top-level module name.
- During any diagnostic session investigating a "dep not available" symptom.

## What the rule does NOT cover

- Test-fixture `sys.path.insert` at the end of `sys.path` (via `.append`) with a narrowly scoped insert — this is orthogonal, generally safe.
- Module-level relative imports (`from .X import Y`) — these do not touch `sys.path`.
- The broader hygiene question of "is every `sys.path.insert` across the tree necessary?" — that is a separate review, explicitly out of scope for the triggering TASK-REV-MCPS.

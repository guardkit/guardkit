# Portfolio Python Pinning Guide

A pragmatic recommendation for how downstream projects derived from GuardKit's
LangChain DeepAgents templates should pin `requires-python` in their
`pyproject.toml`.

## TL;DR

For new projects derived from a `langchain-deepagents*` template, use:

```toml
[project]
requires-python = ">=3.11"
```

Open upper bound. No `<X.Y` clause. Defensive upper bounds belong in CI matrices
and known-bad version exclusions, not in `requires-python`.

## Recommendation

| Property | Value | Why |
|---|---|---|
| Lower bound | `>=3.11` | Matches the canonical pin used by every shipped LangChain DeepAgents template (`langchain-deepagents`, `langchain-deepagents-orchestrator`, `langchain-deepagents-weighted-evaluation`) and every healthy sibling consumer (forge, study-tutor, agentic-dataset-factory, specialist-agent). |
| Upper bound | *(none)* | Closed upper bounds in `requires-python` create resolver traps that go silently latent until a new Python minor releases. See [Rationale](#rationale). |

## Rationale

### 1. `requires-python` is a resolver constraint, not a CI policy

`requires-python` is consulted by every package resolver (pip, uv, poetry) at
install time and by every interpreter selector (uv-managed envs, pyenv shims,
direnv, IDE plugins) at run time. A closed upper bound `<X.Y` says "I refuse
to install on Python X.Y or newer." If a developer has only Python X.Y on PATH
— which becomes increasingly likely as the cap ages — the project becomes
*unbootstrappable* with no actionable error from the resolver.

### 2. The upper-bound trap goes latent, not loud

A `<3.13` constraint introduced when 3.12 is the latest stable will work fine
for months. When 3.13 ships, machines that auto-update Homebrew or pyenv
silently get a default interpreter the project rejects. The failure surfaces
as a stall in whatever orchestrator first tries to use that interpreter — not
as "your `requires-python` excludes the only Python you have."

This was the exact failure mechanism documented in
[TASK-REV-FA04](../reviews/TASK-REV-FA04-report.md) §F9 / §F0:

- Jarvis's `pyproject.toml` pinned `>=3.12,<3.13` (introduced 2025-11, when
  `nats-core` was the latest version requiring `>=3.13`).
- Six months later, Python 3.14 became the default on macOS Homebrew (released
  2025-10-07).
- Every Jarvis AutoBuild run on Mac thereafter silently failed to bootstrap a
  worktree — the `requires-python` clause excluded the active interpreter.
- The failure surfaced as an `unrecoverable_stall` with a misleading "Review
  task_type classification" hint; the real cause (`requires-python` excluded
  `sys.executable`) was buried six layers down in the bootstrap log.
- **Verified follow-up (2026-04-27)**: the upstream `nats-core` package has
  since broadened its own `requires-python` to `>=3.10`. Jarvis's tight pin no
  longer has a load-bearing reason — the dependency it was protecting against
  changed shape, but the cap stayed put. *This is the canonical decay path for
  closed upper bounds: the constraint that motivated them resolves upstream,
  the cap silently lingers, and a stale cap is indistinguishable from a real
  one until something downstream fails.*

A 33-minute autobuild run, a feature-stall trapdoor with a misleading
diagnostic, and ~6 hours of post-mortem analysis (TASK-REV-FA04 + Wave 1
remediation) — all to fix what should have been a one-line `requires-python`
relaxation. The closed upper bound, once stale, paid no rent and cost real
incidents.

### 3. Defensive upper bounds belong in the CI matrix, not the manifest

The legitimate concern behind a closed upper bound is "I don't know if the
project works on the next Python minor." That concern is correctly addressed
by:

- **CI matrix** that exercises `3.11`, `3.12`, `3.13`, `3.14, …` — adds a row
  per release, blocks merges when the new minor breaks the build.
- **Known-bad version exclusions** for transitively-broken packages, expressed
  inline as `dep>=X,!=BAD_VERSION` rather than as a blanket Python cap.
- **Lockfiles** (`uv.lock`, `poetry.lock`) that pin every transitive dependency
  for reproducibility without restricting the interpreter's PATH availability.

A closed upper bound in `requires-python` does none of this. It only
*pre-commits the project to refusing future interpreters that may or may not
actually break the build*. That tradeoff almost never pays off; when 3.X+1
breaks something real, you have to relax the cap anyway, and in the meantime
every clean install on a new dev machine fails for no good reason.

### 4. The Schreiner principle

Henry Schreiner's analysis of upper-bound pinning in Python packaging
([iscinumpy.dev](https://iscinumpy.dev/post/bound-version-constraints/) and
related posts) makes the strong-form case: for libraries, *every* upper bound
on `requires-python` and `Requires-Dist` makes the resolver's job harder and
is rarely justified by actual evidence of breakage. Applications can be
slightly more aggressive about caps, but the calculus is the same: caps cost
real ergonomics now and only buy speculative protection later.

The GuardKit portfolio is a mix of libraries (template scaffolds) and
applications (consumer projects). The recommendation here biases toward
Schreiner's posture — open upper bounds by default — for the same reasons.

## When a Tighter Pin is Genuinely Required

Sometimes a pin is load-bearing. Examples:

1. **A direct dependency caps interpreters tighter than your code does.** If
   `nats-core==2.10.0` declares `requires-python = ">=3.13"` and you need that
   version, you can either bump your floor (`>=3.13`) or accept that 3.11 and
   3.12 won't resolve. *This is a floor concern, not an upper bound concern.*

2. **A transitive dependency has a known-broken release on a specific minor.**
   Example: `package==1.5.0` has a CPython 3.13 bug that's fixed in 1.5.1.
   Pin the dependency, not the interpreter:
   `package = ">=1.5.1, !=1.5.0"`.

3. **You depend on an interpreter feature that's pending removal.** Rare.
   Document inline with a comment naming the deprecation timeline and a
   calendar review date:

   ```toml
   # 3.14 removed `pkg_resources`; revisit when our `legacy_loader` migrates
   # off it (target: 2026-Q3 review).
   requires-python = ">=3.11,<3.14"
   ```

   The comment makes the pin auditable. Without one, the same trapdoor that
   bit Jarvis bites the next maintainer.

In every case: **document the constraint inline**, **set a calendar cadence
to re-evaluate** (quarterly is reasonable), and **prefer narrowing the
specific dependency over capping the whole interpreter** when the choice is
available.

## How GuardKit Enforces This

The `template-validate` harness emits an informational warning when a
`langchain-deepagents`-derived template (or rendered project) declares a
`requires-python` constraint with a closed upper bound that excludes a
released, stable Python minor. The warning is **non-blocking** — projects can
ship with a closed upper bound when they have a documented reason; the warning
just makes the choice visible during validation runs.

See `installer/core/lib/template_validation/sections/section_01_manifest.py`
for the implementation.

## Out of Scope

- **This guide does not change any sibling project's pin.** GuardKit is the
  template authority; consumer projects (forge, study-tutor, jarvis,
  agentic-dataset-factory, specialist-agent) make their own decisions
  informed by this guide.
- **CI matrix templates and lockfile policy** are tracked separately. This
  guide only addresses the `requires-python` clause.

## References

- Origin incident review: [TASK-REV-FA04 report](../reviews/TASK-REV-FA04-report.md)
  — see §F9 (sibling pin comparison), §R7 (standardisation recommendation),
  and "Standardisation Proposal" section.
- Schreiner, H. *"Should You Use Upper Bound Version Constraints?"* —
  [iscinumpy.dev/post/bound-version-constraints](https://iscinumpy.dev/post/bound-version-constraints/)
- Canonical pins:
  - `installer/core/templates/langchain-deepagents/templates/other/other/pyproject.toml.template`
  - `installer/core/templates/langchain-deepagents-orchestrator/templates/other/other/pyproject.toml.template`
  - `installer/core/templates/langchain-deepagents-weighted-evaluation/manifest.json` (inherits via `extends`)

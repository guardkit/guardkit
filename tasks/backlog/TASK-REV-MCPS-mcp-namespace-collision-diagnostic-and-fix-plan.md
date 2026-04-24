---
id: TASK-REV-MCPS
title: MCP namespace collision — diagnostic + fix plan + preventive rule (greenfield_qa_session.py sys.path insert shadows Anthropic mcp SDK, breaks AutoBuild)
status: review_complete
task_type: review
review_mode: architectural
review_depth: standard
decision_required: true
created: 2026-04-24T00:00:00Z
updated: 2026-04-24T00:00:00Z
priority: high
complexity: 5
tags: [architecture-review, namespace-collision, mcp-shadowing, autobuild-blocker, graphiti-driven, preventive-rule, rwop-successor]
parent_review: TASK-REV-STKB
related_to: TASK-REV-STKB
related_tasks:
  - TASK-REV-STKB
  - TASK-REV-RWOP1
  - TASK-COH-RUN1
  - TASK-FIX-RWOP1.3.3
blocks: TASK-COH-RUN1
test_results:
  status: pending
  coverage: null
  last_run: null
review_results:
  mode: architectural
  depth: standard
  score: 62
  findings_count: 8
  recommendations_count: 5
  decision: implement
  strategy: minimal-then-complete
  report_path: docs/reviews/TASK-REV-MCPS-namespace-collision-review.md
  preamble_path: docs/reviews/TASK-REV-MCPS-graphiti-preamble.md
  rule_path: .claude/rules/namespace-hygiene.md
  graphiti_nodes_seeded:
    - group: guardkit__project_decisions
      name: "Design rule candidate: GuardKit internal module names must not shadow PyPI packages (namespace-hygiene)"
    - group: guardkit__task_outcomes
      name: "Review outcome: TASK-REV-MCPS (namespace collision — architectural, 62/100)"
  subtasks_created:
    - TASK-FIX-MCPS.1
    - TASK-FIX-MCPS.2
    - TASK-FIX-MCPS.3
  subtasks_folder: tasks/backlog/mcps-namespace-collision/
  completed_at: 2026-04-24T00:00:00Z
---

# Task: MCP namespace collision diagnostic + fix plan + preventive rule

## Problem Statement

On 2026-04-24 the user ran `guardkit autobuild feature FEAT-J002 --verbose --max-turns 30` from jarvis and received:

```
Error: Claude Agent SDK not available

AutoBuild requires the Claude Agent SDK.
```

Every RWOP1 fix shipped. `claude-agent-sdk` version 0.1.37 is installed and importable. Multiple diagnostic subprocesses confirmed `from claude_agent_sdk import query` succeeds from a fresh Python context. Yet AutoBuild continues to report the SDK as unavailable and the root cause was neither SDK-related nor RWOP1-related.

### What's actually happening

A three-layer failure:

1. **Namespace collision.** GuardKit has an internal module at
   [installer/core/lib/mcp/](../../installer/core/lib/mcp/) (the Context7
   client / MCPMonitor utilities — completely unrelated to Anthropic's
   Model Context Protocol) that shares a name with the installed
   [mcp](https://pypi.org/project/mcp/) PyPI package (Anthropic's MCP
   SDK, v1.25.0) — a transitive dependency of `claude-agent-sdk`.
2. **sys.path shadow activation.**
   [installer/core/commands/lib/greenfield_qa_session.py:29-39](../../installer/core/commands/lib/greenfield_qa_session.py)
   has a dev-mode `try/except ImportError` fallback:
   ```python
   try:
       from .state_paths import get_state_file, TEMPLATE_SESSION, TEMPLATE_PARTIAL_SESSION
   except ImportError:
       import sys
       from pathlib import Path
       _lib_dir = Path(__file__).parent.parent.parent / "lib"
       if str(_lib_dir) not in sys.path:
           sys.path.insert(0, str(_lib_dir))
       from state_paths import get_state_file, TEMPLATE_SESSION, TEMPLATE_PARTIAL_SESSION
   ```
   The "production" branch attempts `from .state_paths import ...`, but
   `installer/core/commands/lib/state_paths.py` **does not exist** —
   only `installer/core/lib/state_paths.py` does. So the production
   branch always raises `ImportError`, the fallback always runs, and
   `installer/core/lib/` is prepended at `sys.path[0]`. Once that
   directory is on the path at position 0, GuardKit's `installer/core/lib/mcp/`
   wins the `import mcp` resolution race against
   `site-packages/mcp/`.
3. **Misleading error message.**
   [guardkit/cli/autobuild.py:58-103](../../guardkit/cli/autobuild.py) has a
   `_check_sdk_available()` function whose `try/except ImportError`
   swallows the actual `ModuleNotFoundError: No module named 'mcp.types'`
   and re-prints a hard-coded message blaming `claude-agent-sdk`. The
   real failure never reaches the console.

### Verified diagnostic trace

```bash
# Direct import in subprocess → OK
$ python3 -c "from claude_agent_sdk import query; print('OK')"
OK

# Same import through guardkit.cli.autobuild → fails
$ python3 -c "
from guardkit.cli.autobuild import _check_sdk_available
print('sdk available?', _check_sdk_available())
try:
    from claude_agent_sdk import query
except ImportError as e:
    print('real error:', e)
"
sdk available? False
real error: No module named 'mcp.types'

# sys.path inspection
$ python3 -c "
import sys
before = set(sys.path)
import guardkit.cli.autobuild
after = set(sys.path)
print('ADDED:', after - before)
"
ADDED: {'/Users/.../guardkit/installer/core/lib'}

# mcp module resolves to GuardKit's internal, not Anthropic's
$ python3 -c "
import guardkit.cli.autobuild
import mcp
print('mcp resolves to:', mcp.__file__)
"
mcp resolves to: /Users/.../guardkit/installer/core/lib/mcp/__init__.py
```

### Why it's surfacing now

The bug is **latent** — the dev-mode fallback has always run because
`state_paths.py` never existed in `installer/core/commands/lib/`. What
changed is **which import chains load `greenfield_qa_session.py`**:
[TASK-FIX-RWOP1.3.3 Batches 1-2](../completed/TASK-FIX-RWOP1.3.3/) (commits
`af80cb14`, `e7c5dc44`) rewrote
[installer/core/commands/lib/__init__.py](../../installer/core/commands/lib/__init__.py)
to delete orphan re-exports. That shifted the import graph enough that
`guardkit.orchestrator.*` now pulls `greenfield_qa_session` in during
AutoBuild initialisation where it didn't before. The shadowing was a
time-bomb; RWOP1.3.3 pulled its pin.

### Why this is the same class of defect as TASK-REV-STKB

[TASK-REV-STKB](TASK-REV-STKB-stack-blindness-audit-and-bdd-plugin-architecture.md)
identified that `bdd_runner.py` violated CLAUDE.md's stated
"stack-specific plugins" architecture. This bug violates a different
but equivalent implicit contract: **internal module names must not
collide with common PyPI package names**, especially
dependencies-of-dependencies. Both are cases where GuardKit made a
local decision (pytest-only runner / `mcp` module name) without
checking whether it conflicted with an externally-defined namespace
or contract. Both slipped through because no Graphiti design rule
captured the constraint. Both are symptoms of the same process gap.

This task sits as a sibling of TASK-REV-STKB — same root cause, same
required Graphiti remediation shape — and reinforces that the
preventive-rule work in TASK-REV-STKB Workstream D must land.

## Scope

**User intent for this task** (captured verbatim from the /task-create
invocation): *"ensure we use Graphiti for knowledge query, capture
etc and we don't break anything."*

That shapes the scope: Graphiti-first diagnostic workflow, explicit
risk assessment before any code change, and seeding the findings as
a design rule for future sessions.

### In-Scope

**Workstream A — Graphiti query before touching code:**

Before proposing or applying any fix, query Graphiti comprehensively
to learn what the knowledge graph already knows. Specifically:

1. MCP queries (preferred when available):
   ```
   mcp__graphiti__search_nodes("mcp module namespace collision sys.path",
       group_ids=["guardkit__project_decisions",
                  "guardkit__project_architecture",
                  "architecture_decisions"])

   mcp__graphiti__search_memory_facts("installer core lib sys path insert",
       group_ids=["guardkit__project_decisions", "guardkit__task_outcomes"])

   mcp__graphiti__search_nodes("greenfield_qa_session state_paths",
       group_ids=["guardkit__project_decisions", "guardkit__task_outcomes"])

   mcp__graphiti__search_nodes("Context7 MCPMonitor Context7Client",
       group_ids=["product_knowledge", "guardkit__project_architecture"])
   ```
2. CLI fallback: `~/.agentecflow/bin/graphiti-check --status --task-context`
   from the guardkit repo root.
3. Record findings in `docs/reviews/TASK-REV-MCPS-graphiti-preamble.md`
   before proceeding to Workstream B. If the graph already knows
   something relevant (e.g. a "do not rename Context7 module" past
   decision, or a previous sys.path discussion), that evidence must
   inform the fix path.

**Workstream B — Name-collision sweep:**

Don't fix only this one case. Grep the runtime Python surface for
other module-names under `installer/core/lib/`,
`installer/core/commands/lib/`, and `guardkit/` subpackages that
collide with installed PyPI packages. Produce a table of:

`{local_module_path, colliding_pypi_package, severity,
transitively_imported_by}`.

Starting places to check (not exhaustive — expand based on
Workstream A's Graphiti findings):

- `mcp` — known collision (this bug)
- `cli`, `commands`, `lib`, `utils`, `models`, `tasks` — common
  generic names; check if any GuardKit submodule shadows a PyPI
  package with the same name
- `bdd`, `integrations`, `templates`, `validation` — check GuardKit
  subpackage names against PyPI search

For each finding, classify:
- **Active hazard** — currently on `sys.path` via some insert OR
  loaded via editable install in a way that shadows a dependency.
- **Latent hazard** — the collision exists in the tree but no import
  chain currently shadows anything (same state `mcp` was in before
  RWOP1.3.3 activated it).
- **Non-issue** — name collision but no shadowing risk (e.g. module
  only ever imported via fully-qualified `guardkit.X.Y`).

**Workstream C — Fix triage (three candidate fixes, pick which
ship):**

| # | Fix | Effort | Risk | Description |
|---|---|---:|---|---|
| 1 | **Minimal unblock**: change `greenfield_qa_session.py:29-39` to use an `importlib.util.spec_from_file_location` load of `state_paths.py`, OR switch both branches to the fully-qualified `installer.core.lib.state_paths` import (the editable install already puts repo root on `sys.path`). Eliminates the `sys.path.insert(0, ...)` that triggers shadowing. | ~10 lines | very low | Unblocks AutoBuild immediately without renaming anything. Does NOT fix the root-cause collision — the next `sys.path.insert` of `installer/core/lib/` from any other module re-activates the bug. |
| 2 | **Namespace rename**: rename `installer/core/lib/mcp/` to `installer/core/lib/mcp_utils/` (or `installer/core/lib/context7/` — more accurate). Update all callers. Eliminates the collision class entirely. | 15-45 min depending on caller count | low-medium | Correct long-term fix. Risk is missing a caller during the grep-and-replace. Must include a comprehensive grep audit + test-suite run before landing. |
| 3 | **Better diagnostics**: modify `guardkit/cli/autobuild.py:_check_sdk_available()` + `_require_sdk()` to capture and print the actual `ImportError` traceback instead of the hard-coded "SDK not available" text. | ~10 lines | very low | Means the next silent import-shadowing problem is diagnosed in 30 seconds rather than 30+ minutes. Should ship regardless of fix #1 vs #2 choice. |

For each fix, produce:

- **Risk table**: what could break? which tests exercise the affected
  code path? what's the rollback mechanism?
- **Test matrix**: which tests to run before/after. At minimum: full
  `pytest` suite; `guardkit autobuild --help` and
  `guardkit autobuild feature --help`; a manual `_check_sdk_available()`
  invocation.
- **Graphiti-query pre-flight**: any past decision in Graphiti that
  argues against this fix path? (E.g. a previous "we chose to put
  Context7 at module name `mcp` for reason X" decision.)
- **Graphiti-seed post-flight**: what episode/fact to add on completion.

**Workstream D — Preventive design rule (Graphiti seeding):**

Close the loop so this class of defect is caught structurally next
time. Paralleling TASK-REV-STKB Workstream D:

1. Draft a Graphiti design-rule candidate node with working name
   **"GuardKit internal module names must not shadow PyPI packages"**.
   Include:
   - The concrete symptom (silent import-shadowing, misleading error
     message, tests-green-but-production-broken).
   - The detection recipe (grep patterns; specifically
     `sys.path.insert(0, ...)` with directory containing common
     PyPI names).
   - The remediation recipe (rename to a distinctive name;
     structural imports over `sys.path.insert`).
   - A grep-able signature for the next agent.
2. Seed into `guardkit__project_decisions` on Workstream A's pre-flight
   completion (i.e. before Workstream B/C if possible — so Workstream
   B can use Graphiti as a reference during the sweep).
3. Pair with the TASK-REV-STKB *"stack-assumption must be isolated"*
   node as a sibling rule. Both are instances of a broader meta-rule
   that should also be seeded: **"Local design decisions that touch
   externally-defined namespaces (Python modules, shell PATH, HTTP
   paths, filesystem locations, environment variables) must be
   audited against those external namespaces before merging."**
4. Draft a CLAUDE.md addendum or new
   `.claude/rules/namespace-hygiene.md` mirroring the Graphiti node
   content. CLAUDE.md + Graphiti must agree on the rule, per the
   TASK-REV-STKB retrospective conclusion.

**Workstream E — Decision on fix execution path:**

At the decision checkpoint at the end of this review, pick the fix
execution strategy:

- **Minimal**: ship fix #1 + fix #3 only. Defer #2. Fastest unblock;
  leaves the root-cause collision in place with a seeded rule
  preventing re-activation.
- **Complete**: ship fix #1 + fix #2 + fix #3. Root-cause eliminated.
  Longer blast radius window during the rename.
- **Minimal-then-complete**: ship fix #1 + #3 immediately to unblock
  AutoBuild for TASK-COH-RUN1 Phase 0, then schedule fix #2 as a
  follow-on after cohort-scale evidence collects.

The review must pick one and justify against Workstream A's
evidence + Workstream B's sweep findings.

### Out-of-Scope

- Implementing any of the three fixes in this review. Fix execution
  spawns from the [I]mplement checkpoint.
- Auditing every file in the repo for generic sys.path manipulation
  hygiene — scope is name-collision-shaped sys.path inserts only.
- Refactoring the `try/except ImportError` idiom across the wider
  codebase. That's a separate hygiene review if Workstream B finds
  it's pervasive.
- Changes to `claude-agent-sdk` or Anthropic's `mcp` package. Both are
  third-party and stable.
- The broader CLAUDE.md-to-Graphiti sync programme proposed by
  TASK-REV-STKB. This review contributes one rule; the programme is
  STKB's problem.

## Acceptance Criteria

- [ ] Workstream A complete: Graphiti preamble queried + findings
      recorded in `docs/reviews/TASK-REV-MCPS-graphiti-preamble.md`.
      At least four targeted queries run; absence of relevant
      knowledge is itself a finding (confirms the rule needs seeding).
- [ ] Workstream B complete: name-collision sweep table produced
      in the main review report. Active + latent + non-issue
      classifications per finding. At minimum covers
      `installer/core/lib/`, `installer/core/commands/lib/`, and
      `guardkit/` subpackage names.
- [ ] Workstream C complete: per-fix risk tables + test matrices +
      Graphiti pre/post queries captured in the main review report.
- [ ] Workstream D complete: Graphiti design-rule candidate node
      drafted with the full content (symptom + detection recipe +
      remediation recipe + grep signature); CLAUDE.md addendum or
      `.claude/rules/namespace-hygiene.md` draft prepared. Both
      artefacts ready to seed/commit on [A]ccept.
- [ ] Workstream E complete: fix execution strategy chosen (Minimal
      / Complete / Minimal-then-complete) with a two-paragraph
      rationale citing Workstream A+B evidence.
- [ ] Main review report filed at
      `docs/reviews/TASK-REV-MCPS-namespace-collision-review.md`
      with per-workstream sections, diagnostic trace preserved,
      and an explicit "does this change TASK-COH-RUN1 Phase 0
      readiness?" answer.
- [ ] On [A]ccept: Graphiti seeded with (a) the namespace-hygiene
      design-rule node, (b) a retrospective episode naming the
      specific process gap (same pattern TASK-REV-STKB will use).
- [ ] On [I]mplement: execution sub-tasks filed per the chosen
      strategy. Suggested shape:
      - **TASK-FIX-MCPS.1** — greenfield_qa_session.py fallback
        rewrite (fix #1).
      - **TASK-FIX-MCPS.2** — `_check_sdk_available` / `_require_sdk`
        better-error messaging (fix #3).
      - **TASK-FIX-MCPS.3** — `installer/core/lib/mcp/` rename (fix #2,
        only if Complete or Minimal-then-complete chosen).
- [ ] Decision block recorded: does this review change TASK-COH-RUN1
      Phase 0 ordering? (Expected: Phase 0 runs AFTER at least
      TASK-FIX-MCPS.1 + TASK-FIX-MCPS.2 land, because AutoBuild is
      the Phase 2 target and must be functional before Phase 0
      prep begins in earnest.)

## Implementation Notes

### Working hypothesis on fix priority (confirm or revise in Workstream C)

TASK-FIX-MCPS.1 (~10 lines, very low risk) unblocks AutoBuild for the
whole FinProxy / cohort workstream and should land today-or-tomorrow.
TASK-FIX-MCPS.2 should land alongside — same blast radius, prevents
the NEXT diagnostic rabbit-hole. TASK-FIX-MCPS.3 (the rename) is the
only one with any real blast radius; decide based on Workstream B
sweep whether it can wait until post-cohort or must land now.

### Specific fix #1 code sketch (for Workstream C to refine)

Two viable approaches for `greenfield_qa_session.py:29-39`:

**Option 1a — use the editable-install-resolvable fully-qualified
path:**

```python
# CURRENT (broken):
try:
    from .state_paths import get_state_file, TEMPLATE_SESSION, TEMPLATE_PARTIAL_SESSION
except ImportError:
    import sys
    _lib_dir = Path(__file__).parent.parent.parent / "lib"
    if str(_lib_dir) not in sys.path:
        sys.path.insert(0, str(_lib_dir))
    from state_paths import get_state_file, TEMPLATE_SESSION, TEMPLATE_PARTIAL_SESSION

# PROPOSED:
from installer.core.lib.state_paths import (
    get_state_file,
    TEMPLATE_SESSION,
    TEMPLATE_PARTIAL_SESSION,
)
```

The editable install places the repo root on `sys.path` via
`_editable_impl_guardkit_py.pth`, so `installer.core.lib.state_paths`
resolves naturally with no `sys.path.insert` needed.

**Option 1b — use `importlib.util` to load from explicit path:**

```python
# Scoped load; does not touch sys.path at all
import importlib.util
_state_paths_file = Path(__file__).resolve().parents[2] / "lib" / "state_paths.py"
_spec = importlib.util.spec_from_file_location("_state_paths", _state_paths_file)
_state_paths = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_state_paths)
get_state_file = _state_paths.get_state_file
TEMPLATE_SESSION = _state_paths.TEMPLATE_SESSION
TEMPLATE_PARTIAL_SESSION = _state_paths.TEMPLATE_PARTIAL_SESSION
```

Option 1a is simpler. Option 1b avoids any assumption about editable
install. Workstream C decides.

### Specific fix #3 code sketch

```python
# CURRENT (opaque):
def _check_sdk_available() -> bool:
    try:
        from claude_agent_sdk import query  # noqa: F401
        return True
    except ImportError:
        return False

def _require_sdk() -> None:
    if not _check_sdk_available():
        console.print("[red]Error: Claude Agent SDK not available[/red]")
        ...

# PROPOSED (diagnostic):
def _check_sdk_available() -> tuple[bool, str | None]:
    """Returns (is_available, error_detail). error_detail is None on success."""
    try:
        from claude_agent_sdk import query  # noqa: F401
        return (True, None)
    except ImportError as e:
        return (False, str(e))

def _require_sdk() -> None:
    available, err = _check_sdk_available()
    if not available:
        console.print("[red]Error: Claude Agent SDK import failed[/red]")
        console.print()
        console.print(f"[yellow]Underlying error: {err}[/yellow]")
        console.print()
        # ... existing install guidance ...
        console.print()
        console.print("[dim]If the error mentions a module like 'mcp.types', 'anyio',")
        console.print("or another transitive dependency, this may be a namespace collision")
        console.print("rather than a missing install. Run: [cyan]guardkit doctor[/cyan][/dim]")
        sys.exit(1)
```

### Specific fix #2 sweep targets (for Workstream B to refine)

Initial grep seeds:

```bash
# All callers of installer.core.lib.mcp
grep -rn "from installer.core.lib.mcp\|import installer.core.lib.mcp" \
    --include="*.py" /Users/richardwoollcott/Projects/appmilla_github/guardkit/

# All callers via the installer/core/lib/mcp relative path
grep -rn "from.*mcp\.\(context7\|monitor\|detail_level\|utils\)" \
    --include="*.py" /Users/richardwoollcott/Projects/appmilla_github/guardkit/

# Other dirs under installer/core/lib/ whose names might collide
ls /Users/richardwoollcott/Projects/appmilla_github/guardkit/installer/core/lib/
```

If the sweep shows fewer than ~10 callers, fix #2 is mechanically
safe. If it shows many, Workstream C's risk column upgrades to
"medium" and Workstream E may favour Minimal-then-complete.

### Why Graphiti matters for this specific review

The user's /task-create arguments explicitly name Graphiti: *"ensure
we use Graphiti for knowledge query, capture etc and we don't break
anything."* That phrasing maps onto three concrete Graphiti usages
already specified in the workstreams:

1. **Query** (Workstream A) — before any code change, ask the graph
   what it knows about the affected modules, past decisions, and
   similar historical bugs.
2. **Capture** (Workstream D) — seed the namespace-hygiene rule as a
   queryable design-rule candidate so future agents inherit this
   lesson without having to re-derive it.
3. **Don't break** (Workstream C) — the risk table per fix explicitly
   requires a Graphiti pre-flight step asking whether any past
   decision argues against the proposed change. This is the
   structural version of "ask before acting."

This review is the first formal application of the Graphiti-first
discipline TASK-REV-STKB Workstream A will codify more broadly. If
executed well, its report becomes a reusable template.

### Out-of-band: should AutoBuild be unblocked with a quick patch before this review finishes?

The reviewer should address this explicitly. Two possibilities:

- **Wait for the review.** The full scope takes ~half a day; cohort
  preparation is already paused. A half-day delay is tolerable and
  produces cleaner artefacts.
- **Unblock first, review second.** Apply fix #1 immediately as a
  "break-glass" patch to restore AutoBuild, file the review to
  retrospectively capture the lesson + drive fixes #2 and #3. Carries
  risk that the retrospective doesn't happen cleanly if the break-
  glass fix feels "good enough."

Given the user's explicit framing ("I've purposefully waited until
fixing guardkit before running through any further on the forge /
study-tutor or jarvis repos"), **option 1 (wait for the review) is
the aligned choice** — and the user's request for this review task
confirms that preference. Proceed accordingly.

## Related

- Sibling pattern review:
  [TASK-REV-STKB-stack-blindness-audit-and-bdd-plugin-architecture.md](TASK-REV-STKB-stack-blindness-audit-and-bdd-plugin-architecture.md)
  — same meta-rule (externally-defined-namespace contract violation),
  different surface (stack-specific runners vs module names).
- Immediate predecessor (import graph that activated this bug):
  [tasks/completed/2026-04/TASK-FIX-RWOP1.3.3/](../completed/TASK-FIX-RWOP1.3.3/)
  Batches 1-2 — `installer/core/commands/lib/__init__.py` rewrite.
- Parent sweep that spawned this chain:
  [docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md](../../docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md)
- Blocked downstream:
  [tasks/backlog/r2-pipeline-closure-and-forge-cohort/TASK-COH-RUN1-forge-and-study-tutor-cohort-run.md](r2-pipeline-closure-and-forge-cohort/TASK-COH-RUN1-forge-and-study-tutor-cohort-run.md)
  — AutoBuild must work before Phase 2 fires.
- Offending code:
  - [installer/core/commands/lib/greenfield_qa_session.py:29-39](../../installer/core/commands/lib/greenfield_qa_session.py)
    (the sys.path.insert)
  - [installer/core/lib/mcp/](../../installer/core/lib/mcp/)
    (the colliding internal module)
  - [guardkit/cli/autobuild.py:58-103](../../guardkit/cli/autobuild.py)
    (the opaque error message)
- Graphiti integration reference:
  [.claude/rules/graphiti-knowledge-graph.md](../../.claude/rules/graphiti-knowledge-graph.md)
  — MCP usage, group IDs, search patterns.
- Design-rule candidate (sibling, already seeded):
  *"runner without producer anti-pattern"* — group
  `guardkit__project_decisions`, uuid
  `184731b0-3cb6-4eb2-a310-883421767dbf`. This review will add a
  companion rule node and explicitly cross-reference it in the node
  body.
- Design-rule candidate (pending from TASK-REV-STKB seed, 2026-04-23):
  *"Design-rule candidate: stack-assumption must be isolated in
  named plugin"*. This review's rule pairs with that one under the
  broader meta-rule *"local decisions touching external namespaces
  require explicit audit."*

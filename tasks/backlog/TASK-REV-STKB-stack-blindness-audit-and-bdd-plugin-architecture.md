---
id: TASK-REV-STKB
title: Stack-blindness audit across GuardKit quality gates + BDD plugin architecture proposal + retrospective on why Graphiti didn't catch the anti-pattern
status: backlog
task_type: review
review_mode: architectural
review_depth: comprehensive
decision_required: true
created: 2026-04-23T00:00:00Z
updated: 2026-04-23T00:00:00Z
priority: medium
complexity: 7
tags: [architecture-review, stack-agnostic, bdd-runner, multi-stack, graphiti-meta, preventive-rule, rwop-successor]
related_to: TASK-REV-RWOP1
related_tasks:
  - TASK-REV-RWOP1
  - TASK-REV-4D190
  - TASK-FIX-RWOP1.1
  - TASK-FIX-RWOP1.2
  - TASK-COH-RUN1
  - TASK-BDD-JBKF
  - TASK-BDD-E8954
parent_review: TASK-REV-RWOP1
blocks: TASK-BDD-ARCH
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Stack-blindness audit + BDD plugin architecture + Graphiti retrospective

## Problem Statement

GuardKit's stated core architecture is:

> *"This is an AI-powered task workflow system with built-in quality
> gates that prevents broken code from reaching production. The system
> is **technology-agnostic with stack-specific plugins**."*
> — [.claude/CLAUDE.md](../../.claude/CLAUDE.md)

The same file documents the stack-detection matrix:

- React/TypeScript → Playwright + Vitest
- Python API → pytest (pytest-bdd for BDD mode)
- .NET → xUnit/NUnit + platform-specific testing
- Mobile → Platform-specific testing
- Infrastructure → Terraform testing

Despite that stated architecture, the R2 BDD oracle at
[guardkit/orchestrator/quality_gates/bdd_runner.py](../../guardkit/orchestrator/quality_gates/bdd_runner.py)
is hardcoded to `pytest-bdd` — it shells out to `pytest` and parses
pytest-bdd's output format. On any non-Python stack (.NET SpecFlow,
TypeScript Cucumber.js, Java Cucumber-JVM, Ruby Cucumber, etc.) it
either crashes or silently returns zero scenarios.

Worse, the Coach validator consumes `bdd_results` with a schema
(`scenarios_passed`, `scenarios_failed`, `scenarios_pending`) that
cannot distinguish "BDD ran and all scenarios passed" from any of:

1. `.feature` file has no `@task:` tags → runner collected zero
   scenarios (the RWOP1.1 failure mode)
2. No `.feature` file exists at all → runner found nothing to run
3. Stack has no BDD runner implementation → runner short-circuited
4. Runner crashed mid-execution → caught-and-silenced exception

All five produce the same `{0, 0, 0}` shape at Coach's consumption
point. Coach reads that as a pass. This is the R2 contamination
pattern writ larger: structural schema-level flaw, not just a
missing nudge.

### Why this failure is process-level, not just technical

This review is deliberately scoped to include a **retrospective on
why this slipped through**, not just the architectural fix. Three
facts about our process:

1. The stack-plugin architecture is documented in
   [.claude/CLAUDE.md](../../.claude/CLAUDE.md) — the top-level
   project-instructions file every Claude session loads.
2. We operate a Graphiti knowledge graph with
   [.claude/rules/graphiti-knowledge-graph.md](../../.claude/rules/graphiti-knowledge-graph.md)
   specifically to retain architectural decisions across sessions so
   future agents inherit context without re-deriving it.
3. [TASK-REV-4D190](../../docs/reviews/TASK-REV-4D190-jarvis-first-autobuild-review.md)
   seeded a *"runner without producer anti-pattern"* Graphiti node
   when R1/R2/R3 gaps were first identified — that node later helped
   [TASK-REV-RWOP1](../../docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md)
   find 41 more instances. Graphiti worked for that specific class
   of defect.

Yet stack-blindness — a class of defect the project's own CLAUDE.md
explicitly warns against — was not captured as a design rule
anywhere Graphiti could surface it to the agent that built
`bdd_runner.py`. That agent either (a) didn't query Graphiti for
multi-stack constraints, or (b) queried and found nothing because
nobody had seeded the constraint as a rule.

This is not a one-off. The same gap likely applies to other
components in `guardkit/orchestrator/quality_gates/`,
`installer/core/commands/lib/`, and any place test-framework
assumptions could leak. A structural process fix is needed alongside
the `bdd_runner` architectural fix, or we will rediscover this
pattern in six weeks wearing a different hat.

### Immediate pressure

- **TASK-COH-RUN1** (forge + study-tutor cohort run, both Python) —
  NOT blocked by this review. Current `bdd_runner.py` works fine on
  Python. Proceed when RWOP1 ships.
- **FinProxy autobuild** (.NET, ~1–2 weeks out) — IS blocked. Cannot
  run until a SpecFlow runner exists and `bdd_runner` becomes
  stack-pluggable.
- **Every future non-Python project** — silently contaminated until
  graceful degradation is in place.

## Scope

### In-Scope

Four workstreams, ordered. All four must produce artefacts; only
the first is purely investigative.

**Workstream A — Retrospective (why did this slip?):**

Investigate how the stack-plugin contract in CLAUDE.md failed to
propagate into `bdd_runner.py`'s implementation. Specifically:

1. Walk the git history of `guardkit/orchestrator/quality_gates/bdd_runner.py` +
   its sibling task files (TASK-BDD-E8954, TASK-BDD-JBKF, any others
   that delivered the runner). Identify the implementing agent
   session if possible. Were multi-stack constraints raised at any
   point?
2. Search Graphiti at the time the runner was implemented — was the
   stack-pluggable constraint captured as a node, a fact, or an
   episode? If yes: why didn't the implementing agent see it (query
   form? group_id? task-context loader priority?). If no: why not —
   is there a process gap where architectural-intent statements in
   CLAUDE.md don't automatically become Graphiti rules?
3. Query Graphiti today (via MCP) for the current state of any
   "stack-pluggable" / "multi-stack" / "stack-agnostic" rules.
   Enumerate what's there vs what should be.
4. Record findings in a retrospective section of the review report.
   Call out specific process gaps with severity (architectural
   intent uncaptured / intent captured but unqueryable / intent
   captured + queryable but not queried).

**Workstream B — Stack-blindness audit across GuardKit:**

`bdd_runner.py` is the known case. Scope out the remaining surface:

1. Walk every file under `guardkit/orchestrator/` and
   `installer/core/commands/lib/` for hardcoded stack assumptions.
   Proxies for the search:
   - `import pytest`, `subprocess.run(["pytest", …])`,
     `.pytest_cache`, `coverage.json`, `.coverage`
   - Node/npm/yarn/pnpm mentions
   - `dotnet`, `nuget`, `.csproj`, `.sln`
   - `cargo`, `go mod`, `mvn`, `gradle`, `composer`, `gem`
   - Test-framework imports: `unittest`, `mocha`, `jest`, `vitest`,
     `xunit`, `nunit`, `mstest`, `rspec`
   - Coverage tool assumptions: `coverage.py`, `nyc`, `c8`,
     `coverlet`, `jacoco`, `simplecov`
2. For each finding, classify:
   - **Correctly isolated** — stack assumption is inside a clearly
     named plugin (`pytest_runner.py`, fine).
   - **Leaked** — stack assumption is inside a file the orchestrator
     assumes is stack-agnostic (the `bdd_runner.py` pattern).
   - **Schema-level** — shape of a produced artefact can't carry
     cross-stack information (e.g. `bdd_results` missing a `status`
     discriminator).
3. Produce a table: `{file:line, assumption, class, severity,
   remediation-sketch}`.

**Workstream C — BDD plugin architecture decision:**

Using the evidence from Workstream B, make the architectural
decisions needed for FEAT-BDD-PLUG. Specifically:

1. **`bdd_results` schema extension.** Approve or revise the
   proposed schema (draft in Implementation Notes below). Must carry
   enough metadata for Coach to distinguish real pass from every
   silent-miss mode.
2. **Runner protocol.** Define the minimum contract a stack-specific
   runner must implement. Inputs (task-scope, feature-file paths,
   tags), outputs (normalised `BddResult`), error semantics,
   configuration.
3. **Registry + dispatch.** Where does stack detection live today?
   How does the registry find the right runner? What happens on
   unknown stack (degrade silently? warn? refuse?).
4. **Coach contract update.** Coach must treat `status != "executed"`
   as *absence of evidence*, not *passing evidence*. Decide the
   exact policy: block, warn, or accept-if-no-BDD-scope? Per task
   or global?
5. **Degradation matrix.** For each known stack, what's the
   expected runner? For unknown stacks, what's the fall-through
   behaviour?
6. **Test strategy.** How do we test cross-stack runners in CI
   without requiring every stack's toolchain? (Suggestion: contract
   tests against mock runners; real-runner tests opt-in per CI.)

**Workstream D — Preventive process rule:**

Close the loop so this class of defect is caught structurally, not
by luck:

1. Draft a Graphiti design-rule candidate node — tentative name
   *"stack-assumption must be isolated in a named plugin"* — with a
   detection recipe (grep patterns) and a remediation recipe
   (extract into `{stack}_runner.py` + registry entry).
2. Draft a CLAUDE.md addendum (or a new
   `.claude/rules/stack-plugin-architecture.md`) that codifies:
   - What makes a component stack-specific vs stack-agnostic.
   - Where stack-specific code lives in the tree.
   - How to query Graphiti for the multi-stack rule before building
     a new quality-gate component.
   - Pre-build checklist: "does this component shell out to a test
     runner? if yes, is it in a `runners/` folder? if yes, does it
     register with the stack dispatcher?"
3. Propose (optional) a pre-commit or CI check that greps for
   stack-specific imports outside `runners/` folders. Scope this
   as a follow-up task, don't execute in this review.
4. Seed the new design-rule node into Graphiti
   (`guardkit__project_decisions` group) so future agents querying
   for quality-gate work inherit the constraint.

### Out-of-Scope

- **Implementing the BDD plugin architecture.** This review
  produces the design; implementation is FEAT-BDD-PLUG (spawned
  from this review's [I]mplement checkpoint).
- **Writing the SpecFlow runner.** Scope for TASK-BDD-SPECFLOW
  inside FEAT-BDD-PLUG.
- **Executing the pre-commit / CI check.** Design-only in this
  review; filed as a follow-up if evidence supports it.
- **Retrofitting existing stack-specific components that are NOT
  bdd_runner.** Workstream B produces the inventory; separate
  remediation tasks follow per item if severity warrants.
- **Fixing the root-cause if it's an LLM / agent-behaviour problem**
  (e.g. agents skip Graphiti queries under context pressure).
  Flag it, don't fix it in this review.
- **Blocking anything currently in flight in RWOP1.** Path α is
  confirmed: RWOP1.1 / 1.3 / 1.4 / 1.5 / 1.6 / 1.7 proceed; this
  review runs after or alongside.

## Acceptance Criteria

- [ ] Workstream A retrospective completed. Report names specifically:
      (a) whether multi-stack constraints were ever captured in
      Graphiti at `bdd_runner.py` implementation time, (b) what the
      current Graphiti state is, (c) at least one concrete process
      gap (architectural intent in CLAUDE.md not auto-seeded to
      Graphiti, or Graphiti query not made, or similar).
- [ ] Workstream B stack-assumption audit table produced. Total
      imperative surfaces walked and count of leaked vs isolated vs
      schema-level findings cited. Target: audit at least
      `guardkit/orchestrator/quality_gates/*.py`,
      `guardkit/orchestrator/bdd/*.py` (if any),
      `installer/core/commands/lib/*.py`, and any `installer/core/lib/*.py`.
- [ ] Workstream C architectural decisions captured in a design doc
      at `docs/design/bdd-plugin-architecture.md`. Contains: runner
      protocol (pseudo-code signature), extended `bdd_results`
      schema, registry + dispatch logic, Coach contract policy,
      degradation matrix per stack.
- [ ] Workstream D preventive rule drafted: Graphiti design-rule
      candidate text + CLAUDE.md addendum OR
      `.claude/rules/stack-plugin-architecture.md` draft. Both
      artefacts ready to seed/commit on [A]ccept.
- [ ] Review report filed at
      `docs/reviews/TASK-REV-STKB-stack-blindness-audit.md`. Includes
      per-workstream sections, per-finding severity, and a
      prioritised remediation order.
- [ ] FEAT-BDD-PLUG sub-feature scope confirmed (or revised):
      TASK-BDD-ARCH / TASK-BDD-BASE / TASK-BDD-DEGRADE /
      TASK-BDD-SPECFLOW / TASK-REV-BDD-STACK. Estimates and
      dependencies validated against the design doc.
- [ ] On [A]ccept: Graphiti seeded with (a) the stack-plugin
      design-rule node, (b) a retrospective episode naming the
      specific process gap so future agents see the lesson.
- [ ] On [I]mplement: `tasks/backlog/feat-bdd-plug/` folder created
      with README + IMPLEMENTATION-GUIDE + the 5 sub-tasks, same
      layout pattern as FEAT-RWOP1.
- [ ] Decision block recorded: does this change TASK-COH-RUN1's
      go/no-go for forge + study-tutor? (Expected: no — both are
      Python.) And explicit go/no-go for FinProxy autobuild
      (Expected: blocked on FEAT-BDD-PLUG through TASK-BDD-SPECFLOW.)

## Implementation Notes

### Draft `bdd_results` schema (for Workstream C to refine)

```python
bdd_results = {
    "status": "executed"                       # ran end-to-end
            | "skipped_no_runner"              # stack has no registered runner
            | "skipped_no_scenarios"           # no .feature files in scope
            | "skipped_no_tagged_scenarios"    # .feature files present but none @task:-tagged
            | "skipped_bdd_disabled"           # project opted out
            | "error",                         # runner crashed; see reason
    "runner": "pytest-bdd" | "specflow" | "cucumber-js" | null,
    "stack_detected": "python" | "dotnet" | "typescript" | "java" | "ruby" | "unknown",
    "scenarios_passed": int,
    "scenarios_failed": int,
    "scenarios_pending": int,
    "reason": str | null,           # human-readable for Coach + logs
    "artefacts": {
        "feature_files": [str],     # paths inspected
        "runner_log": str | null,   # path to captured runner stdout/stderr
        "output_format": str | null # e.g. "trx", "json", "pytest-stdout"
    }
}
```

Coach rule: `status != "executed"` is *absence of BDD evidence*,
NOT *passing BDD evidence*. Whether that absence blocks task
approval is a per-task policy (Workstream C-4 decision).

### Draft BddRunner protocol (for Workstream C to refine)

```python
from typing import Protocol, List, Literal
from pathlib import Path

class BddRunner(Protocol):
    stack: Literal["python", "dotnet", "typescript", "java", "ruby"]
    name: str  # "pytest-bdd", "specflow", "cucumber-js", etc.

    def is_available(self, project_root: Path) -> bool:
        """Return True if the runner's toolchain is installed and usable."""
        ...

    def discover_features(self, project_root: Path) -> List[Path]:
        """Return all .feature file paths the runner would consider."""
        ...

    def run_for_task(
        self,
        project_root: Path,
        task_id: str,
        task_scope_tags: List[str],  # e.g. ["@task:TASK-FOO-123"]
    ) -> "BddResult":
        """Execute scenarios matching task_scope_tags, return normalised result."""
        ...
```

### FEAT-BDD-PLUG sub-task estimates (to validate in Workstream C)

| # | Task | Kind | Complexity | Depends on |
|---|---|---|---:|---|
| 1 | TASK-BDD-ARCH — this review's [I]mplement artefact | decision review | 5 | — |
| 2 | TASK-BDD-BASE — implement `BddRunner` protocol + `runners/registry.py` + move pytest-bdd code into `runners/pytest_bdd_runner.py` (refactor, no behaviour change) | impl | 4 | #1 |
| 3 | TASK-BDD-DEGRADE — extend `bdd_results` schema + dispatch for degradation cases + Coach contract update | impl | 6 | #2 |
| 4 | TASK-BDD-SPECFLOW — SpecFlow runner for FinProxy | impl | 6 | #3 |
| 5 | TASK-REV-BDD-STACK — closure review (Coach behaviour per degradation path, per-stack runner parity) | review | 3 | #4 |

Budget: ~2–3 weeks at one engineer, less if parallelised after #2.

### Methodology hints

- Workstream A: start with `git log --all --follow guardkit/orchestrator/quality_gates/bdd_runner.py`
  and `git log --all -- tasks/completed/**TASK-BDD*.md` to reconstruct the
  implementation history. Pair with MCP Graphiti queries:
  `search_nodes("stack agnostic multi-stack plugin")` +
  `search_memory_facts("pytest-bdd stack specific")` across
  `product_knowledge`, `architecture_decisions`, `guardkit__project_decisions`,
  `guardkit__project_architecture`.
- Workstream B: use `grep -rn "subprocess.*pytest\|import pytest\|'pytest'"` +
  analogues for other stacks. Build the inventory in a spreadsheet or
  markdown table; classify per row.
- Workstream C: the draft schema and protocol above are starting
  points — revise based on Workstream B findings (e.g. if coverage
  tooling has the same shape, the schema may need a parallel
  `coverage_results` upgrade).
- Workstream D: the CLAUDE.md addendum should be short and
  imperative. The Graphiti node should include a grep recipe the
  next agent can actually run.

### Anti-pattern to avoid in this review itself

**Don't let the retrospective become punitive.** This isn't about
fault-finding; it's about closing a process gap. The aim is
structural prevention, not blame. Name agents / sessions only where
strictly needed to trace the causal chain; frame findings as
"capability gap" not "agent error."

## Related

- Parent review:
  [docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md](../../docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md)
  §Cohort impact — where the stack-pytest-hardcoding was first
  surfaced as a contamination risk
- Grandparent review:
  [docs/reviews/TASK-REV-4D190-jarvis-first-autobuild-review.md](../../docs/reviews/TASK-REV-4D190-jarvis-first-autobuild-review.md)
  §R1 / Addendum A — original runner-without-producer design-rule seed
- Stated architecture:
  [.claude/CLAUDE.md](../../.claude/CLAUDE.md) — *"technology-agnostic
  with stack-specific plugins"* + stack detection matrix
- Graphiti integration:
  [.claude/rules/graphiti-knowledge-graph.md](../../.claude/rules/graphiti-knowledge-graph.md)
  — MCP access, group IDs, search patterns
- Offending component:
  [guardkit/orchestrator/quality_gates/bdd_runner.py](../../guardkit/orchestrator/quality_gates/bdd_runner.py)
- R2 origin tasks:
  - [tasks/completed/TASK-BDD-E8954](../completed/TASK-BDD-E8954/) (R2 task-scope runner)
  - [tasks/completed/TASK-BDD-JBKF](../completed/TASK-BDD-JBKF/) (R2 F584 fix)
- Cohort run (Python, NOT blocked by this):
  [tasks/backlog/r2-pipeline-closure-and-forge-cohort/TASK-COH-RUN1-forge-and-study-tutor-cohort-run.md](r2-pipeline-closure-and-forge-cohort/TASK-COH-RUN1-forge-and-study-tutor-cohort-run.md)
- Design-rule candidates (Graphiti): *"runner without producer
  anti-pattern"* (uuid `184731b0-3cb6-4eb2-a310-883421767dbf`) —
  this review's preventive rule will pair with that one as a
  sibling "stack-assumption must be isolated" entry.

## Sequencing (confirmed with user — Path α)

- **First:** RWOP1.1 / RWOP1.3 / RWOP1.4 / RWOP1.5 (landed) / RWOP1.6 / RWOP1.7 land.
- **Then:** TASK-COH-RUN1 fires against forge + study-tutor (both Python).
- **Then:** this review (TASK-REV-STKB) runs.
- **Then:** FEAT-BDD-PLUG executes (via this review's [I]mplement).
- **Then:** FinProxy autobuild unblocks.

Estimated calendar: ~1 week for RWOP1 + cohort, ~half-week for this
review, ~2 weeks for FEAT-BDD-PLUG. FinProxy-ready in ~3.5 weeks
from today, matching the user's stated "1–2 weeks perhaps" rough
window plus architectural investment.

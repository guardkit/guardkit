---
id: TASK-REV-4D012
title: Review AutoBuild Coach integration verification gaps
status: review_complete
task_type: review
review_mode: architectural
review_depth: comprehensive
decision_required: true
created: 2026-04-21T00:00:00Z
updated: 2026-04-21T00:00:00Z
previous_state: backlog
state_transition_reason: "Review complete — awaiting decision checkpoint"
priority: high
complexity: 0
tags: [autobuild, coach, review, integration-testing, bdd, feature-spec, feature-plan, c4-diagrams, quality-gates]
test_results:
  status: pending
  coverage: null
  last_run: null
review_results:
  mode: architectural
  depth: comprehensive
  score: null
  findings_count: 6
  recommendations_count: 6
  decision: implement
  decision_detail: "Implement R1-R3 with scoping refinements (warn-mode R1; artefact-triggered, task-scoped, Python-only R2; between-waves R3). Defer R4/R5. Reject R6."
  report_path: docs/reviews/TASK-REV-4D012-autobuild-coach-integration-review.md
  completed_at: 2026-04-21T00:00:00Z
  graphiti_episodes_written: 2
  followup_tasks:
    - TASK-AC-53445
    - TASK-BDD-E8954
    - TASK-SMK-F703A
  deferred_recommendations:
    - R4  # cross-phase Coach input
    - R5  # opt-in integration gate
  rejected_recommendations:
    - R6  # role boundary change — violates feature-build-invariants
  cohort_sequencing:
    ship_order: [TASK-AC-53445, TASK-BDD-E8954, TASK-SMK-F703A]
    run_order: [jarvis, "forge+study-tutor in parallel"]
  headline: "Coach surface is unit-shaped; BDD oracle is generated but discarded before feature-build; AC phrasing is the real differentiator, not integration tests. R1-R3 implemented before jarvis/forge/study-tutor cohort."
  prior_hypotheses_falsified:
    - "YTM succeeded because integration tests ran via Coach (falsified by addopts)"
    - "specialist-agent had worst Player-Coach rate (falsified: 95%, higher than YTM's 81%)"
---

# Task: Review AutoBuild Coach integration verification gaps

## Problem Statement

AutoBuild is stable and the happy path works end-to-end, but **integration-level verification is inconsistent**. Some features ship clean out of the box (nats-core, nats-infrastructure, agentic-dataset-factory, youtube-transcript-mcp); others require meaningful post-build work (specialist-agent). The working hypothesis from the specialist-agent experience is that the **Coach performs shallow checks** — unit tests + gates pass, but feature-level integration behaviour (the intent captured in `/feature-spec` BDD) isn't actually exercised before the Coach approves.

With `/system-arch` now complete in **jarvis**, **forge**, and **study-tutor** and large AutoBuild feature runs imminent, we need a structured review of Coach verification scope and the upstream `/feature-spec` + `/feature-plan` commands **before** those runs start. Target: move from ~80% ready to ~90% ready **without regressing** what already works.

## Scope

This is a **review / decision task**. No implementation. Output is a review report + recommendations + (optionally) follow-on implementation tasks.

### In-Scope

1. **AutoBuild Coach verification depth** — What does the Coach actually check? Where does "shallow" bite?
2. **BDD specification-by-example gap** — Why isn't Gherkin produced by `/feature-spec` being used as the Coach's verification oracle?
3. **Feature-level integration test feasibility** — Where did integration/e2e tests make the difference (youtube-transcript-mcp) and where are they viable as a default?
4. **Execution-flow tracing** — Follow a feature-build run across agent, command, and system boundaries.
5. **`/feature-spec` and `/feature-plan` quality** — Are they producing artefacts the Coach could verify against? Are BDD scenarios / acceptance criteria / plans propagating into the Player-Coach loop?
6. **Regression risk envelope** — What cannot change before the jarvis/forge/study-tutor runs?

### Out-of-Scope

- Implementation of any fixes (create follow-on `/task-work` tasks instead).
- Changes to the Player agent's generation strategy.
- Template-level changes unrelated to verification.

## Source Material to Analyse

### AutoBuild command histories (full traceability)

- `/Users/richardwoollcott/Projects/appmilla_github/specialist-agent/command_history.md` *(primary — the "required more work" case)*
- `/Users/richardwoollcott/Projects/appmilla_github/nats-infrastructure/command-history.md` *("worked out of the box")*
- `/Users/richardwoollcott/Projects/appmilla_github/nats-core/command-history.md` *("worked out of the box")*

### Specialist-agent per-feature histories (for depth)

- `fature-spec-DDD-context-map-history.md` *(sic — filename typo)*
- `feature-plan-DDD-context-map-history.md`
- `feature-spec-FEAT-001..007-history.md`
- `feature-plan-{adaptive-mode-inference,ADR-output,assumption-defence,fidelity,graphiti-query-tool,mcp-server-adapter,mode2-pipeline,mode3-explorer,nats-fleet-integration,role-learning,session-write,web-search}-history.md`
- `system-{arch,design,plan}-history.md`
- `phase1b-phase2-validation-history.md`

### Success-pattern references

- **youtube-transcript-mcp** — first-time success attributed to integration/e2e tests running as part of verification.
- **agentic-dataset-factory** — broadly successful (recall from memory; corroborate via `docs/reviews/` if evidence exists).

### Prior consolidation review (related analysis)

- `/Users/richardwoollcott/Projects/appmilla_github/specialist-agent/tasks/backlog/TASK-REV-POEX-review-feat-por-ext-consolidation-path.md` — prior review of the feat-por-ext consolidation path in specialist-agent. Read for overlap and to avoid duplicating conclusions.

### GuardKit code/config

- `installer/core/agents/autobuild-coach.md` (+ project copy `.claude/agents/autobuild-coach.md`)
- `installer/core/agents/autobuild-player.md`
- `installer/core/commands/feature-spec.md`, `feature-plan.md`, `feature-build.md`, `task-work.md`
- `guardkit/` AutoBuild orchestration source (Player-Coach loop, quality-gate JSON shape)
- `.claude/rules/autobuild.md`, `.claude/rules/graphiti-knowledge*.md`
- Existing artefacts: `docs/reviews/autobuild-diagnostic-diagrams.md`, `docs/reviews/autobuild-fixes`, `docs/reviews/autobuild-api-key-isolation`

## Deliverables

1. **Review Report** — `docs/reviews/TASK-REV-4D012-autobuild-coach-integration-review.md`
   - Executive summary (1 page, decision-ready).
   - Findings by theme (Coach depth, BDD gap, integration-test feasibility, `/feature-spec` + `/feature-plan` quality).
   - Evidence table: for each finding, cite the command_history.md lines / code references / artefact paths that support it.
   - Success-vs-struggle comparison matrix across: nats-core, nats-infrastructure, specialist-agent, youtube-transcript-mcp, agentic-dataset-factory.

2. **C4 sequence diagrams** (Mermaid, embedded in the report)
   - **L1 — Context**: user → `/feature-build` → GuardKit → external systems (Graphiti, LLM providers, test runners).
   - **L2 — Container**: `/feature-spec` → `/feature-plan` → `/task-work` → Player ↔ Coach → quality-gate JSON → decision.
   - **L3 — Component** (at minimum for the Coach): task_work_results.json read path, independent test-verification path, acceptance-criterion enumeration, BDD-scenario consumption (or absence thereof).
   - Cross-boundary annotations: what crosses the filesystem boundary, the subprocess boundary (pytest/npm/dotnet), the MCP boundary (Graphiti), and the LLM-call boundary.

3. **Recommendations** (prioritised, each tagged with regression risk Low/Med/High)
   - What to change in the Coach (verification depth).
   - What to change in `/feature-spec` output so BDD is machine-consumable as a Coach oracle.
   - Where feature-level integration tests are viable as a default vs opt-in.
   - Sequencing: what is **safe to ship before** jarvis/forge/study-tutor runs vs what waits.

4. **Follow-on task list** — draft `/task-create` commands for each recommendation accepted at checkpoint.

## Acceptance Criteria

- [ ] All three primary `command*history.md` files traced end-to-end; key divergence points identified with file:line citations.
- [ ] C4 L1 + L2 diagrams produced; L3 covers the Coach at minimum.
- [ ] Success-vs-struggle matrix covers at least 5 repos (nats-core, nats-infrastructure, specialist-agent, youtube-transcript-mcp, agentic-dataset-factory).
- [ ] Each recommendation has explicit regression-risk classification for the jarvis/forge/study-tutor cohort.
- [ ] Report answers: *"Why did youtube-transcript-mcp pass first-time and specialist-agent did not?"* with evidence, not speculation.
- [ ] Report answers: *"Is the `/feature-spec` BDD output actually consumed anywhere in the Player-Coach loop?"* with a yes/no + citations.
- [ ] Decision checkpoint presented: [A]ccept / [I]mplement / [R]evise / [C]ancel, with draft follow-on tasks if [I].
- [ ] Prior consolidation review (`specialist-agent/tasks/backlog/TASK-REV-POEX-...`) consulted; any overlap with its conclusions is called out explicitly.

## Non-Goals / Guardrails

- **No code changes** in this task. Recommendations only.
- **No Coach prompt edits** proposed without evidence from historical runs showing the current prompt misses a specific class of defect.
- **Do not overclaim the problem** — user's baseline is that AutoBuild works; target is 80% → 90%, not a rewrite.

## Suggested Review Modes

Run with `/task-review TASK-REV-4D012 --mode=architectural --depth=deep` — this is cross-component (Player, Coach, `/feature-spec`, `/feature-plan`, `/feature-build`) and cross-boundary (filesystem, subprocess, MCP, LLM). Architectural-reviewer + software-architect subagents are appropriate; consider a parallel qa-tester pass focused on the "what would we test?" dimension of feature-level integration.

## Context / Why Now

- Jarvis, forge, study-tutor are at `/system-arch`-complete; autobuild feature runs start within days.
- specialist-agent experience established that Coach depth is the weakest link.
- Spec-by-example BDD exists in the pipeline but appears unused as a verification oracle — high-leverage if true.
- User's explicit framing: happy with current state, looking for a **90% uplift**, not a rewrite. Recommendations should be proportionate.

## Related

- `installer/core/agents/autobuild-coach.md`
- `installer/core/commands/feature-spec.md`, `feature-plan.md`, `feature-build.md`
- `docs/reviews/autobuild-diagnostic-diagrams.md`
- `.claude/rules/autobuild.md`
- Prior review tasks: `TASK-REV-8A31`, `TASK-REV-B601`, `TASK-REV-FFD3` (check for overlap before starting)

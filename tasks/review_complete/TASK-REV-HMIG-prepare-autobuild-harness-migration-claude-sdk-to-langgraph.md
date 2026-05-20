---
id: TASK-REV-HMIG
title: Prepare architectural + implementation review of AutoBuild to support migration from Claude Agents SDK to LangGraph/DeepAgents harness
status: review_complete
task_type: review
review_mode: architectural
review_depth: comprehensive
decision_required: true
created: 2026-05-19T00:00:00Z
updated: 2026-05-20T10:30:00Z
previous_state: backlog
state_transition_reason: "Architectural review completed and revised three times (Revisions 1 + 2 + 3) after three [R]evise checkpoints; Revision 3 corrected the Coach architecture from deterministic-primary back to LLM-primary per the Block adversarial-cooperation paper; awaiting Phase 5 decision (implementation in progress)"
review_results:
  mode: architectural
  depth: comprehensive
  verdict: proceed-with-conditions
  conditions_count: 5
  findings_count: 8           # eight failure patterns catalogued
  decisions_count: 12         # D-01..D-11 + D-01a (added Revision 2)
  recommendations_count: 8    # revised: 10 (v1) → 7 (Revision 1) → 8 (Revision 2: added TASK-HMIG-000)
  ac_compliance: 10/10
  cross_repo_files_swept: 62
  sdk_touchpoints_catalogued: 38
  total_effort_estimate_hours: 237   # revised: 239 (v1) → 223 (Rev1) → 229 (Rev2) → 237 (Rev3, +8h for LLM Coach restoration)
  validation_slack_hours: 33         # revised: 31 (v1) → 47 (Rev1) → 41 (Rev2) → 33 (Rev3)
  cutover_target: 2026-06-10
  validation_margin_days: 5
  central_falsifier_threshold: 0.75
  implementation_home:
    primary_repo: guardkitfactory       # new repo per Revision 2 / D-01
    template: langchain-deepagents      # per Revision 2 / D-01a
    consumer_repo: guardkit             # imports guardkitfactory as runtime dep
  revision_count: 3
  revisions:
    - revision: 1
      date: 2026-05-19
      trigger: operator [R]evise at Phase 5 checkpoint
      scope: D-03 (DeepAgents built-in tools), D-10 (Skills as role-packaging), D-11 (sandbox backend swap), R-01/R-05 severity reductions, Wave 1 collapse (TASK-HMIG-002/003/004/005 → TASK-HMIG-002R)
      effort_delta_hours: -16
      slack_delta_hours: +16
      sources_added:
        - https://github.com/langchain-ai/deepagents/tree/main/examples/deploy-coding-agent
        - https://docs.langchain.com/oss/python/deepagents/overview
        - https://docs.langchain.com/oss/python/deepagents/customization
        - https://docs.langchain.com/oss/python/deepagents/backends
        - https://docs.langchain.com/oss/python/deepagents/sandboxes
        - https://docs.langchain.com/oss/python/deepagents/permissions
        - https://docs.langchain.com/oss/python/deepagents/skills
        - https://www.langchain.com/blog/langchain-skills
    - revision: 2
      date: 2026-05-19
      trigger: operator [R]evise at Revision 1 checkpoint ("new repo, use one of the langchain templates")
      scope: D-01 rewritten (new repo guardkitfactory), D-01a added (template choice = langchain-deepagents base), TASK-HMIG-000 added (bootstrap), TASK-HMIG-006 +2h cross-repo wiring, R-11 added (template rough edges), R-12 added (cross-repo version pinning), §10 reconciliation strengthened (new code outside frozen paths)
      effort_delta_hours: +6
      slack_delta_hours: -6
      sources_added:
        - installer/core/templates/langchain-deepagents/manifest.json
        - installer/core/templates/langchain-deepagents-orchestrator/manifest.json
        - installer/core/templates/langchain-deepagents-weighted-evaluation/manifest.json
        - docs/guides/portfolio-python-pinning.md
    - revision: 3
      date: 2026-05-20
      trigger: operator [R]evise after challenging the v1/v2 D-06 framing — "the original idea was to base this on the paper from block adversarial cooperation… I don't want deterministic python"
      scope: |
        D-06 inverted (was: deterministic CoachValidator survives intact; now: LLM Coach restored as primary with CoachValidator reframed as evidence supplier).
        §1.1 condition #1 rewritten.
        TASK-HMIG-008 renamed to TASK-HMIG-008R, scope expanded from 4h (honesty Layer 1 wiring) to 12h (LLM-Coach-primary restoration + CoachEvidenceBundle refactor + zero-cardinality prompt guards + GUARDKIT_COACH_LEGACY emergency-revert).
        R-13 added (LLM Coach absence-of-failure recurrence risk).
        Reframing of §5 Patterns 3 + 4 (deterministic short-circuit logic is gone; LLM Coach with structured evidence replaces it).
      effort_delta_hours: +8
      slack_delta_hours: -8
      ground_truth_citations:
        - guardkit/orchestrator/autobuild.py:5281-5355 (CoachValidator primary; SDK fallback)
        - guardkit/orchestrator/agent_invoker.py:1828-1947 (current LLM Coach SDK impl, running as fallback)
        - guardkit/orchestrator/quality_gates/coach_validator.py:1-31 (Option D docstring)
        - tasks/completed/2026-05/TASK-AB-FIX-INVAB1/ (May-6 fix that wired honesty into deterministic path; did NOT restore LLM-primacy)
      sources_added:
        - https://block.xyz/documents/adversarial-cooperation-in-code-synthesis.pdf
        - .claude/reviews/TASK-INV-AB1-review-report.md
        - .claude/reviews/TASK-REV-0414-review-report.md
  report_path: .claude/reviews/TASK-REV-HMIG-review-report.md
  implementation_guide_path: .claude/reviews/TASK-REV-HMIG-implementation-guide.md
  completed_at: 2026-05-19T18:00:00Z
  revised_at: 2026-05-20T10:30:00Z
priority: critical
complexity: 9
deadline: 2026-06-15
tags:
  - review
  - autobuild
  - migration
  - claude-sdk
  - langgraph
  - deepagents
  - bdd
  - plugin-architecture
  - c4-diagrams
  - strategic-decision
related_to: TASK-REV-ABST
related_tasks:
  - TASK-REV-ABST   # autobuild BDD-verification stocktake (review_complete, 2026-05-10) — decided "Narrow (Option B)" + gate freeze
  - TASK-REV-STKB   # stack-blindness audit + BDD plugin architecture proposal (backlog) — prior art for tech-agnostic BDD
  - TASK-REV-4D012  # autobuild coach integration gaps
  - TASK-REV-1B452  # honesty-verification false-fail after state-bridge move
  - TASK-AB-FIX-INVAB1  # absence-of-failure-is-not-success seed
  - TASK-FIX-CAUD-PREFLIGHT-C3B0  # most recent pre-turn-1 gate fix
related_decisions:
  - DECISION-DF-001  # no cloud API on critical path
research_input: docs/research/autobuild-harness-migration.md
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Prepare AutoBuild Harness Migration Review (Claude Agents SDK → LangGraph/DeepAgents)

> **This is a `/task-review` task, not a `/task-work` task.** Do not implement
> anything. The deliverable is an evidence-backed architectural + implementation
> review report (with C4 diagrams traced from the live execution flow) and a
> set of strategic decisions about *how* to migrate the AutoBuild harness off
> the Claude Agents SDK before Anthropic's API-key enforcement on **15 June 2026**.

## Why this review is happening now

[`docs/research/autobuild-harness-migration.md`](../../docs/research/autobuild-harness-migration.md)
(2026-05-19) frames the constraint:

- **15 June 2026** — Anthropic enforces API-key validation on its endpoints.
  The local-inference redirect pattern (`ANTHROPIC_BASE_URL=http://gb10:9000/v1`
  with a dummy key) stops working. AutoBuild — the core build engine of the
  whole software factory — stops running on local models, in direct violation
  of DECISION-DF-001 (no cloud API on critical path).
- **27 days** to validate a replacement.
- The research document already proposes the **target stack**: LangGraph +
  DeepAgents for the AutoBuild coding-agent harness, with OpenCode for
  interactive coding (out of scope for this review). The same framework is
  already running specialist-agent, jarvis, study-tutor, and
  agentic-dataset-factory at ~90-95% first-pass success.

The research document is a strategic case for the *destination*. **This review
must produce the architectural and implementation evidence required to execute
the migration** — what to preserve, what to redesign, what to drop, and where
the BDD-verification scars from the last two months should heal differently.

## Scope of this review

### In scope

1. **Trace the current AutoBuild execution flow end-to-end** and produce
   **C4 diagrams** (Context, Container, Component, Code) from the trace.
   The diagrams must be derived from actually walking the live code — not
   from documentation or memory — and must include every boundary the
   migration has to honour:
   - `guardkit autobuild` CLI entrypoint → `AutoBuildOrchestrator`
   - Player invocation path (Claude Agent SDK subprocess / library call)
   - Coach invocation path (deterministic `CoachValidator` +
     `CoachVerifier`, and the LLM-Coach fallback)
   - Tool surface exposed to the Player (read, write, edit, bash, list_dir,
     plus any GuardKit-specific tools)
   - State / checkpoint surface (turn states, baseline diffs,
     `state_transitions.json`, completion-promise tracking)
   - Quality-gate stack invoked by the Coach (BDD runner, smoke gates,
     test discovery, honesty verification, plan audit, etc.)
   - NATS / Graphiti / git side-channels
   - All the seams the Claude Agents SDK currently fills (system-prompt
     injection, session management, tool calling, headless execution,
     context-window management)

2. **Map every SDK-specific touch-point** in the codebase. For each,
   classify it as: *trivially portable*, *needs adaptation*, or
   *fundamentally re-architected by the migration*. Include line/file
   references. The output is the "what to port" checklist.

3. **Synthesise the BDD-verification tortured history** into a failure-pattern
   catalogue. Use the existing evidence:

   - `tasks/review_complete/TASK-REV-ABST-autobuild-bdd-verification-stocktake.md`
     (2026-05-10) — Option B "Narrow" decision, 3.57:1 fix-to-gate ratio,
     10% first-pass success, the active gate-stack freeze 2026-05-11→17.
   - `tasks/backlog/TASK-REV-STKB-stack-blindness-audit-and-bdd-plugin-architecture.md`
     — prior art for the technology-agnostic plugin proposal this review
     must extend.
   - `tasks/review_complete/TASK-REV-4039-review-bdd-requirekit-marker-detection.md`,
     `tasks/completed/2026-05/autobuild-bdd-oracle-fix/TASK-AB-001..004*` —
     per-task glue modules, env-var contract (`GUARDKIT_BDD_TASK_ID`),
     pytest-bdd skip-on-missing-step false-greens.
   - `.claude/rules/absence-of-failure-is-not-success.md`
   - `.claude/rules/path-string-mismatch-is-not-dishonesty.md`
   - `.claude/rules/bdd-per-task-glue.md`
   - `.claude/rules/namespace-hygiene.md`
   - `.claude/reviews/TASK-REV-ABST-review-report.md` and siblings
     (TASK-REV-1B452, TASK-REV-0414, TASK-REV-FFC6, TASK-REV-AB04,
     TASK-REV-50E1, TASK-REV-4D012).
   - **Cross-repo evidence**: every `autobuild-*` history file under
     `~/Projects/appmilla_github/forge/docs/history/`,
     `~/Projects/appmilla_github/jarvis/docs/history/`,
     `~/Projects/appmilla_github/study-tutor/docs/history/`, and
     `~/Projects/appmilla_github/specialist-agent/docs/history/`. These
     contain the actual failure runs the rules above abstract over.

   For each pattern, identify: (a) the harness behaviour that enabled the
   failure, (b) whether the LangGraph/DeepAgents harness would inherit, fix,
   or mask the same pattern, and (c) what the migration must explicitly
   carry forward as a guard.

4. **Design the BDD verification surface for the new harness — technology-
   agnostically**. The prompt's specific brief is:

   > *"ideally in a technology agnostic manner, maybe the LangGraph Deep
   > Agents SDK harness can load the tooling dynamically based on the
   > language being implemented."*

   This means:
   - Codify what "the BDD oracle" actually is as an *interface*, decoupled
     from pytest-bdd, the JUnit-XML parser, the per-task marker filter, the
     env-var contract, and the worktree path conventions.
   - Propose a plugin loader pattern (analogous to GuardKit's stack-detection
     matrix — Python→pytest-bdd, .NET→SpecFlow/Reqnroll, TypeScript→Cucumber.js,
     etc.) that the LangGraph harness can resolve at runtime from the detected
     target stack.
   - State which existing failure-pattern guards (per-task glue naming,
     zero-cardinality precondition, identity-bounded path resolution) become
     *interface contracts* in the new design and which become
     *plugin-implementation concerns*.
   - Be explicit about whether DeepAgents' built-in file-system / sub-agent
     tools subsume any GuardKit-specific quality-gate plumbing, and where
     GuardKit must keep its own implementations.

5. **Propose a migration sequencing plan**, evidence-backed by the C4
   trace and the touch-point map, that fits inside the 27-day window with
   margin. Reconcile against:
   - the research-doc's Phase 1/2/3 sequencing,
   - the active gate-stack freeze (`.claude/state/gate-freeze-2026-05-17.md`),
   - the existing specialist-agent Player-Coach LangGraph template at
     `installer/core/templates/langchain-deepagents/` (and `-orchestrator`,
     `-weighted-evaluation` variants),
   - TASK-REV-ABST's "narrow" mandate (no new gates without removing one).

6. **Decision points the review must surface** (each as a checkpoint
   for the user):
   - Repository home for the new harness: `guardkit` vs `guardkitfactory`
     vs a new package (research-doc Open Question #1).
   - Reuse vs reimplementation of specialist-agent tools (Open Question #2-3).
   - Whether to expose the harness as an A2A endpoint in v1 or defer
     (Open Question #5).
   - How BDD plugin discovery interacts with `guardkit init` template
     selection and stack detection.
   - Whether the deterministic `CoachValidator` path survives the migration
     or is collapsed back into a single LLM-Coach node with tools (the
     2025-12-30 Option D split that produced the absence-of-failure-is-not-
     success class).

### Explicitly out of scope

- The OpenCode-for-interactive-coding decision (Phase 1 of the research
  doc). That is a separate decision track and does not block AutoBuild.
- Implementation of any tool, node, or harness wiring. This task produces
  the *plan*; the implementation lives in follow-on `/task-work` tasks
  spawned from this review's recommendations.
- ADR drafting for the migration. ADRs (`ADR-ARCH-031`, `ADR-ARCH-032`)
  are explicitly downstream of this review's decisions.
- Changes to the Graphiti seed schema or NATS contracts. Those are
  side-channels the harness must continue to honour, but their internal
  design is not on the table here.

## Deliverables

The review must produce **all** of the following under
`.claude/reviews/TASK-REV-HMIG-*`:

1. **`TASK-REV-HMIG-review-report.md`** — the primary deliverable. Must
   include:
   - Executive summary (≤2 pages) with go/no-go-with-conditions verdict on
     the LangGraph/DeepAgents migration as scoped in the research doc.
   - **C4 diagrams** (Mermaid or rendered PNG, embedded inline) at all four
     levels, derived from the traced execution flow. Each diagram annotated
     with the SDK touch-points discovered in step 2.
   - SDK touch-point map (file:line table, ≤100 rows, classified by
     port-difficulty).
   - BDD failure-pattern catalogue cross-referenced to the existing rules
     and the cross-repo history evidence.
   - Technology-agnostic BDD plugin interface specification (interface
     name, method signatures, lifecycle hooks, contract tests the harness
     must run against any plugin to honour the migration's guards).
   - Migration sequencing plan with named follow-on tasks (each ≤8h, each
     with a falsifier criterion).
   - Decision-point table with recommendation + dissenting view per point.
   - Risk register, calibrated against the 27-day window.

2. **`TASK-REV-HMIG-c4-diagrams.md`** *(optional split)* — if the diagrams
   exceed what the main report can carry inline, factor them into a sibling
   file linked from the report. Include the source for every diagram so
   future agents can regenerate them after code drift.

3. **`TASK-REV-HMIG-implementation-guide.md`** — the seed for the follow-on
   `/feature-plan` if the user [I]mplements at the checkpoint. Lists every
   downstream task as a `name + acceptance-criteria + parallel-group` row,
   ready to be parsed by `/feature-plan` and `/feature-build`.

## Acceptance Criteria

- [ ] AC-001: Live execution-flow trace produced (file:line list of every
      function executed by `guardkit autobuild task TASK-XXX` for a known
      passing fixture, captured by reading the code — not by running it).
- [ ] AC-002: C4 diagrams (Context, Container, Component, Code) rendered
      and embedded in the report, each annotated with SDK touch-points.
- [ ] AC-003: SDK touch-point map enumerates ≥95% of `claude_agent_sdk`,
      `anthropic`, and `ANTHROPIC_BASE_URL` references in `guardkit/`,
      `installer/core/`, and any test fixtures that pin SDK behaviour.
      Each row classified `trivial-port` | `adaptation` | `redesign`.
- [ ] AC-004: BDD failure-pattern catalogue contains ≥6 distinct patterns
      drawn from the existing rules + cross-repo history, each with the
      `harness-behaviour-that-enabled-it / langgraph-inheritance-verdict /
      migration-guard-required` triple.
- [ ] AC-005: Technology-agnostic BDD plugin interface specified with
      ≥3 worked examples (Python/pytest-bdd, .NET/Reqnroll, TypeScript/
      Cucumber.js) showing how each implements the same interface. The
      spec must include contract tests the harness will run against every
      plugin to enforce the migration's failure-pattern guards.
- [ ] AC-006: Migration sequencing plan fits inside the 27-day window with
      ≥5 days of validation margin before 2026-06-15. Each follow-on task
      ≤8h with a written falsifier criterion.
- [ ] AC-007: Decision-point table covers all ≥5 open questions enumerated
      in the research doc plus any new questions surfaced by the trace.
      Each row carries a recommendation + the strongest dissent.
- [ ] AC-008: Cross-repo history synthesis cites ≥15 distinct
      `autobuild-*-history.md` files across forge/jarvis/study-tutor/
      specialist-agent. No pattern is asserted without a citation.
- [ ] AC-009: The report's recommendations explicitly reconcile with
      TASK-REV-ABST's "narrow" mandate (no new gates without removing one)
      and the active gate-stack freeze. Conflicts surfaced, not glossed.
- [ ] AC-010: Falsifier articulated for the review's central
      recommendation. If the recommendation is "proceed with LangGraph/
      DeepAgents migration as scoped", the falsifier must be observable
      within the validation window.

## References

### Primary input
- `docs/research/autobuild-harness-migration.md` (the migration case)

### Prior reviews (synthesise, do not duplicate)
- `tasks/review_complete/TASK-REV-ABST-autobuild-bdd-verification-stocktake.md`
- `tasks/backlog/TASK-REV-STKB-stack-blindness-audit-and-bdd-plugin-architecture.md`
- `.claude/reviews/TASK-REV-ABST-review-report.md`
- `.claude/reviews/TASK-REV-1B452-review-report.md`
- `.claude/reviews/TASK-REV-0414-review-report.md`
- `.claude/reviews/TASK-REV-4D012-*`

### Failure-pattern rules
- `.claude/rules/absence-of-failure-is-not-success.md`
- `.claude/rules/path-string-mismatch-is-not-dishonesty.md`
- `.claude/rules/namespace-hygiene.md`
- `.claude/rules/bdd-per-task-glue.md`
- `.claude/rules/autobuild.md`

### Cross-repo history (cite extensively)
- `~/Projects/appmilla_github/forge/docs/history/autobuild-*.md`
- `~/Projects/appmilla_github/jarvis/docs/history/autobuild-*.md`
- `~/Projects/appmilla_github/study-tutor/docs/history/autobuild-*.md`
- `~/Projects/appmilla_github/specialist-agent/docs/history/autobuild-*.{md,log}`
- Review reports under `study-tutor/.claude/reviews/`, `jarvis/.claude/reviews/`,
  `forge/.claude/reviews/` for the same features.

### Target-stack reference
- `installer/core/templates/langchain-deepagents/`
- `installer/core/templates/langchain-deepagents-orchestrator/`
- `installer/core/templates/langchain-deepagents-weighted-evaluation/`
- specialist-agent's Player-Coach LangGraph implementation
  (`~/Projects/appmilla_github/specialist-agent/`)

### Active constraints
- `.claude/state/gate-freeze-2026-05-17.md` (gate-stack freeze 2026-05-11→17)
- DECISION-DF-001 (no cloud API on critical path)

## Notes for the reviewer

- Phase 2.7 complexity evaluation is pre-set to **9 (Very Complex)**. The
  task is *not* a candidate for splitting because the deliverable is a
  single coherent architectural report and the downstream split happens
  in the implementation-guide step (AC-003 follow-on tasks). If the
  evaluator disagrees, surface the disagreement at the Phase 2.8 human
  checkpoint rather than auto-splitting — the integrity of the C4 trace
  + plugin spec + sequencing plan depends on one author holding the whole
  picture.
- This task is the natural successor to TASK-REV-ABST (which decided
  "narrow") and TASK-REV-STKB (which proposed the plugin architecture).
  The migration changes the harness substrate underneath both. The review
  must answer: *does the substrate change make the narrow-path or the
  plugin-architecture decision easier, harder, or moot?*
- The cross-repo history is the strongest evidence available — it is the
  closest thing to a controlled comparison the fleet has (same Player-
  Coach methodology, different harness substrates). Lean on it heavily.

## Next steps after task creation

1. Review this task scope. If the framing needs adjustment, edit before
   running `/task-review`.
2. When ready: `/task-review TASK-REV-HMIG --mode=architectural --depth=comprehensive`
3. At the checkpoint, choose:
   - **[A]ccept** — file the report, take no further action.
   - **[I]mplement** — spawn follow-on `/feature-plan` from the
     implementation-guide deliverable to execute the migration.
   - **[R]evise** — request deeper analysis on specific decision points.
   - **[C]ancel** — discard the review.

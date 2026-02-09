# GuardKit Evolution: Specification Kickoff Document

> **Purpose**: Roadmap for five focused specification conversations, each producing a feature spec document ready for `/feature-plan` consumption.
>
> **Approach**: Use Claude Desktop with extended thinking for each conversation. Each conversation refines one area, produces one spec document, and keeps scope manageable to avoid compaction.
>
> **Output**: Five spec documents that feed directly into GuardKit's `/feature-plan` command for task decomposition and implementation.

---

## How to Use This Document

For each spec session:

1. **Start a new conversation** in Claude Desktop with extended thinking enabled
2. **Provide context**: Upload this kickoff document + the referenced input files listed for that spec
3. **State the goal**: "I want to refine Spec N and produce a feature spec document for `/feature-plan`"
4. **Work through the key questions** — these are the design decisions that need resolving
5. **Output**: A markdown feature spec following the established format (see Format Reference below)

Work through specs in order — Spec 1 and 3 are prerequisites for the others, but Specs 1 and 3 can be done in parallel.

---

## Spec Overview and Dependency Map

```
Spec 1: /system-plan Command ─────────────┐
                                           ├──→ Spec 2: System Context Read Commands
Spec 3: Critical Graphiti Entities ────────┘
                                           
Spec 4: RequireKit v2 Refinement ──────────→ (independent, but benefits from Spec 3)

Spec 5: BDD Living Documentation Loop ────→ (depends on Spec 3 for Graphiti schema)
```

**Recommended order**: Spec 1 → Spec 3 → Spec 2 → Spec 4 → Spec 5
(or Spec 1 and 3 in parallel, then 2, then 4 and 5)

---

## Spec 1: `/system-plan` Command

> **Phase**: 1 (Highest ROI)
> **Target repo**: GuardKit
> **Estimated spec complexity**: High — most novel command, needs careful design
> **Implementation estimate**: 3-5 days

### Goal

Design the interactive architecture planning command that establishes and maintains system-level context in Graphiti. This is the highest-leverage addition — it's what bridges the gap between requirements (RequireKit) and execution (GuardKit task workflow).

### Scope

- Command definition, arguments, and modes of operation
- Interactive planning flow (what questions does it ask, in what order)
- Graphiti read/write patterns (which group_ids, what episode structure)
- Output artefacts (markdown architecture docs, C4 diagrams, ADRs)
- Integration points with existing commands (how does `/feature-plan` consume its output)
- How it handles first-time setup vs iterative refinement vs review mode

### Key Questions to Resolve

1. **Command structure**: Is it `/system-plan "project name"` or `/system-plan --mode=setup|refine|review`? Or does it infer the mode from whether architecture context already exists in Graphiti?

2. **Interactive flow design**: What's the question sequence for initial setup? The task-review and feature-plan commands have proven interactive patterns — how does system-plan adapt these for architecture-level concerns? Consider:
   - Domain discovery (what does this system do, who are the users)
   - Bounded context identification (what are the major subsystems)
   - Service/module relationships (how do they communicate)
   - Technology decisions (stack, infrastructure, deployment)
   - Cross-cutting concerns (auth, logging, error handling, observability)
   - Constraints and non-functional requirements

3. **ADR integration**: Should `/architecture-decision` be a separate command or a natural output of `/system-plan`? The strategy doc suggests folding it in. If folded in, how does the user trigger an ADR during a planning session?

4. **Graphiti schema**: What exact episode structure for architecture context? The existing `project_architecture` group_id is defined but the episode content needs specifying. How granular should episodes be — one per bounded context, one per service, one per decision?

5. **Output format**: What markdown documents does it produce? Propose:
   - `docs/architecture/system-context.md` — C4 Level 1 diagram as markdown
   - `docs/architecture/bounded-contexts.md` — bounded context map
   - `docs/architecture/decisions/ADR-NNN.md` — individual ADRs
   - Or a single `docs/architecture/SYSTEM.md`?

6. **Feature-plan integration**: How does `/feature-plan` read the architecture context? Does it query Graphiti directly, or does it read the markdown files `/system-plan` produced? (Principle: markdown is authoritative, Graphiti provides queryability — so probably both?)

7. **AutoBuild coach integration**: How does the coach receive system context during player-coach loops? Is it automatically included in the coach prompt, or does complexity scoring gate it?

8. **Complexity gating**: Simple bug fixes shouldn't load full system context. How does the system decide when to include architecture context? The existing complexity scoring may need enhancement.

### Reference Materials to Provide

- This kickoff document
- `guardkit-requirekit-evolution-strategy.md` (the updated strategy)
- `TASK-REV-1505-review-report.md` (the architectural review — particularly Parts 3 and 4)
- `FEATURE-001-enhanced-feature-plan.md` (as format reference for the spec output)
- Existing `/task-review` and `/feature-plan` command files from `.claude/commands/` (to understand the interactive pattern)
- `AutoBuild_Product_Specification.md` (for coach/player context retrieval patterns)

### Spec Output Structure

```markdown
# Feature: /system-plan Command
> Feature ID: FEAT-SP-001
> Priority: P0
> Dependencies: Spec 3 (Graphiti entities)

## Summary
## Current State  
## Command Design
### Arguments and Modes
### Interactive Flow (per mode)
### Graphiti Integration
### Output Artefacts
## Integration Points
### With /feature-plan
### With AutoBuild Coach
### With /system-overview (Spec 2)
## Acceptance Criteria
## Testing Approach
## File Changes
```

---

## Spec 2: System Context Read Commands

> **Phase**: 1
> **Target repo**: GuardKit
> **Estimated spec complexity**: Medium — simpler commands, well-defined patterns
> **Implementation estimate**: 2-3 days
> **Depends on**: Spec 1 (defines what data these commands read), Spec 3 (Graphiti schema)

### Goal

Design the three read-only commands that consume the knowledge `/system-plan` produces: `/system-overview`, `/impact-analysis`, and `/context-switch`.

### Scope

- Command definitions, arguments, and output formats
- Graphiti query patterns for each command
- How they integrate into the task workflow (when are they invoked automatically vs manually)
- `/context-switch` project isolation and orientation display
- How `/impact-analysis` cross-references tasks against BDD scenarios, components, and services

### Key Questions to Resolve

1. **`/system-overview` output**: What does it actually display? A condensed version of the architecture docs? A summary pulled from Graphiti? How detailed vs concise — should it fit in one screen or be multi-page?

2. **`/impact-analysis` depth**: How deep should the analysis go? Just listing affected components, or actually assessing risk? Should it show:
   - Components/services this task touches
   - BDD scenarios that might be affected
   - ADRs that constrain the implementation
   - Related tasks in the same feature (already completed or pending)
   - A risk score?

3. **`/context-switch` state management**: When switching projects, what happens to the current project's state? Is it purely about loading different Graphiti group_ids, or does it also manage git worktrees, active task state, etc.?

4. **Automatic vs manual invocation**: Should `/system-overview` be automatically injected into AutoBuild coach context? Should `/impact-analysis` run automatically before every `/task-work`? Or only for tasks above a complexity threshold?

5. **Graceful degradation**: What happens when these commands are run on a project that hasn't had `/system-plan` run yet? Show a helpful message suggesting system-plan, or return whatever partial context exists?

6. **Token budget**: How much of the context window should these commands consume? TASK-REV-1505 identified context budget management as a moderate concern. Each command should have a target token budget.

### Reference Materials to Provide

- This kickoff document
- `guardkit-requirekit-evolution-strategy.md`
- The completed Spec 1 output (the `/system-plan` spec)
- `TASK-REV-1505-review-report.md` (Part 4: context budget allocation)
- Existing command patterns from `.claude/commands/`

### Spec Output Structure

```markdown
# Feature: System Context Read Commands
> Feature ID: FEAT-SC-001
> Priority: P0
> Dependencies: FEAT-SP-001 (/system-plan), Spec 3 (Graphiti entities)

## Summary
## Commands
### /system-overview
#### Arguments
#### Output Format
#### Graphiti Queries
#### Token Budget
### /impact-analysis
#### Arguments
#### Analysis Depth
#### Output Format
#### Graphiti Queries
#### Token Budget
### /context-switch
#### Arguments
#### State Management
#### Orientation Display
## Automatic Integration
### AutoBuild Coach Context
### Task-work Pre-flight
### Complexity Gating
## Graceful Degradation
## Acceptance Criteria
## Testing Approach
## File Changes
```

---

## Spec 3: Critical Graphiti Entity Additions

> **Phase**: 1
> **Target repo**: GuardKit
> **Estimated spec complexity**: Medium — schema design + seeding changes
> **Implementation estimate**: 2-3 days
> **Depends on**: Nothing (can be done in parallel with Spec 1)

### Goal

Add the four missing entity types identified by TASK-REV-1505 to the Graphiti Refinement roadmap: `role_constraints`, `quality_gate_configs`, `turn_states`, and `implementation_modes`. These plug the gaps that caused the most painful AutoBuild problems.

### Scope

- Entity schemas for each new type
- Seeding strategy (when and how are these entities created/updated)
- Integration with existing FEAT-GR-001 (Project Knowledge Seeding)
- How feature-build reads and enforces role constraints and quality gate configs
- Turn state write/read lifecycle during player-coach loops
- Relationship to existing Graphiti Refinement prerequisites (PRE-000 through PRE-003)

### Key Questions to Resolve

1. **Role constraints scope**: Are role constraints project-specific or global? The player/coach roles don't change per project, but specific constraints might (e.g., PoA project might have additional compliance-related coach responsibilities). Propose: global defaults with per-project overrides.

2. **Quality gate config storage**: Should these live in Graphiti, in project config files (`.guardkit/config/quality-gates.yaml`), or both? Graphiti provides queryability but config files are more transparent and editable. Consider: config files are authoritative (human-editable), Graphiti is populated from them during seeding.

3. **Turn state lifecycle**: When exactly are turn states written and read?
   - Written: At the end of each player-coach turn during feature-build
   - Read: At the start of the next turn, and during state recovery
   - Cleaned up: After feature-build completes successfully? Or retained as historical record?
   - Size concern: Turn states could accumulate. What's the retention policy?

4. **Implementation modes enforcement**: How does the system determine which mode to use? Is it purely advisory (recommended mode displayed to user), or does it gate behaviour (prevents running AutoBuild on a simple bug fix)?

5. **Relationship to existing GR features**: These entities need to be added to FEAT-GR-001 (Project Knowledge Seeding). Does this change the estimate for GR-001? The TASK-REV-1505 review suggested adding these to the seeding phase — confirm this is the right integration point.

6. **Backward compatibility**: Projects that haven't re-seeded their Graphiti after these entities are added should still work. How do we handle missing entity types gracefully?

### Reference Materials to Provide

- This kickoff document
- `guardkit-requirekit-evolution-strategy.md` (Section 5: Critical Graphiti Entity Gaps)
- `TASK-REV-1505-review-report.md` (Parts 4-6: findings and recommendations)
- Existing Graphiti Refinement research docs from `docs/research/graphiti-refinement/`:
  - `FEAT-GR-000-gap-analysis.md`
  - `FEAT-GR-001-project-knowledge-seeding.md`
  - `FEAT-GR-PRE-002-episode-metadata-schema.md`
- Current `guardkit/graphiti/` source code (for existing patterns)

### Spec Output Structure

```markdown
# Feature: Critical Graphiti Entity Additions
> Feature ID: FEAT-GE-001
> Priority: P0
> Dependencies: FEAT-GR-PRE-000 through PRE-003 (Graphiti prerequisites)

## Summary
## Entity Schemas
### role_constraints
#### Schema
#### Default Values
#### Per-project Overrides
### quality_gate_configs
#### Schema
#### Config File Format
#### Graphiti Seeding
### turn_states
#### Schema
#### Write Lifecycle
#### Read Lifecycle
#### Retention Policy
### implementation_modes
#### Schema
#### Mode Selection Logic
## Seeding Integration
### Changes to FEAT-GR-001
### Seeding Commands
## Feature-build Integration
### Coach Receives Role Constraints
### Coach Enforces Quality Gates
### Player-Coach Turn State Tracking
## Backward Compatibility
## Acceptance Criteria
## Testing Approach
## File Changes
```

---

## Spec 4: RequireKit v2 Refinement Commands

> **Phase**: 2
> **Target repo**: RequireKit
> **Estimated spec complexity**: Medium — extends existing patterns
> **Implementation estimate**: 3-5 days
> **Depends on**: Spec 3 (for Graphiti schema), but can be specced independently

### Goal

Add iterative refinement commands to RequireKit (`/epic-refine`, `/feature-refine`) and Graphiti backing for requirements, making RequireKit usable for James as product owner.

### Scope

- Refinement command design (interactive flow, what questions they ask)
- Graphiti integration for epics and features (episode structure, group_ids)
- How refined requirements flow to GuardKit (the RequireKit → Graphiti → GuardKit pipeline)
- UX considerations for James (non-technical product owner workflow)

### Key Questions to Resolve

1. **Refinement interaction model**: What does a `/epic-refine` session actually look like? It should show the current epic state and ask targeted questions. What question categories?
   - Scope clarity (what's in, what's out)
   - Success criteria gaps (how do we know this epic is done)
   - Acceptance criteria specificity (are they testable)
   - Dependency identification (what blocks this, what does this block)
   - Risk assessment (what could go wrong)
   - Constraint capture (regulatory, technical, business)

2. **Graphiti group_id for requirements**: The strategy proposes `group_id: "requirements"`. Should this be more granular — `{project}__epics`, `{project}__features`, `{project}__requirements`? Or one group with entity_type differentiation?

3. **Cross-tool query pattern**: When GuardKit's `/feature-plan` runs, how does it discover RequireKit's Graphiti data? Same Graphiti instance with different group_ids? The strategy says "GuardKit tasks query RequireKit's Graphiti store" — what does this mean technically?

4. **James's UX**: James couldn't distinguish commands from conversation. What guardrails prevent this?
   - Clear command prompt differentiation
   - Explicit "refinement mode" with structured prompts
   - Summary output after each refinement showing what changed
   - Should refinement commands work in Claude Desktop as well as Claude Code?

5. **Markdown-first principle**: Refinement updates the epic/feature markdown file AND pushes to Graphiti. What happens when they drift? Which is authoritative? (Strategy says markdown is authoritative — how do we re-sync Graphiti from markdown?)

6. **RequireKit Graphiti integration**: Does RequireKit need its own Graphiti connection, or does it rely on GuardKit's? If RequireKit is used standalone (without GuardKit), how does Graphiti work?

### Reference Materials to Provide

- This kickoff document
- `guardkit-requirekit-evolution-strategy.md` (Sections 4.2, 6)
- RequireKit source code and existing command files
- Existing epic/feature markdown templates from RequireKit
- `TASK-REV-1505-review-report.md` (for Graphiti group_id reference)

### Spec Output Structure

```markdown
# Feature: RequireKit v2 Refinement Commands
> Feature ID: FEAT-RK-001
> Priority: P1
> Dependencies: Graphiti infrastructure (FEAT-GR prerequisites)

## Summary
## Current State
## New Commands
### /epic-refine
#### Arguments
#### Interactive Flow
#### Question Categories
#### Output (markdown + Graphiti)
### /feature-refine
#### Arguments
#### Interactive Flow
#### Output
## Graphiti Integration
### Episode Schema for Epics
### Episode Schema for Features
### Group ID Strategy
### Cross-tool Query Pattern
## UX Design for Product Owners
### Command Differentiation
### Refinement Mode
### Change Summaries
## Markdown-Graphiti Sync
## Acceptance Criteria
## Testing Approach
## File Changes
```

---

## Spec 5: BDD Living Documentation Loop

> **Phase**: 3
> **Target repo**: Both GuardKit and RequireKit
> **Estimated spec complexity**: Medium — cross-repo integration
> **Implementation estimate**: 2-3 days
> **Depends on**: Spec 3 (Graphiti schema), Spec 4 (RequireKit Graphiti integration)

### Goal

Create the feedback loop where BDD scenarios from RequireKit become queryable living documentation in Graphiti, consumed by GuardKit during task-work and updated on task-complete.

### Scope

- Enhancing RequireKit's `/generate-bdd` to push scenarios to Graphiti
- GuardKit's task-work reading BDD context before implementation
- AutoBuild coach receiving BDD context during validation
- Task-complete updating BDD scenario verification status
- `/feature-status` command showing scenario pass/fail state

### Key Questions to Resolve

1. **BDD episode granularity**: One episode per .feature file, or one per individual scenario? Per-scenario gives better queryability but creates more Graphiti entries. Proposal: one episode per scenario with feature file as metadata.

2. **Scenario verification lifecycle**: When a scenario is "verified" during task-complete, what does that mean technically? Did pytest/behave run and pass? Or is it a declaration by the coach? How do we handle scenarios that can't be automated?

3. **Cross-repo coordination**: The loop spans RequireKit (generate-bdd) and GuardKit (task-work, task-complete). How do they share the Graphiti instance? Same Neo4j database with different group_ids?

4. **Relevance matching**: When task-work queries "which BDD scenarios are relevant to this task?", how does it determine relevance? By feature reference? By keyword matching against the task description? By Graphiti semantic search? This is a retrieval quality question.

5. **Regression detection**: If a task-complete finds that previously-passing BDD scenarios now fail, what happens? Block completion? Warn and continue? This ties into quality gate configuration (Spec 3).

6. **Feature-status display**: What does the `/feature-status` command show? A dashboard of green/red scenarios per feature? Coverage percentage? Last verified date? Should this be a GuardKit command, a RequireKit command, or available in both?

7. **Initial population**: For existing projects with .feature files but no Graphiti BDD episodes, how do we bootstrap? A one-time migration command? Part of `guardkit init`?

### Reference Materials to Provide

- This kickoff document
- `guardkit-requirekit-evolution-strategy.md` (Sections 4.3, feedback loop diagram)
- Completed Specs 3 and 4 (for Graphiti schema and RequireKit integration)
- RequireKit's existing `/generate-bdd` command implementation
- GuardKit's task-work and task-complete command implementations
- `TASK-REV-1505-review-report.md` (Part 3: AutoBuild lessons alignment)

### Spec Output Structure

```markdown
# Feature: BDD Living Documentation Loop
> Feature ID: FEAT-BDD-001
> Priority: P1
> Dependencies: FEAT-GE-001 (Graphiti entities), FEAT-RK-001 (RequireKit Graphiti)

## Summary
## Current State
## The Feedback Loop
### Step 1: /generate-bdd → Graphiti
#### Episode Schema for BDD Scenarios
#### Group ID: bdd_scenarios
### Step 2: task-work Reads BDD Context
#### Relevance Matching Strategy
#### Context Injection Point
### Step 3: AutoBuild Coach BDD Validation
#### Coach Prompt Integration
### Step 4: task-complete Updates Status
#### Verification Criteria
#### Regression Handling
## /feature-status Command
### Output Format
### Cross-repo Availability
## Initial Population / Migration
## Acceptance Criteria
## Testing Approach
## File Changes (GuardKit)
## File Changes (RequireKit)
```

---

## Format Reference

Each spec should follow the established GuardKit feature spec pattern:

```markdown
# Feature: [Title]

> **Feature ID**: FEAT-XXX-NNN
> **Priority**: P0/P1/P2
> **Estimated Effort**: X-Y days
> **Dependencies**: [list]

---

## Summary
[One paragraph describing what this feature does and why]

## Current State
[What exists today, what's missing]

## Required Changes
### [Section per major change]
[Design detail, code examples where helpful, Graphiti schemas]

## Integration Points
[How this connects to other commands/features]

## Acceptance Criteria
- [ ] [Testable criterion]
- [ ] [Testable criterion]

## Testing Approach
### Unit Tests
### Integration Tests

## File Changes
### New Files
### Modified Files

## References
[Links to strategy doc, TASK-REV-1505, etc.]
```

---

## Conversation Management Tips

- **Start each conversation with clear scope**: "We're working on Spec N from the GuardKit Evolution Kickoff. Goal is to produce a feature spec for `/feature-plan`."
- **Upload this kickoff doc plus the referenced materials** — this gives the conversation the full context without needing to re-explain the strategy
- **Use extended thinking for design decisions** — the key questions listed above are the ones that benefit from deeper reasoning
- **Keep specs self-contained** — each spec should be understandable without having read the others (though they can reference them)
- **Target ~200-400 lines per spec** — enough detail for `/feature-plan` to decompose into tasks, not so much that it becomes implementation code
- **If a conversation starts getting long**, produce the spec and stop. Refinement can happen in follow-up conversations or during the actual `/feature-plan` session

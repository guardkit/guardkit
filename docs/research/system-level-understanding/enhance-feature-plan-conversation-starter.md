# Conversation Starter: Enhancing GuardKit `/feature-plan` for Two-Phase AI Workflows

## Instructions for This Session

I'm using Claude Desktop with extended thinking to research and design enhancements to GuardKit's `/feature-plan` command. The output of this session will itself be structured as a feature specification that I'll pass through `/feature-plan` to implement — a deliberate compounding effect where the planning tool improves itself.

Please use extended thinking to deeply reason about each section before responding. I value thorough analysis over quick answers.

---

## Context: The Two-Phase Workflow

I've designed a workflow that splits AI-assisted development into two phases with different compute profiles:

**Phase 1 — Research & Planning (MacBook Pro + Claude Desktop/API)**
- Exploratory research using frontier models with extended thinking
- Architecture decisions, trade-off analysis, deep reasoning
- Produces detailed feature specifications with ADRs (Architecture Decision Records)
- Uses GuardKit `/feature-plan` to structure specs into implementation tasks
- Seeds decisions into Graphiti knowledge graph via `guardkit graphiti add-context`
- Commits plans, specs, and feature branches to the repo

**Phase 2 — Implementation (Dell ProMax GB10 + Local vLLM)**
- GuardKit AutoBuild executes against the detailed specs using local models
- Player-Coach adversarial loop: Player implements (full file access) → Coach validates (read-only, runs tests) → repeat until Coach approves or max turns (5) reached
- Graphiti's job-specific context retrieval provides each task with semantically relevant ADRs, warnings, and patterns — not the entire project history
- `/feature-build FEAT-XXX` runs the full autonomous loop, or `/task-work TASK-XXX` for interactive execution
- Work preserved in `.guardkit/worktrees/FEAT-XXX/` for human review before merge
- No API costs — the local model does mechanical execution, not creative reasoning

**The key insight:** The quality gap between frontier and local models matters far less when the local model is following a detailed, unambiguous specification. Implementation quality is bottlenecked by specification clarity, not model intelligence. Graphiti's context retrieval ensures the Player has exactly the right decisions and patterns available without context window bloat.

---

## Current Understanding of GuardKit's Architecture

Based on my research into GuardKit's documentation, here's what I understand:

### `/feature-plan` → `/feature-build` Pipeline
- `/feature-plan` takes a feature description, creates FEAT-XXX with ordered subtasks
- `/feature-build FEAT-XXX` executes the Player-Coach loop autonomously
- Player: full file system access, implements code, writes tests
- Coach: read-only access, runs test commands, validates against acceptance criteria
- Dialectical loop runs up to 5 turns per task before escalation

### Graphiti Knowledge Graph (replaces CLAUDE.md)
- Temporal knowledge graph built on Neo4j with semantic search
- Stores: ADRs, product knowledge, command workflows, quality gate phases, technology stack, failure patterns, component status, integration points
- **Job-specific context retrieval pipeline:** TaskAnalyzer → DynamicBudgetCalculator → JobContextRetriever → SmartFiltering → PromptInjection
- Dynamic token budgets: ~2000 (simple) to 6000+ (complex) based on task analysis
- Context categories: Feature Context, Similar Outcomes, Relevant Patterns, Architecture Context, Warnings, Domain Knowledge
- AutoBuild-specific categories: Role Constraints, Quality Gate Configs, Turn States, Implementation Modes
- Turn state tracking: Turn 2+ loads previous turn states (what was rejected, Coach feedback) with adjusted allocation

### Seeding Commands
```bash
guardkit graphiti seed                        # One-time system knowledge
guardkit graphiti add-context docs/adr/*.md   # Project ADRs
guardkit graphiti verify --verbose            # Verify seeding
```

---

## What I Need You to Help Me Investigate and Design

1. **Current behaviour audit** — What does `/feature-plan` actually produce? What's the output format? How does AutoBuild's Player-Coach loop consume it? What are the handoff points between planning and execution?

2. **Gap analysis for the two-phase workflow** — Given the architecture above, where does the current pipeline fall short? Specifically:
   - Does `/feature-plan` produce task metadata that Graphiti's job-specific context retrieval can work with (complexity, type, domain tags)?
   - Are decisions encoded as proper ADRs that seed cleanly into Graphiti, or as flat text the Player can't semantically retrieve?
   - Is the task granularity appropriate for single Player-Coach cycles (the Coach should be able to validate within 5 turns)?
   - Are acceptance criteria machine-verifiable (exact test commands for the Coach, not subjective judgements)?
   - Are Player constraints explicit enough to prevent file-scope drift?

3. **Enhancement specification** — Design concrete improvements to `/feature-plan` that optimise it for the two-phase workflow:
   - A `--local-model` or `--implementation-target` flag that adjusts output verbosity, explicitness, and Graphiti context budget recommendations
   - Automatic ADR generation from decision logs in the spec (structured for `guardkit graphiti add-context`)
   - Generating quality gate YAML configs per feature (`.guardkit/quality-gates/FEAT-XXX.yaml`)
   - Explicit file path declarations AND exclusions for every task (Player constraints: "touch these files only")
   - Coach validation commands as structured blocks, not prose
   - Domain tags per task for Graphiti semantic retrieval
   - Dependency ordering that prevents parallel task execution from creating conflicts
   - Turn budget hints (simple tasks: expect 1-2 turns, complex: allow 4-5)

4. **Graphiti integration design** — How should the research template output flow into Graphiti?
   - Which sections map to which Graphiti context categories?
   - Should ADRs be generated as separate files or inline in the feature spec?
   - How should warnings and constraints be structured for high-priority retrieval?
   - What's the right granularity for seeding — one big spec file vs. many small focused documents?
   - How do we handle cross-feature ADRs that apply to multiple features?

5. **Research template integration** — I have a "Research-to-Implementation Handoff Template" (structure below) that I use for Phase 1 output. How should `/feature-plan` consume this format? Should it be a recognised input schema?

---

## Research Template Structure (for reference)

The template I use for Phase 1 research output contains these sections:

1. **Problem Statement** — 2-3 sentences grounding the "why"
2. **Decision Log** — Table of decisions with rationale, rejected alternatives, and ADR status
3. **Architecture** — System context diagram, component design, data flow, message schemas
4. **API Contracts** — Request/response shapes, error codes, edge cases
5. **Implementation Tasks** — Ordered, atomic tasks with file paths, domain tags, complexity, Player constraints, Coach validation commands, and machine-verifiable acceptance criteria
6. **Test Strategy** — Unit, integration, and manual verification specs
7. **Dependencies & Setup** — Exact packages, versions, system requirements
8. **File Tree (Target State)** — What the directory looks like when done
9. **Out of Scope** — Explicit exclusions to prevent scope creep
10. **Open Questions (Resolved)** — Research questions with their resolutions
11. **Graphiti ADR Seeding** — ADR file formats, seeding commands, context category mapping, quality gate configuration, and Phase 2 execution workflow

---

## Questions to Explore

Using extended thinking, please reason through:

### On the `/feature-plan` → AutoBuild pipeline:
- What is the optimal output format for a plan consumed by a Player-Coach loop where the Player is a 30B local model?
- Should `/feature-plan` produce different output depending on the target implementation model's capability level?
- How should it handle the distinction between "decisions already made" (seeded as ADRs in Graphiti) and "decisions to make during implementation" (left to the Player within constraints)?
- What task metadata should `/feature-plan` generate to maximise Graphiti's context retrieval effectiveness?
- How should Player constraints and Coach validation commands be structured for machine parsing?

### On task granularity and the Player-Coach cycle:
- What's the right size for a task that a Player completes within the 5-turn Coach validation budget?
- Should tasks be defined by time, by file count, by complexity, or by logical unit?
- How should tasks handle cross-file changes that need to be atomic?
- When should a task be split into sub-tasks vs. handled as a single complex task with higher turn budget?

### On Graphiti context retrieval:
- How do we ensure critical ADRs are always retrieved for relevant tasks (explicit cross-references vs. purely semantic)?
- What's the optimal domain tag taxonomy for a distributed systems project like Ship's Computer?
- How should turn states (Coach rejections, feedback) be weighted against initial context on subsequent turns?
- What happens when the Graphiti token budget is exhausted but critical context remains? How should overflow be handled?

### On the compounding effect:
- This enhancement to `/feature-plan` will itself be implemented via the two-phase workflow. What aspects of the specification need to be extra explicit to avoid circular dependency issues?
- How can we validate that the enhanced `/feature-plan` produces better plans than the original? What would an A/B test look like?

---

## Desired Output

By the end of this session, I want:

1. **A feature specification** for `/feature-plan` enhancements, structured using the Research-to-Implementation Handoff Template above — complete with Decision Log, ADR files, Graphiti seeding commands, task domain tags, Player constraints, and Coach validation commands — so it's ready to be fed back through the (enhanced) workflow

2. **A clear set of implementation tasks** with full AutoBuild metadata (complexity, type, domain tags, file constraints, validation commands) that I can commit to my repo and execute via `/feature-build` on the Dell ProMax with a local model

3. **A Graphiti seeding strategy** for this feature — which ADRs to create, which context categories to populate, what warnings to seed, and the exact `guardkit graphiti add-context` commands to run before Phase 2

4. **Quality gate configuration** — a `.guardkit/quality-gates/FEAT-XXX.yaml` file tuned for this feature's test strategy

---

## My Setup (for reference)

- **MacBook Pro M2 Max, 96GB** — Claude Desktop, Claude Code, VS Code, development machine
- **Dell ProMax GB10, 128GB unified memory** — vLLM serving local models (native Anthropic Messages API), GuardKit AutoBuild execution
- **Synology DS918+ NAS** — Data storage, model cache
- **Ship's Computer** — Distributed agent orchestration system using NATS messaging
- **GuardKit** — Claude Code enhancement toolkit with AutoBuild Player-Coach workflow, Graphiti knowledge graph integration
- **Graphiti + Neo4j** — Temporal knowledge graph for persistent project context (semantic search, dynamic token budgets)
- **Models available locally:** Qwen3-Coder-30B-A3B, nvidia/Qwen3-32B-FP4, Nemotron-3-Nano-30B

---

## Let's Begin

Please start by reasoning deeply (using extended thinking) about the current state of agentic coding tool planning commands — what works, what doesn't, and what the ideal `/feature-plan` output looks like when:

1. The implementation target is a capable but not frontier local model
2. Context is provided via semantic knowledge graph retrieval (Graphiti), not a static CLAUDE.md file
3. Execution follows an adversarial Player-Coach pattern with turn budgets
4. Every decision that requires intelligence has already been made in Phase 1

Then we'll work through the enhancement specification section by section.

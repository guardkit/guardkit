# Conversation Starter: `/feature-spec` Command — BDD Specification Generator for GuardKit (v2)

## Context for This Session

This document captures decisions from a research session (21 Feb 2026) where we rethought the RequireKit → GuardKit workflow. **RequireKit is being retired.** Its structured elicitation approach doesn't match how the product owner (James) works, and Rich doesn't need it either. What's needed is a fast path from loose feature descriptions to machine-verifiable specifications.

The solution: a `/feature-spec` command in GuardKit that takes vague requirements and generates comprehensive BDD Gherkin feature files using a **Propose-Review** methodology (Specification by Example).

## Three Core Design Principles

### 1. Technology-Stack Agnostic

Gherkin is the universal specification format. It works for any language. The `.feature` file is always generated. Stack-specific test scaffolding (step definitions, runner config, fixtures) is a pluggable convenience layer that auto-detects the target project's stack from codebase signals (pyproject.toml → Python/pytest-bdd, package.json → TypeScript/cucumber-js, go.mod → Go/godog). When no stack is detected, Gherkin-only output is produced.

Gherkin scenarios use **domain language** ("the upload should succeed") not implementation language ("return 201"). This keeps specs valid regardless of whether the implementation is REST, GraphQL, gRPC, CLI, or message queue.

### 2. Propose-Review Methodology (Not Elicitation)

RequireKit failed because it interrogated the product owner. `/feature-spec` inverts this using Specification by Example (Gojko Adžić):

**The AI proposes concrete behavioural examples. The human curates.**

The 6-phase cycle:
1. **Context Gathering** — AI reads codebase, Graphiti ADRs, existing features (no human interaction)
2. **Initial Proposal** — AI generates a COMPLETE Gherkin scenario set, organised by category:
   - Key Examples (core happy path)
   - Boundary Examples (0, 1, max, max+1, empty, null)
   - Negative Examples (invalid input, unauthorised, unsupported)
   - Illustrative Examples (edge cases, concurrency, failure recovery)
3. **Human Curation** — Accept ✓ / Reject ✗ / Modify ✎ / Add + / Defer ? per scenario group
4. **Edge Case Expansion** — AI generates additional scenarios human didn't consider (security, race conditions, data integrity)
5. **Assumption Resolution** — AI proposes sensible defaults for deferred items with reasoning; human accepts or overrides
6. **Output Generation** — `.feature` + `_assumptions.yaml` + `_summary.md` + stack-specific scaffolding

Key difference from RequireKit: curation is lower-friction than authoring. Human's fastest path is "accept all, modify a few" — takes 5-10 minutes vs 30-60 minutes of Q&A.

### 3. Structured Uncertainty Integration (Defence-in-Depth)

`/feature-spec` is Layer 1 in a 4-layer defence against silent assumptions:

| Layer | When | What | Tool |
|-------|------|------|------|
| 1. /feature-spec | Specification time | Generates comprehensive Gherkin, captures assumptions in manifest | Propose-Review cycle |
| 2. Mandatory Assumptions Document | AutoBuild execution | Player declares implementation-level assumptions before coding | Structured YAML output |
| 3. Coach Ambiguity Detection | AutoBuild validation | Coach detects divergence from Gherkin + assumptions | External detection patterns |
| 4. Graphiti Coverage Gating | Before execution | Low knowledge-graph coverage → pause | Context coverage thresholds |

The Assumptions Manifest (`_assumptions.yaml`) generated alongside Gherkin feeds into AutoBuild's gating:
- High confidence → auto-proceed
- Medium confidence → Coach reviews
- Low confidence → mandatory human review

This connects directly to the Structured Uncertainty Handling architecture (see `structured-uncertainty-handling.md`).

## Key Decisions Already Made

| # | Decision | Key Rationale |
|---|----------|--------------|
| D1 | Gherkin format | Universal, readable, executable, massive LLM training data |
| D2 | GuardKit slash command | Claude Code reads actual codebase for concrete scenarios |
| D3 | Stack detection + pluggable scaffolding | Gherkin universal, test scaffolding adapts per language |
| D4 | Generate .feature + scaffolding + assumptions + summary | Complete output set for the pipeline |
| D5 | Accept any unstructured input | Bridges from loose ideas to precise specs |
| D6 | Propose-Review methodology | AI generates, human curates (inverse of RequireKit) |
| D7 | Feature summary for /feature-plan | Auto-generated from Gherkin, not separate authoring |
| D8 | Markdown command + Python module | Prompt methodology IS the product |
| D9 | Structured Assumptions Manifest | Every assumption explicit with confidence levels |
| D10 | Domain language in Gherkin | "Upload should succeed" not "return 201" |

## The Pipeline

```
Loose idea (from anywhere)
    → /feature-spec (propose-review cycle generates Gherkin + assumptions)
    → Rich reviews (~5-10 mins, curating not authoring)
    → /feature-plan --from-spec (decomposes into AutoBuild tasks)
    → /feature-build FEAT-XXX (Player implements, Coach validates against Gherkin)
    → PR review and merge
```

## Feature Specification

The complete v2 specification is in:
`FEATURE-SPEC-feature-spec-command-v2.md`

6 implementation tasks: Gherkin formatter → Stack detector + scaffolding → Assumptions + summary → Slash command methodology → Orchestration → Integration tests + docs.

## What Needs Attention in This Session

### 1. Slash Command Methodology (Task 4)

This is the most important deliverable. The `.guardkit/commands/feature-spec.md` file encodes the entire propose-review methodology. Areas to explore:
- How exactly should the AI present grouped scenarios for batch review?
- What makes a good vs bad boundary example? Systematic rules the prompt can follow?
- How much edge case expansion is too much? When does it become noise?
- Should the methodology explicitly reference the Specification by Example categories by name?

### 2. `/feature-plan` Integration

The spec generates a `_summary.md` that `/feature-plan` consumes via `--from-spec`. Questions:
- Does this flag exist? If not, what changes does `/feature-plan` need?
- How should `/feature-plan` map Gherkin scenarios to task acceptance criteria?
- Should low-confidence assumptions from the manifest affect task complexity scoring?

### 3. Real-World Validation

Run `/feature-spec` (even as manual simulation) against actual features:
- A Python GuardKit feature (internal tooling)
- A TypeScript client-facing API feature
- A Go microservice feature
- A GCSE tutor feature (educational, less technical)

This validates: (a) domain-language Gherkin is specific enough, (b) stack detection works, (c) propose-review cycle is natural, (d) assumptions are genuinely useful not just noise.

### 4. AutoBuild Integration

How does the Coach actually use Gherkin during validation?
- Coach runs: `pytest tests/features/{name}_steps.py -v` (Python)
- Coach runs: `npx cucumber-js features/{name}.feature` (TypeScript)
- Coach runs: `go test -v ./features/...` (Go)
- What about the assumptions manifest? Does the Coach parse it or just the Gherkin?

### 5. Template Quality

The scaffolding templates for each language need to be good enough that the Player can implement step bodies without restructuring. Worth getting real developers to review the Python, TypeScript, and Go templates.

## Setup Context

- **MacBook Pro M2 Max, 96GB** — Claude Desktop and Claude Code
- **Dell ProMax GB10, 128GB** — vLLM, GuardKit AutoBuild execution
- **GuardKit** — AutoBuild Player-Coach workflow, Graphiti knowledge graph, slash commands
- **Graphiti + Neo4j** — Temporal knowledge graph for context retrieval
- **Models locally:** Qwen3-Coder-30B-A3B, nvidia/Qwen3-32B-FP4

## Background Documents

- `FEATURE-SPEC-feature-spec-command-v2.md` — The full feature specification (this session's primary input)
- `structured-uncertainty-handling.md` — Defence-in-depth architecture for assumption management
- `research-to-implementation-template.md` — The template format for feature specs
- `dev-pipeline-system-spec.md` — The NATS-based pipeline architecture
- `james-feedback-analysis-v2.md` — Why RequireKit's structured elicitation didn't work

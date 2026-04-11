---
id: TASK-REV-C7B9
title: Design review — should dotnet-railway-fastendpoints be split into minimal and full variants
status: backlog
created: 2026-04-11T12:00:00Z
updated: 2026-04-11T12:00:00Z
priority: low
tags: [template, dotnet, design, review, architecture]
task_type: review
review_mode: decision
review_depth: standard
parent_review: TASK-REV-D0C1
complexity: 5
depends_on: [TASK-DRF-003]
---

# Task: Design review — should dotnet-railway-fastendpoints be split into minimal and full variants

## Description

The `dotnet-railway-fastendpoints` template is rated **complexity 10/10** — the highest of any GuardKit builtin. It bundles a large stack: ASP.NET Core 10.0, FastEndpoints, Railway-Oriented Programming, Dapper+PostgreSQL, NATS Fleet integration, Keycloak auth/observability, xUnit+Testcontainers, modular monolith with bounded-context isolation, 7 specialist agents.

This decision point was raised in the TASK-REV-D0C1 review (Decision Point 4) and deferred — the review recommended keeping it as a single template for initial registration, and evaluating a split later based on user feedback.

This task is the follow-up design review to make that call.

## Decision to Make

**Should `dotnet-railway-fastendpoints` be split into two or more variants?**

Candidate shapes:

| Variant | Scope | Target user |
|---------|-------|-------------|
| **dotnet-minimal** | ASP.NET Core + FastEndpoints + Railway-Oriented Programming + xUnit. **No** NATS, Keycloak, Dapper, Fleet. | Someone starting a small C# API without infrastructure commitments |
| **dotnet-railway-fastendpoints** (current) | Everything | Someone building a production monolith with the full stack |
| **dotnet-full-stack** (rename?) | Same as current, renamed for clarity | — |

Or: keep as single template and document how to strip layers.

## Scope

### 1. User Feedback / Signal Gathering

- [ ] **Check for user feedback** — has anyone actually used the template since it was registered (TASK-DRF-003)? Any issues filed, Graphiti knowledge entries, or Conductor traces?
- [ ] **Complexity barrier evidence** — is there evidence that the 10/10 complexity is blocking adoption, or is it aspirational for power users who actively wanted the full stack?
- [ ] **Compare to langchain-deepagents precedent** — that template was split into 3 variants (base, orchestrator, weighted-evaluation). What triggered those splits? Was it pre-planned or in response to user needs?

### 2. Technical Feasibility

- [ ] **Analyze layer coupling** — can NATS Fleet, Keycloak, and Dapper actually be cleanly removed without breaking the Railway-Oriented Programming core?
  - `Program.cs.template` already wires Fleet via `builder.Services.AddFleetIntegration(...)` — easy to delete
  - Keycloak auth is a middleware registration — easy to delete
  - Dapper+PostgreSQL repositories would need replacing (e.g. in-memory) for a minimal variant
- [ ] **Identify shared vs divergent files** — which of the 20 scaffold templates belong to a minimal variant vs full variant?
- [ ] **Agent overlap** — of the 7 agents, which are minimal-relevant vs full-stack-only?
  - Minimal-relevant: `railway-result-pipeline-specialist`, `fastendpoints-endpoint-specialist`, `bounded-context-domain-specialist`, `xunit-testcontainers-testing-specialist` (4)
  - Full-stack-only: `dapper-postgresql-repository-specialist`, `nats-fleet-integration-specialist`, `keycloak-auth-observability-specialist` (3)

### 3. Maintenance Cost

- [ ] **Quantify the maintenance burden** of a split — shared code between two variants must be kept in sync. GuardKit does not currently have a template composition / inheritance mechanism (verified in review).
- [ ] **Evaluate alternatives to a hard split**:
  - **Post-generation stripping**: document a `guardkit init dotnet-railway-fastendpoints --exclude=nats,keycloak` flag (requires init.py work)
  - **Template Q&A with layer toggles**: use `/template-qa` to let users toggle layers during scaffolding
  - **Single template + clear CLAUDE.md section**: document "How to strip Fleet/NATS/Keycloak" in the template's `.claude/CLAUDE.md` so users can remove layers themselves

### 4. Recommendation

Generate a decision with one of:
- **SPLIT** into `dotnet-minimal` + `dotnet-railway-fastendpoints`, with a migration plan
- **RENAME** current to something more specific (e.g. `dotnet-railway-full`) to signal it's opinionated, and defer the minimal variant indefinitely
- **KEEP AS-IS** + add a "How to strip layers" section to CLAUDE.md
- **ADD LAYER TOGGLES** via Q&A or flags instead of splitting

## Acceptance Criteria

- [ ] Review report generated at `.claude/reviews/TASK-REV-C7B9-review-report.md`
- [ ] Each of the 4 decision options (SPLIT / RENAME / KEEP AS-IS / ADD TOGGLES) evaluated with effort, risk, user impact
- [ ] Clear recommendation with rationale
- [ ] If recommendation is SPLIT or ADD TOGGLES, include an implementation sketch with file-level changes
- [ ] User feedback / signal evidence captured (or "no signal yet" documented explicitly)

## Notes

- **Why depends on TASK-DRF-003**: this review makes more sense once the template is actually registered and has been available for some time. Running it before registration would be premature — there would be zero usage signal.
- **Low priority**: don't block feature work on this. Revisit after the dotnet template has been registered for a few weeks and any user feedback has accumulated.
- **Precedent**: langchain-deepagents was split into 3 variants (base / orchestrator / weighted-evaluation). Use that split's rationale as a reference when analyzing this one.

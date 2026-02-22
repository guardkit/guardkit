# GuardKit Architecture

> **Methodology**: Modular
> **Last Updated**: 2026-02-22
> **Source**: `guardkit-system-spec.md`

## Overview

GuardKit is an AI-assisted software development tool with quality gates that prevents broken code from reaching production. It is a CLI tool installed via pip with optional Docker services (FalkorDB for knowledge graph, Graphiti for temporal knowledge).

## Architecture Documents

| Document | Contents |
|----------|----------|
| [System Context](system-context.md) | Actors, external systems, system boundary |
| [Components](components.md) | 9 components, communication patterns, data flows |
| [Cross-Cutting Concerns](crosscutting-concerns.md) | 7 shared concerns (error handling, thread safety, logging, etc.) |
| [Quality Gate Pipeline](quality-gate-pipeline.md) | 10-phase validation pipeline, adversarial intensity gradient |
| [Failure Patterns](failure-patterns.md) | 6 documented failure patterns with prevention strategies |
| [System Spec](guardkit-system-spec.md) | Authoritative source spec (input for /system-plan) |

## Architecture Decisions

| ADR | Title | Status |
|-----|-------|--------|
| [ADR-SP-001](decisions/ADR-SP-001-falkordb-over-neo4j.md) | FalkorDB over Neo4j for Knowledge Graph | Accepted |
| [ADR-SP-002](decisions/ADR-SP-002-client-level-metadata-injection.md) | Client-Level Metadata Injection | Accepted |
| [ADR-SP-003](decisions/ADR-SP-003-adversarial-cooperation.md) | Adversarial Cooperation over Single-Agent | Accepted |
| [ADR-SP-004](decisions/ADR-SP-004-progressive-disclosure.md) | Progressive Disclosure for Token Optimization | Accepted |
| [ADR-SP-005](decisions/ADR-SP-005-ai-first-agent-enhancement.md) | AI-First Agent Enhancement with Static Fallback | Accepted |
| [ADR-SP-006](decisions/ADR-SP-006-adaptive-ceremony.md) | Adaptive Ceremony via Complexity Scoring | Accepted |
| [ADR-SP-007](decisions/ADR-SP-007-markdown-authoritative.md) | Markdown Authoritative, Graphiti Queryable | Accepted |
| [ADR-SP-008](decisions/ADR-SP-008-hash-based-task-ids.md) | Hash-Based Task IDs | Accepted |
| [ADR-SP-009](decisions/ADR-SP-009-honeycomb-testing-model.md) | Honeycomb Testing Model for Seam-First Testing | Accepted |
| [ADR-FS-001](decisions/ADR-FS-001-gherkin-specification-format.md) | Gherkin as Specification Format for AutoBuild | Accepted |
| [ADR-FS-002](decisions/ADR-FS-002-stack-agnostic-scaffolding.md) | Stack-Agnostic Scaffolding with Pluggable Language Support | Accepted |
| [ADR-FS-003](decisions/ADR-FS-003-propose-review-methodology.md) | Propose-Review Specification Methodology | Accepted |

## Component Diagram

```mermaid
graph LR
    CLI[CLI Layer] --> FS[/feature-spec]
    CLI[CLI Layer] --> PE[Planning Engine]
    CLI --> AB[AutoBuild]
    CLI --> TM[Task Management]
    CLI --> TS[Template System]

    FS -->|.feature + summary| PE
    FS -->|seeds scenarios| KL[Knowledge Layer]

    PE --> KL
    PE --> QG[Quality Gates]

    AB --> AI[Agent Invoker]
    AB --> QG
    AB --> KL
    AB --> TM

    FO[Feature Orchestrator] --> AB
    FO --> TM

    AI --> CC[Claude Code Subagents]
    KL --> FDB[(FalkorDB)]

    style FS fill:#ff9,stroke:#333
```

## Key Principles

1. **Quality First** - Never compromise on test coverage or architecture
2. **Pragmatic Approach** - Right amount of process for task complexity
3. **AI/Human Collaboration** - AI does heavy lifting, humans make decisions
4. **Zero Ceremony** - No unnecessary documentation or process
5. **Fail Fast** - Block bad code early, don't let it reach production

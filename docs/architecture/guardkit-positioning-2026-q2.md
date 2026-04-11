# GuardKit Positioning: Q2 2026

**Date:** 2026-04-11
**Author:** Rich
**Status:** Active — seeds into Graphiti as authoritative positioning
**Supersedes:** All prior references to "lightweight task workflow system"

---

## 1. What GuardKit Was (Q4 2025 – Q1 2026)

GuardKit started as a lightweight, pragmatic task workflow system with built-in quality gates. The original positioning — reflected in CLAUDE.md, system-context.md, and Graphiti context — emphasised:

- Simple workflow: Create → Work → Complete
- Quality gates (Phase 2.5 + 4.5) to catch broken code before production
- Zero ceremony — minimal process overhead
- AI/human collaboration with AI doing heavy lifting

This was accurate at the time. GuardKit solved a real problem: giving Claude Code a structured loop (Player-Coach) with quality checkpoints, so that AI-generated code met production standards.

## 2. What Changed (Q1 – Q2 2026)

Three developments shifted GuardKit's scope beyond a task workflow system:

**a) The full pipeline crystallised.** GuardKit is no longer standalone. It sits at the heart of a multi-agent pipeline: Ideation Agent → Product Owner Agent → Architect Agent → **GuardKit Factory** → deployed software. The upstream agents produce structured specifications; GuardKit consumes them and builds software. This is not a task system — it is the build stage of a software factory.

**b) `/template-create` and the template ecosystem matured.** GuardKit now ships 10+ builtin templates across Python, TypeScript, Go, .NET, and React. Each template contains two layers:
- **Config layer** — agents, rules, CLAUDE.md, manifest (consumed by `guardkit init`)
- **Pattern layer** — parameterised `.template` scaffold files that encode stack-specific code patterns (produced by `/template-create`, currently unconsumed at build time)

The pattern layer represents codified architectural knowledge: how a FastAPI router should look, how a NATS handler delegates to a service, how a .NET endpoint follows Railway Oriented Programming. This is the factory's instruction set.

**c) The dev-pipeline architecture was designed.** The NATS-based `dev-pipeline` introduces a Build Agent that receives `ready-for-dev` events, clones repos, runs AutoBuild, and publishes results. GuardKit's AutoBuild is the execution engine inside this autonomous build loop. A task workflow system doesn't have a build agent — a factory does.

## 3. What GuardKit Is Now

**GuardKit is an AI software factory with adversarial quality gates.**

It combines:
1. **Structured specification consumption** — `/feature-spec` (Gherkin + assumptions), `/feature-plan` (task decomposition), `/system-arch` and `/system-design` (architecture)
2. **Template-driven code generation** — stack-specific code patterns that teach the Player how to build features in a given architecture
3. **Adversarial build loop** — Player-Coach AutoBuild with configurable intensity, structured uncertainty handling, and machine-verifiable acceptance criteria
4. **Temporal knowledge graph** — Graphiti stores ADRs, patterns, warnings, and build history; semantic retrieval gives each build turn only the context it needs
5. **Quality gates at every stage** — Phase 2.5 (design review), Phase 4.5 (pre-merge validation), Coach criteria verification, assumption gating

The task workflow (create/work/complete) remains as the unit of work inside the factory. But the system's purpose is not task management — it is **turning specifications into production-quality software with AI, faster and more reliably than unstructured AI coding**.

## 4. Positioning Statement

> GuardKit is an AI software factory that turns structured specifications into production-quality code through adversarial Player-Coach automation, template-driven stack patterns, and defence-in-depth quality gates — replacing ad-hoc AI-assisted development with a repeatable, auditable build pipeline.

## 5. The Five Differentiators

These five elements, combined, distinguish GuardKit from every public analogue (validated in DDD Southwest talk research, April 2026):

1. **Adversarial Player-Coach** — separate AI roles for generation and validation, using different model families, with structured feedback loops
2. **Template-driven patterns** — codified architectural knowledge that teaches the AI how to build in a specific stack, not just what to build
3. **Structured uncertainty handling** — four-layer assumption defence (feature-spec → mandatory assumptions document → Coach detection → Graphiti coverage gating) that catches autonomy bias before it reaches production
4. **Temporal knowledge graph** — Graphiti accumulates architectural context across builds; each new feature benefits from decisions made in previous ones
5. **Full pipeline integration** — GuardKit is not standalone; it is the build stage in an end-to-end pipeline from ideation to deployment

## 6. What This Means for CLAUDE.md and Graphiti

### CLAUDE.md Update Required

The opening line of CLAUDE.md currently reads:
> "A lightweight, pragmatic task workflow system with built-in quality gates that prevents broken code from reaching production."

This should be updated to:
> "An AI software factory with adversarial quality gates that turns structured specifications into production-quality code through template-driven Player-Coach automation."

The core principles remain valid. The commands remain the same. What changes is the framing: GuardKit is not trying to be lightweight — it is trying to be comprehensive, reliable, and autonomous.

### Graphiti Seeding

This document should be seeded into Graphiti so that all future builds, reviews, and planning sessions operate from the updated positioning:

```bash
guardkit graphiti add-context docs/architecture/guardkit-positioning-2026-q2.md
guardkit graphiti verify --verbose
```

### Deprecation of Prior Positioning

Any Graphiti nodes containing the phrase "lightweight, pragmatic task workflow system" should be understood as historical. This document is the authoritative positioning as of April 2026.

## 7. Implications for Open Work

| Area | Implication |
|------|-------------|
| **Template scaffold files** | Not dead weight or reference material — they are build-time patterns. A new feature (FEAT-TPL-PLAYER) should wire them into AutoBuild Player context. |
| **`guardkit init`** | Remains config-layer only. Correct decision. Init sets up the workspace; the factory uses patterns at build time. |
| **DDD Southwest talk** | "2026: The Year of the Software Factory" — positioning aligns directly. GuardKit IS the factory. |
| **Architect Agent** | Produces `/system-arch` output that GuardKit consumes. The Architect is upstream; GuardKit is downstream. The factory metaphor holds. |
| **dev-pipeline** | The Build Agent is the factory floor supervisor. It dispatches work to GuardKit's AutoBuild. NATS is the conveyor belt. |

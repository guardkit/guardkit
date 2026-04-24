# ADR-FLEET-002: Selective Retrieval Over Always-On RAG

## Status

Accepted

## Date

2026-04-24

## Context

Empirical testing of the fine-tuned `gcse-tutor-gemma4-moe` model (23 April 2026) revealed that always-on RAG retrieval against a partial corpus **actively degrades** model quality below the no-retrieval baseline. The mechanism: any instruction that says "ground your response in the retrieved context" implicitly tells the model to suppress knowledge that isn't in the retrieved context. When the corpus is incomplete — which is the common case — that suppression destroys value the model would otherwise contribute.

This finding generalises beyond the study tutor. Any agent in the fleet that retrieves context from Graphiti, ChromaDB, or injected documents is subject to the same degradation pattern when corpus coverage is partial.

### Observed failure modes

1. **Study Tutor (OpenWebUI + RAG):** Quote-discipline rule ("only quote verbatim lines from the attached documents") suppressed the model's own memorised Shakespeare when the corpus contained only secondary study-guide material. Direct Ollama (no RAG) produced verbatim canonical quotes, correct AO framing, and unprompted analytical insights. The same model through OpenWebUI with RAG lost all of these.

2. **Specialist-Agent Architect Role (projected):** Product documentation is always-injected into the Player prompt. The player prompt contains "Only include components, actors, and integrations that are evidenced in the product documentation." Combined with the Coach's PHANTOM detection pattern (critical severity, -0.10 penalty), this creates a product-docs-as-ceiling effect that suppresses legitimate architectural concerns the model would otherwise raise (authentication, observability, rate limiting) when product docs are silent on these topics.

3. **Forge / AutoBuild (projected):** Player and Coach share the same Graphiti retrieval source. When coverage is partial, both are degraded simultaneously — the Coach cannot act as a safety net for retrieval gaps it shares.

### Root cause

The root cause is a conflation of two distinct instructions:

- **"Use retrieved context as evidence"** (additive — correct)
- **"Only use retrieved context"** (ceiling — harmful when corpus is incomplete)

The first is a grounding instruction. The second is a suppression instruction. Most RAG integration patterns (OpenWebUI's default template, "ground your answer in the retrieved documents", PHANTOM detection) conflate these two into a single directive.

## Decision

**Retrieval is additive evidence, not a knowledge ceiling.** Always-on retrieval against a partial corpus degrades quality below the no-retrieval baseline. Agents must evaluate corpus coverage before deciding to retrieve, and must treat below-threshold coverage as a signal to rely on model knowledge with explicit epistemic flagging — not as a signal to retrieve harder.

### Implementation rules

1. **Pre-retrieval coverage check.** Before injecting retrieved context, the agent (or its orchestration layer) must assess whether the corpus has meaningful coverage for the query domain. Below-threshold coverage → skip retrieval, answer from model knowledge, flag epistemic status.

2. **Source-type labelling.** Retrieved content must carry a source-type label: `primary` (authoritative specification, ADR, primary text) vs `secondary` (discussion, study guide, meeting notes). Instructions that constrain model behaviour ("only quote from context") should apply only to primary sources.

3. **No shared-corpus blind spots.** When Player and Coach both retrieve from the same source (Graphiti, ChromaDB), partial coverage degrades both simultaneously. The Coach must have an independent quality signal for detecting retrieval-gap-driven quality loss — it cannot rely solely on corpus-grounded evaluation when the corpus is the problem.

4. **Retrieval-bypass categories.** Some knowledge categories are inherently training-data-first, not retrieval-first. For the study tutor, AO3 (historical/social context) almost never appears in a set-text corpus. For the architect, cross-cutting concerns (security, observability, operability) rarely appear in product docs. These categories must be explicitly exempted from retrieval-ceiling rules.

5. **"Evidence, not a ceiling" language.** Prompt templates must use additive language ("use the following context as supporting evidence") not ceiling language ("only include information from the following context"). The distinction is load-bearing.

## Consequences

### Positive

- Preserves model knowledge value when corpus is incomplete (the common case)
- Prevents silent quality degradation that is hard to diagnose (the model produces plausible but inferior output)
- Enables split-persona patterns (e.g., study tutor's Shakespeare-only vs Modern-texts-only personas)
- Aligns with the existing structured-uncertainty-handling design (Graphiti-Gated Execution, context coverage thresholds)

### Negative

- Adds complexity to retrieval orchestration (coverage-check step before retrieval)
- Source-type labelling requires metadata on corpus entries (ingestion pipeline change)
- "Flag epistemic status" adds visible uncertainty markers to agent output, which may reduce user confidence even when the output is correct

## Applies to

- **study-tutor**: Direct empirical validation. Persona-split already implemented as interim fix. Phase A verifier (FEAT-PO-006) must implement source-type labelling (R1) and dynamic retrieval decision (R2).
- **specialist-agent (architect role)**: Audit player.md for ceiling language in scope-constraint and domain-fidelity rules. Consider adding an ARCHITECTURAL_CONCERN_SUPPRESSED detection pattern to the Coach that fires when the model omits cross-cutting concerns the product docs are silent on. Open Questions section is the existing escape valve — verify the Coach does not penalise its use.
- **specialist-agent (product-owner role)**: Product docs are always-injected in all modes. Same ceiling risk applies when docs are early-stage or incomplete. The existing MISSING_COVERAGE Coach detection partially addresses this but is oriented toward "did the output cover the docs" not "did the docs suppress knowledge the model should contribute."
- **forge**: Confidence-gated checkpoints should distinguish "insufficient context to proceed" (pause) from "partial context is actively misleading" (skip retrieval, proceed on model knowledge, flag). Player-Coach shared-corpus blind spot applies directly.
- **jarvis**: Low impact at v1 (intent routing, no deep knowledge grounding). Note for v1.5+: if RAG is added to dispatch logic, this ADR applies.

## References

- `study-tutor/docs/research/ideas/openwebui-rag-empirical-findings-2026-04-23.md` — primary empirical evidence
- `study-tutor/docs/research/ideas/rag-grounding-design.md` — Phase A MVP design (predecessor)
- `study-tutor/docs/research/ideas/cross-repo-rag-impact-analysis-2026-04-24.md` — expanded cross-repo analysis
- `structured-uncertainty-handling.md` §3.4 — Graphiti-Gated Execution (context coverage thresholds)
- ADR-ARCH-009 — 70/30 split principle (related: what belongs in prompts vs code)

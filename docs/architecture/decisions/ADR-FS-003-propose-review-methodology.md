# ADR-FS-003: Propose-Review Specification Methodology

- **Date**: 2026-02
- **Status**: Accepted

## Context

RequireKit's elicitation-based approach failed because it required the product owner to author answers from scratch under interrogation. Product owners resist this — it feels like an exam. A different interaction model is needed where the AI does the creative work and the human curates.

## Decision

Use a Propose-Review methodology based on Specification by Example (Gojko Adzic). The AI generates concrete behavioural examples as Gherkin scenarios organised by category (Key, Boundary, Negative, Illustrative). The human curates them using accept/reject/modify/add/defer per group. AI does the creative work; human does quality control.

## Rationale

Curation is lower-friction than authoring. Product owners naturally think in terms of "yes that's right" or "no it should be like this instead" rather than generating requirements from scratch. The AI's edge case generation adds scenarios the human wouldn't have considered — boundary values, security implications, concurrency, failure recovery.

## Alternatives Rejected

- **Question-based elicitation** — RequireKit's failed approach; humans abandon the session
- **No interaction** — Risks generating wrong behaviour with no correction opportunity
- **Structured questionnaire** — Same friction problem as elicitation

## Consequences

**Positive:**
- 5-10 minutes of review vs 30-60 minutes of Q&A
- AI generates edge cases human wouldn't consider
- Assumptions explicitly tracked with confidence levels
- Fast path: accept entire groups at once

**Negative:**
- AI may propose obviously wrong behaviour (mitigated by human curation)
- Requires AI with good domain understanding (mitigated by codebase context gathering)

## The 6-Phase Cycle

1. **Context Gathering** — AI reads codebase, Graphiti, existing patterns (no human interaction)
2. **Initial Proposal** — AI generates complete Gherkin set grouped by Spec by Example categories
3. **Human Curation** — Accept/reject/modify/add/defer per group
4. **Edge Case Expansion** — AI generates additional security, concurrency, failure scenarios
5. **Assumption Resolution** — AI proposes defaults for deferred items with confidence levels
6. **Output Generation** — `.feature`, `_assumptions.yaml`, `_summary.md`, scaffolding

## Related

- Supersedes RequireKit's `/gather-requirements` approach for Rich's workflow
- Feeds into [ADR-SP-003](ADR-SP-003-adversarial-cooperation.md) — Gherkin becomes the Coach's validation contract
- Follows [ADR-SP-006](ADR-SP-006-adaptive-ceremony.md) — `--auto` flag for low-ceremony, full cycle for high-ceremony

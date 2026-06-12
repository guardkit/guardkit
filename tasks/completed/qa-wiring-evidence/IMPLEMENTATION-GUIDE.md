# Implementation Guide: FEAT-QAWE — Stack-agnostic wiring evidence

> Full design: [`docs/features/qa-verifier-wiring-probes-scope.md`](../../../docs/features/qa-verifier-wiring-probes-scope.md).
> QA-Verifier piece #2. Governing rule: `.claude/rules/stack-plugin-architecture.md`
> (stack-agnostic by default; plugin only for irreducible execution).

## Data Flow: Read/Write Paths

```mermaid
flowchart LR
    subgraph Analyze["Wave 0: guardkitfactory.wiring (tree-sitter, agnostic)"]
        A1["WiringAnalyzer + dialects<br/>py/js/ts/csharp (DATA)"]
    end
    subgraph Seam["guardkit←factory lazy seam"]
        SE["analyze_wiring(authored, worktree, task_type)"]
    end
    subgraph Storage["coach_evidence (Waves 1-3)"]
        S1[("bundle.wiring")]
        S2[("bundle.mocked_seam")]
        S3[("bundle.spec_gap")]
    end
    subgraph Reads["Coach verdict"]
        R1["_render_evidence_bundle_section<br/>+ guard #7 (advisory)"]
        R2["_apply_spec_gap_absent_guard<br/>(deterministic, whole-file only)"]
    end
    subgraph BDD["FEAT-E2CB (BDDWIRE)"]
        B1["BDDRunResult (multi-stack)"]
    end

    A1 -->|UNWIRED| SE
    A1 -->|MOCKED| SE
    SE --> S1
    SE --> S2
    B1 -->|"executed evidence (Wave 3 dep)"| S3
    S1 --> R1
    S2 --> R1
    S3 --> R1
    S3 --> R2

    style A1 fill:#cfc,stroke:#090
    style B1 fill:#ffc,stroke:#c90
    style R2 fill:#cff,stroke:#099
```

**Note:** `bundle.spec_gap` (Wave 3) reads executed evidence from **FEAT-E2CB
(BDDWIRE)** — cross-feature dependency, operator-sequenced (BDDWIRE merges first). All
analysis is stack-agnostic tree-sitter; the only plugin layer is BDD *execution*
(consumed, not duplicated).

## Task Dependencies

```mermaid
graph TD
    T1["QAWE-001<br/>Wave 0: analyzer core"] --> T2["QAWE-002<br/>Wave 1: UNWIRED integration"]
    T1 --> T3["QAWE-003<br/>Wave 2: MOCKED_SEAM"]
    T2 --> T4["QAWE-004<br/>Wave 3: SPEC_GAP + guard<br/>(needs FEAT-E2CB merged)"]
    style T2 fill:#cfc,stroke:#090
    style T3 fill:#cfc,stroke:#090
```

_QAWE-002 and QAWE-003 can run in parallel (both depend only on QAWE-001)._

## Waves

| Wave | Task | Focus | Complexity |
|---|---|---|---:|
| 1 | QAWE-001 | tree-sitter WiringAnalyzer + 4 dialects, fixture-tested, no guardkit integration | 6 |
| 2 | QAWE-002 | UNWIRED_PATH bundle integration (fields, gather, render) | 5 |
| 3 | QAWE-003 | MOCKED_SEAM evidence (parallel with Wave 2) | 4 |
| 4 | QAWE-004 | SPEC_GAP + deterministic hard-guard — **gated on FEAT-E2CB (BDDWIRE)** | 5 |

## Scope boundaries

Plugins ONLY for execution (the existing `guardkitfactory/bdd`, consumed by SPEC_GAP).
No new per-stack analysis code. QA-Verifier #1 (fine-tune) and #3 (glue-policy) OUT.

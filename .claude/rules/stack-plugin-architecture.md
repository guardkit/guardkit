# Stack-agnostic by default; plugin only for irreducible execution

> **Source**: Seeded 2026-06-12 from the QA-Verifier wiring-probe design
> session, which first proposed a Python-`ast` monolith (Python-only) for a
> *stack-agnostic* quality gate — the exact stack-blindness anti-pattern
> [TASK-REV-STKB](../../tasks/backlog/TASK-REV-STKB-stack-blindness-audit-and-bdd-plugin-architecture.md)
> exists to prevent. This is the rule TASK-REV-STKB Workstream D specified
> ("stack-assumption must be isolated in a named plugin") but never landed —
> and its absence is *why* the anti-pattern recurred. Paired with the Graphiti
> node of the same name under `guardkit__project_decisions`. Sibling of
> [`namespace-hygiene.md`](namespace-hygiene.md),
> [`absence-of-failure-is-not-success.md`](absence-of-failure-is-not-success.md),
> and the Graphiti *"runner without producer anti-pattern"* node.

## The rule

GuardKit and guardkitfactory are **multi-stack** (Python, TypeScript/JavaScript,
.NET/C#, and more — see `installer/core/templates/`). When building a
quality-gate or analysis component:

1. **A stack-AGNOSTIC mechanism is the DEFAULT.**
2. **A per-stack plugin is a LAST RESORT**, justified ONLY where the operation
   is *irreducibly* stack-specific.

The dividing line is **static analysis vs execution**:

| Operation | Mechanism | Why |
|---|---|---|
| **Static analysis** — reachability, mock-seam detection, symbol/reference extraction, wiring/composition-root checks | **ONE multi-language parser** (`tree-sitter`: one library, declarative S-expression queries, precompiled grammars for `python`/`javascript`/`typescript`/`c_sharp`/… via `tree-sitter-language-pack`) + thin **declarative per-language dialect descriptors** (queries + framework pattern lists as **DATA**) | Parsing many languages is a solved, agnostic problem. A new language = a descriptor (data), not a code plugin. |
| **Execution** — actually *running* pytest-bdd vs reqnroll vs cucumber-js | **Plugin**: ABC + contract-gated loader + `discover(stack)` + a **`status` discriminator** that degrades an unsupported stack to **absent-signal, never a false pass** | You genuinely cannot parse your way out of "run the tests." This is the *only* legitimate plugin case. |

**Static analysis must NOT be siloed into the plugin system.** Writing a plugin
per stack for something a multi-language parser does once is the anti-pattern.

## The built reference (copy this shape for execution plugins)

`guardkitfactory/src/guardkitfactory/bdd/` — `BDDPlugin` ABC + `BDDRunResult`
contract (`plugin.py`), a **contract-gated** `loader.py` (a plugin cannot
`register` unless its C1–C6 contract tests pass), `discover(stack_profile)`
dispatch, and three stacks: `pytest_bdd_plugin.py`, `reqnroll_plugin.py` (.NET),
`cucumber_js_plugin.py` (JS). 42 tests. The `status` discriminator distinguishes
"ran and passed" from "no runner / no scenarios / crashed" — so an unsupported
stack is **absent evidence, not a pass** (the `absence-of-failure` rule).

## Symptom

- A component the orchestrator treats as stack-agnostic that, in fact, only
  works on one stack (the `bdd_runner.py` pytest-bdd hardcoding; the
  QA-Verifier wiring-probe Python-`ast` first draft).
- On any other stack it crashes or silently returns a zero/empty result that a
  downstream gate reads as "no problem found" → false pass.

## Detection recipe

```bash
# 1. Single-language parser used for ANALYSIS in a stack-agnostic component
rg -n "^import ast$|^\s*import ast\b|ast\.parse\(" guardkit/orchestrator/ guardkitfactory/src/
#    -> if it's analysing TARGET-PROJECT code (not guardkit's own), it's stack-blind.

# 2. A test/build runner shelled directly without a registry + status discriminator
rg -n "subprocess.*\b(pytest|dotnet|npm|jest|vitest|reqnroll|cucumber)\b" guardkit/orchestrator/ | rg -v "runners?/|plugins?/"

# 3. A new analysis component that should be tree-sitter but isn't
rg -ln "tree_sitter|tree-sitter" guardkit guardkitfactory   # expected hits once analysis lands

# 4. Sibling-rule lookup
rg "stack-plugin-architecture|stack-assumption" .claude/ ; rg "runner without producer" .claude/
```

## Remediation recipe

1. **Analysis → tree-sitter + dialect descriptors.** One analyzer over the CST;
   per-language queries + framework registration/mock pattern lists as data.
   Day-one parity is cheap (Python + JS + TS + C# are all in the language pack);
   a new language is a descriptor, not a plugin.
2. **Execution → plugin behind the `guardkitfactory/bdd` pattern.** ABC +
   contract-gated loader + `discover(stack)` + `status` discriminator.
3. **Unknown / unsupported stack → absent-signal.** Emit a `status` that the
   Coach reads as ABSENT EVIDENCE (surface as feedback / unverified), never a
   silent pass. See `absence-of-failure-is-not-success.md`.
4. **Capture the decision in Graphiti** (`guardkit__project_decisions`) AND a
   `.claude/rules/` file so the next session inherits it — the failure mode this
   rule documents is itself a *Graphiti-didn't-capture-it* failure.

## When this rule triggers

- Before building ANY new quality-gate / analysis component that touches
  target-project source, tests, or build artefacts.
- During Phase 2.5 architectural review for anything under
  `guardkit/orchestrator/quality_gates/` or `guardkitfactory/`.
- Whenever a design says "Python-first, other stacks later" for analysis — that
  phrasing is the smell; for analysis, multi-stack is *free* via tree-sitter and
  "later" is the stack-blindness deferral.

## What this rule does NOT require

- guardkit's OWN tooling (the orchestrator) is legitimately Python — this rule
  is about analysing **target projects**, which may be any stack. Parsing
  guardkit's own `ast` for guardkit-internal purposes is fine.
- It does not forbid plugins — it forbids them as the *default*. Execution is a
  real plugin case; keep using the `guardkitfactory/bdd` pattern there.

# qa/ — this repo's verification data (GuardKit tier-1 QA formats)

Scaffolded by `guardkit init` (WS2 session B1, 2026-07-07). Schemas are owned
by guardkit (`guardkit/qa/formats/`); the INSTANCES in this directory belong
to this repo — gates travel with the agent (decision DF-007).

Validate any instance:

```bash
guardkit qa validate <kind> <path>
# kinds: pass-bar (f1), known-failures (f2), leak-sweep (f3),
#        gate-registry (f4), results-envelope, evidence-index (f5)
guardkit qa kinds            # list kinds + schema versions
guardkit qa schema <kind>    # JSON-Schema export
```

| File | Format | What it is |
|---|---|---|
| `pass-bar-<TASK-ID>.yaml` | F1 | The observable success bar, committed BEFORE implementation. Written at spec/plan time (headless `/feature-spec` + `/feature-plan` will emit it). |
| `known-failures.yaml` | F2 | The documented expected suite outcome + triaged known failures. Runs are diffed against this ledger, never against "all green". Written by human/Coach at triage only — never mid-build. |
| `leak-sweep.yaml` | F3 | Which surfaces are claimed real, what mock strings/patterns must never appear there, which regions stay mock by design. |
| `gates/registry.yaml` | F4 | The repo's durable, named live-gate scripts (exit 0 = pass; non-zero enumerates failures in a JSON results envelope). |
| `<evidence-dir>/EVIDENCE.yaml` | F5 | Index of evidence artifacts (numbered screenshots etc.) with per-artifact inspection state. Emitted by the live-gate runner. |

The scaffolded stubs validate as-is but carry placeholder content — replace
the placeholders with this repo's reality before enforcement
(`qa.enforce_tier1`) is switched on for this repo.

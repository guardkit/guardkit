# DCL v1.0 — Compiler-Verified Closed Vocabulary

**Provenance.** Upstream: `github.com/russelleast/Capability-Language` @ pin `4f9fbe56414eecbd100c337da770e1e24c2fcc85` (v1.0.6, Apache-2.0; LICENSE retained upstream). Enum sets extracted from the Go semantic checker (`compiler/internal/compiler/policy_domain.go`, `domain_constants.go`, `compiler.go`; grammar from `compiler/internal/parser/parser.go`). **Every literal below was verified against the running compiler**: 227 probes (161 accept + 66 reject) through the estate's vendored WASM checker (`fleet-evals/harness/dcl/bin/dcl-check.mjs`, vendored from the same pin), 2026-07-17, all consistent with the extracted sets — including the skeleton below, which compiles verbatim with zero diagnostics. This file contains only compiler-verified facts. Using a literal outside a closed set below produces the named `DCL_*` error and the file fails to compile.

## File header

Every file starts with `language dcl 1.0`. (Omitting it is only a warning, `DCL_VERSION_DECL_MISSING`. Any name other than `dcl` → `DCL_PARSE_LANGUAGE_UNSUPPORTED`.) Line comments use `//`.

## Top-level declarations (closed set)

`language` · `context <Name>` · `depends on <context>` · `shape` · `actor` · `event` · `effect` · `policy` · `capability`
Anything else → `DCL_PARSE_EXPECTED_DECLARATION`. `shape/actor/event/effect/policy/capability` may be prefixed `private`.

## Capability file skeleton (all constructs verified)

```dcl
language dcl 1.0

actor Customer is human                    // actor <Name> is <kind>

shape OrderInput {                         // field: Type [required]
  orderId: Uuid required
  notes: Text
}

event OrderPlaced is {                     // inline payload — or: event OrderPlaced is SomeShape
  orderId: Uuid required
}

effect PersistOrder is persistence         // effect <Name> is <kind> — or: effect X { kind persistence }
effect NotifyCustomer is notification

policy OrderReliability {
  reliability {                            // one or more family blocks
    timeout 5 seconds
    idempotency required
  }
}

capability PlaceOrder {
  intent OrderInput from Customer          // or a named block: intents { Submit with OrderInput from Customer }
  actors {                                 // optional role bindings
    approver: Customer
  }
  outcomes {                               // or single: outcome Accepted [is {…} | is Shape]
    Accepted
    Rejected
  }
  rules {                                  // or single line: rule R1: <free-form expression>
    ValidTotal: total above 0
  }
  effects {                                // references to top-level effects only
    PersistOrder                           // (re-declaring a kind here is a parse error)
    NotifyCustomer after PersistOrder      // optional ordering
  }
  events {
    emits OrderPlaced
  }
  policies {
    OrderReliability governs capability    // `governs` (canonical) or `applies to`
  }
  observe {
    capability duration as place_order_duration
    effect PersistOrder count failures as persist_failures
  }
  lifecycle {                              // owned lifecycle; supervised form below
    begin step Started
    end step Completed
    step Started {
      kind active
      deadline 2 days causing outcome Rejected
    }
    move Started to Completed on outcome Accepted
  }
  when {                                   // every declared outcome must be caused here
    ValidTotal violated then Rejected
    otherwise then Accepted                // otherwise must be last; `always X` must be the only branch
  }
}
```

Supervised lifecycle (cross-capability): `supervises lifecycle <Name> { identity <field>  contributors { <Capability>… }  begin step … end step … step X { kind waiting  waits for outcome <O> from <Capability> }  move A to B on outcome <O> from <Capability> }`. Recovery: inside a step, `recovery <CapabilityOrEffect>` — target must be a contributor capability (or effect) with at least one `move … from <target>` transition. Decision steps: `requires decision from <role-or-actor>`.
Unknown capability-section keyword → `DCL_PARSE_UNKNOWN_CAPABILITY_SECTION`. Valid sections: `intent, intents, actors, outcome, outcomes, rule, rules, effect, effects, events, policies, observe, when, lifecycle, supervises`.

## Closed enums

### Actor kinds — `actor X is <kind>` (`DCL_SEM_ACTOR_KIND_UNKNOWN`)
`human` · `system` · `agent` · `scheduled_process`

### Effect kinds — `effect X is <kind>` (`DCL_SEM_EFFECT_KIND_UNKNOWN`)
`persistence` · `notification` · `invocation` · `tool`
Legacy aliases `persist`, `notify`, `invoke` compile with warning `DCL_SEM_EFFECT_KIND_LEGACY` and normalize to the canonical kinds. Do not use them.

### Field types — built-in (`shape`/payload fields)
`Text` · `Boolean` · `Number` · `Date` · `DateTime` · `Uuid` · `Email` · `Money` · `List<T>` (T = any valid type) · any declared `shape` name.
A shape may not shadow a built-in name (`DCL_SEM_TYPE_BUILTIN_SHADOWED`). **Caution:** in the default (no `context`) scope the compiler does NOT reject unknown type names (e.g. `String`, `Int` compile silently); inside a declared `context` they fail with `DCL_SEM_UNDEFINED_SYMBOL`. Always use the list above — never `String`/`Int`/`Float`.

### Policy families — block name inside `policy` (`DCL_SEM_POLICY_FAMILY_UNKNOWN`)
`reliability` · `availability` · `scalability` · `performance` · `security` · `compliance` · `governance` · `data_protection` · `confidence`
A policy must declare ≥1 family (`DCL_SEM_POLICY_FAMILY_REQUIRED`).

### Policy `kind` keyword (`DCL_SEM_POLICY_KIND_UNKNOWN`)
Only `confidence` is valid as `kind <k>` (and then `threshold <0..1>` is required).

### Policy concerns — closed set, each bound to specific families (`DCL_SEM_POLICY_CONCERN_UNKNOWN`; wrong family → `DCL_SEM_POLICY_CONCERN_WRONG_FAMILY`)

| Family | Concerns (verified value shapes) |
|---|---|
| reliability | `retry { attempts <n> [backoff <strategy>] }` · `backoff <strategy>` (requires retry) · `timeout <duration>` · `idempotency required\|allowed\|forbidden` · `compensation <name>` · `circuit_breaker { opens after <n> failures  resets after <duration-single-token, e.g. 30s> }` |
| availability | `degradation allowed\|forbidden` · `fallback <OutcomeName>` · `dependency_tolerance required\|allowed\|forbidden` |
| scalability | `concurrency <n>` · `rate_limit <n> per <unit>` · `queue allowed\|forbidden` · `backpressure <strategy>` |
| performance | `latency <percentile> under <duration-single-token, e.g. 200ms>` · `throughput above <n> per <unit>` · `budget <duration>` |
| security | `authentication req/allow/forbid` · `authorization req/allow/forbid` · `classification <level>` · `encryption req/allow/forbid` |
| compliance | `audit` · `retention <n> <period-unit>` · `approval` · `evidence` (all `required\|allowed\|forbidden` except retention) |
| governance | `audit` · `approval` · `evidence` · `retention` (same shapes as compliance) |
| data_protection | `sensitivity <level>` · `masking` · `minimization` · `deletion` (req/allow/forbid) · `retention <n> <period-unit>` |
| confidence | `threshold <0..1>` (parsed as the `confidence` concern) |

Concern parameter names are closed per concern (`DCL_SEM_POLICY_CONCERN_UNSUPPORTED`): retry → `attempts`, `backoff`; circuit_breaker → `opens`, `resets`; confidence → `threshold`; all others → single scalar `value` line.

### Concern enum values (`DCL_SEM_POLICY_CONCERN_VALUE_INVALID`)
- required/allowed/forbidden set (idempotency, authentication, authorization, encryption, audit, approval, evidence, masking, minimization, deletion, dependency_tolerance): `required` · `allowed` · `forbidden`
- allowed/forbidden only (degradation, queue): `allowed` · `forbidden` (`required` is REJECTED here)
- `classification`: `public` · `internal` · `confidential` · `restricted`
- `sensitivity`: `none` · `personal` · `sensitive` · `special_category`

### Duration units (timeout, budget, circuit_breaker resets, deadline …) (`DCL_SEM_POLICY_CONCERN_VALUE_INVALID`)
`ms` · `millisecond(s)` · `s` · `second(s)` · `m` · `minute(s)` · `h` · `hour(s)` · `d` · `day(s)` — as `<n> <unit>` or single token `<n><short-unit>` (e.g. `500ms`, `30s`). No weeks.

### Period units (retention only)
`day(s)` · `month(s)` · `year(s)` — note `hours`/`weeks` are invalid for retention.

### Policy attachment targets — `<Policy> governs <target>` (`DCL_SEM_POLICY_ATTACHMENT_INVALID` / `DCL_SEM_POLICY_TARGET_UNKNOWN`)
`capability` · `effect <name>` · `outcome <name>` · `event <name>` · `lifecycle`
Attachment constraints (verified): `circuit_breaker` may only govern effects (`DCL_SEM_POLICY_CONCERN_ATTACHMENT_INVALID`); a `retry` policy attached to a target requires `idempotency allowed|required` effective on the same target (`DCL_SEM_RETRY_REQUIRES_IDEMPOTENCY`).

### Observe target kinds — first token of an `observe` line (`DCL_SEM_OBSERVE_TARGET_UNKNOWN`)
`capability` · `effect <name>` · `outcome <name>` · `event <name>` · `lifecycle`

### Observation types (`DCL_SEM_OBSERVE_TYPE_UNSUPPORTED`)
`count` · `duration` · `violations` · `failures` · `transitions`
Line shape: `<target-kind> [<target-name>] <type> [as <metric_name>]` (e.g. `effect X count failures as m` — `count <word>` re-reads the word as the type).

### Lifecycle step kinds — `kind <k>` inside `step` (`DCL_SEM_LIFECYCLE_STEP_KIND_INVALID`)
`active` · `waiting` · `decision` · `recovery` · `terminal`
`waiting` steps must declare ≥1 `waits for …` and have an exit transition. `end step` steps are terminal implicitly.

### Lifecycle transition triggers — `move A to B on <kind> <name> [from <Capability>]` (`DCL_SEM_LIFECYCLE_TRIGGER_KIND`)
`event` · `outcome`

### Wait signal kinds — `waits for <kind> <name> [from <Capability>]` (`DCL_SEM_LIFECYCLE_WAIT_SIGNAL_KIND`)
`event` · `outcome` (enforced with or without `from`)

### Deadline consequence — `deadline <duration> causing <kind> <name>` (`DCL_SEM_LIFECYCLE_DEADLINE_CONSEQUENCE_KIND`)
`outcome` only.

### `when` block grammar (causation; every outcome must appear — `DCL_SEM_OUTCOME_CAUSE_REQUIRED`)
- `always <Outcome>` — must be the ONLY branch (`DCL_SEM_ALWAYS_WITH_OTHER_BRANCHES`)
- `otherwise then <Outcome>` — must be last, at most once
- `<Rule> violated then <Outcome>`
- `<Effect> unresolved then <Outcome>` (`failed` is a silent legacy alias of `unresolved`)
- `policy <Policy> <state> then <Outcome>`
Non-policy decisions outside {`violated`, `unresolved`, `failed`, `denied`, `denies`, `fails`} → `DCL_SEM_CAUSATION_DECISION_UNKNOWN`.

### Policy causation states — `policy P <state> then O` (`DCL_SEM_POLICY_CAUSATION_STATE_INVALID`)
`denies` (alias `denied`) · `exhausted` · `times_out` · `open` · `degraded` · `fallback_used` · `fails`
Each state requires the matching concern on an attached policy, else `DCL_SEM_POLICY_CAUSATION_CONCERN_MISSING`:
`denies`←authorization · `exhausted`←retry · `times_out`←timeout · `open`←circuit_breaker · `degraded`←degradation · `fallback_used`←fallback · `fails`←confidence.

## Verified quirks of the vendored WASM checker
- `language dcl 9.9` is ACCEPTED by the WASM build (its version manifest is unresolvable in WASM, so the `DCL_VERSION_UNSUPPORTED` gate is inert; version.json at the pin says supports=1.0). Always write `1.0`.
- Unknown field types pass silently in the default context (see Field types above).

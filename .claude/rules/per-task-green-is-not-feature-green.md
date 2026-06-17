# Per-task-green is not feature-green; a mocked primary seam is absent integration evidence

> **Source**: Seeded by TASK-AB-WIREGATE01 (2026-06-17). Pair with the Graphiti
> design-rule node *"per-task-green is not feature-green; a mocked primary seam
> is absent integration evidence"* under `guardkit__project_decisions`. Sixth
> member of the low-fidelity-oracle meta-frame family, alongside
> [`absence-of-failure-is-not-success.md`](absence-of-failure-is-not-success.md)
> (false-green interpretation),
> [`path-string-mismatch-is-not-dishonesty.md`](path-string-mismatch-is-not-dishonesty.md)
> (false-red interpretation),
> [`harness-cancellation-contract.md`](harness-cancellation-contract.md)
> (dispatch),
> [`evidence-boundary-narrower-than-write-surface.md`](evidence-boundary-narrower-than-write-surface.md)
> (collection — this rule's direct parent), and
> [`smoke-gate-is-feedback-not-terminator.md`](smoke-gate-is-feedback-not-terminator.md)
> (disposition). The shared meta-frame: *a binary verdict from a low-fidelity
> oracle that cannot distinguish "no signal" from "positive/negative signal"*.

## The rule

The per-task Coach is an evidence aperture **narrower than the assembled
feature**. A whole feature can pass **every per-task Coach + the full unit
suite** yet be **non-functional**, because the per-task aperture never exercises
the assembled composition: an "integration" test mocks the very seam it claims
to integrate, and the composition root wires services up with the wrong
constructor arity. Per-task-green is therefore **not** feature-green. A mocked
**primary in-repo seam** is **absent integration evidence**, not a passing
integration; a composition-root constructor-arity mismatch is a wiring defect no
per-task pytest can see (each task's tests pass in isolation).

The remediation is a **post-wave** wiring gate whose aperture is the
**wave-aggregate authored set** (the assembled feature), pairing the binary
per-task verdict with a positive integration-evidence precondition: the primary
seams are exercised, not mocked, and the composition root constructs each
first-party service with all required `__init__` args. Findings feed back to the
Player (bounded retry), never hard-terminate (warning-severity heuristics).

## Why this rule exists

1. **2026-06-13/14** — FEAT-POC-006 (lpa-platform-poc, cloud/SDK autobuild).
   The router/"integration" tests did `AsyncMock(spec=VoiceService)` of the
   primary in-repo service, and `main.py` constructed the service with the
   wrong/missing `__init__` args. **345 tests green, feature dead.** Every
   per-task Coach approved; the assembled feature never ran. This is the same
   *green ≠ correct* class FEAT-FAUD exposed locally (synthetic tests that
   encode the implementation's own wrong assumption), now at the
   feature-assembly boundary instead of the single-task boundary.

The defect is a **collection** defect (the parent
`evidence-boundary-narrower-than-write-surface` shape): the oracle never sees
the work because its aperture is too narrow — here the aperture is *temporal /
assembly* (per-task, pre-composition) rather than *spatial* (a sibling repo).
The spurious "no signal" is "no integration failure", read as "integration
passes", when in fact integration was **never exercised** (the seam was mocked;
the composition root was never arity-checked per task).

## Symptom

- A feature finishes with every wave's per-task Coach `approve`, the full unit
  suite green, and the deliverable nonetheless non-functional when run for real.
- An integration-tier test (`tests/integration/`, `tests/e2e/`, `features/`)
  constructs `AsyncMock(spec=<Service>)` / `MagicMock(spec=<Service>)` /
  `create_autospec(<Service>)` / `patch("<pkg>.<Service>")` where `<Service>` is
  a **first-party** module the feature is supposed to wire together.
- The composition root (`main.py` / app factory / DI container) constructs a
  first-party service with fewer (or more) positional/keyword args than its
  `__init__` signature requires.

## Detection recipe

```bash
# 1. The post-wave wiring gate must exist and run between the smoke gate and
#    wave-completion persistence. MUST MATCH; absence = the gate is gone.
rg -n "_run_post_wave_wiring_gate" guardkit/orchestrator/feature_orchestrator.py

# 2. The turn-rejecting collector: only mocked-primary-seam + ctor-arity feed
#    back; UNWIRED stays advisory; absent signals are never turn-rejecting.
rg -n "_collect_turn_rejecting_wiring_findings|authored_this_turn" \
   guardkit/orchestrator/feature_orchestrator.py

# 3. The stack-agnostic analysis lives in guardkitfactory (tree-sitter + DATA),
#    NOT a guardkit-side python-ast monolith (stack-plugin-architecture.md).
rg -n "ctor_arity|CTOR_ARITY|constructor_signature_query" \
   ../guardkitfactory/src/guardkitfactory/wiring/

# 4. The cross-repo contract is CI-guarded (a factory version skew that drops
#    the ctor_arity key fails in seconds, not on a live run).
rg -n "ctor_arity" tests/orchestrator/test_wiring_ctor_arity_seam.py

# 5. Sibling-rule lookup (this rule + the family).
rg "per-task-green-is-not-feature-green|evidence-boundary-narrower|absence-of-failure|smoke-gate-is-feedback" .claude/rules/
```

## Remediation recipe

1. **Widen the aperture to the assembled feature.** Run the wiring analysis
   over the **wave-aggregate** authored set (`_wave_authored_files`), not the
   per-task authored set. Per-task isolation is the aperture that is too narrow.
2. **Pair the per-task verdict with a positive integration-evidence
   precondition.** A mocked **primary in-repo seam** is absent integration
   evidence — flag it. A composition root that constructs a first-party service
   with the wrong arity is a wiring defect — flag it. Only these two
   high-confidence signals are turn-rejecting; UNWIRED stays advisory.
3. **Stack-agnostic static analysis** (per
   `stack-plugin-architecture.md`): tree-sitter + declarative per-language
   dialect descriptors (`guardkitfactory.wiring`), never a python-`ast`
   monolith. Day-one Python; other stacks are a dialect (DATA) away.
4. **Absence-of-failure-safe** (per `absence-of-failure-is-not-success.md`):
   unsupported stack, no composition root, no acceptance files, a splat at the
   call site or in the signature, parse-degraded — all are **absent** signals,
   never a pass and never a turn-rejection. Only a *ran-and-found* result feeds
   back. Bias toward no-finding on any uncertainty.
5. **Feed back, do not terminate** (per
   `smoke-gate-is-feedback-not-terminator.md`): findings become turn-1
   `seed_feedback` bounded by `GUARDKIT_WIRING_GATE_MAX_RETRIES` (default 1).
   Unlike the smoke gate, exhausting the budget NEVER hard-terminates the
   feature — wiring findings are warning-severity heuristics, so an unresolved
   finding becomes advisory and the build continues.
6. **Boundary mocks are legitimate.** Mocking a true external boundary
   (HTTP clients, DB drivers, allow-listed third-party modules) is NOT flagged.
   The signal is specifically a **first-party** seam being mocked away.
7. **CI-guard the cross-repo contract** (per `namespace-hygiene.md` /
   `harness-cancellation-contract.md`): a seam test asserts the real installed
   `guardkitfactory.wiring.analyze_wiring` carries the `ctor_arity` key and the
   dialect exposes the ctor-arity query fields, so a version skew fails in CI.

## Grep-able signature (for next agent)

```bash
# Gate-present fingerprint (MUST MATCH):
rg -n "_run_post_wave_wiring_gate" guardkit/orchestrator/feature_orchestrator.py
# Collector fingerprint — only seam(authored)+ctor are turn-rejecting:
rg -n "authored_this_turn is True|ctor.get\(.status.\) == .ran." \
   guardkit/orchestrator/feature_orchestrator.py
# Never-terminate fingerprint — findings_unresolved, terminate stays False:
rg -n "findings_unresolved" guardkit/orchestrator/feature_orchestrator.py
# Factory analysis fingerprint (stack-agnostic, in guardkitfactory):
rg -n "def _summarise_params|CtorArityResult|mock_call_query" \
   ../guardkitfactory/src/guardkitfactory/wiring/
# Sibling-rule lookup:
rg "per-task-green-is-not-feature-green|evidence-boundary-narrower" .claude/rules/
```

## Meta-frame

| Rule | Failure locus | Direction | Spurious "no signal" comes from… |
|---|---|---|---|
| `absence-of-failure-is-not-success` | interpretation | false-green | a zero counter read as a pass when zero attempts ran |
| `path-string-mismatch-is-not-dishonesty` | interpretation | false-red | a path miss read as a lie when the orchestrator moved the file |
| `harness-cancellation-contract` | dispatch | divergence | a cancel that no-ops on a substrate it wasn't written for |
| `evidence-boundary-narrower-than-write-surface` | collection | both | work done outside the oracle's *spatial* aperture (a sibling repo) |
| `smoke-gate-is-feedback-not-terminator` | disposition | wasted-signal | a *correct* high-fidelity failure used to terminate instead of feed back |
| **`per-task-green-is-not-feature-green`** | **collection** | **false-green** | **integration done outside the oracle's *assembly/temporal* aperture (per-task, pre-composition) — a mocked primary seam, an un-arity-checked composition root** |

This rule is the **assembly/temporal** sibling of
`evidence-boundary-narrower-than-write-surface` (whose missing aperture is
*spatial*, across a repo split). Both are collection-locus defects; both pair
the binary verdict with a *positive-evidence* precondition before trusting a
"no problem here" verdict — there it is a spatial aperture covering the declared
write surface, here it is an assembly aperture covering the *composed* feature
(seams exercised, composition root arity-checked).

## Prior art

- **Direct parent (collection locus, spatial)**:
  [`evidence-boundary-narrower-than-write-surface.md`](evidence-boundary-narrower-than-write-surface.md).
- **Stack-agnostic mandate**:
  [`stack-plugin-architecture.md`](stack-plugin-architecture.md) — the wiring
  analysis is tree-sitter + DATA in `guardkitfactory.wiring`, never a
  python-`ast` monolith.
- **Absence-of-failure safety**:
  [`absence-of-failure-is-not-success.md`](absence-of-failure-is-not-success.md).
- **Feed-back-not-terminator disposition**:
  [`smoke-gate-is-feedback-not-terminator.md`](smoke-gate-is-feedback-not-terminator.md)
  — `_run_post_wave_wiring_gate` is placed and shaped exactly like
  `_run_post_wave_smoke_gate`, with the stronger never-terminate posture.
- **Cross-repo contract CI-guard**:
  [`namespace-hygiene.md`](namespace-hygiene.md) /
  [`harness-cancellation-contract.md`](harness-cancellation-contract.md) — the
  `ctor_arity` seam test (`tests/orchestrator/test_wiring_ctor_arity_seam.py`)
  is the analogue of the harness `test_xrepo_contract_seam.py`.
- **Originating defect**: FEAT-POC-006 (lpa-platform-poc voice autobuild retro).
  Cross-reference: `docs/retro/autobuild-retro-xref-2026-06-17.md` §3.1 / §5.2.
- **Originating fix**: TASK-AB-WIREGATE01 (2026-06-17). guardkitfactory:
  `CtorArityResult` + `_extract_ctor_signatures` / `_summarise_params` /
  `_summarise_call_args` in `wiring/analyzer.py`, ctor-arity + spec-mock query
  data in `wiring/dialects/python.py`. guardkit:
  `_run_post_wave_wiring_gate` / `_wave_authored_files` /
  `_collect_turn_rejecting_wiring_findings` / `_build_wiring_feedback` +
  `WiringGatePhaseOutcome` + `GUARDKIT_WIRING_GATE_MAX_RETRIES` in
  `feature_orchestrator.py`.
- **Reproducer tests**: `guardkitfactory/tests/wiring/test_ctor_arity.py`
  (AC#6 a/b/c fixtures), `tests/unit/orchestrator/test_wiring_gate.py`,
  `tests/orchestrator/test_wiring_ctor_arity_seam.py`.
- **Pre-existing partial coverage this widened**: `mocked_seam` / `UNWIRED_PATH`
  evidence (`coach_evidence.py`, advisory) and `direct_mode_wiring_gap`
  (`autobuild.py`, registered-bin-entry-in-direct-mode only).

## When this rule triggers

- Before introducing or modifying any post-wave gate in
  `feature_orchestrator.py`, or the wiring analysis in
  `guardkitfactory.wiring`.
- Before authoring a feature whose deliverable is an assembled, multi-service
  composition (a router + services + a composition root) — the per-task Coach
  cannot see the assembly.
- Before broadening the turn-rejecting set beyond mocked-primary-seam +
  ctor-arity (e.g. promoting UNWIRED to turn-rejecting) — that raises the
  false-positive surface of a syntactic heuristic.
- During Phase 2.5 architectural review for anything touching the wave loop,
  `guardkitfactory/wiring/`, or the Coach wiring-evidence path.
- During any diagnostic session investigating a "every task approved and the
  unit suite is green but the feature does not run" report.

## What the rule does NOT cover

- **Boundary mocks.** Mocking a true external boundary (HTTP client, DB driver,
  an allow-listed third-party module) is correct test hygiene and is never
  flagged. The signal is a **first-party** seam being mocked away.
- **Dataclass / inherited / factory-built constructors.** A service with no
  explicit `__init__` (e.g. `@dataclass`), an inherited `__init__`, or one
  constructed through a helper rather than a direct `ClassName(...)` call yields
  no signature / no direct call and is an accepted false-negative (bias OK).
- **Variadic signatures or splat call-sites.** `__init__(self, *args, **kwargs)`
  or a call `Service(*args)` makes arity unknowable — never flagged.
- **Attribute-qualified construction.** `module.Service(...)` (a non-bare
  callee) is an accepted false-negative for the ctor-arity probe.
- **Non-feature task types.** The probe gates to FEATURE / REFACTOR /
  INTEGRATION; other task types legitimately produce un-wired stubs.
- **Keyword-name validation.** The arity check counts args; it does not validate
  that keyword names match parameter names (an accepted false-negative).
- **Coach-side hallucination of a passing integration verdict.** That is a
  different meta-defect (hallucinated evidence), not this aperture-too-narrow
  shape.

# Feature Spec Summary: QA Verifier Behavioural-Evidence Gates

**Stack**: python
**Generated**: 2026-07-04T16:05:00+01:00 (--auto mode)
**Scenarios**: 22 total (6 smoke, 3 regression)
**Assumptions**: 8 total (0 high / 0 medium / 8 low confidence)
**Review required**: Yes (--auto mode: all assumptions unconfirmed)

## Scope

The three genuinely-NEW QA-Verifier gates per the 2026-07-04 state consolidation
(`docs/retro/qa-verifier-state-consolidation-2026-07-04.md` §2): **L2 anti-stub
body scan** (tree-sitter + dialect DATA, extending the existing guardkitfactory
`WiringAnalyzer` dialect descriptors — NOT Python-ast, NOT a parallel analyzer),
**L3 runtime coverage/reachability gate** (suite under coverage; flag authored
public surface with zero real execution), and **L4 behavioural round-trip
oracle** (an oracle the Player did not author, run against the live dependency;
failed = hard RED verdict override persisted to disk, absent = WARN in v0).
Schema: three new sibling `Optional` absent-signal-safe fields on
`CoachEvidenceBundle` (`stub_scan`, `coverage`, `behavioural_oracle`) directly
after the existing `wiring`/`mocked_seam`/`spec_gap` fields
(`guardkit/orchestrator/quality_gates/coach_evidence.py:295-297`).

**Explicitly excluded**: the L1 wiring probes (UNWIRED_PATH / MOCKED_SEAM /
SPEC_GAP) — built 12–17 June (FEAT-C332); the Coach fine-tune (Phase 1, A3);
BDD glue-policy enforcement (QA-Verifier piece #3). A1–A6 stand unchanged.

## Scenario Counts by Category

| Category | Count |
|----------|-------|
| Key examples (@key-example) | 7 |
| Boundary conditions (@boundary) | 6 (incl. 1 outline x3 examples) |
| Negative cases (@negative) | 6 |
| Edge cases (@edge-case) | 5 |

## Deferred Items

None (--auto mode: no groups deferred; Phase 4 edge-case expansion skipped).

## Open Assumptions (low confidence)

All eight (ASSUM-001 … ASSUM-008) — `--auto` mode marks everything
unconfirmed. The load-bearing three to verify first:

- **ASSUM-003** — oracle declaration mechanism (artefact-presence convention
  path vs feature-YAML command). Governs the L4 activation seam.
- **ASSUM-005** — oracle timeout = ran-and-failed vs absent. Mirrors the
  COACHRUNPARITY01 asymmetry; wrong choice re-opens a false-red/false-green.
- **ASSUM-006** — only the failed oracle overrides verdicts in v0; stub +
  coverage stay advisory. Governs the false-red surface.

## Binding build constraints (from the consolidation — not assumptions)

- L2 is tree-sitter + dialect DATA extending `guardkitfactory/src/guardkitfactory/wiring/`
  dialect descriptors; a parallel analyzer or Python-`ast` monolith is the
  stack-blindness anti-pattern (`.claude/rules/stack-plugin-architecture.md`).
- The three bundle fields follow the absent-signal discipline: `None` = probe
  did not run; positive status + `findings: []` = real clean verdict; no status
  ever maps to "pass" (`.claude/rules/absence-of-failure-is-not-success.md`).
- Absence must survive every reconciliation/serialization layer to the
  checkpoint (`.claude/rules/absence-must-survive-every-reconciliation-layer.md`).
- The L4 verdict override must re-persist `coach_turn_N.json`
  (`.claude/rules/deterministic-verdict-override-must-persist-to-disk.md`).
- The bundle schema change is additive + versioned — it is the frozen seam
  forge consumes via `--coach-model` output (starter OQ#6); record in the
  dependable-forge overview when it lands.
- Dogfood rule (execution plan ACTION 3): every task in this feature's own
  buildplan carries an independent behavioural check, not only co-generated
  unit tests. Validate against the fs-01 case (FEAT-MEM-04 false green) and a
  deliberate correctly-wired stub (the class L1 cannot catch).

## Integration with /feature-plan

    /feature-plan "QA Verifier Behavioural-Evidence Gates" \
      --context features/qav-behavioural-gates/qav-behavioural-gates_summary.md

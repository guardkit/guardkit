"""GuardKit QA — machine-readable verification formats and (later) the live-gate runner.

WS2 layering (see ai-transition/docs/ws2-qa-verifier-and-last-mile-scope-design-2026-07-07.md):

- ``guardkit.qa.formats`` — the tier-1 format SCHEMAS (F1–F5), owned by guardkit.
  INSTANCES live in each app repo under ``qa/`` (DF-007: gates travel with the
  agent). Session B1 (2026-07-07) built the schemas + validators; no enforcement
  is wired here — enforcement (ledger diff, Coach pass-bar precondition,
  feature-complete gate refusal) is session B2's deliverable, kept separate so
  the schema layer stays reviewable.
"""

# api_test @ 5bc6fd1 — the routing law's hand-stamped 60 (READ-ONLY fixture)

Nine feature YAMLs (`.guardkit/features/`), their nine Gherkin files (`features/`) and the
gate registry (`qa/gates/registry.yaml`, carrying the `hurl-twins` gate that gives the repo
its HTTP surface), copied verbatim from api_test main `5bc6fd1` (2026-08-15, the hand
stamping of 60 scenarios). `tests/orchestrator/test_stamp_normalizer.py` runs the
normalizer in dry-run over this tree with existing stamps ignored and pins the
reproduction: 57/60 identical, the three divergences = users-count 7.1–7.3 (hurl by rule
R9, toolchain by hand) — the one divergence the 2026-08-15 rules doc named.

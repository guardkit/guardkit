# The estate corpus — the stamp normalizer's NEGATIVE regression fixture

READ-ONLY copies of every primary-tree `.feature` across the estate repos
(tracked `features/**/*.feature`; lpa-platform-poc: `docs/poc/features/`),
at the SHAs listed in `MANIFEST.tsv` (115 files, 3,077 scenarios; worktrees,
archives and test fixtures excluded), plus each repo's SURFACE evidence
(`qa/gates/registry.yaml`, `.guardkit/config.yaml`, `pyproject.toml`,
`package.json`) so the HTTP surface is detected structurally from the fixture.

`EXPECTED.json` is the committed per-repo histogram of homes + REFUSED (the
honest number). `tests/orchestrator/test_stamp_normalizer_estate_corpus.py`
asserts (a) operator == the four enumerated explicit-human scenarios,
(b) hurl == 0 wherever there is no hurl gate / declared surface, (c) the
histogram equals this file. Re-baseline ONLY after a deliberate rule change:
`STAMP_CORPUS_REBASELINE=1 pytest tests/orchestrator/test_stamp_normalizer_estate_corpus.py`.

Do not edit the copies. Refresh = re-copy from the repos + update MANIFEST.tsv
+ re-baseline, in one commit that says so.

| repo | http | total | refused | bus | process | exam | flutter | playwright | hurl | operator |
|---|---|---|---|---|---|---|---|---|---|---|
| forge | no | 535 | 413 | 92 | 29 | 0 | 0 | 0 | 0 | 1 |
| jarvis | no | 279 | 233 | 40 | 6 | 0 | 0 | 0 | 0 | 0 |
| fleet-memory | no | 233 | 215 | 13 | 5 | 0 | 0 | 0 | 0 | 0 |
| fleet-gateway | no | 33 | 18 | 15 | 0 | 0 | 0 | 0 | 0 | 0 |
| specialist-agent | no | 796 | 731 | 27 | 3 | 35 | 0 | 0 | 0 | 0 |
| study-tutor | YES (starlette) | 501 | 366 | 14 | 10 | 5 | 28 | 1 | 76 | 1 |
| guardkit | no | 168 | 159 | 8 | 1 | 0 | 0 | 0 | 0 | 0 |
| lpa-platform-poc | no | 205 | 195 | 0 | 0 | 4 | 0 | 4 | 0 | 2 |
| agentic-dataset-factory | no | 253 | 251 | 0 | 2 | 0 | 0 | 0 | 0 | 0 |
| api_test | YES (hurl-twins gate) | 74 | 0 | 0 | 17 | 0 | 0 | 0 | 57 | 0 |
| **TOTAL** | | **3077** | **2581** | 209 | 73 | 44 | 28 | 5 | 133 | 4 |

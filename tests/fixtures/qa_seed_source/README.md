# qa_seed_source — committed fixture for PB-6 (qa-seed harvest)

A tiny "source repo" the PB-6 qa-seed harvest phase is exercised against
(`guardkit/templates/qa_seed.py`, scope
`ai-transition/docs/pb6-harvest-verification-seeds-scope-2026-07-09.md` §7).

Deliberate contents:

- **`tests/check_pass.py`** — 3 passing tests (the observable green count).
- **`tests/check_red.py`** — 1 deliberately-failing test (a triaged red the F2
  baseline must record with owner+review_by, not swallow).
- **`tests/fixture_mocks.py`** — real mock identity strings the F3 deny_patterns
  seed is gathered from.
- **`settings.json`** — ≥2 `layer_mappings` (the F12 discovery-gate join key).
- **`pytest.ini`** — `python_files = check_*.py` so the fixture's tests are
  collected only when pytest runs **inside** this dir (via `observe_suite`'s
  isolated subprocess), never by guardkit's own `test_*.py` suite. This is why
  the deliberately-red test does not turn guardkit's suite red.

Nothing here is production code; it is test data.

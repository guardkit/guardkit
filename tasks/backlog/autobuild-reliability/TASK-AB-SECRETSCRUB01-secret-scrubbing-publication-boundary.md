---
id: TASK-AB-SECRETSCRUB01
title: Scrub secret-shaped strings at the evidence→publication boundary + secret-scan lint for tracked run-state artifacts
status: backlog
created: 2026-07-05T08:30:00Z
priority: high
tags: [autobuild, security, evidence, turn-tracking, publication-path]
complexity: 5
source: docs/retro/abl001-run3-honest-fail-and-credential-leak-2026-07-04.md
---

# Task: Anything the test suite prints is one chore commit from public — scrub it first

> Filed 2026-07-05 from the ABL-001 run-3 credential leak. Ready to implement
> (not design-first): the design decisions are made below; prior art exists.
>
> **Implemented 2026-07-05 (session following the 2026-07-04 handoff); this
> file is the tracking record.** Scrubber: `guardkit/lib/secret_scrub.py`
> (kept separate from `instrumentation/redaction.py`, whose blanket
> event-path semantics are pinned by its own tests). Wired at the two
> publication writers: `AutoBuildOrchestrator._serialize_turn_history`
> (scrub-before-truncate, so a truncation cut can never expose a partial
> secret — the incident's 14/32-char mechanism) and
> `ReviewSummaryGenerator.generate`. Lint:
> `tests/rules/test_no_secrets_in_tracked_artifacts.py` (placeholder
> heuristic + audited `KNOWN_BENIGN_LITERALS` for the llama-swap local dev
> key). Tests: `tests/unit/test_secret_scrub.py` (33).

## Description

ABL-001 run 3 (2026-07-04): a failing assertion compared a monkeypatched DSN
against config that read the **ambient** `FLEET_MEMORY_PG_DSN` — so pytest
printed the **live NAS store's credentials** in the expected-vs-actual diff.
That output then travelled the standard publication path:

```
pytest output → Coach evidence / turn-tracking JSON (.guardkit/autobuild/, gitignored)
  → task-md frontmatter turn history (tasks/backlog/...md — TRACKED)
    → chore commit "land stashed run state" (cbce5cf2)
      → public GitHub
```

14 of 32 password characters went public (pytest's diff truncation cut the
rest). Remediated at HEAD (`65dc82562`); password rotation + history-rewrite
decision are operator-owed (see the 2026-07-04 session handoff addendum).

Retro lesson 2 is the invariant this task implements: **"turn-tracking is a
publication path — treat evidence-file content as publish-equivalent."**

## Acceptance Criteria

- [x] AC-001: A `scrub_secrets`-style helper in guardkit (port/generalize the
      ABL-005 prior art, fleet-memory `fixture/dsn.py`) that redacts
      secret-shaped substrings: URL userinfo credentials
      (`scheme://user:pass@host` → `scheme://user:***@host`), and common token
      shapes (AWS key ids, `Bearer <jwt-ish>`, `sk-`/`ghp_`-style prefixes).
      Deterministic (same input → same redaction) so repeated writes and
      honesty comparisons stay stable. Localhost/127.0.0.1 credentials MAY be
      preserved (fixture DSNs are the documented, legitimate pattern).
- [x] AC-002: The scrubber is applied at every writer that produces TRACKED or
      operator-copyable artifacts embedding captured output: the task-md
      frontmatter turn-history writer (autobuild_state), review-summary
      writers, and any path that copies evidence content out of gitignored
      dirs into docs/ or tasks/. It is NOT applied to the in-memory/gitignored
      evidence the Coach verdicts on (the oracle must see real output; the
      boundary is publication, not verification).
- [x] AC-003: Fail-closed on scrubber errors at the publication boundary:
      if scrubbing raises, redact the whole embedded block with a marker and a
      WARNING — never write the unscrubbed content, never crash the loop.
- [x] AC-004: A repo lint in the style of `tests/rules/test_no_dead_task_id_references.py`:
      scan TRACKED files under `tasks/` and `docs/` for non-localhost URL
      userinfo credentials and token shapes; fail with file:line (values
      masked in the failure message). Seed an allowlist for the known-benign
      localhost fixture DSNs. This is the standing gate the retro asked for on
      "land stashed run state" chores.
- [x] AC-005: Regression tests: DSN in embedded test output is masked in the
      written task-md; localhost fixture DSN untouched; scrubber determinism;
      fail-closed path; the lint catches a planted non-localhost DSN in a
      tracked file (and the failure message itself contains no secret).

## Implementation Notes

- Publication writers: rg for the turn-history embedding in the task-md
  frontmatter writer (autobuild_state / state_bridge surface) and the
  review-summary writer (`review_summary.py`).
- Prior art to port: fleet-memory `fixture/dsn.py` `scrub_secrets` (ABL-005).
- The lint failure message MUST mask matched values (print host + file:line
  only) — a CI log is also a publication path.
- Out of scope: rewriting git history (operator decision), rotating
  credentials (ops), scanning gitignored evidence dirs (they are the
  legitimate raw record; the boundary is what leaves them).

## Regression constraints

- `.claude/rules/path-string-mismatch-is-not-dishonesty.md` /
  honesty comparisons: scrubbing must be deterministic and applied
  symmetrically wherever a claim and its evidence are both scrubbed, or not at
  all on the verification side — never scrub one side of a comparison the
  Coach performs.
- `.claude/rules/absence-of-failure-is-not-success.md`: a scrub failure is
  handled fail-closed (redact-all) — it must never silently drop the evidence
  block in a way a gate reads as "no output" → verdict change.
- The Coach remains read-only; scrubbing happens in orchestrator writers
  (feature-build-invariants.md).

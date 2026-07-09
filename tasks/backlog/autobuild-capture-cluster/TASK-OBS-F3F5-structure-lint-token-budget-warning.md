---
id: TASK-OBS-F3F5
title: Flip template structure-lint token budgets INFO→WARNING at the committed 32K-floor figure
task_type: feature
priority: medium
feature_id: FEAT-OBSC
wave: 1
implementation_mode: task-work
complexity: 2
dependencies: []
status: backlog
decision_of_record: M2 lint-budget rider (kickoff Step 4) per WS4 Amendment M3
created: 2026-07-09
---

# TASK-OBS-F3F5: Flip template structure-lint token budgets INFO→WARNING at the committed 32K-floor figure

## Description

The M2 template-structure lint (commit `ec1a5124`, PB-5/WS2,
`guardkit/templates/structure_lint.py`) shipped its per-section token-budget check
(check (c)) as **INFO/report-only** because no serving-window figure was committed —
the "32k" figure had circular provenance at ship time. WS4 has since committed the
figure (WS4 Amendment M3 / §Amendment A-B of
`ai-transition/docs/ws4-learning-flywheel-scope-and-build-plan-2026-07-07.md`):
**32K (32768 tokens) is the worst-case serving floor; a task-generating slice must fit
≤ ~20k tokens against it; the 64K seat is headroom, not the gate.**

The flip seam is already built: `lint_structure(text, *, serving_window_tokens:
Optional[int] = None)` (def `structure_lint.py:353`, signature at `:354`) branches
severity on the figure — `Severity.INFO if report_only else Severity.WARNING`
(`:279`) — and the CLI wiring is `_print_structure_lint` (`cli/template.py:38`,
called at `:144`), which invokes `lint_command_templates()` (`structure_lint.py:371`,
also accepting `serving_window_tokens`). This task threads the committed figure
through that call chain; it was anticipated in the code as "a future WS4 wiring
change, not this session" (`:277-278`).

Carried in this feature as the M2 rider (kickoff Step 4) rather than a separate lane
claim.

## Changes

1. Add a module-level committed-figure constant in `structure_lint.py` (e.g.
   `COMMITTED_SERVING_WINDOW_TOKENS = 32768` with the per-slice budget derivation
   documented), with a provenance comment citing WS4 Amendment M3 (§Amendment A/B)
   and the ~20k per-slice target.
2. Pass it from `cli/template.py:_print_structure_lint` through
   `lint_command_templates(serving_window_tokens=...)` (which forwards to
   `lint_structure`), flipping check (c) findings to WARNING.
3. **Exit-code neutrality is preserved**: the lint remains a second check that NEVER
   affects `guardkit template validate --deterministic`'s exit code (the ec1a5124
   contract). This flip changes severity display only.

## Acceptance Criteria

- [ ] AC-1: Section-token-budget findings on an oversized section render as WARNING
      (not INFO), and the finding text names the committed figure instead of
      "report-only (no committed serving-window figure — WS4)".
- [ ] AC-2: `guardkit template validate --deterministic` exit code is unchanged by
      budget findings — pinned by a test (a template with oversized sections exits
      exactly as before).
- [ ] AC-3: The constant's provenance comment cites WS4 Amendment M3 and states the
      64K-seat-is-headroom-not-the-gate rule, so the next reader doesn't "helpfully"
      raise it to 64K.
- [ ] AC-4: Existing structure-lint tests stay green; a new test covers the
      severity flip at the boundary.

## Test Strategy

Extend the structure-lint unit tests: same fixture, with/without the figure,
severity asserted each way; exit-code neutrality asserted via the CLI path.

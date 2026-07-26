---
complexity: 4
dependencies: []
feature_id: FEAT-SBHO
id: TASK-SBHO-001
implementation_mode: task-work
status: design_approved
task_type: feature
title: Budget the specialist/advisory prompt seams
wave: 1
---

# Budget the specialist/advisory prompt seams

The FEAT-8AD1 merge (58bc42b6) filed this follow-up: the code-reviewer specialist prompt
is a SEPARATE seam from the coach synthesis budget (3 live overflow receipts,
advisory/non-fatal) — same budget owed. Two seams are unbudgeted today:
guardkit/qa/review_seat.py::build_seat_messages (:319-338 — only the diff is capped at
60k; repo_context and the assembled payload are unbounded) and
guardkit/orchestrator/specialist_invocations.py::_build_code_reviewer_prompt (:886-936 —
a ~2000-char seed cap only). Mirror the _trim_synthesis_prompt pattern
(agent_invoker.py:3402-3665): env-tunable ceiling, protected sections, loud in-prompt
truncation marker + WARNING log, degrade never raise. Binding spec:
docs/specialist-budget-and-holdout-scope-and-buildplan.md §2.

## Acceptance Criteria
- [ ] GUARDKIT_REVIEW_SEAT_MAX_CHARS (default 300000) bounds the ASSEMBLED review-seat user message: a hermetic test builds an oversized payload (huge repo_context + big diff) and asserts the assembled message fits the budget, contains the loud truncation marker, trims repo_context before the diff, and never trims the instruction header or the finding-schema section
- [ ] GUARDKIT_SPECIALIST_PROMPT_MAX_CHARS (default 300000) backstops the final prompt for the specialist builders in specialist_invocations.py; the existing ~2000-char seed-cap behaviour is unchanged when under budget
- [ ] Advisory/non-fatal contracts unchanged: run_advisory_review still never raises and never returns blocking=True (existing tests pass unmodified); a WARNING log fires on any trim
- [ ] Zero net-new failures on the existing suite; both new tests are hermetic (no model calls)
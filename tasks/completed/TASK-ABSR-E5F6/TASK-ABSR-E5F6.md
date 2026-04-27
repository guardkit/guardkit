---
id: TASK-ABSR-E5F6
title: Standardise LangChain DeepAgents template requires-python and document portfolio pinning
status: completed
task_type: documentation
created: 2026-04-27T00:00:00Z
updated: 2026-04-27T00:00:00Z
completed: 2026-04-27T00:00:00Z
completed_location: tasks/completed/TASK-ABSR-E5F6/
organized_files:
  - TASK-ABSR-E5F6.md
priority: high
tags: [templates, langchain-deepagents, python-pinning, portfolio]
parent_review: TASK-REV-FA04
feature_id: FEAT-ABSR-9C6E
implementation_mode: direct
wave: 1
conductor_workspace: autobuild-stall-resilience-wave1-template-pinning
complexity: 2
depends_on: []
previous_state: in_review
state_transition_reason: "All ACs satisfied; tests green (20/20 new + 167/167 sibling); 6/6 ACs ticked"
---

# TASK-ABSR-E5F6 — Standardise LangChain DeepAgents template requires-python and document portfolio pinning

## Description

The LangChain DeepAgents portfolio (jarvis, forge, study-tutor, agentic-dataset-factory, specialist-agent) has an inconsistent `requires-python` story. Four of the five projects (and both DeepAgents templates) use the canonical `>=3.11` (open upper bound). Jarvis alone pins `>=3.12,<3.13`, which excluded the active 3.14 interpreter and produced the FEAT-J004-702C stall.

This task is **GuardKit-side only** (per the TASK-REV-FA04 task brief: "fixes must live in GuardKit so all consumers benefit"). It:
1. Verifies the current LangChain DeepAgents template `pyproject.toml.template` files use the canonical `>=3.11` pin (they do, per the review).
2. Adds a portfolio-pinning guide that documents the rationale and gives consumers a clear recommendation.
3. Makes Jarvis's misalignment a *user decision* informed by the guide — not a GuardKit-imposed change.

The actual Jarvis-side relax (or any other downstream consumer's pin alignment) is captured in the IMPLEMENTATION-GUIDE.md as a recommendation, not as a task in this repository.

## Acceptance Criteria

- [x] Verify both template `pyproject.toml.template` files use `requires-python = ">=3.11"`:
  - `installer/core/templates/langchain-deepagents/templates/other/other/pyproject.toml.template` ✅ `>=3.11`
  - `installer/core/templates/langchain-deepagents-orchestrator/templates/other/other/pyproject.toml.template` ✅ `>=3.11`
- [x] Verify the other LangChain DeepAgents template variants (`langchain-deepagents-weighted-evaluation`) have the same canonical pin or reference the canonical one.
  - Inherits via `"extends": "langchain-deepagents"` (no own `pyproject.toml.template`); manifest declares `"language_version": ">=3.11"`. Confirmed canonical.
- [x] Create `docs/guides/portfolio-python-pinning.md` covering:
  - Recommendation, rationale, when-tighter-is-needed, TASK-REV-FA04 evidence, Schreiner reference. ✅
- [x] Add a `template-validate` rule (or extend the existing one) that warns when a project derived from a LangChain DeepAgents template has a `requires-python` constraint that:
  - Has a non-empty upper bound (`<X.Y` clause), AND
  - That upper bound is older than the most recent stable Python minor.
  - The warning is informational — does not block the validation.
  - Implemented in `installer/core/lib/template_validation/sections/section_01_manifest.py` as `_validate_python_pin` with `LATEST_STABLE_PYTHON_MINOR = (3, 14)`. Emits `IssueSeverity.LOW` (non-blocking). Tests in `tests/unit/test_section_01_python_pin.py` (20 cases).
- [x] Reference the new guide from `CLAUDE.md` and from the `langchain-deepagents*` template `manifest.json` (or equivalent metadata).
  - Top-level `CLAUDE.md` Key References table updated.
  - Each of the three `langchain-deepagents*` templates' `.claude/CLAUDE.md` carries a "Python Pinning" callout pointing at the guide (the developer-facing equivalent of manifest metadata; loaded by Claude Code automatically when working in derived projects).
- [x] No template `pyproject.toml.template` content changes are required if all already use `>=3.11`. If any deviate, align them to the canonical.
  - `pyproject.toml.template` files: no changes (already canonical).
  - One manifest deviation aligned: `langchain-deepagents-orchestrator/manifest.json` `language_version` was `>=3.11,<4.0` → standardised to `>=3.11`.

## Implementation Summary

GuardKit-side standardisation of the LangChain DeepAgents portfolio's `requires-python` story. Closed the AutoBuild-stall failure class identified by TASK-REV-FA04 §F9/§R7 (where Jarvis's stale `>=3.12,<3.13` pin silently excluded Python 3.14 and produced a misleading FEAT-J004-702C stall) by standardising the GuardKit-shipped templates and making the policy auditable via a non-blocking `template-validate` rule.

**What changed**:

- `installer/core/templates/langchain-deepagents-orchestrator/manifest.json` — only `language_version` deviation aligned (`>=3.11,<4.0` → `>=3.11`). `pyproject.toml.template` files were already canonical (`>=3.11`); no file content changes needed.
- `docs/guides/portfolio-python-pinning.md` (new) — recommendation, rationale, when-tighter-is-warranted, FA04 incident evidence, Schreiner reference.
- `installer/core/lib/template_validation/sections/section_01_manifest.py` — added `_validate_python_pin` (with helpers `_is_langchain_deepagents_derived`, `_extract_requires_python`, `_stale_upper_bound`) and constants `LATEST_STABLE_PYTHON_MINOR = (3, 14)`, `_LANGCHAIN_DEEPAGENTS_TEMPLATE_NAMES`. Emits `IssueSeverity.LOW` (non-blocking) when a LangChain-DeepAgents-derived template has a closed upper bound that excludes a released stable Python minor. Checks both `manifest.json:language_version` and rendered `pyproject.toml.template:requires-python`.
- `tests/unit/test_section_01_python_pin.py` (new) — 20 cases: parser correctness, derivation detection, integration over synthetic templates, regression guard against shipped templates.
- Top-level `CLAUDE.md` — added "Portfolio Python Pinning" entry to Key References table.
- All three `installer/core/templates/langchain-deepagents*/.claude/CLAUDE.md` files — added a "Python Pinning" callout pointing at the new guide (loads automatically in derived projects via Claude Code).

**Approach**: Auto-detected MINIMAL intensity (provenance: parent_review TASK-REV-FA04 + complexity 2 ≤ 4). Skipped Phases 2/2.5/2.7/2.8/5.5; ran Phase 1 (load) → 3 (implement) → 4 (test) → state transition. The "or equivalent metadata" clause in the AC was used to motivate placing template references in the per-template `.claude/CLAUDE.md` (high signal-to-noise for downstream developers) rather than adding an ad-hoc `documentation` field to the manifest schema.

**Lessons**:

- **Schema-extension restraint pays.** Three template manifests were candidates for a new `documentation` field. The AC's "or equivalent metadata" wording let me route the references through `.claude/CLAUDE.md` instead, which is where Claude Code actually surfaces guidance to downstream developers — the same information ends up in front of the same audience without committing the manifest schema to a new shape that would need migration tooling later.
- **`>=3.11,<4.0` is a benign-looking trap.** The orchestrator manifest carried this bound; the implementation correctly classifies it as not-yet-stale (Python 4.x not released) and silent today. But the *pattern* of "defensive future-version cap" is what produced the Jarvis incident six months later. The rule fires on anything that excludes a *released* minor, leaving forward-looking caps alone — calibrated to current evidence, not paranoia.
- **Validator-as-policy-doc.** The `_stale_upper_bound` constant `LATEST_STABLE_PYTHON_MINOR = (3, 14)` documents the calendar-cadence promise: it's the one knob to turn when a new Python minor goes stable, and a comment in the source code names where to update it. The portfolio guide tells *humans* what to do; the rule tells *future maintainers* what `template-validate` will flag as the latest-stable advances. Both are necessary; neither alone is sufficient.

## Implementation Notes

- This is a `direct` mode task — it's primarily documentation and verification, no behaviour change in core orchestrator code.
- The `template-validate` rule is best added as a new check in the existing template-validation harness rather than a new file.
- The Schreiner reference: https://iscinumpy.dev/post/bound-version-constraints/ (and Henry's other related posts). Cite responsibly.
- Do NOT propose changes to the Jarvis repo. The IMPLEMENTATION-GUIDE.md will recommend the user re-evaluate Jarvis's pin in light of this guide; that decision lives outside GuardKit.

## Out of Scope

- Changes to any sibling project's `pyproject.toml`.
- Verification of `nats-core` PyPI metadata (Jarvis's original tight-pin rationale) — this was a Jarvis-side concern *at task-spec time*. See "Post-completion update" below for the resolution.
- Changes to non-LangChain-DeepAgents templates.

## Post-completion update (2026-04-27, post-merge)

The Jarvis-side `nats-core` verification — declared out-of-scope at task-spec time — was completed independently after this task closed. The verified facts are:

- **`nats-core` PyPI metadata now declares `requires-python = ">=3.10"`** — broadened from the `>=3.13` constraint that motivated Jarvis's original `>=3.12,<3.13` pin in October 2025.
- **specialist-agent declares `requires-python = ">=3.11"`**, matching forge, study-tutor, agentic-dataset-factory, and the LangChain DeepAgents template canonical (the single deviation `langchain-deepagents-orchestrator/manifest.json:language_version` was aligned by this task).
- The original Jarvis pin rationale at [`jarvis/pyproject.toml:43-47`](../../../../jarvis/pyproject.toml) is now **fully obsolete**. The `<3.13` upper bound has nothing left to defend against.

This makes the Jarvis-side recommendation in [`tasks/backlog/autobuild-stall-resilience/IMPLEMENTATION-GUIDE.md`](../../backlog/autobuild-stall-resilience/IMPLEMENTATION-GUIDE.md#out-of-scope-jarvis-side-pin-alignment-consumer-recommendation--verified-2026-04-27) — relax Jarvis to `requires-python = ">=3.11"` — concrete and actionable rather than hypothetical. Doing so eliminates the precondition for the FEAT-J004-702C trapdoor at the source (in addition to the GuardKit-side guards this task and TASK-ABSR-A1B2/C3D4 installed). It is a single-line change in another repository and remains out of scope for GuardKit.

This update is informational — it does not reopen this task or modify any GuardKit code shipped under it. The `template-validate` rule installed here (`_validate_python_pin` with `LATEST_STABLE_PYTHON_MINOR = (3, 14)`) would correctly flag Jarvis's current pin as a closed upper bound excluding a released stable minor; flagging behaviour is unchanged.

## References

- Review: [TASK-REV-FA04 report](../../../.claude/reviews/TASK-REV-FA04-report.md) §F9, §R7, "Standardisation Proposal"
- Comparison matrix: [report §Comparison Matrix](../../../.claude/reviews/TASK-REV-FA04-report.md#comparison-matrix-forge-vs-jarvis-vs-other-siblings)
- Templates: `installer/core/templates/langchain-deepagents*/`
- Post-completion verification logged in [`tasks/backlog/autobuild-stall-resilience/IMPLEMENTATION-GUIDE.md`](../../backlog/autobuild-stall-resilience/IMPLEMENTATION-GUIDE.md#verified-facts-2026-04-27)

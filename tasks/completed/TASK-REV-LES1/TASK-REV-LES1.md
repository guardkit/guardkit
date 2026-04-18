---
id: TASK-REV-LES1
title: Review cross-agent lessons (LES1) for langchain-deepagents templates
status: completed
created: 2026-04-18T00:00:00Z
updated: 2026-04-18T00:00:00Z
completed: 2026-04-18T00:00:00Z
completed_location: tasks/completed/TASK-REV-LES1/
priority: high
tags: [review, templates, langchain-deepagents, mcp, nats, deployment-lessons]
task_type: review
review_mode: architectural
review_depth: standard
decision_required: true
complexity: 0
test_results:
  status: pending
  coverage: null
  last_run: null
review_results:
  mode: architectural
  depth: standard
  score: 68
  findings_count: 13
  recommendations_count: 12
  decision: implement
  report_path: .claude/reviews/TASK-REV-LES1-review-report.md
  completed_at: 2026-04-18T00:00:00Z
  implementation_feature: FEAT-LTL1
  implementation_path: tasks/backlog/langchain-template-lessons/
---

# Task: Review cross-agent lessons (LES1) for langchain-deepagents templates

## Description

Evaluate the LES1 cross-agent lessons document from the specialist-agent MacBook
walkthrough (TASK-REV-B8E4) and decide which lessons must be back-ported into each
of GuardKit's three `langchain-deepagents*` templates. One template
(`langchain-deepagents-weighted-evaluation`) has already received a partial
update in a prior review round; the remaining two templates
(`langchain-deepagents`, `langchain-deepagents-orchestrator`) have not yet been
assessed against LES1. This review determines the delta and produces a
prioritised implementation backlog.

## Why this task exists

Deploying `specialist-agent` on a clean MacBook (via MCP + NATS to Claude
Desktop) exposed a cluster of systemic failures that are **not specific to
specialist-agent** — they are the result of patterns shared by any agent
built from the langchain-deepagents template family:

- MCP stdio banner emitted on stdout (protocol violation)
- `serve-nats` registered commands in tests but never subscribed in production
- Provider resolution hard-coded to Claude; `langchain-openai` missing from extras
- `Dockerfile` `pip install .` drifting from documented `pip install .[providers]`
- `.env` placeholder keys silently overriding real shell-env keys
- Synchronous `await` on generation loops that exceed the 240s MCP timeout
- Multi-role dispatch tables registering commands only for one role
- Listed handlers with missing core-layer methods (schema → adapter → core → orch gap)
- `docker compose down` silently no-op'ing against stale worktree labels
- Fresh-volume NATS provisioning treated as optional rather than required

These failures map onto "six parity surfaces" in the LES1 doc: **Transport,
Provider, Packaging, Handler, Tooling, Ops**. Each surface has at least one
concrete gate that any agent built from our templates must pass before first
merge. If those gates are not encoded in the templates themselves, every
downstream agent (jarvis, forge, study-tutor, and future agents) will re-hit
the same class of bugs.

## Reference material

**Primary inputs** (read in this order):

1. `/Users/richardwoollcott/Projects/appmilla_github/specialist-agent/docs/reference/cross-agent-lessons-from-specialist-agent.md`
   — The LES1 canonical lessons doc. 8 lesson clusters, the 6-surface parity
   matrix, and a 22-item per-agent checklist. **This is the primary input.**

2. User-cited: `.claude/reviews/TASK-REV-8A08-review-report.md`
   — User referenced this as the "previous weighted-evaluation template update"
   review. **Verify before relying on it** — inspection during task creation
   shows 8A08 is actually about a FEAT-486D AutoBuild stall (partial API
   outage), not a langchain template update. The real template-update
   reviews appear to be **TASK-REV-4F71** and **TASK-REV-32D2** (both
   reference `langchain-deepagents-weighted-evaluation`). The reviewer
   should confirm which report actually documents the prior template update
   and use that as the baseline for "what has already been done."

3. User-cited: `.claude/reviews/TASK-REV-B8E4-walkthrough-log.md`
   — User cited this for context; **file not found at that path** during
   task creation. It is referenced from the LES1 doc's frontmatter. The
   reviewer should (a) search the specialist-agent repo for the walkthrough
   log (likely `specialist-agent/docs/reviews/` or `.claude/reviews/`),
   and (b) note that the key walkthrough evidence is already distilled into
   the LES1 doc — the walkthrough log is useful for depth, not essential
   for the decision.

4. Recent commit `dfa8090d` — "reviews and updates to
   langchain-deepagents-weighted-eval template". Use `git log` / `git show`
   on this SHA to see exactly which files changed in the prior update round
   — this is the ground truth for what has been applied to that template so far.

**Target templates** (all three live under
`installer/core/templates/`):

- `langchain-deepagents-weighted-evaluation/` — partially updated (baseline)
- `langchain-deepagents/` — not yet assessed against LES1
- `langchain-deepagents-orchestrator/` — not yet assessed against LES1

## Scope

**In scope**:

1. For each of the 8 LES1 lesson clusters, determine applicability to each
   target template.
2. For each of the 6 parity surfaces, audit the current template contents
   (manifest.json, settings.json, agents/, docs/, lib/, templates/ — whichever
   exist per template) and record: `already-addressed` / `partially-addressed`
   / `gap`.
3. For the weighted-evaluation template, diff the prior update round
   (commit `dfa8090d` plus any earlier review-driven commits) against the
   full LES1 checklist and report residual gaps.
4. For the other two templates, produce a full gap list.
5. Group findings by severity: **blocker** (template ships a known footgun),
   **high** (missing guardrail that will reliably bite downstream agents),
   **medium** (generalisable improvement), **low** (nice-to-have).
6. Propose a concrete sub-task list for implementation, grouped by template
   and sequenced so shared infrastructure work (e.g. `[providers]` extras
   pattern, MCP stdio wrapper, NATS provisioning script) is done once.
7. Decide whether any lessons apply to templates **outside** the
   langchain-deepagents family (e.g. `fastapi-python`, `python-library`,
   `nats-asyncio-service`) — the LES1 doc is explicitly scoped to agent
   templates, but some lessons (MCP stdio discipline, `.env` hygiene,
   `docker compose` orphans) are transport-agnostic.

**Out of scope**:

- Actually implementing the changes — this is a review-and-plan task. The
  implementation will be split into one or more `/task-work` tasks per
  the decision at the end of this review.
- Revisiting specialist-agent itself — that agent is the source of truth;
  this task back-ports lessons outward, not inward.
- Refactoring unrelated aspects of the templates.

## Acceptance Criteria

- [ ] LES1 doc read in full; 6-surface matrix summarised in plain English
  at the top of the review report.
- [ ] Prior weighted-evaluation update round identified (correct review
  file + commit) and its scope documented — so "what has been done" is
  unambiguous.
- [ ] Each of the 3 langchain-deepagents templates audited against the
  22-item per-agent checklist (LES1 doc §"Per-agent pre-implementation
  checklists"); results in a table with one column per template.
- [ ] Gap list produced per template, grouped by severity (blocker / high /
  medium / low).
- [ ] Shared-infrastructure work identified — any gate that applies to ≥2
  templates should be designed once and reused.
- [ ] Decision on applicability to non-langchain-deepagents templates:
  either a short "no, scope contained" justification, or a list of
  extractable lessons for the wider template set.
- [ ] Prioritised sub-task list produced for implementation, with each
  sub-task sized to fit a single `/task-work` invocation (complexity ≤6
  preferred).
- [ ] Reviewer records whether the `specialist-agent` walkthrough log
  (TASK-REV-B8E4) was located; if so, one-paragraph summary of any
  evidence not already captured in the LES1 doc.
- [ ] Final output: `.claude/reviews/TASK-REV-LES1-review-report.md`
  following the standard review-report format, plus a decision checkpoint
  (Accept / Implement / Revise / Cancel).

## Review Mode

Recommended: `/task-review TASK-REV-LES1 --mode=architectural --depth=standard`

Rationale: the decision touches architecture (transport parity, provider
resolution, packaging), not just code quality. The architectural-reviewer
agent is the right lens for the 6-surface parity audit.

## Deliverables

1. **Review report** at `.claude/reviews/TASK-REV-LES1-review-report.md`
   containing:
   - Executive summary (≤10 lines)
   - LES1 6-surface matrix → per-template applicability table
   - 22-item checklist → per-template status table
   - Gap list (blocker/high/medium/low) with file-path evidence
   - Prior-work reconciliation (what commit `dfa8090d` and its preceding
     review(s) actually delivered to the weighted-evaluation template)
   - Prioritised implementation plan (sub-task list with proposed IDs)
   - Cross-template extraction opportunities
   - Decision checkpoint

2. **Optional appendix**: proposed sub-task stubs in
   `tasks/backlog/langchain-template-lessons/` (a folder following the
   feature-build subfolder convention) if the reviewer deems the scope
   large enough to warrant `/feature-build` orchestration.

## Notes on reference-file discrepancies

During task creation, the following discrepancies in the user's cited
references were noted — the reviewer should resolve these first:

- `TASK-REV-8A08-review-report.md` exists but is about a **FEAT-486D
  AutoBuild stall** (partial upstream API outage). It does **not** document
  a langchain-deepagents-weighted-evaluation template update. Candidate
  replacements — grep-confirmed to reference that template — are
  **TASK-REV-4F71-review-report.md** and **TASK-REV-32D2-review-report.md**.
- `TASK-REV-B8E4-walkthrough-log.md` at the cited path does **not exist in
  this repo**. The LES1 doc's frontmatter references it as a sibling of
  the lessons doc, suggesting it lives in the specialist-agent repo
  (`specialist-agent/docs/reviews/` or similar). The reviewer should
  search there; if not found, proceed with the LES1 doc alone since it
  was written specifically to distil the walkthrough's findings.

## Next Steps

1. Execute review: `/task-review TASK-REV-LES1 --mode=architectural`
2. At checkpoint:
   - **[A]ccept** — file findings, no immediate implementation
   - **[I]mplement** — spawn implementation sub-tasks per template
   - **[R]evise** — deeper audit (e.g. include non-langchain templates)
   - **[C]ancel** — discard if lessons turn out to be fully encoded already
3. Complete review: `/task-complete TASK-REV-LES1`

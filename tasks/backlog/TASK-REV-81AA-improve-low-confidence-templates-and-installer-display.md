---
id: TASK-REV-81AA
title: Improve low-confidence templates and standardise installer template display
status: review_complete
created: 2026-04-03T22:30:00Z
updated: 2026-04-03T23:15:00Z
review_results:
  mode: architectural
  depth: standard
  score: 62
  findings_count: 12
  recommendations_count: 14
  report_path: .claude/reviews/TASK-REV-81AA-review-report.md
priority: medium
tags: [template, confidence-score, installer, display]
task_type: review
review_mode: architectural
review_depth: standard
complexity: 5
---

# Task: Improve low-confidence templates and standardise installer template display

## Description

Several templates have low confidence scores and the installer's "Available Templates" listing has inconsistencies. This review covers two areas:

1. **Low-confidence template improvement** — Two templates score below 75/100 and need metadata/content quality improvements to bring them up to the standard of other builtins.
2. **Installer display standardisation** — The template listing in `install.sh` has missing descriptions, missing ratings, and no label explaining what the score means.

## Review Scope

### 1. Low-Confidence Templates

#### nats-asyncio-service (confidence: 70.0 / 7.0 out of 10)

- [ ] Review manifest.json for accuracy and completeness
- [ ] Review settings.json layer mappings and conventions
- [ ] Review agent quality and coverage
- [ ] Review CLAUDE.md and rules for completeness
- [ ] Identify specific improvements to raise confidence above 80
- [ ] Compare against high-scoring templates (fastapi-python at 9+) for gap analysis

#### langchain-deepagents-orchestrator (confidence: 68.33 / 6.8 out of 10)

- [ ] Review manifest.json for accuracy and completeness
- [ ] Review settings.json conventions
- [ ] Review agent quality and coverage
- [ ] Review CLAUDE.md and rules for completeness
- [ ] Identify specific improvements to raise confidence above 80
- [ ] Compare against langchain-deepagents (9.7) for gap analysis — orchestrator extends this template

### 2. Installer Display Issues

#### Missing descriptions

- [ ] `common` — shows no description (is this even user-facing? should it be hidden?)
- [ ] `mcp-typescript` — has no confidence rating in description (manifest has no `confidence_score` field)

#### Missing confidence_score in manifest

- [ ] `mcp-typescript/manifest.json` — add `confidence_score` field

#### Add "Confidence Rating" label

Currently the scores appear as bare numbers like `(9+/10)` or `(7.0/10)` with no explanation. Users may interpret this as a quality/recommendation rating rather than an AI analysis confidence metric.

- [ ] Add a label or legend to the installer output explaining what the score means, e.g.:
  ```
  Available Templates (confidence rating = AI analysis accuracy, not quality):
  ```
  Or append to each line:
  ```
  • fastapi-python - FastAPI backend with layered architecture (confidence: 9+/10)
  ```

#### Consider dynamic score reading

- [ ] Currently scores are hardcoded in `install.sh` case statements — evaluate whether to read `confidence_score` from `manifest.json` dynamically instead, so scores stay in sync automatically

## Decision Points

1. **Label format**: "confidence: X/10" vs "(AI confidence: X/10)" vs separate legend line?
2. **Common template**: Should it appear in the listing or be filtered out as internal-only?
3. **Dynamic vs hardcoded scores**: Is the shell complexity worth the maintenance benefit?
4. **Target score**: What minimum confidence score should builtins have? (suggest 75+)

## Acceptance Criteria

- [ ] Both low-confidence templates have actionable improvement recommendations
- [ ] All templates in installer listing have descriptions and confidence ratings
- [ ] Score display includes a label explaining what it means
- [ ] Recommendation on dynamic vs hardcoded score display

## References

- Installer template listing: `installer/scripts/install.sh` lines 1646-1686
- Template manifests: `installer/core/templates/*/manifest.json`
- Parent review context: TASK-REV-DF07 (template registration review)

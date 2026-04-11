---
id: TASK-TSE-8A1C
title: Fix stale EXPECTED_TEMPLATES set in test_seed_enrichment.py
status: backlog
created: 2026-04-11T12:00:00Z
updated: 2026-04-11T12:00:00Z
priority: medium
tags: [tests, cleanup, templates, seed-enrichment, technical-debt]
parent_review: TASK-REV-D0C1
implementation_mode: task-work
complexity: 3
depends_on: []
---

# Task: Fix stale EXPECTED_TEMPLATES set in test_seed_enrichment.py

## Description

The `EXPECTED_TEMPLATES` constant in [tests/knowledge/test_seed_enrichment.py:36-44](../../tests/knowledge/test_seed_enrichment.py#L36) is stale — it currently lists only 7 templates but the filesystem contains 13+ builtin templates. This was surfaced during the TASK-REV-D0C1 review of the `dotnet-railway-fastendpoints` registration.

## Current State

```python
EXPECTED_TEMPLATES = {
    "default",
    "fastapi-python",
    "fastmcp-python",
    "mcp-typescript",
    "nextjs-fullstack",
    "react-fastapi-monorepo",
    "react-typescript",
}
```

## Missing Templates (verified via `ls installer/core/templates/`)

- `python-library`
- `nats-asyncio-service`
- `langchain-deepagents`
- `langchain-deepagents-orchestrator`
- `langchain-deepagents-weighted-evaluation`
- `dotnet-railway-fastendpoints` (once TASK-DRF-002 lands)

## Acceptance Criteria

- [ ] **Investigate the test's purpose** first — read the test file to understand what assertions depend on `EXPECTED_TEMPLATES`. The fix strategy depends on whether the set is used as:
  - **(a) A snapshot of what should be present** → update the set to include all templates, including `dotnet-railway-fastendpoints` if TASK-DRF-002 has landed by the time this task runs.
  - **(b) A subset used to parameterize specific assertions** → leave the set alone, but document in a comment why it's a subset and what the broader template list is.
  - **(c) A genuinely obsolete constant** → delete it and replace with dynamic discovery.

- [ ] **Consider auto-discovery** as a better long-term fix: scan `installer/core/templates/` for directories containing `manifest.json` at test-collection time, so the test never goes stale again. Reference: `guardkit/knowledge/seed_templates.py:40` already implements `_discover_templates()` — the test could reuse that helper.

- [ ] **If updating to a hardcoded list**: include all current templates and add a comment at the top of the set indicating it must be kept in sync with `installer/core/templates/` or point to the auto-discovery approach as a TODO.

- [ ] **Run the test suite** to confirm no regressions:
  ```bash
  pytest tests/knowledge/test_seed_enrichment.py -v
  ```

- [ ] **Exclude `common/`** — `installer/core/templates/common/` is shared resources, not a template. Any discovery logic must filter it out.

## Rationale

- Every new template registration risks this test silently passing without covering the new template.
- Auto-discovery eliminates this class of technical debt entirely.
- This is a known follow-up flagged by [TASK-REV-D0C1 review report §6](../../.claude/reviews/TASK-REV-D0C1-review-report.md).

## Notes

- **Not blocking** for TASK-DRF-001/002/003/004. This can run independently, before or after the dotnet template registration.
- If auto-discovery is chosen, confirm `_discover_templates()` behavior handles the `guardkit.marker.json` file and any non-template directories (`common/`).

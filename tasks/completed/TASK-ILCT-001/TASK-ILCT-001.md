---
id: TASK-ILCT-001
title: Enrich nats-asyncio-service manifest and settings
status: completed
completed: 2026-04-03T23:45:00Z
completed_location: tasks/completed/TASK-ILCT-001/
created: 2026-04-03T23:15:00Z
priority: high
tags: [template, nats-asyncio-service, manifest, confidence-score]
parent_review: TASK-REV-81AA
feature_id: FEAT-ILCT
implementation_mode: task-work
wave: 1
complexity: 3
depends_on: []
---

# Task: Enrich nats-asyncio-service manifest and settings

## Description

The nats-asyncio-service template (confidence 70.0/100) is missing several metadata fields that high-confidence templates include. This task adds the missing fields to bring the manifest up to the standard established by fastapi-python (95) and fastmcp-python (90).

## Changes Required

### manifest.json

1. **Add `quality_scores` object** — assess the template and add scores:
   ```json
   "quality_scores": {
       "solid_compliance": <score>,
       "dry_compliance": <score>,
       "yagni_compliance": <score>,
       "test_coverage": <score>,
       "documentation": <score>
   }
   ```

2. **Add production metadata flags**:
   ```json
   "production_ready": true,
   "learning_resource": true,
   "reference_implementation": true
   ```

3. **Add framework versions** from exemplar requirements (replace `null` values):
   ```json
   {"name": "FastStream", "version": ">=0.5.0", "purpose": "core"}
   ```

4. **Add `requires` entry for agent** if not already present

### settings.json

5. **Add `responsibilities` to each layer_mapping** — describe what each layer does:
   ```json
   "Entry Point": {
       "name": "Entry Point",
       "directory": "{{project_name}}/",
       "responsibilities": ["Application bootstrap", "Broker initialization"]
   }
   ```

6. **Add examples to empty naming convention arrays** (class, constant)

## Acceptance Criteria

- [x] manifest.json has `quality_scores` with 5 dimensions
- [x] manifest.json has `production_ready`, `learning_resource`, `reference_implementation`
- [x] All framework entries have version constraints (no null)
- [x] settings.json layer_mappings have responsibilities
- [x] settings.json naming_conventions have examples for all types
- [x] manifest.json is valid JSON

## References

- High-confidence reference: `installer/core/templates/fastmcp-python/manifest.json`
- Template under review: `installer/core/templates/nats-asyncio-service/manifest.json`
- Review report: `.claude/reviews/TASK-REV-81AA-review-report.md` (Findings 1, 2, 4)

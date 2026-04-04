---
id: TASK-ILCT-002
title: Enrich langchain-deepagents-orchestrator manifest and settings
status: completed
updated: 2026-04-03T23:50:00Z
completed: 2026-04-03T23:50:00Z
created: 2026-04-03T23:15:00Z
priority: high
tags: [template, langchain-deepagents-orchestrator, manifest, confidence-score]
parent_review: TASK-REV-81AA
feature_id: FEAT-ILCT
implementation_mode: task-work
wave: 1
complexity: 3
depends_on: []
---

# Task: Enrich langchain-deepagents-orchestrator manifest and settings

## Description

The langchain-deepagents-orchestrator template (confidence 68.33/100) has several structural metadata issues beyond the common missing fields. The architecture label is a generic fallback, patterns are generic names instead of DeepAgents-specific, and layer mappings cover only 2 of 5+ actual layers.

## Changes Required

### manifest.json

1. **Add `quality_scores` object** — assess and add scores

2. **Add production metadata flags** (`production_ready`, `learning_resource`, `reference_implementation`)

3. **Fix architecture label**: `"Standard Structure"` → `"Two-Model Pipeline Orchestrator"`

4. **Replace generic patterns** with DeepAgents-specific patterns from the rule files:
   ```json
   "patterns": [
       "Two-Model Orchestration",
       "SubAgent Composition",
       "Domain Prompt Injection",
       "Factory Function Agents",
       "Config-Driven Model Selection",
       "Defensive Fallback Chain"
   ]
   ```

5. **Populate `requires`**:
   ```json
   "requires": ["deepagents>=0.4.11", "langchain>=1.2.11", "langgraph>=0.2"]
   ```

6. **Populate `compatible_with`**:
   ```json
   "compatible_with": ["langchain-deepagents"]
   ```

### settings.json

7. **Add layer mappings** for actual project structure (Agents, Tools, Prompts, Config, Domains) — currently only Infrastructure and Shared

8. **Add `responsibilities`** to all layer mappings

9. **Add examples** to empty naming convention arrays (class, constant)

## Acceptance Criteria

- [x] manifest.json architecture is "Two-Model Pipeline Orchestrator"
- [x] manifest.json patterns reflect actual DeepAgents patterns (not generic)
- [x] manifest.json has `quality_scores`, production flags
- [x] manifest.json `requires` and `compatible_with` populated
- [x] settings.json has 5+ layer mappings with responsibilities
- [x] All JSON is valid

## References

- Parent template reference: `installer/core/templates/langchain-deepagents/manifest.json` (96.67 confidence)
- Pattern rule files: `installer/core/templates/langchain-deepagents-orchestrator/.claude/rules/patterns/`
- Review report: `.claude/reviews/TASK-REV-81AA-review-report.md` (Findings 1, 2, 5, 6, 7, 8)

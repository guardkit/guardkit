---
id: TASK-TI-011
title: Canonical pipeline module (normalize -> extract -> validate -> write)
status: backlog
created: 2026-03-27T22:00:00Z
updated: 2026-03-27T22:00:00Z
priority: p3
tags: [template, adversarial, pipeline]
complexity: 4
parent_review: TASK-REV-TRF12
feature_id: FEAT-TI
wave: 4
implementation_mode: task-work
depends_on: [TASK-TI-001, TASK-TI-009]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Canonical Pipeline Module

## Description

Create the canonical processing pipeline that enforces the correct order: normalize -> extract -> validate -> write. This prevents the pipeline ordering bugs (TRF-020) and ensures all processing steps are applied consistently.

## What to Build

### Pipeline Stages (in order)
1. **Normalize**: Think block tag normalization, content format handling (string vs block-list)
2. **Extract**: JsonExtractor 5-strategy cascade (from TI-001)
3. **Validate**: Domain validation with type coercion (from TI-005)
4. **Write**: Orchestrator-gated write (from TI-003)

### Pipeline Class
```python
class ContentPipeline:
    def __init__(self, extractor: JsonExtractor, validator: DomainValidator, logger: ObservabilityLogger):
        ...

    def process(self, raw_content: str | list) -> PipelineResult:
        normalized = self.normalize(raw_content)    # Stage 1
        extracted = self.extract(normalized)         # Stage 2
        validated = self.validate(extracted)         # Stage 3
        return PipelineResult(content=validated, stages=self._stage_log)

    # Each stage logs content length via ObservabilityLogger
```

### Stage Hooks
- `on_stage_complete(stage_name, input_length, output_length)` — observability
- `on_stage_failure(stage_name, error, content_preview)` — error context
- Pipeline is extensible: custom stages can be inserted between standard ones

## Acceptance Criteria

- [ ] Four stages in canonical order (normalize, extract, validate, write)
- [ ] Pipeline enforces order — cannot skip or reorder stages
- [ ] Each stage logs input/output length via observability scaffold
- [ ] Stage failure provides error context (head + tail + length)
- [ ] Pipeline is composable (add custom stages)
- [ ] Unit tests for each stage in isolation and full pipeline
- [ ] Regression test: TRF-020 scenario (normalize after extract fails, normalize before extract succeeds)

## Effort Estimate

1 day

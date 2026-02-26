---
id: TASK-FIX-VL07
title: Add semantic matching config option and enhance synthetic promise quality
status: backlog
created: 2026-02-26T13:00:00Z
updated: 2026-02-26T13:00:00Z
priority: medium
tags: [autobuild, vllm, enhancement, semantic-matching, synthetic-promises, coach-validator]
complexity: 5
task_type: enhancement
parent_review: TASK-REV-8A94
feature_id: FEAT-VL01
wave: 3
implementation_mode: task-work
dependencies: [TASK-FIX-VL02]
---

# Task: Add semantic matching config option and enhance synthetic promise quality

## Description

This task addresses two related improvements to the coach validation pipeline:

### Part A: Semantic matching configuration (P5)

The coach validator's `matching_strategy: text` requires Jaccard keyword overlap ≥70% between acceptance criteria text and `requirements_met` entries. Local models like Qwen3 often paraphrase criteria differently than Anthropic models, causing legitimate work to be rejected.

A configurable `matching_strategy` option would allow selecting `semantic` matching for local backends where text matching is unreliable.

### Part B: Enhanced synthetic promise generation (P3b)

When Fix 5 generates synthetic file-existence promises, the current pattern matching is basic (file path regex extraction from AC text). Enhancing the regex patterns and adding directory-structure matching would improve coverage for tasks where the agent creates files but uses different naming conventions.

## Requirements

### Part A: Semantic Matching Config
- Add `matching_strategy` configuration option: `text` (default), `semantic`, `auto`
- `auto` mode: use `text` for Anthropic API, `semantic` for localhost backends
- `semantic` mode: lower Jaccard threshold to 50% AND add fuzzy keyword matching
- Configuration available via CLI flag and environment variable

### Part B: Enhanced Synthetic Promises
- Improve regex patterns in `generate_file_existence_promises()` to catch more file references
- Add directory-structure matching (e.g., AC says "Create models directory" → match `models/` in files_created)
- Add partial path matching for common patterns (e.g., `alembic/versions/*.py`)
- Improve promise confidence scoring based on match quality

## Acceptance Criteria

- `matching_strategy` config option available with values: `text`, `semantic`, `auto`
- `auto` mode selects strategy based on `ANTHROPIC_BASE_URL`
- `semantic` mode uses lower Jaccard threshold (50%) with fuzzy keyword matching
- Enhanced regex patterns in `generate_file_existence_promises()` capture more file references
- Directory-structure matching works for "Create X directory" style ACs
- Partial path matching works for glob-like patterns in ACs
- Existing `text` matching behaviour unchanged when explicitly selected
- Unit tests cover semantic matching fallback and enhanced regex patterns
- Integration test verifies vLLM-style paraphrased requirements are matched

## Files to Modify

- `guardkit/orchestrator/quality_gates/coach_validator.py` (matching strategy config)
- `guardkit/orchestrator/synthetic_report.py` (enhanced regex and directory matching)
- `guardkit/orchestrator/feature_orchestrator.py` (pass config to coach)

## Implementation Notes

### Part A: Matching Strategy

```python
# In coach_validator.py
class CoachValidator:
    def __init__(self, ..., matching_strategy: str = "text"):
        self.matching_strategy = matching_strategy

    def _get_jaccard_threshold(self) -> float:
        if self.matching_strategy == "semantic":
            return 0.50  # Lower threshold for paraphrased criteria
        return 0.70  # Default strict text matching

    def _match_by_text(self, requirements_met, acceptance_criteria):
        threshold = self._get_jaccard_threshold()
        # ... existing logic with configurable threshold ...
```

### Part B: Enhanced Synthetic Promises

```python
# In synthetic_report.py - additional patterns
DIRECTORY_PATTERNS = [
    r'[Cc]reate\s+(?:a\s+)?(\w+(?:/\w+)*)\s+directory',
    r'[Ss]et\s+up\s+(\w+(?:/\w+)*)\s+(?:folder|directory|structure)',
]

GLOB_PATTERNS = [
    r'([\w./\-]+/\*\.[\w]{1,5})',  # path/*.ext
    r'([\w./\-]+/\*\*/\*\.[\w]{1,5})',  # path/**/*.ext
]
```

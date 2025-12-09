---
id: TASK-FIX-PD04
title: Fix progressive disclosure section name mapping in applier.py
status: completed
task_type: implementation
created: 2025-12-09
completed: 2025-12-09
completed_location: tasks/completed/TASK-FIX-PD04/
priority: high
tags: [progressive-disclosure, agent-enhance, bug-fix]
related_tasks: [TASK-REV-AB89, TASK-FIX-PD03, TASK-FIX-DBFA]
estimated_complexity: 3
organized_files: [TASK-FIX-PD04.md]
---

# TASK-FIX-PD04: Fix Progressive Disclosure Section Name Mapping

## Summary

Fix the section name mapping in `applier.py` so that AI-generated content is correctly routed to extended files. Currently, AI returns sections named `examples` and `related_templates`, but these are not recognized by the applier's `EXTENDED_SECTIONS` constant or `section_order` list, causing the extended file to be nearly empty.

## Background

From TASK-REV-AB89 code quality review:
- Extended file has only 11 lines instead of 50+
- AI-generated content (`examples`, `related_templates`) was lost
- Root cause: `_build_extended_content()` only outputs sections matching its hardcoded `section_order` list

## Acceptance Criteria

### AC1: Update EXTENDED_SECTIONS Constant
- [x] Add `examples` to EXTENDED_SECTIONS list (line ~48-56)
- [x] Add `related_templates` to EXTENDED_SECTIONS list
- [x] Consider adding other common AI section names

### AC2: Update section_order in _build_extended_content()
- [x] Add `examples` to section_order (line ~665-673)
- [x] Add `related_templates` to section_order
- [x] Ensure order is logical (templates first, then examples)

### AC3: Fix Duplicate Loading Instruction
- [x] Add deduplication check in `_build_core_content()` before appending loading instruction
- [x] Check if "## Extended Documentation" already exists in merged content

### AC4: Preserve AI-Generated Boundaries
- [x] In `_merge_content()`, detect if existing boundaries are generic
- [x] Prioritize AI boundaries over generic fallback via `is_generic_boundaries()`
- [x] Only use generic boundaries if AI boundaries are empty/missing

### AC5: Integration Test
- [x] Verified EXTENDED_SECTIONS contains `examples` and `related_templates`
- [x] Verified section_order includes new sections in correct order
- [x] Verified duplicate loading instruction check in place
- [x] Verified `is_generic_boundaries()` function and helper methods exist

## Implementation Details

### File: installer/global/lib/agent_enhancement/applier.py

**Change 1: Update EXTENDED_SECTIONS (lines 48-56)**
```python
EXTENDED_SECTIONS = [
    'detailed_examples',
    'examples',              # AI may use this instead of detailed_examples
    'best_practices',
    'anti_patterns',
    'cross_stack',
    'mcp_integration',
    'troubleshooting',
    'technology_specific',
    'related_templates',     # AI-generated template references
]
```

**Change 2: Update section_order (lines 665-673)**
```python
section_order = [
    'related_templates',     # Templates first for context
    'detailed_examples',
    'examples',              # AI alternate name
    'best_practices',
    'anti_patterns',
    'cross_stack',
    'mcp_integration',
    'troubleshooting',
    'technology_specific',
]
```

**Change 3: Fix duplicate loading instruction (around line 612)**
```python
if has_extended and "## Extended Documentation" not in merged_content:
    loading_instruction = self._format_loading_instruction(agent_name)
    merged_content = self._append_section(merged_content, loading_instruction)
```

**Change 4: Preserve AI boundaries in apply_with_split() (around line 380)**
```python
# Step 3: Build and write core content - preserve AI boundaries
# Check if AI provided boundaries before using generic
has_ai_boundaries = (
    'boundaries' in core_sections and
    core_sections.get('boundaries', '').strip()
)
```

## Test Verification

After implementation, re-run the test scenario:
```bash
/agent-enhance docs/reviews/progressive-disclosure/svelte5-component-specialist --hybrid
```

Expected results:
- Extended file: 50+ lines with examples and related_templates
- Core file: No duplicate "## Extended Documentation" sections
- Boundaries: Svelte 5-specific (from AI), not generic

## Review Report Reference

Full analysis: [.claude/reviews/TASK-REV-AB89-review-report.md](../../.claude/reviews/TASK-REV-AB89-review-report.md)

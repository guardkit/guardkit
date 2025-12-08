---
id: TASK-PD-026
title: Template agent validation and metrics capture
status: completed
created: 2025-12-06T20:00:00Z
updated: 2025-12-06T21:30:00Z
completed: 2025-12-06T21:30:00Z
priority: medium
tags: [progressive-disclosure, phase-7, validation, templates, final]
complexity: 4
blocked_by: [TASK-PD-025]
blocks: []
review_task: null
test_results:
  status: passed
  coverage: null
  last_run: 2025-12-06T21:30:00Z
---

# Task: Template agent validation and metrics capture

## Phase

**Phase 7: Template Agent Migration** (Task 2 of 2 - FINAL)

## Description

Comprehensive validation of template agent progressive disclosure migration, including token reduction metrics and quality assurance.

## Validation Steps

### 1. Size Metrics by Template

```bash
#!/bin/bash
# Capture template agent size metrics

echo "=== Template Agent Size Metrics ==="
echo ""

for template in react-typescript fastapi-python nextjs-fullstack react-fastapi-monorepo; do
    echo "Template: $template"
    echo "---"

    core_total=0
    ext_total=0

    for f in installer/global/templates/$template/agents/*.md; do
        if [[ ! "$f" == *"-ext.md" ]]; then
            core_size=$(wc -c < "$f")
            core_total=$((core_total + core_size))

            ext_file="${f%.md}-ext.md"
            if [ -f "$ext_file" ]; then
                ext_size=$(wc -c < "$ext_file")
                ext_total=$((ext_total + ext_size))
            fi

            printf "  %-45s Core: %6d  Ext: %6d\n" "$(basename $f)" "$core_size" "${ext_size:-0}"
        fi
    done

    echo ""
    echo "  Core total: $core_total bytes ($(echo "scale=1; $core_total/1024" | bc)KB)"
    echo "  Extended total: $ext_total bytes ($(echo "scale=1; $ext_total/1024" | bc)KB)"
    echo ""
done
```

### 2. Overall Reduction Calculation

```bash
#!/bin/bash
# Calculate overall template reduction

echo "=== Overall Template Metrics ==="

baseline=327782  # Current total (320.1KB + 7.7KB stubs)

core_total=0
ext_total=0

for template in react-typescript fastapi-python nextjs-fullstack react-fastapi-monorepo; do
    for f in installer/global/templates/$template/agents/*.md; do
        if [[ ! "$f" == *"-ext.md" ]]; then
            core_size=$(wc -c < "$f")
            core_total=$((core_total + core_size))

            ext_file="${f%.md}-ext.md"
            if [ -f "$ext_file" ]; then
                ext_size=$(wc -c < "$ext_file")
                ext_total=$((ext_total + ext_size))
            fi
        fi
    done
done

combined=$((core_total + ext_total))
reduction=$(echo "scale=1; (1 - $core_total / $baseline) * 100" | bc)

echo "Baseline (pre-migration): $baseline bytes ($(echo "scale=1; $baseline/1024" | bc)KB)"
echo "Core total (post-migration): $core_total bytes ($(echo "scale=1; $core_total/1024" | bc)KB)"
echo "Extended total: $ext_total bytes ($(echo "scale=1; $ext_total/1024" | bc)KB)"
echo "Combined total: $combined bytes ($(echo "scale=1; $combined/1024" | bc)KB)"
echo ""
echo "Token reduction: ${reduction}%"
echo "Target: ≥55%"
```

### 3. Loading Instructions Check

```bash
#!/bin/bash
# Verify all template agents have loading instructions

echo "=== Loading Instructions Check ==="

for template in react-typescript fastapi-python nextjs-fullstack react-fastapi-monorepo; do
    echo ""
    echo "Template: $template"

    for f in installer/global/templates/$template/agents/*.md; do
        if [[ ! "$f" == *"-ext.md" ]]; then
            if grep -q "## Extended Reference" "$f"; then
                echo "  ✓ $(basename $f)"
            else
                echo "  ✗ $(basename $f) - MISSING"
            fi
        fi
    done
done
```

### 4. Content Preservation Check

```bash
#!/bin/bash
# Verify no content loss by comparing with backups

echo "=== Content Preservation Check ==="

for template in react-typescript fastapi-python nextjs-fullstack react-fastapi-monorepo; do
    echo ""
    echo "Template: $template"

    for bak in installer/global/templates/$template/agents/*.md.bak; do
        if [ -f "$bak" ]; then
            base=$(basename "$bak" .md.bak)
            core="installer/global/templates/$template/agents/${base}.md"
            ext="installer/global/templates/$template/agents/${base}-ext.md"

            if [ -f "$core" ] && [ -f "$ext" ]; then
                bak_size=$(wc -c < "$bak")
                combined_size=$(($(wc -c < "$core") + $(wc -c < "$ext")))

                variance=$(echo "scale=1; ($combined_size - $bak_size) / $bak_size * 100" | bc)

                if (( $(echo "$variance > 5 || $variance < -5" | bc -l) )); then
                    echo "  ⚠ $base: ${variance}% variance"
                else
                    echo "  ✓ $base: ${variance}% variance"
                fi
            fi
        fi
    done
done
```

### 5. Discovery Validation

```python
#!/usr/bin/env python3
"""Validate template agent discovery excludes -ext.md files."""

from pathlib import Path
import sys

sys.path.insert(0, 'installer/global/lib/agent_scanner')
from agent_scanner import MultiSourceAgentScanner

print("=== Template Agent Discovery Validation ===")

templates = [
    'react-typescript',
    'fastapi-python',
    'nextjs-fullstack',
    'react-fastapi-monorepo'
]

for template in templates:
    template_path = Path(f'installer/global/templates/{template}/agents')
    if template_path.exists():
        scanner = MultiSourceAgentScanner(
            global_path=Path('installer/global/agents'),
            template_path=template_path
        )
        inventory = scanner.scan()

        # Check for extended files in template agents
        ext_found = [a for a in inventory.template_agents if '-ext' in a.name]
        if ext_found:
            print(f"✗ {template}: Extended files in discovery: {[a.name for a in ext_found]}")
        else:
            agent_count = len(inventory.template_agents)
            print(f"✓ {template}: {agent_count} agents discovered (no -ext files)")

print()
print("✓ Template agent discovery validation passed")
```

## Final Metrics Report

Generate comprehensive report:

```markdown
# Progressive Disclosure Template Report

**Date**: YYYY-MM-DD
**Status**: COMPLETE
**Phase**: 7 (Template Agent Migration)

## Token Reduction by Template

| Template | Original | Core | Ext | Reduction |
|----------|----------|------|-----|-----------|
| react-typescript | 84.3KB | XX.XKB | XX.XKB | XX.X% |
| fastapi-python | 66.2KB | XX.XKB | XX.XKB | XX.X% |
| nextjs-fullstack | 91.2KB | XX.XKB | XX.XKB | XX.X% |
| react-fastapi-monorepo | 78.4KB | XX.XKB | XX.XKB | XX.X% |
| **Total** | **320.1KB** | **XX.XKB** | **XX.XKB** | **XX.X%** |

## Combined Progressive Disclosure Metrics

| Category | Original | Core | Reduction |
|----------|----------|------|-----------|
| Global agents | 509KB | 120.5KB | 76.3% |
| Template agents | 320.1KB | XX.XKB | XX.X% |
| **Total** | **829.1KB** | **XX.XKB** | **XX.X%** |

## Quality Metrics

| Check | Status |
|-------|--------|
| All template agents migrated (14) | ✓/✗ |
| Loading instructions present (14) | ✓/✗ |
| Content preserved (±5%) | ✓/✗ |
| Discovery excludes -ext files | ✓/✗ |
| Overall reduction ≥55% | ✓/✗ |

## Recommendations

1. [Any follow-up items]
2. [Template-specific notes]
```

## Acceptance Criteria

- [x] Token reduction ≥55% achieved for templates (actual: 70.0%)
- [x] All 14 template agents migrated
- [x] All 14 extended files contain content (not stubs)
- [x] All loading instructions present (14/14)
- [x] Template agent discovery excludes extended files
- [x] Content preservation verified (0% variance)
- [x] Final report generated (docs/reports/progressive-disclosure-final-report.md)
- [x] Phase 7 marked complete in README

## Estimated Effort

**0.5 days**

## Dependencies

- TASK-PD-025 (template agents migrated)

## Completion

This is the **FINAL TASK** of Phase 7 (Template Agent Migration).

After completion:
1. Mark TASK-PD-025 and TASK-PD-026 as complete
2. Update progressive-disclosure README with Phase 7 results
3. Update docs/reports/progressive-disclosure-final-report.md with template metrics
4. Commit all changes
5. Progressive Disclosure implementation COMPLETE

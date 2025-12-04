---
id: TASK-PD-011
title: Validate all split agents (discovery, loading, content)
status: backlog
created: 2025-12-03T16:00:00Z
updated: 2025-12-03T16:00:00Z
priority: high
tags: [progressive-disclosure, phase-3, validation, checkpoint]
complexity: 4
blocked_by: [TASK-PD-010]
blocks: [TASK-PD-012, TASK-PD-013, TASK-PD-014, TASK-PD-015]
review_task: TASK-REV-426C
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Validate all split agents (discovery, loading, content)

## Phase

**Phase 3: Automated Global Agent Migration** (Final - Checkpoint)

## Description

Comprehensive validation of all split global agents before proceeding to template agent splits.

## Validation Checklist

### 1. File Structure Validation

```bash
# Verify file counts
python3 -c "
from pathlib import Path

agents_dir = Path('installer/global/agents')
core_files = [f for f in agents_dir.glob('*.md') if not f.stem.endswith('-ext')]
ext_files = list(agents_dir.glob('*-ext.md'))

print(f'Core files: {len(core_files)}')
print(f'Extended files: {len(ext_files)}')

# Each core should have matching extended
for core in core_files:
    ext = agents_dir / f'{core.stem}-ext.md'
    if not ext.exists():
        print(f'MISSING: {ext.name}')

# Each extended should have matching core
for ext in ext_files:
    core_stem = ext.stem.replace('-ext', '')
    core = agents_dir / f'{core_stem}.md'
    if not core.exists():
        print(f'ORPHAN: {ext.name}')
"
```

### 2. Discovery System Validation

```bash
# Run discovery scan
python3 -c "
from pathlib import Path
import sys
sys.path.insert(0, 'installer/global/lib')
from agent_scanner import AgentScanner

scanner = AgentScanner()
agents = scanner.scan_agents(Path('installer/global/agents'))

print(f'Discovered agents: {len(agents)}')
print()

# Check no -ext files in results
errors = []
for agent in agents:
    if '-ext' in agent.name:
        errors.append(f'Extended file in discovery: {agent.name}')

    # Verify frontmatter intact
    if not agent.description:
        errors.append(f'Missing description: {agent.name}')

if errors:
    print('ERRORS:')
    for e in errors:
        print(f'  - {e}')
else:
    print('All agents discovered correctly')
    for agent in sorted(agents, key=lambda a: a.name):
        print(f'  {agent.name}')
"
```

### 3. Content Validation

```bash
# Validate content structure
python3 scripts/split-agent.py --validate --all-global

# Expected output for each agent:
# - Frontmatter: PRESENT
# - Boundaries: PRESENT
# - Loading Instruction: PRESENT
# - Extended Header: PRESENT
# - Content Preserved: YES
```

### 4. Size Validation

```python
# scripts/validate-splits.py
from pathlib import Path

def validate_sizes():
    """Validate split file sizes meet targets."""
    agents_dir = Path('installer/global/agents')
    results = []

    for core_file in agents_dir.glob('*.md'):
        if core_file.stem.endswith('-ext'):
            continue

        ext_file = agents_dir / f'{core_file.stem}-ext.md'
        if not ext_file.exists():
            results.append({
                'agent': core_file.stem,
                'status': 'MISSING_EXT',
                'error': f'Extended file not found'
            })
            continue

        core_size = core_file.stat().st_size
        ext_size = ext_file.stat().st_size
        total_size = core_size + ext_size

        # Estimate original size (backup if exists)
        backup_file = core_file.with_suffix('.md.bak')
        if backup_file.exists():
            original_size = backup_file.stat().st_size
        else:
            original_size = total_size  # Approximate

        reduction = ((original_size - core_size) / original_size) * 100 if original_size > 0 else 0

        status = 'PASS'
        errors = []

        if core_size > 20 * 1024:  # 20KB limit
            status = 'FAIL'
            errors.append(f'Core too large: {core_size/1024:.1f}KB > 20KB')

        if reduction < 40:
            status = 'WARN'
            errors.append(f'Low reduction: {reduction:.1f}% < 40%')

        results.append({
            'agent': core_file.stem,
            'status': status,
            'core_kb': core_size / 1024,
            'ext_kb': ext_size / 1024,
            'reduction': reduction,
            'errors': errors
        })

    return results

if __name__ == '__main__':
    results = validate_sizes()

    print("SPLIT VALIDATION RESULTS")
    print("=" * 70)

    passed = 0
    warned = 0
    failed = 0

    for r in sorted(results, key=lambda x: x['agent']):
        status_icon = {'PASS': '✅', 'WARN': '⚠️', 'FAIL': '❌'}.get(r['status'], '?')
        print(f"{status_icon} {r['agent']}")
        print(f"   Core: {r.get('core_kb', 0):.1f}KB | Ext: {r.get('ext_kb', 0):.1f}KB | Reduction: {r.get('reduction', 0):.1f}%")
        if r.get('errors'):
            for e in r['errors']:
                print(f"   ⚠️  {e}")
        print()

        if r['status'] == 'PASS':
            passed += 1
        elif r['status'] == 'WARN':
            warned += 1
        else:
            failed += 1

    print("=" * 70)
    print(f"SUMMARY: {passed} passed, {warned} warnings, {failed} failed")
```

### 5. Loading Instruction Validation

```bash
# Check all core files have loading instruction
for f in installer/global/agents/*.md; do
    if [[ ! "$f" == *"-ext.md" ]]; then
        if ! grep -q "## Extended Reference" "$f"; then
            echo "MISSING loading instruction: $f"
        fi
    fi
done
```

### 6. Functional Test

```bash
# Test that an agent can be loaded and extended content accessed
cat installer/global/agents/task-manager.md | head -50
# Should show core content ending with loading instruction

cat installer/global/agents/task-manager-ext.md | head -20
# Should show extended header and detailed content
```

## Acceptance Criteria

- [ ] All 19 agents have matching core and extended files
- [ ] Discovery finds exactly 19 agents (no -ext files)
- [ ] All frontmatter intact and parseable
- [ ] All core files have Boundaries section
- [ ] All core files have loading instruction
- [ ] All extended files have reference header
- [ ] Average core size ≤15KB
- [ ] No core file exceeds 20KB
- [ ] Average reduction ≥50%
- [ ] No content loss (validated by diff)

## Validation Report Template

```markdown
# Progressive Disclosure Validation Report

**Date**: YYYY-MM-DD
**Phase**: 3 - Global Agent Migration

## Summary

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Agents processed | 19 | XX | ✅/❌ |
| Core files | 19 | XX | ✅/❌ |
| Extended files | 19 | XX | ✅/❌ |
| Discovery count | 19 | XX | ✅/❌ |
| Avg core size | ≤15KB | XXkB | ✅/❌ |
| Max core size | ≤20KB | XXkB | ✅/❌ |
| Avg reduction | ≥50% | XX% | ✅/❌ |

## Agent Details

[Table of all 19 agents with sizes and status]

## Issues Found

[List any issues and resolutions]

## Conclusion

[Ready/Not Ready] to proceed to Phase 4 (Template Agents)
```

## Estimated Effort

**0.5 days**

## Dependencies

- TASK-PD-010 (all agents split)

## Checkpoint

**This is a CHECKPOINT task.** Do not proceed to Phase 4 until all validation criteria pass.

If validation fails:
1. Identify failing agents
2. Fix categorization rules (TASK-PD-009)
3. Re-run split for affected agents
4. Re-validate

---
id: TASK-PD-019
title: Full integration testing (end-to-end workflow)
status: backlog
created: 2025-12-03T16:00:00Z
updated: 2025-12-03T16:00:00Z
priority: high
tags: [progressive-disclosure, phase-5, testing, integration, final]
complexity: 5
blocked_by: [TASK-PD-018]
blocks: []
review_task: TASK-REV-426C
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Full integration testing (end-to-end workflow)

## Phase

**Phase 5: Validation & Documentation** (FINAL TASK)

## Description

Comprehensive end-to-end testing of the progressive disclosure implementation across all workflows.

## Test Scenarios

### Test 1: template-create Workflow

```bash
# Create template from sample codebase
/template-create --source ~/Projects/sample-react-app --output /tmp/test-template

# Verify split structure
ls -la /tmp/test-template/
ls -la /tmp/test-template/docs/patterns/
ls -la /tmp/test-template/docs/reference/
ls -la /tmp/test-template/agents/

# Verify sizes
wc -c /tmp/test-template/CLAUDE.md  # Should be ≤10KB
wc -c /tmp/test-template/docs/patterns/README.md
wc -c /tmp/test-template/docs/reference/README.md

# Verify loading instructions
grep "## Extended Documentation" /tmp/test-template/CLAUDE.md
grep "docs/patterns" /tmp/test-template/CLAUDE.md
```

**Success Criteria**:
- [ ] CLAUDE.md ≤10KB
- [ ] docs/patterns/README.md exists
- [ ] docs/reference/README.md exists
- [ ] Loading instructions present

### Test 2: agent-enhance Workflow

```bash
# Create test agent
cat > /tmp/test-agent.md << 'EOF'
---
name: test-specialist
description: Test agent for progressive disclosure
tools: [Read, Write, Edit]
---
# Test Specialist
Basic test agent.
EOF

# Enhance with split
/agent-enhance /tmp/test-agent.md /tmp/test-template

# Verify split output
ls -la /tmp/test-template/agents/test-specialist*.md

# Verify core has loading instruction
grep "## Extended Reference" /tmp/test-template/agents/test-specialist.md

# Verify extended has content
head -20 /tmp/test-template/agents/test-specialist-ext.md
```

**Success Criteria**:
- [ ] Both core and extended files created
- [ ] Core has loading instruction
- [ ] Extended has header referencing core

### Test 3: Agent Discovery

```bash
# Run discovery on split agents
python3 -c "
from pathlib import Path
import sys
sys.path.insert(0, 'installer/global/lib')
from agent_scanner import AgentScanner

scanner = AgentScanner()

# Test global agents
global_agents = scanner.scan_agents(Path('installer/global/agents'))
print(f'Global agents: {len(global_agents)}')
for a in global_agents:
    if '-ext' in a.name:
        print(f'ERROR: Extended file discovered: {a.name}')
        sys.exit(1)

# Test template agents
template_agents = scanner.scan_agents(Path('installer/global/templates/react-typescript/agents'))
print(f'Template agents: {len(template_agents)}')
for a in template_agents:
    if '-ext' in a.name:
        print(f'ERROR: Extended file discovered: {a.name}')
        sys.exit(1)

print('Discovery test PASSED')
"
```

**Success Criteria**:
- [ ] No -ext files in discovery results
- [ ] All core agents discovered
- [ ] Frontmatter intact

### Test 4: Task Workflow with Split Agents

```bash
# Create a task and work on it
/task-create "Test progressive disclosure" priority:low

# Work on task (uses split agents)
/task-work TASK-XXX

# Verify agents loaded correctly
# (Manual check: AI should use core content, load ext when implementing)
```

**Success Criteria**:
- [ ] Task workflow completes
- [ ] No errors from missing content
- [ ] Extended content accessible when needed

### Test 5: Token Usage Comparison

```bash
# Before progressive disclosure (from backups)
python3 -c "
from pathlib import Path

# Calculate original sizes
original_size = 0
for f in Path('installer/global/agents').glob('*.md.bak'):
    original_size += f.stat().st_size

# Calculate core sizes
core_size = 0
for f in Path('installer/global/agents').glob('*.md'):
    if not f.stem.endswith('-ext'):
        core_size += f.stat().st_size

reduction = ((original_size - core_size) / original_size) * 100 if original_size > 0 else 0

print(f'Original total: {original_size/1024:.1f}KB')
print(f'Core total: {core_size/1024:.1f}KB')
print(f'Reduction: {reduction:.1f}%')
"
```

**Success Criteria**:
- [ ] Overall reduction ≥50%
- [ ] Typical task context reduced by ≥55%

### Test 6: Backward Compatibility

```bash
# Test single-file mode still works
/template-create --source ~/Projects/sample --output /tmp/single-test --no-split

# Verify single CLAUDE.md
ls -la /tmp/single-test/CLAUDE.md
ls -la /tmp/single-test/docs/  # Should not exist or be empty
```

**Success Criteria**:
- [ ] Single-file mode produces expected output
- [ ] No split structure created

## Integration Test Script

```bash
#!/bin/bash
# scripts/test-progressive-disclosure.sh

set -e

echo "=== Progressive Disclosure Integration Tests ==="
echo ""

# Test 1: Global agent structure
echo "Test 1: Global agent structure..."
core_count=$(ls installer/global/agents/*.md 2>/dev/null | grep -v "\-ext" | wc -l)
ext_count=$(ls installer/global/agents/*-ext.md 2>/dev/null | wc -l)
echo "  Core files: $core_count"
echo "  Extended files: $ext_count"
if [ "$core_count" -eq "$ext_count" ]; then
    echo "  ✅ PASSED"
else
    echo "  ❌ FAILED: Mismatch in file counts"
    exit 1
fi
echo ""

# Test 2: Loading instructions
echo "Test 2: Loading instructions..."
missing=0
for f in installer/global/agents/*.md; do
    if [[ ! "$f" == *"-ext.md" ]]; then
        if ! grep -q "## Extended Reference" "$f"; then
            echo "  Missing: $f"
            missing=$((missing + 1))
        fi
    fi
done
if [ "$missing" -eq 0 ]; then
    echo "  ✅ PASSED"
else
    echo "  ❌ FAILED: $missing files missing loading instructions"
    exit 1
fi
echo ""

# Test 3: Discovery exclusion
echo "Test 3: Discovery exclusion..."
python3 -c "
from pathlib import Path
import sys
sys.path.insert(0, 'installer/global/lib')
from agent_scanner import AgentScanner
scanner = AgentScanner()
agents = scanner.scan_agents(Path('installer/global/agents'))
ext_found = [a for a in agents if '-ext' in a.name]
if ext_found:
    print(f'  ❌ FAILED: Extended files in discovery: {[a.name for a in ext_found]}')
    sys.exit(1)
print(f'  Discovered: {len(agents)} agents')
print('  ✅ PASSED')
"
echo ""

# Test 4: Size validation
echo "Test 4: Size validation..."
python3 -c "
from pathlib import Path
oversized = []
for f in Path('installer/global/agents').glob('*.md'):
    if not f.stem.endswith('-ext'):
        size = f.stat().st_size
        if size > 20 * 1024:
            oversized.append((f.name, size/1024))
if oversized:
    for name, size in oversized:
        print(f'  Oversized: {name} ({size:.1f}KB)')
    print('  ❌ FAILED')
    exit(1)
print('  ✅ PASSED')
"
echo ""

echo "=== All Tests PASSED ==="
```

## Final Validation Report

Generate comprehensive report:

```markdown
# Progressive Disclosure Implementation Report

**Date**: YYYY-MM-DD
**Status**: COMPLETE

## Metrics

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Global agents split | 19 | XX | ✅ |
| Template agents split | XX | XX | ✅ |
| Avg core reduction | ≥50% | XX% | ✅ |
| Discovery working | Yes | Yes | ✅ |
| Workflows tested | 6 | 6 | ✅ |
| Backward compat | Yes | Yes | ✅ |

## Files Changed

- installer/global/agents/*.md (38 files)
- installer/global/templates/*/agents/*.md
- installer/global/lib/agent_enhancement/applier.py
- installer/global/lib/agent_enhancement/enhancer.py
- installer/global/lib/template_generator/claude_md_generator.py
- scripts/split-agent.py (new)
- CLAUDE.md
- Command documentation

## Ready for Production

✅ Progressive disclosure implementation complete and validated
```

## Acceptance Criteria

- [ ] All 6 test scenarios pass
- [ ] Integration test script passes
- [ ] Final validation report generated
- [ ] No regressions in existing workflows
- [ ] Documentation complete

## Estimated Effort

**1 day**

## Dependencies

- TASK-PD-018 (documentation updated)

## Completion

This is the **FINAL TASK** of the progressive disclosure initiative.

After completion:
1. Mark all TASK-PD-* tasks as complete
2. Mark TASK-REV-426C as complete
3. Commit all changes
4. Tag release (if appropriate)

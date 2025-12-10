#!/bin/bash
# Progressive Disclosure Integration Tests
# TASK-PD-019: Full integration testing (end-to-end workflow)
#
# Tests the progressive disclosure infrastructure:
# - Agent discovery excludes -ext.md files
# - Extended file structure exists
# - Agent scanner works correctly
# - Size metrics

set -e

echo "=== Progressive Disclosure Integration Tests ==="
echo "Date: $(date)"
echo ""

PASS_COUNT=0
FAIL_COUNT=0

pass() {
    echo "  ✅ PASSED"
    PASS_COUNT=$((PASS_COUNT + 1))
}

fail() {
    echo "  ❌ FAILED: $1"
    FAIL_COUNT=$((FAIL_COUNT + 1))
}

# Test 1: Extended file structure exists
echo "Test 1: Extended file structure..."
core_count=$(ls installer/core/agents/*.md 2>/dev/null | grep -v "\-ext" | wc -l | tr -d ' ')
ext_count=$(ls installer/core/agents/*-ext.md 2>/dev/null | wc -l | tr -d ' ')
echo "  Core files: $core_count"
echo "  Extended files: $ext_count"

if [ "$ext_count" -gt 0 ]; then
    pass
else
    fail "No extended files found"
fi
echo ""

# Test 2: Agent discovery excludes extended files
echo "Test 2: Agent discovery excludes -ext.md files..."
python3 -c "
from pathlib import Path
import sys
sys.path.insert(0, 'installer/core/lib/agent_scanner')
from agent_scanner import MultiSourceAgentScanner

scanner = MultiSourceAgentScanner(global_path=Path('installer/core/agents'))
inventory = scanner.scan()

# Check for extended files in discovery
ext_found = [a for a in inventory.global_agents if '-ext' in a.name]
if ext_found:
    print(f'  Extended files in discovery: {[a.name for a in ext_found]}')
    sys.exit(1)
print(f'  Discovered: {len(inventory.global_agents)} agents (no -ext files)')
" 2>/dev/null && pass || fail "Extended files found in discovery"
echo ""

# Test 3: is_extended_file function works correctly
echo "Test 3: Extended file detection function..."
python3 -c "
from pathlib import Path
import sys
sys.path.insert(0, 'installer/core/lib/agent_scanner')
from agent_scanner import is_extended_file

# Test cases
tests = [
    (Path('task-manager-ext.md'), True),
    (Path('task-manager.md'), False),
    (Path('my-ext-agent.md'), False),  # 'ext' not at end
    (Path('code-reviewer-ext.md'), True),
    (Path('agents/security-specialist-ext.md'), True),
]

for path, expected in tests:
    result = is_extended_file(path)
    if result != expected:
        print(f'  FAIL: is_extended_file({path}) = {result}, expected {expected}')
        sys.exit(1)

print('  All test cases passed')
" && pass || fail "Extended file detection incorrect"
echo ""

# Test 4: Extended files are valid markdown with header
echo "Test 4: Extended files have proper header..."
valid_ext=0
invalid_ext=0
for f in installer/core/agents/*-ext.md; do
    if [ -f "$f" ]; then
        if head -1 "$f" | grep -q "^# "; then
            valid_ext=$((valid_ext + 1))
        else
            echo "  Invalid header: $(basename $f)"
            invalid_ext=$((invalid_ext + 1))
        fi
    fi
done
echo "  Valid headers: $valid_ext"
if [ "$invalid_ext" -eq 0 ]; then
    pass
else
    fail "$invalid_ext files with invalid headers"
fi
echo ""

# Test 5: Agent frontmatter intact after infrastructure changes
echo "Test 5: Agent frontmatter intact..."
python3 -c "
from pathlib import Path
import frontmatter
import sys

errors = []
for f in Path('installer/core/agents').glob('*.md'):
    if not f.stem.endswith('-ext'):
        try:
            post = frontmatter.load(f)
            if 'name' not in post.metadata:
                errors.append(f'{f.name}: missing name')
            if 'description' not in post.metadata:
                errors.append(f'{f.name}: missing description')
        except Exception as e:
            errors.append(f'{f.name}: {e}')

if errors:
    for e in errors[:5]:
        print(f'  {e}')
    sys.exit(1)

print('  All core agents have valid frontmatter')
" && pass || fail "Frontmatter validation failed"
echo ""

# Test 6: Documentation references progressive disclosure
echo "Test 6: Documentation updated..."
docs_ok=true

if grep -q "Progressive Disclosure" CLAUDE.md 2>/dev/null; then
    echo "  ✓ Root CLAUDE.md mentions progressive disclosure"
else
    echo "  ✗ Root CLAUDE.md missing progressive disclosure section"
    docs_ok=false
fi

if grep -q "Progressive Disclosure" .claude/CLAUDE.md 2>/dev/null; then
    echo "  ✓ .claude/CLAUDE.md mentions progressive disclosure"
else
    echo "  ✗ .claude/CLAUDE.md missing progressive disclosure section"
    docs_ok=false
fi

if [ "$docs_ok" = true ]; then
    pass
else
    fail "Documentation incomplete"
fi
echo ""

# Summary
echo "=== Test Summary ==="
echo "Passed: $PASS_COUNT"
echo "Failed: $FAIL_COUNT"
echo ""

if [ "$FAIL_COUNT" -eq 0 ]; then
    echo "✅ All Progressive Disclosure Integration Tests PASSED"
    exit 0
else
    echo "❌ Some tests failed"
    exit 1
fi

#!/bin/bash
#
# Validation Script for GuardKit Rename
# Checks for remaining "taskwright" references and validates the rename
#
# Usage: ./scripts/validate-rename.sh
#
# Exit codes:
#   0 - Validation passed
#   1 - Critical issues found (taskwright in critical files)
#   2 - Warnings found (taskwright in non-critical files)
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  GuardKit Rename - Validation Script${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# Track exit status
CRITICAL_ISSUES=0
WARNINGS=0

# Find project root
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$PROJECT_ROOT"

echo "Working directory: $PROJECT_ROOT"
echo ""

# ═══════════════════════════════════════════════════════
# Section 1: Critical Files Check - ensure NO taskwright remains
# ═══════════════════════════════════════════════════════

echo -e "${BLUE}[1/5]${NC} Checking critical files for old 'taskwright' references..."

CRITICAL_FILES=(
    "CLAUDE.md"
    "README.md"
    "installer/scripts/install.sh"
    ".claude/CLAUDE.md"
)

for file in "${CRITICAL_FILES[@]}"; do
    if [[ -f "$file" ]]; then
        # Search case-insensitively for taskwright (the OLD name)
        if grep -qi "taskwright" "$file" 2>/dev/null; then
            echo -e "${RED}  ✗ CRITICAL: Found old 'taskwright' in $file${NC}"
            grep -in "taskwright" "$file" 2>/dev/null | head -5 | while read -r line; do
                echo -e "     ${line}"
            done
            ((CRITICAL_ISSUES++))
        else
            echo -e "${GREEN}  ✓ Clean: $file (no taskwright references)${NC}"
        fi
    else
        echo -e "${YELLOW}  ⚠ Not found: $file${NC}"
    fi
done

echo ""

# ═══════════════════════════════════════════════════════
# Section 2: Marker File Check
# ═══════════════════════════════════════════════════════

echo -e "${BLUE}[2/5]${NC} Checking marker files..."

# Check for OLD marker file (should NOT exist)
OLD_MARKER="installer/global/templates/taskwright.marker.json"
# Check for NEW marker file (should exist)
NEW_MARKER="installer/global/templates/guardkit.marker.json"

if [[ -f "$OLD_MARKER" ]]; then
    echo -e "${RED}  ✗ CRITICAL: Old marker file still exists: $OLD_MARKER${NC}"
    ((CRITICAL_ISSUES++))
else
    echo -e "${GREEN}  ✓ Old marker file removed: $OLD_MARKER${NC}"
fi

if [[ -f "$NEW_MARKER" ]]; then
    # Validate content has guardkit
    if grep -q '"package":\s*"guardkit"' "$NEW_MARKER" 2>/dev/null || \
       grep -q '"package": "guardkit"' "$NEW_MARKER" 2>/dev/null; then
        echo -e "${GREEN}  ✓ New marker file valid: $NEW_MARKER${NC}"
    else
        echo -e "${RED}  ✗ CRITICAL: New marker file has incorrect content${NC}"
        cat "$NEW_MARKER"
        ((CRITICAL_ISSUES++))
    fi
else
    echo -e "${YELLOW}  ⚠ New marker file not found: $NEW_MARKER${NC}"
    echo -e "     Will be created during installation"
fi

echo ""

# ═══════════════════════════════════════════════════════
# Section 3: Solution/Project File Check
# ═══════════════════════════════════════════════════════

echo -e "${BLUE}[3/5]${NC} Checking solution/project files..."

# Check for OLD solution file (should NOT exist)
if [[ -f "taskwright.sln" ]]; then
    echo -e "${RED}  ✗ CRITICAL: Old solution file still exists: taskwright.sln${NC}"
    ((CRITICAL_ISSUES++))
else
    echo -e "${GREEN}  ✓ Old solution file removed: taskwright.sln${NC}"
fi

# Check for NEW solution file (should exist)
if [[ -f "guardkit.sln" ]]; then
    echo -e "${GREEN}  ✓ New solution file exists: guardkit.sln${NC}"
else
    echo -e "${YELLOW}  ⚠ New solution file not found: guardkit.sln${NC}"
fi

echo ""

# ═══════════════════════════════════════════════════════
# Section 4: Full Codebase Search for OLD name (excluding historical)
# ═══════════════════════════════════════════════════════

echo -e "${BLUE}[4/5]${NC} Searching codebase for remaining 'taskwright' references..."

# Search for taskwright (OLD name) in active files (excluding historical)
REMAINING=$(grep -ri "taskwright" . \
    --include="*.py" \
    --include="*.md" \
    --include="*.sh" \
    --include="*.json" \
    --include="*.yml" \
    --include="*.yaml" \
    --include="*.toml" \
    --include="*.txt" \
    --include="*.sln" \
    --include="*.csproj" \
    2>/dev/null \
    | grep -v "tasks/completed/" \
    | grep -v "tasks/archived/" \
    | grep -v "tasks/backlog/" \
    | grep -v "tasks/in_progress/" \
    | grep -v "tasks/in_review/" \
    | grep -v ".claude/reviews/" \
    | grep -v ".claude/state/" \
    | grep -v ".git/" \
    | grep -v "docs/adr/" \
    | grep -v "scripts/rename-taskwright-to-guardkit.py" \
    | grep -v "scripts/validate-rename.sh" \
    || true)

if [[ -n "$REMAINING" ]]; then
    echo -e "${YELLOW}  ⚠ Found remaining 'taskwright' references:${NC}"
    echo ""
    echo "$REMAINING" | head -30 | while read -r line; do
        echo -e "     ${line}"
    done

    REMAINING_COUNT=$(echo "$REMAINING" | wc -l | tr -d ' ')

    if [[ $REMAINING_COUNT -gt 30 ]]; then
        echo ""
        echo -e "     ${YELLOW}... and $((REMAINING_COUNT - 30)) more${NC}"
    fi

    echo ""
    echo -e "  Total remaining references: ${REMAINING_COUNT}"
    ((WARNINGS++))
else
    echo -e "${GREEN}  ✓ No remaining 'taskwright' references in active files${NC}"
fi

echo ""

# ═══════════════════════════════════════════════════════
# Section 5: CLI Alias Check for OLD aliases
# ═══════════════════════════════════════════════════════

echo -e "${BLUE}[5/5]${NC} Checking for old CLI alias references (tw/twi)..."

# Search for old tw/twi aliases in scripts (with word boundaries)
OLD_ALIASES=$(grep -rE '\btw\b|\btwi\b' . \
    --include="*.sh" \
    --include="*.py" \
    --include="*.md" \
    2>/dev/null \
    | grep -v ".git/" \
    | grep -v "tasks/completed/" \
    | grep -v "tasks/archived/" \
    | grep -v ".claude/reviews/" \
    | grep -v "scripts/rename-taskwright-to-guardkit.py" \
    | grep -v "scripts/validate-rename.sh" \
    | grep -v "# tw " \
    | grep -v "twitter" \
    | grep -v "between" \
    | grep -v "two" \
    | grep -v "twice" \
    || true)

if [[ -n "$OLD_ALIASES" ]]; then
    echo -e "${YELLOW}  ⚠ Potential old CLI alias references found:${NC}"
    echo "$OLD_ALIASES" | head -10 | while read -r line; do
        echo -e "     ${line}"
    done
    echo ""
    echo "  Note: Review these manually - some may be false positives"
    ((WARNINGS++))
else
    echo -e "${GREEN}  ✓ No obvious old CLI alias references found${NC}"
fi

echo ""

# ═══════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════

echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"

if [[ $CRITICAL_ISSUES -gt 0 ]]; then
    echo -e "${RED}  Validation FAILED - $CRITICAL_ISSUES critical issue(s)${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo ""
    echo "Critical issues must be resolved before proceeding."
    echo ""
    echo "To fix:"
    echo "  1. Run rename script: python3 scripts/rename-taskwright-to-guardkit.py"
    echo "  2. Re-run validation: ./scripts/validate-rename.sh"
    echo ""
    exit 1
elif [[ $WARNINGS -gt 0 ]]; then
    echo -e "${YELLOW}  Validation PASSED with $WARNINGS warning(s)${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo ""
    echo "Warnings are informational - review and address if needed."
    echo ""
    echo "Next steps:"
    echo "  1. Review warnings above"
    echo "  2. Run tests: pytest tests/ -v"
    echo "  3. Commit changes: git add -A && git commit -m 'Rename Taskwright to GuardKit'"
    echo ""
    exit 0
else
    echo -e "${GREEN}  Validation PASSED - All checks clean${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo ""
    echo "The rename operation completed successfully!"
    echo ""
    echo "Next steps:"
    echo "  1. Run tests: pytest tests/ -v"
    echo "  2. Test installation: ./installer/scripts/install.sh"
    echo "  3. Commit changes: git add -A && git commit -m 'Rename Taskwright to GuardKit'"
    echo ""
    exit 0
fi

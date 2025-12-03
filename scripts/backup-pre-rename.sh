#!/bin/bash
#
# Backup Script for GuardKit Rename
# Creates a timestamped backup branch before the rename operation
#
# Usage: ./scripts/backup-pre-rename.sh
#
# Creates:
#   - Backup branch: backup/pre-guardkit-rename-YYYYMMDD-HHMMSS
#   - State summary: .claude/state/backup-YYYYMMDD-HHMMSS.txt
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Generate timestamp
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_BRANCH="backup/pre-guardkit-rename-${TIMESTAMP}"

echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  GuardKit Rename - Backup Script${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# Step 1: Verify we're in a git repository
echo -e "${BLUE}[1/5]${NC} Verifying git repository..."
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${RED}Error: Not in a git repository${NC}"
    exit 1
fi
echo -e "${GREEN}  ✓ Git repository found${NC}"

# Step 2: Verify clean working directory
echo -e "${BLUE}[2/5]${NC} Checking working directory status..."
if [[ -n $(git status --porcelain) ]]; then
    echo -e "${YELLOW}Warning: Working directory has uncommitted changes${NC}"
    echo ""
    git status --short
    echo ""
    read -p "Continue anyway? [y/N]: " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}Aborted. Commit or stash changes first.${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}  ✓ Working directory is clean${NC}"
fi

# Step 3: Get current branch and commit info
echo -e "${BLUE}[3/5]${NC} Recording current state..."
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "detached HEAD")
CURRENT_COMMIT=$(git rev-parse HEAD)
COMMIT_MESSAGE=$(git log -1 --format=%s HEAD)
FILE_COUNT=$(git ls-files | wc -l | tr -d ' ')

echo -e "${GREEN}  ✓ Current branch: ${CURRENT_BRANCH}${NC}"
echo -e "${GREEN}  ✓ Current commit: ${CURRENT_COMMIT:0:8}${NC}"

# Step 4: Create backup branch
echo -e "${BLUE}[4/5]${NC} Creating backup branch..."
if git branch "${BACKUP_BRANCH}" 2>/dev/null; then
    echo -e "${GREEN}  ✓ Created branch: ${BACKUP_BRANCH}${NC}"
else
    echo -e "${YELLOW}  ⚠ Branch already exists, using existing backup${NC}"
fi

# Step 5: Export state summary
echo -e "${BLUE}[5/5]${NC} Exporting state summary..."

# Ensure state directory exists
mkdir -p .claude/state

# Create state summary file
STATE_FILE=".claude/state/backup-${TIMESTAMP}.txt"
{
    echo "═══════════════════════════════════════════════════════"
    echo "  GuardKit Rename - Backup State Summary"
    echo "═══════════════════════════════════════════════════════"
    echo ""
    echo "Backup Information:"
    echo "  Backup Branch: ${BACKUP_BRANCH}"
    echo "  Timestamp: ${TIMESTAMP}"
    echo "  Created: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    echo ""
    echo "Repository State:"
    echo "  Current Branch: ${CURRENT_BRANCH}"
    echo "  Current Commit: ${CURRENT_COMMIT}"
    echo "  Commit Message: ${COMMIT_MESSAGE}"
    echo "  File Count: ${FILE_COUNT} files"
    echo ""
    echo "Rollback Instructions:"
    echo "  To restore pre-rename state:"
    echo "    git checkout ${BACKUP_BRANCH}"
    echo ""
    echo "  To delete backup after successful rename:"
    echo "    git branch -D ${BACKUP_BRANCH}"
    echo ""
    echo "═══════════════════════════════════════════════════════"
} > "${STATE_FILE}"

echo -e "${GREEN}  ✓ State summary saved to: ${STATE_FILE}${NC}"

# Final summary
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Backup Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo ""
echo "Backup Branch: ${BACKUP_BRANCH}"
echo "State Summary: ${STATE_FILE}"
echo ""
echo "Next Steps:"
echo "  1. Run rename script: python3 scripts/rename-guardkit-to-guardkit.py"
echo "  2. Validate changes: ./scripts/validate-rename.sh"
echo "  3. Review changes: git diff ${BACKUP_BRANCH}"
echo ""
echo "Rollback (if needed):"
echo "  git checkout ${BACKUP_BRANCH}"
echo ""

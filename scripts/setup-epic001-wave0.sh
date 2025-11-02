#!/bin/bash
#
# Setup Wave 0 worktrees for EPIC-001 Template Creation Automation
#
# This script creates 6 worktrees for the foundation tasks that have no dependencies
# and can be executed in parallel immediately.
#

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  EPIC-001 Wave 0 Setup: Foundation Tasks"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Creating 6 parallel worktrees for foundation tasks..."
echo ""

cd "$PROJECT_ROOT"

# Check if Conductor is installed
if ! command -v conductor &> /dev/null; then
    echo "❌ Error: Conductor not found"
    echo ""
    echo "Please install Conductor first:"
    echo "  npm install -g @conductor/cli"
    echo ""
    exit 1
fi

# Wave 0 Round 1: Create first 4 worktrees (highest priority)
echo "📦 Round 1: Creating primary worktrees..."
echo ""

echo "  [1/4] TASK-037A: Universal Language Mapping (3h)"
conductor worktree create epic001-w0-lang TASK-037A || echo "    (worktree may already exist)"

echo "  [2/4] TASK-037: Technology Stack Detection (6h)"
conductor worktree create epic001-w0-stack TASK-037 || echo "    (worktree may already exist)"

echo "  [3/4] TASK-048B: Local Agent Scanner (4h)"
conductor worktree create epic001-w0-local TASK-048B || echo "    (worktree may already exist)"

echo "  [4/4] TASK-048: Subagents.cc Scraper (6h)"
conductor worktree create epic001-w0-ext TASK-048 || echo "    (worktree may already exist)"

echo ""
echo "✅ Round 1 complete: 4 worktrees created (25 hours of work)"
echo ""

# Ask user if they want to create Round 2 now or wait
read -p "Create Round 2 worktrees now? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "📦 Round 2: Creating additional worktrees..."
    echo ""

    echo "  [5/6] TASK-049: GitHub Agent Parsers (8h)"
    conductor worktree create epic001-w0-github TASK-049 || echo "    (worktree may already exist)"

    echo "  [6/6] TASK-053: Template-init QA Flow (6h)"
    conductor worktree create epic001-w0-qa TASK-053 || echo "    (worktree may already exist)"

    echo ""
    echo "✅ Round 2 complete: All 6 Wave 0 worktrees created"
else
    echo ""
    echo "ℹ️  Skipping Round 2 for now."
    echo ""
    echo "Create them later with:"
    echo "  conductor worktree create epic001-w0-github TASK-049"
    echo "  conductor worktree create epic001-w0-qa TASK-053"
fi

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  Setup Complete!"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Worktrees created in:"
echo "  $(dirname "$PROJECT_ROOT")/epic001-w0-*/"
echo ""
echo "📋 Developer Assignment (Round 1):"
echo ""
echo "  Developer 1 (Language Expert):"
echo "    cd ../epic001-w0-lang"
echo "    # Implement TASK-037A: Universal Language Mapping (3h)"
echo ""
echo "  Developer 2 (Stack Detection):"
echo "    cd ../epic001-w0-stack"
echo "    # Implement TASK-037: Technology Stack Detection (6h)"
echo ""
echo "  Developer 3 (Local Agents):"
echo "    cd ../epic001-w0-local"
echo "    # Implement TASK-048B: Local Agent Scanner (4h)"
echo ""
echo "  Developer 4 (External Agents):"
echo "    cd ../epic001-w0-ext"
echo "    # Implement TASK-048: Subagents.cc Scraper (6h)"
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📋 Developer Assignment (Round 2):"
    echo ""
    echo "  Developer 1 (after completing TASK-037A):"
    echo "    cd ../epic001-w0-github"
    echo "    # Implement TASK-049: GitHub Agent Parsers (8h)"
    echo ""
    echo "  Developer 4 (after completing TASK-048):"
    echo "    cd ../epic001-w0-qa"
    echo "    # Implement TASK-053: Template-init QA Flow (6h)"
    echo ""
fi

echo "📖 Task Details:"
echo "  View full task breakdown in:"
echo "    tasks/backlog/EPIC-001-PARALLEL-QUICK-START.md"
echo ""
echo "🔍 Monitor Progress:"
echo "  conductor status"
echo "  conductor status | grep epic001-w0"
echo ""
echo "🎯 Wave 0 Success Criteria:"
echo "  ✓ 50+ languages mapped"
echo "  ✓ Stack detection working"
echo "  ✓ 15+ local agents discovered"
echo "  ✓ External agent sources integrated"
echo "  ✓ Q&A flow structure ready"
echo ""
echo "⏱️  Estimated Completion: 1.5 weeks with 4 developers"
echo ""

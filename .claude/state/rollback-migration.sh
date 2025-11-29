#!/bin/bash
# Rollback hash ID migration
# Run this if migration goes wrong

set -e

echo "🔄 Rolling back task ID migration..."

# Delete new hash-based tasks
rm -rf tasks/

# Restore from backup
cp -r .claude/state/backup/tasks-pre-hash-migration-20251110-223848 tasks/

echo "✅ Rollback complete"
echo "📋 Verify: ls tasks/backlog/ | head -5"

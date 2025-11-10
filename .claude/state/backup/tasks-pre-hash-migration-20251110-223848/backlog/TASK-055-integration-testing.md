---
id: TASK-055
title: Integration testing and rollback script
status: backlog
created: 2025-01-08T00:00:00Z
updated: 2025-01-08T00:00:00Z
priority: high
tags: [infrastructure, hash-ids, testing, quality-assurance]
complexity: 6
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Integration testing and rollback script

## Description

Create comprehensive integration tests for the entire hash-based ID system and a robust rollback mechanism in case of issues. This is the final quality gate before deployment.

## Acceptance Criteria

- [ ] End-to-end tests for complete workflow (create → work → complete)
- [ ] Concurrent creation tests (10+ simultaneous task creates)
- [ ] PM tool integration tests (mapping, export, sync)
- [ ] Migration validation tests (before/after comparison)
- [ ] Rollback script tested and verified
- [ ] Performance tests (1,000+ tasks)
- [ ] Cross-reference integrity tests
- [ ] Conductor.build parallel worktree tests
- [ ] All tests pass with ≥95% success rate

## Test Requirements

- [ ] Integration test suite (pytest)
- [ ] Performance benchmarks
- [ ] Rollback validation tests
- [ ] Cross-worktree tests
- [ ] PM tool mock integration
- [ ] Test coverage ≥85% overall system

## Implementation Notes

### File Location
Create new file: `tests/integration/test_hash_id_system.py`
Create new file: `installer/scripts/rollback-hash-ids.sh`

### Test Categories

**1. End-to-End Workflow Tests**
```python
def test_complete_task_workflow():
    """Test create → work → complete with hash IDs."""
    # Create task
    result = run_command("/task-create", "Test task")
    task_id = extract_task_id(result)
    assert re.match(r'TASK-[a-f0-9]{4,6}', task_id)

    # Work on task
    result = run_command("/task-work", task_id)
    assert "in_progress" in result

    # Complete task
    result = run_command("/task-complete", task_id)
    assert "completed" in result

    # Verify file moved to completed/
    assert task_exists(f"tasks/completed/{task_id}-*.md")
```

**2. Concurrent Creation Tests**
```python
def test_concurrent_task_creation():
    """Test 10 simultaneous task creations produce unique IDs."""
    import concurrent.futures

    def create_task(i):
        return run_command("/task-create", f"Task {i}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(create_task, range(10)))

    task_ids = [extract_task_id(r) for r in results]

    # All IDs must be unique
    assert len(task_ids) == len(set(task_ids))

    # All IDs must be valid format
    for tid in task_ids:
        assert re.match(r'TASK-[a-f0-9]{4,6}', tid)
```

**3. PM Tool Integration Tests**
```python
def test_pm_tool_mapping():
    """Test internal → external ID mapping."""
    # Create task
    task_id = create_task("Test task")

    # Map to JIRA
    jira_id = map_to_external(task_id, "jira", "PROJ")
    assert re.match(r'PROJ-\d+', jira_id)

    # Map to Azure DevOps
    ado_id = map_to_external(task_id, "azure_devops")
    assert ado_id.isdigit()

    # Reverse lookup
    assert get_internal_id(jira_id, "jira") == task_id
    assert get_internal_id(ado_id, "azure_devops") == task_id
```

**4. Migration Validation Tests**
```python
def test_migration_preserves_data():
    """Test migration preserves all task data."""
    # Create old-format task
    old_task = create_old_format_task("TASK-042", "Test task")

    # Run migration
    run_migration()

    # Verify new task exists
    new_tasks = find_tasks_with_legacy_id("TASK-042")
    assert len(new_tasks) == 1

    new_task = new_tasks[0]

    # Verify data preserved
    assert new_task.title == old_task.title
    assert new_task.status == old_task.status
    assert new_task.priority == old_task.priority
    assert new_task.legacy_id == "TASK-042"

    # Verify new ID format
    assert re.match(r'TASK-[a-f0-9]{4,6}', new_task.id)
```

**5. Prefix Inference Tests**
```python
def test_prefix_inference():
    """Test automatic prefix inference."""
    # Epic inference
    result = run_command("/task-create", "Test", "epic:EPIC-001")
    task_id = extract_task_id(result)
    assert task_id.startswith("TASK-E01-")

    # Tag inference
    result = run_command("/task-create", "Test", "tags:[docs]")
    task_id = extract_task_id(result)
    assert task_id.startswith("TASK-DOC-")

    # Manual override
    result = run_command("/task-create", "Test", "epic:EPIC-001", "prefix:CUSTOM")
    task_id = extract_task_id(result)
    assert task_id.startswith("TASK-CUSTOM-")
```

**6. Cross-Reference Tests**
```python
def test_cross_reference_updates():
    """Test cross-references updated during migration."""
    # Create two old-format tasks with cross-reference
    task1 = create_old_format_task("TASK-042", "Task 1")
    task2 = create_old_format_task("TASK-043", "Task 2, refs TASK-042")

    # Run migration
    migration_map = run_migration()

    # Verify cross-reference updated
    new_task2 = load_task(migration_map["TASK-043"])
    assert migration_map["TASK-042"] in new_task2.content
    assert "TASK-042" not in new_task2.content or "legacy_id" in new_task2.content
```

**7. Performance Tests**
```python
def test_large_scale_performance():
    """Test system performance with 1,000+ tasks."""
    import time

    # Generate 1,000 task IDs
    start = time.time()
    task_ids = [generate_task_id() for _ in range(1000)]
    duration = time.time() - start

    # Should complete in <1 second
    assert duration < 1.0

    # All IDs unique
    assert len(task_ids) == len(set(task_ids))

    # All IDs valid
    for tid in task_ids:
        assert re.match(r'TASK-[a-f0-9]{4,6}', tid)
```

**8. Conductor.build Worktree Tests**
```python
def test_parallel_worktree_creation():
    """Test task creation in parallel git worktrees."""
    # Create two worktrees
    worktree1 = create_worktree("feature-1")
    worktree2 = create_worktree("feature-2")

    # Create tasks concurrently in different worktrees
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future1 = executor.submit(create_task_in_worktree, worktree1, "Task 1")
        future2 = executor.submit(create_task_in_worktree, worktree2, "Task 2")

        task_id1 = future1.result()
        task_id2 = future2.result()

    # IDs must be unique
    assert task_id1 != task_id2

    # Both tasks must exist
    assert task_exists_in_worktree(worktree1, task_id1)
    assert task_exists_in_worktree(worktree2, task_id2)
```

### Rollback Script

```bash
#!/bin/bash
# rollback-hash-ids.sh
# Rollback hash-based ID migration

set -e

BACKUP_DIR=".claude/state/backup/pre-hash-migration"
ROLLBACK_LOG=".claude/state/rollback-$(date +%Y%m%d-%H%M%S).log"

echo "Starting rollback of hash-based ID migration..." | tee -a "$ROLLBACK_LOG"

# Verify backup exists
if [ ! -d "$BACKUP_DIR" ]; then
    echo "❌ ERROR: Backup directory not found: $BACKUP_DIR"
    exit 1
fi

# Count files
backup_count=$(find "$BACKUP_DIR" -name "*.md" | wc -l)
echo "Found $backup_count backup files" | tee -a "$ROLLBACK_LOG"

# Restore all tasks
for backup_file in "$BACKUP_DIR"/**/*.md; do
    # Extract original path
    original_path=$(echo "$backup_file" | sed "s|$BACKUP_DIR/||")

    # Restore file
    echo "Restoring: $original_path" >> "$ROLLBACK_LOG"
    cp "$backup_file" "tasks/$original_path"
done

# Restore mapping files (delete new ones)
rm -f .claude/state/external_id_mapping.json
rm -f .claude/state/external_id_counters.json

# Verify restoration
restored_count=$(find tasks -name "TASK-*.md" | wc -l)
echo "Restored $restored_count task files" | tee -a "$ROLLBACK_LOG"

echo "✅ Rollback complete. Log: $ROLLBACK_LOG"
echo "Please verify tasks manually and run tests."
```

### Validation Checklist

Before declaring success, verify:

- [ ] All 10 test categories pass
- [ ] Performance benchmarks met (1,000 IDs in <1 second)
- [ ] Zero collisions in 10,000 ID generation test
- [ ] Rollback script successfully restores original state
- [ ] Migration script handles all edge cases
- [ ] PM tool mapping works for all 4 tools
- [ ] Concurrent creation produces unique IDs
- [ ] Conductor.build worktrees work independently
- [ ] Documentation is complete and accurate

## Dependencies

All previous tasks must be completed:
- TASK-046: Hash ID generator
- TASK-047: Validation
- TASK-048: /task-create update
- TASK-049: External ID mapper
- TASK-050: Persistence
- TASK-051: Frontmatter schema
- TASK-052: Migration script
- TASK-053: Documentation
- TASK-054: Prefix support

## Related Tasks

This is the final task in the hash ID implementation sequence.

## Test Execution Log

[Automatically populated by /task-work]

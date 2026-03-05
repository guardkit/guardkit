# Implementation Guide: Init Seeding Fixes (FEAT-ISF)

## Execution Strategy

### Wave 1: Short-Term Reverts (Parallel)

Unblock init reliability by reverting the two harmful changes from TASK-FIX-b7a7.

| Task | Description | Effort | Method |
|------|-------------|--------|--------|
| TASK-ISF-001 | Revert parallel sync → sequential | 2/10 | /task-work |
| TASK-ISF-002 | Revert rule main_content → content_preview | 1/10 | /task-work |

**Expected outcome**: Restore ~10/12 rule sync, 2/3 agent sync. Init takes ~35 min (slower but reliable).

```bash
# Can run in parallel (no file conflicts)
/task-work TASK-ISF-001
/task-work TASK-ISF-002
```

### Wave 2: Ext Files + Knowledge (Parallel)

Fix template copying and seed critical architectural knowledge.

| Task | Description | Effort | Method |
|------|-------------|--------|--------|
| TASK-ISF-003 | Fix -ext.md file copying in init | 3/10 | /task-work |
| TASK-ISF-004 | Seed Graphiti fidelity knowledge | 2/10 | direct |

```bash
# Can run in parallel (different files)
/task-work TASK-ISF-003
# TASK-ISF-004: direct edit/command
```

### Wave 3: Architectural Fix (Sequential)

Decouple system seeding from init. ISF-005 must complete before ISF-006.

| Task | Description | Effort | Method |
|------|-------------|--------|--------|
| TASK-ISF-005 | Create `guardkit graphiti seed-system` command | 4/10 | /task-work |
| TASK-ISF-006 | Slim init to project-only seeding | 3/10 | /task-work |

```bash
# Sequential (ISF-006 depends on ISF-005)
/task-work TASK-ISF-005
# Wait for completion
/task-work TASK-ISF-006
```

## Verification

After Wave 1, run init and verify:
```bash
guardkit init fastapi-python --project-id test-verify
# Expected: ~10/12 rules synced, 2-3/3 agents synced, 0 circuit breaker trips
```

After Wave 3, run init and verify:
```bash
guardkit graphiti seed-system --template fastapi-python  # One-time
guardkit init fastapi-python --project-id test-verify    # Fast (~5-8 min)
```

## Alignment with Existing Features

| Feature | Relationship | Status |
|---------|-------------|--------|
| FEAT-CR01 | Complementary — handles static trimming (Graphiti-independent) | Backlog, Waves 1-5 |
| FEAT-GE | Complementary — adds AutoBuild enhancements to Graphiti | Backlog, 7 tasks |
| FEAT-init-graphiti-remaining-fixes | Predecessor — prior fix iterations | Mixed |

**Key constraint**: Graphiti extracts facts, not verbatim content. Static rules remain as-is. FEAT-CR01 reduces their size through trimming, not migration.

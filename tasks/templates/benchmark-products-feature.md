---
id: TASK-BENCH-{hash}
title: Benchmark - Products feature implementation
status: backlog
priority: high
complexity: 5
task_type: benchmark
measurement_run: {baseline|after}
---

# Benchmark: Products Feature Implementation

## Purpose

Standardized benchmark task for measuring progressive disclosure impact.

## Procedure

1. **Fresh VM/Container**:
   ```bash
   # macOS VM or Docker container
   mkdir -p ~/benchmark-test && cd ~/benchmark-test
   ```

2. **Install GuardKit**:
   ```bash
   git clone https://github.com/appmilla/guardkit.git
   cd guardkit
   ./installer/scripts/install.sh
   ```

3. **Initialize Project**:
   ```bash
   mkdir -p ~/benchmark-test/api-project && cd ~/benchmark-test/api-project
   guardkit init fastapi-python
   ```

4. **Capture Baseline** (before progressive disclosure):
   ```bash
   python3 ~/benchmark-test/guardkit/scripts/measure-token-usage.py --baseline
   ```

5. **Execute Benchmark Tasks**:
   ```bash
   # Task 1: Infrastructure (complexity 3)
   /task-create "Initialize FastAPI application infrastructure" prefix:BENCH
   /task-work TASK-BENCH-XXXX

   # Task 2: Products feature (complexity 5)
   /task-create "Create Products CRUD feature" prefix:BENCH
   /task-work TASK-BENCH-YYYY
   ```

6. **Record Metrics**:
   - Total session tokens (from Claude Code stats)
   - Wall-clock time for each task
   - Number of agent invocations
   - Any errors or retries

## Expected Outcomes

### Baseline (Before)
- CLAUDE.md: ~20KB
- Global agents: ~200KB (19 files)
- Template agents: ~50KB (8 files)
- Total context: ~270KB

### After Progressive Disclosure
- CLAUDE.md: ~8KB (60% reduction)
- Global agents: ~80KB core (60% reduction)
- Template agents: ~20KB core (60% reduction)
- Total context: ~108KB

### Target
- **55-60% reduction** in total context per task
- **No quality degradation** (tests still pass, same functionality)

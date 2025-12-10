---
task_id: TASK-ENH-9F2A
title: Implement batch agent enhancement capability
status: BACKLOG
priority: LOW
complexity: 4
created: 2025-11-20T21:20:00Z
updated: 2025-11-20T21:20:00Z
assignee: null
tags: [enhancement, phase-8, future, batch-processing]
related_tasks: [TASK-PHASE-8-INCREMENTAL, TASK-AI-2B37]
estimated_duration: 4 hours
technologies: [python, concurrent-processing]
review_source: docs/reviews/phase-8-implementation-review.md
---

# Implement Batch Agent Enhancement Capability

## Problem Statement

Currently, `/agent-enhance` enhances one agent at a time. For templates with 10+ agents, users must invoke the command multiple times. Batch enhancement would allow enhancing all agents in one command.

**Review Finding** (Section 6.4, Future Enhancement #1):
> **Batch Processing**: Phase 8 is one-at-a-time, could add batch mode
> **Priority**: LOW (stateless design makes this easy to add later)

## Current State

**Location**: `installer/core/commands/lib/agent_enhancement/enhancer.py`

**Current API**:
```python
def enhance(self, agent_file: Path, template_dir: Path) -> EnhancementResult:
    """Enhance single agent."""
```

**Limitation**: Only processes one agent per invocation.

## Acceptance Criteria

### 1. Batch Enhancement Method
- [ ] New method: `enhance_batch(agent_files: List[Path], template_dir: Path)`
- [ ] Processes multiple agents in single invocation
- [ ] Returns list of EnhancementResult
- [ ] Maintains existing single-agent API

### 2. Parallel Processing
- [ ] Use ThreadPoolExecutor for concurrent enhancement
- [ ] Configurable max workers (default: 5)
- [ ] Thread-safe implementation
- [ ] Proper error isolation (one failure doesn't kill batch)

### 3. Progress Reporting
- [ ] Show progress: "Enhancing 3/10 agents..."
- [ ] Real-time status updates
- [ ] Summary report at end
- [ ] Individual agent results

### 4. Command Line Interface
- [ ] New flag: `--batch` or detect multiple agent files
- [ ] Accept glob patterns: `agents/*.md`
- [ ] Accept directory: enhance all agents in directory
- [ ] Backward compatible with single-agent usage

### 5. Error Handling
- [ ] Continue on individual agent failure
- [ ] Collect all errors
- [ ] Report failed agents at end
- [ ] Exit code reflects partial vs complete failure

## Technical Details

### Files to Modify

**1. `installer/core/commands/lib/agent_enhancement/enhancer.py`**
- Add `enhance_batch` method
- Add parallel processing logic

**2. `installer/core/commands/agent-enhance` (if exists)**
- Add batch mode flag
- Add glob pattern support

### Recommended Implementation

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List
import logging

class SingleAgentEnhancer:
    def __init__(self, strategy: str = "hybrid", max_workers: int = 5):
        self.strategy = strategy
        self.max_workers = max_workers
        # ... existing init

    def enhance_batch(
        self,
        agent_files: List[Path],
        template_dir: Path,
        show_progress: bool = True
    ) -> List[EnhancementResult]:
        """Enhance multiple agents in parallel.

        Args:
            agent_files: List of agent file paths
            template_dir: Template directory
            show_progress: Show progress updates

        Returns:
            List[EnhancementResult]: Results for each agent
        """
        logger.info(f"Batch enhancing {len(agent_files)} agents...")

        results = []
        completed = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all enhancement tasks
            future_to_agent = {
                executor.submit(self.enhance, agent_file, template_dir): agent_file
                for agent_file in agent_files
            }

            # Process as they complete
            for future in as_completed(future_to_agent):
                agent_file = future_to_agent[future]
                completed += 1

                try:
                    result = future.result()
                    results.append(result)

                    if show_progress:
                        status = "✅" if result.success else "❌"
                        print(f"{status} [{completed}/{len(agent_files)}] {agent_file.stem}")

                except Exception as e:
                    logger.error(f"Failed to enhance {agent_file.name}: {e}")
                    results.append(EnhancementResult(
                        success=False,
                        agent_name=agent_file.stem,
                        error=str(e)
                    ))

        return results

    def _print_batch_summary(self, results: List[EnhancementResult]):
        """Print summary of batch enhancement results."""
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        print(f"\n{'='*60}")
        print(f"Batch Enhancement Complete")
        print(f"{'='*60}")
        print(f"Total agents: {len(results)}")
        print(f"✅ Successful: {len(successful)}")
        print(f"❌ Failed: {len(failed)}")

        if failed:
            print(f"\nFailed agents:")
            for result in failed:
                print(f"  - {result.agent_name}: {result.error}")

        print(f"{'='*60}")
```

### Command Line Usage

```bash
# Option 1: Explicit batch flag with glob pattern
/agent-enhance agents/*.md ~/templates/my-template --batch

# Option 2: Directory enhancement (all agents in directory)
/agent-enhance agents/ ~/templates/my-template --batch

# Option 3: Explicit file list
/agent-enhance agents/api.md agents/db.md ~/templates/my-template --batch

# With parallel configuration
/agent-enhance agents/*.md ~/templates/my-template --batch --max-workers=10

# With dry-run (preview all enhancements)
/agent-enhance agents/*.md ~/templates/my-template --batch --dry-run
```

### Performance Optimization

**Considerations**:
1. **AI Rate Limiting**: May need semaphore if AI has rate limits
2. **I/O Bound**: ThreadPool good for I/O operations
3. **CPU Bound**: If static strategy, consider ProcessPoolExecutor
4. **Memory**: Load template once, share across workers

**Optimized Version**:
```python
class BatchEnhancer:
    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        # Pre-load template data (shared across workers)
        self.template_cache = None

    def enhance_batch(self, agent_files: List[Path], template_dir: Path):
        # Load template once
        self.template_cache = self._load_template_data(template_dir)

        # Enhance agents in parallel using cached template
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [
                executor.submit(self._enhance_with_cache, agent, template_dir)
                for agent in agent_files
            ]
            return [f.result() for f in as_completed(futures)]

    def _enhance_with_cache(self, agent_file: Path, template_dir: Path):
        """Enhance using pre-loaded template cache."""
        # Use self.template_cache instead of re-loading
        ...
```

## Success Metrics

### Functional Tests
- [ ] Batch enhance 10 agents successfully
- [ ] Partial failure handled (5 succeed, 5 fail)
- [ ] Progress reporting accurate
- [ ] Summary report complete

### Performance Tests
- [ ] 10 agents in parallel faster than sequential
- [ ] Max workers configurable
- [ ] No memory leaks with 50+ agents
- [ ] Thread-safe (no race conditions)

### Error Handling
- [ ] One agent failure doesn't stop batch
- [ ] All errors collected and reported
- [ ] Exit code reflects partial failure

## Dependencies

**Blocked By**:
- TASK-AI-2B37 (AI integration) - for AI strategy to work

**Related**:
- TASK-PHASE-8-INCREMENTAL (main implementation)

## Related Review Findings

**From**: `docs/reviews/phase-8-implementation-review.md`

- **Section 5.2**: Tradeoff Analysis - Batch Processing not yet implemented
- **Section 6.4**: Future Enhancement #1 (batch enhancement)
- **Section 8**: Recommendations - Long Term #9

## Estimated Effort

**Duration**: 4 hours

**Breakdown**:
- Batch enhancement method (1.5 hours)
- Command line interface (1 hour)
- Progress reporting (0.5 hours)
- Testing (1 hour)

## Test Plan

### Unit Tests

```python
def test_batch_enhancement():
    """Test batch enhancement of multiple agents."""
    enhancer = SingleAgentEnhancer()
    agent_files = [
        Path("agents/api.md"),
        Path("agents/db.md"),
        Path("agents/ui.md"),
    ]

    results = enhancer.enhance_batch(agent_files, Path("template"))

    assert len(results) == 3
    assert all(isinstance(r, EnhancementResult) for r in results)

def test_batch_partial_failure():
    """Test batch enhancement with partial failures."""
    enhancer = SingleAgentEnhancer()
    agent_files = [
        Path("agents/valid.md"),
        Path("agents/invalid.md"),  # Will fail
        Path("agents/valid2.md"),
    ]

    results = enhancer.enhance_batch(agent_files, Path("template"))

    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    assert len(successful) == 2
    assert len(failed) == 1

def test_batch_parallel_performance():
    """Test batch enhancement is faster than sequential."""
    import time

    enhancer = SingleAgentEnhancer(max_workers=5)
    agent_files = [Path(f"agents/agent{i}.md") for i in range(10)]

    # Batch (parallel)
    start = time.time()
    enhancer.enhance_batch(agent_files, Path("template"))
    batch_time = time.time() - start

    # Sequential (for comparison)
    start = time.time()
    for agent in agent_files:
        enhancer.enhance(agent, Path("template"))
    sequential_time = time.time() - start

    # Batch should be significantly faster
    assert batch_time < sequential_time * 0.5  # At least 2x faster
```

### Integration Tests

```python
def test_batch_command_line(tmp_path):
    """Test batch enhancement via command line."""
    # Create test agents
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()

    for i in range(5):
        (agents_dir / f"agent{i}.md").write_text(f"---\nname: agent{i}\n---\n")

    # Run batch enhancement
    result = subprocess.run(
        ["/agent-enhance", str(agents_dir / "*.md"), str(tmp_path), "--batch"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0
    assert "5/5" in result.stdout  # Progress indicator
    assert "Batch Enhancement Complete" in result.stdout
```

## Notes

- **Priority**: LOW - nice to have, not blocking
- **Effort**: 4 hours (relatively easy given stateless design)
- **Impact**: User convenience for large templates
- **Risk**: LOW - additive feature

## Future Considerations

### Progressive Enhancement

Phase 1 (this task):
- Basic batch with ThreadPoolExecutor
- Progress reporting
- Error handling

Phase 2 (future):
- Intelligent scheduling (high priority agents first)
- Dependency-aware enhancement (some agents depend on others)
- Caching and optimization

Phase 3 (future):
- Distributed enhancement (multiple machines)
- Cloud-based enhancement service
- Real-time collaboration

## Example Output

```bash
$ /agent-enhance agents/*.md ~/templates/my-template --batch

Batch enhancing 8 agents...
✅ [1/8] api-service-specialist
✅ [2/8] database-specialist
❌ [3/8] cache-specialist (AI timeout, fell back to static)
✅ [4/8] domain-model-specialist
✅ [5/8] testing-specialist
✅ [6/8] ui-component-specialist
✅ [7/8] validation-specialist
✅ [8/8] logging-specialist

============================================================
Batch Enhancement Complete
============================================================
Total agents: 8
✅ Successful: 8
❌ Failed: 0

Duration: 2 minutes 34 seconds
Average: 19 seconds per agent
============================================================
```

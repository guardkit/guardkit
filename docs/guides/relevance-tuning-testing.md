# Relevance Tuning Testing Guide

> **Purpose**: Manual testing procedures for validating context retrieval relevance and quality metrics.
>
> **Task**: TASK-GR6-011
> **Feature**: FEAT-GR-006 (Job-Specific Context Retrieval)

---

## Overview

This guide provides manual testing procedures for validating that relevance tuning correctly filters context retrieval results based on task characteristics. The relevance tuning system uses configurable thresholds to ensure high-quality, relevant context is returned for each task type.

---

## Relevance Threshold Configuration

### Default Thresholds

| Task Type | Threshold | Rationale |
|-----------|-----------|-----------|
| First-of-type | 0.5 | More inclusive - needs broader context for novel tasks |
| Standard | 0.6 | Balanced filtering for typical tasks |
| Refinement | 0.55 | Slightly more inclusive - needs context about similar approaches |
| AutoBuild | 0.5 | More inclusive - autonomous workflows benefit from more context |

### Configuration Options

```python
from guardkit.knowledge.relevance_tuning import (
    RelevanceConfig,
    default_config,
    strict_config,
    relaxed_config,
)

# Default thresholds
config = default_config()  # first_of_type=0.5, standard=0.6, refinement=0.55

# Stricter filtering (higher quality, fewer results)
config = strict_config()  # first_of_type=0.6, standard=0.7, refinement=0.65

# More inclusive (more results, potentially lower relevance)
config = relaxed_config()  # first_of_type=0.35, standard=0.45, refinement=0.4

# Custom configuration
config = RelevanceConfig(
    first_of_type_threshold=0.45,
    standard_threshold=0.65,
    refinement_threshold=0.5,
    autobuild_threshold=0.45,
)
```

---

## Test Scenarios

### Scenario 1: First-of-Type Task

**Description**: Test context retrieval for a task that is the first of its type in the project.

**Setup**:
```python
from guardkit.knowledge.task_analyzer import TaskCharacteristics, TaskType, TaskPhase
from guardkit.knowledge.relevance_tuning import default_config

characteristics = TaskCharacteristics(
    task_id="TASK-TEST-001",
    description="Implement new GraphQL endpoint",
    tech_stack="python",
    task_type=TaskType.IMPLEMENTATION,
    current_phase=TaskPhase.IMPLEMENT,
    complexity=5,
    is_first_of_type=True,  # First GraphQL task
    similar_task_count=0,
    feature_id="FEAT-API-001",
    is_refinement=False,
    refinement_attempt=0,
    previous_failure_type=None,
    avg_turns_for_type=3.0,
    success_rate_for_type=0.8,
)

config = default_config()
threshold = config.get_threshold(characteristics)
assert threshold == 0.5, f"Expected 0.5, got {threshold}"
```

**Expected Behavior**:
- Threshold should be 0.5 (lower to allow more context)
- More results should pass filtering
- Architecture and pattern context should be emphasized

**Verification Checklist**:
- [ ] Threshold returns 0.5 for first-of-type tasks
- [ ] Retrieved context includes architecture guidance
- [ ] Retrieved context includes relevant patterns
- [ ] Context budget is increased by 30% for novelty

---

### Scenario 2: Standard Implementation Task

**Description**: Test context retrieval for a typical implementation task.

**Setup**:
```python
characteristics = TaskCharacteristics(
    task_id="TASK-TEST-002",
    description="Add validation to user registration",
    tech_stack="python",
    task_type=TaskType.IMPLEMENTATION,
    current_phase=TaskPhase.IMPLEMENT,
    complexity=4,
    is_first_of_type=False,
    similar_task_count=5,  # Similar validation tasks exist
    feature_id="FEAT-USER-001",
    is_refinement=False,
    refinement_attempt=0,
    previous_failure_type=None,
    avg_turns_for_type=2.5,
    success_rate_for_type=0.85,
)

config = default_config()
threshold = config.get_threshold(characteristics)
assert threshold == 0.6, f"Expected 0.6, got {threshold}"
```

**Expected Behavior**:
- Threshold should be 0.6 (standard filtering)
- Only results above 0.6 relevance score should pass
- Balanced context allocation across categories

**Verification Checklist**:
- [ ] Threshold returns 0.6 for standard tasks
- [ ] Low-relevance results (score < 0.6) are filtered out
- [ ] Context quality remains high (>70% relevance rate)

---

### Scenario 3: Refinement Task

**Description**: Test context retrieval for a task that is a retry after a previous failure.

**Setup**:
```python
characteristics = TaskCharacteristics(
    task_id="TASK-TEST-003",
    description="Fix authentication middleware",
    tech_stack="python",
    task_type=TaskType.IMPLEMENTATION,
    current_phase=TaskPhase.IMPLEMENT,
    complexity=5,
    is_first_of_type=False,
    similar_task_count=3,
    feature_id="FEAT-AUTH-001",
    is_refinement=True,  # This is a retry
    refinement_attempt=2,
    previous_failure_type="circular_dependency",
    avg_turns_for_type=4.0,
    success_rate_for_type=0.7,
)

config = default_config()
threshold = config.get_threshold(characteristics)
assert threshold == 0.55, f"Expected 0.55, got {threshold}"
```

**Expected Behavior**:
- Threshold should be 0.55 (slightly more inclusive for refinements)
- Warning and failure pattern context should be emphasized
- Context budget increased by 20% for refinement bonus

**Verification Checklist**:
- [ ] Threshold returns 0.55 for refinement tasks
- [ ] Warnings section is prominently included
- [ ] Context about similar failures is retrieved
- [ ] Budget allocation shifts toward warnings (35%)

---

### Scenario 4: AutoBuild Task

**Description**: Test context retrieval for tasks running in `/feature-build` autonomous mode.

**Setup**:
```python
characteristics = TaskCharacteristics(
    task_id="TASK-TEST-004",
    description="Implement user profile page",
    tech_stack="python",
    task_type=TaskType.IMPLEMENTATION,
    current_phase=TaskPhase.IMPLEMENT,
    complexity=5,
    is_first_of_type=False,
    similar_task_count=2,
    feature_id="FEAT-USER-001",
    is_refinement=False,
    refinement_attempt=0,
    previous_failure_type=None,
    avg_turns_for_type=3.0,
    success_rate_for_type=0.8,
    current_actor="player",
    turn_number=2,
    is_autobuild=True,  # Running in AutoBuild mode
    has_previous_turns=True,
)

config = default_config()
threshold = config.get_threshold(characteristics)
assert threshold == 0.5, f"Expected 0.5, got {threshold}"
```

**Expected Behavior**:
- Threshold should be 0.5 (AutoBuild takes priority)
- Role constraints context should be included
- Turn state context from previous turns should be loaded
- Quality gate configs should be retrieved

**Verification Checklist**:
- [ ] Threshold returns 0.5 for AutoBuild tasks
- [ ] Role constraints section is present in context
- [ ] Previous turn context is loaded
- [ ] Quality gate thresholds are specified

---

### Scenario 5: Review Task

**Description**: Test context retrieval for code review tasks.

**Setup**:
```python
characteristics = TaskCharacteristics(
    task_id="TASK-TEST-005",
    description="Review authentication implementation",
    tech_stack="python",
    task_type=TaskType.REVIEW,
    current_phase=TaskPhase.REVIEW,
    complexity=4,
    is_first_of_type=False,
    similar_task_count=4,
    feature_id=None,
    is_refinement=False,
    refinement_attempt=0,
    previous_failure_type=None,
    avg_turns_for_type=1.5,
    success_rate_for_type=0.9,
)

config = default_config()
threshold = config.get_threshold(characteristics)
assert threshold == 0.6, f"Expected 0.6, got {threshold}"
```

**Expected Behavior**:
- Threshold should be 0.6 (standard for review tasks)
- Pattern and architecture context should be emphasized
- Budget allocation shifts toward patterns (30%) and architecture (25%)

**Verification Checklist**:
- [ ] Threshold returns 0.6 for review tasks
- [ ] Pattern context allocation is ~30%
- [ ] Architecture context allocation is ~25%

---

## Quality Metrics Testing

### Metric Collection

```python
from guardkit.knowledge.relevance_tuning import MetricsCollector, ContextQualityMetrics

# Create collector with threshold and budget
collector = MetricsCollector(
    threshold=0.6,
    total_budget=4000,
    budget_per_category={"feature_context": 10, "similar_outcomes": 10}
)

# Simulate adding results during retrieval
collector.add_result({"score": 0.8, "fact": "Pattern A"}, category="similar_outcomes")
collector.add_result({"score": 0.7, "fact": "Pattern B"}, category="similar_outcomes")
collector.add_result({"score": 0.5, "fact": "Pattern C"}, category="similar_outcomes")  # Below threshold
collector.add_result({"score": 0.9, "fact": "Feature X"}, category="feature_context")

# Track budget usage
collector.add_budget_usage(2500)

# Get aggregated metrics
metrics = collector.get_metrics()

# Verify metrics
assert metrics.total_items_retrieved == 4
assert metrics.items_above_threshold == 3  # 0.8, 0.7, 0.9
assert metrics.items_below_threshold == 1  # 0.5
assert metrics.relevance_rate == 0.75  # 3/4
assert metrics.budget_utilization == 0.625  # 2500/4000
assert metrics.is_quality_acceptable()  # 0.75 >= 0.7
```

### Quality Acceptance Criteria

| Metric | Minimum Acceptable | Target | Excellent |
|--------|-------------------|--------|-----------|
| Relevance Rate | 70% | 80% | 90%+ |
| Budget Utilization | 60% | 75% | 85-95% |
| Avg Relevance Score | 0.55 | 0.65 | 0.75+ |

---

## Integration Testing

### Test with JobContextRetriever

```python
import asyncio
from guardkit.knowledge.job_context_retriever import JobContextRetriever
from guardkit.knowledge.task_analyzer import TaskPhase

async def test_integration():
    # Create retriever with default config
    retriever = JobContextRetriever(
        graphiti=mock_graphiti_client,
        relevance_config=default_config()
    )

    # Test task data
    task = {
        "id": "TASK-INT-001",
        "description": "Add caching to API endpoints",
        "tech_stack": "python",
        "task_type": "implementation",
        "complexity": 5,
        "feature_id": "FEAT-PERF-001",
    }

    # Retrieve with metrics
    context = await retriever.retrieve(
        task=task,
        phase=TaskPhase.IMPLEMENT,
        collect_metrics=True
    )

    # Verify context structure
    assert context.task_id == "TASK-INT-001"
    assert context.budget_used <= context.budget_total

    # Verify metrics
    metrics = context.metrics
    assert metrics.is_quality_acceptable()

    # Print context for manual review
    print(context.to_prompt())

    return context

# Run test
context = asyncio.run(test_integration())
```

---

## Troubleshooting

### Issue: All Results Filtered Out

**Symptom**: Context is empty despite Graphiti returning results.

**Diagnosis**:
```python
# Check if threshold is too high
config = RelevanceConfig(standard_threshold=0.9)  # Very strict
# Most results will be filtered

# Solution: Use relaxed config for initial testing
config = relaxed_config()
```

### Issue: Too Many Irrelevant Results

**Symptom**: Context includes low-quality items.

**Diagnosis**:
```python
# Check if threshold is too low
config = RelevanceConfig(standard_threshold=0.3)  # Too permissive

# Solution: Increase threshold
config = strict_config()
```

### Issue: Budget Exceeded

**Symptom**: Retrieved context uses more tokens than allocated.

**Diagnosis**:
```python
# Check budget utilization
metrics = collector.get_metrics()
if metrics.budget_utilization > 1.0:
    print(f"Budget exceeded by {(metrics.budget_utilization - 1.0) * 100:.1f}%")

# Solution: Reduce max_results_per_category or increase budget
```

---

## Performance Benchmarks

### Expected Performance

| Operation | Target | Maximum |
|-----------|--------|---------|
| Task Analysis | < 100ms | 200ms |
| Budget Calculation | < 10ms | 50ms |
| Context Retrieval | < 2000ms | 5000ms |
| Metrics Calculation | < 10ms | 50ms |

### Load Testing

```python
import time
import statistics

async def benchmark_retrieval(retriever, task, iterations=10):
    times = []
    for _ in range(iterations):
        start = time.time()
        await retriever.retrieve(task, TaskPhase.IMPLEMENT)
        times.append(time.time() - start)

    print(f"Average: {statistics.mean(times)*1000:.1f}ms")
    print(f"Median: {statistics.median(times)*1000:.1f}ms")
    print(f"P95: {sorted(times)[int(len(times)*0.95)]*1000:.1f}ms")
```

---

## Regression Testing Checklist

Before releasing changes to relevance tuning:

- [ ] All unit tests pass (`pytest tests/knowledge/test_relevance_tuning.py -v`)
- [ ] Integration tests pass (`pytest tests/knowledge/test_job_context_retriever.py -v`)
- [ ] First-of-type threshold is 0.5
- [ ] Standard threshold is 0.6
- [ ] Refinement threshold is 0.55
- [ ] AutoBuild threshold is 0.5
- [ ] Quality metrics calculation is accurate
- [ ] Budget allocation sums to 1.0
- [ ] No performance regression (retrieval < 2s)

---

## See Also

- [FEAT-GR-006: Job-Specific Context Retrieval](../../research/graphiti-refinement/FEAT-GR-006-job-specific-context.md)
- [Graphiti Integration Guide](./graphiti-integration-guide.md)
- [AutoBuild Workflow Guide](./autobuild-workflow.md)

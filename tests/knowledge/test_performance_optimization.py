"""
Tests for performance optimization in JobContextRetriever (TASK-GR6-012).

TDD RED Phase Tests - All tests should FAIL initially.

This module tests the following performance optimizations:
1. Parallel queries using asyncio.gather() for independent categories
2. LRU cache for static context (patterns, architecture)
3. Connection pooling for Neo4j/Graphiti (ensure single client reuse)
4. Early termination when budget exhausted

Benchmark targets:
- Simple task (complexity 1-3): < 500ms
- Medium task (complexity 4-6): < 1000ms
- Complex task (complexity 7-10): < 2000ms

References:
    - TASK-GR6-012: Performance optimization for context retrieval
    - FEAT-GR-006: Job-Specific Context Retrieval
"""

import asyncio
import json
import time
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from guardkit.knowledge.job_context_retriever import JobContextRetriever, RetrievedContext
from guardkit.knowledge.task_analyzer import TaskPhase


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_graphiti():
    """Create a mock Graphiti client with realistic search behavior."""
    graphiti = MagicMock()

    # Default search response with delay to simulate network latency
    async def mock_search(query: str, group_ids: List[str] = None, num_results: int = 10):
        # Simulate network latency (50ms per query)
        await asyncio.sleep(0.05)

        # Return mock results based on group_ids
        if not group_ids:
            return []

        group_id = group_ids[0] if group_ids else ""

        # Return realistic mock data
        return [
            {
                "name": f"Item from {group_id}",
                "content": f"Content for {query}",
                "score": 0.85,
            }
        ]

    graphiti.search = AsyncMock(side_effect=mock_search)
    return graphiti


@pytest.fixture
def simple_task():
    """Create a simple task (complexity 1-3)."""
    return {
        "id": "TASK-SIMPLE-001",
        "description": "Fix typo in documentation",
        "tech_stack": "python",
        "complexity": 2,
    }


@pytest.fixture
def medium_task():
    """Create a medium complexity task (complexity 4-6)."""
    return {
        "id": "TASK-MEDIUM-001",
        "description": "Add user authentication endpoint",
        "tech_stack": "python",
        "complexity": 5,
    }


@pytest.fixture
def complex_task():
    """Create a complex task (complexity 7-10)."""
    return {
        "id": "TASK-COMPLEX-001",
        "description": "Refactor authentication system with OAuth2 support",
        "tech_stack": "python",
        "complexity": 8,
    }


# ============================================================================
# Test 1: Parallel Queries Faster Than Sequential
# ============================================================================


@pytest.mark.asyncio
async def test_parallel_queries_faster_than_sequential(mock_graphiti, simple_task):
    """
    Test that parallel queries are faster than sequential queries.

    This test should FAIL initially because JobContextRetriever currently
    makes SEQUENTIAL queries (one after another).

    Expected behavior (after optimization):
    - Parallel queries should complete in ~50-100ms (single batch)
    - Sequential queries would take ~300-400ms (6-8 categories × 50ms)
    - Speedup should be at least 2x

    Current behavior (will FAIL):
    - All queries are sequential, so no speedup observed
    """
    retriever = JobContextRetriever(mock_graphiti)

    # Measure sequential baseline (current implementation)
    start_sequential = time.perf_counter()
    context_sequential = await retriever.retrieve(simple_task, TaskPhase.IMPLEMENT)
    duration_sequential = (time.perf_counter() - start_sequential) * 1000  # Convert to ms

    # Measure parallel (optimized implementation - NOT YET IMPLEMENTED)
    # This will fail because parallel queries are not implemented yet
    start_parallel = time.perf_counter()
    context_parallel = await retriever.retrieve_parallel(simple_task, TaskPhase.IMPLEMENT)
    duration_parallel = (time.perf_counter() - start_parallel) * 1000  # Convert to ms

    # Verify parallel is at least 2x faster
    speedup = duration_sequential / duration_parallel
    assert speedup >= 2.0, (
        f"Parallel queries should be at least 2x faster. "
        f"Sequential: {duration_sequential:.1f}ms, "
        f"Parallel: {duration_parallel:.1f}ms, "
        f"Speedup: {speedup:.2f}x"
    )

    # Verify both return the same data
    assert context_parallel.feature_context == context_sequential.feature_context
    assert context_parallel.similar_outcomes == context_sequential.similar_outcomes


# ============================================================================
# Test 2: Parallel Queries Retrieve All Categories
# ============================================================================


@pytest.mark.asyncio
async def test_parallel_queries_all_categories_retrieved(mock_graphiti, medium_task):
    """
    Test that parallel queries retrieve all expected categories.

    This test should FAIL initially because retrieve_parallel() doesn't exist.

    Expected behavior (after optimization):
    - All 6 standard categories retrieved
    - All 4 AutoBuild categories retrieved (if is_autobuild=True)
    - No data loss compared to sequential queries

    Current behavior (will FAIL):
    - Method doesn't exist yet
    """
    retriever = JobContextRetriever(mock_graphiti)

    # Test standard task (6 categories)
    context = await retriever.retrieve_parallel(medium_task, TaskPhase.IMPLEMENT)

    # Verify all standard categories are present
    assert isinstance(context.feature_context, list)
    assert isinstance(context.similar_outcomes, list)
    assert isinstance(context.relevant_patterns, list)
    assert isinstance(context.architecture_context, list)
    assert isinstance(context.warnings, list)
    assert isinstance(context.domain_knowledge, list)

    # Verify budget tracking
    assert context.budget_used >= 0
    assert context.budget_total > 0

    # Test AutoBuild task (10 categories)
    autobuild_task = {**medium_task, "is_autobuild": True}
    context_autobuild = await retriever.retrieve_parallel(autobuild_task, TaskPhase.IMPLEMENT)

    # Verify AutoBuild categories are present
    assert isinstance(context_autobuild.role_constraints, list)
    assert isinstance(context_autobuild.quality_gate_configs, list)
    assert isinstance(context_autobuild.turn_states, list)
    assert isinstance(context_autobuild.implementation_modes, list)


# ============================================================================
# Test 3: Cache Hit Returns Cached Data
# ============================================================================


@pytest.mark.asyncio
async def test_cache_hit_returns_cached_data(mock_graphiti, simple_task):
    """
    Test that cache hit returns cached data without querying Graphiti.

    This test should FAIL initially because caching is not implemented.

    Expected behavior (after optimization):
    - First query hits Graphiti
    - Second query with same parameters returns cached data
    - Graphiti is NOT called on cache hit
    - Cached data matches original query result

    Current behavior (will FAIL):
    - No caching implemented, so Graphiti is called every time
    """
    retriever = JobContextRetriever(mock_graphiti)

    # First query - should hit Graphiti
    context1 = await retriever.retrieve(simple_task, TaskPhase.IMPLEMENT)
    first_call_count = mock_graphiti.search.call_count

    # Second query with same parameters - should hit cache
    context2 = await retriever.retrieve(simple_task, TaskPhase.IMPLEMENT)
    second_call_count = mock_graphiti.search.call_count

    # Verify cache hit (no additional Graphiti calls)
    assert second_call_count == first_call_count, (
        f"Expected cache hit (no additional calls), but Graphiti was called again. "
        f"First: {first_call_count} calls, Second: {second_call_count} calls"
    )

    # Verify cached data matches original
    assert context2.feature_context == context1.feature_context
    assert context2.similar_outcomes == context1.similar_outcomes
    assert context2.budget_used == context1.budget_used


# ============================================================================
# Test 4: Cache Miss Queries Graphiti
# ============================================================================


@pytest.mark.asyncio
async def test_cache_miss_queries_graphiti(mock_graphiti, simple_task, medium_task):
    """
    Test that cache miss triggers new Graphiti query.

    This test should FAIL initially because caching is not implemented.

    Expected behavior (after optimization):
    - First query for task A hits Graphiti
    - Query for task B (different description) hits Graphiti again
    - Each unique query gets its own cache entry

    Current behavior (will FAIL):
    - No caching logic exists
    """
    retriever = JobContextRetriever(mock_graphiti)

    # First query - different task
    context1 = await retriever.retrieve(simple_task, TaskPhase.IMPLEMENT)
    first_call_count = mock_graphiti.search.call_count

    # Second query - different task (cache miss)
    context2 = await retriever.retrieve(medium_task, TaskPhase.IMPLEMENT)
    second_call_count = mock_graphiti.search.call_count

    # Verify cache miss (additional Graphiti calls)
    assert second_call_count > first_call_count, (
        f"Expected cache miss (additional calls), but call count didn't increase. "
        f"First: {first_call_count} calls, Second: {second_call_count} calls"
    )

    # Verify different results for different tasks
    # (The actual content might differ based on mock implementation)
    assert context1.task_id != context2.task_id


# ============================================================================
# Test 5: Cache TTL Expires
# ============================================================================


@pytest.mark.asyncio
async def test_cache_ttl_expires(mock_graphiti, simple_task):
    """
    Test that cache entries expire after TTL.

    This test should FAIL initially because caching with TTL is not implemented.

    Expected behavior (after optimization):
    - First query hits Graphiti and caches result
    - Second query within TTL hits cache
    - Third query after TTL expires hits Graphiti again

    Current behavior (will FAIL):
    - No TTL mechanism exists
    """
    # Configure retriever with short TTL for testing (e.g., 100ms)
    retriever = JobContextRetriever(mock_graphiti, cache_ttl=0.1)  # 100ms TTL

    # First query - should hit Graphiti
    context1 = await retriever.retrieve(simple_task, TaskPhase.IMPLEMENT)
    first_call_count = mock_graphiti.search.call_count

    # Second query immediately - should hit cache
    context2 = await retriever.retrieve(simple_task, TaskPhase.IMPLEMENT)
    second_call_count = mock_graphiti.search.call_count

    # Verify cache hit
    assert second_call_count == first_call_count, "Expected cache hit before TTL expires"

    # Wait for TTL to expire
    await asyncio.sleep(0.15)  # Wait 150ms (TTL is 100ms)

    # Third query after TTL - should hit Graphiti again
    context3 = await retriever.retrieve(simple_task, TaskPhase.IMPLEMENT)
    third_call_count = mock_graphiti.search.call_count

    # Verify cache miss after TTL
    assert third_call_count > second_call_count, (
        f"Expected cache miss after TTL expires, but no additional calls. "
        f"Second: {second_call_count} calls, Third: {third_call_count} calls"
    )


# ============================================================================
# Test 6: Early Termination When Budget Exhausted
# ============================================================================


@pytest.mark.asyncio
async def test_early_termination_when_budget_exhausted(mock_graphiti, complex_task):
    """
    Test that retrieval stops early when budget is exhausted.

    This test should FAIL initially because early termination is not implemented.

    Expected behavior (after optimization):
    - Categories are processed in priority order
    - Processing stops when budget is full (>= 95% used)
    - Low-priority categories are skipped if budget exhausted
    - Graphiti calls are minimized

    Current behavior (will FAIL):
    - All categories are always queried, even if budget full
    """
    # Create a mock that returns large results
    async def mock_large_search(query: str, group_ids: List[str] = None, num_results: int = 10):
        await asyncio.sleep(0.05)
        # Return large results that will consume budget quickly
        return [
            {
                "name": f"Large item {i}",
                "content": "x" * 500,  # 500 chars = ~250 tokens
                "score": 0.9,
            }
            for i in range(10)
        ]

    mock_graphiti.search = AsyncMock(side_effect=mock_large_search)

    retriever = JobContextRetriever(mock_graphiti)

    # Retrieve with early termination enabled
    context = await retriever.retrieve(complex_task, TaskPhase.IMPLEMENT, early_termination=True)

    # Verify budget exhaustion triggered early stop
    budget_usage_ratio = context.budget_used / context.budget_total
    assert budget_usage_ratio >= 0.95, (
        f"Expected budget to be nearly full (>= 95%), but got {budget_usage_ratio:.2%}"
    )

    # Verify not all categories were queried (early stop)
    call_count = mock_graphiti.search.call_count
    max_categories = 10  # 6 standard + 4 AutoBuild (if enabled)

    # Early termination should result in fewer calls than max categories
    # (at least one category should be skipped)
    assert call_count < max_categories, (
        f"Expected early termination to skip some categories, "
        f"but all {call_count} categories were queried"
    )


# ============================================================================
# Test 7: Benchmark Simple Task Under 500ms
# ============================================================================


@pytest.mark.asyncio
async def test_benchmark_simple_task_under_500ms(mock_graphiti, simple_task):
    """
    Test that simple tasks complete in < 500ms.

    This test should FAIL initially due to sequential queries and no caching.

    Expected behavior (after optimization):
    - Parallel queries reduce latency
    - Cache hits on static context (patterns, architecture)
    - Total retrieval time < 500ms

    Current behavior (will FAIL):
    - Sequential queries take ~300-400ms
    - No caching adds overhead
    - Total time likely > 500ms
    """
    retriever = JobContextRetriever(mock_graphiti)

    # Warm up cache (if caching is implemented)
    await retriever.retrieve(simple_task, TaskPhase.IMPLEMENT)

    # Benchmark retrieval
    start = time.perf_counter()
    context = await retriever.retrieve(simple_task, TaskPhase.IMPLEMENT)
    duration_ms = (time.perf_counter() - start) * 1000

    # Verify performance target
    assert duration_ms < 500, (
        f"Simple task should complete in < 500ms, but took {duration_ms:.1f}ms"
    )

    # Verify we got valid context
    assert context.task_id == simple_task["id"]
    assert context.budget_used > 0


# ============================================================================
# Test 8: Benchmark Medium Task Under 1000ms
# ============================================================================


@pytest.mark.asyncio
async def test_benchmark_medium_task_under_1000ms(mock_graphiti, medium_task):
    """
    Test that medium complexity tasks complete in < 1000ms.

    This test should FAIL initially due to sequential queries and no optimization.

    Expected behavior (after optimization):
    - Parallel queries reduce latency
    - Partial caching helps
    - Total retrieval time < 1000ms

    Current behavior (will FAIL):
    - Sequential queries take longer for more categories
    - Total time likely > 1000ms
    """
    retriever = JobContextRetriever(mock_graphiti)

    # Warm up cache
    await retriever.retrieve(medium_task, TaskPhase.IMPLEMENT)

    # Benchmark retrieval
    start = time.perf_counter()
    context = await retriever.retrieve(medium_task, TaskPhase.IMPLEMENT)
    duration_ms = (time.perf_counter() - start) * 1000

    # Verify performance target
    assert duration_ms < 1000, (
        f"Medium task should complete in < 1000ms, but took {duration_ms:.1f}ms"
    )

    # Verify we got valid context
    assert context.task_id == medium_task["id"]
    assert context.budget_used > 0


# ============================================================================
# Test 9: Benchmark Complex Task Under 2000ms
# ============================================================================


@pytest.mark.asyncio
async def test_benchmark_complex_task_under_2000ms(mock_graphiti, complex_task):
    """
    Test that complex tasks complete in < 2000ms.

    This test should FAIL initially due to all optimization issues.

    Expected behavior (after optimization):
    - Parallel queries reduce latency significantly
    - Early termination prevents unnecessary queries
    - Caching helps on repeated access
    - Total retrieval time < 2000ms

    Current behavior (will FAIL):
    - Sequential queries for all categories
    - No early termination
    - Total time likely > 2000ms
    """
    retriever = JobContextRetriever(mock_graphiti)

    # Warm up cache
    await retriever.retrieve(complex_task, TaskPhase.IMPLEMENT)

    # Benchmark retrieval
    start = time.perf_counter()
    context = await retriever.retrieve(complex_task, TaskPhase.IMPLEMENT)
    duration_ms = (time.perf_counter() - start) * 1000

    # Verify performance target
    assert duration_ms < 2000, (
        f"Complex task should complete in < 2000ms, but took {duration_ms:.1f}ms"
    )

    # Verify we got valid context
    assert context.task_id == complex_task["id"]
    assert context.budget_used > 0


# ============================================================================
# Test 10: Connection Reuse
# ============================================================================


@pytest.mark.asyncio
async def test_connection_reuse(mock_graphiti, simple_task, medium_task, complex_task):
    """
    Test that the same Graphiti client instance is reused across queries.

    This test should FAIL if new connections are created for each query.

    Expected behavior (after optimization):
    - Single Graphiti client instance
    - Connection pooling handles concurrency
    - No new client creation per query

    Current behavior (may PASS or FAIL depending on implementation):
    - If client is already reused, this will pass
    - If new clients are created, this will fail
    """
    retriever = JobContextRetriever(mock_graphiti)

    # Store original client instance
    original_client = retriever.graphiti

    # Make multiple queries
    await retriever.retrieve(simple_task, TaskPhase.IMPLEMENT)
    await retriever.retrieve(medium_task, TaskPhase.IMPLEMENT)
    await retriever.retrieve(complex_task, TaskPhase.IMPLEMENT)

    # Verify same client instance is used
    assert retriever.graphiti is original_client, (
        "Expected same Graphiti client instance to be reused, "
        "but a new client was created"
    )

    # Verify the client was called (not replaced with a new instance)
    assert mock_graphiti.search.call_count > 0, (
        "Expected Graphiti client to be used, but search was never called"
    )


# ============================================================================
# Additional Helper Tests
# ============================================================================


@pytest.mark.asyncio
async def test_parallel_vs_sequential_call_count(mock_graphiti, simple_task):
    """
    Test that parallel queries make the same number of Graphiti calls as sequential.

    Parallel execution should not change the number of queries, only their timing.

    This test should FAIL initially because retrieve_parallel() doesn't exist.
    """
    retriever = JobContextRetriever(mock_graphiti)

    # Sequential queries
    mock_graphiti.search.reset_mock()
    context_sequential = await retriever.retrieve(simple_task, TaskPhase.IMPLEMENT)
    sequential_calls = mock_graphiti.search.call_count

    # Parallel queries
    mock_graphiti.search.reset_mock()
    context_parallel = await retriever.retrieve_parallel(simple_task, TaskPhase.IMPLEMENT)
    parallel_calls = mock_graphiti.search.call_count

    # Verify same number of calls
    assert parallel_calls == sequential_calls, (
        f"Parallel should make same number of calls as sequential. "
        f"Sequential: {sequential_calls}, Parallel: {parallel_calls}"
    )


@pytest.mark.asyncio
async def test_cache_key_includes_task_description(mock_graphiti):
    """
    Test that cache key includes task description for uniqueness.

    This test should FAIL initially because caching is not implemented.

    Different tasks with different descriptions should have separate cache entries.
    """
    retriever = JobContextRetriever(mock_graphiti)

    task1 = {"id": "TASK-001", "description": "Fix bug in auth", "tech_stack": "python"}
    task2 = {"id": "TASK-002", "description": "Add new endpoint", "tech_stack": "python"}

    # Query both tasks
    await retriever.retrieve(task1, TaskPhase.IMPLEMENT)
    first_call_count = mock_graphiti.search.call_count

    await retriever.retrieve(task2, TaskPhase.IMPLEMENT)
    second_call_count = mock_graphiti.search.call_count

    # Verify cache miss (different descriptions)
    assert second_call_count > first_call_count, (
        "Expected cache miss for different task description"
    )

    # Query task1 again - should hit cache
    await retriever.retrieve(task1, TaskPhase.IMPLEMENT)
    third_call_count = mock_graphiti.search.call_count

    # Verify cache hit (same description)
    assert third_call_count == second_call_count, (
        "Expected cache hit for same task description"
    )


@pytest.mark.asyncio
async def test_early_termination_priority_order(mock_graphiti, complex_task):
    """
    Test that high-priority categories are queried first during early termination.

    This test should FAIL initially because priority-based query ordering is not implemented.

    When budget is limited, high-priority categories (similar_outcomes, relevant_patterns)
    should be retrieved before low-priority categories (domain_knowledge).
    """
    # Create a mock that exhausts budget quickly
    call_order = []

    async def mock_tracked_search(query: str, group_ids: List[str] = None, num_results: int = 10):
        if group_ids:
            call_order.append(group_ids[0])
        await asyncio.sleep(0.05)
        return [{
            "name": f"Item from {group_ids[0] if group_ids else 'unknown'}",
            "content": "x" * 1000,  # Large content to exhaust budget
            "score": 0.9,
        }]

    mock_graphiti.search = AsyncMock(side_effect=mock_tracked_search)

    retriever = JobContextRetriever(mock_graphiti)
    context = await retriever.retrieve(complex_task, TaskPhase.IMPLEMENT, early_termination=True)

    # Define expected priority order (high to low)
    high_priority = ["feature_specs", "task_outcomes", "patterns_python"]
    low_priority = ["domain_knowledge"]

    # Verify high-priority categories were queried
    for group_id in high_priority:
        assert group_id in call_order, (
            f"High-priority category '{group_id}' should be queried first"
        )

    # Verify low-priority categories were skipped (if budget exhausted)
    budget_ratio = context.budget_used / context.budget_total
    if budget_ratio >= 0.95:
        for group_id in low_priority:
            assert group_id not in call_order, (
                f"Low-priority category '{group_id}' should be skipped when budget exhausted"
            )

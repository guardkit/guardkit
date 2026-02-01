# Graphiti Context Retrieval Troubleshooting Guide

This guide helps diagnose and resolve issues with job-specific context retrieval in GuardKit.

## Overview

Job-specific context retrieval (FEAT-GR-006) automatically loads relevant knowledge for each task based on its characteristics. When context isn't behaving as expected, this guide will help you identify and fix the issue.

## Common Issues

### 1. Context Missing Relevant Information

**Symptoms**:
- Task execution lacks expected knowledge
- Similar past tasks aren't referenced
- Architecture context not appearing
- Warnings from past failures missing

**Diagnosis**:

```bash
# Check if knowledge exists in Graphiti
guardkit graphiti search "your task description" --limit 20

# Check specific groups
guardkit graphiti search "architecture patterns" --group patterns
guardkit graphiti search "failed approach" --group failure_patterns
```

**Solutions**:

#### If No Results Found:
Knowledge hasn't been seeded to Graphiti.

```bash
# Seed system context
guardkit graphiti seed

# Add specific context
guardkit graphiti add-context "architecture pattern: use FastAPI dependency injection for database sessions"

# Capture interactive knowledge
guardkit graphiti capture --interactive --focus architecture
```

#### If Results Exist But Aren't Retrieved:
Relevance threshold too strict or task description not specific enough.

```python
# Option 1: Lower relevance threshold (in code)
# Edit guardkit/knowledge/relevance_tuning.py
config = RelevanceConfig(
    standard_threshold=0.5,  # Lower from 0.6
    first_of_type_threshold=0.4  # Lower from 0.5
)

# Option 2: Make task description more specific
# Edit task file to include relevant keywords:
---
description: "Implement authentication using FastAPI dependency injection pattern"
# Instead of just "Implement authentication"
---
```

### 2. Context Contains Irrelevant Information

**Symptoms**:
- Retrieved context not applicable to task
- Token budget wasted on unrelated facts
- Relevance scores consistently low (<0.5)

**Diagnosis**:

```bash
# Enable verbose logging to see retrieval details
GUARDKIT_LOG_LEVEL=DEBUG /task-work TASK-XXX 2>&1 | grep "Retrieved context"

# Check quality of seeded knowledge
guardkit graphiti search "your query" --limit 20
# Look for irrelevant results with high scores
```

**Solutions**:

#### If Seeded Knowledge is Low Quality:
Clean up and re-seed.

```bash
# Remove all system context
guardkit graphiti seed --force

# Re-add high-quality knowledge
guardkit graphiti capture --interactive
```

#### If Relevance Threshold Too Low:
Increase threshold for higher precision.

```python
# Edit guardkit/knowledge/relevance_tuning.py
config = RelevanceConfig(
    standard_threshold=0.7,  # Increase from 0.6
    refinement_threshold=0.6  # Increase from 0.5
)
```

### 3. Context Budget Exceeded

**Symptoms**:
- Error: "Context budget exceeded"
- Truncated context sections
- Missing expected context categories

**Diagnosis**:

This should **rarely occur** - budget is enforced via trimming logic.

```bash
# Check if this is reproducible
GUARDKIT_LOG_LEVEL=DEBUG /task-work TASK-XXX 2>&1 | grep "budget"
```

**Solutions**:

#### If Budget Exceeded:
This is likely a bug - the trimming logic should prevent this.

```bash
# Report as bug with:
# 1. Task characteristics (complexity, type, is_autobuild)
# 2. Retrieved context sizes
# 3. Full debug logs

# Workaround: Increase budget (temporary)
# Edit guardkit/knowledge/budget_calculator.py
BASE_BUDGETS = {
    (1, 3): 3000,   # Increase from 2000
    (4, 6): 6000,   # Increase from 4000
    (7, 10): 9000   # Increase from 6000
}
```

### 4. AutoBuild Context Missing

**Symptoms**:
- Role constraints not appearing during /feature-build
- Quality gate configs missing
- Turn states not loaded on Turn 2+
- Implementation modes not referenced

**Diagnosis**:

```bash
# Check if AutoBuild context is seeded
guardkit graphiti search "role constraints player" --group role_constraints
guardkit graphiti search "quality gate coverage" --group quality_gate_configs
guardkit graphiti search "turn state" --group turn_states

# Check task metadata
grep "is_autobuild" tasks/*/TASK-XXX*.md
```

**Solutions**:

#### If AutoBuild Groups Not Seeded:
Seed AutoBuild-specific knowledge.

```bash
# Seed role constraints
guardkit graphiti capture --interactive --focus role-customization

# Seed quality gates
guardkit graphiti capture --interactive --focus quality-gates

# Seed workflow preferences
guardkit graphiti capture --interactive --focus workflow-preferences
```

#### If Task Metadata Missing `is_autobuild`:
Update task metadata (should be automatic during /feature-build).

```yaml
# In task frontmatter
---
autobuild:
  is_autobuild: true
  turn_number: 1
  current_actor: player
---
```

#### If Turn States Not Persisted:
Check turn state capture logic.

```bash
# Turn states should be created after each Coach evaluation
ls -la .guardkit/autobuild/TASK-XXX/

# Should see:
# - player_turn_1.json
# - coach_turn_1.json
# - player_turn_2.json
# - coach_turn_2.json
```

### 5. Slow Context Retrieval (>2 seconds)

**Symptoms**:
- Task execution feels sluggish
- Long delays before implementation starts
- Timeout warnings in logs

**Diagnosis**:

```bash
# Check retrieval time
GUARDKIT_LOG_LEVEL=DEBUG /task-work TASK-XXX 2>&1 | grep "retrieval time"

# Check Neo4j performance
docker stats neo4j
```

**Solutions**:

#### If Neo4j Slow:
Increase Neo4j resources.

```yaml
# In docker-compose.yml or deployment config
services:
  neo4j:
    environment:
      - NEO4J_dbms_memory_heap_initial__size=512m
      - NEO4J_dbms_memory_heap_max__size=2g
      - NEO4J_dbms_memory_pagecache_size=1g
```

#### If Network Latency:
Check network between GuardKit and Neo4j.

```bash
# Ping Neo4j
ping <neo4j-host>

# Check connection time
time curl -I http://<neo4j-host>:7474
```

#### If Too Many Context Categories:
Reduce categories retrieved (rare edge case).

```python
# Edit guardkit/knowledge/job_context_retriever.py
# Comment out less critical categories
# (Not recommended - contact maintainers first)
```

### 6. Context Not Appearing in Prompt

**Symptoms**:
- Task executes but context clearly not used
- No "Retrieved job-specific context" log message
- Agent makes mistakes that context would prevent

**Diagnosis**:

```bash
# Check if retrieval happening at all
GUARDKIT_LOG_LEVEL=DEBUG /task-work TASK-XXX 2>&1 | grep "job-specific"

# Check if integration is enabled
grep -r "JobContextRetriever" guardkit/cli/commands/
```

**Solutions**:

#### If Retrieval Not Happening:
Integration may be disabled or broken.

```bash
# Check if Graphiti enabled
guardkit graphiti status

# If disabled, enable in config/graphiti.yaml
enabled: true
```

#### If Retrieval Happening But Not Injected:
Check prompt formatting.

```python
# Verify RetrievedContext.to_prompt() is called
# Should see in task_work.py or feature_build.py:
context_prompt = context.to_prompt()
```

### 7. Duplicate Context

**Symptoms**:
- Same facts appear multiple times
- Token budget wasted on redundancy
- Context sections overlap significantly

**Diagnosis**:

```bash
# Check for duplicate episodes in Graphiti
guardkit graphiti search "your fact" --limit 50
# Look for exact duplicates with same content
```

**Solutions**:

#### If Duplicates in Graphiti:
Deduplication failed during seeding.

```bash
# Clean and re-seed
guardkit graphiti seed --force

# Future: Add upsert logic (FEAT-GR-PRE-003)
```

#### If Deduplication Not Working:
Check deduplication logic.

```python
# Should see in job_context_retriever.py:
def _deduplicate_results(self, results: List[Dict]) -> List[Dict]:
    # Hash-based deduplication
    seen = set()
    deduplicated = []
    for result in results:
        content_hash = hashlib.sha256(str(result).encode()).hexdigest()
        if content_hash not in seen:
            seen.add(content_hash)
            deduplicated.append(result)
    return deduplicated
```

## Debugging Checklist

When troubleshooting context issues, go through this checklist:

- [ ] **Graphiti is running**: `guardkit graphiti status`
- [ ] **Knowledge is seeded**: `guardkit graphiti search "test"` returns results
- [ ] **Task description is specific**: Includes relevant keywords for matching
- [ ] **Relevance thresholds are appropriate**: Not too strict (>0.7) or too loose (<0.4)
- [ ] **AutoBuild metadata is set**: `is_autobuild=true` if using /feature-build
- [ ] **Turn states are persisted**: Check `.guardkit/autobuild/TASK-XXX/` for JSON files
- [ ] **Neo4j is performant**: Check `docker stats neo4j` for resource issues
- [ ] **Integration is enabled**: JobContextRetriever is being called
- [ ] **Deduplication is working**: No obvious duplicates in retrieved context

## Enabling Debug Mode

For detailed troubleshooting, enable debug logging:

```bash
# Environment variable
export GUARDKIT_LOG_LEVEL=DEBUG

# Run command
/task-work TASK-XXX

# Or in one line
GUARDKIT_LOG_LEVEL=DEBUG /task-work TASK-XXX 2>&1 | tee debug.log
```

Debug logs will show:
- Task characteristics analysis
- Budget calculation breakdown
- Category-by-category retrieval
- Relevance scores for each result
- Deduplication statistics
- Final context size and budget usage

## Performance Benchmarks

Expected performance for context retrieval:

| Metric | Target | Acceptable | Action If Exceeded |
|--------|--------|------------|-------------------|
| Retrieval time | <800ms | <2s | Check Neo4j, network |
| Budget utilization | 70-90% | 50-100% | Adjust allocations if consistently low/high |
| Relevance scores | 0.65-0.85 | 0.5-0.9 | Tune thresholds if outside range |
| Cache hit rate | 30-50% | 20-60% | Check if tasks are similar enough for caching |

## Getting Help

If this guide doesn't resolve your issue:

1. **Collect debug logs**: `GUARDKIT_LOG_LEVEL=DEBUG /task-work TASK-XXX 2>&1 > debug.log`
2. **Collect Graphiti status**: `guardkit graphiti status --verbose > graphiti-status.txt`
3. **Collect task file**: `cat tasks/*/TASK-XXX*.md > task-xxx.md`
4. **Report issue** with all three files to GuardKit maintainers

## Related Documentation

- [FEAT-GR-006: Job-Specific Context Retrieval](../research/graphiti-refinement/FEAT-GR-006-job-specific-context.md) - Technical specification
- [Graphiti Integration Guide](graphiti-integration-guide.md) - Setup and configuration
- [Graphiti Commands](graphiti-commands.md) - CLI command reference
- [AutoBuild Documentation](../../installer/core/commands/feature-build.md) - Feature-build workflow

## Changelog

- **2026-02-01**: Initial version (TASK-GR6-014)

---
id: TASK-CSC-004
title: Implement context caching
status: backlog
created: 2026-01-23T11:30:00Z
priority: high
tags: [context-sensitive-coach, caching, performance, quality-gates]
task_type: feature
complexity: 4
parent_review: TASK-REV-CSC1
feature_id: FEAT-CSC
wave: 2
implementation_mode: task-work
conductor_workspace: csc-wave2-cache
dependencies:
  - TASK-CSC-001
---

# Task: Implement Context Caching

## Description

Implement caching for context analysis results to avoid redundant AI calls between turns. The cache should invalidate when files change.

## Acceptance Criteria

- [ ] `ContextCache` class with get/set/invalidate methods
- [ ] Cache key computation based on file content hashes
- [ ] Cache invalidation for changed files
- [ ] Persistence between turns (file-based)
- [ ] TTL/expiration handling
- [ ] Unit tests with >80% coverage

## Implementation Notes

### Location

Create in: `guardkit/orchestrator/quality_gates/context_analysis/cache.py`

### Cache Storage

Store in: `.guardkit/autobuild/{task_id}/context_cache.json`

```json
{
  "cache_version": "1.0",
  "task_id": "TASK-001",
  "entries": {
    "abc123def456": {
      "context_hash": "abc123def456",
      "analysis": {
        "testability_score": 25,
        "patterns": ["declarative_config"],
        "is_declarative": true,
        "arch_review_recommended": false,
        "rationale": "Simple Pydantic model"
      },
      "created_at": "2026-01-23T11:30:00Z",
      "turn": 1
    }
  }
}
```

### Cache Key Computation

```python
def _compute_cache_key(self, context: UniversalContext) -> str:
    """Compute cache key from file content hashes."""
    # Hash all changed file contents
    hasher = hashlib.sha256()
    for file_path in sorted(context.changed_files):
        content = Path(file_path).read_bytes()
        hasher.update(content)
    return hasher.hexdigest()[:12]
```

### ContextCache Interface

```python
@dataclass
class CachedAnalysis:
    context_hash: str
    analysis: AIAnalysisResult
    created_at: datetime
    turn: int

class ContextCache:
    def __init__(self, cache_dir: Path, task_id: str):
        self.cache_file = cache_dir / task_id / "context_cache.json"

    def get(self, cache_key: str) -> Optional[AIAnalysisResult]:
        """Get cached analysis if valid."""
        ...

    def set(self, cache_key: str, analysis: AIAnalysisResult, turn: int) -> None:
        """Cache analysis result."""
        ...

    def invalidate(self, cache_key: str) -> None:
        """Invalidate specific cache entry."""
        ...

    def invalidate_all(self) -> None:
        """Clear entire cache for task."""
        ...

    def is_valid(self, cache_key: str) -> bool:
        """Check if cache entry is valid (not expired, same key)."""
        ...
```

### Cache Invalidation Strategy

```python
def invalidate_changed_files(
    self,
    previous_context: UniversalContext,
    current_context: UniversalContext,
) -> None:
    """Invalidate cache if files changed between turns."""
    prev_hash = self._compute_cache_key(previous_context)
    curr_hash = self._compute_cache_key(current_context)

    if prev_hash != curr_hash:
        # Files changed - invalidate
        self.invalidate(prev_hash)
```

### TTL Handling

Cache entries expire after 1 hour (paranoid safety):

```python
def _is_expired(self, entry: CachedAnalysis) -> bool:
    """Check if cache entry has expired."""
    max_age = timedelta(hours=1)
    return datetime.now() - entry.created_at > max_age
```

## Testing Strategy

- Test cache key computation with various file sets
- Test cache hit/miss scenarios
- Test invalidation on file changes
- Test TTL expiration
- Test persistence (save/load)

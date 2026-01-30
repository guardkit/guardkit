# Implementation Plan: TASK-SD-CA08

**Task**: Add Stub Detection to Phase 4.5 Quality Gate
**Generated**: 2026-01-30T12:00:00Z
**Complexity**: 5/10 (Medium)
**Architectural Review**: 82/100 (Approved with Recommendations)

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `installer/core/lib/stub_detector.py` | Create | Stub detection logic |
| `installer/core/lib/stub_detector_test.py` | Create | Unit tests |
| `installer/core/commands/task-work.md` | Modify | Add Phase 4.5C |
| `docs/guides/stub-detection.md` | Create | Documentation |

## Architecture Decisions

### Applied Recommendations from Review

1. **DRY**: Extract `_check_patterns()` helper function
2. **YAGNI**: Start with Python only, add languages incrementally
3. **YAGNI**: Simplify `verify_library_usage()` to imports only (remove required_calls)

### Final Design

```python
@dataclass
class StubFinding:
    file_path: str
    line_number: int
    pattern_type: str
    matched_text: str
    severity: str

LANGUAGE_PATTERNS = {
    "python": {
        "extensions": [".py"],
        "comment_patterns": [...],
        "stub_patterns": [...]
    }
    # Add TypeScript, Go, Rust, C# incrementally when needed
}

def detect_language(file_path: Path) -> Optional[str]: ...
def _check_patterns(line: str, patterns: List[str], flags: int) -> Optional[str]: ...
def detect_stubs(file_path: Path, content: str) -> List[StubFinding]: ...
def verify_library_usage(file_path: Path, content: str, required_imports: List[str]) -> List[StubFinding]: ...
```

## Estimated Effort

| Phase | Duration |
|-------|----------|
| Core implementation | 45 min |
| Unit tests | 45 min |
| Documentation | 30 min |
| task-work.md update | 15 min |
| **Total** | **~2.25 hours** |

## Success Criteria

1. All acceptance criteria met
2. Unit tests pass with ≥80% coverage
3. Phase 4.5C integrated into task-work workflow
4. Configuration (warn/block) functional

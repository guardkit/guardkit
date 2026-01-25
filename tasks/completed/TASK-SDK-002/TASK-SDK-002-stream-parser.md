---
id: TASK-SDK-002
title: Implement stream parser for quality gate extraction
status: completed
task_type: implementation
created: 2026-01-10T11:00:00Z
updated: 2026-01-10T11:45:00Z
completed: 2026-01-10T12:30:00Z
priority: critical
tags: [sdk-delegation, stream-parser, quality-gates, feature-build]
complexity: 6
wave: 1
parent_feature: sdk-delegation-fix
depends_on: []
completed_location: tasks/completed/TASK-SDK-002/
organized_files: [
  "TASK-SDK-002-stream-parser.md"
]
---

# Implement stream parser for quality gate extraction

## Description

Implement a stream parser that extracts quality gate results from the task-work SDK message stream. This data will be used to create `task_work_results.json` for Coach validation.

## Target Implementation

```python
def _parse_task_work_stream(self, text: str, result_data: dict) -> dict:
    """
    Parse task-work output stream to extract quality gate information.

    Patterns to detect:
    - Phase markers: "Phase N: ..." or "✓ Phase N complete"
    - Test results: "X tests passed", "X tests failed"
    - Coverage: "Coverage: XX%"
    - Quality gates: "Quality gates: PASSED/FAILED"
    - Files: "Modified: file.py", "Created: file.py"
    """
    import re

    # Phase detection
    phase_match = re.search(r'Phase (\d+(?:\.\d+)?)[:\s]+(.*)', text)
    if phase_match:
        phase_num = phase_match.group(1)
        result_data.setdefault("phases", {})[f"phase_{phase_num}"] = {
            "detected": True,
            "text": phase_match.group(2)[:100]
        }

    # Test results
    tests_match = re.search(r'(\d+) tests? passed', text, re.IGNORECASE)
    if tests_match:
        result_data["tests_passed"] = int(tests_match.group(1))

    failed_match = re.search(r'(\d+) tests? failed', text, re.IGNORECASE)
    if failed_match:
        result_data["tests_failed"] = int(failed_match.group(1))

    # Coverage
    coverage_match = re.search(r'[Cc]overage[:\s]+(\d+(?:\.\d+)?)%', text)
    if coverage_match:
        result_data["coverage"] = float(coverage_match.group(1))

    # Quality gates
    if 'quality gates: passed' in text.lower() or 'all quality gates passed' in text.lower():
        result_data["quality_gates_passed"] = True
    elif 'quality gates: failed' in text.lower():
        result_data["quality_gates_passed"] = False

    # File modifications
    for pattern in [r'(?:Modified|Changed):\s*([^\s,]+)', r'(?:Created|Added):\s*([^\s,]+)']:
        matches = re.findall(pattern, text)
        if matches:
            key = "files_modified" if "Modified" in pattern else "files_created"
            result_data.setdefault(key, []).extend(matches)

    return result_data
```

## Acceptance Criteria

- [x] Parser extracts phase completion markers
- [x] Parser extracts test pass/fail counts
- [x] Parser extracts coverage percentage
- [x] Parser extracts quality gate status
- [x] Parser extracts file modification list
- [x] Handles partial/incremental parsing (stream)
- [x] Graceful handling of unrecognized output
- [x] Unit tests for each parsing pattern
- [x] Integration with SDK stream processing

## Implementation Notes

- Parser must be incremental (called for each stream message)
- Use regex patterns for flexibility
- Accumulate results in dict passed between calls
- Don't fail on unrecognized patterns (graceful degradation)
- Consider logging unrecognized patterns for debugging

## Test Cases

```python
def test_parse_test_results():
    parser = StreamParser()
    result = parser.parse("12 tests passed, 0 tests failed", {})
    assert result["tests_passed"] == 12
    assert result["tests_failed"] == 0

def test_parse_coverage():
    parser = StreamParser()
    result = parser.parse("Coverage: 85.5%", {})
    assert result["coverage"] == 85.5

def test_parse_quality_gates():
    parser = StreamParser()
    result = parser.parse("Quality gates: PASSED", {})
    assert result["quality_gates_passed"] == True
```

## Files to Modify

- `guardkit/orchestrator/agent_invoker.py` - Add `_parse_task_work_stream` method
- `tests/unit/test_agent_invoker.py` - Add parser tests

## Related

- TASK-SDK-001: SDK query (parallel, same wave)
- TASK-SDK-003: Results writer (depends on this)

## Completion Summary

**Completed**: 2026-01-10T12:30:00Z

**Implementation**:
- `TaskWorkStreamParser` class implemented in `guardkit/orchestrator/agent_invoker.py`
- `_parse_task_work_stream` method integrated into `AgentInvoker`
- Comprehensive test coverage with 35+ test cases covering all parsing patterns

**Test Results**:
- 62 parser-related tests passing
- Coverage for phase markers, test results, coverage %, quality gates, and file modifications
- Incremental parsing, deduplication, and edge cases all tested

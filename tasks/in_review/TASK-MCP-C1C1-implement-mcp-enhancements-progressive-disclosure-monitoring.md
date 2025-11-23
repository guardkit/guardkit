---
id: TASK-MCP-C1C1
title: Implement MCP Enhancements - Progressive Disclosure and Response Monitoring
status: in_review
created: 2025-01-22T12:10:00Z
updated: 2025-01-23T09:15:00Z
priority: high
tags: [mcp, optimization, context7, monitoring, performance]
complexity: 7
related_to: TASK-MCP-7796
test_results:
  status: passed
  coverage:
    line: 83.7
    branch: 80.0
  total_tests: 55
  passed: 55
  failed: 0
  last_run: 2025-01-23T09:10:00Z
previous_state: in_progress
state_transition_reason: "All quality gates passed - ready for human review"
implementation_summary:
  files_created: 5
  loc_production: 1037
  loc_test: 828
  tests_count: 55
  code_quality_score: 8.5
  architectural_review_score: 82
  complexity_evaluation_score: 3
---

# TASK-MCP-C1C1: Implement MCP Enhancements - Progressive Disclosure and Response Monitoring

**Task ID**: TASK-MCP-C1C1
**Priority**: HIGH
**Status**: IN_PROGRESS
**Created**: 2025-01-22T12:10:00Z
**Complexity**: 7/10 (Complex - two enhancements, requires careful integration)
**Related**: TASK-MCP-7796 (Review findings that identified these recommendations)

---

## Overview

Implement two HIGH priority MCP optimization enhancements identified in TASK-MCP-7796 review:

1. **Progressive Disclosure for Context7**: Add `detail_level` parameter to reduce token usage by 50-70% in planning phase
2. **MCP Response Size Monitoring**: Add real-time token usage tracking with budget variance detection

**Expected Impact**:
- **Token Savings**: 2,000-3,500 tokens per task (50-70% reduction in Phase 2)
- **Visibility**: Real-time monitoring prevents budget overruns
- **Optimization**: Data-driven budget tuning based on actual usage
- **Risk**: Low (backward compatible, additive changes)

**Estimated Effort**: 40 hours (~5 days) or 2-3 weeks with testing/validation

---

## Background

### Context from TASK-MCP-7796 Review

The review of Anthropic's MCP Code Execution article identified that Taskwright's current MCP usage aligns well with Anthropic's optimization patterns (7/8 patterns aligned, 84% overall). However, two opportunities for improvement were identified:

**Current State**:
- ✅ Context7 uses topic-based scoping (90% token reduction vs. full docs)
- ✅ Token budgets implemented (2000-6000 based on phase)
- ✅ Performance excellent (2-6% context window usage)
- ⚠️ Single-tier loading (planning phase fetches 3500 tokens, could be 500)
- ⚠️ No runtime monitoring (optimization relies on manual audits)

**Target State**:
- ✅ Progressive disclosure: Planning fetches summary (500 tokens), implementation fetches detailed (5000 tokens)
- ✅ Real-time monitoring: Track actual vs. expected token usage, warn on overages
- ✅ Data-driven optimization: Historical data enables budget tuning

**Alignment with Anthropic Patterns**:
- **Progressive disclosure**: Anthropic's #1 recommendation (98.7% token reduction achieved via this pattern)
- **Monitoring**: Essential for production MCP usage (detect issues proactively)

---

## Enhancement #1: Progressive Disclosure for Context7

### Problem Statement

Context7 currently uses single-tier loading:
- **Phase 2 (Planning)**: Fetches full topic docs (3500-4000 tokens)
- **Phase 3 (Implementation)**: Fetches full topic docs again (5000 tokens)

**Issue**: Planning phase doesn't need detailed examples, just high-level overview.

**Opportunity**: Fetch 500-1000 token summary in planning, save 2500-3000 tokens.

### Proposed Solution

Add `detail_level` parameter to Context7 MCP with two modes:

#### DetailLevel Enum

```python
from enum import Enum

class DetailLevel(Enum):
    SUMMARY = "summary"      # 500-1000 tokens: High-level overview
    DETAILED = "detailed"    # 3500-5000 tokens: Full examples and docs
```

#### Updated Context7Client API

```python
class Context7Client:
    def get_library_docs(
        self,
        library_id: str,
        topic: str,
        detail_level: DetailLevel = DetailLevel.DETAILED,  # Backward compatible
        tokens: Optional[int] = None  # Auto-set based on detail_level if None
    ) -> str:
        """
        Fetch library documentation with optional detail level control.

        Args:
            library_id: Library ID (e.g., "/tiangolo/fastapi")
            topic: Topic to focus on (e.g., "dependency-injection")
            detail_level: SUMMARY (500-1000 tokens) or DETAILED (3500-5000 tokens)
            tokens: Manual token override (auto-set if None)

        Returns:
            Documentation content as string

        Examples:
            # Phase 2: Planning - get summary
            summary = client.get_library_docs(
                library_id="/tiangolo/fastapi",
                topic="dependency-injection",
                detail_level=DetailLevel.SUMMARY
            )  # Returns ~750 tokens

            # Phase 3: Implementation - get detailed content
            detailed = client.get_library_docs(
                library_id="/tiangolo/fastapi",
                topic="dependency-injection",
                detail_level=DetailLevel.DETAILED
            )  # Returns ~4500 tokens
        """
        pass

    def get_summary(self, library_id: str, topic: str) -> str:
        """Convenience method: Fetch summary-level docs (500-1000 tokens)"""
        return self.get_library_docs(library_id, topic, DetailLevel.SUMMARY)

    def get_detailed(self, library_id: str, topic: str) -> str:
        """Convenience method: Fetch detailed docs (3500-5000 tokens)"""
        return self.get_library_docs(library_id, topic, DetailLevel.DETAILED)
```

#### Integration with task-manager

**Phase 2 (Planning)**:
```python
# OLD: Fetch detailed docs (3500 tokens)
docs = context7.get_library_docs(library_id, topic=topic, tokens=3500)

# NEW: Fetch summary only (750 tokens)
docs = context7.get_summary(library_id, topic=topic)
# Savings: 2750 tokens (78% reduction)
```

**Phase 3 (Implementation)**:
```python
# Unchanged: Fetch detailed docs (5000 tokens)
docs = context7.get_detailed(library_id, topic=topic)
```

#### Token Budget Mapping

| Detail Level | Token Range | Use Case | Phase |
|--------------|-------------|----------|-------|
| **SUMMARY** | 500-1000 | High-level architecture overview | Phase 2 (Planning) |
| **DETAILED** | 3500-5000 (default) | Full API docs and code examples | Phase 3 (Implementation) |

#### Backward Compatibility

**100% backward compatible**:
- Default behavior: `detail_level=DetailLevel.DETAILED` (unchanged)
- Existing calls work without modification
- Token parameter still respected if provided

**Migration**:
- Update task-manager Phase 2 to use `get_summary()`
- Phase 3 remains unchanged (already uses detailed)
- Gradual rollout (verify token savings before full deployment)

### Acceptance Criteria (AC1)

#### AC1.1: API Implementation
- [ ] **AC1.1.1**: `DetailLevel` enum created with SUMMARY and DETAILED values
- [ ] **AC1.1.2**: `Context7Client.get_library_docs()` accepts `detail_level` parameter
- [ ] **AC1.1.3**: Default `detail_level` is DETAILED (backward compatible)
- [ ] **AC1.1.4**: Token auto-selection based on detail_level (500-1000 for SUMMARY, 3500-5000 for DETAILED)
- [ ] **AC1.1.5**: Manual `tokens` parameter overrides auto-selection

#### AC1.2: Convenience Methods
- [ ] **AC1.2.1**: `get_summary()` method created (calls with SUMMARY)
- [ ] **AC1.2.2**: `get_detailed()` method created (calls with DETAILED)
- [ ] **AC1.2.3**: Both methods delegate to `get_library_docs()`

#### AC1.3: Integration with task-manager
- [ ] **AC1.3.1**: Phase 2 (Planning) updated to use `get_summary()`
- [ ] **AC1.3.2**: Phase 3 (Implementation) uses `get_detailed()` (or unchanged if already detailed)
- [ ] **AC1.3.3**: Phase 4 (Testing) uses appropriate detail level (summary or detailed based on need)

#### AC1.4: Token Savings Validation
- [ ] **AC1.4.1**: SUMMARY mode returns 500-1000 tokens (not 3500+)
- [ ] **AC1.4.2**: DETAILED mode returns 3500-5000 tokens (unchanged)
- [ ] **AC1.4.3**: Phase 2 token usage reduced by 50-70% (measured in real task)

#### AC1.5: Error Handling
- [ ] **AC1.5.1**: Invalid `detail_level` raises clear error
- [ ] **AC1.5.2**: MCP unavailable falls back to training data (graceful degradation)
- [ ] **AC1.5.3**: Token count mismatch logged but doesn't fail request

#### AC1.6: Documentation
- [ ] **AC1.6.1**: API docstrings include examples for both detail levels
- [ ] **AC1.6.2**: MCP optimization guide updated (lines 95-134)
- [ ] **AC1.6.3**: task-manager.md updated with new usage pattern (lines 23-73)

---

## Enhancement #2: MCP Response Size Monitoring

### Problem Statement

Current system lacks runtime monitoring of actual vs. expected token usage:
- **Manual audits only**: Optimization relies on periodic reviews (like TASK-012)
- **No real-time detection**: Over-budget queries discovered after the fact
- **No historical data**: Cannot tune budgets based on actual usage

**Issue**: Reactive optimization (fix issues after they occur) vs. proactive (prevent issues).

### Proposed Solution

Add `MCPMonitor` class for real-time token usage tracking with budget variance detection.

#### MCPMonitor Class

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
import json

@dataclass
class MCPRequest:
    """Represents an MCP request"""
    mcp_name: str
    method: str
    query: dict
    expected_tokens: int
    phase: str
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class MCPResponse:
    """Represents an MCP response with token metrics"""
    request: MCPRequest
    actual_tokens: int
    duration_seconds: float
    success: bool
    error_message: Optional[str] = None
    variance: float = field(init=False)

    def __post_init__(self):
        """Calculate variance after initialization"""
        self.variance = (self.actual_tokens - self.request.expected_tokens) / self.request.expected_tokens

class MCPMonitor:
    """
    Monitor MCP requests and responses for token usage tracking.

    Features:
    - Real-time variance detection (warns at >20% over budget)
    - Phase-specific tracking
    - Historical data for budget tuning
    - JSON report generation

    Example:
        monitor = MCPMonitor()

        # Record request
        request = monitor.record_request(
            mcp_name="context7",
            method="get_library_docs",
            query={"library_id": "/fastapi", "topic": "DI"},
            expected_tokens=1000,
            phase="phase_2"
        )

        # Record response
        monitor.record_response(
            request=request,
            actual_tokens=850,
            duration_seconds=1.2,
            success=True
        )  # Logs: ✓ Variance: -15.0% from budget

        # Generate report
        report = monitor.generate_report()
        monitor.save_report("docs/state/TASK-001/mcp_usage_report.json")
    """

    def __init__(self):
        self.requests: List[MCPRequest] = []
        self.responses: List[MCPResponse] = []
        self.variance_threshold: float = 0.20  # Warn at >20% over budget

    def record_request(
        self,
        mcp_name: str,
        method: str,
        query: dict,
        expected_tokens: int,
        phase: str
    ) -> MCPRequest:
        """Record MCP request before execution"""
        request = MCPRequest(
            mcp_name=mcp_name,
            method=method,
            query=query,
            expected_tokens=expected_tokens,
            phase=phase
        )
        self.requests.append(request)

        # Real-time console output
        print(f"📡 MCP Request: {mcp_name}/{method} (Phase {phase})")
        print(f"   Budget: {expected_tokens} tokens")

        return request

    def record_response(
        self,
        request: MCPRequest,
        actual_tokens: int,
        duration_seconds: float,
        success: bool,
        error_message: Optional[str] = None
    ) -> MCPResponse:
        """Record MCP response after execution"""
        response = MCPResponse(
            request=request,
            actual_tokens=actual_tokens,
            duration_seconds=duration_seconds,
            success=success,
            error_message=error_message
        )
        self.responses.append(response)

        # Real-time console output
        status_emoji = "✅" if success else "❌"
        print(f"{status_emoji} MCP Response: {request.mcp_name}/{request.method}")
        print(f"   Actual: {actual_tokens} tokens")

        # Variance detection
        variance_pct = response.variance * 100
        if abs(response.variance) > self.variance_threshold:
            variance_emoji = "⚠️" if response.variance > 0 else "ℹ️"
            print(f"   {variance_emoji} Variance: {variance_pct:+.1f}% from budget")

            if response.variance > self.variance_threshold:
                print(f"   WARNING: Exceeded budget by {variance_pct:.1f}%")
        else:
            print(f"   ✓ Variance: {variance_pct:+.1f}% from budget")

        return response

    def generate_report(self) -> dict:
        """Generate comprehensive usage report"""
        if not self.responses:
            return {"message": "No MCP requests tracked"}

        total_calls = len(self.responses)
        successful_calls = sum(1 for r in self.responses if r.success)
        failed_calls = total_calls - successful_calls

        total_expected = sum(r.request.expected_tokens for r in self.responses)
        total_actual = sum(r.actual_tokens for r in self.responses)
        total_variance = (total_actual - total_expected) / total_expected if total_expected > 0 else 0

        over_budget_calls = sum(1 for r in self.responses if r.variance > self.variance_threshold)

        # Phase breakdown
        phases = {}
        for response in self.responses:
            phase = response.request.phase
            if phase not in phases:
                phases[phase] = {
                    "calls": 0,
                    "expected_tokens": 0,
                    "actual_tokens": 0,
                    "over_budget": 0
                }

            phases[phase]["calls"] += 1
            phases[phase]["expected_tokens"] += response.request.expected_tokens
            phases[phase]["actual_tokens"] += response.actual_tokens
            if response.variance > self.variance_threshold:
                phases[phase]["over_budget"] += 1

        return {
            "summary": {
                "total_calls": total_calls,
                "successful_calls": successful_calls,
                "failed_calls": failed_calls,
                "total_expected_tokens": total_expected,
                "total_actual_tokens": total_actual,
                "total_variance_pct": total_variance * 100,
                "over_budget_calls": over_budget_calls,
                "over_budget_pct": (over_budget_calls / total_calls * 100) if total_calls > 0 else 0
            },
            "phases": phases,
            "requests": [
                {
                    "mcp": r.request.mcp_name,
                    "method": r.request.method,
                    "phase": r.request.phase,
                    "expected_tokens": r.request.expected_tokens,
                    "actual_tokens": r.actual_tokens,
                    "variance_pct": r.variance * 100,
                    "duration_seconds": r.duration_seconds,
                    "success": r.success
                }
                for r in self.responses
            ]
        }

    def save_report(self, filepath: str):
        """Save report to JSON file"""
        report = self.generate_report()
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"📊 MCP Usage Report saved: {filepath}")
```

#### Integration with task-work

```python
# In task-manager or orchestrator

# Initialize monitor at task start
monitor = MCPMonitor()

# Phase 2: Planning
request = monitor.record_request(
    mcp_name="context7",
    method="get_library_docs",
    query={"library_id": "/fastapi", "topic": "DI"},
    expected_tokens=1000,  # Summary mode
    phase="phase_2"
)

# Execute Context7 call (with timing)
start_time = time.time()
docs = context7.get_summary("/tiangolo/fastapi", "dependency-injection")
duration = time.time() - start_time

# Record response
actual_tokens = count_tokens(docs)  # Utility function
monitor.record_response(
    request=request,
    actual_tokens=actual_tokens,
    duration_seconds=duration,
    success=True
)

# At task completion
report = monitor.generate_report()
monitor.save_report(f"docs/state/{task_id}/mcp_usage_report.json")
```

#### Report Output Example

```json
{
  "summary": {
    "total_calls": 3,
    "successful_calls": 3,
    "failed_calls": 0,
    "total_expected_tokens": 7500,
    "total_actual_tokens": 6850,
    "total_variance_pct": -8.67,
    "over_budget_calls": 0,
    "over_budget_pct": 0.0
  },
  "phases": {
    "phase_2": {
      "calls": 1,
      "expected_tokens": 1000,
      "actual_tokens": 850,
      "over_budget": 0
    },
    "phase_3": {
      "calls": 2,
      "expected_tokens": 6500,
      "actual_tokens": 6000,
      "over_budget": 0
    }
  },
  "requests": [
    {
      "mcp": "context7",
      "method": "get_library_docs",
      "phase": "phase_2",
      "expected_tokens": 1000,
      "actual_tokens": 850,
      "variance_pct": -15.0,
      "duration_seconds": 1.2,
      "success": true
    }
  ]
}
```

### Acceptance Criteria (AC2)

#### AC2.1: MCPMonitor Implementation
- [ ] **AC2.1.1**: `MCPRequest` dataclass created with all required fields
- [ ] **AC2.1.2**: `MCPResponse` dataclass created with variance auto-calculation
- [ ] **AC2.1.3**: `MCPMonitor` class created with request/response tracking
- [ ] **AC2.1.4**: `record_request()` method logs real-time console output
- [ ] **AC2.1.5**: `record_response()` method calculates and logs variance

#### AC2.2: Variance Detection
- [ ] **AC2.2.1**: Variance threshold configurable (default: 20%)
- [ ] **AC2.2.2**: Warning logged when actual > expected by >20%
- [ ] **AC2.2.3**: Informational message when actual < expected (under-budget)
- [ ] **AC2.2.4**: No warning when variance ≤20%

#### AC2.3: Report Generation
- [ ] **AC2.3.1**: `generate_report()` returns summary statistics
- [ ] **AC2.3.2**: Report includes phase breakdown (calls, tokens, over-budget count)
- [ ] **AC2.3.3**: Report includes per-request details (mcp, phase, tokens, variance)
- [ ] **AC2.3.4**: `save_report()` writes JSON to specified path

#### AC2.4: Integration with task-work
- [ ] **AC2.4.1**: MCPMonitor initialized at task start
- [ ] **AC2.4.2**: Context7 calls wrapped with monitoring (request + response)
- [ ] **AC2.4.3**: design-patterns calls wrapped with monitoring
- [ ] **AC2.4.4**: Report saved to `docs/state/{task_id}/mcp_usage_report.json` at task completion

#### AC2.5: Real-Time Console Output
- [ ] **AC2.5.1**: Request logged with emoji, MCP name, method, phase, budget
- [ ] **AC2.5.2**: Response logged with emoji (✅/❌), actual tokens
- [ ] **AC2.5.3**: Variance logged with emoji (⚠️/>20%, ✓/≤20%, ℹ️/under-budget)
- [ ] **AC2.5.4**: Warning message for over-budget calls

#### AC2.6: Error Handling
- [ ] **AC2.6.1**: Failed MCP calls tracked (success=False, error_message)
- [ ] **AC2.6.2**: Division by zero handled (variance calculation when expected=0)
- [ ] **AC2.6.3**: File I/O errors handled gracefully (save_report)

#### AC2.7: Documentation
- [ ] **AC2.7.1**: MCPMonitor class docstring with usage examples
- [ ] **AC2.7.2**: MCP optimization guide updated with monitoring section
- [ ] **AC2.7.3**: Report format documented with example output

---

## Implementation Plan

### Phase 1: Foundation (Week 1, 16 hours)

**Deliverables**: Core classes and unit tests

#### Step 1.1: Create DetailLevel Enum (2 hours)
- [ ] Create `installer/global/lib/mcp/detail_level.py`
- [ ] Implement `DetailLevel` enum (SUMMARY, DETAILED)
- [ ] Write unit tests (test valid values, string conversion)

#### Step 1.2: Update Context7Client (6 hours)
- [ ] Add `detail_level` parameter to `get_library_docs()`
- [ ] Implement auto token selection based on detail level
- [ ] Add `get_summary()` convenience method
- [ ] Add `get_detailed()` convenience method
- [ ] Write unit tests (12+ tests covering all scenarios)

#### Step 1.3: Implement MCPMonitor Class (8 hours)
- [ ] Create `installer/global/lib/mcp/monitor.py`
- [ ] Implement `MCPRequest` dataclass
- [ ] Implement `MCPResponse` dataclass with variance calculation
- [ ] Implement `MCPMonitor` class (record_request, record_response, generate_report, save_report)
- [ ] Write unit tests (15+ tests covering all methods)

### Phase 2: Integration (Week 2, 12 hours)

**Deliverables**: Updated task-manager and workflow integration

#### Step 2.1: Integrate Context7 Progressive Disclosure (4 hours)
- [ ] Update task-manager Phase 2 to use `get_summary()`
- [ ] Verify Phase 3 uses `get_detailed()` (or update if needed)
- [ ] Update Phase 4 (Testing) with appropriate detail level
- [ ] Write integration tests (real Context7 MCP calls)

#### Step 2.2: Integrate MCPMonitor (6 hours)
- [ ] Add monitor initialization to task orchestrator
- [ ] Wrap Context7 calls with monitoring (request + response)
- [ ] Wrap design-patterns calls with monitoring
- [ ] Add report generation at task completion
- [ ] Write integration tests (verify report contents)

#### Step 2.3: Token Counting Utility (2 hours)
- [ ] Create `count_tokens()` utility function (1 token ≈ 4 characters)
- [ ] Integrate with MCPMonitor for actual token measurement
- [ ] Write unit tests (verify accuracy ±5%)

### Phase 3: Validation (Week 3, 8 hours)

**Deliverables**: Real-world testing and validation

#### Step 3.1: Real Task Testing (4 hours)
- [ ] Run `/task-work` on sample task with Context7 usage
- [ ] Verify Phase 2 uses summary mode (500-1000 tokens)
- [ ] Verify Phase 3 uses detailed mode (3500-5000 tokens)
- [ ] Measure actual token savings (50-70% target)
- [ ] Verify MCP usage report generated and saved

#### Step 3.2: Acceptance Criteria Validation (2 hours)
- [ ] Validate all AC1 criteria (Progressive Disclosure)
- [ ] Validate all AC2 criteria (Monitoring)
- [ ] Document any deviations or issues

#### Step 3.3: Performance Testing (2 hours)
- [ ] Measure monitoring overhead (<2% target)
- [ ] Verify no performance degradation in task execution
- [ ] Load test (simulate 100+ MCP calls)

### Phase 4: Documentation & Rollout (Week 4, 4 hours)

**Deliverables**: Documentation updates and production deployment

#### Step 4.1: Documentation Updates (2 hours)
- [ ] Update `docs/deep-dives/mcp-integration/mcp-optimization.md` (lines 95-134 for progressive disclosure)
- [ ] Update `installer/global/agents/task-manager.md` (lines 23-73 for Context7 usage)
- [ ] Add monitoring section to MCP optimization guide
- [ ] Create usage examples document

#### Step 4.2: Production Rollout (2 hours)
- [ ] Merge to main branch
- [ ] Update CLAUDE.md with new features (if needed)
- [ ] Create announcement/changelog entry
- [ ] Monitor initial production usage

---

## Testing Strategy

### Unit Tests (Target: 100% coverage)

#### Context7 Tests (12 tests)
```python
def test_detail_level_enum_values():
    assert DetailLevel.SUMMARY.value == "summary"
    assert DetailLevel.DETAILED.value == "detailed"

def test_get_library_docs_default_detailed():
    client = Context7Client()
    # Should default to DETAILED mode
    pass

def test_get_library_docs_summary_mode():
    client = Context7Client()
    # Should use 500-1000 token budget
    pass

def test_get_summary_convenience_method():
    client = Context7Client()
    # Should call get_library_docs with SUMMARY
    pass

def test_get_detailed_convenience_method():
    client = Context7Client()
    # Should call get_library_docs with DETAILED
    pass

def test_token_auto_selection_summary():
    # Should set tokens=750 (midpoint of 500-1000)
    pass

def test_token_auto_selection_detailed():
    # Should set tokens=4250 (midpoint of 3500-5000)
    pass

def test_manual_token_override():
    # Manual tokens parameter should override auto-selection
    pass

# ... 4 more tests for error handling, edge cases
```

#### MCPMonitor Tests (15 tests)
```python
def test_record_request_creates_request():
    monitor = MCPMonitor()
    request = monitor.record_request(...)
    assert len(monitor.requests) == 1

def test_record_response_calculates_variance():
    monitor = MCPMonitor()
    request = monitor.record_request(expected_tokens=1000, ...)
    response = monitor.record_response(request, actual_tokens=1200, ...)
    assert response.variance == 0.20  # 20% over

def test_variance_warning_threshold():
    # Should warn when variance > 20%
    pass

def test_generate_report_summary():
    # Should include total_calls, expected_tokens, actual_tokens
    pass

def test_generate_report_phase_breakdown():
    # Should group by phase
    pass

def test_save_report_creates_file():
    # Should write JSON to specified path
    pass

# ... 9 more tests for error handling, edge cases
```

### Integration Tests (Real MCP calls)

#### Context7 Integration Test
```python
def test_context7_progressive_disclosure_in_task():
    """Test that Phase 2 uses summary, Phase 3 uses detailed"""
    # Simulate task execution
    # Phase 2: get_summary() should return ~750 tokens
    # Phase 3: get_detailed() should return ~4500 tokens
    # Verify total savings vs. old approach
    pass
```

#### MCPMonitor Integration Test
```python
def test_monitor_tracks_real_context7_calls():
    """Test that MCPMonitor correctly tracks Context7 calls"""
    # Execute Context7 call with monitoring
    # Verify request recorded
    # Verify response recorded with correct variance
    # Verify report includes this call
    pass
```

### Validation Tests (Acceptance criteria)

```python
def test_ac1_4_3_token_savings():
    """AC1.4.3: Phase 2 token usage reduced by 50-70%"""
    # Run real task with new vs. old approach
    # Measure actual token savings
    # Assert savings ≥ 50%
    pass

def test_ac2_2_2_variance_warning():
    """AC2.2.2: Warning logged when actual > expected by >20%"""
    # Simulate over-budget response
    # Verify warning logged
    pass
```

---

## Files Modified

### New Files
1. `installer/global/lib/mcp/detail_level.py` - DetailLevel enum
2. `installer/global/lib/mcp/monitor.py` - MCPMonitor, MCPRequest, MCPResponse classes
3. `installer/global/lib/mcp/__init__.py` - Package exports
4. `tests/unit/lib/mcp/test_detail_level.py` - DetailLevel tests
5. `tests/unit/lib/mcp/test_monitor.py` - MCPMonitor tests
6. `tests/integration/mcp/test_context7_progressive_disclosure.py` - Integration tests
7. `tests/integration/mcp/test_monitor_integration.py` - Monitor integration tests

### Modified Files
1. `installer/global/lib/mcp/context7_client.py` - Add detail_level parameter, convenience methods
2. `installer/global/agents/task-manager.md` - Update Context7 usage (lines 23-73)
3. `docs/deep-dives/mcp-integration/mcp-optimization.md` - Add progressive disclosure section (after line 134)
4. `CLAUDE.md` - Document new features (lines 669-679)

---

## Success Metrics

### Quantitative Metrics

#### Enhancement #1: Progressive Disclosure
- [ ] **Token Savings**: Phase 2 uses 500-1000 tokens (vs. 3500 current) = 50-70% reduction
- [ ] **Net Savings**: 2500-3000 tokens per task (measured across 10 sample tasks)
- [ ] **Context Impact**: Phase 2 reduced from 3.5% to 0.5-1% context window usage
- [ ] **Backward Compatibility**: 100% of existing code works without changes

#### Enhancement #2: Monitoring
- [ ] **Coverage**: 100% of MCP calls tracked (Context7, design-patterns)
- [ ] **Accuracy**: Token counts within ±5% of actual
- [ ] **Performance**: Monitoring overhead <2% (measured via task duration)
- [ ] **Reports Generated**: 100% of tasks have MCP usage report saved

### Qualitative Metrics

#### Enhancement #1: Progressive Disclosure
- [ ] **Developer Experience**: API is intuitive (get_summary, get_detailed)
- [ ] **Documentation**: Clear usage examples in docs
- [ ] **Migration**: Existing code works without changes (zero-breaking-change)

#### Enhancement #2: Monitoring
- [ ] **Visibility**: Real-time console output shows token usage
- [ ] **Actionability**: Over-budget warnings enable immediate investigation
- [ ] **Historical Data**: Reports enable data-driven budget tuning

---

## Risk Assessment

### Risk 1: Token Savings Less Than Expected

**Likelihood**: Low (Anthropic achieved 98.7% with similar pattern)
**Impact**: Medium (still useful, but less ROI)

**Mitigation**:
- Validate token savings in real tasks before rollout
- If savings <30%, reassess summary mode token budget
- If MCP doesn't support granular detail levels, fallback to topic scoping

### Risk 2: Summary Mode Insufficient for Planning

**Likelihood**: Low (planning needs high-level overview, not detailed examples)
**Impact**: Medium (might need to fetch detailed in some cases)

**Mitigation**:
- Phase 2 can fetch detailed if summary insufficient (fallback logic)
- Document scenarios where summary might not suffice
- Provide override mechanism (manual detail_level selection)

### Risk 3: Monitoring Overhead Impacts Performance

**Likelihood**: Low (monitoring is lightweight - just logging and counters)
**Impact**: Low (worst case: 2-3% slowdown)

**Mitigation**:
- Measure overhead in performance tests (<2% target)
- Make monitoring optional (env var or config flag)
- Use efficient data structures (dataclasses, no heavy serialization)

### Risk 4: Backward Compatibility Break

**Likelihood**: Very Low (default behavior unchanged)
**Impact**: High (existing workflows broken)

**Mitigation**:
- Default `detail_level=DETAILED` (100% backward compatible)
- Extensive integration tests with existing code
- Gradual rollout (opt-in initially, then default)

### Risk 5: Report Storage Accumulation

**Likelihood**: Medium (reports saved for every task)
**Impact**: Low (disk space usage, manageable)

**Mitigation**:
- Reports are small (<10KB each)
- Store in task-specific state directory (deleted on task completion if desired)
- Add cleanup job (delete reports >30 days old)

---

## Rollout Strategy

### Phase 1: Foundation (Week 1)
- Merge core classes (DetailLevel, MCPMonitor)
- Unit tests pass (100% coverage)
- **Checkpoint**: Code review, unit test review

### Phase 2: Integration (Week 2)
- Integrate with task-manager
- Integration tests pass
- **Checkpoint**: Integration testing with real MCP calls

### Phase 3: Validation (Week 3)
- Run on 5-10 real tasks
- Measure actual token savings and monitoring accuracy
- **Checkpoint**: Validate all acceptance criteria

### Phase 4: Production (Week 4)
- Update documentation
- Merge to main branch
- **Checkpoint**: Monitor initial production usage (1 week)

**Go/No-Go Decision Points**:
- After Phase 1: Code quality acceptable?
- After Phase 2: Integration smooth?
- After Phase 3: Metrics meet targets (≥50% savings, <2% overhead)?
- After Phase 4: No production issues in first week?

---

## Dependencies

### Required
- Python 3.8+ (dataclasses, type hints)
- Context7 MCP server (must support detail_level or topic granularity)
- Existing Context7Client implementation

### Optional
- design-patterns MCP (for monitoring integration, not required for progressive disclosure)

---

## Related Tasks

- **TASK-MCP-7796**: Review that identified these recommendations (COMPLETED)
- **Future**: TASK-MCP-YYYY - Implement MEDIUM priority recommendations (dynamic budgeting, caching docs)

---

## Notes

### Design Decisions

#### Decision 1: Why Enum for DetailLevel?
**Chosen**: Enum (SUMMARY, DETAILED)
**Alternative**: String literals ("summary", "detailed")

**Rationale**:
- Type safety (IDE autocomplete, mypy validation)
- Prevents typos ("summery" vs. "summary")
- Extensible (can add MINIMAL, COMPREHENSIVE later)

#### Decision 2: Why Two Separate Enhancements?
**Chosen**: Implement both in one task
**Alternative**: Two separate tasks

**Rationale**:
- Closely related (both MCP optimization)
- Shared testing (can validate savings with monitoring)
- Reduced overhead (single PR, single review, single rollout)
- Estimated effort manageable for single task (40 hours)

#### Decision 3: Why Default to DETAILED?
**Chosen**: Backward compatible default (DETAILED)
**Alternative**: Default to SUMMARY (force migration)

**Rationale**:
- 100% backward compatibility (zero-breaking-change)
- Existing code works without modification
- Gradual opt-in (Phase 2 updates separately)
- Lower risk rollout

### Open Questions

1. **Q**: Does Context7 MCP support detail_level parameter?
   **A**: TBD - Verify with MCP server documentation. If not, use token parameter as proxy (500 vs. 5000).

2. **Q**: Should monitoring be always-on or opt-in?
   **A**: Always-on by default (minimal overhead), opt-out via env var if needed.

3. **Q**: Where to store MCP usage reports long-term?
   **A**: `docs/state/{task_id}/mcp_usage_report.json` (deleted on task cleanup or kept for historical analysis).

---

**Created**: 2025-01-22T12:10:00Z
**Status**: IN_PROGRESS (Ready for implementation)
**Complexity**: 7/10 (Complex - two enhancements, requires careful integration)
**Estimated Effort**: 40 hours (~5 days) or 2-3 weeks with testing
**Priority**: HIGH
**Related**: TASK-MCP-7796 (Review findings)

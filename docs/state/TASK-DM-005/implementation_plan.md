# Implementation Plan: TASK-DM-005

## Task: Implement BrowserVerifier Abstraction

## Overview

Create a `BrowserVerifier` abstraction that hides browser verification tool selection from downstream agents. The orchestrator selects the right implementation based on task metadata. Primary implementation uses agent-browser (5.7x more token-efficient), with Playwright + Appium fallback for MAUI platform targets.

## Files to Create

### 1. `guardkit/orchestrator/browser_verifier.py` (Main Module)

**Purpose**: BrowserVerifier ABC and concrete implementations

**Components**:
- `BrowserVerifier` - Abstract base class defining interface
- `AgentBrowserVerifier` - Primary implementation using agent-browser CLI
- `PlaywrightAppiumVerifier` - Fallback for MAUI platform targets
- `select_verifier()` - Factory function for implementation selection

**Estimated LOC**: ~200 lines

### 2. `tests/unit/test_browser_verifier.py` (Unit Tests)

**Purpose**: Comprehensive unit tests with mocked browser interactions

**Test Coverage**:
- ABC interface contract tests
- AgentBrowserVerifier with mocked subprocess
- PlaywrightAppiumVerifier with mocked MCP calls
- select_verifier() routing logic
- Error handling (missing agent-browser, connection failures)
- Screenshot returns bytes for SSIM comparison

**Estimated LOC**: ~250 lines

## Implementation Phases

### Phase 1: TDD - Write Tests First (RED)
1. Create test file with failing tests for:
   - BrowserVerifier ABC structure
   - AgentBrowserVerifier.open(), screenshot(), get_accessibility_tree(), close()
   - PlaywrightAppiumVerifier methods
   - select_verifier() routing logic
   - Error handling scenarios

### Phase 2: Implementation (GREEN)
1. Create BrowserVerifier ABC
2. Implement AgentBrowserVerifier using subprocess for CLI
3. Implement PlaywrightAppiumVerifier (stub for Playwright MCP)
4. Implement select_verifier() factory
5. Add graceful error handling

### Phase 3: Refactor
1. Ensure clean separation of concerns
2. Add comprehensive docstrings
3. Export in __init__.py

## Dependencies

- Python 3.9+ (async/await support)
- pytest, pytest-asyncio (testing)
- typing (ABC, Optional, List, Dict)
- subprocess (for agent-browser CLI)
- No new external dependencies required

## Estimated Effort

- Duration: 4 hours
- LOC: ~450 lines total
- Complexity: 6/10

## Risk Mitigations

1. **Agent-browser not installed**: Graceful fallback with clear error message
2. **Subprocess failures**: Proper exception handling with BrowserVerifierError
3. **Async complexity**: Use asyncio patterns consistent with codebase

## Acceptance Criteria Mapping

| Criterion | Test | Implementation |
|-----------|------|----------------|
| BrowserVerifier ABC defined | test_browser_verifier_is_abc | BrowserVerifier class |
| AgentBrowserVerifier implements interface | test_agent_browser_verifier_* | AgentBrowserVerifier class |
| PlaywrightAppiumVerifier implements interface | test_playwright_appium_verifier_* | PlaywrightAppiumVerifier class |
| select_verifier() routes correctly | test_select_verifier_* | select_verifier() function |
| Agent-browser default for web | test_select_verifier_web_default | select_verifier() logic |
| Playwright for MAUI iOS/Android | test_select_verifier_maui_platform | select_verifier() logic |
| Screenshot returns bytes | test_screenshot_returns_bytes | screenshot() method |
| Graceful error handling | test_agent_browser_not_installed | Exception handling |

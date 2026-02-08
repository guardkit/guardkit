---
autobuild_state:
  base_branch: main
  current_turn: 1
  last_updated: '2026-02-08T08:13:49.880952'
  max_turns: 15
  started_at: '2026-02-08T08:05:44.435793'
  turns:
  - coach_success: true
    decision: approve
    feedback: null
    player_success: true
    player_summary: Implementation via task-work delegation
    timestamp: '2026-02-08T08:05:44.435793'
    turn: 1
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-D4CE
complexity: 6
created: 2026-02-07 10:00:00+00:00
dependencies:
- TASK-DM-003
feature_id: FEAT-D4CE
id: TASK-DM-005
implementation_mode: task-work
parent_review: TASK-REV-D3E0
priority: high
status: design_approved
tags:
- design-mode
- browser
- verification
- agent-browser
- playwright
task_type: feature
test_results:
  coverage: null
  last_run: null
  status: pending
title: Implement BrowserVerifier abstraction
updated: 2026-02-07 10:00:00+00:00
wave: 3
---

# Implement BrowserVerifier Abstraction

## Description

Create a `BrowserVerifier` abstraction that hides the browser verification tool choice from downstream agents. The orchestrator selects the right implementation based on task metadata's target stack. Primary: agent-browser (5.7x more token-efficient). Fallback: Playwright + Appium for MAUI platform targets.

## Requirements

1. Create `guardkit/orchestrator/browser_verifier.py`:
   ```python
   class BrowserVerifier(ABC):
       @abstractmethod
       async def open(self, url: str) -> None: ...
       @abstractmethod
       async def screenshot(self, selector: Optional[str] = None) -> bytes: ...
       @abstractmethod
       async def get_accessibility_tree(self) -> List[Dict]: ...
       @abstractmethod
       async def close(self) -> None: ...
   ```

2. `AgentBrowserVerifier` implementation (primary):
   - Uses agent-browser CLI (Vercel Labs)
   - ~1,400 tokens per verification cycle
   - Element refs (@e1, @e2) instead of CSS selectors
   - Default for all web targets (React/TypeScript, MAUI web preview)

3. `PlaywrightAppiumVerifier` implementation (fallback):
   - Uses Playwright MCP + Appium
   - ~7,800 tokens per verification cycle
   - Only for MAUI platform-specific targets (iOS Simulator, Android Emulator)

4. Factory function for implementation selection:
   ```python
   def select_verifier(target_stack: str, platform_target: Optional[str] = None) -> BrowserVerifier:
       if target_stack == 'maui' and platform_target not in (None, 'web'):
           return PlaywrightAppiumVerifier(platform_target)
       return AgentBrowserVerifier()
   ```

5. Coach never knows which browser tool is being used — only interacts via `BrowserVerifier` interface.

## Acceptance Criteria

- [ ] `BrowserVerifier` ABC defined with open/screenshot/get_accessibility_tree/close
- [ ] `AgentBrowserVerifier` implements the interface using agent-browser CLI
- [ ] `PlaywrightAppiumVerifier` implements the interface for MAUI platform targets
- [ ] `select_verifier()` factory routes based on target stack and platform
- [ ] Agent-browser is default for all web targets
- [ ] Playwright activates only for MAUI iOS/Android targets
- [ ] Screenshot returns bytes suitable for SSIM comparison
- [ ] Graceful error handling if agent-browser not installed
- [ ] Unit tests with mocked browser interactions

## Technical Notes

- See FEAT-DESIGN-MODE-spec.md §6 (Coach Agent: Visual Verification)
- See open questions analysis: agent-browser is 5.7x more token-efficient
- agent-browser requires: `npm install -g @anthropic/agent-browser` or similar
- Follows existing delegation pattern — orchestrator selects, agents don't know
---
id: TASK-TWD-008
title: Implement Coach honesty verification for Player claims
status: completed
started: 2026-01-02T10:00:00Z
completed: 2026-01-02T11:30:00Z
task_type: implementation
created: 2025-12-31T14:30:00Z
priority: medium
tags: [autobuild, coach, verification, quality-assurance]
complexity: 3
parent_feature: autobuild-task-work-delegation
wave: 4
implementation_mode: task-work
conductor_workspace: autobuild-twd-wave4-2
source_review: TASK-REV-RW01
completion_summary:
  files_created:
    - guardkit/orchestrator/coach_verification.py
    - tests/unit/test_coach_verification.py
  files_modified:
    - guardkit/orchestrator/agent_invoker.py
    - guardkit/orchestrator/autobuild.py
    - .claude/agents/autobuild-coach.md
    - tests/unit/test_agent_invoker.py
  tests_added: 25
  tests_passing: 128
  architectural_score: 82
---

# Task: Implement Coach honesty verification for Player claims

## Description

Add verification logic to the Coach agent that cross-references Player's self-reported claims against actual test results. If discrepancies are found, the Coach should flag them and factor this into the feedback.

This pattern is inspired by the Ralph Wiggum plugin's "intellectual honesty" design principle.

## Problem

Currently, the Coach trusts the Player's self-reported claims:
- `tests_passed: true` → Coach assumes tests actually pass
- `files_created: [...]` → Coach assumes files exist
- `test_output_summary: "5 tests passed"` → Coach assumes accuracy

If the Player (due to hallucination or optimization) reports false success, the Coach might approve prematurely.

## Target Behavior

Coach independently verifies key Player claims:
1. **Test Results**: Run tests and compare actual output vs claimed output
2. **File Existence**: Check that claimed files actually exist
3. **Test Count**: Verify test count matches claimed count
4. **Honesty Score**: Track discrepancy rate across turns

## Implementation

### 1. Add Honesty Verification to Coach

```python
# guardkit/orchestrator/coach_verification.py

from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path
import subprocess


@dataclass
class HonestyVerification:
    """Result of verifying Player claims."""
    verified: bool
    discrepancies: List[Discrepancy]
    honesty_score: float  # 0.0 to 1.0


@dataclass
class Discrepancy:
    """A discrepancy between Player claim and reality."""
    claim_type: str  # "test_result", "file_existence", "test_count"
    player_claim: str
    actual_value: str
    severity: str  # "critical", "warning", "info"


class CoachVerifier:
    """Verifies Player claims against reality."""

    def __init__(self, worktree_path: Path):
        self.worktree_path = worktree_path

    def verify_player_report(self, player_report: dict) -> HonestyVerification:
        """Verify all verifiable claims in Player report."""
        discrepancies = []

        # Verify test results
        if test_disc := self._verify_test_results(player_report):
            discrepancies.extend(test_disc)

        # Verify file existence
        if file_disc := self._verify_files_exist(player_report):
            discrepancies.extend(file_disc)

        # Verify test count
        if count_disc := self._verify_test_count(player_report):
            discrepancies.extend(count_disc)

        # Calculate honesty score
        total_claims = self._count_verifiable_claims(player_report)
        failed_claims = len([d for d in discrepancies if d.severity == "critical"])
        honesty_score = 1.0 - (failed_claims / max(total_claims, 1))

        return HonestyVerification(
            verified=len(discrepancies) == 0,
            discrepancies=discrepancies,
            honesty_score=honesty_score,
        )

    def _verify_test_results(self, report: dict) -> List[Discrepancy]:
        """Verify tests_passed claim against actual test run."""
        discrepancies = []

        claimed_passed = report.get("tests_passed", False)
        claimed_run = report.get("tests_run", False)

        if not claimed_run:
            # Player claims tests weren't run - verify by checking for test files
            return discrepancies

        # Run tests independently
        actual_result = self._run_tests()

        if claimed_passed != actual_result.passed:
            discrepancies.append(Discrepancy(
                claim_type="test_result",
                player_claim=f"tests_passed: {claimed_passed}",
                actual_value=f"tests_passed: {actual_result.passed}",
                severity="critical",
            ))

        return discrepancies

    def _verify_files_exist(self, report: dict) -> List[Discrepancy]:
        """Verify claimed files actually exist."""
        discrepancies = []

        for file_list_key in ["files_created", "files_modified", "tests_written"]:
            claimed_files = report.get(file_list_key, [])

            for file_path in claimed_files:
                full_path = self.worktree_path / file_path
                if not full_path.exists():
                    discrepancies.append(Discrepancy(
                        claim_type="file_existence",
                        player_claim=f"{file_list_key}: {file_path}",
                        actual_value="File does not exist",
                        severity="critical",
                    ))

        return discrepancies

    def _verify_test_count(self, report: dict) -> List[Discrepancy]:
        """Verify test count in summary matches actual."""
        discrepancies = []

        summary = report.get("test_output_summary", "")
        if not summary:
            return discrepancies

        # Extract claimed count from summary (e.g., "5 passed in 0.23s")
        claimed_count = self._extract_test_count(summary)
        if claimed_count is None:
            return discrepancies

        # Run tests and get actual count
        actual_result = self._run_tests()
        actual_count = actual_result.test_count

        if claimed_count != actual_count:
            discrepancies.append(Discrepancy(
                claim_type="test_count",
                player_claim=f"{claimed_count} tests",
                actual_value=f"{actual_count} tests",
                severity="warning",
            ))

        return discrepancies

    def _run_tests(self) -> "TestResult":
        """Run tests in worktree and return result."""
        # Detect test framework and run appropriate command
        # This is simplified - actual implementation would detect pytest/jest/etc.
        try:
            result = subprocess.run(
                ["pytest", "--tb=no", "-q"],
                cwd=self.worktree_path,
                capture_output=True,
                text=True,
                timeout=120,
            )
            return TestResult(
                passed=result.returncode == 0,
                test_count=self._parse_pytest_count(result.stdout),
                output=result.stdout,
            )
        except Exception as e:
            return TestResult(passed=False, test_count=0, output=str(e))

    def _extract_test_count(self, summary: str) -> Optional[int]:
        """Extract test count from summary string."""
        import re
        match = re.search(r"(\d+)\s+passed", summary)
        return int(match.group(1)) if match else None

    def _parse_pytest_count(self, output: str) -> int:
        """Parse test count from pytest output."""
        import re
        match = re.search(r"(\d+)\s+passed", output)
        return int(match.group(1)) if match else 0

    def _count_verifiable_claims(self, report: dict) -> int:
        """Count total verifiable claims in report."""
        count = 0
        if report.get("tests_run"):
            count += 2  # tests_passed + test_count
        count += len(report.get("files_created", []))
        count += len(report.get("files_modified", []))
        count += len(report.get("tests_written", []))
        return count


@dataclass
class TestResult:
    passed: bool
    test_count: int
    output: str
```

### 2. Update Coach Agent to Use Verification

```python
# guardkit/orchestrator/agent_invoker.py

async def invoke_coach(
    self,
    task_id: str,
    turn: int,
    player_report: dict,
    requirements: str,
    acceptance_criteria: List[str],
) -> CoachResult:
    """Invoke Coach with honesty verification."""

    # First: Verify Player claims
    verifier = CoachVerifier(self.worktree_path)
    honesty_check = verifier.verify_player_report(player_report)

    # Include verification in Coach context
    verification_context = self._format_verification_context(honesty_check)

    # Build Coach prompt with verification results
    prompt = self._build_coach_prompt(
        task_id=task_id,
        turn=turn,
        player_report=player_report,
        verification_context=verification_context,  # NEW
        requirements=requirements,
        acceptance_criteria=acceptance_criteria,
    )

    # ... rest of Coach invocation
```

### 3. Update Coach Agent Prompt

Add to `.claude/agents/autobuild-coach.md`:

```markdown
## Honesty Verification

Before reviewing the Player's work, the system automatically verifies key claims.
You will receive a verification report showing any discrepancies.

### Verification Categories

| Claim Type | What's Verified |
|------------|-----------------|
| test_result | Claimed `tests_passed` vs actual test run |
| file_existence | Claimed files vs filesystem reality |
| test_count | Claimed test count vs actual count |

### Handling Discrepancies

**Critical Discrepancies** (severity: critical):
- MUST result in `decision: feedback`
- Include discrepancy in your feedback
- Do NOT approve if critical discrepancies exist

**Warning Discrepancies** (severity: warning):
- Note in your validation but may not block approval
- Use judgment based on overall quality

### Example Verification Context

```
HONESTY VERIFICATION RESULTS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Honesty Score: 0.67 (2/3 claims verified)

DISCREPANCIES FOUND:
  ✗ [CRITICAL] test_result
    Player claimed: tests_passed: true
    Actual value: tests_passed: false

  ✗ [WARNING] test_count
    Player claimed: 5 tests
    Actual value: 4 tests

FILES VERIFIED:
  ✓ src/auth/oauth.py exists
  ✓ tests/test_oauth.py exists
```

### Response to Discrepancies

When critical discrepancies are found:

```json
{
  "decision": "feedback",
  "honesty_issues": [
    {
      "claim": "tests_passed: true",
      "actual": "tests_passed: false",
      "action_required": "Fix failing tests before claiming success"
    }
  ],
  "feedback": "Player claimed tests pass but verification shows failures. Fix the failing tests."
}
```
```

### 4. Add Honesty Tracking Across Turns

```python
# guardkit/orchestrator/autobuild.py

class AutoBuildOrchestrator:
    def __init__(self, ...):
        # ...
        self.honesty_history: List[float] = []  # Track scores across turns

    def _record_honesty(self, score: float) -> None:
        """Record honesty score for this turn."""
        self.honesty_history.append(score)

        # Warn if pattern of dishonesty
        if len(self.honesty_history) >= 3:
            avg_score = sum(self.honesty_history) / len(self.honesty_history)
            if avg_score < 0.8:
                logger.warning(
                    f"Low average honesty score: {avg_score:.2f}. "
                    "Player may be hallucinating or over-claiming."
                )
```

## Acceptance Criteria

1. Coach verifies `tests_passed` claim by running tests independently
2. Coach verifies claimed files exist on filesystem
3. Coach verifies test count matches claimed summary
4. Critical discrepancies prevent approval
5. Honesty score tracked across turns
6. Verification results included in Coach report

## Files to Modify

- `guardkit/orchestrator/coach_verification.py` - New verification module
- `guardkit/orchestrator/agent_invoker.py` - Add verification to Coach flow
- `.claude/agents/autobuild-coach.md` - Add honesty verification instructions
- `guardkit/orchestrator/autobuild.py` - Track honesty history

## Testing

1. Unit test: File existence verification
2. Unit test: Test result verification
3. Unit test: Test count parsing
4. Unit test: Honesty score calculation
5. Integration test: Coach rejects when critical discrepancy found
6. Integration test: Coach approves when all claims verified

## Notes

- Verification adds latency (running tests twice) - consider caching
- Some claims may not be verifiable (implementation_notes, concerns)
- Focus on objective, verifiable claims
- Consider making verification optional via flag for speed-critical scenarios

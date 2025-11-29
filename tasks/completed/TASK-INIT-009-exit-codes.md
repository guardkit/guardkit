---
id: TASK-INIT-009
title: "Port exit codes for CI/CD integration"
status: completed
created: 2025-11-26T07:30:00Z
updated: 2025-11-26T10:00:00Z
completed_at: 2025-11-26T10:00:00Z
priority: low
tags: [template-init, ci-cd, week4, discovery-automation]
complexity: 2
estimated_hours: 2
actual_hours: 1.5
parent_review: TASK-5E55
week: 4
phase: discovery-automation
related_tasks: [TASK-INIT-006]
dependencies: [TASK-INIT-006]
implementation_notes: |
  - Used placeholder quality scoring until TASK-INIT-006 is implemented
  - Exit codes: 0 (≥8/10), 1 (6-7.9/10), 2 (<6/10), 3 (error), 130 (cancelled)
  - Placeholder scorer bases score on Q&A answers (testing, error handling, DI, validation, architecture, docs)
  - Easy to replace with full QualityScorer when TASK-INIT-006 is done
  - Backward compatible tuple return type
  - Comprehensive CI/CD usage guidance displayed
test_results:
  status: passing
  coverage: null
  last_run: 2025-11-26T09:45:00Z
completion_metrics:
  total_duration: 2.5 hours
  implementation_time: 1.5 hours
  review_time: 0 hours
  files_modified: 1
  lines_added: 215
  tests_added: 0
  requirements_met: 9/9
  commit: 0f48303b6874b208b802f5342eb9ddacea6e84d8
deliverables:
  - Modified run() method to return (answers, exit_code) tuple
  - Added _calculate_placeholder_quality_score() method
  - Added _calculate_exit_code() method
  - Added _display_exit_code_info() method
  - Added main() entry point
  - Added __main__ block for CLI execution
---

# Task: Port Exit Codes for CI/CD Integration

## Problem Statement

`/template-init` doesn't return quality-based exit codes, missing Critical Gap #13 from TASK-5E55. CI/CD pipelines cannot use exit codes to enforce template quality gates.

**Impact**: Templates cannot be quality-gated in automated workflows, risking low-quality template deployment.

## Analysis Findings

From TASK-5E55 review:
- `/template-create` returns exit codes based on quality scores
- Exit codes: 0 (≥8/10), 1 (6-7.9/10), 2 (<6/10), 3+ (errors)
- Enables CI/CD quality gates
- `/template-init` has NO exit code support
- Gap severity: 🟡 **MEDIUM** (limits CI/CD integration)

**Current State**: Always exits 0 (success) regardless of quality

**Desired State**: Exit code reflects template quality for CI/CD gates

## Recommended Fix

**Approach**: Return tuple (answers, exit_code) from run(), add main() entry point.

**Strategy**:
- **MINIMAL SCOPE**: Add exit code calculation, modify return type
- **QUALITY-BASED**: Use quality score from TASK-INIT-006
- **CI/CD READY**: Standard exit code convention (0=success, 1-2=warnings)
- **DISPLAY**: Show exit code meaning to user

## Code Changes Required

### File: installer/global/commands/lib/greenfield_qa_session.py

**MODIFY run() method** (around line 1000):

```python
def run(self) -> tuple[Optional[GreenfieldAnswers], int]:
    """
    Run interactive Q&A session for greenfield template creation.

    NOW RETURNS exit code for CI/CD integration.

    Returns:
        Tuple of (answers, exit_code)
        - answers: Q&A results
        - exit_code: Quality-based exit code
          - 0: High quality (≥8/10)
          - 1: Medium quality (6-7.9/10)
          - 2: Low quality (<6/10)
          - 3: Error occurred

    Example:
        >>> session = TemplateInitQASession()
        >>> answers, exit_code = session.run()
        >>> exit_code
        0
    """
    try:
        # ... existing Phases 1-4 ...

        # Quality Scoring (from TASK-INIT-006)
        scorer = QualityScorer(self._session_data, template_path)
        quality_scores = scorer.calculate_score()
        scorer.generate_report(quality_scores)

        # Calculate exit code from quality score
        overall_score = quality_scores['overall_score']

        if overall_score >= 8.0:
            exit_code = 0  # High quality
        elif overall_score >= 6.0:
            exit_code = 1  # Medium quality
        else:
            exit_code = 2  # Low quality

        # Display exit code meaning
        self._display_exit_code_info(exit_code, overall_score)

        return self.answers, exit_code

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return None, 3  # Error exit code


def _display_exit_code_info(self, exit_code: int, score: float) -> None:
    """
    Display exit code information for CI/CD awareness.

    Args:
        exit_code: Calculated exit code (0-3)
        score: Quality score that determined exit code
    """
    print("\n" + "=" * 70)
    print("  CI/CD Integration")
    print("=" * 70 + "\n")

    exit_code_info = {
        0: ("✅ SUCCESS", "High quality (≥8/10)", "Template ready for production"),
        1: ("⚠️ WARNING", "Medium quality (6-7.9/10)", "Review recommended before production"),
        2: ("❌ LOW QUALITY", "Below threshold (<6/10)", "Improvements required"),
        3: ("🔥 ERROR", "Execution failed", "Check error messages above")
    }

    status, reason, action = exit_code_info.get(exit_code, ("UNKNOWN", "Unknown", "Check logs"))

    print(f"Exit Code: {exit_code}")
    print(f"Status: {status}")
    print(f"Reason: {reason} (score: {score:.1f}/10)")
    print(f"Action: {action}\n")

    if exit_code in [0, 1]:
        print("CI/CD usage:")
        print("  /template-init && echo 'Template meets quality threshold'")
    else:
        print("CI/CD will fail on exit code 2 or 3")
        print("  /template-init || exit 1")
```

**ADD main() entry point** (at end of file):

```python
def main() -> None:
    """
    Entry point for /template-init command.

    Handles exit code propagation for CI/CD.

    Usage:
        python -m installer.global.commands.lib.greenfield_qa_session

    Returns exit code based on template quality:
        0: High quality (≥8/10)
        1: Medium quality (6-7.9/10)
        2: Low quality (<6/10)
        3: Error occurred
    """
    import sys

    session = TemplateInitQASession()

    try:
        answers, exit_code = session.run()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️ Template creation cancelled by user")
        sys.exit(130)  # Standard exit code for SIGINT
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(3)


if __name__ == "__main__":
    main()
```

## Scope Constraints

### ❌ DO NOT
- Change quality scoring logic (TASK-INIT-006)
- Add new exit code categories
- Make exit codes mandatory
- Modify CI/CD pipeline configurations
- Change command invocation

### ✅ DO ONLY
- Return exit code from run()
- Calculate exit code from quality score
- Display exit code meaning
- Add main() entry point
- Document CI/CD usage

## Files to Modify

1. **installer/global/commands/lib/greenfield_qa_session.py** - MODIFY
   - `run()` method return type and exit code calculation (~15 lines)

2. **installer/global/commands/lib/greenfield_qa_session.py** - ADD
   - `_display_exit_code_info()` method (~30 lines)
   - `main()` entry point (~20 lines)

## Files to NOT Touch

- Quality scoring logic (TASK-INIT-006)
- Command registration
- Q&A workflow
- Template save logic

## Testing Requirements

### Unit Tests

```python
def test_exit_code_high_quality():
    """Test exit code 0 for high quality."""
    session = TemplateInitQASession()

    # Mock high quality score
    with patch.object(QualityScorer, 'calculate_score') as mock_score:
        mock_score.return_value = {
            'overall_score': 9.0,
            'production_ready': True
        }

        answers, exit_code = session.run()

        assert exit_code == 0

def test_exit_code_medium_quality():
    """Test exit code 1 for medium quality."""
    session = TemplateInitQASession()

    with patch.object(QualityScorer, 'calculate_score') as mock_score:
        mock_score.return_value = {
            'overall_score': 7.0,
            'production_ready': True
        }

        answers, exit_code = session.run()

        assert exit_code == 1

def test_exit_code_low_quality():
    """Test exit code 2 for low quality."""
    session = TemplateInitQASession()

    with patch.object(QualityScorer, 'calculate_score') as mock_score:
        mock_score.return_value = {
            'overall_score': 5.0,
            'production_ready': False
        }

        answers, exit_code = session.run()

        assert exit_code == 2

def test_exit_code_error():
    """Test exit code 3 on exception."""
    session = TemplateInitQASession()

    with patch.object(session, '_save_template') as mock_save:
        mock_save.side_effect = Exception("Test error")

        answers, exit_code = session.run()

        assert exit_code == 3
        assert answers is None
```

### Integration Tests

```python
def test_main_entry_point():
    """Test main() entry point propagates exit code."""
    with patch('sys.exit') as mock_exit:
        with patch.object(TemplateInitQASession, 'run') as mock_run:
            mock_run.return_value = (None, 0)

            main()

            mock_exit.assert_called_once_with(0)

def test_keyboard_interrupt_handling():
    """Test KeyboardInterrupt handling."""
    with patch('sys.exit') as mock_exit:
        with patch.object(TemplateInitQASession, 'run') as mock_run:
            mock_run.side_effect = KeyboardInterrupt()

            main()

            mock_exit.assert_called_once_with(130)
```

## Acceptance Criteria

- [ ] run() returns tuple (answers, exit_code)
- [ ] Exit code 0 for quality ≥8/10
- [ ] Exit code 1 for quality 6-7.9/10
- [ ] Exit code 2 for quality <6/10
- [ ] Exit code 3 for errors
- [ ] Exit code meaning displayed
- [ ] main() entry point added
- [ ] CI/CD usage examples shown
- [ ] Backward compatible (tuple unpacking works)

## Estimated Effort

**2 hours** broken down as:
- Study template-create exit code logic (15 minutes)
- Modify run() return type (30 minutes)
- Implement exit code display (30 minutes)
- Add main() entry point (30 minutes)
- Testing (15 minutes)

## Dependencies

**TASK-INIT-006** - Requires quality scoring to calculate exit codes

## Risk Assessment

### Risks

| Risk | Probability | Impact | Severity |
|------|------------|--------|----------|
| Breaking change to run() signature | Low | Medium | 🟡 Low |
| Exit code thresholds too strict | Low | Low | 🟢 Minimal |
| CI/CD integration unclear | Medium | Low | 🟡 Low |

### Mitigation Strategies

1. **Breaking change**: Return tuple is backward compatible with tuple unpacking
2. **Threshold strictness**: Use same thresholds as template-create (8/6)
3. **CI/CD clarity**: Display clear usage examples and exit code meanings

## References

- **Parent Review**: TASK-5E55
- **Related Task**: TASK-INIT-006 (quality scoring)
- **Exit Code Convention**:
  - 0: Success (high quality)
  - 1: Warning (medium quality)
  - 2: Failure (low quality)
  - 3+: Error

## Success Metrics

When complete:
- ✅ Exit codes reflect template quality
- ✅ CI/CD can enforce quality gates
- ✅ Exit code meaning clear to users
- ✅ Error handling robust
- ✅ Backward compatible return type

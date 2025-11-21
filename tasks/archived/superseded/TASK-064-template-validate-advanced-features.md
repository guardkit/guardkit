# TASK-064: Template Validate Advanced Features (Phase 3)

**Created**: 2025-11-08
**Priority**: Low
**Type**: Enhancement
**Parent**: Template Validation Strategy
**Status**: Backlog
**Complexity**: 5/10 (Medium)
**Estimated Effort**: 2-3 days (16-24 hours)
**Dependencies**: TASK-044 (Template Validate Command - MVP)

---

## Problem Statement

Enhance `/template-validate` command with advanced features that were deferred from the MVP (TASK-044) to optimize initial implementation time. These features add significant value for power users and CI/CD integration but are not required for basic template validation workflows.

**Goal**: Add session persistence, inline fix automation, and batch processing capabilities to the template validation system.

---

## Context

**Related Tasks**:
- [TASK-044](./TASK-044-create-template-validate-command.md) - Template Validate Command MVP (prerequisite)
- [Template Validation Strategy](../../docs/research/template-validation-strategy.md) - Overall strategy

**Current State** (After TASK-044):
- Interactive template validation with 16-section framework ✓
- Section selection (--sections flag) ✓
- Comprehensive audit reports ✓
- Detection-only mode (no inline fixes) ✓
- In-memory session state (no persistence) ✓
- Interactive mode only ✓

**Desired State**:
- Session save/resume for multi-hour audits
- Inline fix automation for common issues
- Non-interactive batch mode for CI/CD
- Session history and metrics tracking

---

## Objectives

### Primary Objective
Add advanced features to `/template-validate` that enhance usability for complex audits and enable CI/CD integration.

### Success Criteria
- [x] Session persistence (save/resume with --resume flag)
- [x] Inline fix automation for fixable issues
- [x] Non-interactive batch mode (--non-interactive flag)
- [x] Session history tracking
- [x] Fix success rate metrics
- [x] All features tested (≥75% coverage)
- [x] Backward compatible with TASK-044 MVP
- [x] Documentation updated

---

## Features to Implement

### Feature 1: Session Persistence & Resume

**Purpose**: Allow users to pause long audits and resume later without losing progress.

**Implementation**:

```python
# File: installer/global/lib/template_validation/session.py

class SessionManager:
    """Manage audit session persistence"""

    def __init__(self, sessions_dir: Path):
        self.sessions_dir = sessions_dir
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def save_session(self, session: AuditSession) -> Path:
        """
        Save session to JSON file.

        Location: ~/.agentecflow/template-validation/sessions/{session_id}.json

        Format:
        {
          "session_id": "audit-{template_name}-{timestamp}",
          "template_path": "/path/to/template",
          "created_at": "2025-11-08T14:30:00Z",
          "updated_at": "2025-11-08T15:45:00Z",
          "sections_completed": [1, 2, 3, 4, 5],
          "section_results": {
            "1": {
              "score": 9.2,
              "issues": [...],
              "findings": {...}
            },
            ...
          },
          "fixes_applied": []
        }
        """
        session_file = self.sessions_dir / f"{session.session_id}.json"

        data = {
            'session_id': session.session_id,
            'template_path': str(session.template_path),
            'template_name': session.template_name,
            'created_at': session.created_at.isoformat(),
            'updated_at': datetime.now().isoformat(),
            'sections_completed': session.sections_completed,
            'section_results': self._serialize_results(session.section_results),
            'fixes_applied': self._serialize_fixes(session.fixes_applied)
        }

        # Atomic write (write to temp, then rename)
        temp_file = session_file.with_suffix('.tmp')
        temp_file.write_text(json.dumps(data, indent=2))
        temp_file.rename(session_file)

        return session_file

    def load_session(self, session_id: str) -> Optional[AuditSession]:
        """Load session from JSON file"""
        session_file = self.sessions_dir / f"{session_id}.json"

        if not session_file.exists():
            return None

        try:
            data = json.loads(session_file.read_text())

            # Validate schema
            self._validate_session_schema(data)

            return AuditSession(
                session_id=data['session_id'],
                template_path=Path(data['template_path']),
                template_name=data['template_name'],
                created_at=datetime.fromisoformat(data['created_at']),
                updated_at=datetime.fromisoformat(data['updated_at']),
                sections_completed=data['sections_completed'],
                section_results=self._deserialize_results(data['section_results']),
                fixes_applied=self._deserialize_fixes(data['fixes_applied'])
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            raise SessionLoadError(f"Failed to load session {session_id}: {e}")

    def list_sessions(self, template_name: Optional[str] = None) -> List[SessionInfo]:
        """List all saved sessions, optionally filtered by template"""
        sessions = []
        for session_file in self.sessions_dir.glob("*.json"):
            try:
                data = json.loads(session_file.read_text())
                if template_name is None or data['template_name'] == template_name:
                    sessions.append(SessionInfo(
                        session_id=data['session_id'],
                        template_name=data['template_name'],
                        created_at=datetime.fromisoformat(data['created_at']),
                        updated_at=datetime.fromisoformat(data['updated_at']),
                        sections_completed=len(data['sections_completed']),
                        total_sections=16
                    ))
            except (json.JSONDecodeError, KeyError):
                # Skip corrupted sessions
                continue

        return sorted(sessions, key=lambda s: s.updated_at, reverse=True)
```

**Usage**:
```bash
# Start audit
/template-validate ./templates/my-template

# Session auto-saved after each section
# Session ID: audit-my-template-20251108143000

# Resume later
/template-validate ./templates/my-template --resume audit-my-template-20251108143000

# List sessions
/template-validate --list-sessions
/template-validate --list-sessions --template my-template
```

**Testing**:
- Test save/load round-trip
- Test atomic write (no corruption on crash)
- Test schema validation on load
- Test session listing and filtering

---

### Feature 2: Inline Fix Automation

**Purpose**: Automatically fix common issues detected during audit (with user approval).

**Implementation**:

```python
# File: installer/global/lib/template_validation/inline_fixer.py

class InlineFixer:
    """Apply automated fixes for common audit issues"""

    def __init__(self):
        self.fix_handlers = self._register_handlers()

    def _register_handlers(self) -> Dict[str, FixHandler]:
        """Register fix handlers for different issue types"""
        return {
            'missing_placeholder': self._fix_missing_placeholder,
            'invalid_naming': self._fix_invalid_naming,
            'missing_metadata': self._fix_missing_metadata,
            'broken_reference': self._fix_broken_reference,
            # ... more handlers
        }

    def can_fix(self, issue: AuditIssue) -> bool:
        """Check if issue is fixable"""
        return issue.fixable and issue.fix_action in self.fix_handlers

    def apply_fix(
        self,
        issue: AuditIssue,
        interactive: bool = True
    ) -> FixLog:
        """
        Apply fix for an issue.

        Args:
            issue: Issue to fix
            interactive: Prompt user for confirmation

        Returns:
            FixLog with success status and details
        """
        if not self.can_fix(issue):
            raise ValueError(f"Issue not fixable: {issue.title}")

        # Interactive confirmation
        if interactive:
            print(f"\nFixable issue detected:")
            print(f"  Section: {issue.section_num}")
            print(f"  Issue: {issue.title}")
            print(f"  Fix: {issue.fix_action}")
            print(f"  File: {issue.file_path}")

            response = input("\nApply fix? [y/N]: ").strip().lower()
            if response != 'y':
                return FixLog(
                    timestamp=datetime.now(),
                    section_num=issue.section_num,
                    issue_title=issue.title,
                    fix_action=issue.fix_action,
                    success=False,
                    error_message="User declined fix"
                )

        # Apply fix
        try:
            handler = self.fix_handlers[issue.fix_action]
            handler(issue)

            return FixLog(
                timestamp=datetime.now(),
                section_num=issue.section_num,
                issue_title=issue.title,
                fix_action=issue.fix_action,
                success=True
            )
        except Exception as e:
            return FixLog(
                timestamp=datetime.now(),
                section_num=issue.section_num,
                issue_title=issue.title,
                fix_action=issue.fix_action,
                success=False,
                error_message=str(e)
            )

    def _fix_missing_placeholder(self, issue: AuditIssue):
        """Add missing placeholder to manifest"""
        manifest_path = issue.file_path
        manifest = json.loads(manifest_path.read_text())

        manifest['placeholders'].append(issue.fix_data['placeholder'])

        manifest_path.write_text(json.dumps(manifest, indent=2))

    def _fix_invalid_naming(self, issue: AuditIssue):
        """Rename file to match naming convention"""
        old_path = issue.file_path
        new_path = issue.fix_data['new_path']

        old_path.rename(new_path)

    # ... more fix handlers
```

**Fixable Issues**:
1. Missing placeholders in manifest
2. Invalid file naming conventions
3. Missing metadata fields
4. Broken cross-references
5. Incorrect file permissions
6. Missing required files (can auto-generate templates)

**Usage**:
```bash
# Interactive mode (prompts for each fix)
/template-validate ./templates/my-template

# Auto-fix mode (applies all fixes without prompting)
/template-validate ./templates/my-template --auto-fix

# Fix-only mode (run fixes from previous audit)
/template-validate ./templates/my-template --resume session-id --apply-fixes
```

**Testing**:
- Test each fix handler individually
- Test fix rollback on error
- Test interactive vs auto-fix modes
- Test fix logging and metrics

---

### Feature 3: Non-Interactive Batch Mode

**Purpose**: Run audits in CI/CD pipelines without user interaction.

**Implementation**:

```python
# File: installer/global/commands/lib/template_validate/orchestrator.py

class TemplateValidateOrchestrator:
    """Enhanced orchestrator with batch mode support"""

    def run(self) -> AuditResult:
        """Execute validation (interactive or batch)"""

        if self.config.non_interactive:
            return self._run_batch_mode()
        else:
            return self._run_interactive_mode()

    def _run_batch_mode(self) -> AuditResult:
        """
        Non-interactive batch mode for CI/CD.

        Behavior:
        - No user prompts
        - Auto-select all sections (unless --sections specified)
        - No inline fix prompts (apply if --auto-fix, otherwise skip)
        - Generate report and exit with code based on result
        - Save session for later review
        """
        # Auto-select sections
        if self.config.sections:
            sections = self._parse_section_spec(self.config.sections)
        else:
            sections = list(range(1, 17))  # All sections

        # Execute all sections
        for section_num in sections:
            print(f"Executing Section {section_num}...", end='', flush=True)

            result = self._execute_section(section_num)
            self.session.add_result(section_num, result)

            # Auto-fix if enabled
            if self.config.auto_fix and result.has_fixable_issues():
                for issue in result.fixable_issues():
                    fix_log = self.fixer.apply_fix(issue, interactive=False)
                    self.session.add_fix(fix_log)

            print(f" Score: {result.score:.1f}/10")

        # Generate report
        report = self._generate_report()

        # Save session
        self.session_manager.save_session(self.session)

        return AuditResult(
            session=self.session,
            report=report,
            recommendation=self.session.recommendation()
        )
```

**Exit Codes**:
```python
EXIT_CODES = {
    0: "APPROVE - Template approved for production",
    1: "NEEDS_IMPROVEMENT - Template needs fixes",
    2: "REJECT - Template rejected",
    3: "ERROR - Validation error"
}
```

**Usage**:
```bash
# CI/CD batch mode
/template-validate ./templates/my-template --non-interactive --sections 1-12

# Exit code 0 = approve, 1 = needs improvement, 2 = reject
echo $?

# With auto-fix
/template-validate ./templates/my-template --non-interactive --auto-fix

# Generate JSON report for parsing
/template-validate ./templates/my-template --non-interactive --output-format=json
```

**Testing**:
- Test batch mode with all sections
- Test exit code generation
- Test JSON report format
- Test integration with CI/CD scripts

---

### Feature 4: Session History & Metrics

**Purpose**: Track validation history and improvement over time.

**Implementation**:

```python
# File: installer/global/lib/template_validation/metrics.py

@dataclass
class ValidationMetrics:
    """Metrics for validation history"""
    template_name: str
    total_audits: int
    average_score: float
    score_trend: List[float]  # Last 10 scores
    most_common_issues: List[Tuple[str, int]]  # (issue_title, count)
    fix_success_rate: float
    sections_with_most_issues: List[Tuple[int, int]]  # (section_num, issue_count)

class MetricsTracker:
    """Track validation metrics over time"""

    def __init__(self, metrics_dir: Path):
        self.metrics_dir = metrics_dir
        self.metrics_dir.mkdir(parents=True, exist_ok=True)

    def record_audit(self, session: AuditSession):
        """Record audit results for metrics"""
        metrics_file = self.metrics_dir / f"{session.template_name}.json"

        if metrics_file.exists():
            data = json.loads(metrics_file.read_text())
        else:
            data = {
                'template_name': session.template_name,
                'audits': []
            }

        data['audits'].append({
            'session_id': session.session_id,
            'date': session.created_at.isoformat(),
            'score': session.overall_score(),
            'sections_completed': len(session.sections_completed),
            'issues_found': sum(len(r.issues) for r in session.section_results.values()),
            'fixes_applied': len(session.fixes_applied)
        })

        metrics_file.write_text(json.dumps(data, indent=2))

    def get_metrics(self, template_name: str) -> ValidationMetrics:
        """Get metrics for a template"""
        # Calculate metrics from history
        # ...
```

**Usage**:
```bash
# Show metrics for template
/template-validate --metrics my-template

# Show trends
/template-validate --metrics my-template --show-trends
```

---

## Implementation Strategy

### Phase 1: Session Persistence (1 day)
1. Implement `SessionManager` class
2. Add JSON serialization/deserialization
3. Add atomic write safety
4. Add schema validation on load
5. Add session listing
6. Unit tests for save/load/list
7. Integration test with orchestrator

### Phase 2: Inline Fix Automation (1 day)
1. Implement `InlineFixer` class
2. Implement fix handlers for 5-6 common issues
3. Add fix confirmation prompts (interactive)
4. Add auto-fix mode (--auto-fix flag)
5. Add fix logging to session
6. Unit tests for each fix handler
7. Integration test with orchestrator

### Phase 3: Batch Mode (0.5 day)
1. Add `--non-interactive` flag support
2. Implement batch mode execution
3. Add exit code logic
4. Add JSON output format
5. Integration tests for CI/CD scenarios

### Phase 4: Metrics & History (0.5 day)
1. Implement `MetricsTracker` class
2. Add metrics recording after each audit
3. Add metrics display command
4. Add trend visualization
5. Unit tests for metrics calculation

### Phase 5: Testing & Documentation (0.5 day)
1. Complete test coverage (≥75%)
2. End-to-end testing of all features
3. Update command specification
4. Add usage examples
5. Update validation strategy doc

**Total Estimated Effort**: 2-3 days (16-24 hours)

---

## Files to Create/Modify

### New Files
- `installer/global/lib/template_validation/session.py` - Session persistence
- `installer/global/lib/template_validation/inline_fixer.py` - Fix automation
- `installer/global/lib/template_validation/metrics.py` - Metrics tracking
- `tests/unit/test_session_manager.py` - Session tests
- `tests/unit/test_inline_fixer.py` - Fixer tests
- `tests/unit/test_metrics.py` - Metrics tests
- `tests/integration/test_batch_mode.py` - Batch mode tests

### Modified Files
- `installer/global/commands/lib/template_validate/orchestrator.py` - Add batch mode, fix integration
- `installer/global/commands/lib/template_validate/config.py` - Add new flags
- `installer/global/commands/template-validate.md` - Update documentation
- `installer/global/lib/template_validation/models.py` - Add FixLog, SessionInfo models

---

## Acceptance Criteria

### Functional Requirements
- [ ] Session save/resume works (--resume flag)
- [ ] Sessions list correctly (--list-sessions)
- [ ] Inline fixes work (interactive prompts)
- [ ] Auto-fix mode works (--auto-fix flag)
- [ ] Batch mode works (--non-interactive flag)
- [ ] Exit codes correct (0/1/2/3)
- [ ] JSON output format works
- [ ] Metrics tracking works
- [ ] All features backward compatible with MVP

### Quality Requirements
- [ ] Test coverage ≥75%
- [ ] All tests passing
- [ ] Session corruption impossible (atomic writes)
- [ ] Fix handlers tested individually
- [ ] Batch mode tested in CI/CD context

### Documentation Requirements
- [ ] Command specification updated
- [ ] Usage examples for all features
- [ ] CI/CD integration guide

---

## Testing Strategy

### Unit Tests
```python
# tests/unit/test_session_manager.py
def test_save_load_roundtrip()
def test_atomic_write_on_crash()
def test_schema_validation()
def test_list_sessions()

# tests/unit/test_inline_fixer.py
def test_fix_missing_placeholder()
def test_fix_invalid_naming()
def test_fix_confirmation_prompt()
def test_auto_fix_mode()

# tests/unit/test_metrics.py
def test_record_audit()
def test_calculate_metrics()
def test_score_trends()
```

### Integration Tests
```python
# tests/integration/test_batch_mode.py
def test_batch_mode_all_sections()
def test_batch_mode_with_auto_fix()
def test_exit_code_approve()
def test_exit_code_needs_improvement()
def test_exit_code_reject()
def test_json_output_format()
```

---

## Usage Examples

### Session Persistence
```bash
# Long audit - save progress
/template-validate ./templates/complex-template --sections 1-8
# (Ctrl+C to interrupt)

# Resume later
/template-validate ./templates/complex-template --resume audit-complex-template-20251108143000

# Continue from section 9
# (Sections 1-8 already completed, scores preserved)
```

### Inline Fixes
```bash
# Interactive fix mode
/template-validate ./templates/my-template

# Output:
# Section 1: Manifest Analysis
# ✓ Score: 8.5/10
# ⚠️  1 fixable issue detected:
#     Issue: Missing placeholder 'project_description'
#     Fix: Add placeholder to manifest.json
#
#     Apply fix? [y/N]: y
#
# ✅ Fix applied successfully
```

### Batch Mode (CI/CD)
```bash
# .github/workflows/validate-templates.yml
name: Validate Templates

on: [pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Validate Template
        run: |
          /template-validate ./templates/new-template \
            --non-interactive \
            --sections 1-12 \
            --output-format=json \
            > validation-report.json

      - name: Check Result
        run: |
          EXIT_CODE=$?
          if [ $EXIT_CODE -eq 0 ]; then
            echo "✅ Template approved"
          elif [ $EXIT_CODE -eq 1 ]; then
            echo "⚠️  Template needs improvement"
            exit 1
          else
            echo "❌ Template rejected"
            exit 1
          fi
```

---

## Dependencies

**Required**:
- TASK-044: Template Validate Command MVP (must be completed first)
- Python 3.8+
- Existing template validation infrastructure

**Optional**:
- CI/CD system for batch mode testing (GitHub Actions, GitLab CI, etc.)

---

## Risks and Mitigation

### Risk 1: Session Corruption
**Mitigation**: Atomic writes, backup before save, schema validation on load

### Risk 2: Fix Side Effects
**Mitigation**: Comprehensive testing of each fix handler, rollback on error

### Risk 3: Backward Compatibility
**Mitigation**: All new features behind flags, MVP behavior unchanged by default

---

## Success Metrics

**Quantitative**:
- Session save/resume 100% reliable
- Fix success rate ≥90%
- Test coverage ≥75%
- Batch mode exit codes 100% accurate

**Qualitative**:
- Users can pause/resume long audits
- Common issues fixed automatically
- CI/CD integration works smoothly
- Metrics provide actionable insights

---

## Related Documents

- [TASK-044](./TASK-044-create-template-validate-command.md) - Template Validate MVP
- [Template Validation Strategy](../../docs/research/template-validation-strategy.md) - Overall strategy

---

**Document Status**: Ready for Implementation (after TASK-044)
**Created**: 2025-11-08
**Phase**: 3 of 3 (Template Validation Strategy - Advanced Features)
**Parent Task**: TASK-044

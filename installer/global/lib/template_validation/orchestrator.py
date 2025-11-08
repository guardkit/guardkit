"""
Template Validate Orchestrator

Interactive orchestrator for comprehensive template validation.
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .audit_session import AuditSession
from .audit_report_generator import AuditReportGenerator
from .comprehensive_auditor import ComprehensiveAuditor
from .models import ValidateConfig, AuditResult, AuditRecommendation, FixLog


class TemplateValidateOrchestrator:
    """
    Interactive orchestrator for comprehensive template validation.

    Guides user through 16-section audit framework with:
    - Section navigation
    - Progress tracking
    - Inline fixes
    - Session save/resume
    - Report generation
    """

    def __init__(self, config: ValidateConfig):
        self.config = config
        self.session: Optional[AuditSession] = None
        self.auditor = ComprehensiveAuditor()
        self.report_generator = AuditReportGenerator()

    def run(self) -> AuditResult:
        """Execute interactive validation"""
        print("\n" + "=" * 60)
        print("  Template Comprehensive Audit")
        print("=" * 60)
        print(f"\nTemplate: {self.config.template_path.name}")
        print(f"Location: {self.config.template_path}")

        # Load or create session
        if self.config.resume_session_id:
            self.session = self._load_session(self.config.resume_session_id)
            print(f"\nResuming session: {self.session.session_id}")
            print(f"Progress: {len(self.session.sections_completed)}/16 sections completed")
        else:
            self.session = self._create_session()
            print(f"\nNew audit session: {self.session.session_id}")

        # Determine which sections to run
        sections = self._select_sections()

        if not sections:
            print("\nNo sections selected. Exiting.")
            return self._create_result()

        print(f"\nRunning {len(sections)} section(s)...")

        # Execute each section
        for section_num in sections:
            if not self._execute_section(section_num):
                # User cancelled
                break

            # Save progress after each section
            self._save_session()

        # Generate report
        print("\n" + "-" * 60)
        print("Generating audit report...")
        report_path = self._generate_report()
        print(f"Report saved: {report_path}")

        # Return result
        return self._create_result()

    def _create_session(self) -> AuditSession:
        """Create a new audit session"""
        return AuditSession.create(self.config.template_path)

    def _load_session(self, session_id: str) -> AuditSession:
        """Load existing session"""
        output_dir = self.config.output_dir or self.config.template_path
        session_file = output_dir / f"audit-session-{session_id}.json"

        if not session_file.exists():
            print(f"Session file not found: {session_file}")
            print("Creating new session instead...")
            return self._create_session()

        try:
            return AuditSession.load(session_file)
        except Exception as e:
            print(f"Error loading session: {e}")
            print("Creating new session instead...")
            return self._create_session()

    def _select_sections(self) -> List[int]:
        """Interactive section selection"""
        if self.config.sections:
            # Command-line specified
            return self._parse_section_spec(self.config.sections)

        if not self.config.interactive:
            # Non-interactive mode: run all sections
            return list(range(1, 17))

        # Interactive menu
        print("\n" + "-" * 60)
        print("Audit Sections:")
        print("  [1-7]   Technical Validation")
        print("  [8-13]  Quality Assessment")
        print("  [14-16] Decision Framework")
        print("\nOptions:")
        print("  all     - Run all 16 sections")
        print("  tech    - Run technical validation (1-7)")
        print("  quality - Run quality assessment (8-13)")
        print("  decision - Run decision framework (14-16)")
        print("  custom  - Enter custom section numbers")

        choice = input("\nYour choice [all/tech/quality/decision/custom]: ").strip().lower()

        if choice == "all" or not choice:
            return list(range(1, 17))
        elif choice == "tech":
            return list(range(1, 8))
        elif choice == "quality":
            return list(range(8, 14))
        elif choice == "decision":
            return list(range(14, 17))
        elif choice == "custom":
            spec = input("Enter sections (e.g., 1,4,7 or 1-7): ").strip()
            return self._parse_section_spec([spec])
        else:
            print(f"Invalid choice: {choice}")
            return []

    def _parse_section_spec(self, sections: List[str]) -> List[int]:
        """Parse section specification (e.g., '1,4,7' or '1-7')"""
        result = []
        for spec in sections:
            spec = spec.strip()
            if '-' in spec:
                # Range: 1-7
                parts = spec.split('-')
                if len(parts) == 2:
                    try:
                        start = int(parts[0])
                        end = int(parts[1])
                        result.extend(range(start, end + 1))
                    except ValueError:
                        print(f"Invalid range: {spec}")
            elif ',' in spec:
                # Multiple: 1,4,7
                for num_str in spec.split(','):
                    try:
                        result.append(int(num_str.strip()))
                    except ValueError:
                        print(f"Invalid section number: {num_str}")
            else:
                # Single: 7
                try:
                    result.append(int(spec))
                except ValueError:
                    print(f"Invalid section number: {spec}")

        # Filter to valid range and remove duplicates
        result = sorted(set(num for num in result if 1 <= num <= 16))
        return result

    def _execute_section(self, section_num: int) -> bool:
        """Execute a single audit section. Returns True if should continue."""
        print("\n" + "=" * 60)
        section = self.auditor.get_section(section_num)
        print(f"Section {section_num}: {section.title}")
        print("=" * 60)
        print(f"{section.description}\n")

        # Execute section
        try:
            result = section.execute(
                template_path=self.config.template_path,
                interactive=self.config.interactive
            )
        except Exception as e:
            print(f"Error executing section: {e}")
            import traceback
            traceback.print_exc()
            return True  # Continue with next section

        # Store result
        self.session.add_result(section_num, result)

        # Display summary
        score_str = f"{result.score:.1f}/10" if result.score is not None else "N/A"
        print(f"\nSection Score: {score_str}")
        if result.issues:
            print(f"Issues Found: {len(result.issues)}")
        if result.findings:
            print(f"Findings: {len(result.findings)}")

        # Offer inline fixes if applicable
        if self.config.auto_fix and result.has_issues():
            self._offer_fixes(result)

        # Continue prompt (in interactive mode)
        if self.config.interactive:
            print("\nOptions:")
            print("  [Enter] - Continue to next section")
            print("  [q]     - Quit audit")
            choice = input("\nYour choice: ").strip().lower()
            if choice == 'q':
                print("\nAudit paused. Resume with: --resume " + self.session.session_id)
                return False

        return True

    def _offer_fixes(self, result):
        """Offer inline fixes for detected issues"""
        fixable_issues = result.fixable_issues()
        if not fixable_issues:
            return

        print(f"\n{len(fixable_issues)} fixable issue(s) found.")
        for issue in fixable_issues:
            if not self.config.interactive:
                # Auto-fix in non-interactive mode
                self._apply_fix(issue, result.section_num)
            else:
                # Prompt user in interactive mode
                print(f"\nIssue: {issue.message}")
                print(f"Fix: {issue.fix_description}")
                choice = input("Apply fix? [y/N]: ").strip().lower()
                if choice == 'y':
                    self._apply_fix(issue, result.section_num)

    def _apply_fix(self, issue, section_num: int):
        """Apply a fix and log it"""
        print(f"Applying fix...")
        try:
            if issue.auto_fix:
                issue.auto_fix()
                fix_log = FixLog(
                    timestamp=datetime.now(),
                    section_num=section_num,
                    issue_description=issue.message,
                    fix_description=issue.fix_description,
                    success=True,
                )
                print("✅ Fix applied successfully")
            else:
                fix_log = FixLog(
                    timestamp=datetime.now(),
                    section_num=section_num,
                    issue_description=issue.message,
                    fix_description=issue.fix_description,
                    success=False,
                    error_message="No auto-fix implementation available",
                )
                print("⚠️ Manual fix required")

            self.session.log_fix(fix_log)
        except Exception as e:
            fix_log = FixLog(
                timestamp=datetime.now(),
                section_num=section_num,
                issue_description=issue.message,
                fix_description=issue.fix_description,
                success=False,
                error_message=str(e),
            )
            self.session.log_fix(fix_log)
            print(f"❌ Fix failed: {e}")

    def _save_session(self):
        """Save session state"""
        output_dir = self.config.output_dir or self.config.template_path
        session_file = self.session.get_session_file_path(output_dir)
        self.session.save(session_file)

    def _generate_report(self) -> Path:
        """Generate comprehensive audit report"""
        output_dir = self.config.output_dir or self.config.template_path
        template_name = self.config.template_path.name

        return self.report_generator.generate_report(
            session=self.session,
            template_name=template_name,
            output_path=output_dir
        )

    def _create_result(self) -> AuditResult:
        """Create audit result from session"""
        # Calculate overall score
        scores = [
            r.score for r in self.session.section_results.values()
            if r.score is not None
        ]
        overall_score = sum(scores) / len(scores) if scores else 0.0

        # Calculate grade
        grade = self.report_generator._calculate_grade(overall_score)

        # Determine recommendation
        if overall_score >= 8.0:
            recommendation = AuditRecommendation.APPROVE
        elif overall_score >= 6.0:
            recommendation = AuditRecommendation.NEEDS_IMPROVEMENT
        else:
            recommendation = AuditRecommendation.REJECT

        # Collect critical issues
        critical_issues = []
        for result in self.session.section_results.values():
            critical_issues.extend([
                issue for issue in result.issues
                if issue.severity.value == "critical"
            ])

        # Calculate duration
        duration = (self.session.updated_at - self.session.created_at).total_seconds()

        return AuditResult(
            template_name=self.config.template_path.name,
            template_path=self.config.template_path,
            overall_score=overall_score,
            grade=grade,
            recommendation=recommendation,
            section_results=list(self.session.section_results.values()),
            critical_issues=critical_issues,
            audit_duration_seconds=duration,
        )

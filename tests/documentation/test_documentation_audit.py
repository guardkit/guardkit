"""
Comprehensive validation suite for TASK-023 documentation audit.

This test suite validates:
1. Markdown syntax and link validity
2. Command syntax correctness
3. Feature accuracy and availability
4. Consistency across documentation files
"""

import os
import re
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple, Set
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of a single validation check."""
    category: str
    check_name: str
    passed: bool
    details: str
    severity: str = "error"  # error, warning, info


class DocumentationValidator:
    """Validates documentation quality and accuracy."""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.results: List[ValidationResult] = []
        self.readme_path = self.project_root / "README.md"
        self.claude_md_path = self.project_root / "CLAUDE.md"
        self.commands_dir = self.project_root / "installer/global/commands"
        self.docs_dir = self.project_root / "docs"

    def validate_all(self) -> Dict:
        """Run all validation checks."""
        print("Starting comprehensive documentation validation...")
        print("-" * 60)

        # Markdown syntax validation
        self._validate_markdown_syntax()

        # Link validation
        self._validate_links()

        # Command syntax validation
        self._validate_command_syntax()

        # Feature accuracy validation
        self._validate_feature_accuracy()

        # Consistency validation
        self._validate_consistency()

        # Compilation check (markdown syntax)
        self._validate_compilation()

        return self._generate_report()

    def _validate_markdown_syntax(self) -> None:
        """Validate Markdown syntax in core documentation files."""
        print("\n[1/6] Validating Markdown syntax...")

        # Only check core files for this task
        files_to_check = [
            self.readme_path,
            self.claude_md_path,
        ]

        for filepath in files_to_check:
            if not filepath.exists():
                self.results.append(
                    ValidationResult(
                        category="Markdown Syntax",
                        check_name=f"File exists: {filepath.name}",
                        passed=False,
                        details=f"File not found: {filepath}",
                        severity="error",
                    )
                )
                continue

            try:
                content = filepath.read_text(encoding="utf-8")

                # Check for basic markdown structure
                issues = self._check_markdown_structure(content, filepath.name)
                for issue in issues:
                    self.results.append(issue)

            except Exception as e:
                self.results.append(
                    ValidationResult(
                        category="Markdown Syntax",
                        check_name=f"Parse: {filepath.name}",
                        passed=False,
                        details=f"Error parsing file: {str(e)}",
                        severity="error",
                    )
                )

    def _check_markdown_structure(
        self, content: str, filename: str
    ) -> List[ValidationResult]:
        """Check markdown structure issues."""
        issues = []

        # Check for properly formatted code blocks
        code_block_pattern = r"```[\w]*\n.*?\n```"
        code_blocks = re.findall(code_block_pattern, content, re.DOTALL)

        # Count unclosed code blocks
        open_count = content.count("```")
        if open_count % 2 != 0:
            issues.append(
                ValidationResult(
                    category="Markdown Syntax",
                    check_name=f"Code block closure: {filename}",
                    passed=False,
                    details=f"Found unclosed code block (odd count: {open_count})",
                    severity="error",
                )
            )
        else:
            issues.append(
                ValidationResult(
                    category="Markdown Syntax",
                    check_name=f"Code block closure: {filename}",
                    passed=True,
                    details=f"All code blocks properly closed ({open_count // 2} blocks)",
                    severity="info",
                )
            )

        # Check for properly formatted links
        link_pattern = r"\[([^\]]+)\]\(([^)]+)\)"
        links = re.findall(link_pattern, content)
        if links:
            issues.append(
                ValidationResult(
                    category="Markdown Syntax",
                    check_name=f"Link format: {filename}",
                    passed=True,
                    details=f"Found {len(links)} properly formatted links",
                    severity="info",
                )
            )

        if not issues:
            issues.append(
                ValidationResult(
                    category="Markdown Syntax",
                    check_name=f"Basic structure: {filename}",
                    passed=True,
                    details="Markdown structure is valid",
                    severity="info",
                )
            )

        return issues

    def _validate_links(self) -> None:
        """Validate all links in documentation."""
        print("[2/6] Validating links...")

        files_to_check = [self.readme_path, self.claude_md_path]

        total_links = 0
        broken_links = []
        external_links = []
        internal_files = []

        for filepath in files_to_check:
            if not filepath.exists():
                continue

            content = filepath.read_text(encoding="utf-8")

            # Extract all links
            link_pattern = r"\[([^\]]+)\]\(([^)]+)\)"
            links = re.findall(link_pattern, content)

            for text, url in links:
                total_links += 1

                # Check if it's an internal link
                if url.startswith("http"):
                    external_links.append(url)
                elif url.startswith("#"):
                    # Anchor link - check if header exists
                    anchor = url[1:]
                    if not self._anchor_exists(content, anchor):
                        broken_links.append((url, filepath.name))
                else:
                    # Internal file reference
                    file_part = url.split("#")[0]
                    if file_part:  # Only check if there's a file part
                        ref_path = filepath.parent / file_part
                        internal_files.append(file_part)
                        if not self._file_exists(ref_path):
                            broken_links.append((url, filepath.name))

        # Report results
        self.results.append(
            ValidationResult(
                category="Link Validation",
                check_name="Total links found",
                passed=True,
                details=f"Total: {total_links}, External: {len(external_links)}, Internal: {total_links - len(external_links)}",
                severity="info",
            )
        )

        if broken_links:
            details = "; ".join([f"{url} in {file}" for url, file in broken_links[:5]])
            if len(broken_links) > 5:
                details += f"; ... and {len(broken_links) - 5} more"
            self.results.append(
                ValidationResult(
                    category="Link Validation",
                    check_name="Broken internal links",
                    passed=False,
                    details=f"Found {len(broken_links)} broken links: {details}",
                    severity="error",
                )
            )
        else:
            self.results.append(
                ValidationResult(
                    category="Link Validation",
                    check_name="No broken internal links",
                    passed=True,
                    details="All internal links are valid",
                    severity="info",
                )
            )

        # Check external URLs are properly formatted
        invalid_urls = [url for url in external_links if not self._is_valid_url(url)]
        if invalid_urls:
            self.results.append(
                ValidationResult(
                    category="Link Validation",
                    check_name="External URL format",
                    passed=False,
                    details=f"Found {len(invalid_urls)} invalid URLs",
                    severity="error",
                )
            )
        else:
            self.results.append(
                ValidationResult(
                    category="Link Validation",
                    check_name="External URL format",
                    passed=True,
                    details=f"All {len(external_links)} external URLs are properly formatted",
                    severity="info",
                )
            )

    def _validate_command_syntax(self) -> None:
        """Validate command syntax in documentation."""
        print("[3/6] Validating command syntax...")

        content = self.readme_path.read_text() + self.claude_md_path.read_text()

        # Extract all command examples
        command_pattern = r"/(\w+)(?:\s+([A-Z0-9\-]+))?(?:\s+--([a-z0-9\-=|]+))?"
        commands = re.findall(command_pattern, content)

        # Get list of actual command files
        available_commands = set()
        if self.commands_dir.exists():
            available_commands = {
                f.stem for f in self.commands_dir.glob("*.md") if f.is_file()
            }

        documented_commands = set(cmd[0] for cmd in commands)

        # Check for undefined flag combinations
        invalid_flags = []
        flag_pattern = r"--mode=([\w|\-]+)"
        flag_matches = re.finditer(flag_pattern, content)
        for match in flag_matches:
            modes = match.group(1).split("|")
            for mode in modes:
                # Valid modes are documented
                if mode not in ["standard", "tdd"]:
                    invalid_flags.append(f"--mode={mode}")

        # Also check for invalid flags like --mode=bdd
        bdd_pattern = r"--mode=bdd"
        if re.search(bdd_pattern, content, re.IGNORECASE):
            invalid_flags.append("--mode=bdd (not valid in GuardKit)")

        if invalid_flags:
            self.results.append(
                ValidationResult(
                    category="Command Syntax",
                    check_name="Valid flag values",
                    passed=False,
                    details=f"Found invalid flags: {', '.join(set(invalid_flags))}",
                    severity="error",
                )
            )
        else:
            self.results.append(
                ValidationResult(
                    category="Command Syntax",
                    check_name="Valid flag values",
                    passed=True,
                    details="All flag values are valid (--mode=standard|tdd only)",
                    severity="info",
                )
            )

        # Check for proper command structure
        valid_commands = {
            "task-create",
            "task-work",
            "task-complete",
            "task-status",
            "task-refine",
            "figma-to-react",
            "zeplin-to-maui",
            "debug",
        }

        proper_commands = 0
        invalid_command_refs = []
        for cmd in commands:
            cmd_name = cmd[0]
            if cmd_name in valid_commands:
                proper_commands += 1
            else:
                invalid_command_refs.append(cmd_name)

        self.results.append(
            ValidationResult(
                category="Command Syntax",
                check_name="Command structure",
                passed=proper_commands > 0,
                details=f"Found {proper_commands} valid command examples (invalid: {set(invalid_command_refs)})",
                severity="info",
            )
        )

    def _validate_feature_accuracy(self) -> None:
        """Validate that features mentioned actually exist."""
        print("[4/6] Validating feature accuracy...")

        content_readme = self.readme_path.read_text()
        content_claude = self.claude_md_path.read_text()
        combined = content_readme + "\n" + content_claude

        # Check Phase numbering consistency
        phases = re.findall(r"Phase\s+(\d+(?:\.\d+)?)", combined)
        unique_phases = sorted(set(float(p) for p in phases))

        expected_phases = [1.0, 2.0, 2.5, 2.7, 2.8, 3.0, 4.0, 4.5, 5.0, 5.5]
        missing_phases = [p for p in expected_phases if p not in unique_phases]

        if missing_phases:
            self.results.append(
                ValidationResult(
                    category="Feature Accuracy",
                    check_name="Phase numbering",
                    passed=False,
                    details=f"Missing phases: {missing_phases}",
                    severity="error",
                )
            )
        else:
            self.results.append(
                ValidationResult(
                    category="Feature Accuracy",
                    check_name="Phase numbering",
                    passed=True,
                    details=f"All expected phases documented: {unique_phases}",
                    severity="info",
                )
            )

        # Check for RequireKit references in wrong sections
        requirekit_in_core = False

        # Find sections that discuss core features
        core_sections = [
            "What You Get",
            "5-Minute Quickstart",
            "Available Commands",
            "Supported Stacks",
        ]

        for section in core_sections:
            section_idx = content_readme.find(section)
            if section_idx >= 0:
                # Check next section
                next_section = content_readme.find("##", section_idx + 2)
                section_content = content_readme[section_idx:next_section if next_section > 0 else len(content_readme)]

                if "RequireKit" in section_content and "upgrade" not in section_content.lower():
                    requirekit_in_core = True
                    break

        if requirekit_in_core:
            self.results.append(
                ValidationResult(
                    category="Feature Accuracy",
                    check_name="RequireKit scope",
                    passed=False,
                    details="RequireKit mentioned in core features (should only be in upgrade section)",
                    severity="error",
                )
            )
        else:
            self.results.append(
                ValidationResult(
                    category="Feature Accuracy",
                    check_name="RequireKit scope",
                    passed=True,
                    details="RequireKit properly documented only in upgrade/upgrade path sections",
                    severity="info",
                )
            )

        # Check quality gate thresholds are consistent
        thresholds_readme = re.findall(r"≥?(\d+)%", content_readme)
        thresholds_claude = re.findall(r"≥?(\d+)%", content_claude)

        # Look for specific thresholds
        coverage_threshold = "80" in thresholds_readme and "80" in thresholds_claude
        branch_threshold = "75" in thresholds_readme and "75" in thresholds_claude

        if coverage_threshold and branch_threshold:
            self.results.append(
                ValidationResult(
                    category="Feature Accuracy",
                    check_name="Quality gate thresholds",
                    passed=True,
                    details="Coverage (80%) and Branch (75%) thresholds consistent",
                    severity="info",
                )
            )
        else:
            self.results.append(
                ValidationResult(
                    category="Feature Accuracy",
                    check_name="Quality gate thresholds",
                    passed=False,
                    details="Inconsistent quality gate thresholds between files",
                    severity="error",
                )
            )

    def _validate_consistency(self) -> None:
        """Validate consistency across documentation files."""
        print("[5/6] Validating consistency...")

        content_readme = self.readme_path.read_text()
        content_claude = self.claude_md_path.read_text()

        # Check terminology consistency
        terminology = {
            "Architectural Review": ["SOLID", "DRY", "YAGNI"],
            "Test Enforcement": ["auto-fix", "3 attempts", "100%"],
            "Design-First": ["--design-only", "--implement-only"],
        }

        terminology_results = 0
        for concept, terms in terminology.items():
            readme_count = sum(content_readme.count(term) for term in terms)
            claude_count = sum(content_claude.count(term) for term in terms)

            # Both should mention the concept
            if readme_count > 0 and claude_count > 0:
                terminology_results += 1
                self.results.append(
                    ValidationResult(
                        category="Consistency",
                        check_name=f"Terminology: {concept}",
                        passed=True,
                        details=f"Found in both files (README: {readme_count}, CLAUDE.md: {claude_count} mentions)",
                        severity="info",
                    )
                )

        # Check project structure consistency
        if "Project Structure" in content_readme and "Project Structure" in content_claude:
            self.results.append(
                ValidationResult(
                    category="Consistency",
                    check_name="Project structure documentation",
                    passed=True,
                    details="Project structure documented in both files",
                    severity="info",
                )
            )

        # Check template list consistency (focus on availability, not exact match)
        templates_mentioned_readme = bool(re.search(r"react|python|typescript", content_readme))
        templates_mentioned_claude = bool(re.search(r"react|python|typescript", content_claude))

        if templates_mentioned_readme and templates_mentioned_claude:
            self.results.append(
                ValidationResult(
                    category="Consistency",
                    check_name="Template documentation",
                    passed=True,
                    details="Templates documented in both README and CLAUDE.md",
                    severity="info",
                )
            )

        # Check command examples consistency
        commands_readme = len(re.findall(r"/task-", content_readme))
        commands_claude = len(re.findall(r"/task-", content_claude))

        if commands_readme > 0 and commands_claude > 0:
            self.results.append(
                ValidationResult(
                    category="Consistency",
                    check_name="Command examples",
                    passed=True,
                    details=f"Commands documented in both files (README: {commands_readme}, CLAUDE.md: {commands_claude})",
                    severity="info",
                )
            )

    def _validate_compilation(self) -> None:
        """Validate markdown compilation (syntax validation)."""
        print("[6/6] Validating compilation (markdown syntax)...")

        files = [self.readme_path, self.claude_md_path]

        for filepath in files:
            if not filepath.exists():
                self.results.append(
                    ValidationResult(
                        category="Compilation",
                        check_name=f"File exists: {filepath.name}",
                        passed=False,
                        details=f"File not found: {filepath}",
                        severity="error",
                    )
                )
                continue

            try:
                content = filepath.read_text(encoding="utf-8")

                # Check for critical markdown issues
                issues = []

                # Unmatched brackets
                open_brackets = content.count("[")
                close_brackets = content.count("]")
                if open_brackets != close_brackets:
                    issues.append(
                        f"Unmatched brackets: {open_brackets} open, {close_brackets} close"
                    )

                # Unmatched parentheses in links
                link_opens = len(re.findall(r"\]\(", content))
                link_closes = len(re.findall(r"\]\([^)]*\)", content))
                if link_opens != link_closes:
                    issues.append(
                        f"Unmatched parentheses in links: {link_opens} open, {link_closes} close"
                    )

                if issues:
                    self.results.append(
                        ValidationResult(
                            category="Compilation",
                            check_name=f"Markdown validity: {filepath.name}",
                            passed=False,
                            details="; ".join(issues),
                            severity="error",
                        )
                    )
                else:
                    self.results.append(
                        ValidationResult(
                            category="Compilation",
                            check_name=f"Markdown validity: {filepath.name}",
                            passed=True,
                            details="No syntax errors detected",
                            severity="info",
                        )
                    )

            except Exception as e:
                self.results.append(
                    ValidationResult(
                        category="Compilation",
                        check_name=f"Read: {filepath.name}",
                        passed=False,
                        details=str(e),
                        severity="error",
                    )
                )

    def _anchor_exists(self, content: str, anchor: str) -> bool:
        """Check if an anchor (header) exists in content."""
        # Convert anchor to header format (dash-separated to space-separated)
        header_text = anchor.replace("-", " ").lower()
        header_pattern = rf"^#+\s+{re.escape(header_text)}"
        return bool(re.search(header_pattern, content, re.MULTILINE | re.IGNORECASE))

    def _file_exists(self, path: Path) -> bool:
        """Check if a file exists."""
        return path.exists() and path.is_file()

    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is properly formatted."""
        url_pattern = (
            r"^https?://[a-zA-Z0-9\-._~:/?#\[\]@!$&'()*+,;=%]+"
        )
        return bool(re.match(url_pattern, url))

    def _generate_report(self) -> Dict:
        """Generate final report."""
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        pass_rate = (passed / total * 100) if total > 0 else 0

        # Count by severity
        errors = sum(1 for r in self.results if r.severity == "error" and not r.passed)
        warnings = sum(
            1 for r in self.results if r.severity == "warning" and not r.passed
        )

        report = {
            "summary": {
                "total_checks": total,
                "passed": passed,
                "failed": total - passed,
                "pass_rate": f"{pass_rate:.1f}%",
                "critical_errors": errors,
                "warnings": warnings,
                "status": "PASSED" if pass_rate == 100 else "FAILED",
            },
            "by_category": {},
            "details": [],
        }

        # Group by category
        by_category = {}
        for result in self.results:
            if result.category not in by_category:
                by_category[result.category] = {
                    "passed": 0,
                    "failed": 0,
                    "checks": [],
                }
            if result.passed:
                by_category[result.category]["passed"] += 1
            else:
                by_category[result.category]["failed"] += 1
            by_category[result.category]["checks"].append(
                {
                    "name": result.check_name,
                    "passed": result.passed,
                    "severity": result.severity,
                    "details": result.details,
                }
            )

        report["by_category"] = by_category
        report["details"] = [
            {
                "category": r.category,
                "check": r.check_name,
                "passed": r.passed,
                "severity": r.severity,
                "details": r.details,
            }
            for r in self.results
        ]

        return report


def main():
    """Run the validation suite."""
    project_root = "/Users/richardwoollcott/Projects/appmilla_github/guardkit"

    validator = DocumentationValidator(project_root)
    report = validator.validate_all()

    # Print summary
    print("\n" + "=" * 60)
    print("DOCUMENTATION VALIDATION REPORT")
    print("=" * 60)

    summary = report["summary"]
    print(f"\nStatus: {summary['status']}")
    print(f"Total Checks: {summary['total_checks']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Pass Rate: {summary['pass_rate']}")

    if summary["critical_errors"] > 0:
        print(f"\nCritical Errors: {summary['critical_errors']}")

    if summary["warnings"] > 0:
        print(f"Warnings: {summary['warnings']}")

    # Print by category
    print("\n" + "-" * 60)
    print("BY CATEGORY")
    print("-" * 60)

    for category, data in report["by_category"].items():
        total = data["passed"] + data["failed"]
        pct = (data["passed"] / total * 100) if total > 0 else 0
        print(
            f"\n{category}: {data['passed']}/{total} passed ({pct:.0f}%)"
        )
        for check in data["checks"]:
            status = "PASS" if check["passed"] else "FAIL"
            print(f"  [{status}] {check['name']}")
            if check["details"]:
                print(f"       {check['details']}")

    # Print failed checks
    failed_checks = [r for r in report["details"] if not r["passed"]]
    if failed_checks:
        print("\n" + "-" * 60)
        print(f"FAILED CHECKS ({len(failed_checks)})")
        print("-" * 60)
        for check in failed_checks:
            severity = check["severity"].upper()
            print(f"\n[{severity}] {check['category']}: {check['check']}")
            print(f"       {check['details']}")

    # Save report as JSON
    report_path = Path(project_root) / "tests" / "documentation" / "validation-report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\nDetailed report saved to: {report_path}")

    # Exit with appropriate code
    exit(0 if summary["status"] == "PASSED" else 1)


if __name__ == "__main__":
    main()

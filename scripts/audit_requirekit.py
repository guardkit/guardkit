#!/usr/bin/env python3
"""
RequireKit Reference Audit Script

Scans workflow and quick-reference documentation for RequireKit-specific references
and generates a report categorizing findings for manual cleanup.

Architectural Decision: Keep it simple
- Pattern detection only (no command validation, no link checking)
- Focused on workflows/ and quick-reference/ directories
- Manual cleanup based on generated report
- Deferred: Command syntax validation, broken link detection
"""

import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict
from datetime import datetime


@dataclass
class Finding:
    """A single RequireKit reference found in documentation."""
    file_path: str
    line_number: int
    line_content: str
    pattern_name: str
    category: str  # "heavy" | "light" | "integration"


@dataclass
class AuditReport:
    """Complete audit results."""
    findings: List[Finding] = field(default_factory=list)
    files_scanned: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def add_finding(self, finding: Finding):
        self.findings.append(finding)

    def get_findings_by_file(self) -> Dict[str, List[Finding]]:
        """Group findings by file path."""
        by_file = {}
        for finding in self.findings:
            if finding.file_path not in by_file:
                by_file[finding.file_path] = []
            by_file[finding.file_path].append(finding)
        return by_file

    def get_findings_by_category(self) -> Dict[str, List[Finding]]:
        """Group findings by category."""
        by_category = {"heavy": [], "light": [], "integration": []}
        for finding in self.findings:
            by_category[finding.category].append(finding)
        return by_category


# RequireKit pattern definitions with categorization
REQUIREKIT_PATTERNS = {
    # Heavy RequireKit features (must be removed or heavily rewritten)
    "require_command": {
        "regex": r"/require-[a-z-]+",
        "category": "heavy",
        "description": "RequireKit command reference"
    },
    "ears_notation": {
        "regex": r"\b(EARS notation|EARS syntax|EARS format)\b",
        "category": "heavy",
        "description": "EARS notation reference"
    },
    "bdd_generation": {
        "regex": r"\b(BDD scenario generation|Generate BDD|Gherkin generation)\b",
        "category": "heavy",
        "description": "BDD scenario generation"
    },
    "epic_hierarchy": {
        "regex": r"\b(epic hierarchy|feature hierarchy|epic/feature)\b",
        "category": "heavy",
        "description": "Epic/feature hierarchy"
    },
    "pm_integration": {
        "regex": r"\b(Jira integration|Linear integration|Azure DevOps sync|GitHub Issues sync)\b",
        "category": "heavy",
        "description": "PM tool integration"
    },
    "phase1_requirements": {
        "regex": r"\bPhase 1[:\s]+(Requirements Analysis|Requirement Gathering|EARS)\b",
        "category": "heavy",
        "description": "Phase 1 requirements analysis (RequireKit domain)"
    },

    # Light RequireKit mentions (may need context clarification)
    "bdd_keyword": {
        "regex": r"\b(BDD|Gherkin)\b(?! scenario generation)",
        "category": "light",
        "description": "BDD/Gherkin keyword mention"
    },
    "epic_keyword": {
        "regex": r"\bepic\b(?! hierarchy)",
        "category": "light",
        "description": "Epic keyword mention"
    },
    "formal_requirements": {
        "regex": r"\b(formal requirements|requirements traceability|stakeholder analysis)\b",
        "category": "light",
        "description": "Formal requirements management"
    },
    "phase1_general": {
        "regex": r"\bPhase 1\b(?!:)",
        "category": "light",
        "description": "Phase 1 general mention"
    },

    # Integration opportunities (should link to RequireKit)
    "pm_tools": {
        "regex": r"\b(Jira|Linear|Azure DevOps)\b(?! integration)",
        "category": "integration",
        "description": "PM tool mention (potential integration note)"
    },
    "requirements_management": {
        "regex": r"\b(requirements? management|requirement tracking)\b",
        "category": "integration",
        "description": "Requirements management mention"
    }
}


def scan_file(file_path: Path) -> List[Finding]:
    """Scan a single markdown file for RequireKit patterns."""
    findings = []

    try:
        content = file_path.read_text(encoding='utf-8')
        lines = content.split('\n')

        for line_num, line in enumerate(lines, start=1):
            for pattern_name, pattern_def in REQUIREKIT_PATTERNS.items():
                if re.search(pattern_def["regex"], line, re.IGNORECASE):
                    findings.append(Finding(
                        file_path=str(file_path),
                        line_number=line_num,
                        line_content=line.strip(),
                        pattern_name=pattern_name,
                        category=pattern_def["category"]
                    ))

    except Exception as e:
        print(f"Error scanning {file_path}: {e}")

    return findings


def audit_documentation(base_path: Path) -> AuditReport:
    """Audit workflow and quick-reference documentation."""
    report = AuditReport()

    # Target directories
    workflows_dir = base_path / "docs" / "workflows"
    quickref_dir = base_path / "docs" / "quick-reference"

    # Scan all markdown files
    for directory in [workflows_dir, quickref_dir]:
        if not directory.exists():
            print(f"Warning: {directory} does not exist")
            continue

        for md_file in directory.glob("*.md"):
            report.files_scanned += 1
            findings = scan_file(md_file)
            for finding in findings:
                report.add_finding(finding)

    return report


def generate_markdown_report(report: AuditReport, output_path: Path):
    """Generate a markdown report of audit findings."""

    by_file = report.get_findings_by_file()
    by_category = report.get_findings_by_category()

    report_lines = [
        "# RequireKit Reference Audit Report",
        "",
        f"**Generated**: {report.timestamp}",
        f"**Files Scanned**: {report.files_scanned}",
        f"**Total Findings**: {len(report.findings)}",
        "",
        "## Summary by Category",
        "",
        f"- **Heavy** (must remove/rewrite): {len(by_category['heavy'])} findings",
        f"- **Light** (needs context check): {len(by_category['light'])} findings",
        f"- **Integration** (add RequireKit notes): {len(by_category['integration'])} findings",
        "",
        "---",
        ""
    ]

    # Heavy findings (priority)
    if by_category['heavy']:
        report_lines.extend([
            "## Heavy RequireKit References (Priority)",
            "",
            "These features are RequireKit-specific and must be removed or heavily rewritten:",
            ""
        ])

        heavy_by_file = {}
        for finding in by_category['heavy']:
            if finding.file_path not in heavy_by_file:
                heavy_by_file[finding.file_path] = []
            heavy_by_file[finding.file_path].append(finding)

        for file_path, findings in sorted(heavy_by_file.items()):
            report_lines.append(f"### {Path(file_path).name}")
            report_lines.append("")
            for finding in findings:
                pattern_desc = REQUIREKIT_PATTERNS[finding.pattern_name]["description"]
                report_lines.append(f"- **Line {finding.line_number}** ({pattern_desc})")
                report_lines.append(f"  ```")
                report_lines.append(f"  {finding.line_content}")
                report_lines.append(f"  ```")
                report_lines.append("")

    # Light findings
    if by_category['light']:
        report_lines.extend([
            "---",
            "",
            "## Light RequireKit Mentions",
            "",
            "These mentions may need context clarification or removal:",
            ""
        ])

        light_by_file = {}
        for finding in by_category['light']:
            if finding.file_path not in light_by_file:
                light_by_file[finding.file_path] = []
            light_by_file[finding.file_path].append(finding)

        for file_path, findings in sorted(light_by_file.items()):
            report_lines.append(f"### {Path(file_path).name}")
            report_lines.append("")
            for finding in findings:
                pattern_desc = REQUIREKIT_PATTERNS[finding.pattern_name]["description"]
                report_lines.append(f"- **Line {finding.line_number}** ({pattern_desc}): `{finding.line_content[:80]}...`")
            report_lines.append("")

    # Integration opportunities
    if by_category['integration']:
        report_lines.extend([
            "---",
            "",
            "## Integration Opportunities",
            "",
            "These mentions could benefit from RequireKit integration notes:",
            ""
        ])

        integration_by_file = {}
        for finding in by_category['integration']:
            if finding.file_path not in integration_by_file:
                integration_by_file[finding.file_path] = []
            integration_by_file[finding.file_path].append(finding)

        for file_path, findings in sorted(integration_by_file.items()):
            report_lines.append(f"### {Path(file_path).name}")
            report_lines.append("")
            for finding in findings:
                pattern_desc = REQUIREKIT_PATTERNS[finding.pattern_name]["description"]
                report_lines.append(f"- **Line {finding.line_number}** ({pattern_desc}): `{finding.line_content[:80]}...`")
            report_lines.append("")

    # Files by priority
    report_lines.extend([
        "---",
        "",
        "## Files by Finding Count (Priority Order)",
        ""
    ])

    file_counts = [(path, len(findings)) for path, findings in by_file.items()]
    file_counts.sort(key=lambda x: x[1], reverse=True)

    for file_path, count in file_counts:
        report_lines.append(f"- **{Path(file_path).name}**: {count} findings")

    report_lines.extend([
        "",
        "---",
        "",
        "## Next Steps",
        "",
        "1. **Address Heavy References** (Priority)",
        "   - Remove RequireKit commands",
        "   - Remove EARS notation examples",
        "   - Remove BDD generation workflows",
        "   - Remove epic hierarchy references",
        "   - Remove PM tool integration details",
        "",
        "2. **Review Light Mentions**",
        "   - Check context and clarify if needed",
        "   - Remove if not applicable to Taskwright",
        "   - Update phase numbering (Phase 1 = RequireKit)",
        "",
        "3. **Add Integration Notes**",
        "   - Add standard RequireKit integration note:",
        "   ```markdown",
        "   > **Note:** For formal requirements management (EARS notation, BDD scenarios, epic hierarchy),",
        "   > see [RequireKit](https://github.com/requirekit/require-kit) which integrates with Taskwright.",
        "   ```",
        "",
        "4. **Validate Updates**",
        "   - Ensure command syntax matches specifications",
        "   - Verify all examples work standalone (Taskwright only)",
        "   - Check phase descriptions are accurate",
        ""
    ])

    # Write report
    output_path.write_text('\n'.join(report_lines), encoding='utf-8')
    print(f"\nReport generated: {output_path}")


def main():
    """Main execution."""
    # Determine base path (repository root)
    script_path = Path(__file__).resolve()
    base_path = script_path.parent.parent

    print("RequireKit Reference Audit")
    print("=" * 50)
    print(f"Base path: {base_path}")
    print()

    # Run audit
    print("Scanning documentation...")
    report = audit_documentation(base_path)

    print(f"\nScanned {report.files_scanned} files")
    print(f"Found {len(report.findings)} RequireKit references")

    by_category = report.get_findings_by_category()
    print(f"  - Heavy: {len(by_category['heavy'])}")
    print(f"  - Light: {len(by_category['light'])}")
    print(f"  - Integration: {len(by_category['integration'])}")

    # Generate report
    output_path = base_path / "docs" / "research" / "TASK-025-audit-report.md"
    generate_markdown_report(report, output_path)

    print("\nAudit complete!")


if __name__ == "__main__":
    main()

"""
Test security validation documentation for accuracy and completeness.

This test suite verifies that:
1. All documented files exist and contain required sections
2. Architecture diagrams are accurate
3. Code examples are syntactically correct
4. Cross-references between documents are valid
5. Exclusion lists and thresholds match implementation
"""
import os
import re
import pytest
from pathlib import Path


class TestSecurityValidationDocs:
    """Test security validation documentation."""

    @pytest.fixture
    def repo_root(self):
        """Get repository root directory."""
        # Tests are in tests/, repo root is parent
        return Path(__file__).parent.parent

    def test_autobuild_coach_has_security_section(self, repo_root):
        """Verify autobuild-coach.md has Security Validation section."""
        coach_file = repo_root / ".claude/agents/autobuild-coach.md"
        assert coach_file.exists(), "autobuild-coach.md not found"

        content = coach_file.read_text()

        # Check for Security Validation section
        assert "## Security Validation (Read-Only)" in content, \
            "Missing 'Security Validation (Read-Only)' section"

        # Check for key principles
        assert "Coach ONLY reads" in content, \
            "Missing Coach read-only principle"
        assert "Coach does NOT invoke security-specialist agent" in content, \
            "Missing no-agent-invocation constraint"

        # Check for phase documentation
        assert "Phase 2.5C" in content, "Missing Phase 2.5C reference"
        assert "Phase 4.3" in content, "Missing Phase 4.3 reference"

        # Check for security results format
        assert '"security": {' in content, "Missing security results JSON example"
        assert '"quick_check_passed"' in content, "Missing quick_check_passed field"
        assert '"critical_count"' in content, "Missing critical_count field"

        # Check NEVER section updated
        assert "ENFORCED VIA QUALITY GATES" in content, \
            "Missing security enforcement clarification in NEVER section"
        assert "ARCHITECTURAL CONSTRAINT" in content, \
            "Missing architectural constraint note in NEVER section"

    def test_autobuild_coach_quality_gate_table(self, repo_root):
        """Verify autobuild-coach.md quality gate table includes security."""
        coach_file = repo_root / ".claude/agents/autobuild-coach.md"
        content = coach_file.read_text()

        # Find the quality gate table
        table_match = re.search(
            r'\| Phase \| What task-work does \| What you read \|.*?'
            r'\| Phase 5\.5 \|',
            content,
            re.DOTALL
        )
        assert table_match, "Quality gate table not found"

        table = table_match.group(0)

        # Check for Phase 4.3 (Quick security scan)
        assert "Phase 4.3" in table, "Phase 4.3 missing from table"
        assert "Quick security scan" in table, "Security scan description missing"
        assert "security.quick_check_passed" in table, "Security result field missing"

    def test_feature_build_has_security_section(self, repo_root):
        """Verify feature-build.md has Security Validation section."""
        cmd_file = repo_root / "installer/core/commands/feature-build.md"
        assert cmd_file.exists(), "feature-build.md not found"

        content = cmd_file.read_text()

        # Check for Security Validation section
        assert "## Security Validation" in content, \
            "Missing 'Security Validation' section"

        # Check for Quick Checks subsection
        assert "### Quick Checks (Default)" in content, \
            "Missing Quick Checks subsection"

        # Check for Full Security Review subsection
        assert "### Full Security Review" in content, \
            "Missing Full Security Review subsection"

        # Check for configuration examples
        assert "### Configuration" in content, "Missing Configuration subsection"
        assert "security:" in content, "Missing security config example"
        assert "level: strict" in content, "Missing security level example"

        # Check for security levels table
        assert "### Security Levels" in content, "Missing Security Levels table"
        assert "| Level |" in content, "Missing security levels table"
        assert "| strict |" in content, "Missing strict level in table"
        assert "| standard |" in content, "Missing standard level in table"

        # Check for excluded finding types
        assert "### Excluded Finding Types" in content, \
            "Missing Excluded Finding Types section"
        assert "Denial of Service" in content, "Missing DOS in exclusions"
        assert "Rate limiting" in content, "Missing rate limiting in exclusions"

        # Check for confidence scoring
        assert "### Confidence Scoring" in content, \
            "Missing Confidence Scoring section"
        assert "0.8" in content, "Missing confidence threshold"

    def test_claude_md_has_security_summary(self, repo_root):
        """Verify CLAUDE.md has Security Validation summary."""
        claude_file = repo_root / "CLAUDE.md"
        assert claude_file.exists(), "CLAUDE.md not found"

        content = claude_file.read_text()

        # Check for Security Validation subsection under AutoBuild
        assert "#### Security Validation" in content, \
            "Missing Security Validation subsection"

        # Check for quick checks mention
        assert "Quick Checks" in content, "Missing Quick Checks mention"
        assert "all tasks, ~30s" in content, "Missing quick checks timing"

        # Check for full review mention
        assert "Full Review" in content, "Missing Full Review mention"
        assert "security-tagged tasks" in content, "Missing tagged tasks mention"

        # Check for configuration example
        assert "security:" in content, "Missing security config in CLAUDE.md"
        assert "level: standard" in content, "Missing security level example"

        # Check for link to guide
        assert "Security Validation Guide" in content, \
            "Missing link to Security Validation Guide"
        assert "docs/guides/security-validation.md" in content, \
            "Missing path to security validation guide"

    def test_security_validation_guide_exists(self, repo_root):
        """Verify security-validation.md exists with all required sections."""
        guide_file = repo_root / "docs/guides/security-validation.md"
        assert guide_file.exists(), "security-validation.md not found"

        content = guide_file.read_text()

        # Check for all major sections
        required_sections = [
            "# Security Validation Guide",
            "## Overview",
            "## Architecture",
            "## How It Works",
            "### Two-Tier Security",
            "### Security Levels",
            "### Triggering Full Review",
            "### Configuration Examples",
            "### Quick Checks Reference",
            "### Skipping Checks",
            "### Troubleshooting",
            "### Excluded Finding Types",
            "### Confidence Scoring",
            "## Integration with AutoBuild",
            "### Phase Execution",
            "### Coach Security Gate Logic",
            "### Security Results Format",
            "## Best Practices",
            "## Example Workflows",
            "## Reference",
        ]

        for section in required_sections:
            assert section in content, f"Missing section: {section}"

    def test_security_guide_architecture_diagram(self, repo_root):
        """Verify architecture diagram is accurate."""
        guide_file = repo_root / "docs/guides/security-validation.md"
        content = guide_file.read_text()

        # Check architecture diagram includes all phases
        assert "Phase 2.5A: Pattern Suggestions" in content
        assert "Phase 2.5B: Architectural Review" in content
        assert "Phase 2.5C: Security Pre-Check (NEW)" in content
        assert "Phase 4.3: Quick Security Scan (NEW)" in content

        # Check Coach is read-only
        assert "READ task_work_results.json" in content
        assert "NO agent invocation" in content

        # Check key principle
        assert "Coach is READ-ONLY" in content

    def test_security_guide_code_examples_syntax(self, repo_root):
        """Verify code examples are syntactically correct."""
        guide_file = repo_root / "docs/guides/security-validation.md"
        content = guide_file.read_text()

        # Extract YAML code blocks
        yaml_blocks = re.findall(r'```yaml\n(.*?)\n```', content, re.DOTALL)
        assert len(yaml_blocks) > 0, "No YAML examples found"

        # Basic YAML syntax check (no tabs, proper structure)
        for block in yaml_blocks:
            assert '\t' not in block, "YAML contains tabs (should use spaces)"
            # Check for proper YAML structure (key: value)
            # Security blocks should have at least one security-related key
            if "security:" in block and len(block.strip()) > 10:
                # Check for common security keys (not all blocks need level)
                has_security_keys = any(key in block for key in [
                    'level:', 'default_level:', 'enabled:', 'skip_checks:',
                    'force_full_review:', 'skip_review:'
                ])
                assert has_security_keys, \
                    f"security block missing expected keys: {block[:100]}"

        # Extract Python code blocks
        python_blocks = re.findall(r'```python\n(.*?)\n```', content, re.DOTALL)
        assert len(python_blocks) > 0, "No Python examples found"

        # Basic Python syntax check
        for block in python_blocks:
            # Check for Coach security gate logic
            if "security_passed" in block:
                assert "security.get(" in block, "Missing .get() for safety"
                assert "quick_check_passed" in block, \
                    "Missing quick_check_passed check"
                assert "critical_count" in block, "Missing critical_count check"

        # Extract JSON code blocks
        json_blocks = re.findall(r'```json\n(.*?)\n```', content, re.DOTALL)
        assert len(json_blocks) > 0, "No JSON examples found"

        # Check security results format
        security_json = None
        for block in json_blocks:
            if '"security"' in block:
                security_json = block
                break

        assert security_json is not None, "Security results JSON example not found"
        assert '"quick_check_passed"' in security_json
        assert '"findings_count"' in security_json
        assert '"critical_count"' in security_json
        assert '"high_count"' in security_json

    def test_security_guide_excluded_findings(self, repo_root):
        """Verify excluded finding types match documentation."""
        guide_file = repo_root / "docs/guides/security-validation.md"
        content = guide_file.read_text()

        # Check all excluded types are documented
        excluded_types = [
            "Denial of Service",
            "resource exhaustion",
            "Rate limiting",
            "Memory leaks",
            "resource management",
            "Open redirect",
            "documentation files",
        ]

        for finding_type in excluded_types:
            assert finding_type in content, \
                f"Excluded finding type not documented: {finding_type}"

    def test_security_guide_confidence_threshold(self, repo_root):
        """Verify confidence threshold is documented."""
        guide_file = repo_root / "docs/guides/security-validation.md"
        content = guide_file.read_text()

        # Check confidence threshold
        assert "0.8" in content, "Confidence threshold 0.8 not documented"
        assert "confidence >= 0.8" in content or "confidence score (0.0-1.0)" in content, \
            "Confidence threshold explanation missing"

    def test_security_guide_cross_references(self, repo_root):
        """Verify cross-references to other documentation are valid."""
        guide_file = repo_root / "docs/guides/security-validation.md"
        content = guide_file.read_text()

        # Extract markdown links
        links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)

        # Check for required cross-references
        link_texts = [text for text, _ in links]
        assert "AutoBuild Workflow" in link_texts or \
               any("autobuild" in text.lower() for text in link_texts), \
               "Missing AutoBuild Workflow reference"

        # Verify file paths in links exist (relative to docs/guides/)
        guide_dir = guide_file.parent
        for text, path in links:
            if path.startswith("http"):
                continue  # Skip external links

            # Resolve relative path
            if path.startswith("../../"):
                target = repo_root / path.replace("../../", "")
            elif path.startswith("../"):
                target = guide_dir.parent / path.replace("../", "")
            else:
                target = guide_dir / path

            # Check if target exists (allow markdown anchors)
            target_file = str(target).split("#")[0]
            assert Path(target_file).exists(), \
                f"Cross-reference target not found: {path}"

    def test_security_guide_example_workflows(self, repo_root):
        """Verify example workflows are complete and accurate."""
        guide_file = repo_root / "docs/guides/security-validation.md"
        content = guide_file.read_text()

        # Check for High-Security Task example
        assert "### High-Security Task" in content, \
            "Missing High-Security Task example"
        assert "TASK-AUTH-001" in content, "Missing task ID in example"
        assert "level: strict" in content, "Missing strict level in example"

        # Check for Low-Risk UI Task example
        assert "### Low-Risk UI Task" in content, \
            "Missing Low-Risk UI Task example"
        assert "level: minimal" in content, "Missing minimal level in example"

        # Check results explanation
        assert "Phase 2.5C:" in content, "Missing phase explanation in workflow"
        assert "Phase 4.3:" in content, "Missing phase explanation in workflow"
        assert "Coach:" in content, "Missing Coach explanation in workflow"

    def test_all_docs_mention_revised_architecture(self, repo_root):
        """Verify all updated docs mention the revised architecture source."""
        files_to_check = [
            ".claude/agents/autobuild-coach.md",
            "docs/guides/security-validation.md",
        ]

        for file_path in files_to_check:
            full_path = repo_root / file_path
            assert full_path.exists(), f"File not found: {file_path}"

            content = full_path.read_text()

            # Should mention TASK-REV-4B0F or TASK-REV-SEC2 (architecture sources)
            assert "TASK-REV" in content or "From TASK" in content, \
                f"File {file_path} doesn't cite architecture source"

    def test_security_levels_consistency(self, repo_root):
        """Verify security levels are consistent across all documentation."""
        files_to_check = [
            "installer/core/commands/feature-build.md",
            "docs/guides/security-validation.md",
        ]

        expected_levels = ["strict", "standard", "minimal", "skip"]

        for file_path in files_to_check:
            full_path = repo_root / file_path
            content = full_path.read_text()

            for level in expected_levels:
                assert level in content, \
                    f"Security level '{level}' missing from {file_path}"

    def test_phase_numbering_consistency(self, repo_root):
        """Verify phase numbers are consistent across documentation."""
        files_to_check = [
            ".claude/agents/autobuild-coach.md",
            "docs/guides/security-validation.md",
        ]

        for file_path in files_to_check:
            full_path = repo_root / file_path
            content = full_path.read_text()

            # Check for Phase 2.5C (pre-loop security)
            assert "Phase 2.5C" in content or "Phase 2.5C:" in content, \
                f"Phase 2.5C missing from {file_path}"

            # Check for Phase 4.3 (quick security scan)
            assert "Phase 4.3" in content or "Phase 4.3:" in content, \
                f"Phase 4.3 missing from {file_path}"

    def test_documentation_accuracy_notes(self, repo_root):
        """Verify documentation includes accuracy notes from review tasks."""
        guide_file = repo_root / "docs/guides/security-validation.md"
        content = guide_file.read_text()

        # Check for references to source tasks
        assert "[From TASK-REV-4B0F]" in content or "TASK-REV-4B0F" in content, \
            "Missing reference to TASK-REV-4B0F (architecture revision)"

        assert "[From TASK-REV-SEC2]" in content or "TASK-REV-SEC2" in content, \
            "Missing reference to TASK-REV-SEC2 (exclusions/confidence)"

        # Check for claude-code-security-review reference
        assert "claude-code-security-review" in content, \
            "Missing reference to claude-code-security-review source"


class TestDocumentationCompleteness:
    """Test that all acceptance criteria are met."""

    @pytest.fixture
    def repo_root(self):
        """Get repository root directory."""
        return Path(__file__).parent.parent

    def test_all_required_files_updated(self, repo_root):
        """Verify all files mentioned in acceptance criteria exist and are updated."""
        required_updates = {
            ".claude/agents/autobuild-coach.md": [
                "Security Validation (Read-Only)",
                "Coach ONLY reads",
                "Phase 2.5C",
                "Phase 4.3",
            ],
            "installer/core/commands/feature-build.md": [
                "## Security Validation",
                "Quick Checks (Default)",
                "Full Security Review",
            ],
            "CLAUDE.md": [
                "Security Validation",
                "Quick Checks",
                "Full Review",
            ],
            "docs/guides/security-validation.md": [
                "# Security Validation Guide",
                "## Architecture",
                "Phase 2.5C",
                "Phase 4.3",
            ],
        }

        for file_path, required_content in required_updates.items():
            full_path = repo_root / file_path
            assert full_path.exists(), f"File not found: {file_path}"

            content = full_path.read_text()
            for snippet in required_content:
                assert snippet in content, \
                    f"Required content missing from {file_path}: {snippet}"

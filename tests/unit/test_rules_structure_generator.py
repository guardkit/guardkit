"""
Unit tests for RulesStructureGenerator.

Tests the rules structure generation and validation logic,
including the guidance file size validation (TASK-GA-002).
"""

import pytest
from pathlib import Path
from installer.core.lib.template_generator.rules_structure_generator import (
    RulesStructureGenerator,
    ValidationIssue
)


class TestValidateGuidanceSizes:
    """Tests for validate_guidance_sizes() method (TASK-GA-002)."""

    def test_validate_guidance_sizes_pass(self, tmp_path):
        """Small guidance files should pass validation."""
        # Create temp dir with small guidance file
        rules_dir = tmp_path / ".claude" / "rules"
        guidance_dir = rules_dir / "guidance"
        guidance_dir.mkdir(parents=True)

        guidance_file = guidance_dir / "test.md"
        guidance_file.write_text("Small content\n" * 10)  # ~150 bytes

        # Create a mock generator (we don't need real analysis/agents for this test)
        from installer.core.lib.codebase_analyzer.models import (
            CodebaseAnalysis,
            TechnologyInfo,
            ArchitectureInfo
        )

        from installer.core.lib.codebase_analyzer.models import ConfidenceScore, QualityInfo

        analysis = CodebaseAnalysis(
            codebase_path=str(tmp_path),
            technology=TechnologyInfo(
                primary_language="Python",
                frameworks=[],
                testing_frameworks=[],
                confidence=ConfidenceScore(level="high", percentage=90.0)
            ),
            architecture=ArchitectureInfo(
                architectural_style="Layered",
                patterns=[],
                dependency_flow="Inward",
                confidence=ConfidenceScore(level="high", percentage=90.0)
            ),
            quality=QualityInfo(
                overall_score=80.0,
                solid_compliance=80.0,
                dry_compliance=80.0,
                yagni_compliance=80.0,
                confidence=ConfidenceScore(level="high", percentage=90.0)
            ),
            example_files=[]
        )

        generator = RulesStructureGenerator(
            analysis=analysis,
            agents=[],
            output_path=tmp_path
        )

        # Validate
        issues = generator.validate_guidance_sizes(rules_dir)
        assert len(issues) == 0

    def test_validate_guidance_sizes_warning(self, tmp_path):
        """Large guidance files should trigger warning."""
        # Create temp dir with large guidance file
        rules_dir = tmp_path / ".claude" / "rules"
        guidance_dir = rules_dir / "guidance"
        guidance_dir.mkdir(parents=True)

        guidance_file = guidance_dir / "large.md"
        guidance_file.write_text("x" * 6000)  # 6KB

        # Create a mock generator
        from installer.core.lib.codebase_analyzer.models import (
            CodebaseAnalysis,
            TechnologyInfo,
            ArchitectureInfo
        )

        from installer.core.lib.codebase_analyzer.models import ConfidenceScore, QualityInfo

        analysis = CodebaseAnalysis(
            codebase_path=str(tmp_path),
            technology=TechnologyInfo(
                primary_language="Python",
                frameworks=[],
                testing_frameworks=[],
                confidence=ConfidenceScore(level="high", percentage=90.0)
            ),
            architecture=ArchitectureInfo(
                architectural_style="Layered",
                patterns=[],
                dependency_flow="Inward",
                confidence=ConfidenceScore(level="high", percentage=90.0)
            ),
            quality=QualityInfo(
                overall_score=80.0,
                solid_compliance=80.0,
                dry_compliance=80.0,
                yagni_compliance=80.0,
                confidence=ConfidenceScore(level="high", percentage=90.0)
            ),
            example_files=[]
        )

        generator = RulesStructureGenerator(
            analysis=analysis,
            agents=[],
            output_path=tmp_path
        )

        # Validate
        issues = generator.validate_guidance_sizes(rules_dir)
        assert len(issues) == 1
        assert issues[0].level == "warning"
        assert "exceeds 5KB" in issues[0].message
        assert "6,000 bytes" in issues[0].message
        assert "large.md" in issues[0].message
        assert "Guidance files should be slim summaries" in issues[0].suggestion

    def test_validate_guidance_no_dir(self, tmp_path):
        """Missing guidance directory should not error."""
        rules_dir = tmp_path / ".claude" / "rules"
        rules_dir.mkdir(parents=True)
        # No guidance subdirectory created

        # Create a mock generator
        from installer.core.lib.codebase_analyzer.models import (
            CodebaseAnalysis,
            TechnologyInfo,
            ArchitectureInfo
        )

        from installer.core.lib.codebase_analyzer.models import ConfidenceScore, QualityInfo

        analysis = CodebaseAnalysis(
            codebase_path=str(tmp_path),
            technology=TechnologyInfo(
                primary_language="Python",
                frameworks=[],
                testing_frameworks=[],
                confidence=ConfidenceScore(level="high", percentage=90.0)
            ),
            architecture=ArchitectureInfo(
                architectural_style="Layered",
                patterns=[],
                dependency_flow="Inward",
                confidence=ConfidenceScore(level="high", percentage=90.0)
            ),
            quality=QualityInfo(
                overall_score=80.0,
                solid_compliance=80.0,
                dry_compliance=80.0,
                yagni_compliance=80.0,
                confidence=ConfidenceScore(level="high", percentage=90.0)
            ),
            example_files=[]
        )

        generator = RulesStructureGenerator(
            analysis=analysis,
            agents=[],
            output_path=tmp_path
        )

        # Validate
        issues = generator.validate_guidance_sizes(rules_dir)
        assert len(issues) == 0

    def test_validate_guidance_multiple_files(self, tmp_path):
        """Should validate all guidance files and report multiple issues."""
        # Create temp dir with multiple guidance files
        rules_dir = tmp_path / ".claude" / "rules"
        guidance_dir = rules_dir / "guidance"
        guidance_dir.mkdir(parents=True)

        # Small file (should pass)
        small_file = guidance_dir / "small.md"
        small_file.write_text("Small content\n" * 10)

        # Large file 1 (should warn)
        large_file1 = guidance_dir / "large1.md"
        large_file1.write_text("x" * 6000)

        # Large file 2 (should warn)
        large_file2 = guidance_dir / "large2.md"
        large_file2.write_text("y" * 7000)

        # Create a mock generator
        from installer.core.lib.codebase_analyzer.models import (
            CodebaseAnalysis,
            TechnologyInfo,
            ArchitectureInfo
        )

        from installer.core.lib.codebase_analyzer.models import ConfidenceScore, QualityInfo

        analysis = CodebaseAnalysis(
            codebase_path=str(tmp_path),
            technology=TechnologyInfo(
                primary_language="Python",
                frameworks=[],
                testing_frameworks=[],
                confidence=ConfidenceScore(level="high", percentage=90.0)
            ),
            architecture=ArchitectureInfo(
                architectural_style="Layered",
                patterns=[],
                dependency_flow="Inward",
                confidence=ConfidenceScore(level="high", percentage=90.0)
            ),
            quality=QualityInfo(
                overall_score=80.0,
                solid_compliance=80.0,
                dry_compliance=80.0,
                yagni_compliance=80.0,
                confidence=ConfidenceScore(level="high", percentage=90.0)
            ),
            example_files=[]
        )

        generator = RulesStructureGenerator(
            analysis=analysis,
            agents=[],
            output_path=tmp_path
        )

        # Validate
        issues = generator.validate_guidance_sizes(rules_dir)
        assert len(issues) == 2

        # Check that both large files are reported
        reported_files = [issue.file for issue in issues]
        assert any("large1.md" in f for f in reported_files)
        assert any("large2.md" in f for f in reported_files)

        # Check all are warnings
        assert all(issue.level == "warning" for issue in issues)

    def test_validate_guidance_boundary_size(self, tmp_path):
        """File exactly at 5KB boundary should not trigger warning."""
        rules_dir = tmp_path / ".claude" / "rules"
        guidance_dir = rules_dir / "guidance"
        guidance_dir.mkdir(parents=True)

        # Exactly 5KB (should pass)
        boundary_file = guidance_dir / "boundary.md"
        boundary_file.write_text("x" * 5120)  # Exactly 5KB

        # Create a mock generator
        from installer.core.lib.codebase_analyzer.models import (
            CodebaseAnalysis,
            TechnologyInfo,
            ArchitectureInfo
        )

        from installer.core.lib.codebase_analyzer.models import ConfidenceScore, QualityInfo

        analysis = CodebaseAnalysis(
            codebase_path=str(tmp_path),
            technology=TechnologyInfo(
                primary_language="Python",
                frameworks=[],
                testing_frameworks=[],
                confidence=ConfidenceScore(level="high", percentage=90.0)
            ),
            architecture=ArchitectureInfo(
                architectural_style="Layered",
                patterns=[],
                dependency_flow="Inward",
                confidence=ConfidenceScore(level="high", percentage=90.0)
            ),
            quality=QualityInfo(
                overall_score=80.0,
                solid_compliance=80.0,
                dry_compliance=80.0,
                yagni_compliance=80.0,
                confidence=ConfidenceScore(level="high", percentage=90.0)
            ),
            example_files=[]
        )

        generator = RulesStructureGenerator(
            analysis=analysis,
            agents=[],
            output_path=tmp_path
        )

        # Validate
        issues = generator.validate_guidance_sizes(rules_dir)
        assert len(issues) == 0

        # Just over 5KB (should warn)
        boundary_file.write_text("x" * 5121)
        issues = generator.validate_guidance_sizes(rules_dir)
        assert len(issues) == 1

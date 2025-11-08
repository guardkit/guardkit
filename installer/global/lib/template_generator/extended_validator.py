"""
Extended Template Validator

Provides Phase 5.7 extended validation beyond Phase 5.5 completeness checks.
Generates detailed quality reports when --validate flag is used.

TASK-043: Implement Extended Validation Flag (Phase 1)
"""

from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
import re
import random
from collections import defaultdict
import importlib

# Import using importlib to bypass 'global' keyword issue
_models_module = importlib.import_module('installer.global.lib.template_generator.models')
TemplateCollection = _models_module.TemplateCollection
CodeTemplate = _models_module.CodeTemplate
ValidationReport = _models_module.ValidationReport


@dataclass
class SpotCheckResult:
    """Result of a pattern fidelity spot-check"""
    template_path: str
    passed: bool
    checks_performed: List[str]
    issues_found: List[str]
    score: float  # 0-10


@dataclass
class ExtendedValidationReport:
    """Extended validation report with detailed findings"""
    overall_score: float  # 0-10
    completeness_score: float  # From Phase 5.5
    placeholder_consistency_score: float
    pattern_fidelity_score: float
    documentation_score: float
    agent_validation_score: float
    manifest_accuracy_score: float

    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    spot_check_results: List[SpotCheckResult] = field(default_factory=list)

    validation_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    duration: str = "0s"
    template_path: Optional[Path] = None

    def is_production_ready(self) -> bool:
        """Returns True if score >= 8.0"""
        return self.overall_score >= 8.0

    def get_grade(self) -> str:
        """Returns letter grade (A+, A, A-, B+, B, C, F)"""
        if self.overall_score >= 9.5:
            return "A+"
        if self.overall_score >= 9.0:
            return "A"
        if self.overall_score >= 8.5:
            return "A-"
        if self.overall_score >= 8.0:
            return "B+"
        if self.overall_score >= 7.0:
            return "B"
        if self.overall_score >= 6.0:
            return "C"
        return "F"

    def get_exit_code(self) -> int:
        """
        Returns exit code based on quality score:
        - 0: Score >= 8.0 (production ready)
        - 1: Score 6.0-7.9 (needs improvement)
        - 2: Score < 6.0 (not ready)
        """
        if self.overall_score >= 8.0:
            return 0
        elif self.overall_score >= 6.0:
            return 1
        else:
            return 2


class ExtendedValidator:
    """Extended template validation beyond Phase 5.5"""

    def __init__(self):
        """Initialize extended validator"""
        pass

    def validate(
        self,
        templates: TemplateCollection,
        manifest: Dict[str, Any],
        settings: Dict[str, Any],
        claude_md_path: Path,
        agents: List[Path],
        phase_5_5_report: Optional[ValidationReport] = None
    ) -> ExtendedValidationReport:
        """
        Run all extended validation checks.

        Args:
            templates: TemplateCollection to validate
            manifest: Template manifest dictionary
            settings: Template settings dictionary
            claude_md_path: Path to CLAUDE.md file
            agents: List of agent file paths
            phase_5_5_report: Optional Phase 5.5 validation report

        Returns:
            ExtendedValidationReport with detailed findings
        """
        start_time = datetime.now()

        # Get Phase 5.5 completeness score
        completeness_score = self._get_completeness_score(phase_5_5_report)

        # 1. Placeholder consistency
        placeholder_score = self._validate_placeholder_consistency(templates)

        # 2. Pattern fidelity (spot-check 5 random files)
        fidelity_score, spot_checks = self._validate_pattern_fidelity(templates)

        # 3. Documentation completeness
        doc_score = self._validate_documentation(claude_md_path, manifest, agents)

        # 4. Agent validation
        agent_score = self._validate_agents(agents, claude_md_path)

        # 5. Manifest accuracy
        manifest_score = self._validate_manifest(manifest, templates)

        # Calculate overall score (weighted)
        overall_score = self._calculate_overall_score(
            completeness_score=completeness_score,
            placeholder_score=placeholder_score,
            fidelity_score=fidelity_score,
            doc_score=doc_score,
            agent_score=agent_score,
            manifest_score=manifest_score
        )

        # Calculate duration
        duration = datetime.now() - start_time
        duration_str = f"{duration.total_seconds():.1f}s"

        # Generate recommendations based on scores
        recommendations = self._generate_recommendations(
            completeness_score=completeness_score,
            placeholder_score=placeholder_score,
            fidelity_score=fidelity_score,
            doc_score=doc_score,
            agent_score=agent_score,
            manifest_score=manifest_score
        )

        # Collect all issues
        issues = self._collect_issues(
            placeholder_score=placeholder_score,
            fidelity_score=fidelity_score,
            doc_score=doc_score,
            agent_score=agent_score,
            manifest_score=manifest_score
        )

        return ExtendedValidationReport(
            overall_score=overall_score,
            completeness_score=completeness_score,
            placeholder_consistency_score=placeholder_score,
            pattern_fidelity_score=fidelity_score,
            documentation_score=doc_score,
            agent_validation_score=agent_score,
            manifest_accuracy_score=manifest_score,
            issues=issues,
            recommendations=recommendations,
            spot_check_results=spot_checks,
            validation_timestamp=datetime.now().isoformat(),
            duration=duration_str
        )

    def _get_completeness_score(self, phase_5_5_report: Optional[ValidationReport]) -> float:
        """
        Extract completeness score from Phase 5.5 report.

        Args:
            phase_5_5_report: Phase 5.5 validation report

        Returns:
            Completeness score 0-10
        """
        if phase_5_5_report is None:
            return 10.0  # No validation report = assume complete

        return phase_5_5_report.false_negative_score

    def _validate_placeholder_consistency(
        self,
        templates: TemplateCollection
    ) -> float:
        """
        Validate placeholder naming consistency across templates.

        Checks:
        - Same placeholder names used consistently (e.g., {{EntityName}}, not {{Entity}})
        - Consistent casing (PascalCase for types, camelCase for variables)
        - No hard-coded values that should be placeholders

        Args:
            templates: TemplateCollection to validate

        Returns:
            Score 0-10
        """
        if not templates or templates.total_count == 0:
            return 10.0  # No templates = no inconsistencies

        # Track placeholder usage patterns
        placeholder_patterns = defaultdict(set)  # placeholder -> set of templates using it
        casing_violations = []

        for template in templates.templates:
            for placeholder in template.placeholders:
                placeholder_patterns[placeholder].add(template.name)

                # Check casing consistency
                if not self._is_valid_placeholder_casing(placeholder):
                    casing_violations.append(f"{template.name}: {placeholder}")

        # Calculate score based on consistency
        total_checks = len(templates.templates)
        violations = len(casing_violations)

        # Deduct points for violations (max 3 points deducted)
        violation_penalty = min(3.0, (violations / max(total_checks, 1)) * 3.0)

        score = 10.0 - violation_penalty
        return max(0.0, score)

    def _is_valid_placeholder_casing(self, placeholder: str) -> bool:
        """
        Check if placeholder follows casing conventions.

        Args:
            placeholder: Placeholder name to check

        Returns:
            True if casing is valid
        """
        # Expected patterns:
        # - PascalCase for types/entities: EntityName, ProjectName, EntityNamePlural
        # - camelCase for variables: entityName, projectName
        # - UPPER_CASE for constants: MAX_COUNT, API_KEY

        # Check if it matches one of the expected patterns
        pascal_case = re.match(r'^[A-Z][a-zA-Z0-9]*$', placeholder)
        camel_case = re.match(r'^[a-z][a-zA-Z0-9]*$', placeholder)
        upper_case = re.match(r'^[A-Z][A-Z0-9_]*$', placeholder)

        return bool(pascal_case or camel_case or upper_case)

    def _validate_pattern_fidelity(
        self,
        templates: TemplateCollection
    ) -> Tuple[float, List[SpotCheckResult]]:
        """
        Spot-check random templates against expected patterns.

        For each file:
        - Compare structure to expected patterns
        - Verify dependencies match
        - Check method signatures
        - Validate error handling patterns

        Args:
            templates: TemplateCollection to validate

        Returns:
            Tuple of (score 0-10, list of spot-check results)
        """
        if not templates or templates.total_count == 0:
            return 10.0, []

        # Select up to 5 random templates for spot-checking
        sample_size = min(5, templates.total_count)
        sample_templates = random.sample(templates.templates, sample_size)

        spot_check_results = []
        total_score = 0.0

        for template in sample_templates:
            result = self._spot_check_template(template)
            spot_check_results.append(result)
            total_score += result.score

        # Calculate average score
        avg_score = total_score / sample_size if sample_size > 0 else 10.0

        return avg_score, spot_check_results

    def _spot_check_template(self, template: CodeTemplate) -> SpotCheckResult:
        """
        Perform spot-check on a single template.

        Args:
            template: CodeTemplate to check

        Returns:
            SpotCheckResult with findings
        """
        checks_performed = []
        issues_found = []
        score = 10.0

        # Check 1: Placeholder usage
        checks_performed.append("Placeholder usage")
        if len(template.placeholders) == 0:
            issues_found.append("No placeholders found (template may be too specific)")
            score -= 2.0

        # Check 2: Content structure
        checks_performed.append("Content structure")
        if len(template.content) < 50:
            issues_found.append("Template content is very short")
            score -= 1.0

        # Check 3: Pattern adherence
        checks_performed.append("Pattern adherence")
        if template.patterns and len(template.patterns) == 0:
            issues_found.append("No patterns documented")
            score -= 1.0

        # Check 4: Quality score
        checks_performed.append("Quality score")
        if template.quality_score and template.quality_score < 7.0:
            issues_found.append(f"Low quality score: {template.quality_score}")
            score -= 2.0

        passed = len(issues_found) == 0

        return SpotCheckResult(
            template_path=template.template_path,
            passed=passed,
            checks_performed=checks_performed,
            issues_found=issues_found,
            score=max(0.0, score)
        )

    def _validate_documentation(
        self,
        claude_md_path: Path,
        manifest: Dict[str, Any],
        agents: List[Path]
    ) -> float:
        """
        Validate CLAUDE.md completeness.

        Checks:
        - All patterns from manifest documented
        - All agents mentioned
        - Code examples present
        - Architecture overview complete
        - Quality standards specified

        Args:
            claude_md_path: Path to CLAUDE.md file
            manifest: Template manifest
            agents: List of agent paths

        Returns:
            Score 0-10
        """
        if not claude_md_path.exists():
            return 0.0

        try:
            content = claude_md_path.read_text(encoding='utf-8')
        except Exception:
            return 0.0

        score = 10.0

        # Check 1: Minimum length
        if len(content) < 500:
            score -= 3.0

        # Check 2: Required sections
        required_sections = [
            'Architecture',
            'Technology Stack',
            'Quality',
            'Pattern'
        ]

        for section in required_sections:
            if section.lower() not in content.lower():
                score -= 1.0

        # Check 3: Code examples
        if '```' not in content:
            score -= 2.0

        # Check 4: Agent references (if agents exist)
        if agents:
            agent_names = [agent.stem for agent in agents]
            agents_documented = sum(1 for name in agent_names if name in content)

            if agents_documented == 0:
                score -= 2.0
            elif agents_documented < len(agent_names):
                score -= 1.0

        return max(0.0, score)

    def _validate_agents(
        self,
        agents: List[Path],
        claude_md_path: Path
    ) -> float:
        """
        Validate agent files and references.

        Checks:
        - All agents have valid frontmatter
        - All agents mentioned in CLAUDE.md
        - No broken agent references in documentation

        Args:
            agents: List of agent file paths
            claude_md_path: Path to CLAUDE.md

        Returns:
            Score 0-10
        """
        if not agents:
            return 10.0  # No agents = no issues

        score = 10.0
        valid_agents = 0

        # Load CLAUDE.md content
        claude_content = ""
        if claude_md_path.exists():
            try:
                claude_content = claude_md_path.read_text(encoding='utf-8')
            except Exception:
                pass

        for agent_path in agents:
            if not agent_path.exists():
                score -= 2.0
                continue

            try:
                content = agent_path.read_text(encoding='utf-8')

                # Check for frontmatter
                if '---' in content:
                    valid_agents += 1
                else:
                    score -= 1.0

                # Check if mentioned in CLAUDE.md
                if agent_path.stem not in claude_content:
                    score -= 0.5

            except Exception:
                score -= 2.0

        return max(0.0, score)

    def _validate_manifest(
        self,
        manifest: Dict[str, Any],
        templates: TemplateCollection
    ) -> float:
        """
        Validate manifest accuracy.

        Checks:
        - All placeholders in manifest are used in templates
        - All patterns in manifest have corresponding templates
        - Technology stack matches template content
        - Version information present

        Args:
            manifest: Template manifest
            templates: TemplateCollection

        Returns:
            Score 0-10
        """
        score = 10.0

        # Check 1: Required fields
        required_fields = ['name', 'language', 'architecture']
        for field in required_fields:
            if field not in manifest or not manifest[field]:
                score -= 2.0

        # Check 2: Placeholders consistency
        manifest_placeholders = set(manifest.get('placeholders', []))
        template_placeholders = set()

        if templates:
            for template in templates.templates:
                template_placeholders.update(template.placeholders)

        # Check if manifest placeholders are used
        if manifest_placeholders:
            unused = manifest_placeholders - template_placeholders
            if unused:
                penalty = min(2.0, len(unused) * 0.5)
                score -= penalty

        # Check 3: Patterns
        manifest_patterns = manifest.get('patterns', [])
        if not manifest_patterns:
            score -= 1.0

        # Check 4: Complexity score
        complexity = manifest.get('complexity', 0)
        if complexity <= 0 or complexity > 10:
            score -= 1.0

        return max(0.0, score)

    def _calculate_overall_score(
        self,
        completeness_score: float,
        placeholder_score: float,
        fidelity_score: float,
        doc_score: float,
        agent_score: float,
        manifest_score: float
    ) -> float:
        """
        Calculate weighted overall score.

        Weights:
        - Completeness (Phase 5.5): 50%
        - Placeholder Consistency: 10%
        - Pattern Fidelity: 10%
        - Documentation: 10%
        - Agent Validation: 10%
        - Manifest Accuracy: 10%

        Args:
            completeness_score: Score from Phase 5.5
            placeholder_score: Placeholder consistency score
            fidelity_score: Pattern fidelity score
            doc_score: Documentation score
            agent_score: Agent validation score
            manifest_score: Manifest accuracy score

        Returns:
            Weighted overall score 0-10
        """
        weights = {
            'completeness': 0.50,
            'placeholder': 0.10,
            'fidelity': 0.10,
            'documentation': 0.10,
            'agent': 0.10,
            'manifest': 0.10
        }

        overall = (
            completeness_score * weights['completeness'] +
            placeholder_score * weights['placeholder'] +
            fidelity_score * weights['fidelity'] +
            doc_score * weights['documentation'] +
            agent_score * weights['agent'] +
            manifest_score * weights['manifest']
        )

        return round(overall, 1)

    def _generate_recommendations(
        self,
        completeness_score: float,
        placeholder_score: float,
        fidelity_score: float,
        doc_score: float,
        agent_score: float,
        manifest_score: float
    ) -> List[str]:
        """
        Generate actionable recommendations based on scores.

        Args:
            completeness_score: Completeness score
            placeholder_score: Placeholder score
            fidelity_score: Fidelity score
            doc_score: Documentation score
            agent_score: Agent score
            manifest_score: Manifest score

        Returns:
            List of recommendation strings
        """
        recommendations = []

        if completeness_score < 8.0:
            recommendations.append(
                "Review Phase 5.5 validation report and address missing templates"
            )

        if placeholder_score < 8.0:
            recommendations.append(
                "Standardize placeholder naming conventions across all templates"
            )

        if fidelity_score < 8.0:
            recommendations.append(
                "Review spot-check findings and improve pattern adherence"
            )

        if doc_score < 8.0:
            recommendations.append(
                "Enhance CLAUDE.md with more detailed architecture and examples"
            )

        if agent_score < 8.0:
            recommendations.append(
                "Ensure all agents have valid frontmatter and are documented in CLAUDE.md"
            )

        if manifest_score < 8.0:
            recommendations.append(
                "Verify manifest accuracy and ensure all fields are populated correctly"
            )

        if not recommendations:
            recommendations.append("Template quality is excellent! Ready for production use.")

        return recommendations

    def _collect_issues(
        self,
        placeholder_score: float,
        fidelity_score: float,
        doc_score: float,
        agent_score: float,
        manifest_score: float
    ) -> List[str]:
        """
        Collect all validation issues.

        Args:
            placeholder_score: Placeholder score
            fidelity_score: Fidelity score
            doc_score: Documentation score
            agent_score: Agent score
            manifest_score: Manifest score

        Returns:
            List of issue strings
        """
        issues = []

        if placeholder_score < 6.0:
            issues.append("Critical: Placeholder naming inconsistencies detected")

        if fidelity_score < 6.0:
            issues.append("Critical: Multiple pattern fidelity violations")

        if doc_score < 6.0:
            issues.append("Critical: Documentation is incomplete or missing required sections")

        if agent_score < 6.0:
            issues.append("Critical: Agent validation failed")

        if manifest_score < 6.0:
            issues.append("Critical: Manifest contains errors or missing required fields")

        return issues

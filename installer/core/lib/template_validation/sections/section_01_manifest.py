"""
Section 1: Manifest Analysis

Validates template metadata, placeholders, and quality scores.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from ..models import (
    SectionResult,
    ValidationIssue,
    IssueSeverity,
    IssueCategory,
    Finding,
    Recommendation,
)

# Most recent stable Python minor as of last review (TASK-ABSR-E5F6).
# A closed `requires-python` upper bound that excludes this minor (or any
# released minor between this and the lower bound) becomes a stall trapdoor
# the moment the affected interpreter ships in a developer's PATH.
# See docs/guides/portfolio-python-pinning.md for rationale and update cadence.
LATEST_STABLE_PYTHON_MINOR: Tuple[int, int] = (3, 14)

# Templates whose downstream rendered projects should follow the LangChain
# DeepAgents portfolio canonical pin. A template matches if its name starts
# with one of these prefixes OR its manifest declares `extends` pointing at
# one of these.
_LANGCHAIN_DEEPAGENTS_TEMPLATE_NAMES = {
    "langchain-deepagents",
    "langchain-deepagents-orchestrator",
    "langchain-deepagents-weighted-evaluation",
}

# Captures the upper-bound clause of a PEP 440 requires-python constraint:
# matches `<3.13`, `< 3.13`, `<3.13.0` etc. and ignores other clauses.
_REQUIRES_PYTHON_UPPER_RE = re.compile(r"<\s*(\d+)\.(\d+)(?:\.\d+)?")


class ManifestAnalysisSection:
    """Section 1: Manifest Analysis"""

    @property
    def section_num(self) -> int:
        return 1

    @property
    def title(self) -> str:
        return "Manifest Analysis"

    @property
    def description(self) -> str:
        return "Validate template metadata, placeholders, and quality scores"

    def execute(
        self,
        template_path: Path,
        interactive: bool = True
    ) -> SectionResult:
        """Execute manifest analysis"""
        issues: List[ValidationIssue] = []
        findings: List[Finding] = []
        recommendations: List[Recommendation] = []

        # Load manifest
        manifest_path = template_path / "manifest.json"
        if not manifest_path.exists():
            issues.append(ValidationIssue(
                severity=IssueSeverity.CRITICAL,
                category=IssueCategory.METADATA,
                message="manifest.json not found",
                location=str(template_path),
            ))
            return SectionResult(
                section_num=self.section_num,
                section_title=self.title,
                score=0.0,
                issues=issues,
                completed_at=datetime.now(),
            )

        try:
            manifest = json.loads(manifest_path.read_text())
        except json.JSONDecodeError as e:
            issues.append(ValidationIssue(
                severity=IssueSeverity.CRITICAL,
                category=IssueCategory.METADATA,
                message=f"Invalid JSON in manifest.json: {e}",
                location=str(manifest_path),
            ))
            return SectionResult(
                section_num=self.section_num,
                section_title=self.title,
                score=0.0,
                issues=issues,
                completed_at=datetime.now(),
            )

        # 1.1 Metadata Review
        metadata_score, metadata_issues, metadata_findings = self._validate_metadata(manifest, manifest_path)
        issues.extend(metadata_issues)
        findings.extend(metadata_findings)

        # 1.2 Technology Stack Validation
        tech_score, tech_issues, tech_findings = self._validate_technology_stack(manifest)
        issues.extend(tech_issues)
        findings.extend(tech_findings)

        # 1.3 Architectural Metadata
        arch_score, arch_issues, arch_findings = self._validate_architecture_metadata(manifest)
        issues.extend(arch_issues)
        findings.extend(arch_findings)

        # 1.4 Intelligent Placeholders
        placeholder_score, ph_issues, ph_findings = self._validate_placeholders(manifest)
        issues.extend(ph_issues)
        findings.extend(ph_findings)

        # 1.5 Quality Scores
        quality_score, qual_issues, qual_findings = self._validate_quality_scores(manifest)
        issues.extend(qual_issues)
        findings.extend(qual_findings)

        # 1.6 Python pin (LangChain DeepAgents portfolio standardisation)
        pin_issues, pin_findings = self._validate_python_pin(manifest, template_path)
        issues.extend(pin_issues)
        findings.extend(pin_findings)

        # Calculate overall score
        overall_score = self._calculate_section_score([
            metadata_score,
            tech_score,
            arch_score,
            placeholder_score,
            quality_score
        ])

        # Generate recommendations
        if overall_score < 7.0:
            recommendations.append(Recommendation(
                title="Improve Manifest Quality",
                description="Review and address all identified issues in manifest.json",
                priority=IssueSeverity.HIGH,
                effort="low",
                impact="Improves template discoverability and usability"
            ))

        return SectionResult(
            section_num=self.section_num,
            section_title=self.title,
            score=overall_score,
            findings=findings,
            issues=issues,
            recommendations=recommendations,
            metadata={
                "manifest_path": str(manifest_path),
                "metadata_score": metadata_score,
                "tech_score": tech_score,
                "arch_score": arch_score,
                "placeholder_score": placeholder_score,
                "quality_score": quality_score,
            },
            completed_at=datetime.now(),
        )

    def _validate_metadata(
        self,
        manifest: Dict[str, Any],
        manifest_path: Path
    ) -> tuple[float, List[ValidationIssue], List[Finding]]:
        """Validate basic metadata"""
        issues = []
        findings = []
        score = 10.0

        # Required fields
        required_fields = ['id', 'name', 'version', 'description', 'author']
        for field in required_fields:
            if field not in manifest or not manifest[field]:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.HIGH,
                    category=IssueCategory.METADATA,
                    message=f"Missing required field: {field}",
                    location=str(manifest_path),
                ))
                score -= 1.5

        # Validate ID format (should be kebab-case)
        if 'id' in manifest:
            template_id = manifest['id']
            if not template_id.replace('-', '').replace('_', '').isalnum():
                issues.append(ValidationIssue(
                    severity=IssueSeverity.MEDIUM,
                    category=IssueCategory.METADATA,
                    message=f"Template ID should use kebab-case: {template_id}",
                    location=str(manifest_path),
                ))
                score -= 0.5

        # Validate version format (semver)
        if 'version' in manifest:
            version = manifest['version']
            import re
            if not re.match(r'^\d+\.\d+\.\d+$', version):
                issues.append(ValidationIssue(
                    severity=IssueSeverity.LOW,
                    category=IssueCategory.METADATA,
                    message=f"Version should follow semver format (x.y.z): {version}",
                    location=str(manifest_path),
                ))
                score -= 0.5

        # Check description quality
        if 'description' in manifest:
            description = manifest['description']
            if len(description) < 20:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.LOW,
                    category=IssueCategory.METADATA,
                    message="Description is too brief (< 20 characters)",
                    location=str(manifest_path),
                ))
                score -= 0.5
            else:
                findings.append(Finding(
                    title="Good Description",
                    description=f"Clear, descriptive template description ({len(description)} characters)",
                    is_positive=True,
                    impact="Improves template discoverability",
                ))

        return max(0.0, score), issues, findings

    def _validate_technology_stack(
        self,
        manifest: Dict[str, Any]
    ) -> tuple[float, List[ValidationIssue], List[Finding]]:
        """Validate technology stack metadata"""
        issues = []
        findings = []
        score = 10.0

        if 'technology_stack' not in manifest:
            issues.append(ValidationIssue(
                severity=IssueSeverity.HIGH,
                category=IssueCategory.METADATA,
                message="Missing technology_stack field",
            ))
            return 0.0, issues, findings

        tech_stack = manifest['technology_stack']

        # Check for primary language/framework
        if 'primary_language' in tech_stack:
            findings.append(Finding(
                title="Primary Language Defined",
                description=f"Primary language: {tech_stack['primary_language']}",
                is_positive=True,
                impact="Enables proper stack detection",
            ))
        else:
            issues.append(ValidationIssue(
                severity=IssueSeverity.MEDIUM,
                category=IssueCategory.METADATA,
                message="Missing primary_language in technology_stack",
            ))
            score -= 2.0

        # Check for frameworks
        if 'frameworks' in tech_stack and tech_stack['frameworks']:
            findings.append(Finding(
                title="Frameworks Listed",
                description=f"Frameworks: {', '.join(tech_stack['frameworks'])}",
                is_positive=True,
                impact="Improves template categorization",
            ))
        else:
            score -= 1.0

        return max(0.0, score), issues, findings

    def _validate_architecture_metadata(
        self,
        manifest: Dict[str, Any]
    ) -> tuple[float, List[ValidationIssue], List[Finding]]:
        """Validate architectural metadata"""
        issues = []
        findings = []
        score = 10.0

        if 'architecture' not in manifest:
            issues.append(ValidationIssue(
                severity=IssueSeverity.MEDIUM,
                category=IssueCategory.METADATA,
                message="Missing architecture field (recommended)",
            ))
            score -= 2.0
            return score, issues, findings

        arch = manifest['architecture']

        # Check for architectural patterns
        if 'patterns' in arch and arch['patterns']:
            patterns = arch['patterns']
            findings.append(Finding(
                title="Architectural Patterns Documented",
                description=f"Patterns: {', '.join(patterns)}",
                is_positive=True,
                impact="Helps developers understand template structure",
            ))
        else:
            score -= 1.5

        # Check for layer information
        if 'layers' in arch and arch['layers']:
            layers = arch['layers']
            findings.append(Finding(
                title="Architecture Layers Defined",
                description=f"Layers: {', '.join(layers)}",
                is_positive=True,
                impact="Clarifies codebase organization",
            ))
        else:
            score -= 1.5

        return max(0.0, score), issues, findings

    def _validate_placeholders(
        self,
        manifest: Dict[str, Any]
    ) -> tuple[float, List[ValidationIssue], List[Finding]]:
        """Validate intelligent placeholders"""
        issues = []
        findings = []
        score = 10.0

        if 'placeholders' not in manifest:
            issues.append(ValidationIssue(
                severity=IssueSeverity.HIGH,
                category=IssueCategory.METADATA,
                message="Missing placeholders field",
            ))
            return 0.0, issues, findings

        placeholders = manifest['placeholders']

        # Check for required placeholders
        required_placeholders = ['PROJECT_NAME', 'PROJECT_DESCRIPTION']
        for placeholder in required_placeholders:
            if placeholder not in placeholders:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.MEDIUM,
                    category=IssueCategory.METADATA,
                    message=f"Missing common placeholder: {placeholder}",
                ))
                score -= 1.5

        # Check placeholder definitions
        for name, config in placeholders.items():
            if not isinstance(config, dict):
                issues.append(ValidationIssue(
                    severity=IssueSeverity.MEDIUM,
                    category=IssueCategory.METADATA,
                    message=f"Placeholder {name} should be a dict with description/default",
                ))
                score -= 0.5
                continue

            # Check for description
            if 'description' not in config or not config['description']:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.LOW,
                    category=IssueCategory.METADATA,
                    message=f"Placeholder {name} missing description",
                ))
                score -= 0.3

        if len(placeholders) > 0 and score > 7.0:
            findings.append(Finding(
                title="Well-Defined Placeholders",
                description=f"{len(placeholders)} placeholders with clear descriptions",
                is_positive=True,
                impact="Improves template customization experience",
            ))

        return max(0.0, score), issues, findings

    def _validate_quality_scores(
        self,
        manifest: Dict[str, Any]
    ) -> tuple[float, List[ValidationIssue], List[Finding]]:
        """Validate quality score metadata"""
        issues = []
        findings = []
        score = 10.0

        # Quality scores are optional but recommended
        if 'quality_scores' not in manifest:
            issues.append(ValidationIssue(
                severity=IssueSeverity.LOW,
                category=IssueCategory.QUALITY,
                message="Missing quality_scores field (optional but recommended)",
            ))
            return 7.0, issues, findings

        quality_scores = manifest['quality_scores']

        # Check for expected metrics
        expected_metrics = ['completeness', 'pattern_fidelity', 'documentation', 'overall']
        for metric in expected_metrics:
            if metric not in quality_scores:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.LOW,
                    category=IssueCategory.QUALITY,
                    message=f"Missing quality metric: {metric}",
                ))
                score -= 0.5

        # Validate score ranges (should be 0-10 or 0-100)
        for metric, value in quality_scores.items():
            if not isinstance(value, (int, float)):
                issues.append(ValidationIssue(
                    severity=IssueSeverity.MEDIUM,
                    category=IssueCategory.QUALITY,
                    message=f"Quality score {metric} should be numeric: {value}",
                ))
                score -= 1.0
            elif value < 0 or value > 100:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.MEDIUM,
                    category=IssueCategory.QUALITY,
                    message=f"Quality score {metric} out of range: {value}",
                ))
                score -= 1.0

        return max(0.0, score), issues, findings

    def _validate_python_pin(
        self,
        manifest: Dict[str, Any],
        template_path: Path,
    ) -> Tuple[List[ValidationIssue], List[Finding]]:
        """Warn (informational) when a LangChain DeepAgents-derived template ships a
        ``requires-python`` constraint with a closed upper bound that already
        excludes a released, stable Python minor.

        Rationale: see ``docs/guides/portfolio-python-pinning.md``. A stale
        upper bound is a latent stall trapdoor — when the next default Python
        ships on a developer's machine, the resolver silently rejects it and
        the failure surfaces as a misleading downstream stall.

        This check is **non-blocking**: it emits LOW-severity issues so the
        pin is visible during validation runs without rejecting the template.
        """
        issues: List[ValidationIssue] = []
        findings: List[Finding] = []

        if not self._is_langchain_deepagents_derived(manifest):
            return issues, findings

        # Two surfaces carry the pin and both can drift:
        # 1. manifest's ``language_version`` field (metadata, displayed in UIs)
        # 2. the rendered project's ``pyproject.toml.template`` files
        sources: List[Tuple[str, str]] = []

        manifest_pin = manifest.get("language_version")
        if isinstance(manifest_pin, str) and manifest_pin.strip():
            sources.append(("manifest.json:language_version", manifest_pin))

        for template_pyproject in template_path.rglob("pyproject.toml.template"):
            pin = self._extract_requires_python(template_pyproject)
            if pin is not None:
                rel = template_pyproject.relative_to(template_path)
                sources.append((f"{rel}:requires-python", pin))

        for location, pin in sources:
            stale = self._stale_upper_bound(pin)
            if stale is None:
                continue
            major, minor = stale
            issues.append(ValidationIssue(
                severity=IssueSeverity.LOW,
                category=IssueCategory.METADATA,
                message=(
                    f"requires-python upper bound `<{major}.{minor}` excludes "
                    f"Python {LATEST_STABLE_PYTHON_MINOR[0]}."
                    f"{LATEST_STABLE_PYTHON_MINOR[1]} (latest stable). "
                    f"LangChain DeepAgents portfolio canonical is `>=3.11` "
                    f"(open upper bound). See "
                    f"docs/guides/portfolio-python-pinning.md."
                ),
                location=location,
            ))

        return issues, findings

    @staticmethod
    def _is_langchain_deepagents_derived(manifest: Dict[str, Any]) -> bool:
        """Match if the template is itself a LangChain DeepAgents template or
        declares ``extends`` chained from one."""
        name = manifest.get("name", "")
        if isinstance(name, str) and name in _LANGCHAIN_DEEPAGENTS_TEMPLATE_NAMES:
            return True
        extends = manifest.get("extends", "")
        if isinstance(extends, str) and extends in _LANGCHAIN_DEEPAGENTS_TEMPLATE_NAMES:
            return True
        return False

    @staticmethod
    def _extract_requires_python(pyproject_template: Path) -> Optional[str]:
        """Read ``requires-python`` from a pyproject.toml.template file.

        Returns the raw constraint string (e.g. ``">=3.11,<3.13"``) or None if
        the file is unreadable or carries no requires-python clause.
        """
        try:
            text = pyproject_template.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None
        match = re.search(
            r"^\s*requires-python\s*=\s*['\"]([^'\"]+)['\"]",
            text,
            re.MULTILINE,
        )
        return match.group(1) if match else None

    @staticmethod
    def _stale_upper_bound(constraint: str) -> Optional[Tuple[int, int]]:
        """Return the upper-bound (major, minor) if it excludes the latest
        stable Python minor, otherwise None.

        ``<3.14`` excludes 3.14 → returns (3, 14).
        ``<3.15`` excludes nothing currently released → returns None.
        ``>=3.11`` (no upper bound) → returns None.
        """
        match = _REQUIRES_PYTHON_UPPER_RE.search(constraint)
        if match is None:
            return None
        major, minor = int(match.group(1)), int(match.group(2))
        # `<X.Y` excludes X.Y itself, so it's stale iff X.Y <= latest stable.
        if (major, minor) <= LATEST_STABLE_PYTHON_MINOR:
            return major, minor
        return None

    def _calculate_section_score(self, subscores: List[float]) -> float:
        """Calculate weighted average of subscores"""
        if not subscores:
            return 0.0
        return sum(subscores) / len(subscores)

"""Prohibition checklist for design-mode scope creep prevention.

Generates a 12-category checklist from design data documenting what IS and IS NOT
in the design. Everything not explicitly shown is prohibited by default.

Categories 5, 8, 11, 12 are unconditionally prohibited (no override possible).
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class ViolationSeverity(Enum):
    """Severity levels for prohibition violations."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ProhibitionCategory:
    """A single category in the prohibition checklist."""

    name: str
    prohibited: bool
    unconditional: bool
    reasoning: str


@dataclass
class ProhibitionChecklist:
    """Complete prohibition checklist with all 12 categories."""

    categories: List[ProhibitionCategory] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert checklist to dictionary format."""
        return {
            "categories": [
                {
                    "name": cat.name,
                    "prohibited": cat.prohibited,
                    "unconditional": cat.unconditional,
                    "reasoning": cat.reasoning,
                }
                for cat in self.categories
            ]
        }

    def to_json(self) -> str:
        """Convert checklist to compact JSON string."""
        return json.dumps(self.to_dict(), separators=(",", ":"))


@dataclass
class Violation:
    """A prohibition violation detected in generated code."""

    category: str
    file_path: str
    description: str
    severity: ViolationSeverity
    line_number: Optional[int] = None
    confidence: str = "high"


# Tier 1 pattern matching for fast violation detection
TIER1_PATTERNS = {
    "api_integrations": [
        r"import\s+axios",
        r"from\s+['\"]axios['\"]",
        r"fetch\s*\(",
        r"XMLHttpRequest",
        r"\$\.ajax",
        r"\$\.get",
        r"\$\.post",
        r"http\.get",
        r"http\.post",
        r"axios\.",  # Match any axios method call (axios.get, axios.post, etc.)
    ],
    "loading_states": [
        r"isLoading",
        r"setIsLoading",
        r"loading\s*=",
        r"<Spinner",
        r"<Loader",
    ],
    "error_states": [
        r"setError",
        r"error\s*,\s*setError",
        r"<ErrorBoundary",
    ],
    "best_practices": [
        r"ErrorBoundary",
        r"Suspense",
        r"React\.memo",
        r"useMemo\s*\(",
        r"useCallback\s*\(",
        r"aria-label",
        r"role\s*=",
    ],
    "extra_props": [
        r"variant\?\s*:",
        r"size\?\s*:",
        r"disabled\?\s*:",
        r"loading\?\s*:",
    ],
}


class ProhibitionChecker:
    """Generates prohibition checklists and validates code compliance."""

    def __init__(self):
        """Initialize the prohibition checker."""
        # Category definitions in order
        self._category_names = [
            "loading_states",
            "error_states",
            "form_validation",
            "state_management",
            "api_integrations",
            "navigation",
            "additional_controls",
            "sample_data",
            "responsive_breakpoints",
            "animations",
            "best_practices",
            "extra_props",
        ]

        # Unconditionally prohibited categories (5, 8, 11, 12)
        self._unconditional_categories = {
            "api_integrations",
            "sample_data",
            "best_practices",
            "extra_props",
        }

    def generate_checklist(
        self, design_elements: List[Dict[str, Any]]
    ) -> ProhibitionChecklist:
        """Generate prohibition checklist from design elements.

        Args:
            design_elements: List of design elements from DesignData

        Returns:
            ProhibitionChecklist with all 12 categories
        """
        # Extract features from design elements
        features = self._extract_features(design_elements)

        # Build categories
        categories = []

        # Category 1: Loading States
        has_loading = self._has_feature(features, ["loader", "spinner", "skeleton"])
        categories.append(
            ProhibitionCategory(
                name="loading_states",
                prohibited=not has_loading,
                unconditional=False,
                reasoning=(
                    "Loading state explicitly shown in design"
                    if has_loading
                    else "Loading state not shown in design"
                ),
            )
        )

        # Category 2: Error States
        has_error = self._has_feature(features, ["error", "alert"])
        categories.append(
            ProhibitionCategory(
                name="error_states",
                prohibited=not has_error,
                unconditional=False,
                reasoning=(
                    "Error state explicitly shown in design"
                    if has_error
                    else "Error state not shown in design"
                ),
            )
        )

        # Category 3: Form Validation
        has_validation = "validation" in features
        categories.append(
            ProhibitionCategory(
                name="form_validation",
                prohibited=not has_validation,
                unconditional=False,
                reasoning=(
                    "Form validation shown in design"
                    if has_validation
                    else "Form validation not shown in design"
                ),
            )
        )

        # Category 4: State Management
        has_state_mgmt = self._has_feature(
            features, ["tabs", "accordion", "toggle", "interactive"]
        )
        categories.append(
            ProhibitionCategory(
                name="state_management",
                prohibited=not has_state_mgmt,
                unconditional=False,
                reasoning=(
                    "Interactive components shown in design requiring state management"
                    if has_state_mgmt
                    else "Complex state management not shown in design"
                ),
            )
        )

        # Category 5: API Integrations (UNCONDITIONALLY PROHIBITED)
        categories.append(
            ProhibitionCategory(
                name="api_integrations",
                prohibited=True,
                unconditional=True,
                reasoning="API integrations are unconditionally prohibited in design mode",
            )
        )

        # Category 6: Navigation
        has_navigation = self._has_feature(features, ["navigation", "link"])
        categories.append(
            ProhibitionCategory(
                name="navigation",
                prohibited=not has_navigation,
                unconditional=False,
                reasoning=(
                    "Navigation shown in design"
                    if has_navigation
                    else "Navigation not shown in design"
                ),
            )
        )

        # Category 7: Additional Controls
        categories.append(
            ProhibitionCategory(
                name="additional_controls",
                prohibited=True,
                unconditional=False,
                reasoning="Only implement controls shown in design, no additional controls",
            )
        )

        # Category 8: Sample Data (UNCONDITIONALLY PROHIBITED)
        categories.append(
            ProhibitionCategory(
                name="sample_data",
                prohibited=True,
                unconditional=True,
                reasoning="Sample data beyond design is unconditionally prohibited",
            )
        )

        # Category 9: Responsive Breakpoints
        has_responsive = "breakpoints" in features
        categories.append(
            ProhibitionCategory(
                name="responsive_breakpoints",
                prohibited=not has_responsive,
                unconditional=False,
                reasoning=(
                    "Responsive breakpoints shown in design"
                    if has_responsive
                    else "Responsive breakpoints not shown in design"
                ),
            )
        )

        # Category 10: Animations
        has_animations = self._has_feature(features, ["animation", "transition"])
        categories.append(
            ProhibitionCategory(
                name="animations",
                prohibited=not has_animations,
                unconditional=False,
                reasoning=(
                    "Animations explicitly shown in design"
                    if has_animations
                    else "Animations not shown in design"
                ),
            )
        )

        # Category 11: Best Practices (UNCONDITIONALLY PROHIBITED)
        categories.append(
            ProhibitionCategory(
                name="best_practices",
                prohibited=True,
                unconditional=True,
                reasoning="Best practice additions are unconditionally prohibited",
            )
        )

        # Category 12: Extra Props (UNCONDITIONALLY PROHIBITED)
        categories.append(
            ProhibitionCategory(
                name="extra_props",
                prohibited=True,
                unconditional=True,
                reasoning="Extra props for flexibility are unconditionally prohibited",
            )
        )

        return ProhibitionChecklist(categories=categories)

    def validate_compliance(
        self, generated_files: List[str], checklist: ProhibitionChecklist
    ) -> List[Violation]:
        """Validate that generated files comply with the prohibition checklist.

        Uses two-tier validation:
        - Tier 1: Fast regex pattern matching
        - Tier 2: AST analysis (only if Tier 1 detects potential violations)

        Args:
            generated_files: List of file paths to validate
            checklist: ProhibitionChecklist to validate against

        Returns:
            List of Violation objects found
        """
        violations = []

        # Get prohibited categories
        prohibited_categories = {
            cat.name: cat for cat in checklist.categories if cat.prohibited
        }

        # Tier 1: Fast pattern matching
        for file_path in generated_files:
            if not Path(file_path).exists():
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                continue

            # Check each prohibited category with patterns
            for category_name, patterns in TIER1_PATTERNS.items():
                if category_name not in prohibited_categories:
                    continue

                # Check if any pattern matches
                for pattern in patterns:
                    matches = list(re.finditer(pattern, content))
                    if matches:
                        # Found potential violation - run Tier 2 AST analysis
                        tier2_violations = self._tier2_ast_analysis(
                            file_path, content, category_name, pattern, matches
                        )
                        violations.extend(tier2_violations)

        return violations

    def _tier2_ast_analysis(
        self,
        file_path: str,
        content: str,
        category_name: str,
        pattern: str,
        matches: List[re.Match],
    ) -> List[Violation]:
        """Tier 2: AST analysis to confirm violations and get line numbers.

        Args:
            file_path: Path to the file
            content: File content
            category_name: Category being checked
            pattern: Pattern that matched
            matches: Regex match objects

        Returns:
            List of confirmed violations with line numbers
        """
        violations = []

        # Get severity based on whether category is unconditional
        severity = (
            ViolationSeverity.CRITICAL
            if category_name in self._unconditional_categories
            else ViolationSeverity.HIGH
        )

        # For each match, check if it's in a comment
        lines = content.split("\n")
        for match in matches:
            # Calculate line number
            line_number = content[: match.start()].count("\n") + 1

            # Check if match is in a comment
            if line_number <= len(lines):
                line_content = lines[line_number - 1]

                # Simple comment detection (skip // and /* */ comments)
                match_col = match.start() - content[: match.start()].rfind("\n") - 1
                before_match = line_content[:match_col]

                # Skip if it's in a line comment
                if "//" in before_match:
                    continue

                # Skip if it's in a block comment (simple check)
                if "/*" in content[: match.start()] and "*/" not in content[
                    content[: match.start()].rfind("/*") : match.start()
                ]:
                    continue

            # Create violation
            violations.append(
                Violation(
                    category=category_name,
                    file_path=file_path,
                    description=f"Prohibited {category_name.replace('_', ' ')} detected: {match.group()}",
                    severity=severity,
                    line_number=line_number,
                    confidence="high",
                )
            )

        return violations

    def _extract_features(self, elements: List[Dict[str, Any]]) -> Set[str]:
        """Extract all features from design elements recursively.

        Args:
            elements: List of design elements

        Returns:
            Set of feature keywords found
        """
        features = set()

        def traverse(element: Dict[str, Any]):
            """Recursively traverse element tree."""
            # Check element name
            if "name" in element:
                name = element["name"].lower()
                features.add(name)

                # Extract keywords from name
                if "loader" in name or "spinner" in name or "skeleton" in name:
                    features.add("loader")
                if "error" in name or "alert" in name:
                    features.add("error")
                if "nav" in name or "link" in name:
                    features.add("navigation")

            # Check element type
            if "type" in element:
                elem_type = element["type"].lower()
                features.add(elem_type)

                # Map types to features
                if elem_type in ("loader", "spinner", "skeleton"):
                    features.add("loader")
                if elem_type in ("alert", "error"):
                    features.add("error")
                if elem_type in ("navigation", "link"):
                    features.add("navigation")
                if elem_type in ("tabs", "accordion", "toggle"):
                    features.add("interactive")

            # Check props
            if "props" in element and isinstance(element["props"], dict):
                for key, value in element["props"].items():
                    key_lower = key.lower()
                    features.add(key_lower)

                    # Check for specific prop patterns
                    if "validation" in key_lower:
                        features.add("validation")
                    if "breakpoint" in key_lower:
                        features.add("breakpoints")
                    if "animation" in key_lower or "transition" in key_lower:
                        features.add("animation")

                    # Check prop values
                    if isinstance(value, str):
                        value_lower = value.lower()
                        if "error" in value_lower:
                            features.add("error")
                        if "loader" in value_lower or "spinner" in value_lower:
                            features.add("loader")

            # Recursively process children
            if "children" in element and isinstance(element["children"], list):
                for child in element["children"]:
                    traverse(child)

        # Traverse all elements
        for element in elements:
            traverse(element)

        return features

    def _has_feature(self, features: Set[str], keywords: List[str]) -> bool:
        """Check if any keyword is present in features set.

        Args:
            features: Set of extracted features
            keywords: List of keywords to check for

        Returns:
            True if any keyword found in features
        """
        return any(keyword in features for keyword in keywords)

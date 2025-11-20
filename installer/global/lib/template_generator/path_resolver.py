"""Template path resolution strategies.

This module provides a Strategy pattern implementation for resolving template
file paths based on architectural layers and filename patterns.

The resolver uses a chain of responsibility approach:
1. LayerClassificationStrategy - Uses AI-provided layer information (PRIMARY)
2. PatternClassificationStrategy - Infers layer from filename patterns (FALLBACK)
3. Fallback to templates/other/ when classification fails

This fixes the issue where all templates were being placed in templates/other/
instead of being organized by architectural layer.
"""

from pathlib import Path
from typing import Optional, Protocol, List, Dict
from collections import defaultdict
import importlib

# Import using importlib to avoid 'global' keyword issue
_models_module = importlib.import_module('installer.global.lib.codebase_analyzer.models')

ExampleFile = _models_module.ExampleFile
CodebaseAnalysis = _models_module.CodebaseAnalysis


# Pattern mappings: filename suffix → template subdirectory
PATTERN_MAPPINGS = [
    ('Repository', 'repositories'),
    ('Service', 'services'),
    ('Engine', 'engines'),
    ('View', 'views'),
    ('ViewModel', 'viewmodels'),
    ('Entity', 'entities'),
    ('Model', 'models'),
    ('Error', 'errors'),
    ('Controller', 'controllers'),
    ('Handler', 'handlers'),
    ('Factory', 'factories'),
    ('Builder', 'builders'),
    ('Validator', 'validators'),
    ('Mapper', 'mappers'),
]


class ClassificationStrategy(Protocol):
    """Protocol for template path classification strategies."""

    def classify(self, example_file: ExampleFile, analysis: CodebaseAnalysis) -> Optional[str]:
        """
        Attempt to classify the example file into a template path.

        Args:
            example_file: File to classify
            analysis: Codebase analysis context

        Returns:
            Classified path like "templates/application/repositories/UserRepository.cs.template"
            or None if classification fails
        """
        ...


class LayerClassificationStrategy:
    """
    Primary classification strategy using AI-provided layer information.

    This strategy uses the example_file.layer attribute that was populated
    by the AI during codebase analysis. This is the most accurate method.
    """

    def classify(self, example_file: ExampleFile, analysis: CodebaseAnalysis) -> Optional[str]:
        """
        Classify using AI-provided layer information.

        Args:
            example_file: File to classify
            analysis: Codebase analysis context

        Returns:
            Path like "templates/application/repositories/UserRepository.cs.template"
            or None if layer information not available
        """
        if not example_file.layer:
            return None

        # Get filename components
        original_path = Path(example_file.path)
        filename = original_path.name

        # Infer pattern subdirectory from filename
        pattern_dir = self._infer_pattern(example_file.path)

        # Build template path: templates/{layer}/{pattern}/{filename}.template
        layer = example_file.layer.lower()
        template_path = f"templates/{layer}/{pattern_dir}/{filename}.template"

        return template_path

    def _infer_pattern(self, file_path: str) -> str:
        """
        Infer pattern subdirectory from filename.

        Examples:
            UserRepository.cs → repositories
            AuthService.cs → services
            ConfigurationEngine.cs → engines
            DomainCameraView.cs → views

        Args:
            file_path: Full file path

        Returns:
            Pattern subdirectory name (e.g., "repositories", "services")
        """
        filename = Path(file_path).stem  # Remove extension

        # Check each pattern mapping
        for suffix, pattern_dir in PATTERN_MAPPINGS:
            if filename.endswith(suffix):
                return pattern_dir

        # Fallback: Use parent directory name
        parent_name = Path(file_path).parent.name.lower()
        return parent_name if parent_name else 'other'


class PatternClassificationStrategy:
    """
    Fallback classification strategy using filename patterns to infer layer.

    Used when AI didn't provide layer information. Infers the architectural
    layer from filename patterns:
    - Repository, Service → application layer
    - Entity, Model → domain layer
    - View, ViewModel → presentation layer
    - Engine → infrastructure layer
    """

    # Pattern → Layer mappings
    PATTERN_TO_LAYER = {
        'repositories': 'application',
        'services': 'application',
        'entities': 'domain',
        'models': 'domain',
        'errors': 'domain',
        'views': 'presentation',
        'viewmodels': 'presentation',
        'controllers': 'presentation',
        'engines': 'infrastructure',
        'handlers': 'infrastructure',
    }

    def classify(self, example_file: ExampleFile, analysis: CodebaseAnalysis) -> Optional[str]:
        """
        Classify using filename pattern to infer layer.

        Args:
            example_file: File to classify
            analysis: Codebase analysis context

        Returns:
            Path like "templates/application/repositories/UserRepository.cs.template"
            or None if pattern not recognized
        """
        filename = Path(example_file.path).stem
        original_path = Path(example_file.path)

        # Try to match filename pattern
        for suffix, pattern_dir in PATTERN_MAPPINGS:
            if filename.endswith(suffix):
                # Infer layer from pattern
                layer = self.PATTERN_TO_LAYER.get(pattern_dir)
                if layer:
                    return f"templates/{layer}/{pattern_dir}/{original_path.name}.template"

        return None


class TemplatePathResolver:
    """
    Orchestrator for template path resolution using chain of responsibility.

    Tries multiple strategies in order:
    1. LayerClassificationStrategy (AI-provided layer info)
    2. PatternClassificationStrategy (filename pattern inference)
    3. Fallback to templates/other/

    Tracks statistics and warnings for user feedback.
    """

    def __init__(self):
        """Initialize resolver with strategies."""
        self.strategies: List[ClassificationStrategy] = [
            LayerClassificationStrategy(),
            PatternClassificationStrategy(),
        ]

        # Statistics tracking
        self.classification_stats: Dict[str, int] = defaultdict(int)
        self.warnings: List[str] = []
        self.total_files = 0

    def resolve(self, example_file: ExampleFile, analysis: CodebaseAnalysis) -> str:
        """
        Resolve template path for example file.

        Tries each strategy in order until one succeeds.

        Args:
            example_file: File to classify
            analysis: Codebase analysis context

        Returns:
            Template path (always succeeds - falls back to templates/other/)
        """
        self.total_files += 1

        # Try each strategy
        for strategy in self.strategies:
            path = strategy.classify(example_file, analysis)
            if path:
                strategy_name = strategy.__class__.__name__
                self.classification_stats[strategy_name] += 1
                return path

        # Fallback with warning
        filename = Path(example_file.path).name
        self.warnings.append(f"Could not classify: {example_file.path}")
        self.classification_stats['Fallback'] += 1
        return f"templates/other/{filename}.template"

    def get_classification_summary(self) -> str:
        """
        Generate classification summary for user feedback.

        Returns:
            Multi-line summary string with statistics and warnings
        """
        if self.total_files == 0:
            return "Template Classification Summary: No files classified"

        lines = ["Template Classification Summary:"]

        # Show statistics for each strategy
        for strategy_name, count in sorted(self.classification_stats.items()):
            percentage = (count / self.total_files) * 100
            lines.append(f"  {strategy_name}: {count} files ({percentage:.1f}%)")

        # Warn if high fallback rate
        fallback_count = self.classification_stats.get('Fallback', 0)
        fallback_pct = (fallback_count / self.total_files) * 100
        if fallback_pct > 20:
            lines.append("")
            lines.append(f"  ⚠️  Warning: {fallback_pct:.1f}% of files in 'other/' directory")
            lines.append("     Consider reviewing layer assignments in AI analysis")

        return "\n".join(lines)

    def get_fallback_rate(self) -> float:
        """
        Calculate fallback rate (percentage of files in templates/other/).

        Returns:
            Fallback rate as percentage (0-100)
        """
        if self.total_files == 0:
            return 0.0

        fallback_count = self.classification_stats.get('Fallback', 0)
        return (fallback_count / self.total_files) * 100

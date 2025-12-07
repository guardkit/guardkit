"""
Layer Classification Strategies for Template Organization

Provides a Strategy pattern implementation for classifying code files into
architectural layers. Supports multiple language-specific classifiers with
fallback to generic classification.

This module improves layer classification by:
1. Using language-specific patterns (e.g., JavaScript folder conventions)
2. Providing confidence scores for classification reliability
3. Supporting multiple classification strategies with chain of responsibility
4. Enabling dependency injection for testability

TASK-FIX-40B4: Improve layer classification for JavaScript projects
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict
from pathlib import Path
import re
import importlib

# Import using importlib to avoid 'global' keyword issue
_models_module = importlib.import_module('installer.global.lib.codebase_analyzer.models')

ExampleFile = _models_module.ExampleFile
CodebaseAnalysis = _models_module.CodebaseAnalysis


@dataclass
class ClassificationResult:
    """Result of layer classification with confidence scoring."""

    layer: str
    """The classified architectural layer (e.g., 'presentation', 'data-access')"""

    confidence: float
    """Confidence score (0.0 to 1.0) indicating classification reliability"""

    strategy_used: str
    """Name of the strategy that performed the classification"""

    pattern_matched: Optional[str] = None
    """The specific pattern that matched (for debugging)"""

    def __repr__(self) -> str:
        """String representation showing layer and confidence."""
        return f"ClassificationResult(layer='{self.layer}', confidence={self.confidence:.2f}, strategy='{self.strategy_used}')"


class LayerClassificationStrategy(ABC):
    """
    Abstract base class for layer classification strategies.

    Defines the interface for classifying code files into architectural layers.
    Implementations are language-specific or generic.
    """

    @abstractmethod
    def classify(
        self,
        example_file: ExampleFile,
        analysis: CodebaseAnalysis
    ) -> Optional[ClassificationResult]:
        """
        Attempt to classify example file into an architectural layer.

        Args:
            example_file: File to classify
            analysis: Codebase analysis context

        Returns:
            ClassificationResult with layer and confidence, or None if classification fails

        Example:
            ```python
            result = classifier.classify(example_file, analysis)
            if result:
                print(f"Classified as {result.layer} with {result.confidence:.2%} confidence")
            ```
        """
        ...

    @abstractmethod
    def supports_language(self, language: str) -> bool:
        """
        Check if this strategy supports a specific language.

        Args:
            language: Programming language (e.g., 'JavaScript', 'C#', 'Python')

        Returns:
            True if this strategy can classify files in this language

        Example:
            ```python
            if classifier.supports_language('JavaScript'):
                result = classifier.classify(example_file, analysis)
            ```
        """
        ...


class JavaScriptLayerClassifier(LayerClassificationStrategy):
    """
    JavaScript-specific layer classifier using folder conventions.

    Classifies JavaScript/TypeScript files based on standard folder structures:
    - __mocks__/, .test.js, .spec.js → Testing layer
    - /scripts/, /bin/, /upload/ → Scripts/tooling layer
    - /routes/, /pages/ → Routing/Pages layer
    - /store/, /state/, /context/ → State management layer
    - /firestore/, /api/, query.js → Data access layer
    - /components/, /screens/ → Presentation layer
    - /lib/, /utils/ → Utilities layer (fallback)

    Confidence scores are adjusted based on pattern specificity:
    - High confidence (0.90-0.95): Specific, unambiguous folder names
    - Medium confidence (0.75-0.85): Common patterns with some ambiguity
    - Low confidence (0.70): Fallback patterns that could be in any layer
    """

    # Layer patterns: (folder_pattern, layer, confidence)
    # Ordered by specificity (most specific first)
    LAYER_PATTERNS: List[tuple] = [
        # Testing layer (highest specificity, 0.95 confidence)
        (r'/__mocks__/', 'testing', 0.95),
        (r'/__tests__/', 'testing', 0.95),
        (r'/\.test\.(js|jsx|ts|tsx)$', 'testing', 0.95),
        (r'/\.spec\.(js|jsx|ts|tsx)$', 'testing', 0.95),
        (r'/-mock/', 'testing', 0.95),

        # Scripts/tooling layer (0.90 confidence)
        (r'/scripts/', 'scripts', 0.90),
        (r'/upload/', 'scripts', 0.90),
        (r'/bin/', 'scripts', 0.90),

        # Routes/Pages layer (0.95 confidence)
        (r'/routes/', 'routes', 0.95),
        (r'/pages/', 'routes', 0.95),

        # State management layer (0.90 confidence)
        (r'/store/', 'state', 0.90),
        (r'/state/', 'state', 0.90),
        (r'/context/', 'state', 0.90),

        # Data access layer (0.85 confidence)
        (r'/firestore/', 'data-access', 0.85),
        (r'/api/', 'data-access', 0.85),
        (r'/query\.js$', 'data-access', 0.85),
        (r'/query\.(ts|tsx|jsx)$', 'data-access', 0.85),

        # Presentation layer (0.85 confidence)
        (r'/components/', 'presentation', 0.85),
        (r'/screens/', 'presentation', 0.85),

        # Utilities layer (fallback, 0.75 confidence)
        (r'/lib/', 'utilities', 0.75),
        (r'/utils/', 'utilities', 0.75),
    ]

    def classify(
        self,
        example_file: ExampleFile,
        analysis: CodebaseAnalysis
    ) -> Optional[ClassificationResult]:
        """
        Classify JavaScript/TypeScript file using folder conventions.

        Matches folder patterns in descending specificity order,
        returning the first match with its confidence score.

        Args:
            example_file: File to classify
            analysis: Codebase analysis context (unused in this classifier)

        Returns:
            ClassificationResult with layer and confidence (0.75-0.95),
            or None if no pattern matches

        Examples:
            ```python
            # Test file: high confidence
            file1 = ExampleFile(path="src/components/__tests__/Button.spec.js", ...)
            result1 = classifier.classify(file1, analysis)
            # → ClassificationResult(layer='testing', confidence=0.95)

            # Component file: high confidence
            file2 = ExampleFile(path="src/components/Button.jsx", ...)
            result2 = classifier.classify(file2, analysis)
            # → ClassificationResult(layer='presentation', confidence=0.85)

            # Utility file: fallback
            file3 = ExampleFile(path="src/lib/helpers.js", ...)
            result3 = classifier.classify(file3, analysis)
            # → ClassificationResult(layer='utilities', confidence=0.75)

            # Unrecognized: no match
            file4 = ExampleFile(path="src/random.js", ...)
            result4 = classifier.classify(file4, analysis)
            # → None
            ```
        """
        if not example_file.path:
            return None

        file_path = example_file.path

        # Try to match each pattern in order of specificity
        for pattern, layer, confidence in self.LAYER_PATTERNS:
            if re.search(pattern, file_path):
                return ClassificationResult(
                    layer=layer,
                    confidence=confidence,
                    strategy_used=self.__class__.__name__,
                    pattern_matched=pattern
                )

        # No pattern matched
        return None

    def supports_language(self, language: str) -> bool:
        """
        Check if this classifier supports JavaScript/TypeScript.

        Args:
            language: Programming language name

        Returns:
            True if language is JavaScript or TypeScript
        """
        return language.lower() in ['javascript', 'typescript', 'js', 'ts', 'jsx', 'tsx']


class GenericLayerClassifier(LayerClassificationStrategy):
    """
    Generic layer classifier using cross-language patterns.

    Provides fallback classification when language-specific classifiers
    don't match. Uses common architectural layer naming conventions found
    across many programming languages:
    - Domain, Core → domain layer
    - Application, UseCases → application layer
    - Web, Api, Endpoints → presentation layer
    - Infrastructure, Persistence → infrastructure layer

    Confidence scores are lower than specific classifiers (0.60-0.70)
    to indicate less certainty.
    """

    # Generic layer patterns: (pattern_string, layer, confidence)
    GENERIC_PATTERNS: List[tuple] = [
        # Domain layer
        ('/Domain/', 'domain', 0.70),
        ('/Core/', 'domain', 0.70),
        ('/domain/', 'domain', 0.70),
        ('/core/', 'domain', 0.70),

        # Application layer
        ('/Application/', 'application', 0.65),
        ('/UseCases/', 'application', 0.65),
        ('/application/', 'application', 0.65),
        ('/usecases/', 'application', 0.65),

        # Presentation/Web layer
        ('/Web/', 'presentation', 0.70),
        ('/Api/', 'presentation', 0.70),
        ('/Endpoints/', 'presentation', 0.70),
        ('/Controllers/', 'presentation', 0.65),
        ('/web/', 'presentation', 0.70),
        ('/api/', 'presentation', 0.70),
        ('/endpoints/', 'presentation', 0.70),
        ('/controllers/', 'presentation', 0.65),

        # Infrastructure layer
        ('/Infrastructure/', 'infrastructure', 0.65),
        ('/Persistence/', 'infrastructure', 0.65),
        ('/infrastructure/', 'infrastructure', 0.65),
        ('/persistence/', 'infrastructure', 0.65),
    ]

    def classify(
        self,
        example_file: ExampleFile,
        analysis: CodebaseAnalysis
    ) -> Optional[ClassificationResult]:
        """
        Classify file using generic cross-language patterns.

        Matches folder patterns in the file path, returning first match.
        Confidence scores are lower (0.60-0.70) as this is a fallback
        classifier.

        Args:
            example_file: File to classify
            analysis: Codebase analysis context

        Returns:
            ClassificationResult with layer and lower confidence (0.60-0.70),
            or None if no generic pattern matches

        Examples:
            ```python
            # C# project
            file1 = ExampleFile(path="src/Domain/Products/Product.cs", ...)
            result1 = classifier.classify(file1, analysis)
            # → ClassificationResult(layer='domain', confidence=0.70)

            # Python project
            file2 = ExampleFile(path="src/application/services.py", ...)
            result2 = classifier.classify(file2, analysis)
            # → ClassificationResult(layer='application', confidence=0.65)

            # No match
            file3 = ExampleFile(path="src/random.py", ...)
            result3 = classifier.classify(file3, analysis)
            # → None
            ```
        """
        if not example_file.path:
            return None

        file_path = example_file.path

        # Try to match each pattern
        for pattern_str, layer, confidence in self.GENERIC_PATTERNS:
            if pattern_str in file_path:
                return ClassificationResult(
                    layer=layer,
                    confidence=confidence,
                    strategy_used=self.__class__.__name__,
                    pattern_matched=pattern_str
                )

        # No pattern matched
        return None

    def supports_language(self, language: str) -> bool:
        """
        Check if this classifier supports a language.

        Generic classifier supports all languages.

        Args:
            language: Programming language name

        Returns:
            Always True for generic classifier
        """
        return True


class LayerClassificationOrchestrator:
    """
    Orchestrator for layer classification using chain of responsibility.

    Tries multiple classification strategies in order:
    1. Language-specific classifiers (e.g., JavaScriptLayerClassifier)
    2. Generic fallback classifier (GenericLayerClassifier)

    Tracks statistics and selects the strategy with highest confidence.

    Example:
        ```python
        orchestrator = LayerClassificationOrchestrator()
        result = orchestrator.classify(example_file, analysis)

        if result:
            print(f"Layer: {result.layer} (confidence: {result.confidence:.2%})")
            print(f"Strategy: {result.strategy_used}")
        else:
            print("Could not classify file")
        ```
    """

    def __init__(self, strategies: Optional[List[LayerClassificationStrategy]] = None):
        """
        Initialize orchestrator with classification strategies.

        Args:
            strategies: List of strategies to use (defaults to JS + Generic)
                       Order matters - tried in sequence
        """
        if strategies is None:
            # Default: JavaScript-specific then generic fallback
            strategies = [
                JavaScriptLayerClassifier(),
                GenericLayerClassifier(),
            ]

        self.strategies = strategies

    def classify(
        self,
        example_file: ExampleFile,
        analysis: CodebaseAnalysis
    ) -> Optional[ClassificationResult]:
        """
        Classify example file using available strategies.

        Tries each strategy in order. Returns first successful classification.
        For language-specific strategies, checks supports_language() first.

        Args:
            example_file: File to classify
            analysis: Codebase analysis context

        Returns:
            ClassificationResult from best matching strategy, or None if all fail

        Examples:
            ```python
            orchestrator = LayerClassificationOrchestrator()

            # JavaScript file → uses JavaScriptLayerClassifier
            js_file = ExampleFile(path="src/components/Button.jsx", ...)
            result1 = orchestrator.classify(js_file, analysis)
            # → ClassificationResult(layer='presentation', confidence=0.85, ...)

            # C# file → skips JS classifier, uses generic
            cs_file = ExampleFile(path="src/Domain/Product.cs", ...)
            result2 = orchestrator.classify(cs_file, analysis)
            # → ClassificationResult(layer='domain', confidence=0.70, ...)

            # Unknown file → returns None
            unknown_file = ExampleFile(path="README.md", ...)
            result3 = orchestrator.classify(unknown_file, analysis)
            # → None
            ```
        """
        if not example_file.path:
            return None

        # Detect file language
        file_language = self._detect_language(example_file.path)

        # Try each strategy in order
        for strategy in self.strategies:
            # For language-specific strategies, check if they support this language
            if not strategy.supports_language(file_language):
                continue

            result = strategy.classify(example_file, analysis)
            if result:
                return result

        # No strategy matched
        return None

    @staticmethod
    def _detect_language(file_path: str) -> str:
        """
        Detect programming language from file extension.

        Args:
            file_path: Path to file

        Returns:
            Language name (e.g., 'JavaScript', 'C#', 'Python')

        Examples:
            ```python
            _detect_language("src/Button.jsx") → "JavaScript"
            _detect_language("src/Product.cs") → "C#"
            _detect_language("src/models.py") → "Python"
            ```
        """
        ext = Path(file_path).suffix.lower()

        # JavaScript/TypeScript
        if ext in ['.js', '.jsx', '.ts', '.tsx', '.mjs', '.mts']:
            return 'JavaScript'

        # C#
        if ext == '.cs':
            return 'C#'

        # Python
        if ext == '.py':
            return 'Python'

        # Go
        if ext == '.go':
            return 'Go'

        # Rust
        if ext == '.rs':
            return 'Rust'

        # Java
        if ext == '.java':
            return 'Java'

        # C/C++
        if ext in ['.c', '.cpp', '.cc', '.cxx', '.h', '.hpp']:
            return 'C++'

        # Swift
        if ext == '.swift':
            return 'Swift'

        # Kotlin
        if ext == '.kt':
            return 'Kotlin'

        # PHP
        if ext == '.php':
            return 'PHP'

        # Ruby
        if ext == '.rb':
            return 'Ruby'

        # Default
        return 'Unknown'

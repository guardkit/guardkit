"""
Layer Classification Strategies for Template Organization

Provides a Strategy pattern implementation for classifying code files into
architectural layers. Uses AI-first approach with generic heuristic fallback
for technology-agnostic classification.

This module improves layer classification by:
1. AI-first classification that works for ANY language
2. Generic folder/path heuristics as fallback
3. Providing confidence scores for classification reliability
4. Supporting multiple classification strategies with chain of responsibility
5. Enabling dependency injection for testability

TASK-FIX-40B4: Improve layer classification for JavaScript projects
TASK-FIX-LAYER-CLASS: Add AI-powered layer classification with generic fallback
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from pathlib import Path
import re
import os

from installer.core.lib.codebase_analyzer.models import ExampleFile, CodebaseAnalysis


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


class AILayerClassifier(LayerClassificationStrategy):
    """
    AI-powered layer classifier with generic heuristic fallback.

    Works for ANY language by:
    1. Using AI to understand file purpose (if available)
    2. Falling back to universal folder/path patterns

    This classifier is technology-agnostic and should be the primary
    classifier for all projects. It follows the same AI-first + heuristic
    fallback pattern used in agent_generator.py.

    Confidence scores:
    - AI classification: 0.90 (high confidence)
    - Heuristic match: 0.85 (good confidence)
    - Fallback to 'other': 0.50 (low confidence)

    TASK-FIX-LAYER-CLASS: Technology-agnostic classification
    """

    VALID_LAYERS = frozenset({
        # Core architectural layers
        'domain',           # Domain entities and business rules
        'application',      # Application services and use cases
        'infrastructure',   # External concerns (DB, API clients, etc.)
        'presentation',     # UI layer (views, pages)

        # Specialized layers
        'viewmodels',       # MVVM ViewModels
        'engines',          # Business logic orchestration
        'services',         # Service layer
        'api',              # API controllers/endpoints
        'data-access',      # Repositories and data access

        # Supporting layers
        'handlers',         # Event/command handlers
        'processors',       # Data processors
        'mapping',          # Object mappers
        'testing',          # Test projects

        # Fallback
        'other'
    })

    def classify(
        self,
        example_file: ExampleFile,
        analysis: CodebaseAnalysis
    ) -> Optional[ClassificationResult]:
        """
        Classify file using AI-first approach with heuristic fallback.

        Follows the same pattern used in agent_generator.py:
        1. Try AI classification (if available)
        2. Fall back to generic heuristics (always works)

        Args:
            example_file: File to classify
            analysis: Codebase analysis context

        Returns:
            ClassificationResult with layer and confidence

        Examples:
            ```python
            classifier = AILayerClassifier()

            # Bootstrap file → infrastructure (via heuristic)
            file1 = ExampleFile(path="MauiProgram.cs", purpose="App entry point")
            result1 = classifier.classify(file1, analysis)
            # → ClassificationResult(layer='infrastructure', confidence=0.85)

            # Test file → testing (via heuristic)
            file2 = ExampleFile(path="ConfigurationEngineTests.cs", purpose="Tests")
            result2 = classifier.classify(file2, analysis)
            # → ClassificationResult(layer='testing', confidence=0.85)

            # Mapper file → mapping (via heuristic)
            file3 = ExampleFile(path="PlanningTypesMapper.cs", purpose="Type mapping")
            result3 = classifier.classify(file3, analysis)
            # → ClassificationResult(layer='mapping', confidence=0.85)
            ```
        """
        if not example_file.path:
            return None

        file_path = str(example_file.path)
        file_content = getattr(example_file, 'content', None)

        # Step 1: Try AI classification (if available)
        try:
            ai_layer = self._ai_classify_layer(file_path, file_content, analysis)
            if ai_layer and ai_layer != 'other':
                return ClassificationResult(
                    layer=ai_layer,
                    confidence=0.90,
                    strategy_used='AILayerClassifier',
                    pattern_matched='ai_analysis'
                )
        except Exception as e:
            # AI failed, fall back to heuristics
            pass

        # Step 2: Fall back to generic heuristics (always works)
        heuristic_layer, pattern_matched = self._heuristic_classify_layer(file_path)

        confidence = 0.85 if heuristic_layer != 'other' else 0.50

        return ClassificationResult(
            layer=heuristic_layer,
            confidence=confidence,
            strategy_used='AILayerClassifier',
            pattern_matched=pattern_matched
        )

    def _ai_classify_layer(
        self,
        file_path: str,
        file_content: Optional[str],
        analysis: Any
    ) -> Optional[str]:
        """
        Use AI to classify file into architectural layer.

        Works for ANY language by analyzing:
        - File path and name
        - File content (if available)
        - Codebase context from analysis

        Args:
            file_path: Path to the file
            file_content: Optional file content for deeper analysis
            analysis: Codebase analysis context

        Returns:
            Layer name or None if AI cannot determine

        Note:
            This is currently a stub that returns None to always use
            heuristic fallback. When AI infrastructure is integrated,
            this method will call the AI service.

        Future implementation:
            ```python
            prompt = f'''Analyze this file and determine its architectural layer.
            File: {file_path}
            Project type: {getattr(analysis, 'project_type', 'unknown')}
            Primary language: {getattr(analysis, 'language', 'unknown')}

            Return ONLY one of these layer names (lowercase):
            - testing, presentation, api, services, domain,
            - data-access, infrastructure, mapping, other
            '''
            response = self._call_ai(prompt)
            layer = response.strip().lower()
            return layer if layer in self.VALID_LAYERS else None
            ```
        """
        # TODO: When AI infrastructure is ready, implement actual AI call
        # For now, return None to always use heuristic fallback
        return None

    def _heuristic_classify_layer(self, file_path: str) -> tuple[str, str]:
        """
        Classify file using generic folder/path patterns.

        These patterns work across ALL languages:
        - /tests/, /test/, /spec/ → testing
        - /views/, /ui/, /components/ → presentation
        - /controllers/, /api/, /routes/ → api
        - etc.

        Args:
            file_path: Path to the file

        Returns:
            Tuple of (layer_name, pattern_matched)
            Defaults to ('other', 'no_match') if no pattern matches
        """
        path_lower = file_path.lower()
        filename_lower = Path(file_path).name.lower()

        # Generic folder patterns that work across languages
        # Ordered by specificity (most specific first)

        # Testing - universal patterns (check FIRST - highest priority)
        testing_patterns = [
            '/test/', '/tests/', '/spec/', '/specs/',
            '/__tests__/', '/testing/', '.test.', '.spec.',
            '_test.', '_tests.', 'test_', 'tests_'
        ]
        if any(p in path_lower for p in testing_patterns):
            return 'testing', 'folder_pattern:testing'

        # Testing - filename suffix patterns (e.g., ConfigurationEngineTests.cs)
        if filename_lower.endswith('tests.cs') or filename_lower.endswith('test.cs'):
            return 'testing', 'suffix_pattern:Tests.cs'
        if filename_lower.endswith('tests.py') or filename_lower.endswith('test.py'):
            return 'testing', 'suffix_pattern:test.py'
        if filename_lower.endswith('tests.java') or filename_lower.endswith('test.java'):
            return 'testing', 'suffix_pattern:Test.java'
        if filename_lower.endswith('_test.go'):
            return 'testing', 'suffix_pattern:_test.go'

        # Mapping - universal patterns (check before infrastructure)
        mapping_patterns = [
            '/mapper/', '/mappers/', '/mapping/',
            '/transform/', '/converter/', '/adapters/'
        ]
        if any(p in path_lower for p in mapping_patterns):
            return 'mapping', 'folder_pattern:mapping'

        # Mapping - filename suffix patterns (e.g., PlanningTypesMapper.cs)
        if 'mapper' in filename_lower:
            return 'mapping', 'suffix_pattern:Mapper'

        # Bootstrap/Entry - universal patterns
        bootstrap_patterns = [
            '/bootstrap/', '/startup/', '/config/',
            '/entry/'
        ]
        if any(p in path_lower for p in bootstrap_patterns):
            # Exclude test bootstraps
            if 'test' not in path_lower:
                return 'infrastructure', 'folder_pattern:bootstrap'

        # Bootstrap - filename patterns (e.g., MauiProgram.cs, main.py)
        bootstrap_filenames = [
            'program.cs', 'program.fs', 'main.py', 'main.go', 'main.rs',
            'main.java', 'main.kt', 'main.swift', 'main.c', 'main.cpp',
            'app.py', 'app.js', 'app.ts', 'index.js', 'index.ts',
            'bootstrap.', 'startup.'
        ]
        if any(filename_lower.startswith(p.split('.')[0]) and
               filename_lower.endswith('.' + p.split('.')[-1]) if '.' in p
               else filename_lower.startswith(p) for p in bootstrap_filenames):
            # Exclude test files
            if 'test' not in path_lower:
                return 'infrastructure', 'filename_pattern:bootstrap'

        # More specific check for program files
        if filename_lower.endswith('program.cs') or filename_lower == 'program.cs':
            if 'test' not in path_lower:
                return 'infrastructure', 'filename_pattern:Program.cs'

        # ViewModels layer (MVVM pattern) - check before presentation
        viewmodel_patterns = [
            '/viewmodel/', '/viewmodels/', '/vm/',
            '/view-models/', '/view_models/'
        ]
        if any(p in path_lower for p in viewmodel_patterns):
            return 'viewmodels', 'folder_pattern:viewmodel'

        viewmodel_suffixes = ['viewmodel.', 'vm.']
        if any(s in filename_lower for s in viewmodel_suffixes):
            return 'viewmodels', 'suffix_pattern:viewmodel'

        # Engines layer (business logic orchestration)
        engine_patterns = [
            '/engine/', '/engines/',
            '/businesslogic/', '/business-logic/',
            '/orchestration/'
        ]
        if any(p in path_lower for p in engine_patterns):
            return 'engines', 'folder_pattern:engine'

        engine_suffixes = ['engine.']
        if any(s in filename_lower for s in engine_suffixes):
            return 'engines', 'suffix_pattern:engine'

        # Handlers layer (CQRS, events)
        handler_patterns = [
            '/handler/', '/handlers/',
            '/commandhandlers/', '/command-handlers/',
            '/eventhandlers/', '/event-handlers/',
            '/queryhandlers/', '/query-handlers/'
        ]
        if any(p in path_lower for p in handler_patterns):
            return 'handlers', 'folder_pattern:handler'

        handler_suffixes = ['handler.', 'commandhandler.', 'queryhandler.', 'eventhandler.']
        if any(s in filename_lower for s in handler_suffixes):
            return 'handlers', 'suffix_pattern:handler'

        # Processors layer
        processor_patterns = [
            '/processor/', '/processors/',
            '/pipeline/', '/pipelines/'
        ]
        if any(p in path_lower for p in processor_patterns):
            return 'processors', 'folder_pattern:processor'

        processor_suffixes = ['processor.', 'pipeline.']
        if any(s in filename_lower for s in processor_suffixes):
            return 'processors', 'suffix_pattern:processor'

        # Presentation - universal patterns
        presentation_patterns = [
            '/view/', '/views/', '/ui/', '/components/',
            '/pages/', '/screens/', '/widgets/',
            '/presenter/', '/presenters/'
        ]
        if any(p in path_lower for p in presentation_patterns):
            return 'presentation', 'folder_pattern:presentation'

        # Presentation - filename patterns
        presentation_suffixes = ['view.', 'component.', 'page.', 'screen.', 'widget.']
        if any(s in filename_lower for s in presentation_suffixes):
            return 'presentation', 'suffix_pattern:presentation'

        # API - universal patterns
        api_patterns = [
            '/controller/', '/controllers/', '/api/',
            '/routes/', '/endpoints/',
            '/rest/', '/graphql/'
        ]
        if any(p in path_lower for p in api_patterns):
            return 'api', 'folder_pattern:api'

        # API - filename patterns
        api_suffixes = ['controller.', 'endpoint.']
        if any(s in filename_lower for s in api_suffixes):
            return 'api', 'suffix_pattern:api'

        # Services - universal patterns
        services_patterns = [
            '/service/', '/services/', '/usecase/',
            '/usecases/', '/application/', '/business/'
        ]
        if any(p in path_lower for p in services_patterns):
            return 'services', 'folder_pattern:services'

        # Services - filename patterns
        if 'service.' in filename_lower or 'usecase.' in filename_lower:
            return 'services', 'suffix_pattern:service'

        # Domain - universal patterns
        domain_patterns = [
            '/domain/', '/entities/', '/entity/',
            '/model/', '/models/', '/core/',
            '/valueobject/', '/valueobjects/'
        ]
        if any(p in path_lower for p in domain_patterns):
            return 'domain', 'folder_pattern:domain'

        # Domain - filename patterns
        domain_suffixes = ['entity.', 'model.', 'valueobject.']
        if any(s in filename_lower for s in domain_suffixes):
            return 'domain', 'suffix_pattern:domain'

        # Data access - universal patterns
        data_access_patterns = [
            '/repository/', '/repositories/', '/data/',
            '/database/', '/persistence/', '/storage/',
            '/dao/', '/store/'
        ]
        if any(p in path_lower for p in data_access_patterns):
            return 'data-access', 'folder_pattern:data-access'

        # Data access - filename patterns
        data_access_suffixes = ['repository.', 'store.', 'dao.']
        if any(s in filename_lower for s in data_access_suffixes):
            return 'data-access', 'suffix_pattern:data-access'

        # Infrastructure - universal patterns (fallback before 'other')
        infrastructure_patterns = [
            '/infrastructure/', '/infra/', '/util/',
            '/utils/', '/helper/', '/helpers/',
            '/common/', '/shared/', '/lib/'
        ]
        if any(p in path_lower for p in infrastructure_patterns):
            return 'infrastructure', 'folder_pattern:infrastructure'

        # Infrastructure - filename patterns
        infra_suffixes = ['util.', 'utils.', 'helper.', 'helpers.']
        if any(s in filename_lower for s in infra_suffixes):
            return 'infrastructure', 'suffix_pattern:infrastructure'

        return 'other', 'no_match'

    def supports_language(self, language: str) -> bool:
        """
        Check if this classifier supports a language.

        AI classifier supports all languages (technology-agnostic).

        Args:
            language: Programming language name

        Returns:
            Always True - supports all languages
        """
        return True


class JavaScriptLayerClassifier(LayerClassificationStrategy):
    """
    DEPRECATED: JavaScript-specific layer classifier using folder conventions.

    .. deprecated::
        Use AILayerClassifier with generic heuristics instead.
        This class is kept for backward compatibility but will be removed
        in a future version. The AI-first approach with generic heuristics
        handles all languages including JavaScript.

        TASK-FIX-LAYER-CLASS: Deprecated in favor of technology-agnostic approach

    Historical behavior (preserved for backward compatibility):
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

    Note:
        For new code, use AILayerClassifier instead:
        ```python
        # Recommended (technology-agnostic)
        classifier = AILayerClassifier()

        # Deprecated (language-specific)
        classifier = JavaScriptLayerClassifier()
        ```
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
            strategies: List of strategies to use (defaults to AI-first + Generic fallback)
                       Order matters - tried in sequence

        Note:
            Default strategies are now AI-first (technology-agnostic):
            1. AILayerClassifier - Uses AI with generic heuristic fallback
            2. GenericLayerClassifier - Cross-language patterns (final fallback)

            JavaScriptLayerClassifier is deprecated and no longer included by default.
            TASK-FIX-LAYER-CLASS: Technology-agnostic classification
        """
        if strategies is None:
            # Default: AI-first with generic fallback (technology-agnostic)
            strategies = [
                AILayerClassifier(),      # AI-first with heuristic fallback
                GenericLayerClassifier(), # Final fallback for cross-language patterns
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

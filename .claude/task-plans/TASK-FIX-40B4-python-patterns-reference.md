# TASK-FIX-40B4: Python Implementation Patterns & Best Practices

This document provides Python-specific patterns and best practices for implementing the layer classification system.

## Python Best Practices

### 1. Type Hints and Annotations

Use Python 3.9+ type hints for clarity and IDE support:

```python
from typing import Optional, List, Dict, Set
from dataclasses import dataclass
from pathlib import Path

@dataclass
class ClassificationResult:
    """Result of layer classification with confidence scoring."""
    layer: str                      # e.g., "data-access", "testing"
    confidence: float               # 0.0 to 1.0
    reason: str                     # Why this classification was chosen
    patterns_matched: List[str]     # Which patterns triggered the match

    def __post_init__(self):
        """Validate confidence is in valid range."""
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Confidence must be 0.0-1.0, got {self.confidence}")

        if not self.reason or len(self.reason.strip()) == 0:
            raise ValueError("Reason must be non-empty string")
```

### 2. Abstract Base Classes (ABC)

Define clear contracts for implementations:

```python
from abc import ABC, abstractmethod

class LayerClassificationStrategy(ABC):
    """Abstract base for language-specific layer classification.

    Subclasses implement language-specific rules for determining
    which architectural layer a file belongs to.
    """

    @abstractmethod
    def classify(self, template: 'CodeTemplate') -> Optional[ClassificationResult]:
        """Classify a template file into an architectural layer.

        Args:
            template: CodeTemplate to classify

        Returns:
            ClassificationResult if classification succeeds, None otherwise

        Raises:
            ValueError: If template is invalid
        """
        pass

    @abstractmethod
    def supports_language(self, language: str) -> bool:
        """Check if this classifier supports the language.

        Args:
            language: Programming language name (e.g., "JavaScript", "Python")

        Returns:
            True if this classifier handles the language
        """
        pass

    def __repr__(self) -> str:
        """Provide informative string representation."""
        return f"{self.__class__.__name__}()"
```

### 3. Regex Pattern Management

Organize patterns for readability and maintenance:

```python
import re
from typing import Tuple

class JavaScriptLayerClassifier(LayerClassificationStrategy):
    """JavaScript/TypeScript specific layer classification.

    Patterns are organized by layer and checked in priority order.
    Earlier layers take precedence (first match wins).
    """

    # Constants for confidence levels
    CONFIDENCE_TESTING = 0.95      # __mocks__, .test.js, -mock suffix
    CONFIDENCE_SCRIPTS = 0.90      # /scripts/, /bin/, /upload/
    CONFIDENCE_ROUTES = 0.95       # /routes/, /pages/
    CONFIDENCE_STATE = 0.90        # /store/, /state/
    CONFIDENCE_DATA_ACCESS = 0.85  # /firestore/, /api/
    CONFIDENCE_PRESENTATION = 0.85 # /components/
    CONFIDENCE_UTILITIES = 0.75    # /utils/, /lib/ (generic fallback)

    # Patterns organized by layer (priority order)
    # Compiled regex patterns for performance
    PATTERNS: Dict[str, List[re.Pattern]] = {}

    @classmethod
    def _compile_patterns(cls) -> Dict[str, List[re.Pattern]]:
        """Compile regex patterns for efficient matching.

        Returns:
            Dictionary mapping layer name to list of compiled patterns

        Note:
            Patterns are compiled once at class initialization for performance.
            This method uses @classmethod to ensure single compilation.
        """
        return {
            'testing': [
                re.compile(r'(__mocks__|\.mock|\.test|\.spec)'),
                re.compile(r'/(mock|mocks|test|tests|__tests__)/'),
            ],
            'scripts': [
                re.compile(r'/(scripts|bin|upload|tasks)/'),
                re.compile(r'(script|upload|task|cli)\.js$'),
            ],
            'routes': [
                re.compile(r'/(routes|pages)/'),
            ],
            'state': [
                re.compile(r'/(store|stores|state|context|contexts)/'),
            ],
            'data-access': [
                re.compile(r'/(firestore|api|data|database|repository|repositories)/'),
                re.compile(r'(query|mutation|model|schema)\.js$'),
            ],
            'presentation': [
                re.compile(r'/(components|screens|pages|views)/'),
                re.compile(r'Component\.js$'),
            ],
            'utilities': [
                re.compile(r'/(utils|helpers|lib|services)/'),
            ],
        }

    def __init__(self):
        """Initialize classifier with compiled patterns."""
        if not self.__class__.PATTERNS:
            self.__class__.PATTERNS = self._compile_patterns()

    def classify(self, template: 'CodeTemplate') -> Optional[ClassificationResult]:
        """Classify file based on directory and name patterns.

        Algorithm:
            1. Combine path and filename for searching
            2. Iterate through layers in priority order
            3. Check each pattern regex against search text
            4. Return first match with appropriate confidence
            5. Return None if no patterns match

        Args:
            template: CodeTemplate to classify

        Returns:
            ClassificationResult with layer and confidence, or None

        Examples:
            >>> template = CodeTemplate(
            ...     name="sessions.js",
            ...     original_path="src/lib/firestore/sessions.js",
            ...     language="JavaScript"
            ... )
            >>> result = classifier.classify(template)
            >>> result.layer
            'data-access'
            >>> result.confidence
            0.85
        """
        # Normalize path for consistent matching
        search_text = f"{template.original_path}/{template.name}"
        search_text_normalized = search_text.replace('\\', '/')

        # Check patterns in priority order (first match wins)
        for layer, patterns in self.PATTERNS.items():
            for pattern in patterns:
                if pattern.search(search_text_normalized):
                    confidence = self._get_confidence_for_layer(layer)
                    return ClassificationResult(
                        layer=layer,
                        confidence=confidence,
                        reason=f"Matched pattern '{pattern.pattern}'",
                        patterns_matched=[pattern.pattern]
                    )

        return None

    def _get_confidence_for_layer(self, layer: str) -> float:
        """Get confidence score for a given layer.

        Args:
            layer: Layer name (e.g., "testing", "data-access")

        Returns:
            Confidence float between 0.0 and 1.0

        Note:
            Testing layers have highest confidence (0.95) due to
            distinctive patterns like __mocks__ and .test.js.
            Utilities has lowest (0.75) as lib/ is generic fallback.
        """
        confidence_map = {
            'testing': self.CONFIDENCE_TESTING,
            'scripts': self.CONFIDENCE_SCRIPTS,
            'routes': self.CONFIDENCE_ROUTES,
            'state': self.CONFIDENCE_STATE,
            'data-access': self.CONFIDENCE_DATA_ACCESS,
            'presentation': self.CONFIDENCE_PRESENTATION,
            'utilities': self.CONFIDENCE_UTILITIES,
        }
        return confidence_map.get(layer, 0.5)

    def supports_language(self, language: str) -> bool:
        """Check if classifier handles this language.

        Args:
            language: Language name (e.g., "JavaScript", "TypeScript")

        Returns:
            True if language is JavaScript/TypeScript variant
        """
        if not language:
            return False
        return language.lower() in [
            "javascript", "typescript",
            "js", "ts",
            "jsx", "tsx",
        ]
```

### 4. Factory Pattern Implementation

Use factory function for clean classifier selection:

```python
def get_classifier(language: Optional[str]) -> LayerClassificationStrategy:
    """Get appropriate classifier for language.

    Factory function that returns the correct LayerClassificationStrategy
    for a given programming language.

    Args:
        language: Programming language name, or None for generic

    Returns:
        Appropriate LayerClassificationStrategy instance

    Examples:
        >>> classifier = get_classifier("JavaScript")
        >>> isinstance(classifier, JavaScriptLayerClassifier)
        True

        >>> classifier = get_classifier("Python")
        >>> isinstance(classifier, PythonLayerClassifier)
        True

        >>> classifier = get_classifier("Unknown")
        >>> isinstance(classifier, GenericLayerClassifier)
        True

        >>> classifier = get_classifier(None)
        >>> isinstance(classifier, GenericLayerClassifier)
        True
    """
    if not language:
        return GenericLayerClassifier()

    language_lower = language.lower().strip()

    # JavaScript/TypeScript variants
    if language_lower in [
        "javascript", "typescript",
        "js", "ts", "jsx", "tsx",
    ]:
        return JavaScriptLayerClassifier()

    # Python variants
    elif language_lower in ["python", "py"]:
        return PythonLayerClassifier()

    # C# variants
    elif language_lower in ["c#", "csharp", "cs"]:
        return CSharpLayerClassifier()

    # Go variants
    elif language_lower in ["go", "golang"]:
        return GoLayerClassifier()

    # Fallback for unknown languages
    else:
        return GenericLayerClassifier()
```

### 5. Inheritance and Composition

Extend generic classifier for minimal code duplication:

```python
class GenericLayerClassifier(LayerClassificationStrategy):
    """Generic fallback classifier for unknown languages.

    Uses directory name heuristics that work across languages.
    """

    GENERIC_PATTERNS: Dict[str, List[re.Pattern]] = {
        'testing': [
            re.compile(r'/(test|tests|spec|specs|__tests__)/'),
        ],
        'data-access': [
            re.compile(r'/(data|database|persistence|repository)/'),
        ],
        'presentation': [
            re.compile(r'/(ui|view|views|page|pages|screen)/'),
        ],
        'utilities': [
            re.compile(r'/(util|utils|helper|helpers|lib|libs)/'),
        ],
    }

    def classify(self, template: 'CodeTemplate') -> Optional[ClassificationResult]:
        """Classify using generic patterns."""
        search_text = f"{template.original_path}/{template.name}"

        for layer, patterns in self.GENERIC_PATTERNS.items():
            for pattern in patterns:
                if pattern.search(search_text):
                    return ClassificationResult(
                        layer=layer,
                        confidence=0.5,  # Low confidence for generic
                        reason="Generic pattern matched",
                        patterns_matched=[pattern.pattern]
                    )

        return None

    def supports_language(self, language: str) -> bool:
        """Generic classifier supports any language."""
        return True
```

### 6. Logging Best Practices

Add logging for debugging and monitoring:

```python
import logging

logger = logging.getLogger(__name__)

class JavaScriptLayerClassifier(LayerClassificationStrategy):
    """JavaScript layer classifier with logging."""

    def classify(self, template: 'CodeTemplate') -> Optional[ClassificationResult]:
        """Classify with debug logging."""
        logger.debug(f"Classifying: {template.original_path}/{template.name}")

        # ... classification logic ...

        if result:
            logger.debug(
                f"Classified as '{result.layer}' "
                f"(confidence: {result.confidence:.2f})"
            )
            return result

        logger.debug("No patterns matched, classification failed")
        return None
```

### 7. Error Handling

Handle edge cases gracefully:

```python
from typing import Union

class ClassificationError(Exception):
    """Raised when classification fails unexpectedly."""
    pass

class JavaScriptLayerClassifier(LayerClassificationStrategy):
    """JavaScript classifier with robust error handling."""

    def classify(self, template: 'CodeTemplate') -> Optional[ClassificationResult]:
        """Classify with error handling.

        Args:
            template: CodeTemplate to classify

        Returns:
            ClassificationResult or None

        Raises:
            ClassificationError: If template data is invalid
        """
        if not template:
            raise ClassificationError("Template cannot be None")

        if not template.original_path or not template.name:
            raise ClassificationError(
                f"Template must have original_path and name: {template}"
            )

        try:
            search_text = f"{template.original_path}/{template.name}"
            search_text = search_text.replace('\\', '/')

            # ... pattern matching ...

            return result

        except Exception as e:
            logger.error(f"Classification error: {e}", exc_info=True)
            raise ClassificationError(f"Failed to classify {template.name}") from e
```

### 8. Testing Patterns

Write testable, maintainable tests:

```python
import pytest
from unittest.mock import Mock

class TestJavaScriptLayerClassifier:
    """Test JavaScript layer classification.

    Uses pytest for clear, maintainable test structure.
    Each test focuses on a single classification scenario.
    """

    @pytest.fixture
    def classifier(self):
        """Provide classifier instance."""
        return JavaScriptLayerClassifier()

    def test_firestore_data_access(self, classifier):
        """Test firestore/ directory → data-access layer."""
        template = Mock()
        template.original_path = "src/lib/firestore"
        template.name = "sessions.js"

        result = classifier.classify(template)

        assert result is not None
        assert result.layer == "data-access"
        assert result.confidence >= 0.85

    def test_mock_suffix_testing(self, classifier):
        """Test mock suffix → testing layer (highest priority)."""
        template = Mock()
        template.original_path = "src/lib/firestore-mock"
        template.name = "firebase.js"

        result = classifier.classify(template)

        assert result is not None
        assert result.layer == "testing"
        assert result.confidence >= 0.95

    def test_no_match_returns_none(self, classifier):
        """Test unrecognized paths return None."""
        template = Mock()
        template.original_path = "src/mymodule"
        template.name = "handler.js"

        result = classifier.classify(template)

        assert result is None

    @pytest.mark.parametrize("language", [
        "JavaScript", "TypeScript", "js", "ts", "JSX", "TSX"
    ])
    def test_supports_javascript_variants(self, classifier, language):
        """Test classifier recognizes JavaScript variants."""
        assert classifier.supports_language(language) is True

    @pytest.mark.parametrize("language", [
        "Python", "C#", "Go", "Java", None
    ])
    def test_rejects_other_languages(self, classifier, language):
        """Test classifier rejects non-JavaScript languages."""
        assert classifier.supports_language(language) is False
```

### 9. Docstring Standards

Use clear, consistent docstrings following Google style:

```python
def classify(self, template: 'CodeTemplate') -> Optional[ClassificationResult]:
    """Classify a template file into an architectural layer.

    This method analyzes the template's path and filename to determine
    which architectural layer it belongs to. Patterns are checked in
    priority order, and the first match is returned.

    Args:
        template: CodeTemplate instance to classify. Must have
            original_path and name attributes.

    Returns:
        ClassificationResult with layer and confidence if a pattern
        matches, None if no patterns matched.

    Raises:
        ClassificationError: If template is invalid or None.

    Examples:
        >>> template = CodeTemplate(
        ...     original_path="src/lib/firestore",
        ...     name="sessions.js"
        ... )
        >>> result = classifier.classify(template)
        >>> result.layer
        'data-access'
        >>> result.confidence
        0.85

    Note:
        Patterns are checked in priority order (testing first,
        utilities last). The first matching pattern determines
        the classification.
    """
```

### 10. Performance Optimization

Pre-compile regex patterns and use caching:

```python
import functools
from typing import Dict

class JavaScriptLayerClassifier(LayerClassificationStrategy):
    """Optimized JavaScript classifier with caching."""

    # Class-level pattern cache (compiled once)
    _patterns_cache: Optional[Dict[str, List[re.Pattern]]] = None

    @classmethod
    def _get_patterns(cls) -> Dict[str, List[re.Pattern]]:
        """Get compiled patterns with caching.

        Patterns are compiled once and reused across all instances
        for performance.

        Returns:
            Dictionary of layer → compiled patterns
        """
        if cls._patterns_cache is None:
            cls._patterns_cache = {
                'testing': [re.compile(p) for p in [...]],
                'scripts': [re.compile(p) for p in [...]],
                # ...
            }
        return cls._patterns_cache

    def classify(self, template: 'CodeTemplate') -> Optional[ClassificationResult]:
        """Classify using cached patterns for performance."""
        patterns = self._get_patterns()

        search_text = f"{template.original_path}/{template.name}"

        for layer, compiled_patterns in patterns.items():
            for pattern in compiled_patterns:
                if pattern.search(search_text):
                    # ... return result ...
                    pass

        return None
```

## Design Patterns Used

### 1. Strategy Pattern
Each language has a different classification strategy, allowing runtime selection without conditional logic.

### 2. Factory Pattern
`get_classifier()` function encapsulates classifier creation logic.

### 3. Template Method Pattern
`LayerClassificationStrategy` defines the interface; subclasses implement specifics.

### 4. Decorator Pattern (Optional)
Could wrap classifiers to add logging, caching, or confidence validation.

## Code Organization

```python
# layer_classifier.py

# Section 1: Imports
from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Optional, List, Dict
import re
import logging

# Section 2: Constants
logger = logging.getLogger(__name__)

# Section 3: Data Classes
@dataclass
class ClassificationResult:
    """Result of layer classification."""
    # ...

# Section 4: Abstract Base Class
class LayerClassificationStrategy(ABC):
    """Abstract classifier interface."""
    # ...

# Section 5: Concrete Implementations
class JavaScriptLayerClassifier(LayerClassificationStrategy):
    """JavaScript-specific classifier."""
    # ...

class PythonLayerClassifier(LayerClassificationStrategy):
    """Python-specific classifier."""
    # ...

class GenericLayerClassifier(LayerClassificationStrategy):
    """Generic fallback classifier."""
    # ...

# Section 6: Factory Function
def get_classifier(language: Optional[str]) -> LayerClassificationStrategy:
    """Get classifier for language."""
    # ...
```

## Integration Checklist

- [ ] Add `ClassificationResult` to exports in `__init__.py`
- [ ] Add `LayerClassificationStrategy` to exports
- [ ] Add `get_classifier` to exports
- [ ] Import classifier in `pattern_matcher.py`
- [ ] Update `CRUDPatternMatcher.__init__()` to inject classifier
- [ ] Handle `Optional[ClassificationResult]` returns
- [ ] Add logging calls for debugging
- [ ] Add type hints to all functions
- [ ] Write comprehensive docstrings
- [ ] Test with real JavaScript projects

## Common Pitfalls to Avoid

1. **Regex Performance**: Compile once, reuse many times
2. **Pattern Order**: Testing > Scripts > Data-Access > generic
3. **Path Normalization**: Handle both `/` and `\` separators
4. **None Handling**: Always check for None returns
5. **Language Case**: Always convert to lowercase for comparison
6. **Confidence Range**: Always validate 0.0 <= confidence <= 1.0
7. **Error Messages**: Provide actionable error context

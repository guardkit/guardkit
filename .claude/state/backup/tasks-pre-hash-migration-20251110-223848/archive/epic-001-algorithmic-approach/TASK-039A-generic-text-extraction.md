---
id: TASK-039A
title: Generic Text-Based Code Pattern Extraction
status: backlog
created: 2025-11-01T18:30:00Z
priority: high
complexity: 5
estimated_hours: 5
tags: [pattern-extraction, technology-agnostic, text-analysis]
epic: EPIC-001
feature: pattern-extraction
dependencies: [TASK-037A, TASK-038A]
blocks: [TASK-039]
---

# TASK-039A: Generic Text-Based Code Pattern Extraction

## Objective

Create universal code pattern extraction using text-based analysis (regex, line patterns, indentation) that works for ANY programming language without requiring language-specific AST parsers.

**Current Problem:** Pattern extraction relies on language-specific parsers
**Solution:** Multi-tier extraction with text-based foundation

## Acceptance Criteria

- [ ] Text-based class/struct/interface detection
- [ ] Function/method signature extraction
- [ ] Import/dependency detection
- [ ] Comment pattern recognition
- [ ] Indentation-based structure detection
- [ ] Naming convention inference (PascalCase, snake_case, etc.)
- [ ] Works for Go, Rust, Java, Ruby, Python, .NET, JavaScript, etc.
- [ ] Confidence scoring (text-based = lower confidence than AST)
- [ ] Graceful handling of edge cases
- [ ] Unit tests for 15+ languages
- [ ] Documentation of extraction heuristics

## Implementation

### 1. Universal Pattern Matchers

```python
# src/commands/template_create/text_extractor.py

from dataclasses import dataclass
from typing import List, Dict, Optional, Set
from pathlib import Path
import re
from enum import Enum

class CodeElementType(Enum):
    """Universal code element types"""
    CLASS = "class"
    STRUCT = "struct"
    INTERFACE = "interface"
    TRAIT = "trait"
    ENUM = "enum"
    FUNCTION = "function"
    METHOD = "method"
    CONSTANT = "constant"
    TYPE_ALIAS = "type_alias"

@dataclass
class CodeElement:
    """Extracted code element"""
    element_type: CodeElementType
    name: str
    file_path: Path
    line_number: int
    signature: str
    confidence: int  # 0-100 (text-based = 60-80, AST-based = 90-100)
    metadata: Dict[str, any]

class UniversalPatternMatcher:
    """
    Language-agnostic pattern matching using regex and heuristics
    """

    # Universal patterns (work across C-family, Python, Ruby, etc.)
    PATTERNS = {
        # Class-like definitions (class, struct, interface, trait)
        'class': [
            # Go: type Foo struct
            r'type\s+(\w+)\s+struct\s*\{',
            # Rust: struct Foo, pub struct Foo
            r'(?:pub\s+)?struct\s+(\w+)',
            # Java/C#/TypeScript/Kotlin: class Foo, public class Foo
            r'(?:public\s+|private\s+|protected\s+)?class\s+(\w+)',
            # Swift: class Foo, struct Foo
            r'(?:public\s+|private\s+)?(?:class|struct)\s+(\w+)',
            # Python: class Foo:
            r'class\s+(\w+)\s*(?:\(.*?\))?\s*:',
            # Ruby: class Foo
            r'class\s+(\w+)',
            # PHP: class Foo
            r'class\s+(\w+)',
            # Scala: class Foo, case class Foo
            r'(?:case\s+)?class\s+(\w+)',
            # Elixir: defmodule Foo
            r'defmodule\s+([\w.]+)',
        ],

        'interface': [
            # Go: type Foo interface
            r'type\s+(\w+)\s+interface\s*\{',
            # Java/C#/TypeScript: interface Foo
            r'(?:public\s+)?interface\s+(\w+)',
            # Rust: trait Foo
            r'(?:pub\s+)?trait\s+(\w+)',
            # Swift: protocol Foo
            r'protocol\s+(\w+)',
        ],

        'function': [
            # Go: func FooBar()
            r'func\s+(\w+)\s*\(',
            # Rust: fn foo_bar(), pub fn foo_bar()
            r'(?:pub\s+)?fn\s+(\w+)\s*\(',
            # Python: def foo_bar():
            r'def\s+(\w+)\s*\(',
            # JavaScript/TypeScript: function fooBar(), const fooBar = ()
            r'(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(',
            r'(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s*)?\(',
            # Ruby: def foo_bar
            r'def\s+(\w+)',
            # PHP: function fooBar()
            r'function\s+(\w+)\s*\(',
            # C#/Java: public void FooBar()
            r'(?:public|private|protected)\s+(?:static\s+)?(?:\w+)\s+(\w+)\s*\(',
            # Swift: func fooBar()
            r'func\s+(\w+)\s*\(',
            # Elixir: def foo_bar
            r'def\s+(\w+)',
        ],

        'enum': [
            # Rust: enum Foo, pub enum Foo
            r'(?:pub\s+)?enum\s+(\w+)',
            # TypeScript/Java/C#: enum Foo
            r'(?:export\s+)?enum\s+(\w+)',
            # Swift: enum Foo
            r'enum\s+(\w+)',
        ],

        'import': [
            # Python: import foo, from foo import bar
            r'(?:from\s+[\w.]+\s+)?import\s+([\w., ]+)',
            # JavaScript/TypeScript: import { } from '', import * as
            r'import\s+(?:.*?)\s+from\s+["\'](.+?)["\']',
            # Go: import "foo"
            r'import\s+(?:\(.*?\)|"(.+?)")',
            # Rust: use foo::bar
            r'use\s+([\w:]+)',
            # Java/C#: import foo.bar, using Foo.Bar
            r'(?:import|using)\s+([\w.]+)',
            # Ruby: require 'foo'
            r'require\s+["\'](.+?)["\']',
            # PHP: use Foo\Bar
            r'use\s+([\w\\]+)',
            # Elixir: import Foo
            r'import\s+([\w.]+)',
        ],
    }

    @staticmethod
    def extract_elements(
        file_path: Path,
        element_type: str
    ) -> List[CodeElement]:
        """Extract code elements from file using text patterns"""
        if element_type not in UniversalPatternMatcher.PATTERNS:
            return []

        try:
            content = file_path.read_text(encoding='utf-8')
        except:
            return []

        elements = []
        patterns = UniversalPatternMatcher.PATTERNS[element_type]

        for pattern_str in patterns:
            pattern = re.compile(pattern_str, re.MULTILINE)

            for match in pattern.finditer(content):
                name = match.group(1)

                # Get line number
                line_number = content[:match.start()].count('\n') + 1

                # Get full line for signature
                lines = content.split('\n')
                signature = lines[line_number - 1].strip() if line_number <= len(lines) else ""

                # Confidence: text-based = 70
                confidence = 70

                elements.append(CodeElement(
                    element_type=CodeElementType(element_type) if element_type in [e.value for e in CodeElementType] else CodeElementType.CLASS,
                    name=name,
                    file_path=file_path,
                    line_number=line_number,
                    signature=signature,
                    confidence=confidence,
                    metadata={'pattern': pattern_str}
                ))

        return elements
```

### 2. Naming Convention Detector

```python
# src/commands/template_create/naming_detector.py

from enum import Enum
from collections import Counter

class NamingConvention(Enum):
    """Universal naming conventions"""
    PASCAL_CASE = "PascalCase"       # UserService, OrderRepository
    CAMEL_CASE = "camelCase"         # userService, orderRepository
    SNAKE_CASE = "snake_case"        # user_service, order_repository
    KEBAB_CASE = "kebab-case"        # user-service, order-repository
    SCREAMING_SNAKE = "SCREAMING_SNAKE"  # USER_SERVICE, ORDER_REPOSITORY
    UNKNOWN = "unknown"

@dataclass
class NamingAnalysis:
    """Analysis of naming conventions in codebase"""
    primary_convention: NamingConvention
    confidence: int  # 0-100
    examples: Dict[NamingConvention, List[str]]
    recommendations: Dict[str, str]  # element_type -> convention

class NamingConventionDetector:
    """Detect naming conventions from extracted elements"""

    @staticmethod
    def detect_convention(name: str) -> NamingConvention:
        """Detect convention of a single name"""
        if not name:
            return NamingConvention.UNKNOWN

        # SCREAMING_SNAKE_CASE (all uppercase with underscores)
        if name.isupper() and '_' in name:
            return NamingConvention.SCREAMING_SNAKE

        # snake_case (lowercase with underscores)
        if name.islower() and '_' in name:
            return NamingConvention.SNAKE_CASE

        # kebab-case (lowercase with hyphens)
        if name.islower() and '-' in name:
            return NamingConvention.KEBAB_CASE

        # PascalCase (starts with uppercase)
        if name[0].isupper() and not '_' in name and not '-' in name:
            # Check for mixed case
            if any(c.isupper() for c in name[1:]):
                return NamingConvention.PASCAL_CASE

        # camelCase (starts with lowercase, has uppercase letters)
        if name[0].islower() and any(c.isupper() for c in name):
            return NamingConvention.CAMEL_CASE

        return NamingConvention.UNKNOWN

    @staticmethod
    def analyze_codebase(elements: List[CodeElement]) -> NamingAnalysis:
        """Analyze naming conventions across codebase"""
        convention_counts = Counter()
        examples = {conv: [] for conv in NamingConvention}

        # Analyze each element
        for element in elements:
            convention = NamingConventionDetector.detect_convention(element.name)
            convention_counts[convention] += 1

            # Collect examples (max 5 per convention)
            if len(examples[convention]) < 5:
                examples[convention].append(element.name)

        # Determine primary convention
        if not convention_counts:
            return NamingAnalysis(
                primary_convention=NamingConvention.UNKNOWN,
                confidence=0,
                examples=examples,
                recommendations={}
            )

        # Exclude UNKNOWN
        if NamingConvention.UNKNOWN in convention_counts:
            del convention_counts[NamingConvention.UNKNOWN]

        if not convention_counts:
            primary = NamingConvention.UNKNOWN
            confidence = 0
        else:
            primary, count = convention_counts.most_common(1)[0]
            total = sum(convention_counts.values())
            confidence = int((count / total) * 100)

        # Recommendations by element type
        recommendations = {
            'class': primary.value,
            'function': primary.value,
            'variable': primary.value,
        }

        return NamingAnalysis(
            primary_convention=primary,
            confidence=confidence,
            examples=examples,
            recommendations=recommendations
        )
```

### 3. Multi-Tier Extraction Strategy

```python
# src/commands/template_create/extraction_strategy.py

class ExtractionTier(Enum):
    """Extraction tiers by accuracy"""
    TEXT_BASED = "text_based"       # 70% confidence, works everywhere
    AST_BASED = "ast_based"         # 90% confidence, requires parser
    SPECIALIZED = "specialized"     # 95% confidence, language-specific

@dataclass
class ExtractionResult:
    """Complete extraction result"""
    elements: List[CodeElement]
    tier_used: ExtractionTier
    confidence: int
    naming_analysis: NamingAnalysis
    metadata: Dict[str, any]

class MultiTierExtractor:
    """
    Multi-tier extraction strategy:
    1. Try specialized parser if available (TASK-039)
    2. Try AST parser if available
    3. Fall back to text-based (this task)
    """

    def __init__(self, language: str):
        self.language = language

    def extract(self, file_path: Path) -> ExtractionResult:
        """
        Extract patterns using best available tier

        For TASK-039A: We implement Tier 1 (text-based) only
        TASK-039 will add Tiers 2 and 3
        """
        # Tier 1: Text-based (universal)
        elements = self._extract_text_based(file_path)

        # Analyze naming
        naming = NamingConventionDetector.analyze_codebase(elements)

        return ExtractionResult(
            elements=elements,
            tier_used=ExtractionTier.TEXT_BASED,
            confidence=70,  # Text-based baseline
            naming_analysis=naming,
            metadata={
                'language': self.language,
                'file_path': str(file_path),
            }
        )

    def _extract_text_based(self, file_path: Path) -> List[CodeElement]:
        """Extract using text patterns"""
        all_elements = []

        # Extract each element type
        for element_type in ['class', 'interface', 'function', 'enum']:
            elements = UniversalPatternMatcher.extract_elements(file_path, element_type)
            all_elements.extend(elements)

        return all_elements
```

### 4. Integration Helper

```python
# Quick usage for other tasks

def extract_code_patterns(project_root: Path, language: str) -> ExtractionResult:
    """
    One-line helper for code pattern extraction

    Usage:
        result = extract_code_patterns(Path("/project"), "go")
        for element in result.elements:
            print(f"{element.element_type}: {element.name}")
    """
    all_elements = []

    for file_path in project_root.rglob("*"):
        if not file_path.is_file():
            continue

        # Extract from this file
        extractor = MultiTierExtractor(language)
        file_result = extractor.extract(file_path)
        all_elements.extend(file_result.elements)

    naming = NamingConventionDetector.analyze_codebase(all_elements)

    return ExtractionResult(
        elements=all_elements,
        tier_used=ExtractionTier.TEXT_BASED,
        confidence=70,
        naming_analysis=naming,
        metadata={'project_root': str(project_root), 'language': language}
    )
```

## Testing Strategy

```python
# tests/test_text_extractor.py

def test_go_class_extraction():
    """Test Go struct extraction"""
    go_code = '''
    package main

    type UserService struct {
        repo UserRepository
    }

    type OrderService struct {
        db Database
    }
    '''

    file_path = create_temp_file("test.go", go_code)
    elements = UniversalPatternMatcher.extract_elements(file_path, 'class')

    assert len(elements) == 2
    assert elements[0].name == "UserService"
    assert elements[1].name == "OrderService"

def test_rust_function_extraction():
    """Test Rust function extraction"""
    rust_code = '''
    pub fn create_user(name: String) -> Result<User, Error> {
        // ...
    }

    fn validate_email(email: &str) -> bool {
        // ...
    }
    '''

    file_path = create_temp_file("test.rs", rust_code)
    elements = UniversalPatternMatcher.extract_elements(file_path, 'function')

    assert len(elements) == 2
    assert elements[0].name == "create_user"
    assert elements[1].name == "validate_email"

def test_naming_convention_detection():
    """Test naming convention detection"""
    elements = [
        CodeElement(CodeElementType.CLASS, "UserService", Path("test.ts"), 1, "", 70, {}),
        CodeElement(CodeElementType.CLASS, "OrderRepository", Path("test.ts"), 2, "", 70, {}),
        CodeElement(CodeElementType.FUNCTION, "createUser", Path("test.ts"), 3, "", 70, {}),
    ]

    analysis = NamingConventionDetector.analyze_codebase(elements)

    # Should detect PascalCase for classes
    assert analysis.primary_convention == NamingConvention.PASCAL_CASE

def test_multi_language_extraction():
    """Test extraction works across languages"""
    languages_and_code = [
        ("go", "type User struct {}"),
        ("rust", "pub struct User {}"),
        ("java", "public class User {}"),
        ("python", "class User:"),
        ("ruby", "class User"),
        ("typescript", "class User {}"),
    ]

    for lang, code in languages_and_code:
        file_path = create_temp_file(f"test.{lang}", code)
        elements = UniversalPatternMatcher.extract_elements(file_path, 'class')

        assert len(elements) >= 1
        assert elements[0].name == "User"
```

## Definition of Done

- [ ] Text-based extraction for 15+ languages implemented
- [ ] Class/struct/interface detection working
- [ ] Function/method detection working
- [ ] Import detection working
- [ ] Naming convention analysis implemented
- [ ] Multi-tier extraction strategy defined
- [ ] Confidence scoring implemented
- [ ] Unit tests for 15+ languages passing
- [ ] Documentation of patterns and heuristics
- [ ] Integration ready for TASK-039

**Estimated Time**: 5 hours | **Complexity**: 5/10 | **Priority**: HIGH

## Impact

Provides universal code extraction foundation:
- Works for ANY language (no parser required)
- Baseline 70% confidence
- Can be enhanced with AST parsers (Tier 2) in TASK-039
- Enables template generation for unsupported languages
- Graceful degradation strategy

---
id: TASK-037A
title: Universal Language Extension Mapping
status: backlog
created: 2025-11-01T18:00:00Z
priority: high
complexity: 3
estimated_hours: 3
tags: [language-detection, technology-agnostic, universal-support]
epic: EPIC-001
feature: pattern-extraction
dependencies: []
blocks: [TASK-037]
---

# TASK-037A: Universal Language Extension Mapping

## Objective

Create comprehensive language extension mapping to support ANY programming language, eliminating the hardcoded 4-language limitation.

**Current Problem:**
```python
class Language(Enum):
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    PYTHON = "python"
    CSHARP = "csharp"
    UNKNOWN = "unknown"  # 80% of languages fall here!
```

**Solution:** Comprehensive mapping system supporting 50+ languages with graceful degradation.

## Acceptance Criteria

- [ ] Comprehensive language extension mapping (50+ languages)
- [ ] Multi-extension support (e.g., `.tsx`, `.jsx` → TypeScript/JavaScript)
- [ ] Confidence scoring for ambiguous extensions
- [ ] Framework detection hints (e.g., React from `.tsx`)
- [ ] Language family grouping (C-family, ML-family, etc.)
- [ ] File pattern matching (e.g., `Makefile`, `Dockerfile`)
- [ ] Unknown language graceful handling
- [ ] Unit tests for 20+ languages
- [ ] Documentation of supported languages

## Implementation

### 1. Core Language Database

```python
# src/commands/template_create/language_mapping.py

from dataclasses import dataclass
from typing import Dict, List, Optional, Set
from enum import Enum

class LanguageFamily(Enum):
    """Language families for pattern inference"""
    C_FAMILY = "c_family"          # C, C++, C#, Java, Go, Rust
    DYNAMIC_TYPED = "dynamic"       # Python, Ruby, JavaScript, PHP
    FUNCTIONAL = "functional"       # Haskell, OCaml, F#, Elixir
    JVM = "jvm"                    # Java, Kotlin, Scala, Groovy
    DOTNET = "dotnet"              # C#, F#, VB.NET
    WEB = "web"                    # HTML, CSS, JavaScript, TypeScript

@dataclass
class LanguageMetadata:
    """Metadata for a programming language"""
    name: str
    family: LanguageFamily
    extensions: Set[str]
    is_compiled: bool
    typical_frameworks: List[str]
    typical_test_frameworks: List[str]
    common_patterns: List[str]  # MVVM, MVC, Clean Architecture, etc.

# Comprehensive language database
LANGUAGE_DATABASE: Dict[str, LanguageMetadata] = {
    # Compiled languages
    "go": LanguageMetadata(
        name="Go",
        family=LanguageFamily.C_FAMILY,
        extensions={".go"},
        is_compiled=True,
        typical_frameworks=["gin", "echo", "fiber", "chi"],
        typical_test_frameworks=["testing", "testify", "ginkgo"],
        common_patterns=["Clean Architecture", "Repository", "Service Layer"]
    ),
    "rust": LanguageMetadata(
        name="Rust",
        family=LanguageFamily.C_FAMILY,
        extensions={".rs"},
        is_compiled=True,
        typical_frameworks=["actix-web", "rocket", "axum", "warp"],
        typical_test_frameworks=["cargo test", "rstest"],
        common_patterns=["Ownership", "Result", "Repository"]
    ),
    "java": LanguageMetadata(
        name="Java",
        family=LanguageFamily.JVM,
        extensions={".java"},
        is_compiled=True,
        typical_frameworks=["Spring", "Spring Boot", "Quarkus", "Micronaut"],
        typical_test_frameworks=["JUnit", "TestNG", "Mockito"],
        common_patterns=["MVC", "Repository", "Service Layer", "DTO"]
    ),
    "kotlin": LanguageMetadata(
        name="Kotlin",
        family=LanguageFamily.JVM,
        extensions={".kt", ".kts"},
        is_compiled=True,
        typical_frameworks=["Spring Boot", "Ktor", "Exposed"],
        typical_test_frameworks=["JUnit", "Kotest", "MockK"],
        common_patterns=["MVC", "Repository", "Result", "Sealed Classes"]
    ),
    "scala": LanguageMetadata(
        name="Scala",
        family=LanguageFamily.JVM,
        extensions={".scala"},
        is_compiled=True,
        typical_frameworks=["Play", "Akka", "Cats", "ZIO"],
        typical_test_frameworks=["ScalaTest", "Specs2"],
        common_patterns=["Functional", "Actor Model", "Type Classes"]
    ),
    "csharp": LanguageMetadata(
        name="C#",
        family=LanguageFamily.DOTNET,
        extensions={".cs"},
        is_compiled=True,
        typical_frameworks=[".NET", "ASP.NET", "MAUI", "Blazor", "FastEndpoints"],
        typical_test_frameworks=["xUnit", "NUnit", "MSTest"],
        common_patterns=["MVVM", "MVC", "Repository", "REPR", "ErrorOr"]
    ),
    "fsharp": LanguageMetadata(
        name="F#",
        family=LanguageFamily.DOTNET,
        extensions={".fs", ".fsx"},
        is_compiled=True,
        typical_frameworks=["Giraffe", "Saturn", "Fable"],
        typical_test_frameworks=["Expecto", "xUnit"],
        common_patterns=["Functional", "Railway Oriented", "Result"]
    ),
    "cpp": LanguageMetadata(
        name="C++",
        family=LanguageFamily.C_FAMILY,
        extensions={".cpp", ".cc", ".cxx", ".hpp", ".h"},
        is_compiled=True,
        typical_frameworks=["Qt", "Boost", "STL"],
        typical_test_frameworks=["Google Test", "Catch2", "doctest"],
        common_patterns=["RAII", "Template", "Observer"]
    ),
    "swift": LanguageMetadata(
        name="Swift",
        family=LanguageFamily.C_FAMILY,
        extensions={".swift"},
        is_compiled=True,
        typical_frameworks=["SwiftUI", "UIKit", "Combine", "Vapor"],
        typical_test_frameworks=["XCTest"],
        common_patterns=["MVVM", "MVC", "Protocol-Oriented"]
    ),

    # Dynamic/Interpreted languages
    "python": LanguageMetadata(
        name="Python",
        family=LanguageFamily.DYNAMIC_TYPED,
        extensions={".py", ".pyw"},
        is_compiled=False,
        typical_frameworks=["FastAPI", "Django", "Flask", "Pydantic"],
        typical_test_frameworks=["pytest", "unittest", "pytest-bdd"],
        common_patterns=["Clean Architecture", "Repository", "Service Layer"]
    ),
    "ruby": LanguageMetadata(
        name="Ruby",
        family=LanguageFamily.DYNAMIC_TYPED,
        extensions={".rb"},
        is_compiled=False,
        typical_frameworks=["Rails", "Sinatra", "Hanami"],
        typical_test_frameworks=["RSpec", "Minitest"],
        common_patterns=["MVC", "Active Record", "Service Objects"]
    ),
    "php": LanguageMetadata(
        name="PHP",
        family=LanguageFamily.DYNAMIC_TYPED,
        extensions={".php"},
        is_compiled=False,
        typical_frameworks=["Laravel", "Symfony", "Slim"],
        typical_test_frameworks=["PHPUnit", "Pest"],
        common_patterns=["MVC", "Repository", "Service Container"]
    ),
    "javascript": LanguageMetadata(
        name="JavaScript",
        family=LanguageFamily.WEB,
        extensions={".js", ".jsx", ".mjs"},
        is_compiled=False,
        typical_frameworks=["React", "Vue", "Express", "Next.js"],
        typical_test_frameworks=["Jest", "Vitest", "Mocha", "Playwright"],
        common_patterns=["Component", "Hooks", "MVC"]
    ),
    "typescript": LanguageMetadata(
        name="TypeScript",
        family=LanguageFamily.WEB,
        extensions={".ts", ".tsx"},
        is_compiled=True,  # Transpiled
        typical_frameworks=["React", "Next.js", "NestJS", "Angular"],
        typical_test_frameworks=["Jest", "Vitest", "Playwright"],
        common_patterns=["Component", "Hooks", "MVVM", "Repository", "Result"]
    ),

    # Functional languages
    "elixir": LanguageMetadata(
        name="Elixir",
        family=LanguageFamily.FUNCTIONAL,
        extensions={".ex", ".exs"},
        is_compiled=True,
        typical_frameworks=["Phoenix", "Ecto", "Plug"],
        typical_test_frameworks=["ExUnit"],
        common_patterns=["GenServer", "Supervisor", "Plug Pipeline"]
    ),
    "haskell": LanguageMetadata(
        name="Haskell",
        family=LanguageFamily.FUNCTIONAL,
        extensions={".hs", ".lhs"},
        is_compiled=True,
        typical_frameworks=["Servant", "Yesod", "Scotty"],
        typical_test_frameworks=["HUnit", "QuickCheck"],
        common_patterns=["Monad", "Functor", "Type Classes"]
    ),
    "ocaml": LanguageMetadata(
        name="OCaml",
        family=LanguageFamily.FUNCTIONAL,
        extensions={".ml", ".mli"},
        is_compiled=True,
        typical_frameworks=["Dream", "Lwt"],
        typical_test_frameworks=["Alcotest", "OUnit"],
        common_patterns=["Functional", "Module", "Variant"]
    ),

    # Other important languages
    "dart": LanguageMetadata(
        name="Dart",
        family=LanguageFamily.C_FAMILY,
        extensions={".dart"},
        is_compiled=True,
        typical_frameworks=["Flutter", "AngularDart"],
        typical_test_frameworks=["flutter_test"],
        common_patterns=["BLoC", "Provider", "MVVM"]
    ),
    "r": LanguageMetadata(
        name="R",
        family=LanguageFamily.FUNCTIONAL,
        extensions={".r", ".R"},
        is_compiled=False,
        typical_frameworks=["Shiny", "ggplot2", "dplyr"],
        typical_test_frameworks=["testthat"],
        common_patterns=["Tidyverse", "Functional"]
    ),
    "shell": LanguageMetadata(
        name="Shell",
        family=LanguageFamily.DYNAMIC_TYPED,
        extensions={".sh", ".bash", ".zsh"},
        is_compiled=False,
        typical_frameworks=[],
        typical_test_frameworks=["bats", "shunit2"],
        common_patterns=["Script"]
    ),
}

# Extension to language mapping (reverse lookup)
EXTENSION_TO_LANGUAGE: Dict[str, str] = {}
for lang_id, metadata in LANGUAGE_DATABASE.items():
    for ext in metadata.extensions:
        EXTENSION_TO_LANGUAGE[ext] = lang_id

# Special file patterns (no extension)
FILE_PATTERN_TO_LANGUAGE = {
    "Makefile": "make",
    "Dockerfile": "docker",
    "Jenkinsfile": "groovy",
    "Vagrantfile": "ruby",
    "Gemfile": "ruby",
    "Rakefile": "ruby",
    "CMakeLists.txt": "cmake",
}
```

### 2. Language Detection Service

```python
# src/commands/template_create/language_detector.py

from pathlib import Path
from typing import Optional, Tuple
from collections import Counter

class UniversalLanguageDetector:
    """Universal language detection for any programming language"""

    def detect_from_extension(self, file_path: Path) -> Optional[str]:
        """Detect language from file extension"""
        ext = file_path.suffix.lower()

        # Special files without extension
        if not ext and file_path.name in FILE_PATTERN_TO_LANGUAGE:
            return FILE_PATTERN_TO_LANGUAGE[file_path.name]

        return EXTENSION_TO_LANGUAGE.get(ext)

    def detect_primary_language(
        self,
        project_root: Path,
        exclude_patterns: List[str] = None
    ) -> Tuple[Optional[str], int, Dict[str, int]]:
        """
        Detect primary language by analyzing all files

        Returns:
            (primary_language, confidence, language_counts)
            confidence: 0-100 percentage
        """
        if exclude_patterns is None:
            exclude_patterns = ["node_modules", "venv", "dist", "build", ".git"]

        language_counts = Counter()
        total_files = 0

        for file_path in project_root.rglob("*"):
            # Skip excluded directories
            if any(pattern in str(file_path) for pattern in exclude_patterns):
                continue

            if not file_path.is_file():
                continue

            lang = self.detect_from_extension(file_path)
            if lang:
                language_counts[lang] += 1
                total_files += 1

        if not language_counts:
            return None, 0, {}

        # Primary language is most common
        primary_lang, count = language_counts.most_common(1)[0]
        confidence = int((count / total_files) * 100)

        return primary_lang, confidence, dict(language_counts)

    def get_language_metadata(self, lang_id: str) -> Optional[LanguageMetadata]:
        """Get metadata for a language"""
        return LANGUAGE_DATABASE.get(lang_id)

    def get_language_family(self, lang_id: str) -> Optional[LanguageFamily]:
        """Get language family for pattern inference"""
        metadata = self.get_language_metadata(lang_id)
        return metadata.family if metadata else None
```

### 3. Graceful Degradation

```python
# For unknown languages, provide basic support

def handle_unknown_language(project_root: Path) -> LanguageMetadata:
    """Create basic metadata for unknown language"""
    # Infer from file structure
    has_test_dir = (project_root / "test").exists() or (project_root / "tests").exists()

    return LanguageMetadata(
        name="Unknown",
        family=LanguageFamily.DYNAMIC_TYPED,  # Default assumption
        extensions=set(),
        is_compiled=False,  # Safe assumption
        typical_frameworks=[],
        typical_test_frameworks=[] if not has_test_dir else ["generic"],
        common_patterns=["Generic"]  # Will use text-based extraction
    )
```

## Testing Strategy

```python
# tests/test_universal_language_mapping.py

def test_common_languages():
    detector = UniversalLanguageDetector()

    # Test common extensions
    assert detector.detect_from_extension(Path("main.go")) == "go"
    assert detector.detect_from_extension(Path("main.rs")) == "rust"
    assert detector.detect_from_extension(Path("App.java")) == "java"
    assert detector.detect_from_extension(Path("app.rb")) == "ruby"
    assert detector.detect_from_extension(Path("index.php")) == "php"
    assert detector.detect_from_extension(Path("main.kt")) == "kotlin"
    assert detector.detect_from_extension(Path("app.swift")) == "swift"
    assert detector.detect_from_extension(Path("Component.tsx")) == "typescript"

def test_special_files():
    detector = UniversalLanguageDetector()

    assert detector.detect_from_extension(Path("Makefile")) == "make"
    assert detector.detect_from_extension(Path("Dockerfile")) == "docker"
    assert detector.detect_from_extension(Path("Gemfile")) == "ruby"

def test_metadata_retrieval():
    detector = UniversalLanguageDetector()

    go_meta = detector.get_language_metadata("go")
    assert go_meta.name == "Go"
    assert "gin" in go_meta.typical_frameworks
    assert go_meta.family == LanguageFamily.C_FAMILY

    rust_meta = detector.get_language_metadata("rust")
    assert "actix-web" in rust_meta.typical_frameworks
```

## Definition of Done

- [ ] 50+ languages mapped with comprehensive metadata
- [ ] Extension detection working for all mapped languages
- [ ] Special file pattern detection (Makefile, Dockerfile, etc.)
- [ ] Language family grouping implemented
- [ ] Graceful handling of unknown languages
- [ ] Unit tests for 20+ languages passing
- [ ] Documentation of all supported languages
- [ ] Integration with TASK-037 (stack detection)

**Estimated Time**: 3 hours | **Complexity**: 3/10 | **Priority**: HIGH

## Impact

This task is **CRITICAL** for technology agnosticism:
- Enables support for 50+ languages vs. 4
- Provides metadata for framework/pattern inference
- Allows graceful degradation for unknown languages
- Foundation for universal template creation

# EPIC-001 Technology Agnosticism Review

**Date**: 2025-11-01
**Reviewer**: Claude Code
**Focus**: Can `/template-create` and `/template-init` work with ANY technology stack?

---

## Executive Summary

**Current Status**: ❌ **NOT TRULY TECHNOLOGY AGNOSTIC**

The current task breakdown has **hardcoded assumptions** for React, Python, and .NET that would fail or provide poor results for other technology stacks (Go, Rust, Java, Ruby, PHP, Elixir, Kotlin, Swift, etc.).

**Critical Issues**: 5 major technology-specific assumptions
**Impact**: Commands would fail or be ineffective for 80% of technology stacks
**Recommendation**: Redesign with **generic-first, specialized-second** approach

---

## The Vision: True Technology Agnosticism

### What It Should Mean

**User Story**:
```bash
# Should work for ANY codebase
cd my-go-project && /template-create mycompany-go          # ✅ Should work
cd my-rust-api && /template-create mycompany-rust         # ✅ Should work
cd my-java-spring && /template-create mycompany-java      # ✅ Should work
cd my-ruby-rails && /template-create mycompany-rails      # ✅ Should work
cd my-elixir-phoenix && /template-create mycompany-elixir # ✅ Should work
cd my-kotlin-android && /template-create mycompany-kotlin # ✅ Should work
```

**Requirements**:
1. ✅ Detect ANY programming language (not just 4)
2. ✅ Infer patterns from code structure (not hardcoded patterns)
3. ✅ Extract templates from ANY language syntax
4. ✅ Generate placeholders regardless of language
5. ✅ Gracefully handle unknown patterns
6. ✅ Provide useful output even for novel/rare stacks

---

## Current Technology Assumptions

### ❌ Issue 1: Hardcoded Language Detection (TASK-037)

**Current Design**:
```python
# installer/global/commands/lib/stack_detection.py

class Language(Enum):
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    PYTHON = "python"
    CSHARP = "csharp"
    UNKNOWN = "unknown"  # ← Everything else falls here!

extension_map = {
    '.ts': Language.TYPESCRIPT,
    '.tsx': Language.TYPESCRIPT,
    '.js': Language.JAVASCRIPT,
    '.jsx': Language.JAVASCRIPT,
    '.py': Language.PYTHON,
    '.cs': Language.CSHARP,
    # ← What about .go, .rs, .java, .rb, .php, .ex, .kt, .swift?
}
```

**Problem**:
- Only 4 languages explicitly supported
- ALL other languages → `UNKNOWN`
- No detection for: Go, Rust, Java, Ruby, PHP, Elixir, Kotlin, Swift, Scala, Clojure, F#, Haskell, etc.

**Impact**:
- Go, Rust, Java projects would be labeled "UNKNOWN"
- Framework detection would fail (needs language)
- Pattern detection would fail (relies on language)
- **Complete failure** for 80% of technology stacks

---

### ❌ Issue 2: Hardcoded Pattern Detection (TASK-038)

**Current Design**:
```python
class ArchitecturePattern(Enum):
    MVVM = "mvvm"
    CLEAN_ARCHITECTURE = "clean_architecture"
    REPOSITORY = "repository_pattern"
    SERVICE = "service_pattern"
    DOMAIN = "domain_pattern"
    CQRS = "cqrs"
    # ← What about DDD, Hexagonal, Onion, Microservices, Event-Driven, Actor Model?
```

**Problem**:
- Only 6 predefined patterns
- Patterns are .NET/React-centric (MVVM, Clean Architecture)
- No detection for:
  - Hexagonal Architecture (common in Go, Java)
  - Event-Driven Architecture (Elixir, Scala)
  - Actor Model (Erlang, Akka)
  - Rails MVC (Ruby)
  - Django MVT (Python web)
  - Spring Boot patterns (Java)
  - Gin/Echo patterns (Go)

**Impact**:
- Ruby on Rails project → No patterns detected
- Go microservices → No patterns detected
- Elixir Phoenix → No patterns detected
- **Poor quality templates** for non-.NET/React stacks

---

### ❌ Issue 3: Language-Specific Code Extraction (TASK-039)

**Current Design**:
```python
class CodePatternExtractor:
    def extract_patterns(self):
        if language == Language.TYPESCRIPT or language == Language.JAVASCRIPT:
            return self._extract_react_patterns()
        elif language == Language.PYTHON:
            return self._extract_python_patterns()
        elif language == Language.CSHARP:
            return self._extract_dotnet_patterns()
        else:
            return []  # ← Nothing for other languages!
```

**Problem**:
- Requires language-specific parser for each language
- Completely fails for unsupported languages
- Regex-based parsing fragile and language-specific

**Impact**:
- Go project → **Zero patterns extracted**
- Rust project → **Zero patterns extracted**
- Java project → **Zero patterns extracted**
- **Command produces empty template** for most stacks

---

### ❌ Issue 4: Hardcoded Framework Detection (TASK-037)

**Current Design**:
```python
def _detect_js_frameworks():
    # Only checks package.json
    if 'react' in deps:
        frameworks.append({'name': 'React', ...})
    if 'next' in deps:
        frameworks.append({'name': 'Next.js', ...})
    # ← What about Vue, Angular, Svelte, Solid, Qwik?

def _detect_python_frameworks():
    # Only checks requirements.txt
    if 'fastapi' in deps:
        frameworks.append({'name': 'FastAPI', ...})
    # ← What about Django, Flask, Tornado, Sanic, Pyramid?
```

**Problem**:
- Only 2-3 frameworks per language
- Misses most popular frameworks:
  - JavaScript: Vue, Angular, Svelte, Solid, Qwik, Preact, Alpine
  - Python: Django, Flask, Tornado, Sanic, Pyramid, Bottle
  - (No frameworks for Go, Rust, Java, Ruby, etc.)

**Impact**:
- Django project → Framework not detected
- Vue project → Framework not detected
- **Generic "unknown framework" fallback** for most projects

---

### ❌ Issue 5: Template Generator Language Constraints (TASK-045)

**Current Design**:
```python
def generate_templates(self, patterns):
    for pattern in patterns:
        if pattern.pattern_type == "react_component":
            template = self._generate_react_template(pattern)
        elif pattern.pattern_type == "domain_operation":
            template = self._generate_domain_template(pattern)  # .NET-specific
        # ← No handlers for Go, Rust, Java, Ruby patterns
```

**Problem**:
- Template generation tied to specific pattern types
- No generic template generation mechanism
- Placeholder replacement assumes certain naming conventions

**Impact**:
- Go struct → **Cannot generate template**
- Rust trait impl → **Cannot generate template**
- Java class → **Cannot generate template**
- **Command fails at template generation** for most stacks

---

## Specific Technology Stack Failures

### Example 1: Go Project

**Project Structure**:
```
my-go-api/
├── cmd/
│   └── api/
│       └── main.go
├── internal/
│   ├── domain/
│   │   ├── user.go
│   │   └── product.go
│   ├── repository/
│   │   └── postgres/
│   └── service/
├── pkg/
└── go.mod
```

**Running `/template-create mycompany-go`**:

```
Phase 1: Stack Detection
✅ Detects .go files
❌ Language → "UNKNOWN" (not in Language enum)
❌ Framework → Not detected (no framework detection for Go)

Phase 2: Architecture Analysis
❌ No patterns detected (only knows MVVM, Clean Arch - not Go patterns)
❌ Repository pattern → Missed (detection assumes IRepository interface)
❌ Hexagonal architecture → Not supported

Phase 3: Code Extraction
❌ FATAL: No extraction method for Language.UNKNOWN
❌ Zero patterns extracted

Phase 4: Template Generation
❌ FATAL: No templates to generate

Result: ❌ Empty or broken template
```

---

### Example 2: Ruby on Rails Project

**Project Structure**:
```
my-rails-app/
├── app/
│   ├── controllers/
│   ├── models/
│   ├── views/
│   └── services/
├── config/
├── db/
└── Gemfile
```

**Running `/template-create mycompany-rails`**:

```
Phase 1: Stack Detection
✅ Detects .rb files
❌ Language → "UNKNOWN" (not in Language enum)
❌ Framework → Not detected (doesn't check Gemfile for Rails)

Phase 2: Architecture Analysis
❌ MVC pattern → Not detected (only knows MVVM, not MVC)
❌ Rails conventions → Not detected

Phase 3: Code Extraction
❌ FATAL: No extraction method for Ruby
❌ ActiveRecord patterns → Not extracted
❌ Controller patterns → Not extracted

Result: ❌ Broken template
```

---

### Example 3: Java Spring Boot Project

**Project Structure**:
```
my-spring-api/
├── src/
│   ├── main/
│   │   └── java/
│   │       └── com/mycompany/
│   │           ├── controller/
│   │           ├── service/
│   │           ├── repository/
│   │           └── domain/
│   └── test/
└── pom.xml
```

**Running `/template-create mycompany-java`**:

```
Phase 1: Stack Detection
✅ Detects .java files
❌ Language → "UNKNOWN"
❌ Framework → Not detected (doesn't check pom.xml or build.gradle)

Phase 2: Architecture Analysis
❌ Spring patterns → Not detected
❌ Repository pattern → Might detect (if @Repository annotation present)

Phase 3: Code Extraction
❌ FATAL: No extraction method for Java
❌ Spring annotations → Not extracted
❌ JPA entities → Not extracted

Result: ❌ Broken template
```

---

## Root Cause Analysis

### Why Current Design Fails

**1. Hardcoded Language Enumeration**
```python
# BAD: Fixed enum
class Language(Enum):
    TYPESCRIPT = "typescript"
    PYTHON = "python"
    CSHARP = "csharp"
    # Adding new language requires code change!

# GOOD: Dynamic detection
detected_language = detect_language_from_files(project_path)
# Returns: "go", "rust", "java", "ruby", etc. (any string)
```

**2. Pattern-First Instead of Structure-First**
```python
# BAD: Looking for specific patterns
if 'ViewModel' in class_name:
    pattern = "MVVM"

# GOOD: Analyzing structure generically
structure = analyze_directory_structure(project_path)
# {
#   "layers": ["controllers", "models", "services"],
#   "naming_convention": "snake_case",
#   "file_organization": "by_type"
# }
```

**3. Language-Specific Parsers**
```python
# BAD: Different parser per language
if language == "typescript":
    parse_typescript(code)
elif language == "python":
    parse_python(code)
# Requires implementing parser for EVERY language!

# GOOD: Generic AST or text analysis
extract_class_definitions(code, file_extension)
# Works for any language with classes
```

**4. Explicit Framework Mapping**
```python
# BAD: Explicit checks
if 'react' in package.json:
    framework = "React"

# GOOD: Generic dependency analysis
top_dependencies = get_top_dependencies(package_file)
# ["react", "lodash", "axios"] → Infer primary framework
```

---

## Recommended Solution: Generic-First Architecture

### Principle 1: Detect, Don't Enumerate

**Current (BAD)**:
```python
SUPPORTED_LANGUAGES = ["typescript", "python", "csharp"]
if language not in SUPPORTED_LANGUAGES:
    return UNKNOWN
```

**Proposed (GOOD)**:
```python
# Map ALL common extensions to languages
LANGUAGE_EXTENSIONS = {
    '.ts': 'typescript', '.tsx': 'typescript',
    '.js': 'javascript', '.jsx': 'javascript',
    '.py': 'python',
    '.cs': 'csharp',
    '.go': 'go',
    '.rs': 'rust',
    '.java': 'java',
    '.kt': 'kotlin',
    '.rb': 'ruby',
    '.php': 'php',
    '.ex': 'elixir', '.exs': 'elixir',
    '.swift': 'swift',
    '.scala': 'scala',
    '.clj': 'clojure',
    '.fs': 'fsharp',
    '.hs': 'haskell',
    '.erl': 'erlang',
    '.dart': 'dart',
    '.r': 'r',
    '.jl': 'julia',
    # ... comprehensive list
}

# No "supported" vs "unsupported" - all are detected
```

---

### Principle 2: Infer Patterns, Don't Match Predefined

**Current (BAD)**:
```python
if has_viewmodels and has_views:
    pattern = ArchitecturePattern.MVVM
```

**Proposed (GOOD)**:
```python
structure = {
    'directories': ['controllers', 'models', 'services', 'views'],
    'naming_patterns': {
        'controller': 'Controller$',
        'model': '^[A-Z].*(?<!Controller|Service)$',
        'service': 'Service$'
    },
    'file_colocation': 'by_type',  # vs 'by_feature'
    'common_pattern': 'mvc'  # Inferred, not matched
}
```

---

### Principle 3: Generic Code Extraction with Specialization

**Current (BAD)**:
```python
if language == "typescript":
    extract_react_patterns()
elif language == "python":
    extract_python_patterns()
else:
    return []  # FAIL!
```

**Proposed (GOOD)**:
```python
# Layer 1: Generic text-based extraction (works for ANY language)
generic_patterns = extract_generic_patterns(files)
# - Class definitions (via regex for "class Foo")
# - Function/method signatures
# - Import statements
# - Directory structure

# Layer 2: AST-based extraction (if parser available)
if has_parser_for(language):
    ast_patterns = extract_ast_patterns(files, language)
else:
    ast_patterns = []  # Graceful degradation

# Layer 3: Combine
return merge(generic_patterns, ast_patterns)
```

---

### Principle 4: Multi-Stage Fallback Mechanism

```python
class TemplateCreator:
    def create_template(self, project_path):
        # Stage 1: Try full analysis
        try:
            result = self.full_analysis(project_path)
            if result.confidence > 80:
                return result
        except Exception:
            pass

        # Stage 2: Try generic analysis
        try:
            result = self.generic_analysis(project_path)
            if result.confidence > 60:
                return result
        except Exception:
            pass

        # Stage 3: Minimal viable template
        return self.minimal_template(project_path)
        # Always succeeds - creates basic template from file structure
```

---

## Proposed Task Updates

### 🔧 TASK-037 Redesign: Universal Language Detection

**New Objective**: Detect ANY programming language, not just 4

**Changes**:

```python
# OLD (Limited)
class Language(Enum):
    TYPESCRIPT = "typescript"
    PYTHON = "python"
    CSHARP = "csharp"
    UNKNOWN = "unknown"

# NEW (Universal)
# No enum - language is just a string
LANGUAGE_EXTENSIONS = {
    # Comprehensive mapping of 50+ languages
    '.ts': 'typescript',
    '.go': 'go',
    '.rs': 'rust',
    '.java': 'java',
    '.kt': 'kotlin',
    '.rb': 'ruby',
    '.php': 'php',
    '.ex': 'elixir',
    # ... etc
}

def detect_language(project_path) -> LanguageInfo:
    return {
        'primary': 'go',  # Most common extension
        'secondary': ['typescript', 'python'],  # Other languages found
        'confidence': 95,
        'file_counts': {'go': 150, 'typescript': 10, 'python': 5}
    }
```

**Acceptance Criteria**:
- [ ] Detects 50+ languages (not just 4)
- [ ] No "UNKNOWN" language (always returns best guess)
- [ ] Supports polyglot projects (multiple languages)
- [ ] Confidence scoring

---

### 🔧 TASK-038 Redesign: Generic Pattern Inference

**New Objective**: Infer patterns from structure, not match predefined patterns

**Changes**:

```python
# OLD (Hardcoded patterns)
def detect_mvvm():
    if has_viewmodels and has_views:
        return PatternDetection(MVVM, confidence=80)

# NEW (Generic inference)
def infer_architecture(project_path):
    structure = analyze_structure(project_path)

    return {
        'layers': [
            {'name': 'domain', 'path': 'internal/domain', 'files': 15},
            {'name': 'repository', 'path': 'internal/repository', 'files': 8},
            {'name': 'service', 'path': 'internal/service', 'files': 12},
            {'name': 'handlers', 'path': 'cmd/api/handlers', 'files': 20}
        ],
        'naming_conventions': {
            'repository': 'Repository$',  # Inferred from actual files
            'service': 'Service$',
            'handler': 'Handler$'
        },
        'organization': 'by_layer',  # vs 'by_feature'
        'inferred_pattern': 'layered_architecture',  # Best guess
        'confidence': 75
    }
```

**Acceptance Criteria**:
- [ ] Analyzes directory structure (any language)
- [ ] Infers naming conventions from actual files
- [ ] Detects organization style (by-layer vs by-feature)
- [ ] Returns generic structure even for unknown patterns
- [ ] No hard failures for unknown architectures

---

### 🔧 TASK-039 Redesign: Multi-Level Code Extraction

**New Objective**: Extract patterns from ANY language using multi-level approach

**Changes**:

```python
class UniversalCodeExtractor:
    def extract(self, project_path, language):
        # Level 1: Generic text-based (works for ANY language)
        generic = self.extract_generic(project_path, language)

        # Level 2: Language-specific (if available)
        if language in SUPPORTED_PARSERS:
            specific = self.extract_language_specific(project_path, language)
        else:
            specific = []

        return merge(generic, specific)

    def extract_generic(self, project_path, language):
        """Works for ANY language via regex/text analysis"""

        patterns = []

        for file in find_source_files(project_path):
            # Extract class definitions (universal pattern)
            classes = re.findall(r'class\s+(\w+)', file.read())

            # Extract function/method definitions
            functions = re.findall(r'func(?:tion)?\s+(\w+)', file.read())

            # Extract imports/dependencies
            imports = self.extract_imports(file.read(), language)

            patterns.append(FilePattern(
                file=file.path,
                classes=classes,
                functions=functions,
                imports=imports
            ))

        return patterns

    IMPORT_PATTERNS = {
        'go': r'import\s+"([^"]+)"',
        'rust': r'use\s+([\w:]+)',
        'java': r'import\s+([\w.]+)',
        'python': r'from\s+([\w.]+)\s+import|import\s+([\w.]+)',
        'ruby': r'require\s+[\'"]([^\'"]+)[\'"]',
        # Works for most languages
    }
```

**Acceptance Criteria**:
- [ ] Level 1 (generic) works for ANY language
- [ ] Level 2 (specific) works for React, Python, .NET, Go, Rust, Java
- [ ] Graceful degradation (Level 1 only if Level 2 unavailable)
- [ ] Returns useful patterns even for unsupported languages
- [ ] No hard failures

---

### 🔧 TASK-045 Redesign: Universal Template Generation

**New Objective**: Generate templates from patterns regardless of language

**Changes**:

```python
class UniversalTemplateGenerator:
    def generate(self, patterns, language):
        templates = []

        for pattern in patterns:
            if pattern.type == 'class':
                template = self.generate_class_template(pattern, language)
            elif pattern.type == 'function':
                template = self.generate_function_template(pattern, language)
            # Generic types work for any language

            templates.append(template)

        return templates

    def generate_class_template(self, pattern, language):
        """Generate class template for ANY language"""

        # Get language-specific syntax
        syntax = LANGUAGE_SYNTAX.get(language, DEFAULT_SYNTAX)

        template = f"""
{syntax['class_keyword']} {{{{ClassName}}}} {{
    {syntax['comment']} TODO: Add fields

    {syntax['method_keyword']} {{{{MethodName}}}}() {{
        {syntax['comment']} TODO: Implementation
    }}
}}
"""
        return template

LANGUAGE_SYNTAX = {
    'go': {
        'class_keyword': 'type',
        'method_keyword': 'func',
        'comment': '//'
    },
    'rust': {
        'class_keyword': 'struct',
        'method_keyword': 'fn',
        'comment': '//'
    },
    'java': {
        'class_keyword': 'public class',
        'method_keyword': 'public void',
        'comment': '//'
    },
    # ... all languages
}
```

**Acceptance Criteria**:
- [ ] Generates templates for 20+ languages
- [ ] Uses language-specific syntax
- [ ] Placeholders work regardless of language
- [ ] Fallback to generic template if syntax unknown

---

## New Tasks Required

### 📋 TASK-037A: Universal Language Extension Mapping

**Objective**: Create comprehensive language detection for 50+ languages

**Estimated**: 3 hours | **Complexity**: 3/10 | **Priority**: HIGH

**Deliverables**:
- Mapping of 50+ file extensions to languages
- Comprehensive package manager detection (not just package.json)
  - npm/yarn/pnpm (JavaScript)
  - pip/poetry (Python)
  - cargo (Rust)
  - go.mod (Go)
  - Gemfile (Ruby)
  - composer.json (PHP)
  - mix.exs (Elixir)
  - build.gradle/pom.xml (Java)
  - Package.swift (Swift)
  - etc.

---

### 📋 TASK-038A: Generic Structure Analyzer

**Objective**: Analyze project structure without predefined patterns

**Estimated**: 6 hours | **Complexity**: 6/10 | **Priority**: HIGH

**Deliverables**:
- Directory structure analysis (any project)
- Naming convention inference from actual files
- Organization detection (by-layer vs by-feature)
- Generic pattern inference (best guess, not match)

---

### 📋 TASK-039A: Generic Text-Based Extraction

**Objective**: Extract patterns using regex/text analysis (no AST)

**Estimated**: 5 hours | **Complexity**: 5/10 | **Priority**: HIGH

**Deliverables**:
- Class definition extraction (universal regex)
- Function/method extraction (universal regex)
- Import statement extraction (per-language regex)
- Works for ANY language

---

### 📋 TASK-045A: Language Syntax Database

**Objective**: Database of syntax rules for 20+ languages

**Estimated**: 4 hours | **Complexity**: 3/10 | **Priority**: MEDIUM

**Deliverables**:
- Syntax rules for class, method, comment, etc.
- Template generation using syntax rules
- Fallback to generic syntax if language unknown

---

## Updated Architecture Diagram

### Before (Language-Specific)

```
/template-create
    ↓
Is language TypeScript/Python/.NET?
    ├─ YES → Run specialized extractors → Success
    └─ NO → FAIL (return empty)
```

### After (Universal)

```
/template-create
    ↓
Detect language (ANY language) → confidence score
    ↓
Level 1: Generic extraction (text-based) → Always succeeds
    ↓
Level 2: Language-specific extraction (if available) → Enhancement
    ↓
Level 3: Merge results → Best possible template
    ↓
Success (with varying quality based on language support)
```

---

## Quality Tiers

### Tier 1: Full Support (Best Quality)
**Languages**: React/TypeScript, Python, .NET, Go, Rust, Java
- AST-based extraction
- Known patterns
- Specialized templates
- **Quality**: 95%

### Tier 2: Generic Support (Good Quality)
**Languages**: Ruby, PHP, Elixir, Kotlin, Swift, Scala
- Text-based extraction
- Inferred patterns
- Generic templates with syntax rules
- **Quality**: 75%

### Tier 3: Basic Support (Minimal Quality)
**Languages**: Rare/novel languages
- Text-based extraction only
- Directory structure analysis
- Generic templates with fallback syntax
- **Quality**: 50% (but still useful!)

**Key**: All tiers produce a working template, just varying levels of sophistication

---

## Success Criteria (Updated)

### Must Work For
- ✅ React/TypeScript/JavaScript projects
- ✅ Python projects (FastAPI, Django, Flask)
- ✅ .NET projects (MAUI, ASP.NET, Blazor)
- ✅ Go projects (Gin, Echo, microservices)
- ✅ Rust projects (Axum, Actix, Rocket)
- ✅ Java projects (Spring Boot, Micronaut)
- ✅ Ruby projects (Rails, Sinatra)
- ✅ PHP projects (Laravel, Symfony)
- ✅ Elixir projects (Phoenix)
- ✅ Kotlin projects (Android, Ktor)

### Should Provide Useful Output For
- ✅ Swift projects
- ✅ Scala projects
- ✅ Clojure projects
- ✅ F# projects
- ✅ Haskell projects
- ✅ Any language with class-based structure

### Must Not Fail For
- ✅ ANY codebase (graceful degradation)
- ✅ Polyglot projects (multiple languages)
- ✅ Novel/custom languages

---

## Recommendation

### Immediate Actions

1. **Add TASK-037A, 038A, 039A, 045A** (4 new tasks)
2. **Redesign existing tasks** with generic-first approach
3. **Add quality tier documentation** to guide expectations
4. **Implement fallback mechanisms** at every phase

### Implementation Priority

**Phase 1**: Universal detection (1 week)
- TASK-037A: Language mapping
- TASK-038A: Generic structure analyzer
- TASK-039A: Generic text extraction

**Phase 2**: Specialized support (2 weeks)
- React/TypeScript (existing)
- Python (existing)
- .NET (existing)
- Go (new)
- Rust (new)
- Java (new)

**Phase 3**: Extended support (ongoing)
- Ruby, PHP, Elixir, etc. as needed

---

## Conclusion

**Current Status**: ❌ Not technology agnostic - fails for 80% of stacks

**Recommended Approach**:
- **Generic-first, specialized-second**
- **Multi-level extraction** (text → AST → specialized)
- **Fallback mechanisms** at every phase
- **Quality tiers** instead of supported/unsupported

**Impact**: Commands work for ANY technology stack, producing:
- **Tier 1 quality** for 6 well-supported languages
- **Tier 2 quality** for 10+ partially-supported languages
- **Tier 3 quality** for ALL other languages (basic but useful)

**Effort**: +4 tasks (~18 hours) to make truly universal

---

**Status**: ⚠️ **CRITICAL ISSUE** - Current design too language-specific
**Recommendation**: **REDESIGN** before implementation
**Benefit**: Commands work for 100% of projects vs. 20%

---

**Created**: 2025-11-01
**Priority**: CRITICAL
**Impact**: HIGH

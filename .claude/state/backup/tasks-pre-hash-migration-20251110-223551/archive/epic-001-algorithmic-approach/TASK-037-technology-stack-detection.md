---
id: TASK-037
title: Implement technology stack detection for /template-create
status: backlog
created: 2025-11-01T15:30:00Z
priority: high
complexity: 5
estimated_hours: 6
tags: [template-create, pattern-extraction, stack-detection]
epic: EPIC-001
feature: pattern-extraction
dependencies: []
blocks: [TASK-038, TASK-042]
---

# TASK-037: Implement Technology Stack Detection

## Objective

Create an automatic technology stack detection system that analyzes a codebase and identifies:
- Primary programming language(s)
- Framework(s) and versions
- Build tools and package managers
- Testing frameworks
- Key libraries and dependencies

## Context

This is Phase 1.1 of the `/template-create` command. Accurate stack detection is the foundation for all subsequent pattern analysis and agent discovery.

## Scope

### In Scope
- Language detection (TypeScript, Python, C#, JavaScript, etc.)
- Framework detection (React, FastAPI, .NET MAUI, Next.js, etc.)
- Version extraction from package files
- Build tool identification (Vite, Webpack, npm, dotnet, pip)
- Testing framework detection

### Out of Scope
- Architecture pattern analysis (TASK-038)
- Code pattern extraction (TASK-039)
- Agent discovery (separate feature)

## Requirements

### Functional Requirements

**REQ-1**: Detect primary programming language
```
When analyzing a project directory, the system shall:
- Count files by extension (.ts, .py, .cs, .js, etc.)
- Identify dominant language by file count and LOC
- Return confidence score (0-100) for language detection
```

**REQ-2**: Identify frameworks
```
When analyzing package files, the system shall:
- Parse package.json (React, Next.js, Vite)
- Parse requirements.txt / pyproject.toml (FastAPI, Django, Flask)
- Parse .csproj (MAUI, Blazor, ASP.NET)
- Extract framework names and versions
```

**REQ-3**: Detect build tools
```
When analyzing project configuration, the system shall:
- Identify build tool (Vite, Webpack, esbuild, Rollup)
- Identify package manager (npm, yarn, pnpm, pip, poetry, dotnet)
- Extract versions where available
```

**REQ-4**: Identify testing frameworks
```
When analyzing dependencies and config, the system shall:
- Detect test framework (Vitest, Jest, pytest, xUnit, NUnit)
- Detect testing libraries (React Testing Library, Playwright, Detox)
- Identify mocking libraries (MSW, NSubstitute, unittest.mock)
```

**REQ-5**: Extract library dependencies
```
When analyzing package files, the system shall:
- List top 10 most relevant libraries by usage
- Categorize libraries (UI, state management, utilities, testing)
- Note version constraints
```

## Acceptance Criteria

### AC1: Language Detection
- [ ] Correctly identifies TypeScript projects (>90% accuracy)
- [ ] Correctly identifies Python projects (>90% accuracy)
- [ ] Correctly identifies C# projects (>90% accuracy)
- [ ] Correctly identifies JavaScript projects (>90% accuracy)
- [ ] Returns confidence score for detection
- [ ] Handles multi-language projects (primary + secondary)

### AC2: Framework Detection
- [ ] Detects React + version from package.json
- [ ] Detects Next.js + version from package.json
- [ ] Detects FastAPI + version from requirements.txt
- [ ] Detects .NET MAUI from .csproj
- [ ] Detects Vue, Angular, Svelte (bonus)

### AC3: Build Tool Detection
- [ ] Identifies Vite from vite.config.ts
- [ ] Identifies Webpack from webpack.config.js
- [ ] Identifies npm/yarn/pnpm from lock files
- [ ] Identifies dotnet from .csproj
- [ ] Identifies pip/poetry from Python config files

### AC4: Testing Framework Detection
- [ ] Detects Vitest from vite.config.ts or vitest.config.ts
- [ ] Detects Jest from jest.config.js or package.json
- [ ] Detects pytest from pytest.ini or pyproject.toml
- [ ] Detects xUnit/NUnit from .csproj

### AC5: Data Structure
- [ ] Returns structured JSON with all detected info
- [ ] Includes confidence scores
- [ ] Provides version information where available
- [ ] Categorizes libraries appropriately

## Implementation Plan

### Step 1: Create Detection Module Structure

```python
# installer/global/commands/lib/stack_detection.py

from dataclasses import dataclass
from typing import List, Optional, Dict
from enum import Enum

class Language(Enum):
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    PYTHON = "python"
    CSHARP = "csharp"
    UNKNOWN = "unknown"

@dataclass
class StackDetectionResult:
    primary_language: Language
    language_confidence: int  # 0-100
    frameworks: List[Dict[str, str]]  # [{"name": "React", "version": "18.2.0"}]
    build_tools: List[Dict[str, str]]
    package_manager: str
    testing_framework: Optional[str]
    testing_libraries: List[str]
    key_libraries: List[Dict[str, str]]
    confidence_overall: int  # 0-100

class StackDetector:
    def __init__(self, project_path: str):
        self.project_path = project_path

    def detect(self) -> StackDetectionResult:
        """Main detection method"""
        pass

    def _detect_language(self) -> tuple[Language, int]:
        """Detect primary language and confidence"""
        pass

    def _detect_frameworks(self, language: Language) -> List[Dict[str, str]]:
        """Detect frameworks for given language"""
        pass

    def _detect_build_tools(self, language: Language) -> List[Dict[str, str]]:
        """Detect build tools"""
        pass

    def _detect_testing(self, language: Language) -> tuple[Optional[str], List[str]]:
        """Detect testing framework and libraries"""
        pass
```

### Step 2: Implement Language Detection

```python
def _detect_language(self) -> tuple[Language, int]:
    """Count files by extension and determine primary language"""

    extension_map = {
        '.ts': Language.TYPESCRIPT,
        '.tsx': Language.TYPESCRIPT,
        '.js': Language.JAVASCRIPT,
        '.jsx': Language.JAVASCRIPT,
        '.py': Language.PYTHON,
        '.cs': Language.CSHARP,
    }

    file_counts = {}

    # Walk directory and count files
    for root, dirs, files in os.walk(self.project_path):
        # Skip node_modules, venv, bin, obj
        if any(skip in root for skip in ['node_modules', 'venv', 'bin', 'obj', '.git']):
            continue

        for file in files:
            ext = os.path.splitext(file)[1]
            if ext in extension_map:
                lang = extension_map[ext]
                file_counts[lang] = file_counts.get(lang, 0) + 1

    # Determine primary language
    if not file_counts:
        return Language.UNKNOWN, 0

    primary = max(file_counts, key=file_counts.get)
    total_files = sum(file_counts.values())
    confidence = int((file_counts[primary] / total_files) * 100)

    return primary, confidence
```

### Step 3: Implement Framework Detection

```python
def _detect_frameworks(self, language: Language) -> List[Dict[str, str]]:
    """Detect frameworks based on language"""

    if language == Language.TYPESCRIPT or language == Language.JAVASCRIPT:
        return self._detect_js_frameworks()
    elif language == Language.PYTHON:
        return self._detect_python_frameworks()
    elif language == Language.CSHARP:
        return self._detect_dotnet_frameworks()

    return []

def _detect_js_frameworks(self) -> List[Dict[str, str]]:
    """Parse package.json for JavaScript/TypeScript frameworks"""

    package_json_path = os.path.join(self.project_path, 'package.json')

    if not os.path.exists(package_json_path):
        return []

    with open(package_json_path, 'r') as f:
        package_data = json.load(f)

    frameworks = []
    deps = {**package_data.get('dependencies', {}),
            **package_data.get('devDependencies', {})}

    # Check for React
    if 'react' in deps:
        frameworks.append({
            'name': 'React',
            'version': deps['react'].replace('^', '').replace('~', '')
        })

    # Check for Next.js
    if 'next' in deps:
        frameworks.append({
            'name': 'Next.js',
            'version': deps['next'].replace('^', '').replace('~', '')
        })

    # Check for Vite
    if 'vite' in deps:
        frameworks.append({
            'name': 'Vite',
            'version': deps['vite'].replace('^', '').replace('~', '')
        })

    return frameworks
```

### Step 4: Implement Testing Detection

```python
def _detect_testing(self, language: Language) -> tuple[Optional[str], List[str]]:
    """Detect testing framework and libraries"""

    if language == Language.TYPESCRIPT or language == Language.JAVASCRIPT:
        return self._detect_js_testing()
    elif language == Language.PYTHON:
        return self._detect_python_testing()
    elif language == Language.CSHARP:
        return self._detect_dotnet_testing()

    return None, []

def _detect_js_testing(self) -> tuple[Optional[str], List[str]]:
    """Detect JavaScript/TypeScript testing setup"""

    package_json_path = os.path.join(self.project_path, 'package.json')

    if not os.path.exists(package_json_path):
        return None, []

    with open(package_json_path, 'r') as f:
        package_data = json.load(f)

    deps = {**package_data.get('dependencies', {}),
            **package_data.get('devDependencies', {})}

    framework = None
    libraries = []

    # Check for Vitest
    if 'vitest' in deps:
        framework = 'Vitest'
    # Check for Jest
    elif 'jest' in deps or '@jest/globals' in deps:
        framework = 'Jest'

    # Check for testing libraries
    if '@testing-library/react' in deps:
        libraries.append('React Testing Library')
    if 'playwright' in deps or '@playwright/test' in deps:
        libraries.append('Playwright')
    if 'cypress' in deps:
        libraries.append('Cypress')

    return framework, libraries
```

### Step 5: Create CLI Interface

```python
def detect_stack(project_path: str) -> StackDetectionResult:
    """Public API for stack detection"""

    detector = StackDetector(project_path)
    return detector.detect()

# Usage in /template-create command
if __name__ == "__main__":
    import sys

    project_path = sys.argv[1] if len(sys.argv) > 1 else "."

    result = detect_stack(project_path)

    print(f"Language: {result.primary_language.value} ({result.language_confidence}% confidence)")
    print(f"Frameworks: {', '.join(f['name'] for f in result.frameworks)}")
    print(f"Build Tools: {', '.join(t['name'] for t in result.build_tools)}")
    print(f"Testing: {result.testing_framework}")
    print(f"Libraries: {', '.join(result.key_libraries[:5])}")
```

## Testing Strategy

### Unit Tests

```python
def test_detect_language_typescript():
    """Should detect TypeScript as primary language"""
    # Create mock project with .ts files
    result = detect_stack("tests/fixtures/typescript-project")

    assert result.primary_language == Language.TYPESCRIPT
    assert result.language_confidence >= 90

def test_detect_react_framework():
    """Should detect React framework and version"""
    result = detect_stack("tests/fixtures/react-project")

    frameworks = [f['name'] for f in result.frameworks]
    assert 'React' in frameworks

    react = next(f for f in result.frameworks if f['name'] == 'React')
    assert react['version'] is not None

def test_detect_vitest():
    """Should detect Vitest testing framework"""
    result = detect_stack("tests/fixtures/vitest-project")

    assert result.testing_framework == 'Vitest'
```

### Integration Tests

```bash
# Test with real projects
python installer/global/commands/lib/stack_detection.py /path/to/react-project
python installer/global/commands/lib/stack_detection.py /path/to/python-project
python installer/global/commands/lib/stack_detection.py /path/to/maui-project
```

## Files to Create

1. `installer/global/commands/lib/stack_detection.py` - Main detection module (~400 lines)
2. `installer/global/commands/lib/stack_detection/__init__.py` - Package init
3. `installer/global/commands/lib/stack_detection/language_detector.py` - Language detection (~150 lines)
4. `installer/global/commands/lib/stack_detection/framework_detector.py` - Framework detection (~250 lines)
5. `installer/global/commands/lib/stack_detection/testing_detector.py` - Testing detection (~150 lines)
6. `tests/unit/test_stack_detection.py` - Unit tests (~300 lines)
7. `tests/integration/test_stack_detection_real_projects.py` - Integration tests (~150 lines)
8. `tests/fixtures/` - Test project fixtures

## Definition of Done

- [ ] StackDetector class implemented with all methods
- [ ] Language detection working for TS, JS, Python, C#
- [ ] Framework detection for React, Next.js, FastAPI, .NET MAUI
- [ ] Build tool detection for Vite, npm, dotnet
- [ ] Testing framework detection for Vitest, Jest, pytest, xUnit
- [ ] Returns structured JSON output
- [ ] Unit tests passing (>85% coverage)
- [ ] Integration tests with real projects
- [ ] Documentation and examples

## Success Metrics

- Language detection accuracy: >90%
- Framework detection accuracy: >85%
- Execution time: <5 seconds for typical project
- False positive rate: <10%

## Related Tasks

- **Blocks**: TASK-038 (Architecture Pattern Analyzer)
- **Blocks**: TASK-042 (Manifest Generator)
- **Epic**: EPIC-001 (Template Creation Automation)

---

**Estimated Time**: 6 hours
**Complexity**: 5/10 (Medium)
**Priority**: HIGH (Foundation for template-create)

---
id: TASK-FIX-PATTERN-C5D9
title: Complete Pattern Detection
status: completed
task_type: implementation
created: 2025-12-11T10:45:00Z
updated: 2025-12-11T12:30:00Z
completed: 2025-12-11T12:30:00Z
priority: high
tags: [template-create, pattern-detection, manifest, codebase-analyzer]
complexity: 4
parent_review: TASK-REV-D4A7
test_results:
  status: passing
  coverage: 15%
  last_run: 2025-12-11T12:30:00Z
  tests_passed: 22
  tests_failed: 0
---

# Task: Complete Pattern Detection

## Problem Statement

The heuristic pattern detection in `_detect_patterns()` only detects **3 of 14 patterns** defined in `PATTERN_MAPPINGS`. Critical patterns like MVVM, Engine, and ErrorOr are not detected, resulting in incomplete `manifest.json` output.

**Detection Gap:**

| Pattern | Defined | Detected | Impact |
|---------|---------|----------|--------|
| Repository | ✅ | ✅ | Working |
| Factory | ✅ | ✅ | Working |
| Service Layer | ✅ | ✅ | Working |
| **Engine** | ✅ | ❌ | Missing for business logic |
| **ViewModel** | ✅ | ❌ | Missing for MVVM apps |
| **Error** | ✅ | ❌ | Missing for ErrorOr pattern |
| Entity | ✅ | ❌ | Missing |
| Model | ✅ | ❌ | Missing |
| Controller | ✅ | ❌ | Missing |
| Handler | ✅ | ❌ | Missing |
| Validator | ✅ | ❌ | Missing |
| Mapper | ✅ | ❌ | Missing |
| Builder | ✅ | ❌ | Missing |
| View | ✅ | ❌ | Missing |

## Root Cause

**Current Code** (`agent_invoker.py:418-438`):
```python
def _detect_patterns(self) -> list:
    """Detect design patterns from directory structure."""
    patterns = []

    # Check for repository pattern
    repo_patterns = ["*[Rr]epository*.py", "*[Rr]epository*.ts", "*[Rr]epository*.cs"]
    if any(any(self.codebase_path.rglob(pattern)) for pattern in repo_patterns):
        patterns.append("Repository")

    # Check for factory pattern
    factory_patterns = ["*[Ff]actory*.py", "*[Ff]actory*.ts", "*[Ff]actory*.cs"]
    if any(any(self.codebase_path.rglob(pattern)) for pattern in factory_patterns):
        patterns.append("Factory")

    # Check for service layer pattern
    service_patterns = ["*[Ss]ervice*.py", "*[Ss]ervice*.ts", "*[Ss]ervice*.cs"]
    if any(any(self.codebase_path.rglob(pattern)) for pattern in service_patterns):
        patterns.append("Service Layer")

    return patterns
```

**Pattern Mappings** (`path_resolver.py:34-50`) defines 14 patterns but detection code only covers 3.

## Files to Modify

| File | Lines | Change |
|------|-------|--------|
| `installer/core/lib/codebase_analyzer/agent_invoker.py` | 418-438 | Add detection for all 14 patterns |
| `installer/core/lib/codebase_analyzer/prompt_builder.py` | 240-241 | Update AI prompt with pattern examples |
| `tests/lib/codebase_analyzer/test_pattern_detection.py` | NEW | Add comprehensive pattern tests |

## Implementation Specification

### Step 1: Refactor Pattern Detection (agent_invoker.py)

**Replace lines 418-438 with:**

```python
# Pattern definitions with file glob patterns
PATTERN_DETECTION_CONFIG = {
    'Repository': {
        'patterns': ["*[Rr]epository*.py", "*[Rr]epository*.ts", "*[Rr]epository*.cs", "*[Rr]epository*.java"],
        'description': "Data access abstraction layer"
    },
    'Factory': {
        'patterns': ["*[Ff]actory*.py", "*[Ff]actory*.ts", "*[Ff]actory*.cs", "*[Ff]actory*.java"],
        'description': "Object creation patterns"
    },
    'Service Layer': {
        'patterns': ["*[Ss]ervice*.py", "*[Ss]ervice*.ts", "*[Ss]ervice*.cs", "*[Ss]ervice*.java"],
        'description': "Business logic services"
    },
    'Engine': {
        'patterns': ["*[Ee]ngine*.py", "*[Ee]ngine*.ts", "*[Ee]ngine*.cs", "*[Ee]ngine*.java"],
        'description': "Business logic orchestration"
    },
    'MVVM': {
        'patterns': ["*[Vv]iew[Mm]odel*.py", "*[Vv]iew[Mm]odel*.ts", "*[Vv]iew[Mm]odel*.cs", "*[Vv]iew[Mm]odel*.dart"],
        'description': "Model-View-ViewModel pattern"
    },
    'Railway-Oriented Programming': {
        'patterns': ["*[Ee]rror[Oo]r*.cs", "*[Rr]esult*.cs", "*[Rr]ailway*.py", "*[Ee]ither*.ts"],
        'description': "Functional error handling"
    },
    'Entity': {
        'patterns': ["*[Ee]ntity*.py", "*[Ee]ntity*.cs", "*[Ee]ntity*.java"],
        'description': "Domain entities"
    },
    'Model': {
        'patterns': ["*/models/*.py", "*/models/*.ts", "*/model/*.cs"],
        'description': "Data models"
    },
    'Controller': {
        'patterns': ["*[Cc]ontroller*.py", "*[Cc]ontroller*.ts", "*[Cc]ontroller*.cs", "*[Cc]ontroller*.java"],
        'description': "Request handlers (MVC)"
    },
    'Handler': {
        'patterns': ["*[Hh]andler*.py", "*[Hh]andler*.ts", "*[Hh]andler*.cs"],
        'description': "Event/command handlers"
    },
    'Validator': {
        'patterns': ["*[Vv]alidator*.py", "*[Vv]alidator*.ts", "*[Vv]alidator*.cs"],
        'description': "Input validation"
    },
    'Mapper': {
        'patterns': ["*[Mm]apper*.py", "*[Mm]apper*.ts", "*[Mm]apper*.cs"],
        'description': "Object mapping/transformation"
    },
    'Builder': {
        'patterns': ["*[Bb]uilder*.py", "*[Bb]uilder*.ts", "*[Bb]uilder*.cs"],
        'description': "Complex object construction"
    },
    'View': {
        'patterns': ["*/views/*.py", "*/views/*.ts", "*[Vv]iew.cs", "*[Vv]iew.xaml"],
        'description': "UI views/templates"
    }
}


def _detect_patterns(self) -> list:
    """
    Detect design patterns from directory structure and file naming.

    Returns:
        List of detected pattern names

    Note:
        This is a heuristic fallback when AI analysis is unavailable.
        It scans the codebase for files matching known pattern conventions.
    """
    detected_patterns = []

    for pattern_name, config in PATTERN_DETECTION_CONFIG.items():
        file_patterns = config['patterns']

        # Check if any files match the pattern
        for file_pattern in file_patterns:
            try:
                matches = list(self.codebase_path.rglob(file_pattern))
                if matches:
                    detected_patterns.append(pattern_name)
                    self._log_debug(f"Detected {pattern_name} pattern: {len(matches)} files")
                    break  # Found pattern, no need to check other file patterns
            except Exception as e:
                self._log_debug(f"Error checking pattern {file_pattern}: {e}")

    return detected_patterns
```

### Step 2: Update AI Prompt (prompt_builder.py:240-241)

**Before:**
```python
"architecture": {
    "patterns": ["Repository", "Factory", "..."],
```

**After:**
```python
"architecture": {
    "patterns": [
        "Repository",      # Data access abstraction
        "Factory",         # Object creation
        "Service Layer",   # Business logic services
        "Engine",          # Business logic orchestration
        "MVVM",            # Model-View-ViewModel
        "Railway-Oriented Programming",  # ErrorOr<T>, Result<T>
        "Entity",          # Domain entities
        "Controller",      # Request handlers (MVC)
        "Handler",         # Event/command handlers
        "Validator",       # Input validation
        "Mapper",          # Object transformation (AutoMapper, Mapperly)
        "Builder"          # Complex object construction
    ],
```

### Step 3: Add Comprehensive Tests

```python
# tests/lib/codebase_analyzer/test_pattern_detection.py

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from installer.core.lib.codebase_analyzer.agent_invoker import HeuristicAnalyzer


class TestPatternDetection:
    """Tests for design pattern detection."""

    @pytest.fixture
    def analyzer(self, tmp_path):
        """Create analyzer with temp directory."""
        return HeuristicAnalyzer(codebase_path=tmp_path)

    def test_detect_repository_pattern(self, analyzer, tmp_path):
        """Test Repository pattern detection."""
        (tmp_path / "UserRepository.cs").touch()
        patterns = analyzer._detect_patterns()
        assert "Repository" in patterns

    def test_detect_factory_pattern(self, analyzer, tmp_path):
        """Test Factory pattern detection."""
        (tmp_path / "OrderFactory.py").touch()
        patterns = analyzer._detect_patterns()
        assert "Factory" in patterns

    def test_detect_service_pattern(self, analyzer, tmp_path):
        """Test Service Layer pattern detection."""
        (tmp_path / "PaymentService.ts").touch()
        patterns = analyzer._detect_patterns()
        assert "Service Layer" in patterns

    def test_detect_engine_pattern(self, analyzer, tmp_path):
        """Test Engine pattern detection."""
        (tmp_path / "LoadingEngine.cs").touch()
        patterns = analyzer._detect_patterns()
        assert "Engine" in patterns

    def test_detect_mvvm_pattern(self, analyzer, tmp_path):
        """Test MVVM pattern detection."""
        (tmp_path / "OrderViewModel.cs").touch()
        patterns = analyzer._detect_patterns()
        assert "MVVM" in patterns

    def test_detect_erroror_pattern(self, analyzer, tmp_path):
        """Test Railway-Oriented Programming pattern detection."""
        (tmp_path / "ErrorOr.cs").touch()
        patterns = analyzer._detect_patterns()
        assert "Railway-Oriented Programming" in patterns

    def test_detect_controller_pattern(self, analyzer, tmp_path):
        """Test Controller pattern detection."""
        (tmp_path / "UsersController.cs").touch()
        patterns = analyzer._detect_patterns()
        assert "Controller" in patterns

    def test_detect_handler_pattern(self, analyzer, tmp_path):
        """Test Handler pattern detection."""
        (tmp_path / "CreateOrderHandler.py").touch()
        patterns = analyzer._detect_patterns()
        assert "Handler" in patterns

    def test_detect_validator_pattern(self, analyzer, tmp_path):
        """Test Validator pattern detection."""
        (tmp_path / "EmailValidator.cs").touch()
        patterns = analyzer._detect_patterns()
        assert "Validator" in patterns

    def test_detect_mapper_pattern(self, analyzer, tmp_path):
        """Test Mapper pattern detection."""
        (tmp_path / "UserMapper.cs").touch()
        patterns = analyzer._detect_patterns()
        assert "Mapper" in patterns

    def test_detect_multiple_patterns(self, analyzer, tmp_path):
        """Test detection of multiple patterns in one codebase."""
        (tmp_path / "UserRepository.cs").touch()
        (tmp_path / "OrderService.cs").touch()
        (tmp_path / "ProductViewModel.cs").touch()
        (tmp_path / "ConfigurationMapper.cs").touch()

        patterns = analyzer._detect_patterns()

        assert "Repository" in patterns
        assert "Service Layer" in patterns
        assert "MVVM" in patterns
        assert "Mapper" in patterns
        assert len(patterns) >= 4

    def test_no_patterns_in_empty_directory(self, analyzer):
        """Test that empty directory returns no patterns."""
        patterns = analyzer._detect_patterns()
        assert patterns == []

    def test_case_insensitive_detection(self, analyzer, tmp_path):
        """Test that detection is case-insensitive."""
        (tmp_path / "userrepository.cs").touch()  # lowercase
        patterns = analyzer._detect_patterns()
        assert "Repository" in patterns

    def test_dotnet_maui_project_patterns(self, analyzer, tmp_path):
        """Integration test: Detect patterns in .NET MAUI style project."""
        # Create typical MAUI project structure
        (tmp_path / "ViewModels").mkdir()
        (tmp_path / "ViewModels" / "MainViewModel.cs").touch()
        (tmp_path / "ViewModels" / "SettingsViewModel.cs").touch()

        (tmp_path / "Services").mkdir()
        (tmp_path / "Services" / "ApiService.cs").touch()
        (tmp_path / "Services" / "NavigationService.cs").touch()

        (tmp_path / "Repositories").mkdir()
        (tmp_path / "Repositories" / "UserRepository.cs").touch()

        (tmp_path / "Engines").mkdir()
        (tmp_path / "Engines" / "LoadingEngine.cs").touch()

        (tmp_path / "Mappers").mkdir()
        (tmp_path / "Mappers" / "UserMapper.cs").touch()

        patterns = analyzer._detect_patterns()

        expected = ["MVVM", "Service Layer", "Repository", "Engine", "Mapper"]
        for pattern in expected:
            assert pattern in patterns, f"Expected {pattern} to be detected"
```

## Acceptance Criteria

- [x] All 14 patterns in PATTERN_MAPPINGS are detected
- [x] Railway-Oriented Programming (ErrorOr) pattern added and detected
- [x] MVVM pattern detected for .NET MAUI projects
- [x] Engine pattern detected for business logic layers
- [x] AI prompt updated with comprehensive pattern list
- [x] Patterns appear correctly in manifest.json
- [x] Detection is case-insensitive
- [x] All tests pass (22/22 passing)

## Test Requirements

```bash
# Run pattern detection tests
pytest tests/lib/codebase_analyzer/test_pattern_detection.py -v

# Integration test with real codebase
python3 -c "
from pathlib import Path
from installer.core.lib.codebase_analyzer.agent_invoker import HeuristicAnalyzer

# Test against mydrive template
analyzer = HeuristicAnalyzer(
    codebase_path=Path('docs/reviews/progressive-disclosure/mydrive')
)
patterns = analyzer._detect_patterns()
print('Detected patterns:', patterns)

# Verify critical patterns for MAUI
expected = ['Repository', 'Service Layer', 'MVVM', 'Engine', 'Mapper']
for p in expected:
    status = '✅' if p in patterns else '❌'
    print(f'{status} {p}')
"
```

## Regression Prevention

**Potential Regressions:**
1. Performance impact from scanning more file patterns
2. False positives from overly broad patterns

**Mitigation:**
- Use `break` after first match per pattern (avoid redundant scanning)
- Keep patterns specific (e.g., `*ViewModel*.cs` not `*Model*.cs`)
- Add logging for pattern detection debugging
- Cache results if called multiple times

## Notes

- **High priority** - improves template quality significantly
- Consider adding confidence scores (e.g., 5+ files = high confidence)
- The `PATTERN_DETECTION_CONFIG` structure allows easy extension
- Future: Consider detecting architectural patterns (Clean Architecture, Hexagonal)

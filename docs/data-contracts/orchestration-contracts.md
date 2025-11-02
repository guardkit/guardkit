# Orchestration Data Contracts

**Category**: Command Orchestration & Results
**Version**: 1.0.0
**Status**: ✅ COMPLETE

---

## Overview

Orchestration contracts define result types, validation structures, and abstractions used by command orchestrators (TASK-010, TASK-011) and validators.

---

## ValidationResult

**Purpose**: Standard validation result structure
**Used By**: All validators
**Schema Version**: 1.0.0

### Structure

```python
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class ValidationResult:
    """Result of data contract validation"""

    is_valid: bool
    errors: List[str]
    warnings: List[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.metadata is None:
            self.metadata = {}
```

### Usage Example

```python
class MyValidator(Validator):
    def validate(self, data: MyData) -> ValidationResult:
        errors = []
        warnings = []

        # Validation logic
        if not data.required_field:
            errors.append("required_field is missing")

        if data.optional_field and len(data.optional_field) < 3:
            warnings.append("optional_field is very short")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            metadata={"validator": "MyValidator"}
        )
```

---

## TemplateCreateResult

**Source**: TASK-010 (/template-create Command)
**Schema Version**: 1.0.0

### Structure

```python
@dataclass
class TemplateCreateResult:
    """Result of /template-create command"""

    schema_version: str = "1.0.0"

    # Success/failure
    success: bool
    template_name: str

    # Generated artifacts
    template_path: Path
    manifest_path: Path
    settings_path: Path
    claude_md_path: Path
    agents_dir: Path
    templates_dir: Path

    # Metadata
    agent_count: int = 0
    template_file_count: int = 0
    created_at: str = ""  # ISO 8601
    duration_seconds: float = 0.0

    # Error information
    error: Optional[str] = None
    error_phase: Optional[str] = None  # "qa" | "analysis" | "generation" | "save"
```

### Example JSON

```json
{
  "schema_version": "1.0.0",
  "success": true,
  "template_name": "mycompany-maui-mvvm",
  "template_path": "/path/to/installer/local/templates/mycompany-maui-mvvm",
  "manifest_path": "/path/to/installer/local/templates/mycompany-maui-mvvm/manifest.json",
  "settings_path": "/path/to/installer/local/templates/mycompany-maui-mvvm/settings.json",
  "claude_md_path": "/path/to/installer/local/templates/mycompany-maui-mvvm/CLAUDE.md",
  "agents_dir": "/path/to/installer/local/templates/mycompany-maui-mvvm/agents",
  "templates_dir": "/path/to/installer/local/templates/mycompany-maui-mvvm/templates",
  "agent_count": 8,
  "template_file_count": 12,
  "created_at": "2025-11-01T16:30:00Z",
  "duration_seconds": 145.3,
  "error": null,
  "error_phase": null
}
```

### Usage Example

```python
# From TASK-010 orchestrator
from template_create.command import TemplateCreateCommand

command = TemplateCreateCommand()
result: TemplateCreateResult = command.execute()

if result.success:
    print(f"✅ Template created: {result.template_name}")
    print(f"   Location: {result.template_path}")
    print(f"   Agents: {result.agent_count}")
    print(f"   Templates: {result.template_file_count}")
    print(f"   Duration: {result.duration_seconds:.1f}s")
else:
    print(f"❌ Template creation failed")
    print(f"   Error: {result.error}")
    print(f"   Phase: {result.error_phase}")
```

---

## TemplateInitResult

**Source**: TASK-011 (/template-init Command)
**Schema Version**: 1.0.0

### Structure

```python
@dataclass
class TemplateInitResult:
    """Result of /template-init command (greenfield)"""

    schema_version: str = "1.0.0"

    # Success/failure
    success: bool
    template_name: str

    # Generated artifacts (same as TemplateCreateResult)
    template_path: Path
    manifest_path: Path
    settings_path: Path
    claude_md_path: Path
    agents_dir: Path
    templates_dir: Path

    # Metadata
    agent_count: int = 0
    template_file_count: int = 0
    created_at: str = ""  # ISO 8601
    duration_seconds: float = 0.0

    # Greenfield-specific
    inferred_from_qa: bool = True  # vs analyzed from code

    # Error information
    error: Optional[str] = None
    error_phase: Optional[str] = None  # "qa" | "generation" | "agents" | "save"
```

### Example JSON

```json
{
  "schema_version": "1.0.0",
  "success": true,
  "template_name": "mycompany-new-template",
  "template_path": "/path/to/installer/local/templates/mycompany-new-template",
  "agent_count": 7,
  "template_file_count": 8,
  "created_at": "2025-11-01T16:45:00Z",
  "duration_seconds": 98.7,
  "inferred_from_qa": true,
  "error": null
}
```

---

## AnalysisProvider (Abstract Interface)

**Purpose**: Unified interface for brownfield and greenfield analysis
**Used By**: TASK-005, TASK-006, TASK-007, TASK-008
**Schema Version**: 1.0.0

### Structure

```python
from abc import ABC, abstractmethod

class AnalysisProvider(ABC):
    """
    Abstract interface for providing CodebaseAnalysis

    This allows generators (TASK-005-008) to work with both:
    - Brownfield: Real AI analysis from existing code
    - Greenfield: Inferred analysis from Q&A answers
    """

    @abstractmethod
    def get_analysis(self) -> CodebaseAnalysis:
        """
        Get CodebaseAnalysis

        Returns:
            CodebaseAnalysis suitable for template generation
        """
        pass

    @abstractmethod
    def get_source_type(self) -> str:
        """
        Get source type

        Returns:
            "brownfield" | "greenfield"
        """
        pass
```

### Brownfield Implementation

```python
class BrownfieldAnalysisProvider(AnalysisProvider):
    """Provide analysis from actual codebase (brownfield)"""

    def __init__(self, analysis: CodebaseAnalysis):
        self.analysis = analysis

    def get_analysis(self) -> CodebaseAnalysis:
        """Return AI-analyzed codebase"""
        return self.analysis

    def get_source_type(self) -> str:
        return "brownfield"
```

### Greenfield Implementation

```python
class GreenfieldAnalysisProvider(AnalysisProvider):
    """Provide analysis inferred from Q&A (greenfield)"""

    def __init__(self, answers: GreenfieldAnswers):
        self.answers = answers
        self._analysis: Optional[CodebaseAnalysis] = None

    def get_analysis(self) -> CodebaseAnalysis:
        """Convert GreenfieldAnswers to CodebaseAnalysis"""
        if self._analysis is None:
            adapter = GreenfieldAnalysisAdapter()
            self._analysis = adapter.adapt(self.answers)

        return self._analysis

    def get_source_type(self) -> str:
        return "greenfield"
```

### Usage in Generators

```python
# Generators work with AnalysisProvider interface
class ManifestGenerator:
    def __init__(self, provider: AnalysisProvider):
        self.provider = provider

    def generate(self) -> TemplateManifest:
        """Generate manifest from any analysis source"""
        analysis = self.provider.get_analysis()

        # Same generation logic for brownfield or greenfield
        return TemplateManifest(
            name=analysis.template_name,
            language=analysis.technology.language,
            # ... rest of generation
        )

# Brownfield usage
brownfield_provider = BrownfieldAnalysisProvider(ai_analysis)
manifest_gen = ManifestGenerator(brownfield_provider)
manifest = manifest_gen.generate()

# Greenfield usage
greenfield_provider = GreenfieldAnalysisProvider(qa_answers)
manifest_gen = ManifestGenerator(greenfield_provider)
manifest = manifest_gen.generate()
```

---

## TemplateCreationError (Exception Hierarchy)

**Purpose**: Standard exception hierarchy for template creation
**Used By**: TASK-010, TASK-011

### Structure

```python
class TemplateCreationError(Exception):
    """Base exception for template creation errors"""
    def __init__(self, message: str, phase: Optional[str] = None):
        super().__init__(message)
        self.phase = phase

class QACancelledError(TemplateCreationError):
    """User cancelled Q&A session"""
    def __init__(self):
        super().__init__("Q&A session cancelled by user", phase="qa")

class AnalysisError(TemplateCreationError):
    """AI analysis failed"""
    def __init__(self, reason: str, retry_possible: bool = True):
        super().__init__(f"Analysis failed: {reason}", phase="analysis")
        self.retry_possible = retry_possible

class GenerationError(TemplateCreationError):
    """Template generation failed"""
    def __init__(self, component: str, reason: str):
        super().__init__(f"{component} generation failed: {reason}", phase="generation")
        self.component = component

class SaveError(TemplateCreationError):
    """Save to disk failed"""
    def __init__(self, path: Path, reason: str):
        super().__init__(f"Failed to save {path}: {reason}", phase="save")
        self.path = path

class ValidationError(TemplateCreationError):
    """Validation failed"""
    def __init__(self, errors: List[str]):
        super().__init__(f"Validation failed: {', '.join(errors)}", phase="validation")
        self.errors = errors
```

### Usage Example

```python
# In TASK-010 orchestrator
try:
    # Phase 1: Q&A
    answers = self._run_qa_session()
    if not answers:
        raise QACancelledError()

    # Phase 2: Analysis
    analysis = self._run_analysis(answers)

    # Phase 3: Generation
    manifest = self._generate_manifest(analysis)

    # Phase 4: Save
    self._save_template(manifest)

except QACancelledError:
    return TemplateCreateResult(
        success=False,
        error="User cancelled Q&A",
        error_phase="qa"
    )

except AnalysisError as e:
    if e.retry_possible:
        # Retry logic
        pass
    return TemplateCreateResult(
        success=False,
        error=str(e),
        error_phase="analysis"
    )

except GenerationError as e:
    return TemplateCreateResult(
        success=False,
        error=f"{e.component}: {str(e)}",
        error_phase="generation"
    )

except Exception as e:
    return TemplateCreateResult(
        success=False,
        error=str(e),
        error_phase="unknown"
    )
```

---

## OperationResult (Generic Result Type)

**Purpose**: Generic Result type for operations
**Pattern**: Result<T, E> (Railway-Oriented Programming)

### Structure

```python
from typing import TypeVar, Generic, Union, Callable
from dataclasses import dataclass

T = TypeVar('T')  # Success type
E = TypeVar('E')  # Error type

@dataclass
class Success(Generic[T]):
    """Successful result"""
    value: T

    def is_success(self) -> bool:
        return True

    def is_error(self) -> bool:
        return False

@dataclass
class Error(Generic[E]):
    """Error result"""
    error: E

    def is_success(self) -> bool:
        return False

    def is_error(self) -> bool:
        return True

# Union type
Result = Union[Success[T], Error[E]]

# Helper constructors
class ResultFactory:
    @staticmethod
    def success(value: T) -> Success[T]:
        return Success(value)

    @staticmethod
    def error(error: E) -> Error[E]:
        return Error(error)
```

### Usage Example

```python
def analyze_codebase(path: Path) -> Result[CodebaseAnalysis, AnalysisError]:
    """Analyze codebase, return Result"""
    try:
        # Analysis logic
        analysis = perform_analysis(path)

        # Validate
        validator = CodebaseAnalysisValidator()
        result = validator.validate(analysis)

        if not result.is_valid:
            return ResultFactory.error(
                AnalysisError(f"Invalid analysis: {result.errors}")
            )

        return ResultFactory.success(analysis)

    except Exception as e:
        return ResultFactory.error(
            AnalysisError(str(e), retry_possible=False)
        )

# Usage
result = analyze_codebase(project_path)

if result.is_success():
    analysis = result.value
    # Continue with analysis
else:
    error = result.error
    if error.retry_possible:
        # Retry
        pass
    else:
        # Fail permanently
        pass
```

---

## Retry Strategy

**Purpose**: Retry logic for AI operations

### Structure

```python
from time import sleep
from typing import Callable, TypeVar

T = TypeVar('T')

class RetryStrategy:
    """Retry strategy for AI operations"""

    def __init__(self, max_attempts: int = 3, backoff_base: float = 2.0):
        self.max_attempts = max_attempts
        self.backoff_base = backoff_base

    def execute(
        self,
        operation: Callable[[], T],
        retryable_exceptions: tuple = (AnalysisError,)
    ) -> T:
        """
        Execute operation with retry logic

        Args:
            operation: Operation to execute
            retryable_exceptions: Exceptions to retry on

        Returns:
            Result of operation

        Raises:
            Last exception if all retries fail
        """
        last_exception = None

        for attempt in range(self.max_attempts):
            try:
                return operation()

            except retryable_exceptions as e:
                last_exception = e

                # Check if retryable
                if hasattr(e, 'retry_possible') and not e.retry_possible:
                    raise

                # Last attempt, don't sleep
                if attempt == self.max_attempts - 1:
                    break

                # Exponential backoff
                sleep_time = self.backoff_base ** attempt
                print(f"Retry {attempt + 1}/{self.max_attempts} after {sleep_time}s...")
                sleep(sleep_time)

        # All retries exhausted
        raise last_exception
```

### Usage Example

```python
retry = RetryStrategy(max_attempts=3)

try:
    analysis = retry.execute(
        lambda: analyze_codebase(path),
        retryable_exceptions=(AnalysisError,)
    )
except AnalysisError as e:
    print(f"Analysis failed after {retry.max_attempts} attempts: {e}")
```

---

## Testing

```python
# tests/test_orchestration_contracts.py

def test_validation_result():
    """Test ValidationResult"""
    # Valid
    valid = ValidationResult(is_valid=True, errors=[], warnings=[])
    assert valid.is_valid
    assert len(valid.errors) == 0

    # Invalid
    invalid = ValidationResult(
        is_valid=False,
        errors=["error1", "error2"],
        warnings=["warning1"]
    )
    assert not invalid.is_valid
    assert len(invalid.errors) == 2
    assert len(invalid.warnings) == 1

def test_template_create_result():
    """Test TemplateCreateResult"""
    # Success
    success = TemplateCreateResult(
        success=True,
        template_name="test",
        template_path=Path("/test"),
        manifest_path=Path("/test/manifest.json"),
        settings_path=Path("/test/settings.json"),
        claude_md_path=Path("/test/CLAUDE.md"),
        agents_dir=Path("/test/agents"),
        templates_dir=Path("/test/templates"),
        agent_count=5,
        template_file_count=10,
        duration_seconds=120.5
    )
    assert success.success
    assert success.agent_count == 5

    # Failure
    failure = TemplateCreateResult(
        success=False,
        template_name="test",
        error="Analysis failed",
        error_phase="analysis"
    )
    assert not failure.success
    assert failure.error_phase == "analysis"

def test_analysis_provider():
    """Test AnalysisProvider abstraction"""
    # Brownfield
    analysis = create_mock_codebase_analysis()
    brownfield = BrownfieldAnalysisProvider(analysis)
    assert brownfield.get_source_type() == "brownfield"
    assert brownfield.get_analysis() == analysis

    # Greenfield
    answers = create_mock_greenfield_answers()
    greenfield = GreenfieldAnalysisProvider(answers)
    assert greenfield.get_source_type() == "greenfield"

    greenfield_analysis = greenfield.get_analysis()
    assert greenfield_analysis.source == "greenfield"
    assert greenfield_analysis.template_name == answers.template_name

def test_result_type():
    """Test Result type"""
    # Success
    success = ResultFactory.success("value")
    assert success.is_success()
    assert not success.is_error()
    assert success.value == "value"

    # Error
    error = ResultFactory.error("error message")
    assert error.is_error()
    assert not error.is_success()
    assert error.error == "error message"

def test_retry_strategy():
    """Test RetryStrategy"""
    retry = RetryStrategy(max_attempts=3)

    # Success on first try
    call_count = 0
    def succeed_immediately():
        nonlocal call_count
        call_count += 1
        return "success"

    result = retry.execute(succeed_immediately)
    assert result == "success"
    assert call_count == 1

    # Success on retry
    call_count = 0
    def succeed_on_retry():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise AnalysisError("retry", retry_possible=True)
        return "success"

    result = retry.execute(succeed_on_retry)
    assert result == "success"
    assert call_count == 3

    # Permanent failure
    with pytest.raises(AnalysisError):
        retry.execute(
            lambda: (_ for _ in ()).throw(AnalysisError("fail", retry_possible=False))
        )
```

---

**Created**: 2025-11-01
**Status**: ✅ COMPLETE
**Completed**: All data contracts documentation (23 contracts across 5 files)

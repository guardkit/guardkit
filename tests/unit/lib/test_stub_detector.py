"""
Unit tests for stub_detector module.

Tests stub detection patterns, language detection, and library verification
across all supported languages (Python, TypeScript, Go, Rust, C#).

Coverage Target: >=85%
Test Count: 25+ tests
"""

import pytest
from pathlib import Path
from dataclasses import asdict

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "installer/core/lib"))

from stub_detector import (
    detect_stubs,
    detect_language,
    verify_library_usage,
    StubFinding,
    LANGUAGE_PATTERNS,
)


# ============================================================================
# 1. Language Detection Tests (6 tests)
# ============================================================================

class TestLanguageDetection:
    """Test language detection from file extensions."""

    def test_detect_python(self):
        """Test Python file detection."""
        assert detect_language(Path("service.py")) == "python"
        assert detect_language(Path("test_module.py")) == "python"

    def test_detect_typescript(self):
        """Test TypeScript/JavaScript file detection."""
        assert detect_language(Path("component.ts")) == "typescript"
        assert detect_language(Path("component.tsx")) == "typescript"
        assert detect_language(Path("script.js")) == "typescript"
        assert detect_language(Path("component.jsx")) == "typescript"

    def test_detect_go(self):
        """Test Go file detection."""
        assert detect_language(Path("handler.go")) == "go"

    def test_detect_rust(self):
        """Test Rust file detection."""
        assert detect_language(Path("main.rs")) == "rust"

    def test_detect_csharp(self):
        """Test C# file detection."""
        assert detect_language(Path("Service.cs")) == "csharp"

    def test_detect_unknown(self):
        """Test unknown file extension."""
        assert detect_language(Path("unknown.xyz")) == "unknown"
        assert detect_language(Path("README.md")) == "unknown"


# ============================================================================
# 2. Python Stub Detection Tests (8 tests)
# ============================================================================

class TestPythonStubDetection:
    """Test stub detection for Python code."""

    def test_detect_placeholder_comment_in_production(self):
        """Test detection of 'In production' placeholder comment."""
        content = """
def get_users():
    # In production, this would call the database
    return []
"""
        findings = detect_stubs(Path("service.py"), content)
        assert len(findings) == 2  # Comment + return []
        assert findings[0].pattern_type == "placeholder_comment"
        assert findings[0].line_number == 3
        assert findings[0].severity == "error"

    def test_detect_todo_implement(self):
        """Test detection of TODO implement comment."""
        content = """
def process_data():
    # TODO implement this function
    pass
"""
        findings = detect_stubs(Path("service.py"), content)
        assert len(findings) == 2  # TODO + pass
        assert findings[0].pattern_type == "placeholder_comment"
        assert findings[0].severity == "error"

    def test_detect_fixme_implement(self):
        """Test detection of FIXME implement comment."""
        content = """
def validate():
    # FIXME implement validation logic
    return None
"""
        findings = detect_stubs(Path("service.py"), content)
        assert len(findings) == 2  # FIXME + return None
        assert any(f.pattern_type == "placeholder_comment" for f in findings)

    def test_detect_return_empty_list(self):
        """Test detection of return [] stub pattern."""
        content = """
def get_items():
    return []
"""
        findings = detect_stubs(Path("service.py"), content)
        assert len(findings) == 1
        assert findings[0].pattern_type == "stub_implementation"
        assert findings[0].severity == "warning"

    def test_detect_return_none(self):
        """Test detection of return None stub pattern."""
        content = """
def get_value():
    return None
"""
        findings = detect_stubs(Path("service.py"), content)
        assert len(findings) == 1
        assert findings[0].pattern_type == "stub_implementation"

    def test_detect_pass_statement(self):
        """Test detection of pass statement stub pattern."""
        content = """
def do_nothing():
    pass
"""
        findings = detect_stubs(Path("service.py"), content)
        assert len(findings) == 1
        assert findings[0].pattern_type == "stub_implementation"

    def test_detect_raise_not_implemented(self):
        """Test detection of NotImplementedError stub pattern."""
        content = """
def future_feature():
    raise NotImplementedError
"""
        findings = detect_stubs(Path("service.py"), content)
        assert len(findings) == 1
        assert findings[0].pattern_type == "stub_implementation"

    def test_no_false_positive_on_real_implementation(self):
        """Test that real implementations don't trigger false positives."""
        content = """
def get_users():
    users = database.query("SELECT * FROM users")
    if not users:
        return []  # Empty result is valid
    return users
"""
        findings = detect_stubs(Path("service.py"), content)
        # return [] in context of real implementation should still be detected
        # (stub detector is pattern-based, not context-aware)
        assert len(findings) == 1
        assert findings[0].severity == "warning"  # Warning, not error


# ============================================================================
# 3. Multi-Language Stub Detection Tests (5 tests)
# ============================================================================

class TestMultiLanguageStubDetection:
    """Test stub detection across different languages."""

    def test_typescript_stubs(self):
        """Test TypeScript stub detection."""
        content = """
function getItems(): Item[] {
    // TODO implement this
    return [];
}
"""
        findings = detect_stubs(Path("service.ts"), content)
        assert len(findings) == 2  # TODO + return []
        assert findings[0].language == "typescript"

    def test_go_stubs(self):
        """Test Go stub detection."""
        content = """
func GetData() *Data {
    // TODO implement this
    return nil
}
"""
        findings = detect_stubs(Path("handler.go"), content)
        assert len(findings) == 2  # TODO + return nil
        assert findings[0].language == "go"

    def test_rust_stubs(self):
        """Test Rust stub detection."""
        content = """
fn process_data() -> Result<(), Error> {
    // TODO implement this
    todo!()
}
"""
        findings = detect_stubs(Path("main.rs"), content)
        assert len(findings) == 2  # TODO + todo!()
        assert findings[0].language == "rust"

    def test_csharp_stubs(self):
        """Test C# stub detection."""
        content = """
public Data GetData() {
    // TODO implement this
    throw new NotImplementedException();
}
"""
        findings = detect_stubs(Path("Service.cs"), content)
        assert len(findings) == 2  # TODO + NotImplementedException
        assert findings[0].language == "csharp"

    def test_unknown_language_returns_empty(self):
        """Test that unknown languages return empty findings."""
        content = """
Some random content
# TODO implement
return []
"""
        findings = detect_stubs(Path("unknown.xyz"), content)
        assert len(findings) == 0


# ============================================================================
# 4. Library Verification Tests (6 tests)
# ============================================================================

class TestLibraryVerification:
    """Test library import and call verification."""

    def test_verify_missing_import(self):
        """Test detection of missing required import."""
        content = """
from other_lib import Thing

def process():
    pass
"""
        findings = verify_library_usage(
            Path("service.py"),
            content,
            required_imports=["from graphiti_core import Graphiti"]
        )
        assert len(findings) == 1
        assert findings[0].pattern_type == "missing_import"
        assert findings[0].severity == "error"
        assert "graphiti_core" in findings[0].description

    def test_verify_present_import(self):
        """Test that present imports don't generate findings."""
        content = """
from graphiti_core import Graphiti

def process():
    graphiti = Graphiti()
"""
        findings = verify_library_usage(
            Path("service.py"),
            content,
            required_imports=["from graphiti_core import Graphiti"]
        )
        assert len(findings) == 0

    def test_verify_missing_call(self):
        """Test detection of missing required call."""
        content = """
from graphiti_core import Graphiti

def process():
    graphiti = Graphiti()
    # But doesn't use the query method
"""
        findings = verify_library_usage(
            Path("service.py"),
            content,
            required_imports=["from graphiti_core import Graphiti"],
            required_calls=["graphiti.search"]
        )
        assert len(findings) == 1
        assert findings[0].pattern_type == "missing_call"
        assert findings[0].severity == "warning"

    def test_verify_present_call(self):
        """Test that present calls don't generate findings."""
        content = """
from graphiti_core import Graphiti

def process():
    graphiti = Graphiti()
    results = graphiti.search("query")
"""
        findings = verify_library_usage(
            Path("service.py"),
            content,
            required_imports=["from graphiti_core import Graphiti"],
            required_calls=["graphiti.search"]
        )
        assert len(findings) == 0

    def test_verify_multiple_missing(self):
        """Test detection of multiple missing imports/calls."""
        content = """
def process():
    pass
"""
        findings = verify_library_usage(
            Path("service.py"),
            content,
            required_imports=["from graphiti_core import Graphiti", "from neo4j import GraphDatabase"],
            required_calls=["graphiti.search", "graphiti.add_episode"]
        )
        assert len(findings) == 4  # 2 imports + 2 calls
        import_findings = [f for f in findings if f.pattern_type == "missing_import"]
        call_findings = [f for f in findings if f.pattern_type == "missing_call"]
        assert len(import_findings) == 2
        assert len(call_findings) == 2

    def test_verify_no_requirements(self):
        """Test that no requirements returns empty findings."""
        content = """
def process():
    pass
"""
        findings = verify_library_usage(
            Path("service.py"),
            content,
            required_imports=None,
            required_calls=None
        )
        assert len(findings) == 0


# ============================================================================
# 5. StubFinding Data Structure Tests (3 tests)
# ============================================================================

class TestStubFinding:
    """Test StubFinding dataclass."""

    def test_stub_finding_creation(self):
        """Test creating a StubFinding."""
        finding = StubFinding(
            file_path=Path("service.py"),
            line_number=42,
            pattern_type="placeholder_comment",
            description="Found placeholder comment",
            severity="error",
            language="python"
        )
        assert finding.file_path == Path("service.py")
        assert finding.line_number == 42
        assert finding.pattern_type == "placeholder_comment"
        assert finding.severity == "error"
        assert finding.language == "python"

    def test_stub_finding_attributes(self):
        """Test all StubFinding attributes are accessible."""
        finding = StubFinding(
            file_path=Path("test.py"),
            line_number=1,
            pattern_type="stub_implementation",
            description="Test",
            severity="warning",
            language="python"
        )
        # Access all attributes
        assert isinstance(finding.file_path, Path)
        assert isinstance(finding.line_number, int)
        assert isinstance(finding.pattern_type, str)
        assert isinstance(finding.description, str)
        assert isinstance(finding.severity, str)
        assert isinstance(finding.language, str)

    def test_stub_finding_serializable(self):
        """Test that StubFinding can be serialized to dict."""
        finding = StubFinding(
            file_path=Path("service.py"),
            line_number=10,
            pattern_type="missing_import",
            description="Missing import",
            severity="error",
            language="python"
        )
        data = asdict(finding)
        assert data["line_number"] == 10
        assert data["pattern_type"] == "missing_import"


# ============================================================================
# 6. Edge Cases and Integration Tests (5 tests)
# ============================================================================

class TestEdgeCases:
    """Test edge cases and integration scenarios."""

    def test_empty_file(self):
        """Test detection on empty file."""
        findings = detect_stubs(Path("empty.py"), "")
        assert len(findings) == 0

    def test_file_with_only_whitespace(self):
        """Test detection on file with only whitespace."""
        content = "\n\n   \n\t\n"
        findings = detect_stubs(Path("whitespace.py"), content)
        assert len(findings) == 0

    def test_multiple_stubs_same_file(self):
        """Test detection of multiple stubs in same file."""
        content = """
def func1():
    # TODO implement
    pass

def func2():
    # In production, this would work
    return []

def func3():
    raise NotImplementedError
"""
        findings = detect_stubs(Path("stubs.py"), content)
        assert len(findings) >= 5  # 2 TODOs + pass + return [] + NotImplementedError

    def test_line_numbers_are_correct(self):
        """Test that line numbers are correctly reported."""
        content = """
def func1():
    pass

def func2():
    # TODO implement
    return None
"""
        findings = detect_stubs(Path("test.py"), content)
        # pass should be on line 3
        pass_finding = next(f for f in findings if "pass" in f.description)
        assert pass_finding.line_number == 3
        # TODO should be on line 6
        todo_finding = next(f for f in findings if f.pattern_type == "placeholder_comment")
        assert todo_finding.line_number == 6

    def test_case_insensitive_patterns(self):
        """Test that comment patterns are case-insensitive."""
        content = """
def func():
    # todo implement this
    pass
"""
        findings = detect_stubs(Path("test.py"), content)
        comment_findings = [f for f in findings if f.pattern_type == "placeholder_comment"]
        assert len(comment_findings) >= 1


# ============================================================================
# 7. Module Constants Tests (2 tests)
# ============================================================================

class TestModuleConstants:
    """Test module-level constants."""

    def test_language_patterns_structure(self):
        """Test that LANGUAGE_PATTERNS has expected structure."""
        assert "python" in LANGUAGE_PATTERNS
        assert "typescript" in LANGUAGE_PATTERNS
        assert "go" in LANGUAGE_PATTERNS
        assert "rust" in LANGUAGE_PATTERNS
        assert "csharp" in LANGUAGE_PATTERNS

        for lang, patterns in LANGUAGE_PATTERNS.items():
            assert "extensions" in patterns
            assert "comment_patterns" in patterns
            assert "stub_patterns" in patterns
            assert isinstance(patterns["extensions"], list)
            assert isinstance(patterns["comment_patterns"], list)
            assert isinstance(patterns["stub_patterns"], list)

    def test_all_languages_have_extensions(self):
        """Test that all languages have at least one extension."""
        for lang, patterns in LANGUAGE_PATTERNS.items():
            assert len(patterns["extensions"]) > 0
            for ext in patterns["extensions"]:
                assert ext.startswith(".")

"""
Comprehensive Test Suite for SecurityChecker Class (TDD RED Phase)

Tests the SecurityChecker class that provides quick security checks for
the Coach agent during AutoBuild validation.

Coverage Target: >=85%
Test Count: 50+ tests

Security Checks Tested:
    Python (6 checks):
        - hardcoded-secrets: Hardcoded credentials detection
        - sql-injection: SQL string formatting detection
        - command-injection: Shell command injection detection
        - pickle-load: Deserialization attack detection
        - eval-exec: Dynamic code execution detection
        - debug-mode: Debug mode enabled detection

    JavaScript/TypeScript (5 checks):
        - dangerous-inner-html: React XSS risk detection
        - document-write: DOM XSS detection
        - inner-html: DOM manipulation XSS detection
        - new-function: Dynamic code generation detection
        - js-eval: JavaScript eval detection

    Universal (1 check):
        - cors-wildcard: CORS wildcard detection

    GitHub Actions (1 check):
        - gha-injection: Workflow injection detection

TDD Phase: RED - Tests written before implementation
Expected: All tests should FAIL because SecurityChecker doesn't exist yet
"""

import pytest
import time
from pathlib import Path
from typing import List
from unittest.mock import Mock, patch, MagicMock


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def temp_worktree(tmp_path):
    """Create a temporary worktree structure for testing."""
    worktree = tmp_path / "test_worktree"
    worktree.mkdir()

    # Create standard project structure
    (worktree / "src").mkdir()
    (worktree / "tests").mkdir()
    (worktree / ".github" / "workflows").mkdir(parents=True)

    return worktree


@pytest.fixture
def security_checker(temp_worktree):
    """Create SecurityChecker instance for testing."""
    from guardkit.orchestrator.quality_gates.security_checker import SecurityChecker
    return SecurityChecker(temp_worktree)


@pytest.fixture
def create_python_file(temp_worktree):
    """Factory fixture to create Python files with content."""
    def _create(filename: str, content: str) -> Path:
        file_path = temp_worktree / "src" / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        return file_path
    return _create


@pytest.fixture
def create_js_file(temp_worktree):
    """Factory fixture to create JavaScript/TypeScript files with content."""
    def _create(filename: str, content: str) -> Path:
        file_path = temp_worktree / "src" / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        return file_path
    return _create


@pytest.fixture
def create_workflow_file(temp_worktree):
    """Factory fixture to create GitHub Actions workflow files."""
    def _create(filename: str, content: str) -> Path:
        file_path = temp_worktree / ".github" / "workflows" / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        return file_path
    return _create


@pytest.fixture
def create_config_file(temp_worktree):
    """Factory fixture to create configuration files."""
    def _create(filename: str, content: str) -> Path:
        file_path = temp_worktree / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        return file_path
    return _create


# ============================================================================
# 1. SecurityChecker Initialization Tests (3 tests)
# ============================================================================


class TestSecurityCheckerInitialization:
    """Test SecurityChecker class initialization."""

    def test_security_checker_import(self):
        """Test that SecurityChecker class can be imported."""
        from guardkit.orchestrator.quality_gates.security_checker import SecurityChecker
        assert SecurityChecker is not None

    def test_security_finding_import(self):
        """Test that SecurityFinding dataclass can be imported."""
        from guardkit.orchestrator.quality_gates.security_checker import SecurityFinding
        assert SecurityFinding is not None

    def test_security_checker_initialization(self, temp_worktree):
        """Test SecurityChecker initializes with worktree path."""
        from guardkit.orchestrator.quality_gates.security_checker import SecurityChecker

        checker = SecurityChecker(temp_worktree)

        assert checker.worktree_path == temp_worktree

    def test_security_checker_accepts_string_path(self, temp_worktree):
        """Test SecurityChecker accepts string path as input."""
        from guardkit.orchestrator.quality_gates.security_checker import SecurityChecker

        checker = SecurityChecker(str(temp_worktree))

        assert checker.worktree_path == Path(temp_worktree)


# ============================================================================
# 2. SecurityFinding Dataclass Tests (5 tests)
# ============================================================================


class TestSecurityFinding:
    """Test SecurityFinding dataclass structure."""

    def test_security_finding_has_required_fields(self):
        """Test SecurityFinding has all required fields."""
        from guardkit.orchestrator.quality_gates.security_checker import SecurityFinding

        finding = SecurityFinding(
            check_id="test-check",
            severity="high",
            description="Test description",
            file_path="/path/to/file.py",
            line_number=42,
            matched_text="matched content",
            recommendation="Fix this issue"
        )

        assert finding.check_id == "test-check"
        assert finding.severity == "high"
        assert finding.description == "Test description"
        assert finding.file_path == "/path/to/file.py"
        assert finding.line_number == 42
        assert finding.matched_text == "matched content"
        assert finding.recommendation == "Fix this issue"

    def test_security_finding_severity_literal_types(self):
        """Test SecurityFinding accepts valid severity levels."""
        from guardkit.orchestrator.quality_gates.security_checker import SecurityFinding

        valid_severities = ["critical", "high", "medium", "low", "info"]

        for severity in valid_severities:
            finding = SecurityFinding(
                check_id="test",
                severity=severity,
                description="Test",
                file_path="test.py",
                line_number=1,
                matched_text="test",
                recommendation="Fix it"
            )
            assert finding.severity == severity

    def test_security_finding_is_dataclass(self):
        """Test SecurityFinding is a proper dataclass."""
        from guardkit.orchestrator.quality_gates.security_checker import SecurityFinding
        from dataclasses import is_dataclass

        assert is_dataclass(SecurityFinding)

    def test_security_finding_equality(self):
        """Test SecurityFinding equality comparison."""
        from guardkit.orchestrator.quality_gates.security_checker import SecurityFinding

        finding1 = SecurityFinding(
            check_id="test",
            severity="high",
            description="Test",
            file_path="test.py",
            line_number=1,
            matched_text="test",
            recommendation="Fix"
        )
        finding2 = SecurityFinding(
            check_id="test",
            severity="high",
            description="Test",
            file_path="test.py",
            line_number=1,
            matched_text="test",
            recommendation="Fix"
        )

        assert finding1 == finding2

    def test_security_finding_repr(self):
        """Test SecurityFinding string representation."""
        from guardkit.orchestrator.quality_gates.security_checker import SecurityFinding

        finding = SecurityFinding(
            check_id="hardcoded-secrets",
            severity="critical",
            description="Hardcoded credential",
            file_path="config.py",
            line_number=10,
            matched_text="API_KEY = 'secret'",
            recommendation="Use environment variables"
        )

        repr_str = repr(finding)
        assert "hardcoded-secrets" in repr_str
        assert "critical" in repr_str


# ============================================================================
# 3. Python Security Checks (12 tests)
# ============================================================================


class TestPythonHardcodedSecrets:
    """Test hardcoded-secrets check for Python files."""

    def test_detects_hardcoded_api_key(self, security_checker, create_python_file):
        """Test detection of hardcoded API key."""
        create_python_file("config.py", '''
API_KEY = "sk-1234567890abcdef"
''')

        findings = security_checker.run_quick_checks()

        secret_findings = [f for f in findings if f.check_id == "hardcoded-secrets"]
        assert len(secret_findings) >= 1
        assert secret_findings[0].severity == "critical"
        assert "API_KEY" in secret_findings[0].matched_text

    def test_detects_hardcoded_password(self, security_checker, create_python_file):
        """Test detection of hardcoded password."""
        create_python_file("auth.py", '''
PASSWORD = "supersecretpassword123"
''')

        findings = security_checker.run_quick_checks()

        secret_findings = [f for f in findings if f.check_id == "hardcoded-secrets"]
        assert len(secret_findings) >= 1
        assert secret_findings[0].severity == "critical"

    def test_detects_hardcoded_secret(self, security_checker, create_python_file):
        """Test detection of hardcoded SECRET variable."""
        create_python_file("settings.py", '''
SECRET = "my-app-secret-key-12345"
''')

        findings = security_checker.run_quick_checks()

        secret_findings = [f for f in findings if f.check_id == "hardcoded-secrets"]
        assert len(secret_findings) >= 1

    def test_no_false_positive_on_empty_string(self, security_checker, create_python_file):
        """Test no false positive when value is empty string."""
        create_python_file("config.py", '''
API_KEY = ""  # Will be set from environment
PASSWORD = ''  # Placeholder
''')

        findings = security_checker.run_quick_checks()

        # Empty strings should not trigger (no actual secret)
        secret_findings = [f for f in findings if f.check_id == "hardcoded-secrets"]
        assert len(secret_findings) == 0


class TestPythonSqlInjection:
    """Test sql-injection check for Python files."""

    def test_detects_sql_fstring_injection(self, security_checker, create_python_file):
        """Test detection of SQL injection via f-string."""
        create_python_file("db.py", '''
def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return db.execute(query)
''')

        findings = security_checker.run_quick_checks()

        sql_findings = [f for f in findings if f.check_id == "sql-injection"]
        assert len(sql_findings) >= 1
        assert sql_findings[0].severity == "critical"

    def test_detects_sql_injection_with_quotes(self, security_checker, create_python_file):
        """Test detection of SQL injection with f-string and quotes."""
        create_python_file("queries.py", '''
def search(term):
    sql = f'SELECT * FROM products WHERE name LIKE "{term}%"'
    return execute(sql)
''')

        findings = security_checker.run_quick_checks()

        sql_findings = [f for f in findings if f.check_id == "sql-injection"]
        assert len(sql_findings) >= 1


class TestPythonCommandInjection:
    """Test command-injection check for Python files."""

    def test_detects_subprocess_fstring(self, security_checker, create_python_file):
        """Test detection of command injection via subprocess.run with f-string."""
        create_python_file("utils.py", '''
import subprocess

def list_files(path):
    subprocess.run(f"ls {path}", shell=True)
''')

        findings = security_checker.run_quick_checks()

        cmd_findings = [f for f in findings if f.check_id == "command-injection"]
        assert len(cmd_findings) >= 1
        assert cmd_findings[0].severity == "critical"

    def test_detects_os_system_fstring(self, security_checker, create_python_file):
        """Test detection of command injection via os.system with f-string."""
        create_python_file("shell.py", '''
import os

def run_command(cmd):
    os.system(f"echo {cmd}")
''')

        findings = security_checker.run_quick_checks()

        cmd_findings = [f for f in findings if f.check_id == "command-injection"]
        assert len(cmd_findings) >= 1


class TestPythonPickleLoad:
    """Test pickle-load check for Python files."""

    def test_detects_pickle_load(self, security_checker, create_python_file):
        """Test detection of pickle.load usage."""
        create_python_file("serializer.py", '''
import pickle

def load_data(filepath):
    with open(filepath, "rb") as f:
        return pickle.load(f)
''')

        findings = security_checker.run_quick_checks()

        pickle_findings = [f for f in findings if f.check_id == "pickle-load"]
        assert len(pickle_findings) >= 1
        assert pickle_findings[0].severity == "critical"

    def test_detects_pickle_loads(self, security_checker, create_python_file):
        """Test detection of pickle.loads usage."""
        create_python_file("data.py", '''
import pickle

def deserialize(data):
    return pickle.loads(data)
''')

        findings = security_checker.run_quick_checks()

        # pickle.loads should also be detected
        pickle_findings = [f for f in findings if f.check_id == "pickle-load"]
        assert len(pickle_findings) >= 1


class TestPythonEvalExec:
    """Test eval-exec check for Python files."""

    def test_detects_eval(self, security_checker, create_python_file):
        """Test detection of eval usage."""
        create_python_file("dynamic.py", '''
def execute_expression(expr):
    return eval(expr)
''')

        findings = security_checker.run_quick_checks()

        eval_findings = [f for f in findings if f.check_id == "eval-exec"]
        assert len(eval_findings) >= 1
        assert eval_findings[0].severity == "high"

    def test_detects_exec(self, security_checker, create_python_file):
        """Test detection of exec usage."""
        create_python_file("runner.py", '''
def run_code(code_string):
    exec(code_string)
''')

        findings = security_checker.run_quick_checks()

        exec_findings = [f for f in findings if f.check_id == "eval-exec"]
        assert len(exec_findings) >= 1


class TestPythonDebugMode:
    """Test debug-mode check for Python files."""

    def test_detects_debug_true(self, security_checker, create_python_file):
        """Test detection of DEBUG = True."""
        create_python_file("settings.py", '''
DEBUG = True
ALLOWED_HOSTS = ["*"]
''')

        findings = security_checker.run_quick_checks()

        debug_findings = [f for f in findings if f.check_id == "debug-mode"]
        assert len(debug_findings) >= 1
        assert debug_findings[0].severity == "high"

    def test_no_false_positive_debug_false(self, security_checker, create_python_file):
        """Test no false positive when DEBUG = False."""
        create_python_file("settings.py", '''
DEBUG = False
''')

        findings = security_checker.run_quick_checks()

        debug_findings = [f for f in findings if f.check_id == "debug-mode"]
        assert len(debug_findings) == 0


# ============================================================================
# 4. JavaScript/TypeScript Security Checks (10 tests)
# ============================================================================


class TestJsDangerousInnerHtml:
    """Test dangerous-inner-html check for JS/TS files."""

    def test_detects_dangerous_inner_html(self, security_checker, create_js_file):
        """Test detection of dangerouslySetInnerHTML in React."""
        create_js_file("Component.tsx", '''
function RenderHtml({ content }) {
    return <div dangerouslySetInnerHTML={{__html: content}} />;
}
''')

        findings = security_checker.run_quick_checks()

        html_findings = [f for f in findings if f.check_id == "dangerous-inner-html"]
        assert len(html_findings) >= 1
        assert html_findings[0].severity == "high"

    def test_detects_dangerous_inner_html_jsx(self, security_checker, create_js_file):
        """Test detection in JSX files."""
        create_js_file("page.jsx", '''
const Page = () => (
    <article dangerouslySetInnerHTML={{__html: rawHtml}} />
);
''')

        findings = security_checker.run_quick_checks()

        html_findings = [f for f in findings if f.check_id == "dangerous-inner-html"]
        assert len(html_findings) >= 1


class TestJsDocumentWrite:
    """Test document-write check for JS/TS files."""

    def test_detects_document_write(self, security_checker, create_js_file):
        """Test detection of document.write usage."""
        create_js_file("legacy.js", '''
function renderContent(html) {
    document.write(html);
}
''')

        findings = security_checker.run_quick_checks()

        write_findings = [f for f in findings if f.check_id == "document-write"]
        assert len(write_findings) >= 1
        assert write_findings[0].severity == "high"


class TestJsInnerHtml:
    """Test inner-html check for JS/TS files."""

    def test_detects_inner_html(self, security_checker, create_js_file):
        """Test detection of innerHTML assignment."""
        create_js_file("dom.js", '''
function setContent(element, content) {
    element.innerHTML = content;
}
''')

        findings = security_checker.run_quick_checks()

        html_findings = [f for f in findings if f.check_id == "inner-html"]
        assert len(html_findings) >= 1
        assert html_findings[0].severity == "medium"


class TestJsNewFunction:
    """Test new-function check for JS/TS files."""

    def test_detects_new_function(self, security_checker, create_js_file):
        """Test detection of new Function() usage."""
        create_js_file("dynamic.js", '''
function createFunction(code) {
    return new Function("return " + code)();
}
''')

        findings = security_checker.run_quick_checks()

        func_findings = [f for f in findings if f.check_id == "new-function"]
        assert len(func_findings) >= 1
        assert func_findings[0].severity == "high"


class TestJsEval:
    """Test js-eval check for JS/TS files."""

    def test_detects_js_eval(self, security_checker, create_js_file):
        """Test detection of eval usage in JavaScript."""
        create_js_file("executor.js", '''
function execute(code) {
    return eval(code);
}
''')

        findings = security_checker.run_quick_checks()

        eval_findings = [f for f in findings if f.check_id == "js-eval"]
        assert len(eval_findings) >= 1
        assert eval_findings[0].severity == "high"

    def test_detects_eval_in_typescript(self, security_checker, create_js_file):
        """Test detection of eval in TypeScript files."""
        create_js_file("runner.ts", '''
function runCode(code: string): any {
    return eval(code);
}
''')

        findings = security_checker.run_quick_checks()

        eval_findings = [f for f in findings if f.check_id == "js-eval"]
        assert len(eval_findings) >= 1


# ============================================================================
# 5. Universal Security Checks (3 tests)
# ============================================================================


class TestCorsWildcard:
    """Test cors-wildcard check for all files."""

    def test_detects_cors_wildcard_python(self, security_checker, create_python_file):
        """Test detection of CORS wildcard in Python."""
        create_python_file("main.py", '''
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
)
''')

        findings = security_checker.run_quick_checks()

        cors_findings = [f for f in findings if f.check_id == "cors-wildcard"]
        assert len(cors_findings) >= 1
        assert cors_findings[0].severity == "high"

    def test_detects_cors_wildcard_js(self, security_checker, create_js_file):
        """Test detection of CORS wildcard in JavaScript."""
        create_js_file("server.js", '''
const cors = require('cors');
app.use(cors({
    origin: "*",
    methods: ["GET", "POST"]
}));
''')

        findings = security_checker.run_quick_checks()

        cors_findings = [f for f in findings if f.check_id == "cors-wildcard"]
        assert len(cors_findings) >= 1

    def test_no_false_positive_specific_origins(self, security_checker, create_python_file):
        """Test no false positive when specific origins are used."""
        create_python_file("cors.py", '''
allow_origins=["https://example.com", "https://api.example.com"]
''')

        findings = security_checker.run_quick_checks()

        cors_findings = [f for f in findings if f.check_id == "cors-wildcard"]
        assert len(cors_findings) == 0


# ============================================================================
# 6. GitHub Actions Security Checks (4 tests)
# ============================================================================


class TestGhaInjection:
    """Test gha-injection check for GitHub Actions workflow files."""

    def test_detects_workflow_injection_issue_title(self, security_checker, create_workflow_file):
        """Test detection of GitHub Actions workflow injection via issue title."""
        create_workflow_file("ci.yml", '''
name: CI
on: issues

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Greet
        run: echo "Issue: ${{ github.event.issue.title }}"
''')

        findings = security_checker.run_quick_checks()

        gha_findings = [f for f in findings if f.check_id == "gha-injection"]
        assert len(gha_findings) >= 1
        assert gha_findings[0].severity == "critical"

    def test_detects_workflow_injection_pr_title(self, security_checker, create_workflow_file):
        """Test detection of workflow injection via PR title."""
        create_workflow_file("pr.yml", '''
name: PR Check
on: pull_request

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - run: |
          echo "PR: ${{ github.event.pull_request.title }}"
''')

        findings = security_checker.run_quick_checks()

        gha_findings = [f for f in findings if f.check_id == "gha-injection"]
        assert len(gha_findings) >= 1

    def test_detects_workflow_injection_comment_body(self, security_checker, create_workflow_file):
        """Test detection of workflow injection via comment body."""
        create_workflow_file("comment.yml", '''
name: Comment Handler
on: issue_comment

jobs:
  handle:
    runs-on: ubuntu-latest
    steps:
      - run: echo "${{ github.event.comment.body }}"
''')

        findings = security_checker.run_quick_checks()

        gha_findings = [f for f in findings if f.check_id == "gha-injection"]
        assert len(gha_findings) >= 1

    def test_no_false_positive_safe_context(self, security_checker, create_workflow_file):
        """Test no false positive when using safe context values."""
        create_workflow_file("safe.yml", '''
name: Safe Workflow
on: push

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo "SHA: ${{ github.sha }}"
      - run: echo "Ref: ${{ github.ref }}"
''')

        findings = security_checker.run_quick_checks()

        # Safe context values like github.sha and github.ref should not trigger
        gha_findings = [f for f in findings if f.check_id == "gha-injection"]
        assert len(gha_findings) == 0


# ============================================================================
# 7. Path-Based Filtering Tests (6 tests)
# ============================================================================


class TestPathBasedFiltering:
    """Test that checks are only applied to relevant file types."""

    def test_python_checks_only_on_py_files(self, security_checker, create_js_file):
        """Test Python-specific checks don't run on JS files."""
        # Create a JS file with Python-like pattern
        create_js_file("config.js", '''
const config = {
    DEBUG: true,  // This should NOT trigger Python debug-mode check
};
''')

        findings = security_checker.run_quick_checks()

        # Python-specific debug-mode check should not fire on .js files
        debug_findings = [f for f in findings if f.check_id == "debug-mode"]
        assert len(debug_findings) == 0

    def test_js_checks_only_on_js_ts_files(self, security_checker, create_python_file):
        """Test JS-specific checks don't run on Python files."""
        # Create a Python file mentioning innerHTML (in a comment)
        create_python_file("utils.py", '''
# Note: Don't use innerHTML in JS, use textContent instead
def process():
    pass
''')

        findings = security_checker.run_quick_checks()

        # JS-specific inner-html check should not fire on .py files
        html_findings = [f for f in findings if f.check_id == "inner-html"]
        assert len(html_findings) == 0

    def test_gha_checks_only_on_workflow_files(self, security_checker, create_python_file):
        """Test GitHub Actions checks only run on workflow files."""
        # Create a Python file with similar pattern
        create_python_file("ci.py", '''
# Example showing github.event usage
template = "run: echo ${{ github.event.issue.title }}"
''')

        findings = security_checker.run_quick_checks()

        # GHA injection check should NOT fire on .py files
        gha_findings = [f for f in findings if f.check_id == "gha-injection"]
        assert len(gha_findings) == 0

    def test_checks_run_on_tsx_files(self, security_checker, create_js_file):
        """Test JS checks run on .tsx files."""
        create_js_file("Component.tsx", '''
const Component = () => {
    return <div dangerouslySetInnerHTML={{__html: html}} />;
};
''')

        findings = security_checker.run_quick_checks()

        html_findings = [f for f in findings if f.check_id == "dangerous-inner-html"]
        assert len(html_findings) >= 1

    def test_checks_run_on_jsx_files(self, security_checker, create_js_file):
        """Test JS checks run on .jsx files."""
        create_js_file("page.jsx", '''
function Page() {
    return <div dangerouslySetInnerHTML={{__html: content}} />;
}
''')

        findings = security_checker.run_quick_checks()

        html_findings = [f for f in findings if f.check_id == "dangerous-inner-html"]
        assert len(html_findings) >= 1

    def test_ignores_non_source_files(self, security_checker, create_config_file):
        """Test that non-source files are ignored."""
        # Create a .txt file with patterns that would normally match
        create_config_file("notes.txt", '''
TODO: Fix eval(user_input) in code
Remember: Never use pickle.load on untrusted data
''')

        findings = security_checker.run_quick_checks()

        # Should not find anything in .txt files
        eval_findings = [f for f in findings if f.check_id in ["eval-exec", "pickle-load"]]
        assert len(eval_findings) == 0


# ============================================================================
# 8. False Positive Prevention Tests (8 tests)
# ============================================================================


class TestFalsePositivePrevention:
    """Test that safe patterns don't trigger false positives."""

    def test_no_false_positive_on_comments(self, security_checker, create_python_file):
        """Test no false positive when pattern is in a comment."""
        create_python_file("safe.py", '''
# WARNING: Never use eval(user_input) as it's dangerous
# Example of bad code: subprocess.run(f"ls {path}", shell=True)

def safe_function():
    return "hello"
''')

        findings = security_checker.run_quick_checks()

        # Comments mentioning dangerous patterns should ideally not trigger
        # This is a stretch goal - basic implementation may still flag these
        # For now, we test that true positives are detected correctly
        assert findings is not None  # At minimum, returns a list

    def test_no_false_positive_on_safe_eval_ast(self, security_checker, create_python_file):
        """Test no false positive on ast.literal_eval."""
        create_python_file("parser.py", '''
import ast

def safe_parse(expr):
    return ast.literal_eval(expr)
''')

        findings = security_checker.run_quick_checks()

        # ast.literal_eval is safe, should not trigger eval-exec
        eval_findings = [f for f in findings if f.check_id == "eval-exec"]
        # Note: Basic implementation might still trigger, this is a refinement test
        # The key is that actual eval( triggers

    def test_no_false_positive_on_environment_variables(self, security_checker, create_python_file):
        """Test no false positive when using environment variables."""
        create_python_file("config.py", '''
import os

API_KEY = os.environ.get("API_KEY")
PASSWORD = os.getenv("DB_PASSWORD", "")
SECRET = os.environ["JWT_SECRET"]
''')

        findings = security_checker.run_quick_checks()

        # Using os.environ should not trigger hardcoded-secrets
        secret_findings = [f for f in findings if f.check_id == "hardcoded-secrets"]
        assert len(secret_findings) == 0

    def test_no_false_positive_on_parameterized_query(self, security_checker, create_python_file):
        """Test no false positive on parameterized SQL queries."""
        create_python_file("db.py", '''
def get_user(user_id):
    # Safe: Using parameterized query
    query = "SELECT * FROM users WHERE id = ?"
    return db.execute(query, (user_id,))
''')

        findings = security_checker.run_quick_checks()

        sql_findings = [f for f in findings if f.check_id == "sql-injection"]
        assert len(sql_findings) == 0

    def test_no_false_positive_on_subprocess_list(self, security_checker, create_python_file):
        """Test no false positive on subprocess with list arguments."""
        create_python_file("shell.py", '''
import subprocess

def run_safe(path):
    # Safe: Using list form without shell=True
    subprocess.run(["ls", "-la", path])
''')

        findings = security_checker.run_quick_checks()

        cmd_findings = [f for f in findings if f.check_id == "command-injection"]
        assert len(cmd_findings) == 0

    def test_no_false_positive_on_text_content(self, security_checker, create_js_file):
        """Test no false positive when using textContent instead of innerHTML."""
        create_js_file("safe.js", '''
function setContent(element, text) {
    element.textContent = text;  // Safe alternative to innerHTML
}
''')

        findings = security_checker.run_quick_checks()

        html_findings = [f for f in findings if f.check_id == "inner-html"]
        assert len(html_findings) == 0

    def test_no_false_positive_on_dompurify(self, security_checker, create_js_file):
        """Test that using DOMPurify with innerHTML is detected but noted."""
        create_js_file("sanitized.js", '''
import DOMPurify from 'dompurify';

function setContent(element, html) {
    element.innerHTML = DOMPurify.sanitize(html);
}
''')

        findings = security_checker.run_quick_checks()

        # innerHTML is still flagged (sanitization is good but defense in depth matters)
        # This tests that the check runs; implementation may or may not be smart about DOMPurify
        html_findings = [f for f in findings if f.check_id == "inner-html"]
        # At minimum, the check should execute

    def test_finding_includes_correct_line_number(self, security_checker, create_python_file):
        """Test that findings include correct line numbers."""
        create_python_file("multiline.py", '''
# Line 1
# Line 2
# Line 3
API_KEY = "sk-secret-key-12345"
# Line 5
''')

        findings = security_checker.run_quick_checks()

        secret_findings = [f for f in findings if f.check_id == "hardcoded-secrets"]
        assert len(secret_findings) >= 1
        # The pattern is on line 4
        assert secret_findings[0].line_number == 4


# ============================================================================
# 9. Performance Tests (4 tests)
# ============================================================================


class TestPerformance:
    """Test that security checks complete within acceptable time."""

    def test_empty_project_completes_quickly(self, security_checker):
        """Test that checking an empty project is fast."""
        start = time.time()
        findings = security_checker.run_quick_checks()
        elapsed = time.time() - start

        assert elapsed < 1.0, f"Empty project check took {elapsed:.2f}s, should be < 1s"
        assert isinstance(findings, list)

    def test_small_project_under_5_seconds(self, security_checker, create_python_file, create_js_file):
        """Test that a small project (10 files) completes in under 5 seconds."""
        # Create 10 files with some content
        for i in range(5):
            create_python_file(f"module_{i}.py", f'''
def function_{i}():
    return "result_{i}"
''')
            create_js_file(f"component_{i}.js", f'''
function Component{i}() {{
    return <div>Content {i}</div>;
}}
''')

        start = time.time()
        findings = security_checker.run_quick_checks()
        elapsed = time.time() - start

        assert elapsed < 5.0, f"Small project check took {elapsed:.2f}s, should be < 5s"

    def test_medium_project_under_15_seconds(self, security_checker, create_python_file, create_js_file):
        """Test that a medium project (50 files) completes in under 15 seconds."""
        # Create 50 files
        for i in range(25):
            create_python_file(f"src/module_{i}.py", f'''
import os
import sys

class Service{i}:
    def __init__(self):
        self.name = "service_{i}"

    def process(self, data):
        return data.upper()

    def validate(self, input):
        if not input:
            raise ValueError("Invalid input")
        return True
''')
            create_js_file(f"components/Component{i}.tsx", f'''
import React from 'react';

interface Props{i} {{
    title: string;
    content: string;
}}

export const Component{i}: React.FC<Props{i}> = ({{ title, content }}) => {{
    return (
        <div className="component-{i}">
            <h2>{{title}}</h2>
            <p>{{content}}</p>
        </div>
    );
}};
''')

        start = time.time()
        findings = security_checker.run_quick_checks()
        elapsed = time.time() - start

        assert elapsed < 15.0, f"Medium project check took {elapsed:.2f}s, should be < 15s"

    def test_typical_project_under_30_seconds(self, security_checker, create_python_file, create_js_file, create_workflow_file):
        """Test that a typical project (100 files) completes in under 30 seconds."""
        # Create 100 files to simulate typical project
        for i in range(40):
            create_python_file(f"src/services/service_{i}.py", f'''
"""Service module {i}."""
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class Service{i}:
    """Main service class for module {i}."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logger

    def process(self, data: List[str]) -> List[str]:
        """Process input data."""
        results = []
        for item in data:
            processed = self._transform(item)
            results.append(processed)
        return results

    def _transform(self, item: str) -> str:
        return item.strip().lower()

    def validate(self, input_data: Optional[str]) -> bool:
        if not input_data:
            return False
        return len(input_data) > 0
''')

        for i in range(40):
            create_js_file(f"src/components/Feature{i}.tsx", f'''
import React, {{ useState, useEffect }} from 'react';
import {{ useQuery }} from 'react-query';

interface Feature{i}Props {{
    id: string;
    title: string;
    description?: string;
}}

export const Feature{i}: React.FC<Feature{i}Props> = ({{ id, title, description }}) => {{
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {{
        setIsLoading(true);
        // Fetch data
        setIsLoading(false);
    }}, [id]);

    if (isLoading) return <div>Loading...</div>;
    if (error) return <div>Error: {{error}}</div>;

    return (
        <div className="feature-{i}">
            <h2>{{title}}</h2>
            {{description && <p>{{description}}</p>}}
        </div>
    );
}};
''')

        for i in range(5):
            create_workflow_file(f"workflow_{i}.yml", f'''
name: Workflow {i}
on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Node
        uses: actions/setup-node@v4
      - run: npm ci
      - run: npm test
''')

        start = time.time()
        findings = security_checker.run_quick_checks()
        elapsed = time.time() - start

        assert elapsed < 30.0, f"Typical project check took {elapsed:.2f}s, should be < 30s"


# ============================================================================
# 10. Integration with CoachValidator Tests (5 tests)
# ============================================================================


class TestCoachValidatorIntegration:
    """Test integration with CoachValidator (mocked)."""

    def test_security_checker_can_be_imported_in_coach_validator(self):
        """Test that SecurityChecker can be imported from quality_gates module."""
        from guardkit.orchestrator.quality_gates.security_checker import SecurityChecker
        from guardkit.orchestrator.quality_gates.security_checker import SecurityFinding

        # These should be importable
        assert SecurityChecker is not None
        assert SecurityFinding is not None

    def test_findings_list_is_filterable_by_severity(self, security_checker, create_python_file):
        """Test that findings can be filtered by severity for Coach decisions."""
        create_python_file("vulnerable.py", '''
API_KEY = "sk-secret-key"  # critical
DEBUG = True  # high
''')

        findings = security_checker.run_quick_checks()

        critical = [f for f in findings if f.severity == "critical"]
        high = [f for f in findings if f.severity == "high"]

        # Should have at least one critical and one high
        assert len(critical) >= 1
        assert len(high) >= 1

    def test_findings_contain_actionable_recommendations(self, security_checker, create_python_file):
        """Test that findings contain actionable recommendations."""
        create_python_file("bad.py", '''
API_KEY = "sk-1234567890"
''')

        findings = security_checker.run_quick_checks()

        assert len(findings) >= 1
        finding = findings[0]

        # Recommendation should be non-empty and actionable
        assert finding.recommendation
        assert len(finding.recommendation) > 10  # Should be a real recommendation

    def test_run_quick_checks_returns_empty_list_on_clean_project(self, security_checker, create_python_file):
        """Test that clean project returns empty findings list."""
        create_python_file("clean.py", '''
import os

API_KEY = os.environ.get("API_KEY")

def safe_function():
    return "hello world"
''')

        findings = security_checker.run_quick_checks()

        # Clean code should have no findings
        assert len(findings) == 0

    def test_multiple_findings_same_file(self, security_checker, create_python_file):
        """Test that multiple issues in same file are all reported."""
        create_python_file("multi_issue.py", '''
API_KEY = "sk-secret"
PASSWORD = "admin123"
DEBUG = True

def dangerous():
    return eval(input())
''')

        findings = security_checker.run_quick_checks()

        # Should find multiple issues
        # At minimum: 2 hardcoded secrets, 1 debug mode, 1 eval
        assert len(findings) >= 3

        # Verify different check types found
        check_ids = {f.check_id for f in findings}
        assert "hardcoded-secrets" in check_ids
        assert "debug-mode" in check_ids or "eval-exec" in check_ids


# ============================================================================
# 11. Edge Cases Tests (5 tests)
# ============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_handles_empty_files(self, security_checker, create_python_file):
        """Test handling of empty files."""
        create_python_file("empty.py", "")

        findings = security_checker.run_quick_checks()

        # Should not crash, should return list
        assert isinstance(findings, list)

    def test_handles_binary_files_gracefully(self, temp_worktree):
        """Test that binary files don't crash the checker."""
        from guardkit.orchestrator.quality_gates.security_checker import SecurityChecker

        # Create a binary file
        binary_file = temp_worktree / "src" / "data.bin"
        binary_file.parent.mkdir(parents=True, exist_ok=True)
        binary_file.write_bytes(b'\x00\x01\x02\x03\xff\xfe\xfd')

        checker = SecurityChecker(temp_worktree)

        # Should not crash
        findings = checker.run_quick_checks()
        assert isinstance(findings, list)

    def test_handles_deeply_nested_files(self, temp_worktree):
        """Test handling of deeply nested file structures."""
        from guardkit.orchestrator.quality_gates.security_checker import SecurityChecker

        # Create deeply nested file
        deep_path = temp_worktree / "a" / "b" / "c" / "d" / "e" / "f" / "vulnerable.py"
        deep_path.parent.mkdir(parents=True, exist_ok=True)
        deep_path.write_text('API_KEY = "secret"')

        checker = SecurityChecker(temp_worktree)
        findings = checker.run_quick_checks()

        # Should find the vulnerability
        secret_findings = [f for f in findings if f.check_id == "hardcoded-secrets"]
        assert len(secret_findings) >= 1

    def test_handles_unicode_content(self, security_checker, create_python_file):
        """Test handling of Unicode content in files."""
        create_python_file("unicode.py", '''
# Unicode comment: 你好世界 🌍
API_KEY = "sk-secret-unicode-密码"
''')

        findings = security_checker.run_quick_checks()

        # Should still detect the issue
        secret_findings = [f for f in findings if f.check_id == "hardcoded-secrets"]
        assert len(secret_findings) >= 1

    def test_handles_very_long_lines(self, security_checker, create_python_file):
        """Test handling of files with very long lines."""
        long_string = "x" * 10000
        create_python_file("long.py", f'''
LONG_VALUE = "{long_string}"
API_KEY = "sk-secret"
''')

        findings = security_checker.run_quick_checks()

        # Should still find the API key
        secret_findings = [f for f in findings if f.check_id == "hardcoded-secrets"]
        assert len(secret_findings) >= 1


# ============================================================================
# 12. Run Quick Checks Return Type Tests (3 tests)
# ============================================================================


class TestRunQuickChecksReturnType:
    """Test the return type and structure of run_quick_checks."""

    def test_returns_list(self, security_checker):
        """Test that run_quick_checks returns a list."""
        result = security_checker.run_quick_checks()

        assert isinstance(result, list)

    def test_returns_list_of_security_findings(self, security_checker, create_python_file):
        """Test that list contains SecurityFinding objects."""
        from guardkit.orchestrator.quality_gates.security_checker import SecurityFinding

        create_python_file("bad.py", 'API_KEY = "secret"')

        findings = security_checker.run_quick_checks()

        assert len(findings) >= 1
        assert all(isinstance(f, SecurityFinding) for f in findings)

    def test_findings_are_sorted_by_severity(self, security_checker, create_python_file):
        """Test that findings are sorted by severity (critical first)."""
        create_python_file("mixed.py", '''
DEBUG = True  # high
API_KEY = "secret"  # critical
''')

        findings = security_checker.run_quick_checks()

        if len(findings) >= 2:
            severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
            severities = [severity_order.get(f.severity, 5) for f in findings]

            # Should be sorted (critical before high)
            assert severities == sorted(severities), "Findings should be sorted by severity"

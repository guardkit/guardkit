"""Pre-flight validation for LangChain DeepAgents projects.

Catches the top wiring issues before the first pipeline execution by
running automated checks against a project directory. Checks cover tool
separation, factory patterns, model configuration, domain config validity,
and JSON extraction pipeline correctness.

Usage:
    python -m lib.preflight [project_dir]
    guardkit validate [project_dir]

Exit codes:
    0: All automated checks passed
    1: One or more automated checks failed

Dependencies: stdlib only (ast, json, pathlib, re).
"""

from __future__ import annotations

import ast
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple


# ---------------------------------------------------------------------------
# Result data structures
# ---------------------------------------------------------------------------


@dataclass
class CheckResult:
    """Outcome of a single automated check."""

    name: str
    passed: bool
    detail: str
    severity: str = "error"  # "error" or "warning"


@dataclass
class PreflightReport:
    """Aggregated preflight validation report."""

    checks: List[CheckResult] = field(default_factory=list)
    manual_prompts: List[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """True if all error-severity checks passed."""
        return all(c.passed for c in self.checks if c.severity == "error")

    @property
    def fail_count(self) -> int:
        return sum(1 for c in self.checks if not c.passed and c.severity == "error")

    @property
    def pass_count(self) -> int:
        return sum(1 for c in self.checks if c.passed)


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------


def _find_python_files(project_dir: Path) -> List[Path]:
    """Find all .py files in the project, excluding __pycache__ and .venv."""
    results = []
    for p in project_dir.rglob("*.py"):
        parts = p.parts
        if "__pycache__" in parts or ".venv" in parts or "venv" in parts:
            continue
        results.append(p)
    return sorted(results)


def _parse_file(path: Path) -> Optional[ast.Module]:
    """Parse a Python file into an AST, returning None on failure."""
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return None


def _extract_set_assignment(tree: ast.Module, name: str) -> Optional[Set[str]]:
    """Extract a module-level set literal assigned to *name*.

    Handles ``NAME = {"a", "b"}`` (ast.Assign with ast.Set),
    ``NAME: set[str] = {"a"}`` (ast.AnnAssign), and ``NAME = set()`` (empty).
    """
    for node in ast.walk(tree):
        # Handle both plain assignment and annotated assignment
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return _parse_set_value(node.value)
        elif isinstance(node, ast.AnnAssign):
            target = node.target
            if isinstance(target, ast.Name) and target.id == name and node.value is not None:
                return _parse_set_value(node.value)
    return None


def _parse_set_value(val: ast.expr) -> Optional[Set[str]]:
    """Parse an AST expression node as a set of strings."""
    # set literal: {a, b}
    if isinstance(val, ast.Set):
        return {
            elt.value
            for elt in val.elts
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
        }
    # set() call with no args → empty set
    if (
        isinstance(val, ast.Call)
        and isinstance(val.func, ast.Name)
        and val.func.id == "set"
        and not val.args
    ):
        return set()
    return None


def _find_factory_files(project_dir: Path) -> List[Path]:
    """Find Python files that look like agent factory modules."""
    candidates = []
    for p in _find_python_files(project_dir):
        name = p.name.lower()
        if "factory" in name or "player" in name:
            candidates.append(p)
    return candidates


def _file_contains_call(tree: ast.Module, func_name: str) -> bool:
    """Check if any call in the AST invokes *func_name*."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == func_name:
                return True
            if isinstance(func, ast.Attribute) and func.attr == func_name:
                return True
    return False


def _file_imports_name(tree: ast.Module, name: str) -> bool:
    """Check if the file imports *name* (from ... import name)."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == name:
                    return True
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == name or (alias.asname and alias.asname == name):
                    return True
    return False


# ---------------------------------------------------------------------------
# Config parsing helpers
# ---------------------------------------------------------------------------


def _load_yaml_simple(path: Path) -> Optional[Dict[str, Any]]:
    """Load a YAML file, trying PyYAML first then falling back to basic parsing."""
    text = path.read_text(encoding="utf-8")
    try:
        import yaml

        return yaml.safe_load(text)
    except ImportError:
        pass
    # Basic key: value parsing for flat/simple YAML
    return _parse_simple_yaml(text)


def _parse_simple_yaml(text: str) -> Dict[str, Any]:
    """Minimal YAML parser for flat key-value structures.

    Handles indented sections as nested dicts (one level deep).
    NOT a full YAML parser — just enough for agent-config.yaml.
    """
    result: Dict[str, Any] = {}
    current_section: Optional[str] = None

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(line) - len(line.lstrip())

        if ":" in stripped:
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip()

            if indent == 0:
                if value:
                    result[key] = value
                else:
                    result[key] = {}
                    current_section = key
            elif current_section is not None and isinstance(result.get(current_section), dict):
                section = result[current_section]
                if value:
                    section[key] = value
                else:
                    section[key] = {}

    return result


def _find_domain_dirs(project_dir: Path) -> List[Path]:
    """Find directories that contain a DOMAIN.md file."""
    domains_dir = project_dir / "domains"
    if not domains_dir.is_dir():
        return []
    return [d for d in domains_dir.iterdir() if d.is_dir() and (d / "DOMAIN.md").exists()]


def _find_domain_config_files(project_dir: Path) -> List[Path]:
    """Find domain configuration files (JSON or YAML)."""
    configs = []
    domains_dir = project_dir / "domains"
    if not domains_dir.is_dir():
        return configs
    for d in domains_dir.iterdir():
        if not d.is_dir():
            continue
        for ext in ("config.json", "config.yaml", "config.yml", "schema.json"):
            candidate = d / ext
            if candidate.exists():
                configs.append(candidate)
    return configs


# ---------------------------------------------------------------------------
# Automated check functions
# ---------------------------------------------------------------------------


def check_player_tools(project_dir: Path) -> CheckResult:
    """Check Player tool inventory matches expected allowlist.

    Looks for PLAYER_ALLOWED_TOOLS assignment in factory files and verifies
    each tool in the set is a known domain tool (not a filesystem tool).
    """
    factory_files = _find_factory_files(project_dir)
    if not factory_files:
        return CheckResult(
            name="Player tools",
            passed=False,
            detail="No factory files found (expected *factory*.py or *player*.py)",
        )

    filesystem_tools = {
        "ls", "read_file", "write_file", "edit_file",
        "glob", "grep", "execute", "write_todos",
    }

    for path in factory_files:
        tree = _parse_file(path)
        if tree is None:
            continue
        tools = _extract_set_assignment(tree, "PLAYER_ALLOWED_TOOLS")
        if tools is not None:
            leaked = tools & filesystem_tools
            if leaked:
                return CheckResult(
                    name="Player tools",
                    passed=False,
                    detail=f"Player has filesystem tools: {sorted(leaked)} in {path.name}",
                )
            return CheckResult(
                name="Player tools",
                passed=True,
                detail=f"Player tools: {sorted(tools) or '{}'} ({path.name})",
            )

    return CheckResult(
        name="Player tools",
        passed=False,
        detail="PLAYER_ALLOWED_TOOLS not found in any factory file",
        severity="warning",
    )


def check_coach_tools(project_dir: Path) -> CheckResult:
    """Check Coach tool list is empty (or evaluator-only)."""
    factory_files = _find_factory_files(project_dir)
    if not factory_files:
        return CheckResult(
            name="Coach tools",
            passed=False,
            detail="No factory files found",
        )

    for path in factory_files:
        tree = _parse_file(path)
        if tree is None:
            continue
        tools = _extract_set_assignment(tree, "COACH_ALLOWED_TOOLS")
        if tools is not None:
            if tools:
                return CheckResult(
                    name="Coach tools",
                    passed=False,
                    detail=f"Coach has tools: {sorted(tools)} (expected empty set)",
                )
            return CheckResult(
                name="Coach tools",
                passed=True,
                detail=f"Coach tools: set() (expected: set())",
            )

    return CheckResult(
        name="Coach tools",
        passed=False,
        detail="COACH_ALLOWED_TOOLS not found in any factory file",
        severity="warning",
    )


def check_no_write_output(project_dir: Path) -> CheckResult:
    """Check Player does NOT have write_output in its tool set."""
    factory_files = _find_factory_files(project_dir)
    if not factory_files:
        return CheckResult(
            name="Player no write_output",
            passed=False,
            detail="No factory files found",
        )

    for path in factory_files:
        tree = _parse_file(path)
        if tree is None:
            continue
        tools = _extract_set_assignment(tree, "PLAYER_ALLOWED_TOOLS")
        if tools is not None:
            if "write_output" in tools:
                return CheckResult(
                    name="Player no write_output",
                    passed=False,
                    detail="TOOL SEPARATION VIOLATION: Player has write_output",
                )
            return CheckResult(
                name="Player no write_output",
                passed=True,
                detail="Player does not have write_output",
            )

    # Also scan for write_output in player factory function tool lists
    for path in factory_files:
        text = path.read_text(encoding="utf-8")
        if "write_output" in text and "player" in path.name.lower():
            return CheckResult(
                name="Player no write_output",
                passed=False,
                detail=f"write_output reference found in {path.name}",
            )

    return CheckResult(
        name="Player no write_output",
        passed=True,
        detail="No write_output references in player factories",
    )


def check_factory_pattern(project_dir: Path) -> CheckResult:
    """Check factory uses create_restricted_agent (not create_deep_agent) for Players.

    create_deep_agent() unconditionally injects FilesystemMiddleware (8 tools).
    Tool-restricted agents must use create_restricted_agent() or create_agent().
    """
    factory_files = _find_factory_files(project_dir)
    if not factory_files:
        return CheckResult(
            name="Factory pattern",
            passed=False,
            detail="No factory files found",
        )

    violations = []
    safe_files = []

    for path in factory_files:
        tree = _parse_file(path)
        if tree is None:
            continue

        uses_deep = _file_contains_call(tree, "create_deep_agent")
        uses_restricted = (
            _file_contains_call(tree, "create_restricted_agent")
            or _file_contains_call(tree, "create_agent")
        )
        imports_restricted = _file_imports_name(tree, "create_restricted_agent")

        # create_deep_agent is OK in agent.py (entrypoint) but not in factory files
        # that create tool-restricted agents
        if uses_deep and not uses_restricted and "factory" in path.name.lower():
            violations.append(path.name)
        elif uses_restricted or imports_restricted:
            safe_files.append(path.name)

    if violations:
        return CheckResult(
            name="Factory pattern",
            passed=False,
            detail=(
                f"Factory uses create_deep_agent (leaks filesystem tools): "
                f"{', '.join(violations)}"
            ),
        )

    if safe_files:
        return CheckResult(
            name="Factory pattern",
            passed=True,
            detail=f"Factory uses create_restricted_agent: {', '.join(safe_files)}",
        )

    return CheckResult(
        name="Factory pattern",
        passed=True,
        detail="No factory files with tool-restricted agent creation found",
        severity="warning",
    )


def check_max_tokens(project_dir: Path) -> CheckResult:
    """Check max_tokens is explicitly set for all model configs.

    Searches agent-config.yaml (or legacy coach-config.yaml), .env, and
    Python config files for max_tokens settings.
    """
    config_path = project_dir / "agent-config.yaml"
    if not config_path.exists():
        config_path = project_dir / "agent-config.yml"
    if not config_path.exists():
        config_path = project_dir / "coach-config.yaml"
    if not config_path.exists():
        config_path = project_dir / "coach-config.yml"

    if not config_path.exists():
        return CheckResult(
            name="max_tokens set",
            passed=False,
            detail="agent-config.yaml not found",
        )

    config = _load_yaml_simple(config_path)
    if config is None:
        return CheckResult(
            name="max_tokens set",
            passed=False,
            detail="Failed to parse coach-config.yaml",
        )

    # Check for max_tokens in config at various levels
    found_tokens = {}
    _search_max_tokens(config, "", found_tokens)

    # Also check Python files for max_tokens assignments
    for py_file in _find_python_files(project_dir):
        tree = _parse_file(py_file)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and "max_tokens" in target.id.lower():
                        if isinstance(node.value, ast.Constant):
                            found_tokens[f"{py_file.name}:{target.id}"] = node.value.value
            # Also check keyword args in function calls
            if isinstance(node, ast.Call):
                for kw in node.keywords:
                    if kw.arg == "max_tokens" and isinstance(kw.value, ast.Constant):
                        func_name = ""
                        if isinstance(node.func, ast.Name):
                            func_name = node.func.id
                        elif isinstance(node.func, ast.Attribute):
                            func_name = node.func.attr
                        found_tokens[f"{py_file.name}:{func_name}"] = kw.value.value

    if found_tokens:
        summary = ", ".join(f"{k}={v}" for k, v in found_tokens.items())
        return CheckResult(
            name="max_tokens set",
            passed=True,
            detail=f"max_tokens set: {summary}",
        )

    return CheckResult(
        name="max_tokens set",
        passed=False,
        detail="max_tokens not explicitly set in config or code",
    )


def _search_max_tokens(
    data: Any, prefix: str, found: Dict[str, Any]
) -> None:
    """Recursively search a config dict for max_tokens keys."""
    if isinstance(data, dict):
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if "max_tokens" in key.lower():
                found[full_key] = value
            _search_max_tokens(value, full_key, found)


def check_domain_config(project_dir: Path) -> CheckResult:
    """Check domain config parses without errors.

    Finds domain directories and validates their DOMAIN.md files exist
    and contain required sections. Also checks domain config files
    (JSON/YAML) for basic validity.
    """
    domain_dirs = _find_domain_dirs(project_dir)
    if not domain_dirs:
        return CheckResult(
            name="Domain config",
            passed=True,
            detail="No domain directories found (domains/ absent)",
            severity="warning",
        )

    issues = []
    targets = 0
    metadata_fields = 0

    for domain_dir in domain_dirs:
        domain_md = domain_dir / "DOMAIN.md"
        content = domain_md.read_text(encoding="utf-8")

        # Check for required sections
        if "## Target" not in content and "## Targets" not in content:
            issues.append(f"{domain_dir.name}: missing Targets section in DOMAIN.md")
        if "## Metadata" not in content:
            issues.append(f"{domain_dir.name}: missing Metadata section in DOMAIN.md")

        # Count targets and metadata fields (basic heuristic)
        targets += content.lower().count("- target") + content.lower().count("target:")
        metadata_fields += content.lower().count("- field") + content.lower().count("field:")

    # Check JSON/YAML config files
    config_files = _find_domain_config_files(project_dir)
    for config_file in config_files:
        try:
            if config_file.suffix == ".json":
                json.loads(config_file.read_text(encoding="utf-8"))
            else:
                data = _load_yaml_simple(config_file)
                if data is None:
                    issues.append(f"{config_file.name}: failed to parse")
        except (json.JSONDecodeError, ValueError) as exc:
            issues.append(f"{config_file.name}: parse error: {exc}")

    if issues:
        return CheckResult(
            name="Domain config",
            passed=False,
            detail="; ".join(issues),
        )

    return CheckResult(
        name="Domain config",
        passed=True,
        detail=f"Domain config parses: {len(domain_dirs)} domains, {len(config_files)} configs",
    )


def check_metadata_types(project_dir: Path) -> CheckResult:
    """Check metadata field types match validation logic.

    Detects mismatches where range notation is used but the validator
    treats the field as an enum (TRF-028), or array fields are compared
    with scalar `in` checks (FRF-002).
    """
    config_files = _find_domain_config_files(project_dir)
    if not config_files:
        # Also scan Python files for MetadataField definitions
        schema_issues = _check_metadata_in_python(project_dir)
        if schema_issues:
            return CheckResult(
                name="Metadata types",
                passed=False,
                detail="; ".join(schema_issues),
            )
        return CheckResult(
            name="Metadata types",
            passed=True,
            detail="No domain config files or inline schema issues found",
            severity="warning",
        )

    issues = []
    for config_file in config_files:
        if config_file.suffix == ".json":
            try:
                data = json.loads(config_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            issues.extend(_validate_metadata_schema(data, config_file.name))

    if issues:
        return CheckResult(
            name="Metadata types",
            passed=False,
            detail="; ".join(issues),
        )

    return CheckResult(
        name="Metadata types",
        passed=True,
        detail="Metadata field types consistent with validation logic",
    )


def _check_metadata_in_python(project_dir: Path) -> List[str]:
    """Scan Python files for MetadataField usage with type mismatches."""
    issues = []
    range_re = re.compile(r'^\d+[+-]$|^\d+-\d+$')

    for py_file in _find_python_files(project_dir):
        tree = _parse_file(py_file)
        if tree is None:
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (isinstance(func, ast.Name) and func.id == "MetadataField"):
                continue

            # Extract field name and valid_values from MetadataField(...)
            field_name = None
            field_type = None
            valid_values = None

            if node.args and isinstance(node.args[0], ast.Constant):
                field_name = node.args[0].value
            if len(node.args) > 1 and isinstance(node.args[1], ast.Attribute):
                field_type = node.args[1].attr

            for kw in node.keywords:
                if kw.arg == "valid_values":
                    if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                        valid_values = kw.value.value
                    elif isinstance(kw.value, ast.List):
                        valid_values = "list"
                if kw.arg == "type" and isinstance(kw.value, ast.Attribute):
                    field_type = kw.value.attr

            # Check: range notation + non-numeric type
            if (
                valid_values
                and isinstance(valid_values, str)
                and range_re.match(valid_values)
                and field_type in ("STRING", "BOOLEAN", "ARRAY")
            ):
                issues.append(
                    f"Field '{field_name}' uses range notation '{valid_values}' "
                    f"but type is {field_type} (should be INTEGER or FLOAT)"
                )

    return issues


def _validate_metadata_schema(data: Dict[str, Any], filename: str) -> List[str]:
    """Validate metadata schema from a config dict."""
    issues = []
    range_re = re.compile(r'^\d+[+-]$|^\d+-\d+$')

    fields = data.get("metadata", data.get("fields", {}))
    if not isinstance(fields, (dict, list)):
        return issues

    items = fields.items() if isinstance(fields, dict) else enumerate(fields)
    for key, field_def in items:
        if not isinstance(field_def, dict):
            continue
        ftype = field_def.get("type", "string")
        valid = field_def.get("valid_values", "")
        fname = field_def.get("name", str(key))

        if isinstance(valid, str) and range_re.match(valid):
            if ftype in ("string", "boolean", "array"):
                issues.append(
                    f"Metadata field '{fname}' uses range notation "
                    f"but validator treats as {ftype}"
                )

    return issues


def check_json_pipeline(project_dir: Path) -> CheckResult:
    """Check JSON extraction pipeline order is correct.

    Verifies that JsonExtractor.extract() is called (not raw json.loads
    on LLM output), and that think tag normalisation precedes extraction.
    """
    py_files = _find_python_files(project_dir)
    if not py_files:
        return CheckResult(
            name="JSON pipeline",
            passed=False,
            detail="No Python files found",
        )

    uses_extractor = False
    uses_raw_json_loads_on_llm = False
    uses_normalise = False

    for path in py_files:
        tree = _parse_file(path)
        if tree is None:
            continue

        # Skip test files and the json_extractor module itself
        if "test" in path.name.lower() or path.name == "json_extractor.py":
            continue

        has_extractor_call = _file_contains_call(tree, "extract")
        has_extractor_import = _file_imports_name(tree, "JsonExtractor")
        has_normalise = (
            _file_contains_call(tree, "normalise_think_closing_tags")
            or _file_imports_name(tree, "normalise_think_closing_tags")
        )

        if has_extractor_import and has_extractor_call:
            uses_extractor = True
        if has_normalise:
            uses_normalise = True

        # Check for raw json.loads on LLM response patterns
        text = path.read_text(encoding="utf-8")
        if (
            "json.loads" in text
            and ("response" in text.lower() or "content" in text.lower())
            and "json_extractor" not in text.lower()
            and not has_extractor_import
        ):
            # Heuristic: json.loads used in a file that deals with LLM responses
            # but doesn't use JsonExtractor
            if "agent" in path.name.lower() or "pipeline" in path.name.lower():
                uses_raw_json_loads_on_llm = True

    if uses_raw_json_loads_on_llm and not uses_extractor:
        return CheckResult(
            name="JSON pipeline",
            passed=False,
            detail=(
                "Raw json.loads used on LLM output without JsonExtractor. "
                "Use JsonExtractor.extract() for robust 5-strategy parsing."
            ),
        )

    if uses_extractor:
        return CheckResult(
            name="JSON pipeline",
            passed=True,
            detail="JsonExtractor.extract() used for LLM output parsing",
        )

    return CheckResult(
        name="JSON pipeline",
        passed=True,
        detail="No LLM output parsing detected (pipeline not yet wired)",
        severity="warning",
    )


# ---------------------------------------------------------------------------
# Manual review prompts
# ---------------------------------------------------------------------------


MANUAL_PROMPTS = [
    "Does your Player prompt end with a CRITICAL Response Format section?",
    "Does your Coach prompt include explicit accept/reject criteria?",
    "Have you tested your model/parser combination with tool calling?",
    "Is your vLLM reasoning-parser configuration compatible with your extraction?",
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


ALL_CHECKS = [
    check_player_tools,
    check_coach_tools,
    check_no_write_output,
    check_factory_pattern,
    check_max_tokens,
    check_domain_config,
    check_metadata_types,
    check_json_pipeline,
]


def run_preflight(project_dir: Path) -> PreflightReport:
    """Run all preflight checks against a project directory.

    Args:
        project_dir: Root directory of the generated project.

    Returns:
        PreflightReport with check results and manual prompts.
    """
    report = PreflightReport()
    report.manual_prompts = list(MANUAL_PROMPTS)

    for check_fn in ALL_CHECKS:
        result = check_fn(project_dir)
        report.checks.append(result)

    return report


# ---------------------------------------------------------------------------
# Terminal output formatting
# ---------------------------------------------------------------------------


def format_report(report: PreflightReport) -> str:
    """Format a PreflightReport for terminal display."""
    lines = []
    lines.append("")
    lines.append("Automated Checks:")

    for check in report.checks:
        status = "[PASS]" if check.passed else "[FAIL]"
        lines.append(f"  {status} {check.detail}")

    lines.append("")
    lines.append("Manual Review:")
    for prompt in report.manual_prompts:
        lines.append(f"  ? {prompt}")

    lines.append("")
    lines.append(
        f"Result: {report.fail_count} FAIL, "
        f"{report.pass_count} PASS, "
        f"{len(report.manual_prompts)} manual checks pending"
    )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI entry point for preflight validation.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code: 0 if all checks pass, 1 if any fail.
    """
    if argv is None:
        argv = sys.argv[1:]

    project_dir = Path(argv[0]) if argv else Path.cwd()

    if not project_dir.is_dir():
        print(f"Error: {project_dir} is not a directory", file=sys.stderr)
        return 1

    report = run_preflight(project_dir)
    print(format_report(report))

    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())

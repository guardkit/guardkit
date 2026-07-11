"""Deterministic template render+parse gate (DIM1-F4 / PB-8).

Renders every ``.template`` / ``.j2`` scaffold file with representative
placeholder values and parses the rendered output per stack. A parse ERROR means
the placeholder sweep produced source that does not even parse — the class of
defect **TASK-LCL-001** shipped (the ``{{ProjectName}}`` sweep over-rewrote an SDK
import, and nothing rendered+checked the templates). This gate turns that class
from a post-release surprise into a red build.

Two tiers cover the two failure shapes:

* **Parse tier (this module, all stacks).** Catches *syntactic* mangles — a
  placeholder substituted into a non-identifier (``scratch-core.backends``), a
  leftover ``{{...}}`` in code position, a broken JSX/`namespace` block. Fast, no
  project runtime deps, every stack.
* **Import tier (retained, langchain family).** ``tests/integration/
  test_template_render_import.py`` renders the langchain templates into a scratch
  tree and *imports* them in a subprocess. That is **stricter than a parse** — it
  catches the literal TASK-LCL-001 runtime failure (``from scratch.backends`` is
  valid syntax but ``ModuleNotFoundError`` at import). The two tiers are kept
  together on purpose (DIM1-F4: "they are stricter than a parse; keep both").

**Architecture (``stack-plugin-architecture.md``, BINDING).** Static analysis of
target-project source is stack-agnostic by construction: ONE tree-sitter parser
over the concrete syntax tree, plus per-language **descriptors as DATA**
(``LANGUAGE_BY_EXT``). A new language is a descriptor entry, never a per-stack
code plugin. There is no ``python-ast`` monolith here — ``ast`` would only parse
Python and would silo the other three stacks.

**Absence-of-failure safety (``absence-of-failure-is-not-success.md``).** A file
that was *not parsed* is never counted as a pass: unsupported extensions are
``SKIPPED`` (not ``OK``), and if the tree-sitter runtime is not installed the
gate raises :class:`ParseGateUnavailable` rather than reporting green.

**Opt-out (required before the gate can be red).** A minority of scaffold files
are non-parseable-by-design — real Jinja blocks, or JSX fragments whose braces
interleave placeholders and template literals so literal ``{{Key}}`` substitution
cannot yield valid source. Those carry an explicit opt-out: an inline
``guardkit:template-parse:optout`` marker in the file, or an entry in the seed
:data:`PARSE_OPTOUT` registry (seeded from the same declarative per-template
philosophy as the import tier's ``TEMPLATES`` / ``ENTRYPOINTS_BY_TEMPLATE``
config). An opted-out file is reported as ``OPTOUT``, distinct from ``OK``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional

from guardkit.templates.render import (
    iter_template_files,
    render_text,
    strip_template_suffix,
)

# ---------------------------------------------------------------------------
# Per-language descriptors (DATA — stack-plugin-architecture.md)
# ---------------------------------------------------------------------------
#
# Rendered-file extension -> tree-sitter language name. Adding a stack is a new
# row here, not new code. The names are the tree-sitter-language-pack grammar
# identifiers (note: C# is ``csharp``, not ``c_sharp``).
LANGUAGE_BY_EXT: Dict[str, str] = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".cs": "csharp",
}


# ---------------------------------------------------------------------------
# Representative placeholder registry (DATA)
# ---------------------------------------------------------------------------
#
# Values are chosen to render every stack's scaffolds into *parseable* source:
# identifier-safe names, valid version/number literals. This is "sample-render
# with placeholder substitutions" — not the real project values a consumer would
# supply, just a representative set sufficient for a syntax check.
SAMPLE_PLACEHOLDERS: Dict[str, str] = {
    "ProjectName": "scratch",
    "Namespace": "Scratch",
    "Author": "Test",
    "AuthorName": "Test",
    "AuthorEmail": "t@example.com",
    "ClassName": "Widget",
    "DomainName": "example_domain",
    "Description": "desc",
    "ProjectDescription": "desc",
    "ServiceName": "Widget",
    "EntityName": "Widget",
    "entity_name": "widget",
    "entityName": "widget",
    "entity-name": "widget",
    "EntityNamePlural": "Widgets",
    "entity_name_plural": "widgets",
    "entityNamePlural": "widgets",
    "entity-name-plural": "widgets",
    "FeatureName": "Feature",
    "featureName": "feature",
    "feature-name": "feature",
    "feature_name": "feature",
    "InterfaceName": "IWidget",
    "ServerName": "Server",
    "ServerVersion": "1.0.0",
    "ServerDescription": "desc",
    "ToolName": "Tool",
    "toolName": "tool",
    "tool_name": "tool",
    "tool-name": "tool",
    "ToolDescription": "desc",
    "ToolTitle": "Tool",
    "ResourceName": "Resource",
    "resourceName": "resource",
    "resource_name": "resource",
    "resource-name": "resource",
    "ResourceTitle": "Resource",
    "ResourceDescription": "desc",
    "ResourceUri": "scheme://x",
    "PromptName": "Prompt",
    "promptName": "prompt",
    "prompt-name": "prompt",
    "PromptTitle": "Prompt",
    "PromptTemplate": "tmpl",
    "RecordName": "Record",
    "FieldName": "field",
    "paramName": "param",
    "ParamDescription": "desc",
    "argName": "arg",
    "ArgDescription": "desc",
    "table_name": "widgets",
    "project_id": "proj",
    "group_ids": "g1",
    "APIVersion": "v1",
    "DefaultRole": "admin",
    "protocol": "https",
    "path": "/x",
    "port": "8080",
    "LocalEndpoint": "http://x",
    "service-path": "svc",
    "falkordb_port": "6379",
    "falkordb_host": "localhost",
    "DefaultModel": "model",
    "AbsoluteProjectPath": "/tmp/x",
    "AdversarialIntensity": "full",
    "AcceptanceThreshold": "0.7",
    "MaxRetries": "3",
}

# A safe identifier substituted for any *bare* ``{{...}}`` token still present
# after the named registry runs — i.e. a placeholder the registry does not name
# but which carries no Jinja block/filter/call syntax. This keeps a
# registry gap (an unknown-but-simple placeholder) from producing a *false*
# parse error, while real Jinja (``{% %}``, ``| filter``, calls) is left intact
# so it fails the parse and is forced onto the opt-out path. The gate is a
# syntax check, not a placeholder-completeness check.
_FALLBACK_TOKEN = "Xph"
_FALLBACK_RE = re.compile(r"\{\{[^%|(){}]*?\}\}")

# Inline opt-out marker — a template author writes this literal anywhere in a
# non-parseable-by-design file (e.g. inside a comment) to exclude it from the
# parse tier.
OPTOUT_MARKER = "guardkit:template-parse:optout"

# ---------------------------------------------------------------------------
# Seed opt-out registry (DATA)
# ---------------------------------------------------------------------------
#
# Keys are template-base-relative POSIX paths (``<template-name>/<...>``). Each
# value is the reason. Seeded from analysis of the shipped templates: the only
# non-parseable-by-design *code* files are two Next.js JSX fragments whose braces
# interleave a JSX expression, a ``{{Key}}`` placeholder, and a JS template
# literal (``{{`{${entityNamePlural}}`}}``) — literal substitution cannot yield
# valid TSX for those; the real install-time engine handles them contextually.
# Prefer the inline OPTOUT_MARKER for new files; this registry covers pinned or
# not-easily-annotated files.
PARSE_OPTOUT: Dict[str, str] = {
    "nextjs-fullstack/templates/app/page-server-component.tsx.template": (
        "JSX with a placeholder nested inside a JS template literal "
        "(`{{`{${entityNamePlural}}`}}`) — not renderable by literal substitution"
    ),
    "nextjs-fullstack/templates/components/EntityList.tsx.template": (
        "JSX with placeholders nested inside JSX-expression braces "
        "(`{{{entityNamePlural}}.map(...)`) — not renderable by literal substitution"
    ),
}


class ParseGateUnavailable(RuntimeError):
    """Raised when the tree-sitter runtime needed to parse is not installed.

    Deliberately distinct from a passing result: a gate that could not run is
    NOT green (absence-of-failure-is-not-success). Install the deps with
    ``pip install 'guardkit-py[templates]'``.
    """


class FileStatus(str, Enum):
    OK = "ok"           # rendered and parsed with no ERROR/MISSING nodes
    ERROR = "error"     # rendered output has parse errors — the gate failure
    OPTOUT = "optout"   # explicitly excluded (marker or registry)
    SKIPPED = "skipped"  # not a gated language (config/docs) — NOT a pass


@dataclass(frozen=True)
class ParseFinding:
    """One ERROR / MISSING node in a rendered file."""

    line: int
    column: int
    kind: str          # "ERROR" or "MISSING"
    snippet: str


@dataclass(frozen=True)
class FileResult:
    rel_path: str      # template-base-relative POSIX path of the source file
    language: Optional[str]
    status: FileStatus
    findings: List[ParseFinding] = field(default_factory=list)
    reason: str = ""   # opt-out reason or skip reason


@dataclass(frozen=True)
class GateResult:
    files: List[FileResult]

    @property
    def errors(self) -> List[FileResult]:
        return [f for f in self.files if f.status is FileStatus.ERROR]

    @property
    def ok(self) -> bool:
        return not self.errors

    def counts(self) -> Dict[str, int]:
        out = {s.value: 0 for s in FileStatus}
        for f in self.files:
            out[f.status.value] += 1
        return out


# ---------------------------------------------------------------------------
# Rendering + parsing
# ---------------------------------------------------------------------------


def render_for_parse(
    source: str, placeholders: Optional[Mapping[str, str]] = None
) -> str:
    """Render a scaffold file for a syntax check.

    Applies the named :data:`SAMPLE_PLACEHOLDERS` registry, then normalizes any
    remaining *bare* ``{{...}}`` token (no Jinja block/filter/call syntax) to a
    safe identifier so a registry gap does not false-positive. Real Jinja is left
    verbatim so it fails the parse and is routed to opt-out.
    """
    placeholders = placeholders if placeholders is not None else SAMPLE_PLACEHOLDERS
    rendered = render_text(source, placeholders)
    return _FALLBACK_RE.sub(_FALLBACK_TOKEN, rendered)


def language_for_rendered_name(rendered_name: str) -> Optional[str]:
    """Return the tree-sitter language for a rendered file name, or None."""
    return LANGUAGE_BY_EXT.get(Path(rendered_name).suffix)


_PARSERS: Dict[str, object] = {}


def _get_parser(language: str):
    """Return a cached tree-sitter parser for ``language``.

    ONE parser instance per language, reused across every file — the single
    tree-sitter engine mandated by stack-plugin-architecture.md.

    The parser is built against the **stable ``tree_sitter`` 0.25 API**
    (``tree_sitter.Parser(tree_sitter.Language)``) using the grammar handle from
    ``tree_sitter_language_pack.get_language`` — NOT the pack's own
    ``get_parser``. As of tree-sitter-language-pack 1.10.9 the pack rewrote
    ``get_parser`` to return a native Rust binding whose surface diverges from
    the documented ``tree_sitter`` API (``parse`` wants ``str`` not ``bytes``,
    ``root_node`` is a method, nodes expose ``.kind``/``.start_position``
    instead of ``.type``/``.start_point``). ``get_language`` still yields a real
    ``tree_sitter.Language``, so pairing it with ``tree_sitter.Parser`` keeps
    this module on the stable API the node walker (``_collect_error_findings``)
    is written against, independent of the pack's binding choice. The
    compat-guard test (``test_parse_gate_ts025_compat``) exercises a real parse
    per grammar so a future lock bump that breaks this pairing fails loud in CI
    rather than silently killing the gate.
    """
    parser = _PARSERS.get(language)
    if parser is None:
        try:
            from tree_sitter import Parser
            from tree_sitter_language_pack import get_language
        except ImportError as exc:  # pragma: no cover - exercised via CLI message
            raise ParseGateUnavailable(
                "tree-sitter runtime not installed. Install with "
                "`pip install 'guardkit-py[templates]'`."
            ) from exc
        parser = Parser(get_language(language))
        _PARSERS[language] = parser
    return parser


def available_languages() -> bool:
    """True if the tree-sitter runtime is importable (gate can run)."""
    try:
        import tree_sitter  # noqa: F401
        import tree_sitter_language_pack  # noqa: F401
    except ImportError:
        return False
    return True


def _collect_error_findings(source_bytes: bytes, root, limit: int = 5) -> List[ParseFinding]:
    """Walk the tree collecting ERROR / MISSING nodes (up to ``limit``)."""
    findings: List[ParseFinding] = []
    stack = [root]
    while stack and len(findings) < limit:
        node = stack.pop()
        if node.type == "ERROR" or node.is_missing:
            start_row, start_col = node.start_point
            snippet = (
                source_bytes[node.start_byte:node.end_byte]
                .decode("utf-8", "replace")
                .strip()
                .replace("\n", "\\n")
            )
            findings.append(
                ParseFinding(
                    line=start_row + 1,
                    column=start_col + 1,
                    kind="MISSING" if node.is_missing else "ERROR",
                    snippet=snippet[:120],
                )
            )
            # An ERROR subtree's children are noise; don't descend into it.
            if node.type == "ERROR":
                continue
        # Descend (reversed so findings come out roughly top-to-bottom).
        stack.extend(reversed(node.children))
    return findings


def parse_findings(source: str, language: str) -> List[ParseFinding]:
    """Parse ``source`` as ``language`` and return ERROR/MISSING findings."""
    parser = _get_parser(language)
    source_bytes = source.encode("utf-8")
    tree = parser.parse(source_bytes)
    if not tree.root_node.has_error:
        return []
    return _collect_error_findings(source_bytes, tree.root_node)


# ---------------------------------------------------------------------------
# File / template / gate checks
# ---------------------------------------------------------------------------


def _optout_reason(rel_path: str, text: str) -> Optional[str]:
    if OPTOUT_MARKER in text:
        return "inline opt-out marker"
    return PARSE_OPTOUT.get(rel_path)


def check_file(template_file: Path, rel_path: str) -> FileResult:
    """Render and parse a single scaffold file; classify the outcome.

    ``rel_path`` is the template-base-relative POSIX path used for opt-out
    lookup and reporting.
    """
    rendered_name = strip_template_suffix(template_file.name)
    language = language_for_rendered_name(rendered_name)
    if language is None:
        return FileResult(rel_path, None, FileStatus.SKIPPED, reason="not a gated language")

    raw = template_file.read_text(encoding="utf-8", errors="replace")

    reason = _optout_reason(rel_path, raw)
    if reason is not None:
        return FileResult(rel_path, language, FileStatus.OPTOUT, reason=reason)

    rendered = render_for_parse(raw)
    findings = parse_findings(rendered, language)
    status = FileStatus.ERROR if findings else FileStatus.OK
    return FileResult(rel_path, language, status, findings=findings)


def validate_template_dir(template_dir: Path, template_name: str) -> List[FileResult]:
    """Check every scaffold file under one template directory."""
    results: List[FileResult] = []
    for template_file in iter_template_files(template_dir):
        rel = f"{template_name}/{template_file.relative_to(template_dir).as_posix()}"
        results.append(check_file(template_file, rel))
    return results


def _default_templates_base() -> Path:
    from guardkit.templates.resolver import _get_templates_base_dir

    return _get_templates_base_dir()


def list_template_names(templates_base: Optional[Path] = None) -> List[str]:
    """List stack-template directory names (excludes ``common`` scaffolds and
    non-directory payload files)."""
    base = templates_base if templates_base is not None else _default_templates_base()
    names = []
    for child in sorted(base.iterdir()):
        if child.is_dir() and child.name != "common":
            names.append(child.name)
    return names


def validate_templates(
    names: Optional[Iterable[str]] = None,
    templates_base: Optional[Path] = None,
) -> GateResult:
    """Run the parse gate over the named templates (all, by default).

    Raises :class:`ParseGateUnavailable` if the tree-sitter runtime is missing —
    a gate that cannot run must not report green.
    """
    if not available_languages():
        raise ParseGateUnavailable(
            "tree-sitter runtime not installed. Install with "
            "`pip install 'guardkit-py[templates]'`."
        )
    base = templates_base if templates_base is not None else _default_templates_base()
    selected = list(names) if names is not None else list_template_names(base)

    files: List[FileResult] = []
    for name in selected:
        template_dir = base / name
        if not template_dir.is_dir():
            continue
        files.extend(validate_template_dir(template_dir, name))
    return GateResult(files=files)

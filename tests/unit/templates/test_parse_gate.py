"""Unit tests for the deterministic template render+parse gate (DIM1-F4 / PB-8).

Covers:
  * per-language descriptor mapping (DATA);
  * literal render + fallback normalization;
  * tree-sitter ERROR detection per stack;
  * the TASK-LCL-001 class reproducing RED (a mangled import fails the gate);
  * opt-out (inline marker + seed registry) — required before the gate can be red;
  * the whole shipped template set passing or carrying an explicit opt-out;
  * absence-of-failure safety (unsupported ext -> SKIPPED not OK).

The gate needs the tree-sitter runtime; skip the parse-dependent tests when it
is absent so the suite still collects without the ``templates`` extra.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from guardkit.templates.parse_gate import (
    LANGUAGE_BY_EXT,
    FileStatus,
    OPTOUT_MARKER,
    PARSE_OPTOUT,
    ParseGateUnavailable,
    _get_parser,
    available_languages,
    check_file,
    language_for_rendered_name,
    parse_findings,
    render_for_parse,
    validate_templates,
)

requires_treesitter = pytest.mark.skipif(
    not available_languages(),
    reason="tree-sitter runtime not installed (pip install 'guardkit-py[templates]')",
)


# ---------------------------------------------------------------------------
# Descriptor mapping (DATA — no tree-sitter needed)
# ---------------------------------------------------------------------------


class TestLanguageDescriptors:
    @pytest.mark.parametrize(
        ("name", "lang"),
        [
            ("agent.py", "python"),
            ("route.ts", "typescript"),
            ("page.tsx", "tsx"),
            ("helper.js", "javascript"),
            ("Service.cs", "csharp"),
            ("config.yaml", None),
            ("README.md", None),
            ("Dockerfile", None),
        ],
    )
    def test_extension_maps_to_language(self, name, lang):
        assert language_for_rendered_name(name) == lang


class TestRenderForParse:
    def test_named_placeholder_substituted(self):
        out = render_for_parse("class {{ClassName}}: pass")
        assert "{{" not in out
        assert "Widget" in out

    def test_bare_unknown_placeholder_normalized_not_left(self):
        # A placeholder the registry does not name must NOT be left verbatim
        # (that would false-positive); it is normalized to a safe identifier.
        out = render_for_parse("x = {{TotallyUnknownKey}}")
        assert "{{" not in out
        assert "Xph" in out

    def test_real_jinja_left_intact_to_force_optout(self):
        # Filter/block Jinja is left verbatim so it fails the parse and is routed
        # to opt-out rather than silently normalized.
        src = "x = {{ value | default(0) }}"
        assert "|" in render_for_parse(src)


# ---------------------------------------------------------------------------
# Parsing (tree-sitter)
# ---------------------------------------------------------------------------


@requires_treesitter
class TestParseFindings:
    def test_clean_python_no_findings(self):
        assert parse_findings("from deepagents.backends import x\ny = 1\n", "python") == []

    def test_mangled_python_import_flagged(self):
        # The TASK-LCL-001 class as a *syntactic* mangle: a placeholder sweep
        # produced a non-identifier dotted path.
        findings = parse_findings("from scratch-core.backends import x\n", "python")
        assert findings, "mangled import should produce a parse finding"

    def test_literal_lcl001_is_valid_syntax(self):
        # The literal TASK-LCL-001 render is *valid syntax* (runtime failure) —
        # the parse tier does not catch it; the import tier does. This documents
        # why both tiers are kept.
        assert parse_findings("from scratch.backends import x\n", "python") == []

    def test_clean_typescript(self):
        assert parse_findings("import { a } from './b'\nconst x: number = 1\n", "typescript") == []

    def test_mangled_typescript(self):
        assert parse_findings("import { a } from './{{Broken\n", "typescript")

    def test_clean_csharp(self):
        assert parse_findings("namespace N { public class C { } }\n", "csharp") == []

    def test_mangled_csharp(self):
        assert parse_findings("namespace N { public class {{Name} { } }\n", "csharp")


# ---------------------------------------------------------------------------
# check_file: opt-out + skip + the RED repro
# ---------------------------------------------------------------------------


@requires_treesitter
class TestCheckFile:
    def test_ok_python_file(self, tmp_path: Path):
        f = tmp_path / "coach.py.template"
        f.write_text("from deepagents.backends import x\nvalue = {{ClassName}}\n")
        result = check_file(f, "t/coach.py.template")
        assert result.status is FileStatus.OK

    def test_lcl001_class_reproduces_red(self, tmp_path: Path):
        """A template whose placeholder sweep mangled an import fails the gate."""
        f = tmp_path / "search_data.py.template"
        # The over-rewrite: an SDK import turned into a non-identifier path.
        f.write_text("from {{ProjectName}}-core.backends import tool\n")
        result = check_file(f, "t/search_data.py.template")
        assert result.status is FileStatus.ERROR
        assert result.findings

    def test_inline_optout_marker(self, tmp_path: Path):
        f = tmp_path / "fragment.py.template"
        f.write_text(f"# {OPTOUT_MARKER}\nthis is not valid python {{ % for %}}\n")
        result = check_file(f, "t/fragment.py.template")
        assert result.status is FileStatus.OPTOUT
        assert "marker" in result.reason

    def test_registry_optout(self, tmp_path: Path):
        rel = next(iter(PARSE_OPTOUT))
        f = tmp_path / "EntityList.tsx.template"
        f.write_text("garbage {{{ not valid tsx\n")
        result = check_file(f, rel)
        assert result.status is FileStatus.OPTOUT

    def test_non_code_file_skipped_not_ok(self, tmp_path: Path):
        # absence-of-failure: a config file is SKIPPED, never counted OK.
        f = tmp_path / "config.yaml.template"
        f.write_text("name: {{ProjectName}}\n")
        result = check_file(f, "t/config.yaml.template")
        assert result.status is FileStatus.SKIPPED


# ---------------------------------------------------------------------------
# Whole-suite acceptance
# ---------------------------------------------------------------------------


@requires_treesitter
class TestAllShippedTemplates:
    def test_every_template_passes_or_opts_out(self):
        result = validate_templates()
        # No parse errors: every gated file parses or carries an explicit opt-out.
        assert result.ok, "\n".join(
            f"{fr.rel_path}: {[ (x.kind, x.line, x.snippet) for x in fr.findings]}"
            for fr in result.errors
        )
        counts = result.counts()
        # Coverage extended beyond the langchain 3: multiple stacks parsed.
        assert counts["ok"] > 50
        # The seed opt-outs are present and accounted for.
        assert counts["optout"] == len(PARSE_OPTOUT)

    def test_multiple_stacks_covered(self):
        result = validate_templates()
        langs = {fr.language for fr in result.files if fr.status is FileStatus.OK}
        # python + typescript + tsx + csharp all exercised (3/13 -> N/N).
        assert {"python", "typescript", "tsx", "csharp"} <= langs


# ---------------------------------------------------------------------------
# Locked-runtime API compat guard (PARSEGATE-025)
# ---------------------------------------------------------------------------
#
# The gate broke silently under the repo's own uv.lock (tree-sitter 0.25.2 +
# tree-sitter-language-pack 1.10.9) because the pack rewrote get_parser to return
# a native Rust binding whose surface diverges from the documented tree_sitter
# API (parse wants str not bytes; root_node is a method; nodes expose .kind /
# .start_position, not .type / .start_point). parse_gate now pins itself to the
# stable tree_sitter.Parser(get_language(...)) pairing. These tests execute ONE
# REAL PARSE per supported grammar against the LOCKED binding and assert the
# stable node-API surface the walker depends on — so a future lock bump that
# reintroduces the divergence fails LOUD in CI instead of silently killing the
# gate. (Extends O4's "raises rather than reports green" to API mismatch.)

# The five grammars the gate must support (task-named; every LANGUAGE_BY_EXT
# value must be one of these — a new descriptor row without a real parse here is
# a coverage hole).
_SUPPORTED_GRAMMARS = ("python", "typescript", "tsx", "javascript", "csharp")

# A clean, valid one-liner per grammar — must parse with zero ERROR/MISSING.
_CLEAN_SOURCE = {
    "python": "x = 1\n",
    "typescript": "const x: number = 1;\n",
    "tsx": "const x = <div>{1}</div>;\n",
    "javascript": "const x = 1;\n",
    "csharp": "namespace N { public class C { } }\n",
}


@requires_treesitter
class TestTreeSitter025ApiCompat:
    def test_every_descriptor_grammar_is_covered(self):
        # No descriptor row may name a grammar this guard does not exercise.
        assert set(LANGUAGE_BY_EXT.values()) <= set(_SUPPORTED_GRAMMARS)

    @pytest.mark.parametrize("grammar", _SUPPORTED_GRAMMARS)
    def test_real_parse_uses_stable_tree_sitter_api(self, grammar):
        # Build the parser exactly as the gate does, against the locked binding.
        parser = _get_parser(grammar)

        # The stable tree_sitter 0.25 API: parse() takes BYTES (the pack's Rust
        # get_parser wants str and would raise TypeError here — PARSEGATE-025).
        tree = parser.parse(_CLEAN_SOURCE[grammar].encode("utf-8"))

        # root_node is a PROPERTY (the Rust binding exposes it as a method).
        root = tree.root_node

        # The node-API surface _collect_error_findings depends on. Any of these
        # attribute accesses would raise on the divergent Rust binding, so a
        # lock bump that swaps it back in fails loud right here.
        assert isinstance(root.type, str)
        assert root.has_error is False  # clean source -> no ERROR subtree
        assert root.is_missing is False
        assert isinstance(root.children, list)
        row, col = root.start_point  # Point is (row, column) — not start_position
        assert (row, col) == (0, 0)
        assert isinstance(root.start_byte, int)
        assert isinstance(root.end_byte, int)

    @pytest.mark.parametrize("grammar", _SUPPORTED_GRAMMARS)
    def test_real_parse_detects_error_per_grammar(self, grammar):
        # A deliberately mangled render must surface as has_error under the
        # locked binding — the gate's whole reason to exist.
        parser = _get_parser(grammar)
        tree = parser.parse(b"{{Broken(:\n")
        assert tree.root_node.has_error is True


class TestUnavailableRuntime:
    def test_missing_runtime_is_not_a_pass(self, monkeypatch):
        # Simulate the runtime being absent: validate must raise, never return green.
        import guardkit.templates.parse_gate as pg

        monkeypatch.setattr(pg, "available_languages", lambda: False)
        with pytest.raises(ParseGateUnavailable):
            pg.validate_templates()

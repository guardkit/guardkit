"""Tests for the retry_context lib module (TASK-LCL-008).

Validates the two helpers that keep Player→Coach rejection-revision loops
from drifting off-corpus:

- ``build_context_manifest(target, context)`` — structural manifest from the
  original target (file list + scope), or a context-size fallback.
- ``build_retry_input(player_content, issues, context_manifest)`` — single
  user-role ``ainvoke()`` input per the TASK-REV-R2A1 contract.

Coverage Target: >=85%
Test Count: 15+ tests
"""

from __future__ import annotations

import importlib.util
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

# ---------------------------------------------------------------------------
# Load module directly — directory name contains hyphens, not importable.
# ---------------------------------------------------------------------------
_MODULE_PATH = (
    Path(__file__).resolve().parents[3]
    / "installer"
    / "core"
    / "templates"
    / "langchain-deepagents"
    / "lib"
    / "retry_context.py"
)

_loader = SourceFileLoader("_test_retry_context", str(_MODULE_PATH))
_spec = importlib.util.spec_from_loader("_test_retry_context", _loader)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["_test_retry_context"] = _mod
_loader.exec_module(_mod)

build_context_manifest = _mod.build_context_manifest
build_retry_input = _mod.build_retry_input


# ===========================================================================
# build_context_manifest
# ===========================================================================


class TestBuildContextManifest:
    """Structural extraction from target, with context-length fallback."""

    def test_files_list_of_strings(self):
        target = {"files": ["doc1.md", "doc2.md", "doc3.md"]}
        manifest = build_context_manifest(target, "some context")
        assert "doc1.md" in manifest
        assert "doc2.md" in manifest
        assert "doc3.md" in manifest
        assert "Document manifest" in manifest

    def test_documents_list_of_dicts(self):
        target = {"documents": [{"name": "report.pdf"}, {"path": "notes.md"}]}
        manifest = build_context_manifest(target, "some context")
        assert "report.pdf" in manifest
        assert "notes.md" in manifest

    def test_files_preferred_over_documents(self):
        target = {
            "files": ["primary.md"],
            "documents": [{"name": "secondary.md"}],
        }
        manifest = build_context_manifest(target, "")
        assert "primary.md" in manifest
        assert "secondary.md" not in manifest

    def test_scope_included(self):
        target = {"scope": "Only cover European markets"}
        manifest = build_context_manifest(target, "context")
        assert "European markets" in manifest
        assert "Scope" in manifest

    def test_constraints_aliased_to_scope(self):
        target = {"constraints": "Q3 2025 only"}
        manifest = build_context_manifest(target, "context")
        assert "Q3 2025 only" in manifest

    def test_scope_combined_with_files(self):
        target = {
            "files": ["doc.md"],
            "scope": "Only section 3",
        }
        manifest = build_context_manifest(target, "ctx")
        assert "doc.md" in manifest
        assert "Only section 3" in manifest

    def test_fallback_to_context_length(self):
        target = {"id": "test-1"}
        context = "line1\nline2\nline3"
        manifest = build_context_manifest(target, context)
        assert "3 lines" in manifest

    def test_empty_returns_empty_string(self):
        manifest = build_context_manifest({}, "")
        assert manifest == ""

    def test_unknown_file_shape_stringified(self):
        """Dict without name/path falls back to str(f)."""
        target = {"files": [{"id": "42"}]}
        manifest = build_context_manifest(target, "")
        assert "{'id': '42'}" in manifest or "42" in manifest


# ===========================================================================
# build_retry_input
# ===========================================================================


class TestBuildRetryInput:
    """ainvoke() contract: single user-role message, never a system message."""

    def test_basic_structure(self):
        result = build_retry_input("prev output", ["issue1", "issue2"])
        assert "messages" in result
        assert len(result["messages"]) == 1
        msg = result["messages"][0]
        assert msg["role"] == "user"
        assert "issue1; issue2" in msg["content"]
        assert "prev output" in msg["content"]

    def test_never_uses_system_role(self):
        """TASK-REV-R2A1: create_agent() prepends system_prompt unconditionally.

        Input must never contain system messages or vLLM rejects with HTTP 400.
        """
        result = build_retry_input("x", ["y"], context_manifest="z")
        for msg in result["messages"]:
            assert msg["role"] != "system"

    def test_context_manifest_included(self):
        manifest = "### Document manifest\n- a.md\n- b.md"
        result = build_retry_input(
            "content", ["bad quality"], context_manifest=manifest,
        )
        body = result["messages"][0]["content"]
        assert "a.md" in body
        assert "b.md" in body
        assert "Available Context" in body

    def test_no_context_manifest_omits_section(self):
        result = build_retry_input("content", ["issue"])
        body = result["messages"][0]["content"]
        assert "Available Context" not in body

    def test_empty_context_manifest_omits_section(self):
        """Empty string is falsy — should suppress the section."""
        result = build_retry_input("content", ["issue"], context_manifest="")
        body = result["messages"][0]["content"]
        assert "Available Context" not in body

    def test_preserves_player_output(self):
        prev = "the Player's prior multi-line\noutput that must appear"
        result = build_retry_input(prev, ["feedback"])
        body = result["messages"][0]["content"]
        assert prev in body

    def test_feedback_joined_with_semicolons(self):
        result = build_retry_input("x", ["alpha", "beta", "gamma"])
        body = result["messages"][0]["content"]
        assert "alpha; beta; gamma" in body

    def test_empty_issues_list(self):
        """No issues → empty feedback string; function must not raise."""
        result = build_retry_input("content", [])
        body = result["messages"][0]["content"]
        assert "Feedback:" in body

    def test_rejection_header_present(self):
        """The framing nudges the model to revise rather than restart."""
        result = build_retry_input("x", ["y"])
        body = result["messages"][0]["content"]
        assert "rejected by the Coach" in body
        assert "Do NOT discard existing work" in body

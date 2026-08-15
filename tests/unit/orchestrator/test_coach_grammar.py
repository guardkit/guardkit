"""Unit tests for ``guardkit.orchestrator.coach_grammar`` (TASK-CMIR-003).

Covers:

* ``resolve_coach_contract()`` — env > config.yaml > default precedence
* ``load_coach_verdict_grammar()`` — contract-aware grammar selection
* V4 grammar shape (hermetic structural checks, no llama.cpp)
* Byte-parity between the packaged v4 grammar and the docs source mirror
* Backward compatibility: coachsplit contract loads existing grammars unchanged
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from guardkit.orchestrator import coach_grammar


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_REPO_ROOT = Path(__file__).resolve().parents[3]
_PACKAGED_V4 = (
    _REPO_ROOT / "guardkit" / "orchestrator" / "grammars"
    / "coach-verdict-v4.gbnf"
)
_DOCS_V4 = (
    _REPO_ROOT / "docs" / "research" / "dgx-spark" / "grammars"
    / "coach-verdict-v4.gbnf"
)


def _make_config(tmp_path: Path, content: str) -> Path:
    """Write a .guardkit/config.yaml under *tmp_path* and return its path."""
    config_dir = tmp_path / ".guardkit"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "config.yaml"
    config_file.write_text(content, encoding="utf-8")
    return config_file


# ---------------------------------------------------------------------------
# resolve_coach_contract — Tier 1: env var
# ---------------------------------------------------------------------------


class TestResolveEnvTier:
    def test_env_coachsplit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GUARDKIT_COACH_CONTRACT", "coachsplit")
        # Ensure no config.yaml interferes.
        monkeypatch.delenv("GUARDKIT_COACH_CONTRACT", raising=False)
        monkeypatch.setenv("GUARDKIT_COACH_CONTRACT", "coachsplit")
        with patch.object(coach_grammar, "Path") as mock_path:
            mock_path.side_effect = FileNotFoundError
            result = coach_grammar.resolve_coach_contract()
        assert result == "coachsplit"

    def test_env_v4(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GUARDKIT_COACH_CONTRACT", "v4")
        with patch.object(coach_grammar, "Path") as mock_path:
            mock_path.side_effect = FileNotFoundError
            result = coach_grammar.resolve_coach_contract()
        assert result == "v4"

    def test_env_unrecognised_falls_through(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("GUARDKIT_COACH_CONTRACT", "unknown")
        _make_config(tmp_path, "autobuild:\n  coach:\n    contract: v4\n")
        monkeypatch.chdir(tmp_path)
        # clear the lru_cache so we get a fresh resolve
        coach_grammar.load_coach_verdict_grammar.cache_clear()
        result = coach_grammar.resolve_coach_contract()
        assert result == "v4"

    def test_env_empty_falls_through(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("GUARDKIT_COACH_CONTRACT", "")
        _make_config(tmp_path, "autobuild:\n  coach:\n    contract: v4\n")
        monkeypatch.chdir(tmp_path)
        coach_grammar.load_coach_verdict_grammar.cache_clear()
        result = coach_grammar.resolve_coach_contract()
        assert result == "v4"

    def test_env_unset_falls_through(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.delenv("GUARDKIT_COACH_CONTRACT", raising=False)
        _make_config(tmp_path, "autobuild:\n  coach:\n    contract: v4\n")
        monkeypatch.chdir(tmp_path)
        coach_grammar.load_coach_verdict_grammar.cache_clear()
        result = coach_grammar.resolve_coach_contract()
        assert result == "v4"


# ---------------------------------------------------------------------------
# resolve_coach_contract — Tier 2: config.yaml
# ---------------------------------------------------------------------------


class TestResolveConfigTier:
    def test_config_v4(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GUARDKIT_COACH_CONTRACT", raising=False)
        _make_config(tmp_path, "autobuild:\n  coach:\n    contract: v4\n")
        monkeypatch.chdir(tmp_path)
        coach_grammar.load_coach_verdict_grammar.cache_clear()
        assert coach_grammar.resolve_coach_contract() == "v4"

    def test_config_coachsplit(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GUARDKIT_COACH_CONTRACT", raising=False)
        _make_config(tmp_path, "autobuild:\n  coach:\n    contract: coachsplit\n")
        monkeypatch.chdir(tmp_path)
        coach_grammar.load_coach_verdict_grammar.cache_clear()
        assert coach_grammar.resolve_coach_contract() == "coachsplit"

    def test_config_unrecognised_falls_to_default(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GUARDKIT_COACH_CONTRACT", raising=False)
        _make_config(tmp_path, "autobuild:\n  coach:\n    contract: unknown\n")
        monkeypatch.chdir(tmp_path)
        coach_grammar.load_coach_verdict_grammar.cache_clear()
        assert coach_grammar.resolve_coach_contract() == "coachsplit"

    def test_config_missing_key_defaults(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GUARDKIT_COACH_CONTRACT", raising=False)
        _make_config(tmp_path, "autobuild:\n  coach:\n    qav_shadow:\n      enabled: true\n")
        monkeypatch.chdir(tmp_path)
        coach_grammar.load_coach_verdict_grammar.cache_clear()
        assert coach_grammar.resolve_coach_contract() == "coachsplit"

    def test_config_missing_file_defaults(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GUARDKIT_COACH_CONTRACT", raising=False)
        monkeypatch.chdir(Path("/tmp"))
        coach_grammar.load_coach_verdict_grammar.cache_clear()
        assert coach_grammar.resolve_coach_contract() == "coachsplit"

    def test_env_precedes_config(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GUARDKIT_COACH_CONTRACT", "v4")
        _make_config(tmp_path, "autobuild:\n  coach:\n    contract: coachsplit\n")
        monkeypatch.chdir(tmp_path)
        coach_grammar.load_coach_verdict_grammar.cache_clear()
        assert coach_grammar.resolve_coach_contract() == "v4"


# ---------------------------------------------------------------------------
# resolve_coach_contract — Tier 3: default
# ---------------------------------------------------------------------------


class TestResolveDefaultTier:
    def test_default_is_coachsplit(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GUARDKIT_COACH_CONTRACT", raising=False)
        monkeypatch.chdir(Path("/tmp"))
        coach_grammar.load_coach_verdict_grammar.cache_clear()
        assert coach_grammar.resolve_coach_contract() == "coachsplit"


# ---------------------------------------------------------------------------
# load_coach_verdict_grammar — contract-aware selection
# ---------------------------------------------------------------------------


class TestGrammarLoadByContract:
    def test_coachsplit_loads_primary(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        coach_grammar.load_coach_verdict_grammar.cache_clear()
        g = coach_grammar.load_coach_verdict_grammar(contract="coachsplit")
        assert "root" in g
        assert "req-task-id" in g
        assert '"approve"' in g and '"feedback"' in g

    def test_strict_flag_loads_strict(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # This asserts the coachsplit strict grammar. With no contract given,
        # the loader resolves one from the CURRENT DIRECTORY's config — and
        # guardkit's own .guardkit/config.yaml pins `contract: v4`, so running
        # the suite from the repo root silently loaded the v4 grammar. Pin the
        # contract this test is actually about.
        monkeypatch.setenv("GUARDKIT_COACH_CONTRACT", "coachsplit")
        coach_grammar.load_coach_verdict_grammar.cache_clear()
        g = coach_grammar.load_coach_verdict_grammar(strict=True)
        assert "root" in g and "prelude" in g

    def test_v4_contract_loads_v4_grammar(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        coach_grammar.load_coach_verdict_grammar.cache_clear()
        g = coach_grammar.load_coach_verdict_grammar(contract="v4")
        assert "root" in g
        assert '"verdict"' in g
        assert '"approve"' in g and '"reject"' in g
        assert '"findings"' in g
        assert '"locus"' in g

    def test_none_contract_resolves_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GUARDKIT_COACH_CONTRACT", "v4")
        coach_grammar.load_coach_verdict_grammar.cache_clear()
        g = coach_grammar.load_coach_verdict_grammar(contract=None)
        assert '"verdict"' in g and '"findings"' in g

    def test_none_contract_resolves_default(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GUARDKIT_COACH_CONTRACT", raising=False)
        _make_config(tmp_path, "autobuild:\n  coach:\n    contract: v4\n")
        monkeypatch.chdir(tmp_path)
        coach_grammar.load_coach_verdict_grammar.cache_clear()
        g = coach_grammar.load_coach_verdict_grammar(contract=None)
        assert '"verdict"' in g and '"findings"' in g


# ---------------------------------------------------------------------------
# V4 grammar shape — hermetic structural checks (no llama.cpp)
# ---------------------------------------------------------------------------


class TestV4GrammarShape:
    """Hermetic string/structural assertions on the v4 grammar.

    These tests verify the grammar enforces the v4 wire shape without
    requiring a running llama.cpp instance.
    """

    @pytest.fixture(autouse=True)
    def _clear_cache(self) -> None:
        coach_grammar.load_coach_verdict_grammar.cache_clear()

    # -- canonical accept cases (shape-level) --

    def test_accepts_approve_empty_findings(self) -> None:
        """{"verdict": "approve", "findings": []} should be accepted."""
        g = coach_grammar.load_coach_verdict_grammar(contract="v4")
        # The grammar root must end at the closing brace (forced EOS).
        assert g.rstrip().endswith("}") or "ws \"}\"" in g or 'ws "}"' in g
        # Must require exactly two keys in order.
        assert '"verdict"' in g
        assert '"findings"' in g
        # Must NOT allow extra keys (no trailing-members production).
        assert "trailing-members" not in g

    def test_accepts_reject_with_locus(self) -> None:
        """A reject with locus strings must be accepted."""
        g = coach_grammar.load_coach_verdict_grammar(contract="v4")
        assert '"reject"' in g
        assert '"locus"' in g
        assert "finding-item" in g

    def test_accepts_escaped_quotes_in_locus(self) -> None:
        """Locus values can contain escaped quotes and unicode escapes."""
        g = coach_grammar.load_coach_verdict_grammar(contract="v4")
        # Extract non-comment lines (grammar rules only).
        rules = "\n".join(
            line for line in g.splitlines() if not line.strip().startswith("#")
        )
        # The char production must support unicode escapes: "u" hex hex hex hex
        assert '"u"' in rules or '"\\u"' in rules

    # -- reject cases (shape-level) --

    def test_rejects_extra_keys(self) -> None:
        """The grammar must forbid keys beyond verdict and findings."""
        g = coach_grammar.load_coach_verdict_grammar(contract="v4")
        # Extract non-comment lines (grammar rules only).
        rules = "\n".join(
            line for line in g.splitlines() if not line.strip().startswith("#")
        )
        # No generic member/extra-key productions.
        assert "member" not in rules
        assert "trailing" not in rules
        assert "extra" not in rules

    def test_rejects_class_key(self) -> None:
        """A 'class' key must not be permitted."""
        g = coach_grammar.load_coach_verdict_grammar(contract="v4")
        assert '"class"' not in g

    def test_rejects_fenced_output(self) -> None:
        """No ```json fence production should exist."""
        g = coach_grammar.load_coach_verdict_grammar(contract="v4")
        # Extract non-comment lines (grammar rules only).
        rules = "\n".join(
            line for line in g.splitlines() if not line.strip().startswith("#")
        )
        assert "```" not in rules
        assert "code-fence" not in rules
        assert "prefix" not in rules

    def test_rejects_prose_before_object(self) -> None:
        """Root must start directly at the JSON object — no prose prefix."""
        g = coach_grammar.load_coach_verdict_grammar(contract="v4")
        # Root production must be: root ::= ws json-object (or similar)
        # No prefix/any-text rule before the object.
        root_lines = [
            line for line in g.splitlines()
            if line.strip().startswith("root")
        ]
        assert len(root_lines) == 1
        root_def = root_lines[0]
        # Must NOT contain a prose prefix rule.
        assert "prefix" not in root_def
        assert "any" not in root_def.lower()


# ---------------------------------------------------------------------------
# Byte-parity: packaged v4 grammar == docs mirror
# ---------------------------------------------------------------------------


class TestV4GrammarParity:
    def test_packaged_v4_is_byte_identical_to_docs_source(self) -> None:
        """The packaged v4 grammar MUST match the docs/research twin."""
        assert _PACKAGED_V4.exists(), f"Missing: {_PACKAGED_V4}"
        assert _DOCS_V4.exists(), f"Missing: {_DOCS_V4}"
        packaged = _PACKAGED_V4.read_text(encoding="utf-8")
        docs = _DOCS_V4.read_text(encoding="utf-8")
        assert packaged == docs, (
            f"V4 grammar parity mismatch:\n"
            f"  packaged: {_PACKAGED_V4}\n"
            f"  docs:     {_DOCS_V4}"
        )

    def test_packaged_grammar_file_is_non_empty(self) -> None:
        assert _PACKAGED_V4.exists()
        assert len(_PACKAGED_V4.read_text(encoding="utf-8")) > 0


# ---------------------------------------------------------------------------
# Backward compatibility: coachsplit path unchanged
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    def test_coachsplit_grammar_loader_signature_unchanged(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """load_coach_verdict_grammar(strict=True) still works as before."""
        # Pin the contract: with none given the loader reads the cwd's config,
        # and guardkit's own config pins v4. See test_strict_flag_loads_strict.
        monkeypatch.setenv("GUARDKIT_COACH_CONTRACT", "coachsplit")
        coach_grammar.load_coach_verdict_grammar.cache_clear()
        # The existing test in test_coach_synthesis_split.py calls:
        #   load_coach_verdict_grammar(strict=True)
        g = coach_grammar.load_coach_verdict_grammar(strict=True)
        assert "root" in g and "code-fence" in g

    def test_coachsplit_default_loader_signature_unchanged(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """load_coach_verdict_grammar() (no args) still works as before."""
        # Pin the contract: with none given the loader reads the cwd's config,
        # and guardkit's own config pins v4. See test_strict_flag_loads_strict.
        monkeypatch.setenv("GUARDKIT_COACH_CONTRACT", "coachsplit")
        coach_grammar.load_coach_verdict_grammar.cache_clear()
        g = coach_grammar.load_coach_verdict_grammar()
        assert "root" in g
        assert "req-task-id" in g
        assert "req-turn" in g
        assert '"approve"' in g and '"feedback"' in g

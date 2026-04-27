"""Unit tests for section_01_manifest's stale-upper-bound python pin warning.

Seeded by TASK-ABSR-E5F6 (LangChain DeepAgents template pin standardisation).
Reference: docs/guides/portfolio-python-pinning.md
"""

import json
from pathlib import Path

from installer.core.lib.template_validation.sections.section_01_manifest import (
    LATEST_STABLE_PYTHON_MINOR,
    ManifestAnalysisSection,
    _LANGCHAIN_DEEPAGENTS_TEMPLATE_NAMES,
)
from installer.core.lib.template_validation.models import IssueSeverity


# ----- _stale_upper_bound -------------------------------------------------- #

class TestStaleUpperBound:
    """Pure parser: PEP-440 upper bound vs latest stable Python minor."""

    def test_open_upper_bound_is_not_stale(self):
        assert ManifestAnalysisSection._stale_upper_bound(">=3.11") is None

    def test_jarvis_fingerprint_is_stale(self):
        # The actual Jarvis pin that produced the FEAT-J004-702C stall.
        assert ManifestAnalysisSection._stale_upper_bound(">=3.12,<3.13") == (3, 13)

    def test_excluding_latest_stable_is_stale(self):
        major, minor = LATEST_STABLE_PYTHON_MINOR
        assert ManifestAnalysisSection._stale_upper_bound(
            f">=3.11,<{major}.{minor}"
        ) == (major, minor)

    def test_future_upper_bound_is_not_stale(self):
        major, minor = LATEST_STABLE_PYTHON_MINOR
        future = f">=3.11,<{major}.{minor + 1}"
        assert ManifestAnalysisSection._stale_upper_bound(future) is None

    def test_python_4_upper_is_not_currently_stale(self):
        # Python 4.x is not released; <4.0 is forward-looking, not stale.
        assert ManifestAnalysisSection._stale_upper_bound(">=3.11,<4.0") is None

    def test_handles_whitespace_and_patch_version(self):
        assert ManifestAnalysisSection._stale_upper_bound(">=3.11, < 3.13.0") == (3, 13)


# ----- _is_langchain_deepagents_derived ------------------------------------ #

class TestLangChainDeepAgentsDetection:
    def test_base_template_matches(self):
        assert ManifestAnalysisSection._is_langchain_deepagents_derived(
            {"name": "langchain-deepagents"}
        )

    def test_orchestrator_template_matches(self):
        assert ManifestAnalysisSection._is_langchain_deepagents_derived(
            {"name": "langchain-deepagents-orchestrator"}
        )

    def test_weighted_evaluation_template_matches(self):
        assert ManifestAnalysisSection._is_langchain_deepagents_derived(
            {"name": "langchain-deepagents-weighted-evaluation"}
        )

    def test_extends_chain_matches(self):
        assert ManifestAnalysisSection._is_langchain_deepagents_derived(
            {"name": "downstream-thing", "extends": "langchain-deepagents"}
        )

    def test_unrelated_template_does_not_match(self):
        assert not ManifestAnalysisSection._is_langchain_deepagents_derived(
            {"name": "fastapi-python"}
        )

    def test_empty_manifest_does_not_match(self):
        assert not ManifestAnalysisSection._is_langchain_deepagents_derived({})

    def test_known_names_set_is_complete(self):
        # Belt-and-braces: catch silent regressions in the canonical name set.
        assert "langchain-deepagents" in _LANGCHAIN_DEEPAGENTS_TEMPLATE_NAMES
        assert "langchain-deepagents-orchestrator" in _LANGCHAIN_DEEPAGENTS_TEMPLATE_NAMES
        assert (
            "langchain-deepagents-weighted-evaluation"
            in _LANGCHAIN_DEEPAGENTS_TEMPLATE_NAMES
        )


# ----- _validate_python_pin (integration over template tree) --------------- #

class TestValidatePythonPin:
    """Exercise the full check against synthetic template directories."""

    def _make_template(
        self,
        tmp_path: Path,
        manifest: dict,
        requires_python: str | None = None,
    ) -> Path:
        template_dir = tmp_path / manifest.get("name", "synthetic")
        template_dir.mkdir(parents=True)
        (template_dir / "manifest.json").write_text(json.dumps(manifest))
        if requires_python is not None:
            pyproject_dir = template_dir / "templates" / "other" / "other"
            pyproject_dir.mkdir(parents=True)
            (pyproject_dir / "pyproject.toml.template").write_text(
                f'[project]\nrequires-python = "{requires_python}"\n'
            )
        return template_dir

    def test_silent_for_non_langchain_template(self, tmp_path):
        template = self._make_template(
            tmp_path,
            {"name": "fastapi-python", "language_version": ">=3.10,<3.13"},
            requires_python=">=3.10,<3.13",
        )
        section = ManifestAnalysisSection()
        manifest = json.loads((template / "manifest.json").read_text())
        issues, _ = section._validate_python_pin(manifest, template)
        assert issues == [], "non-LangChain templates must not be flagged"

    def test_silent_for_canonical_pin(self, tmp_path):
        template = self._make_template(
            tmp_path,
            {"name": "langchain-deepagents", "language_version": ">=3.11"},
            requires_python=">=3.11",
        )
        section = ManifestAnalysisSection()
        manifest = json.loads((template / "manifest.json").read_text())
        issues, _ = section._validate_python_pin(manifest, template)
        assert issues == [], "canonical >=3.11 must not be flagged"

    def test_warns_on_stale_manifest_language_version(self, tmp_path):
        template = self._make_template(
            tmp_path,
            {"name": "langchain-deepagents", "language_version": ">=3.11,<3.13"},
            requires_python=">=3.11",
        )
        section = ManifestAnalysisSection()
        manifest = json.loads((template / "manifest.json").read_text())
        issues, _ = section._validate_python_pin(manifest, template)
        assert len(issues) == 1
        assert issues[0].severity == IssueSeverity.LOW
        assert "manifest.json:language_version" in issues[0].location
        assert "<3.13" in issues[0].message

    def test_warns_on_stale_pyproject_template(self, tmp_path):
        # Canonical manifest pin but a stale pyproject.toml.template — the
        # check must catch the rendered-output drift, not just the manifest.
        template = self._make_template(
            tmp_path,
            {"name": "langchain-deepagents", "language_version": ">=3.11"},
            requires_python=">=3.12,<3.13",
        )
        section = ManifestAnalysisSection()
        manifest = json.loads((template / "manifest.json").read_text())
        issues, _ = section._validate_python_pin(manifest, template)
        assert len(issues) == 1
        assert "pyproject.toml.template:requires-python" in issues[0].location

    def test_warns_on_extends_chain(self, tmp_path):
        # Templates that extend langchain-deepagents inherit the standard.
        template = self._make_template(
            tmp_path,
            {
                "name": "downstream-extension",
                "extends": "langchain-deepagents",
                "language_version": ">=3.11,<3.13",
            },
        )
        section = ManifestAnalysisSection()
        manifest = json.loads((template / "manifest.json").read_text())
        issues, _ = section._validate_python_pin(manifest, template)
        assert len(issues) == 1

    def test_check_is_non_blocking(self, tmp_path):
        # AC: "The warning is informational — does not block the validation."
        # i.e. severity is LOW, not HIGH/CRITICAL.
        template = self._make_template(
            tmp_path,
            {"name": "langchain-deepagents", "language_version": ">=3.11,<3.13"},
        )
        section = ManifestAnalysisSection()
        manifest = json.loads((template / "manifest.json").read_text())
        issues, _ = section._validate_python_pin(manifest, template)
        assert all(i.severity == IssueSeverity.LOW for i in issues)


# ----- Integration: real shipped templates --------------------------------- #

class TestShippedTemplatesAreClean:
    """Regression guard: the templates this task standardised must stay clean."""

    REPO_ROOT = Path(__file__).resolve().parents[2]
    TEMPLATES = [
        "installer/core/templates/langchain-deepagents",
        "installer/core/templates/langchain-deepagents-orchestrator",
        "installer/core/templates/langchain-deepagents-weighted-evaluation",
    ]

    def test_no_stale_pin_warnings_in_shipped_templates(self):
        section = ManifestAnalysisSection()
        for rel in self.TEMPLATES:
            template = self.REPO_ROOT / rel
            if not template.exists():
                continue
            manifest = json.loads((template / "manifest.json").read_text())
            issues, _ = section._validate_python_pin(manifest, template)
            assert issues == [], (
                f"Template {rel} carries a stale upper-bound pin: "
                f"{[i.message for i in issues]}"
            )

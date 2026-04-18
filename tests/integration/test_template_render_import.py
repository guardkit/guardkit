"""Smoke test: render each in-scope template and import its declared entrypoints.

Purpose (TASK-LCL-003, FEAT-LTL1):
    Catch broken imports in ``.template`` scaffold files at template-update time
    rather than post-release. TASK-LCL-001 landed a regression where the
    ``{{ProjectName}}`` placeholder sweep over-rewrote SDK imports
    (``from deepagents.backends`` → ``from {{ProjectName}}.backends``). After
    rendering, ``import <project>.backends`` fails with ``ModuleNotFoundError``,
    but no existing test renders the template and imports it, so the bug shipped.

Interface contract:
    - Consumes the raw ``.template`` files under ``installer/core/templates/<name>/``.
      It does NOT call ``guardkit init`` (that CLI deliberately skips ``.template``
      scaffold files — see ``guardkit.cli.init.apply_template``). If the installer
      ever grows a first-class ``.template`` renderer (``guardkit render`` or an
      importable ``render_template(...)`` API), swap the local ``_render_template``
      helper for it — see ``_RENDER_IMPL`` sentinel.
    - For each template in ``TEMPLATES``, the test renders ``.template`` files into
      a ``tmp_path`` scratch tree with ``{{ProjectName}}=scratch`` and invokes a
      subprocess ``python -c "import scratch.<entry>"`` per declared entrypoint.
      Exit code 0 = pass.
    - Entrypoints are maintained as an explicit ``ENTRYPOINTS_BY_TEMPLATE`` dict
      so that silent entrypoint discovery failures cannot mask a regression.

Skip conditions (clear message on each):
    - Template runtime deps (``deepagents``, ``langchain``, …) not importable in
      the test environment. These are NOT guardkit's deps; they belong to the
      generated project. Skipping here is expected in CI unless the langchain
      template deps are installed explicitly.
    - Template source directory missing (e.g. template removed from the repo).

Negative-test proof (TestNegative):
    Breaks one rendered file and asserts the import subprocess fails. Proves the
    positive assertion is actually exercised and not silently passing.

Run:
    pytest tests/integration/test_template_render_import.py -v
    pytest -m integration  # run with all integration tests

Coverage Target: the test covers scaffold correctness, not product code, so
coverage metrics are not reported here.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import pytest


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES_ROOT = REPO_ROOT / "installer" / "core" / "templates"


# ---------------------------------------------------------------------------
# Per-template configuration
# ---------------------------------------------------------------------------
#
# Each entry declares:
#   - entrypoints: modules to import via ``python -c "import scratch.<mod>"``.
#     Order matters — first failure aborts the subprocess, giving a focused
#     error message.
#   - runtime_deps: top-level packages the rendered scaffold imports at module
#     load time. If any is missing, the test skips.
#   - placeholders: literal ``{{Key}}`` → value substitutions applied to every
#     ``.template`` file. ``ProjectName`` must be a valid Python identifier so
#     that ``scratch.<entry>`` is importable.
#   - layout: list of (source_prefix, target_prefix) pairs describing how
#     ``installer/core/templates/<name>/<source_prefix>*.template`` files are
#     relocated into the rendered tree, keyed by longest-prefix match. Python
#     package directories land under ``scratch/`` (target_prefix ``scratch``
#     or ``scratch/<subpkg>``). Non-Python project files land at the tree root.
#     A ``None`` target means "skip this file" (e.g. testing/ scaffolding).
#
# Adding a template:
#   1. Pick the module(s) the template documents as entrypoint(s). For
#      ``langchain-deepagents`` those are ``coach`` and ``player`` (the
#      ``agent`` module has heavy module-level wiring that depends on
#      ``agent-config.yaml`` and live LLM/domain files, so it is covered by
#      the rendered scaffold's own runtime tests, not by this smoke test).
#   2. List its runtime deps (the SDK packages it imports).
#   3. Map each ``templates/`` subtree to its target in the scratch project.


@dataclass(frozen=True)
class EntrypointCase:
    """One module to import after rendering.

    ``xfail_reason`` is set when the entrypoint is known to transitively fail
    on a still-unfixed template regression (e.g. TASK-LCL-001). pytest reports
    the failure as ``XFAIL`` today and as ``XPASS`` once the regression is
    fixed, prompting removal of the marker.
    """

    module: str
    xfail_reason: Optional[str] = None


@dataclass(frozen=True)
class TemplateCase:
    name: str
    entrypoints: List[EntrypointCase]
    runtime_deps: List[str]
    placeholders: Dict[str, str] = field(default_factory=dict)
    # (source_prefix_relative_to_template_root, target_prefix_relative_to_scratch_project_root)
    # target_prefix=None means skip.
    layout: List[tuple] = field(default_factory=list)


_DEFAULT_PLACEHOLDERS = {
    "ProjectName": "scratch",
    "Namespace": "scratch",
    "Author": "Test",
    # Some templates include Jinja2-style class placeholders in testing scaffolds;
    # they are not exercised here (testing/ is not imported), but substituting a
    # safe default avoids accidental syntax errors if a file ends up in the tree.
    "ClassName": "TestRendered",
    "DomainName": "example-domain",
    "AdversarialIntensity": "full",
    "AcceptanceThreshold": "0.7",
    "MaxRetries": "3",
}


# Layout for langchain-deepagents (base template).
# Derived by grepping ``from {{ProjectName}}.X`` imports in the template:
#   - coach.py imports ``{{ProjectName}}.coach_prompts``
#   - player.py imports ``{{ProjectName}}.player_prompts``, ``.search_data``,
#     ``.scaffold.orchestrator_pattern``
#   - agent.py imports ``{{ProjectName}}.coach``, ``.player``,
#     ``.scaffold.orchestrator_pattern``, ``.write_output``
# so agents/, prompts/, tools/ flatten into the package root; scaffold/ is
# preserved as a subpackage.
_LCD_LAYOUT = [
    # Top-level Python entrypoint module
    ("templates/other/other/agent.py.template", "scratch/agent.py"),
    # Project configuration files (kept at tree root so _load_config finds them)
    ("templates/other/other/agent-config.yaml.template", "agent-config.yaml"),
    ("templates/other/other/langgraph.json.template", "langgraph.json"),
    ("templates/other/other/pyproject.toml.template", "pyproject.toml"),
    ("templates/other/other/AGENTS.md.template", "AGENTS.md"),
    ("templates/other/other/.env.example.template", ".env.example"),
    # Package directories — flattened into scratch/ because that is how the
    # rendered imports resolve.
    ("templates/other/agents/", "scratch/"),
    ("templates/other/prompts/", "scratch/"),
    ("templates/other/tools/", "scratch/"),
    # Preserved subpackage
    ("templates/other/scaffold/", "scratch/scaffold/"),
    # Domain assets (consumed by agent.py _load_domain_prompt)
    ("templates/other/example-domain/", "domains/example-domain/"),
    # Skip testing scaffold — it uses mock-style imports like
    # ``from {{ProjectName}}.mock import MagicMock`` that intentionally do not
    # resolve in a freshly-rendered project.
    ("templates/testing/", None),
]


TEMPLATES: List[TemplateCase] = [
    TemplateCase(
        name="langchain-deepagents",
        # Library modules reproduce the TASK-LCL-001 failure surface without
        # requiring live LLM / config files:
        #   - coach imports deepagents.{backends,middleware} and
        #     {{ProjectName}}.coach_prompts (clean chain).
        #   - player imports deepagents.{backends,middleware}, plus
        #     {{ProjectName}}.{player_prompts, search_data,
        #     scaffold.orchestrator_pattern}. The transitive ``search_data.py``
        #     contains ``from {{ProjectName}}.tools import tool`` — after
        #     render that becomes ``from scratch.tools import tool`` which is
        #     the bug TASK-LCL-001 fixes. Marked xfail until LCL-001 lands.
        entrypoints=[
            EntrypointCase(module="scratch.coach"),
            EntrypointCase(
                module="scratch.player",
                xfail_reason=(
                    "Blocked on TASK-LCL-001: search_data.py.template has "
                    "`from {{ProjectName}}.tools import tool` which renders to "
                    "`from scratch.tools import tool` (should be "
                    "`from langchain_core.tools import tool`). Remove this "
                    "xfail once LCL-001 merges."
                ),
            ),
        ],
        runtime_deps=[
            "langchain",
            "langchain_anthropic",
            "deepagents",
        ],
        placeholders=dict(_DEFAULT_PLACEHOLDERS),
        layout=_LCD_LAYOUT,
    ),
]


def _entrypoint_params():
    """Flatten TEMPLATES into (template_case, entrypoint_case) parameter tuples."""
    params = []
    ids = []
    for tc in TEMPLATES:
        for ep in tc.entrypoints:
            marks = []
            if ep.xfail_reason:
                marks.append(pytest.mark.xfail(reason=ep.xfail_reason, strict=True))
            params.append(pytest.param(tc, ep, marks=marks))
            ids.append(f"{tc.name}::{ep.module}")
    return params, ids


# ---------------------------------------------------------------------------
# Render + import helpers
# ---------------------------------------------------------------------------


def _render_text(source: str, placeholders: Dict[str, str]) -> str:
    """Substitute ``{{Key}}`` placeholders. Simple string replacement, no Jinja."""
    rendered = source
    for key, value in placeholders.items():
        rendered = rendered.replace("{{" + key + "}}", value)
    return rendered


def _resolve_target(
    src_rel: Path, layout: List[tuple]
) -> Optional[Path]:
    """Map a source path under ``installer/core/templates/<name>/`` to its
    target under the scratch project root.

    Uses longest-prefix match against ``layout``. ``None`` target = skip.
    Returns the project-relative destination with ``.template`` stripped.
    """
    src_str = src_rel.as_posix()

    # Longest match wins — order layout specific-to-general at construction time
    best_prefix = ""
    best_target = ""
    matched = False
    for source_prefix, target in layout:
        if src_str == source_prefix or src_str.startswith(source_prefix):
            if len(source_prefix) > len(best_prefix):
                best_prefix = source_prefix
                best_target = target
                matched = True

    if not matched:
        return None
    if best_target is None:
        return None

    # Exact file mapping (source_prefix was a file)
    if best_prefix.endswith(".template"):
        dest_str = best_target
    else:
        # Directory mapping — replace the prefix and strip .template suffix
        suffix = src_str[len(best_prefix):]
        dest_str = best_target + suffix
        if dest_str.endswith(".template"):
            dest_str = dest_str[: -len(".template")]

    return Path(dest_str)


def _render_template(
    template_root: Path,
    case: TemplateCase,
    output_root: Path,
) -> List[Path]:
    """Render every ``.template`` file in ``template_root`` into ``output_root``
    according to ``case.layout`` and ``case.placeholders``.

    Returns the list of rendered file paths (relative to ``output_root``).

    This is the local render shim that stands in for an installer-level
    ``.template`` renderer. If guardkit ever gains one, replace the body of
    this function with a call to it — the surrounding test logic does not care.
    """
    _RENDER_IMPL = "local"  # noqa: F841 — sentinel for future grep

    rendered: List[Path] = []
    for template_path in sorted(template_root.rglob("*.template")):
        src_rel = template_path.relative_to(template_root)
        dest_rel = _resolve_target(src_rel, case.layout)
        if dest_rel is None:
            continue

        content = template_path.read_text(encoding="utf-8")
        rendered_content = _render_text(content, case.placeholders)

        dest_abs = output_root / dest_rel
        dest_abs.parent.mkdir(parents=True, exist_ok=True)
        dest_abs.write_text(rendered_content, encoding="utf-8")
        rendered.append(dest_rel)

    return rendered


def _runtime_deps_available(deps: List[str]) -> Optional[str]:
    """Return None if every dep is importable in the current Python env;
    otherwise return the first missing dep name.
    """
    for dep in deps:
        if importlib.util.find_spec(dep) is None:
            return dep
    return None


def _run_import_check(
    project_dir: Path,
    entrypoints: List[str],
) -> subprocess.CompletedProcess:
    """Spawn a subprocess importing each entrypoint in order.

    Running in a subprocess (rather than in-process) is deliberate:
      - Isolates ``sys.modules`` pollution across parametrised cases.
      - Mirrors what a developer would see running ``python -c ...`` at the
        CLI after scaffolding a fresh project.
      - Prevents side effects (module-level code) from leaking into the
        pytest process.
    """
    import_statements = "; ".join(f"import {ep}" for ep in entrypoints)
    script = f"import sys; sys.path.insert(0, '.'); {import_statements}"

    env = os.environ.copy()
    # Keep PYTHONPATH minimal — we want ``import scratch.X`` to resolve via
    # cwd only, not from any ambient path configuration.
    env.pop("PYTHONPATH", None)

    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(project_dir),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


# ---------------------------------------------------------------------------
# Per-template structural checks
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.parametrize(
    "case",
    TEMPLATES,
    ids=[c.name for c in TEMPLATES],
)
class TestTemplateStructure:
    """Structural sanity checks per template (cheap, no subprocess)."""

    def test_template_source_dir_exists(self, case: TemplateCase) -> None:
        """Fail loud if the template directory has been removed or renamed."""
        template_dir = TEMPLATES_ROOT / case.name
        assert template_dir.is_dir(), (
            f"Template source directory missing: {template_dir}\n"
            f"Expected under {TEMPLATES_ROOT}. If the template was renamed, "
            f"update TEMPLATES in this test."
        )

    def test_entrypoints_declared(self, case: TemplateCase) -> None:
        """Guard against silent entrypoint-discovery failure."""
        assert case.entrypoints, (
            f"Template '{case.name}' has no declared entrypoints. Add its "
            f"import targets to TEMPLATES so a broken import is not silently "
            f"tolerated."
        )


# ---------------------------------------------------------------------------
# Positive cases (one parametrised test per entrypoint)
# ---------------------------------------------------------------------------


_RENDER_PARAMS, _RENDER_IDS = _entrypoint_params()


@pytest.mark.integration
@pytest.mark.parametrize(("case", "entrypoint"), _RENDER_PARAMS, ids=_RENDER_IDS)
def test_render_and_import(
    case: TemplateCase,
    entrypoint: EntrypointCase,
    tmp_path: Path,
) -> None:
    """Render ``case`` into ``tmp_path`` and import ``entrypoint.module``.

    xfail-marked entrypoints (see ``EntrypointCase.xfail_reason``) are expected
    to fail until the referenced upstream fix lands. pytest will flag XPASS so
    the xfail can be removed promptly after the fix merges.
    """
    template_dir = TEMPLATES_ROOT / case.name
    if not template_dir.is_dir():
        pytest.skip(f"Template source directory not available: {template_dir}")

    missing = _runtime_deps_available(case.runtime_deps)
    if missing is not None:
        pytest.skip(
            f"Runtime dependency '{missing}' not installed in test env. "
            f"Install the template's runtime deps "
            f"({', '.join(case.runtime_deps)}) to exercise this smoke test."
        )

    rendered = _render_template(template_dir, case, tmp_path)
    assert rendered, (
        f"No files rendered for template '{case.name}'. "
        f"Check layout mappings in TEMPLATES."
    )

    result = _run_import_check(tmp_path, [entrypoint.module])

    assert result.returncode == 0, (
        f"Import of {entrypoint.module!r} failed for rendered template "
        f"'{case.name}'.\n\n"
        f"--- stdout ---\n{result.stdout}\n"
        f"--- stderr ---\n{result.stderr}\n"
        f"--- rendered tree ({tmp_path}) ---\n"
        + "\n".join(f"  {p}" for p in sorted(rendered))
    )


# ---------------------------------------------------------------------------
# Negative-test proof: the positive assertion is actually exercised
# ---------------------------------------------------------------------------


class TestNegative:
    """Prove the positive test would fail on a broken import.

    Rationale: an assertion is only as strong as its test. If we never see the
    smoke test fail, we cannot distinguish "test passes" from "test silently
    does nothing". This class builds a tiny, self-contained scratch tree and
    shows that a deliberately broken import is reported by ``_run_import_check``.
    """

    @pytest.mark.integration
    def test_broken_import_fails_loud(self, tmp_path: Path) -> None:
        """A deliberately broken module import must produce a non-zero exit."""
        pkg = tmp_path / "scratch"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "broken.py").write_text(
            textwrap.dedent(
                """
                # Simulates the TASK-LCL-001 regression: an SDK import was
                # incorrectly rewritten to a project-relative path.
                from scratch.definitely_does_not_exist import something  # noqa
                """
            ).lstrip()
        )

        result = _run_import_check(tmp_path, ["scratch.broken"])

        assert result.returncode != 0, (
            "Broken import unexpectedly succeeded — the smoke test would "
            "not catch real regressions. stdout=%r stderr=%r"
            % (result.stdout, result.stderr)
        )
        assert "ModuleNotFoundError" in result.stderr or "ImportError" in result.stderr, (
            f"Expected ModuleNotFoundError/ImportError in stderr, got: "
            f"{result.stderr!r}"
        )

    @pytest.mark.integration
    def test_clean_import_succeeds(self, tmp_path: Path) -> None:
        """Sanity companion: a clean scratch module imports with exit 0.

        Confirms the subprocess harness itself isn't the reason negative
        cases fail — i.e. failures in the real test reflect the rendered
        scaffold, not the helper.
        """
        pkg = tmp_path / "scratch"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "ok.py").write_text("VALUE = 42\n")

        result = _run_import_check(tmp_path, ["scratch.ok"])

        assert result.returncode == 0, (
            f"Clean import failed — subprocess harness is broken.\n"
            f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
        )


# ---------------------------------------------------------------------------
# Internal helper tests (fast; always run)
# ---------------------------------------------------------------------------


class TestResolveTarget:
    """Unit coverage for _resolve_target layout matching."""

    def test_exact_file_mapping(self) -> None:
        layout = [("templates/other/other/agent.py.template", "scratch/agent.py")]
        result = _resolve_target(
            Path("templates/other/other/agent.py.template"), layout
        )
        assert result == Path("scratch/agent.py")

    def test_directory_mapping_strips_template_suffix(self) -> None:
        layout = [("templates/other/agents/", "scratch/")]
        result = _resolve_target(
            Path("templates/other/agents/coach.py.template"), layout
        )
        assert result == Path("scratch/coach.py")

    def test_preserved_subpackage(self) -> None:
        layout = [("templates/other/scaffold/", "scratch/scaffold/")]
        result = _resolve_target(
            Path("templates/other/scaffold/orchestrator_pattern.py.template"),
            layout,
        )
        assert result == Path("scratch/scaffold/orchestrator_pattern.py")

    def test_longest_prefix_wins(self) -> None:
        # General catch-all plus a specific file mapping — specific wins.
        layout = [
            ("templates/other/other/", "scratch/"),
            ("templates/other/other/pyproject.toml.template", "pyproject.toml"),
        ]
        result = _resolve_target(
            Path("templates/other/other/pyproject.toml.template"), layout
        )
        assert result == Path("pyproject.toml")

    def test_skip_mapping(self) -> None:
        layout = [("templates/testing/", None)]
        result = _resolve_target(
            Path("templates/testing/tests/test_agents.py.template"), layout
        )
        assert result is None

    def test_unmatched_returns_none(self) -> None:
        layout = [("templates/other/", "scratch/")]
        result = _resolve_target(
            Path("docs/something.md.template"), layout
        )
        assert result is None


class TestRenderText:
    """Unit coverage for placeholder substitution."""

    def test_single_placeholder(self) -> None:
        assert _render_text("hello {{ProjectName}}", {"ProjectName": "x"}) == "hello x"

    def test_multiple_placeholders(self) -> None:
        out = _render_text(
            "from {{ProjectName}}.{{Module}} import X",
            {"ProjectName": "scratch", "Module": "coach"},
        )
        assert out == "from scratch.coach import X"

    def test_unknown_placeholder_preserved(self) -> None:
        # Unknown placeholders are left intact so template bugs surface loudly
        # at import time rather than being silently eaten.
        assert (
            _render_text("x = {{Unknown}}", {"ProjectName": "scratch"})
            == "x = {{Unknown}}"
        )

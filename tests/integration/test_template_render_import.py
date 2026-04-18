"""Smoke test: render each in-scope template and import its declared entrypoints.

Purpose (TASK-LCL-003, FEAT-LTL1):
    Catch broken imports in ``.template`` scaffold files at template-update time
    rather than post-release. TASK-LCL-001 landed a regression where the
    ``{{ProjectName}}`` placeholder sweep over-rewrote SDK imports
    (``from deepagents.backends`` → ``from {{ProjectName}}.backends``). After
    rendering, ``import <project>.backends`` fails with ``ModuleNotFoundError``,
    but no existing test renders the template and imports it, so the bug shipped.

Interface contract:
    - Consumes the raw ``.template`` files (base-template convention) AND
      ``.j2`` files (extension-template convention, e.g.
      ``langchain-deepagents-weighted-evaluation``) under
      ``installer/core/templates/<name>/``. Substitution is literal
      ``{{Key}} -> value`` in both cases — this test does NOT evaluate Jinja
      expressions, so any ``.j2`` file containing real Jinja (``{% for %}``,
      filters, ``| default(...)``) must be skipped via the layout's ``None``
      target. See ``_LCDWE_LAYOUT`` for a worked example.
    - It does NOT call ``guardkit init`` (that CLI deliberately skips
      ``.template`` scaffold files — see ``guardkit.cli.init.apply_template``).
      If the installer ever grows a first-class ``.template`` / ``.j2``
      renderer (``guardkit render`` or an importable ``render_template(...)``
      API), swap the local ``_render_template`` helper for it — see
      ``_RENDER_IMPL`` sentinel.
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


# Layout for langchain-deepagents-orchestrator.
# Unlike the base template, this one uses **bare** imports (``from prompts
# import ...``, ``from agents import ...``, ``from tools import ...``,
# ``from lib.X import ...``) — not ``{{ProjectName}}.X``. So the rendered tree
# must place these packages at the **scratch project root**, not under a
# ``scratch/`` subpackage. The subprocess harness runs ``python -c "... import
# <ep>"`` with cwd inserted into ``sys.path``, so root-level packages resolve.
#
# Package-init import bugs in this template were fixed in TASK-FIX-7B2D:
#   - ``prompts/__init__.py.template`` previously used
#     ``from {{ProjectName}}.orchestrator_prompts import ...`` (same-package
#     flatten); now uses ``from .orchestrator_prompts``.
#   - ``agents/__init__.py.template`` previously had a double-placeholder typo
#     ``from {{ProjectName}}.{{ProjectName}} import ...``; now uses
#     ``from .agents import ...``.
#   - ``tools/__init__.py.template`` previously used
#     ``from {{ProjectName}}.orchestrator_tools import ...``; now uses
#     ``from .orchestrator_tools``.
#   - ``tools/orchestrator_tools.py.template`` previously had
#     ``from {{ProjectName}}.tools import tool`` — the TASK-LCL-001 class bug
#     surfacing in the orchestrator sibling; now uses
#     ``from langchain_core.tools import tool`` (matching the base template
#     after TASK-LCL-001).
# All four are now regression-protected by the ``prompts``, ``agents``, and
# ``tools`` entrypoints on the ``langchain-deepagents-orchestrator``
# ``TemplateCase`` below.
_LCDO_LAYOUT = [
    # Top-level entrypoint module. Not used as a smoke-test entrypoint because
    # ``agent.py`` has heavy module-level wiring (argparse, dotenv, yaml config
    # loading, domain file reads) that is exercised by the template's own
    # runtime tests, not by this render+import smoke.
    ("templates/other/other/agent.py.template", "agent.py"),
    # Project configuration files (kept at scratch-project root so agent.py's
    # config loader would find them if it were run).
    ("templates/other/other/pyproject.toml.template", "pyproject.toml"),
    ("templates/other/other/orchestrator-config.yaml.template", "orchestrator-config.yaml"),
    ("templates/other/other/langgraph.json.template", "langgraph.json"),
    ("templates/other/other/AGENTS.md.template", "AGENTS.md"),
    # Package directories at the scratch ROOT (not under ``scratch/``) — see
    # layout docstring above for why.
    ("templates/other/agents/", "agents/"),
    ("templates/other/prompts/", "prompts/"),
    ("templates/other/tools/", "tools/"),
    ("templates/other/lib/", "lib/"),
    # Domain assets (consumed by agent.py's _load_domain_prompt).
    ("templates/other/example-domain/", "domains/example-domain/"),
    # Skip testing scaffold — same rationale as the base template.
    ("templates/testing/", None),
]


# Layout for langchain-deepagents-weighted-evaluation.
# This extension template uses ``.j2`` suffix (not ``.template``) for its
# scaffold files. The substitution here is still literal ``{{Key}}`` → value;
# ``.j2`` is incidental to the file-suffix convention chosen by the extension.
#
# The template ``extends: langchain-deepagents`` at install time, meaning the
# full rendered project also includes the base template's ``lib/`` and
# ``scratch/`` packages. This smoke test renders extensions **standalone** —
# it does NOT compose the ``extends`` chain — so entrypoints that depend on
# inherited modules (e.g. ``scaffold/orchestrator.py.j2`` imports from
# ``{{ProjectName}}.config.adversarial_config`` which is not a ``.j2``/``.template``
# file) are out of scope. We pick clean leaf modules as entrypoints instead.
_LCDWE_LAYOUT = [
    # Scaffold modules under ``scratch/scaffold/`` — the ``.j2`` files use
    # ``{{ProjectName}}.scaffold.X`` imports, which after ``ProjectName=scratch``
    # substitution become ``scratch.scaffold.X``. Python 3 treats ``scratch/``
    # and ``scratch/scaffold/`` as implicit namespace packages (PEP 420), so no
    # ``__init__.py`` is required.
    ("scaffold/", "scratch/scaffold/"),
    # Env example at project root.
    ("templates/other/other/.env.example.template", ".env.example"),
    # Skip ``templates/goal.md.j2`` — contains real Jinja expressions
    # (``{% for %}``, ``| default(...)`` filters) beyond simple ``{{Key}}``
    # substitution. Rendering it with ``_render_text`` leaves Jinja syntax
    # unresolved in the output. Handling these would require a genuine Jinja2
    # evaluator in the test path, which is out of scope for a render+import
    # smoke test.
    ("templates/goal.md.j2", None),
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
        #     previously contained ``from {{ProjectName}}.tools import tool``
        #     which rendered to ``from scratch.tools import tool`` — the
        #     TASK-LCL-001 bug. That was fixed in commit dbc47bc5 (template
        #     now imports ``from langchain_core.tools import tool``), so the
        #     entrypoint is no longer xfail-marked.
        entrypoints=[
            EntrypointCase(module="scratch.coach"),
            EntrypointCase(module="scratch.player"),
        ],
        runtime_deps=[
            "langchain",
            "langchain_anthropic",
            "deepagents",
        ],
        placeholders=dict(_DEFAULT_PLACEHOLDERS),
        layout=_LCD_LAYOUT,
    ),
    TemplateCase(
        name="langchain-deepagents-orchestrator",
        # Entrypoint selection follows the base template's rationale — avoid
        # ``agent.py`` (heavy module-level config/domain wiring) and prefer
        # leaf library modules plus a package ``__init__`` that reproduces the
        # TASK-LCL-001-class failure surfaces documented in ``_LCDO_LAYOUT``.
        #
        #   - ``lib.session_logging``: stdlib-only vendored helper. Clean
        #     control case — if this fails, the render pipeline itself is
        #     broken for this template.
        #   - ``prompts``: importing the package executes ``prompts/__init__.py``,
        #     which re-exports the three role prompts via relative imports
        #     (``from .orchestrator_prompts``, ``.implementer_prompts``,
        #     ``.evaluator_prompts``) after TASK-FIX-7B2D. Covers bug 1 from
        #     that task.
        #   - ``agents``: importing the package executes ``agents/__init__.py``,
        #     which re-exports the factory functions via ``from .agents``
        #     after TASK-FIX-7B2D (bug 2 — the double-placeholder typo).
        #     Transitively imports ``prompts``, ``tools``, ``lib.factory_guards``
        #     plus the ``deepagents`` and ``langgraph`` SDKs (declared in
        #     ``runtime_deps``), exercising the full package-init chain.
        #   - ``tools``: importing the package executes ``tools/__init__.py``,
        #     which re-exports the four orchestrator tools via relative import
        #     (``from .orchestrator_tools``) after TASK-FIX-7B2D (bug 3).
        #     Transitively imports ``langchain_core.tools`` — bug 5, the
        #     TASK-LCL-001 class regression in the orchestrator sibling.
        entrypoints=[
            EntrypointCase(module="lib.session_logging"),
            EntrypointCase(module="prompts"),
            EntrypointCase(module="agents"),
            EntrypointCase(module="tools"),
        ],
        runtime_deps=[
            "langchain",
            "langchain_anthropic",
            "deepagents",
            "langgraph",
        ],
        placeholders=dict(_DEFAULT_PLACEHOLDERS),
        layout=_LCDO_LAYOUT,
    ),
    TemplateCase(
        name="langchain-deepagents-weighted-evaluation",
        # This extension template uses ``.j2`` (Jinja) file suffix instead of
        # ``.template``. Only its scaffold modules have simple-substitution
        # placeholders; the top-level ``templates/goal.md.j2`` uses real Jinja
        # and is skipped in the layout.
        #
        # Entrypoint selection: pick leaf scaffold modules whose module-level
        # imports are all stdlib, so they exercise the render+import loop
        # without pulling in dependencies that are only available when the
        # ``extends: langchain-deepagents`` chain is composed at install time
        # (this smoke test renders extensions **standalone**).
        #
        #   - ``scratch.scaffold.goal_schema``: pure-stdlib dataclasses and
        #     markdown parsing helpers. Clean case.
        #   - ``scratch.scaffold.pipeline``: pure-stdlib dataclasses at module
        #     level; project-relative imports are lazy (inside method bodies).
        #     Clean case.
        #
        # Out of scope: ``scaffold.orchestrator`` has module-level imports from
        # ``{{ProjectName}}.config``/``prompts`` and ``lib.*`` that depend on
        # the base template's rendered files. Testing that chain belongs to a
        # future extends-composition smoke test, not this standalone one.
        entrypoints=[
            EntrypointCase(module="scratch.scaffold.goal_schema"),
            EntrypointCase(module="scratch.scaffold.pipeline"),
        ],
        # Runtime deps are declared for parity with the base template; the
        # chosen scaffold entrypoints only use stdlib at module load, so these
        # would only be exercised transitively. Declared so the skip-on-missing
        # semantics match sibling templates.
        runtime_deps=[
            "langchain",
            "langchain_anthropic",
            "deepagents",
            "langgraph",
        ],
        placeholders=dict(_DEFAULT_PLACEHOLDERS),
        layout=_LCDWE_LAYOUT,
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
    if best_prefix.endswith(".template") or best_prefix.endswith(".j2"):
        dest_str = best_target
    else:
        # Directory mapping — replace the prefix and strip the template suffix.
        # ``.template`` is the base-template convention (simple ``{{Key}}`` sub).
        # ``.j2`` is used by extension templates that normally require Jinja2
        # evaluation; this test only does literal ``{{Key}}`` substitution, so
        # files with real Jinja expressions must be skipped via layout ``None``.
        suffix = src_str[len(best_prefix):]
        dest_str = best_target + suffix
        if dest_str.endswith(".template"):
            dest_str = dest_str[: -len(".template")]
        elif dest_str.endswith(".j2"):
            dest_str = dest_str[: -len(".j2")]

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

    # Pick up both ``.template`` (base-template convention) and ``.j2``
    # (extension-template convention, e.g. langchain-deepagents-weighted-evaluation).
    # NOTE: substitution is literal ``{{Key}} -> value``, not Jinja evaluation.
    # Files that contain real Jinja expressions (``{% for %}``, filters, ``|
    # default(...)``) must be skipped via the layout's ``None`` target or they
    # will render with unresolved Jinja syntax.
    template_files = sorted(
        list(template_root.rglob("*.template")) + list(template_root.rglob("*.j2"))
    )

    rendered: List[Path] = []
    for template_path in template_files:
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
    # Purge the guardkit repo root from sys.path before inserting cwd. The
    # repo is (typically) installed as an editable install via a ``.pth`` file
    # in site-packages, which puts top-level directories at the repo root
    # (``lib/``, ``guardkit/``, ...) on sys.path. That shadows identically
    # named packages rendered into the scratch project — notably the
    # langchain-deepagents-orchestrator template's ``lib/`` which would
    # otherwise resolve to guardkit-py's own ``lib/__init__.py`` rather than
    # the scratch tree. Exact-match filter is sufficient because Python's
    # editable installs use exact-path ``.pth`` entries.
    repo_root_literal = repr(str(REPO_ROOT))
    script = (
        "import sys; "
        f"sys.path[:] = [p for p in sys.path if p != {repo_root_literal}]; "
        "sys.path.insert(0, '.'); "
        f"{import_statements}"
    )

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

    def test_exact_j2_file_mapping(self) -> None:
        # ``.j2`` suffix works the same as ``.template`` for exact file
        # mappings: the target is used verbatim (no suffix stripping needed
        # because the target already declares the final filename).
        layout = [("scaffold/goal_schema.py.j2", "scratch/scaffold/goal_schema.py")]
        result = _resolve_target(
            Path("scaffold/goal_schema.py.j2"), layout
        )
        assert result == Path("scratch/scaffold/goal_schema.py")

    def test_directory_mapping_strips_j2_suffix(self) -> None:
        # Directory mappings auto-strip the template suffix from rendered
        # filenames; ``.j2`` behaves identically to ``.template``.
        layout = [("scaffold/", "scratch/scaffold/")]
        result = _resolve_target(
            Path("scaffold/pipeline.py.j2"), layout
        )
        assert result == Path("scratch/scaffold/pipeline.py")


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

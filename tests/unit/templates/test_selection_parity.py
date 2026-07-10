"""Golden selection-parity test (PB-7 §3) — the "must not silently move the
WS3 baseline" obligation made mechanical.

Records ``select_patterns`` output for a fixture matrix of
(template x tech_stack x hints) inputs with ``GUARDKIT_PATTERN_SELECTION_V2``
UNSET (the default), against a synthetic template tree shaped like
fastapi-python. The golden ``selected_files`` name-lists were captured from
this exact fixture before the v2 code path existed
(``_select_patterns_v1`` is the pre-PB-7 function body, unmodified except for
the rename + the cap-enforcement extraction into ``_apply_selection_caps`` —
both no-ops on output).

If this test ever needs its goldens re-baselined, that re-baseline happens
ONLY in the Phase-2 default-flip commit (PB-7 scope §4) — never casually.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from guardkit.knowledge.template_pattern_loader import (
    TemplatePatternContext,
    pattern_selection_v2_enabled,
    select_patterns,
)


@pytest.fixture
def fastapi_shaped_tree(tmp_path: Path) -> Path:
    """A template tree shaped like fastapi-python's 13-file layout."""
    tpl_dir = tmp_path / "tpl" / "fastapi-python"
    tpl_sub = tpl_dir / "templates"
    file_defs = {
        "api/router.py.template": "# API router template content here...",
        "config/alembic.ini.template": "# Alembic config template content..",
        "config/pyproject.toml.template": "# pyproject.toml template content.",
        "core/config.py.template": "# Core config template content here",
        "core/security.py.template": "# Security template content here...",
        "crud/crud_base.py.template": "# CRUD base template content here..",
        "crud/crud.py.template": "# CRUD template content stored here",
        "db/session.py.template": "# DB session template content here.",
        "models/models.py.template": "# Models template content goes here",
        "schemas/schemas.py.template": "# Schemas template content goes here",
        "testing/conftest.py.template": "# Test conftest template content...",
        "testing/test_router.py.template": "# Test router template content....",
    }
    for rel, content in file_defs.items():
        fpath = tpl_sub / rel
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.write_text(content)
    return tpl_dir


def _make_ctx(tree: Path, template_name: str = "fastapi-python") -> TemplatePatternContext:
    tpl_sub = tree / "templates"
    available = sorted(tpl_sub.rglob("*.template"))
    return TemplatePatternContext(
        template_name=template_name,
        template_dir=tree,
        available_files=available,
        selected_files=[],
        prompt_block="",
        warnings=[],
    )


# Fixture matrix: (tech_stack, file_path_hints) -> golden selected file names,
# captured from the pre-PB-7 select_patterns() body against fastapi_shaped_tree.
GOLDEN_MATRIX = [
    ("Python", ["app/api/users.py"], ["router.py.template"]),
    (
        "Python",
        ["app/crud/items.py"],
        ["crud.py.template", "crud_base.py.template"],
    ),
    (
        "Python",
        [],
        [
            "router.py.template",
            "alembic.ini.template",
            "pyproject.toml.template",
            "config.py.template",
            "security.py.template",
        ],
    ),
    ("", [], ["router.py.template", "alembic.ini.template", "pyproject.toml.template"]),
    ("Haskell", [], ["router.py.template", "alembic.ini.template", "pyproject.toml.template"]),
    (
        "FastAPI",
        [],
        [
            "router.py.template",
            "alembic.ini.template",
            "pyproject.toml.template",
            "config.py.template",
            "security.py.template",
        ],
    ),
]


class TestFlagOffIsUntouched:
    def test_flag_is_unset_by_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GUARDKIT_PATTERN_SELECTION_V2", raising=False)
        assert pattern_selection_v2_enabled() is False

    @pytest.mark.parametrize("tech_stack,hints,golden_names", GOLDEN_MATRIX)
    def test_selection_matches_golden(
        self,
        fastapi_shaped_tree: Path,
        monkeypatch: pytest.MonkeyPatch,
        tech_stack: str,
        hints: list,
        golden_names: list,
    ) -> None:
        monkeypatch.delenv("GUARDKIT_PATTERN_SELECTION_V2", raising=False)
        ctx = _make_ctx(fastapi_shaped_tree)

        result = select_patterns(ctx, tech_stack=tech_stack, file_path_hints=hints)

        selected_names = [f.name for f in result.selected_files]
        assert selected_names == golden_names

    def test_flag_explicitly_off_matches_default(
        self, fastapi_shaped_tree: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        ctx = _make_ctx(fastapi_shaped_tree)
        monkeypatch.delenv("GUARDKIT_PATTERN_SELECTION_V2", raising=False)
        default_result = select_patterns(
            ctx, tech_stack="Python", file_path_hints=["app/api/users.py"]
        )

        monkeypatch.setenv("GUARDKIT_PATTERN_SELECTION_V2", "0")
        explicit_off_result = select_patterns(
            ctx, tech_stack="Python", file_path_hints=["app/api/users.py"]
        )

        assert [f.name for f in default_result.selected_files] == [
            f.name for f in explicit_off_result.selected_files
        ]

    def test_a_manifest_present_does_not_affect_flag_off_selection(
        self, fastapi_shaped_tree: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A patterns-manifest.json sitting next to the templates must be
        completely inert while the flag is off — v1 never reads it."""
        from guardkit.templates.patterns_manifest import (
            PatternEntry,
            PatternsManifest,
            write_patterns_manifest,
        )

        write_patterns_manifest(
            fastapi_shaped_tree,
            PatternsManifest(
                schema_version=1,
                patterns=[PatternEntry(file="crud/crud.py.template", layer="api", priority=1)],
            ),
        )
        monkeypatch.delenv("GUARDKIT_PATTERN_SELECTION_V2", raising=False)
        ctx = _make_ctx(fastapi_shaped_tree)

        result = select_patterns(ctx, tech_stack="Python", file_path_hints=["app/api/users.py"])

        # Golden for this hint is router.py.template — a manifest claiming
        # crud.py.template belongs to "api" must NOT leak into the v1 result.
        assert [f.name for f in result.selected_files] == ["router.py.template"]

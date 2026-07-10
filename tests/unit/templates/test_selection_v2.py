"""Tests for manifest-driven selection v2 (``GUARDKIT_PATTERN_SELECTION_V2=1``).

Covers:
  * flag-on with a valid manifest — hint/keyword matching, priority ordering,
    pairs_with co-selection, caps still enforced (5/3000 untouched);
  * flag-on with NO manifest / a malformed manifest / an empty manifest
    degrades to exactly the v1 result (K4 never-raise extended);
  * flag-on wiring does not relax max_files/max_tokens.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from guardkit.knowledge.template_pattern_loader import (
    TemplatePatternContext,
    _select_patterns_v1,
    select_patterns,
)
from guardkit.templates.patterns_manifest import (
    PatternEntry,
    PatternsManifest,
    write_patterns_manifest,
)


@pytest.fixture(autouse=True)
def _flag_on(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GUARDKIT_PATTERN_SELECTION_V2", "1")


@pytest.fixture
def tpl_dir(tmp_path: Path) -> Path:
    d = tmp_path / "tpl" / "some-template"
    for rel, content in {
        "api/router.py.template": "# router",
        "api/router_v2.py.template": "# router v2",
        "schemas/schemas.py.template": "# schemas",
        "crud/crud.py.template": "# crud",
    }.items():
        fpath = d / "templates" / rel
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.write_text(content)
    return d


def _ctx(tpl_dir: Path) -> TemplatePatternContext:
    available = sorted((tpl_dir / "templates").rglob("*.template"))
    return TemplatePatternContext(
        template_name="some-template",
        template_dir=tpl_dir,
        available_files=available,
        selected_files=[],
        prompt_block="",
        warnings=[],
    )


class TestManifestDrivenMatching:
    def test_keyword_match_selects_declared_layer(self, tpl_dir: Path) -> None:
        write_patterns_manifest(
            tpl_dir,
            PatternsManifest(
                schema_version=1,
                patterns=[
                    PatternEntry(
                        file="api/router.py.template",
                        layer="api",
                        keywords=["endpoint"],
                        priority=1,
                    ),
                    PatternEntry(file="crud/crud.py.template", layer="crud", priority=1),
                ],
            ),
        )
        result = select_patterns(
            _ctx(tpl_dir), tech_stack="python", file_path_hints=["app/endpoint/x.py"]
        )
        names = [f.name for f in result.selected_files]
        assert "router.py.template" in names
        assert "crud.py.template" not in names

    def test_layer_match_via_hint_segment(self, tpl_dir: Path) -> None:
        write_patterns_manifest(
            tpl_dir,
            PatternsManifest(
                schema_version=1,
                patterns=[
                    PatternEntry(file="crud/crud.py.template", layer="crud", priority=1),
                ],
            ),
        )
        result = select_patterns(
            _ctx(tpl_dir), tech_stack="python", file_path_hints=["app/crud/items.py"]
        )
        assert [f.name for f in result.selected_files] == ["crud.py.template"]

    def test_priority_orders_within_matched_set(self, tpl_dir: Path) -> None:
        write_patterns_manifest(
            tpl_dir,
            PatternsManifest(
                schema_version=1,
                patterns=[
                    PatternEntry(
                        file="api/router_v2.py.template", layer="api", priority=2
                    ),
                    PatternEntry(file="api/router.py.template", layer="api", priority=1),
                ],
            ),
        )
        result = select_patterns(
            _ctx(tpl_dir), tech_stack="python", file_path_hints=["app/api/x.py"]
        )
        names = [f.name for f in result.selected_files]
        assert names[0] == "router.py.template"
        assert names[1] == "router_v2.py.template"

    def test_pairs_with_rides_along(self, tpl_dir: Path) -> None:
        write_patterns_manifest(
            tpl_dir,
            PatternsManifest(
                schema_version=1,
                patterns=[
                    PatternEntry(
                        file="api/router.py.template",
                        layer="api",
                        priority=1,
                        pairs_with=["schemas/schemas.py.template"],
                    ),
                    PatternEntry(file="schemas/schemas.py.template", layer="schemas", priority=5),
                ],
            ),
        )
        result = select_patterns(
            _ctx(tpl_dir), tech_stack="python", file_path_hints=["app/api/x.py"]
        )
        names = [f.name for f in result.selected_files]
        assert "router.py.template" in names
        assert "schemas.py.template" in names

    def test_pairs_with_dangling_reference_is_ignored(self, tpl_dir: Path) -> None:
        """A pairs_with target absent from the manifest must not crash selection."""
        write_patterns_manifest(
            tpl_dir,
            PatternsManifest(
                schema_version=1,
                patterns=[
                    PatternEntry(
                        file="api/router.py.template",
                        layer="api",
                        priority=1,
                        pairs_with=["nonexistent/ghost.py.template"],
                    ),
                ],
            ),
        )
        result = select_patterns(
            _ctx(tpl_dir), tech_stack="python", file_path_hints=["app/api/x.py"]
        )
        assert [f.name for f in result.selected_files] == ["router.py.template"]

    def test_caps_still_enforced_under_v2(self, tpl_dir: Path) -> None:
        write_patterns_manifest(
            tpl_dir,
            PatternsManifest(
                schema_version=1,
                patterns=[
                    PatternEntry(file="api/router.py.template", layer="api", priority=1),
                    PatternEntry(file="api/router_v2.py.template", layer="api", priority=2),
                    PatternEntry(file="crud/crud.py.template", layer="api", priority=3),
                    PatternEntry(file="schemas/schemas.py.template", layer="api", priority=4),
                ],
            ),
        )
        result = select_patterns(
            _ctx(tpl_dir),
            tech_stack="python",
            file_path_hints=["app/api/x.py"],
            max_files=2,
        )
        assert len(result.selected_files) <= 2

    def test_no_match_falls_to_alphabetical(self, tpl_dir: Path) -> None:
        write_patterns_manifest(
            tpl_dir,
            PatternsManifest(
                schema_version=1,
                patterns=[
                    PatternEntry(file="api/router.py.template", layer="api", priority=1),
                ],
            ),
        )
        result = select_patterns(_ctx(tpl_dir), tech_stack="", file_path_hints=[])
        assert len(result.selected_files) == 3


class TestDegradesToV1:
    def test_no_manifest_falls_back_to_v1(self, tpl_dir: Path) -> None:
        v1_result = _select_patterns_v1(
            _ctx(tpl_dir), tech_stack="python", file_path_hints=["app/api/x.py"], max_files=5, max_tokens=3000
        )
        v2_result = select_patterns(
            _ctx(tpl_dir), tech_stack="python", file_path_hints=["app/api/x.py"]
        )
        assert [f.name for f in v1_result.selected_files] == [
            f.name for f in v2_result.selected_files
        ]

    def test_malformed_manifest_falls_back_to_v1(self, tpl_dir: Path) -> None:
        (tpl_dir / "templates" / "patterns-manifest.json").write_text("{ not valid json")

        v1_result = _select_patterns_v1(
            _ctx(tpl_dir), tech_stack="python", file_path_hints=["app/api/x.py"], max_files=5, max_tokens=3000
        )
        v2_result = select_patterns(
            _ctx(tpl_dir), tech_stack="python", file_path_hints=["app/api/x.py"]
        )
        assert [f.name for f in v1_result.selected_files] == [
            f.name for f in v2_result.selected_files
        ]

    def test_empty_patterns_manifest_falls_back_to_v1(self, tpl_dir: Path) -> None:
        write_patterns_manifest(
            tpl_dir, PatternsManifest(schema_version=1, patterns=[])
        )
        v1_result = _select_patterns_v1(
            _ctx(tpl_dir), tech_stack="python", file_path_hints=["app/api/x.py"], max_files=5, max_tokens=3000
        )
        v2_result = select_patterns(
            _ctx(tpl_dir), tech_stack="python", file_path_hints=["app/api/x.py"]
        )
        assert [f.name for f in v1_result.selected_files] == [
            f.name for f in v2_result.selected_files
        ]

    def test_template_dir_none_falls_back_to_v1(self) -> None:
        ctx = TemplatePatternContext(
            template_name="x",
            template_dir=None,
            available_files=[],
            selected_files=[],
            prompt_block="",
            warnings=[],
        )
        result = select_patterns(ctx, tech_stack="python", file_path_hints=[])
        assert result.selected_files == []

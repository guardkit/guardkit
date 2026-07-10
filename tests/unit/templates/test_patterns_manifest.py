"""Unit tests for the patterns-manifest.json schema + backfill (PB-7 §3).

Covers:
  * round-trip write/load;
  * never-raise degradation on every malformed shape (missing file, invalid
    JSON, wrong schema_version, non-list patterns, malformed entry);
  * the backfill generator's layer-from-leaf-parent-dir + alpha-order
    priority derivation, including the nested-directory case.
"""

from __future__ import annotations

import json
from pathlib import Path

from guardkit.templates.patterns_manifest import (
    CURRENT_SCHEMA_VERSION,
    PatternEntry,
    PatternsManifest,
    generate_backfill_manifest,
    load_patterns_manifest,
    manifest_to_dict,
    write_patterns_manifest,
)


def _write_template_file(template_dir: Path, rel: str, content: str = "x = 1\n") -> None:
    fpath = template_dir / "templates" / rel
    fpath.parent.mkdir(parents=True, exist_ok=True)
    fpath.write_text(content)


class TestRoundTrip:
    def test_write_then_load_round_trips(self, tmp_path: Path) -> None:
        template_dir = tmp_path / "tpl"
        manifest = PatternsManifest(
            schema_version=CURRENT_SCHEMA_VERSION,
            patterns=[
                PatternEntry(
                    file="api/router.py.template",
                    layer="api",
                    keywords=["endpoint", "route"],
                    priority=1,
                    pairs_with=["schemas/schemas.py.template"],
                )
            ],
        )
        path = write_patterns_manifest(template_dir, manifest)
        assert path.is_file()

        loaded = load_patterns_manifest(template_dir)
        assert loaded == manifest

    def test_manifest_to_dict_shape_matches_spec(self, tmp_path: Path) -> None:
        manifest = PatternsManifest(
            schema_version=1,
            patterns=[PatternEntry(file="a.template", layer="api")],
        )
        data = manifest_to_dict(manifest)
        assert data == {
            "schema_version": 1,
            "patterns": [
                {
                    "file": "a.template",
                    "layer": "api",
                    "keywords": [],
                    "priority": 1,
                    "pairs_with": [],
                }
            ],
        }


class TestNeverRaiseDegradation:
    def test_missing_file_returns_none(self, tmp_path: Path) -> None:
        assert load_patterns_manifest(tmp_path / "nonexistent-tpl") is None

    def test_invalid_json_returns_none(self, tmp_path: Path) -> None:
        template_dir = tmp_path / "tpl"
        (template_dir / "templates").mkdir(parents=True)
        (template_dir / "templates" / "patterns-manifest.json").write_text("{ not json")
        assert load_patterns_manifest(template_dir) is None

    def test_non_dict_json_returns_none(self, tmp_path: Path) -> None:
        template_dir = tmp_path / "tpl"
        (template_dir / "templates").mkdir(parents=True)
        (template_dir / "templates" / "patterns-manifest.json").write_text("[1, 2, 3]")
        assert load_patterns_manifest(template_dir) is None

    def test_wrong_schema_version_returns_none(self, tmp_path: Path) -> None:
        template_dir = tmp_path / "tpl"
        (template_dir / "templates").mkdir(parents=True)
        (template_dir / "templates" / "patterns-manifest.json").write_text(
            json.dumps({"schema_version": 999, "patterns": []})
        )
        assert load_patterns_manifest(template_dir) is None

    def test_missing_schema_version_returns_none(self, tmp_path: Path) -> None:
        template_dir = tmp_path / "tpl"
        (template_dir / "templates").mkdir(parents=True)
        (template_dir / "templates" / "patterns-manifest.json").write_text(
            json.dumps({"patterns": []})
        )
        assert load_patterns_manifest(template_dir) is None

    def test_non_list_patterns_returns_none(self, tmp_path: Path) -> None:
        template_dir = tmp_path / "tpl"
        (template_dir / "templates").mkdir(parents=True)
        (template_dir / "templates" / "patterns-manifest.json").write_text(
            json.dumps({"schema_version": 1, "patterns": "not-a-list"})
        )
        assert load_patterns_manifest(template_dir) is None

    def test_malformed_entry_invalidates_whole_manifest(self, tmp_path: Path) -> None:
        """One bad entry -> None, not a partial/silent list."""
        template_dir = tmp_path / "tpl"
        (template_dir / "templates").mkdir(parents=True)
        (template_dir / "templates" / "patterns-manifest.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "patterns": [
                        {"file": "a.template", "layer": "api"},
                        {"file": "b.template"},  # missing required 'layer'
                    ],
                }
            )
        )
        assert load_patterns_manifest(template_dir) is None

    def test_entry_missing_file_field_returns_none(self, tmp_path: Path) -> None:
        template_dir = tmp_path / "tpl"
        (template_dir / "templates").mkdir(parents=True)
        (template_dir / "templates" / "patterns-manifest.json").write_text(
            json.dumps({"schema_version": 1, "patterns": [{"layer": "api"}]})
        )
        assert load_patterns_manifest(template_dir) is None

    def test_entry_bad_keywords_type_returns_none(self, tmp_path: Path) -> None:
        template_dir = tmp_path / "tpl"
        (template_dir / "templates").mkdir(parents=True)
        (template_dir / "templates" / "patterns-manifest.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "patterns": [
                        {"file": "a.template", "layer": "api", "keywords": "not-a-list"}
                    ],
                }
            )
        )
        assert load_patterns_manifest(template_dir) is None

    def test_entry_bad_priority_type_returns_none(self, tmp_path: Path) -> None:
        template_dir = tmp_path / "tpl"
        (template_dir / "templates").mkdir(parents=True)
        (template_dir / "templates" / "patterns-manifest.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "patterns": [
                        {"file": "a.template", "layer": "api", "priority": "high"}
                    ],
                }
            )
        )
        assert load_patterns_manifest(template_dir) is None

    def test_defaults_applied_when_optional_fields_absent(self, tmp_path: Path) -> None:
        template_dir = tmp_path / "tpl"
        (template_dir / "templates").mkdir(parents=True)
        (template_dir / "templates" / "patterns-manifest.json").write_text(
            json.dumps({"schema_version": 1, "patterns": [{"file": "a.template", "layer": "api"}]})
        )
        loaded = load_patterns_manifest(template_dir)
        assert loaded is not None
        entry = loaded.patterns[0]
        assert entry.keywords == []
        assert entry.priority == 1
        assert entry.pairs_with == []


class TestBackfillGenerator:
    def test_empty_template_dir_yields_empty_manifest(self, tmp_path: Path) -> None:
        template_dir = tmp_path / "tpl"
        template_dir.mkdir()
        manifest = generate_backfill_manifest(template_dir)
        assert manifest.patterns == []
        assert manifest.schema_version == CURRENT_SCHEMA_VERSION

    def test_layer_is_leaf_parent_directory_name(self, tmp_path: Path) -> None:
        template_dir = tmp_path / "tpl"
        _write_template_file(template_dir, "api/router.py.template")
        _write_template_file(template_dir, "crud/crud.py.template")

        manifest = generate_backfill_manifest(template_dir)
        layers = {p.file: p.layer for p in manifest.patterns}
        assert layers == {
            "api/router.py.template": "api",
            "crud/crud.py.template": "crud",
        }

    def test_nested_directory_uses_leaf_not_top_level(self, tmp_path: Path) -> None:
        """Matches the loader's real join — deep nesting, e.g. langchain-deepagents'
        templates/other/agents/coach.py.template -> layer 'agents', not 'other'."""
        template_dir = tmp_path / "tpl"
        _write_template_file(template_dir, "other/agents/coach.py.template")

        manifest = generate_backfill_manifest(template_dir)
        assert manifest.patterns[0].layer == "agents"

    def test_priority_is_alphabetical_order_within_layer(self, tmp_path: Path) -> None:
        template_dir = tmp_path / "tpl"
        _write_template_file(template_dir, "crud/zzz.py.template")
        _write_template_file(template_dir, "crud/aaa.py.template")

        manifest = generate_backfill_manifest(template_dir)
        by_file = {p.file: p.priority for p in manifest.patterns}
        assert by_file["crud/aaa.py.template"] == 1
        assert by_file["crud/zzz.py.template"] == 2

    def test_keywords_and_pairs_with_start_empty(self, tmp_path: Path) -> None:
        template_dir = tmp_path / "tpl"
        _write_template_file(template_dir, "api/router.py.template")

        manifest = generate_backfill_manifest(template_dir)
        assert manifest.patterns[0].keywords == []
        assert manifest.patterns[0].pairs_with == []

    def test_backfill_round_trips_through_write_and_load(self, tmp_path: Path) -> None:
        template_dir = tmp_path / "tpl"
        _write_template_file(template_dir, "api/router.py.template")
        _write_template_file(template_dir, "crud/crud.py.template")

        manifest = generate_backfill_manifest(template_dir)
        write_patterns_manifest(template_dir, manifest)
        loaded = load_patterns_manifest(template_dir)
        assert loaded == manifest


class TestShippedManifestsAreValid:
    """The 12 backfilled manifests committed alongside this build must load."""

    def test_every_shipped_template_manifest_loads_or_is_absent(self) -> None:
        from guardkit.templates.parse_gate import list_template_names
        from guardkit.templates.resolver import _get_templates_base_dir

        base = _get_templates_base_dir()
        broken = []
        for name in list_template_names(base):
            template_dir = base / name
            manifest_path = template_dir / "templates" / "patterns-manifest.json"
            if not manifest_path.is_file():
                continue
            if load_patterns_manifest(template_dir) is None:
                broken.append(name)
        assert not broken, f"manifests present but failed to load: {broken}"

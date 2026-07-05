"""Tests for stacks_for_changed_manifests (per-turn refresh stack scoping).

Regression context: study-tutor FEAT-APP-001 wave 3 (2026-07-05). The repo
hosts a Python backend AND a Flutter app (``app/pubspec.yaml``). The build
host has no ``flutter`` binary, so every turn that edited ``pyproject.toml``
had its venv refresh blocked by the *flutter* manifest's install failure —
three turns of identical infra feedback, task blocked, feature run failed.
The fix scopes ``relevant_stacks`` for the per-turn refresh to the stacks
whose manifests the turn actually changed; other stacks degrade to the
non-blocking warning path ``EnvironmentBootstrapper.bootstrap`` already
implements.
"""

from guardkit.orchestrator.environment_bootstrap import (
    stacks_for_changed_manifests,
)


class TestStacksForChangedManifests:
    def test_python_manifests_map_to_python_only(self):
        assert stacks_for_changed_manifests(
            ["pyproject.toml", "uv.lock", "src/study_tutor/http/app.py"]
        ) == ["python"]

    def test_requirements_variants_map_to_python(self):
        assert stacks_for_changed_manifests(
            ["requirements-dev.txt"]
        ) == ["python"]

    def test_flutter_manifest_maps_to_flutter(self):
        assert stacks_for_changed_manifests(
            ["app/pubspec.yaml", "app/lib/main.dart"]
        ) == ["flutter"]

    def test_pyproject_edit_does_not_include_untouched_flutter(self):
        # The FEAT-APP-001 wave-3 failure shape: only python manifests changed,
        # so flutter must NOT be in the relevant set (its install failure then
        # cannot block the turn).
        stacks = stacks_for_changed_manifests(["pyproject.toml", "uv.lock"])
        assert "flutter" not in stacks
        assert stacks == ["python"]

    def test_mixed_stacks_deduplicated_order_preserving(self):
        assert stacks_for_changed_manifests(
            ["pyproject.toml", "app/pubspec.yaml", "uv.lock", "go.mod"]
        ) == ["python", "flutter", "go"]

    def test_repo_qualified_paths_are_stripped(self):
        # Cross-repo evidence loop prefixes paths as "<repo>:<path>".
        assert stacks_for_changed_manifests(
            ["study-tutor:pyproject.toml"]
        ) == ["python"]

    def test_no_manifests_yields_empty(self):
        assert stacks_for_changed_manifests(
            ["src/main.py", "README.md", ""]
        ) == []

    def test_node_go_rust_mappings(self):
        assert stacks_for_changed_manifests(["package.json"]) == ["node"]
        assert stacks_for_changed_manifests(["yarn.lock"]) == ["node"]
        assert stacks_for_changed_manifests(["Cargo.lock"]) == ["rust"]
        assert stacks_for_changed_manifests(["go.sum"]) == ["go"]

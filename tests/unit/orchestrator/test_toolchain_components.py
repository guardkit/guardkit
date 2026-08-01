"""THE PER-COMPONENT SEAM — schema, the snapshot law, and the task selector.

study-tutor is two products in one tree: a Python backend at the root and a
Flutter app under ``app/``. There is no single ``test:`` string that is correct
for that repo — declare the backend's and every ``app/`` task silently gets the
Python suite as its verdict on Dart work. So the ONE declaration gains
``components:``.

Four properties are pinned here:

1. **The schema** — a component is the SAME fields plus a REQUIRED,
   contained, repo-relative ``cwd``. ``extra="forbid"`` holds at BOTH levels,
   so a typo'd component field is exactly as loud as a typo'd root field.
2. **The snapshot law is UNCHANGED, and that is why this shape was chosen**
   (design §B.2(iii)): the pin is one whole-model dump read back by one
   whole-model validate, so nesting costs zero snapshot changes. Proved by
   round-trip AND by the attack: a Player rewriting a COMPONENT's test command
   mid-build changes nothing.
3. **The selector is explicit and loud** — a task naming an undeclared
   component is a task-load FAILURE, never a quiet fall-back to the root
   block.
4. **Absence is a no-op** — a flat declaration, and a repo with none at all,
   are byte-unchanged.

Network-free and broker-free by construction: nothing here runs a subprocess.
"""

from __future__ import annotations

import inspect
import json

import pytest
import yaml

from guardkit.orchestrator.toolchain_declaration import (
    ComponentToolchain,
    ToolchainDeclaration,
    load_toolchain_declaration,
    load_toolchain_snapshot,
    parse_toolchain_block,
    resolve_component_cwd,
    snapshot_task_toolchain,
    toolchain_snapshot_paths,
)

_TASK_ID = "TASK-PC-001"

# The study-tutor SHAPE: a Python root component + a Flutter `app` component.
STUDY_TUTOR_SHAPE = {
    "test": "uv run --no-sync python -m pytest -q",
    "components": {
        "app": {
            "cwd": "app",
            "test": "flutter test",
            "install": "flutter pub get",
            "test_timeout": 900,
        },
    },
}


def _write_config(root, block):
    cfg_dir = root / ".guardkit"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    payload = {"autobuild": {"coach": {"model": "coach-ft-v4"}}}
    if block is not None:
        payload["toolchain"] = block
    (cfg_dir / "config.yaml").write_text(yaml.safe_dump(payload), encoding="utf-8")
    return cfg_dir / "config.yaml"


@pytest.fixture
def repo(tmp_path):
    """A repo root with a worktree beneath it, laid out as autobuild does."""
    root = tmp_path / "study-tutor"
    worktree = root / ".guardkit" / "worktrees" / _TASK_ID
    worktree.mkdir(parents=True)
    return root, worktree


# =========================================================================
# 1. The schema — good components
# =========================================================================


class TestComponentSchemaGood:
    def test_the_study_tutor_shape_parses(self):
        block = parse_toolchain_block(STUDY_TUTOR_SHAPE)
        assert block.test == "uv run --no-sync python -m pytest -q"
        app = block.component("app")
        assert isinstance(app, ComponentToolchain)
        assert app.cwd == "app"
        assert app.test == "flutter test"
        assert app.test_timeout == 900

    def test_a_component_carries_the_same_fields_as_the_root(self):
        """"the SAME fields" is a claim; this is the check."""
        root_fields = set(ToolchainDeclaration.model_fields) - {"components"}
        component_fields = set(ComponentToolchain.model_fields) - {"cwd"}
        assert root_fields == component_fields

    def test_component_timeouts_default_to_the_historic_values(self):
        block = parse_toolchain_block(
            {"components": {"app": {"cwd": "app", "test": "flutter test"}}}
        )
        app = block.component("app")
        assert app.test_timeout == 300
        assert app.install_timeout == 300

    def test_a_component_may_overlay_the_absence_classifier(self):
        block = parse_toolchain_block(
            {
                "components": {
                    "app": {
                        "cwd": "app",
                        "test": "flutter test",
                        "absent_substrings": ["No tests were found"],
                        "requires_ran_marker": False,
                    }
                }
            }
        )
        assert block.component("app").has_classifier_overlay is True

    def test_cwd_is_normalised_so_snapshot_and_receipt_agree(self):
        block = parse_toolchain_block(
            {"components": {"app": {"cwd": "./app/", "test": "flutter test"}}}
        )
        assert block.component("app").cwd == "app"

    def test_nested_component_directories_are_allowed(self):
        block = parse_toolchain_block(
            {"components": {"web": {"cwd": "clients/web", "test": "npm test"}}}
        )
        assert block.component("web").cwd == "clients/web"

    def test_an_unknown_component_name_resolves_to_none_not_the_root(self):
        """The resolver NEVER substitutes the root block — callers must treat
        ``None`` as an error (that is the whole false-verdict cure)."""
        block = parse_toolchain_block(STUDY_TUTOR_SHAPE)
        assert block.component("api") is None
        assert block.component_names == ["app"]


# =========================================================================
# 2. The schema — a bad component is LOUD
# =========================================================================


class TestComponentSchemaLoud:
    def test_a_component_without_cwd_is_rejected(self):
        with pytest.raises(ValueError, match="cwd"):
            parse_toolchain_block(
                {"components": {"app": {"test": "flutter test"}}}
            )

    def test_a_typod_component_key_is_loud(self):
        """``tests:`` inside a component must not be silently ignored — that
        is exactly the failure ``extra='forbid'`` exists to prevent."""
        with pytest.raises(ValueError) as exc:
            parse_toolchain_block(
                {"components": {"app": {"cwd": "app", "tests": "flutter test"}}}
            )
        assert "tests" in str(exc.value)

    def test_a_typod_components_key_at_the_root_is_loud(self):
        with pytest.raises(ValueError) as exc:
            parse_toolchain_block({"test": "pytest", "component": {"app": {}}})
        assert "component" in str(exc.value)

    def test_the_error_message_names_the_component_rules(self):
        with pytest.raises(ValueError) as exc:
            parse_toolchain_block({"componets": {}})
        assert "components" in str(exc.value)
        assert "cwd" in str(exc.value)

    @pytest.mark.parametrize(
        "bad_cwd", ["../outside", "app/../..", "/etc", "~/app", "   "]
    )
    def test_a_cwd_that_escapes_the_worktree_is_a_declaration_error(self, bad_cwd):
        """§G: 'a cwd that escapes the worktree must be a declaration error,
        not a path that resolves'."""
        with pytest.raises(ValueError):
            parse_toolchain_block(
                {"components": {"app": {"cwd": bad_cwd, "test": "flutter test"}}}
            )

    def test_a_whitespace_bearing_component_name_is_rejected(self):
        with pytest.raises(ValueError, match="whitespace"):
            parse_toolchain_block(
                {"components": {"my app": {"cwd": "app", "test": "true"}}}
            )

    def test_an_empty_component_command_is_rejected(self):
        with pytest.raises(ValueError):
            parse_toolchain_block(
                {"components": {"app": {"cwd": "app", "test": ""}}}
            )

    def test_a_component_timeout_above_the_bound_is_rejected(self):
        with pytest.raises(ValueError):
            parse_toolchain_block(
                {
                    "components": {
                        "app": {"cwd": "app", "test": "true", "test_timeout": 999999}
                    }
                }
            )


# =========================================================================
# 3. The loader
# =========================================================================


class TestLoadWithComponents:
    def test_components_are_read_from_the_repo_config(self, tmp_path):
        _write_config(tmp_path, STUDY_TUTOR_SHAPE)
        declaration = load_toolchain_declaration(tmp_path)
        assert declaration.component("app").test == "flutter test"

    def test_a_components_only_block_is_not_treated_as_empty(self, tmp_path):
        """A repo may declare ONLY components. Dropping that block would
        silently un-declare every component task in the repo."""
        _write_config(
            tmp_path, {"components": {"app": {"cwd": "app", "test": "flutter test"}}}
        )
        declaration = load_toolchain_declaration(tmp_path)
        assert declaration is not None
        assert declaration.component_names == ["app"]

    def test_a_malformed_component_degrades_loudly_to_absent(self, tmp_path, caplog):
        _write_config(tmp_path, {"components": {"app": {"test": "flutter test"}}})
        with caplog.at_level("ERROR"):
            assert load_toolchain_declaration(tmp_path) is None
        assert any(r.levelname == "ERROR" for r in caplog.records)

    def test_a_component_install_is_named_as_declared_but_not_run(
        self, tmp_path, caplog
    ):
        """SCOPED OUT, LOUDLY: per-component install is not wired this lane;
        the declared install stays root-only (design §G)."""
        _write_config(tmp_path, STUDY_TUTOR_SHAPE)
        with caplog.at_level("WARNING"):
            load_toolchain_declaration(tmp_path)
        messages = [r.getMessage() for r in caplog.records]
        assert any("DECLARED BUT NOT RUN" in m and "app" in m for m in messages)

    def test_a_flat_declaration_is_unchanged(self, tmp_path):
        """Back-compat: ``components`` is Optional and defaults to None."""
        _write_config(tmp_path, {"test": "npm test"})
        declaration = load_toolchain_declaration(tmp_path)
        assert declaration.components is None
        assert declaration.component_names == []
        assert declaration.component("app") is None


# =========================================================================
# 4. THE SNAPSHOT LAW — unchanged, and proved unchanged
# =========================================================================


class TestSnapshotCoversComponents:
    def test_the_pin_round_trips_the_whole_nested_model(self, repo):
        """§B.2(iii): the pin is ``json.dumps(model_dump())`` read back by one
        ``model_validate`` — a nested field survives byte-for-byte, which is
        precisely why nesting costs ZERO snapshot changes."""
        root, worktree = repo
        _write_config(root, STUDY_TUTOR_SHAPE)
        declared = load_toolchain_declaration(root)
        snapshot_task_toolchain(_TASK_ID, worktree, root)
        pinned = load_toolchain_snapshot(_TASK_ID, worktree)
        assert pinned.model_dump(mode="json") == declared.model_dump(mode="json")

    def test_the_snapshot_file_carries_the_component_and_its_cwd(self, repo):
        root, worktree = repo
        _write_config(root, STUDY_TUTOR_SHAPE)
        path = snapshot_task_toolchain(_TASK_ID, worktree, root)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["components"]["app"]["test"] == "flutter test"
        assert data["components"]["app"]["cwd"] == "app"
        assert data["components"]["app"]["test_timeout"] == 900

    def test_a_mid_build_edit_cannot_change_a_components_test_command(self, repo):
        """THE ATTACK. A Player turn rewrites the component's command to
        ``true`` in BOTH trees; the pinned command is still what executes."""
        root, worktree = repo
        _write_config(root, STUDY_TUTOR_SHAPE)
        snapshot_task_toolchain(_TASK_ID, worktree, root)

        self_green = {
            "test": "true",
            "components": {"app": {"cwd": "app", "test": "true"}},
        }
        _write_config(worktree, self_green)
        _write_config(root, self_green)

        pinned = load_toolchain_snapshot(_TASK_ID, worktree)
        assert pinned.component("app").test == "flutter test"
        # ...and the live file really does say otherwise.
        assert load_toolchain_declaration(worktree).component("app").test == "true"

    def test_a_mid_build_edit_cannot_add_a_component(self, repo):
        """The inverse attack: a Player cannot invent a component (and its
        cwd) after the pin."""
        root, worktree = repo
        _write_config(root, {"test": "pytest -q"})
        snapshot_task_toolchain(_TASK_ID, worktree, root)
        _write_config(
            worktree, {"test": "pytest -q", "components": {"app": {"cwd": "app", "test": "true"}}}
        )
        assert load_toolchain_snapshot(_TASK_ID, worktree).components is None

    def test_the_snapshot_pair_needed_no_new_code_path(self):
        """§E stage 3: 'Zero edits to snapshot_task_toolchain /
        load_toolchain_snapshot — if either needs to change, the design was
        wrong and the stage stops.' Structural pin: neither function mentions
        components at all; they still dump and validate the WHOLE model."""
        assert "components" not in inspect.getsource(snapshot_task_toolchain)
        assert "components" not in inspect.getsource(load_toolchain_snapshot)
        assert "model_dump" in inspect.getsource(snapshot_task_toolchain)
        assert "model_validate" in inspect.getsource(load_toolchain_snapshot)

    def test_snapshot_paths_are_still_the_one_task_private_file(self, repo):
        root, worktree = repo
        _write_config(root, STUDY_TUTOR_SHAPE)
        snapshot_task_toolchain(_TASK_ID, worktree, root)
        paths = toolchain_snapshot_paths(_TASK_ID, worktree)
        assert paths["file"].exists()
        assert paths["file"].name == "toolchain.json"


# =========================================================================
# 5. resolve_component_cwd — the belt-and-braces containment check
# =========================================================================


class TestResolveComponentCwd:
    def test_a_contained_cwd_resolves_under_the_base(self, tmp_path):
        (tmp_path / "app").mkdir()
        assert resolve_component_cwd(tmp_path, "app") == tmp_path / "app"

    def test_a_symlink_that_escapes_is_refused(self, tmp_path):
        """No schema can see a symlink; this check can."""
        outside = tmp_path / "outside"
        outside.mkdir()
        base = tmp_path / "worktree"
        base.mkdir()
        (base / "app").symlink_to(outside, target_is_directory=True)
        with pytest.raises(ValueError, match="outside the worktree"):
            resolve_component_cwd(base, "app")


# =========================================================================
# 6. THE SELECTOR — lifted from frontmatter, validated LOUDLY
# =========================================================================


def _orchestrator(root):
    from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

    orchestrator = AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)
    orchestrator.repo_root = root
    return orchestrator


class TestComponentSelector:
    def test_absent_selector_means_the_root_component(self, tmp_path):
        """Today's semantics, unchanged — including on a componented repo."""
        _write_config(tmp_path, STUDY_TUTOR_SHAPE)
        assert _orchestrator(tmp_path)._resolve_task_component(_TASK_ID, None) is None

    def test_a_declared_component_resolves(self, tmp_path):
        _write_config(tmp_path, STUDY_TUTOR_SHAPE)
        assert (
            _orchestrator(tmp_path)._resolve_task_component(_TASK_ID, "app") == "app"
        )

    def test_an_undeclared_component_is_a_loud_task_load_failure(self, tmp_path):
        _write_config(tmp_path, STUDY_TUTOR_SHAPE)
        with pytest.raises(ValueError) as exc:
            _orchestrator(tmp_path)._resolve_task_component(_TASK_ID, "api")
        message = str(exc.value)
        assert "api" in message
        assert "declared: app" in message
        assert "NOT used as a fallback" in message

    def test_a_component_on_a_repo_with_no_declaration_is_loud(self, tmp_path):
        with pytest.raises(ValueError, match="declares no such component"):
            _orchestrator(tmp_path)._resolve_task_component(_TASK_ID, "app")

    def test_a_component_on_a_flat_declaration_is_loud(self, tmp_path):
        _write_config(tmp_path, {"test": "pytest -q"})
        with pytest.raises(ValueError, match="<none>"):
            _orchestrator(tmp_path)._resolve_task_component(_TASK_ID, "app")

    @pytest.mark.parametrize("bad", ["", "   ", 7, ["app"], {"name": "app"}])
    def test_a_non_name_selector_is_loud(self, tmp_path, bad):
        _write_config(tmp_path, STUDY_TUTOR_SHAPE)
        with pytest.raises(ValueError, match="Invalid `component:`"):
            _orchestrator(tmp_path)._resolve_task_component(_TASK_ID, bad)

    def test_the_selector_is_whitespace_trimmed(self, tmp_path):
        _write_config(tmp_path, STUDY_TUTOR_SHAPE)
        assert (
            _orchestrator(tmp_path)._resolve_task_component(_TASK_ID, " app ") == "app"
        )


class TestSelectorLiftIsOutsideTheMetadataSwallow:
    """The D.1a cure's precedent: a verdict-bearing declaration's schema error
    must NEVER be swallowed by the broad metadata ``except``."""

    def test_the_lift_is_raw_and_the_validation_sits_after_the_try(self):
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        source = inspect.getsource(AutoBuildOrchestrator.orchestrate)
        lift = source.index('_component_raw = frontmatter.get("component")')
        swallow = source.index("Failed to load task metadata from task file")
        validate = source.index("self._resolve_task_component(task_id, _component_raw)")
        assert lift < swallow < validate

    def test_the_frontmatter_key_is_component(self):
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        source = inspect.getsource(AutoBuildOrchestrator.orchestrate)
        assert 'frontmatter.get("component")' in source

    def test_the_selector_reaches_the_validator_constructor(self):
        """Threaded like ``behavioural_oracle``: orchestrate → loop → turn →
        coach → CoachValidator. Without the last hop the seam is dead wire."""
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        for method in (
            AutoBuildOrchestrator._loop_phase,
            AutoBuildOrchestrator._execute_turn,
            AutoBuildOrchestrator._invoke_coach_safely,
            AutoBuildOrchestrator._invoke_coach_primary,
            AutoBuildOrchestrator._invoke_coach_legacy,
        ):
            assert "component" in inspect.signature(method).parameters
        primary = inspect.getsource(AutoBuildOrchestrator._invoke_coach_primary)
        assert "CoachValidator(" in primary
        assert "component=component" in primary

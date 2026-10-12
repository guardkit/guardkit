"""Integration contract for the shipped React/Go monorepo template."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess

import pytest
import yaml

from guardkit.cli.init import apply_template
from guardkit.knowledge.autobuild_context_loader import AutoBuildContextLoader
from guardkit.knowledge.template_pattern_loader import (
    TemplatePatternContext,
    load_template_patterns,
    select_patterns,
)
from guardkit.orchestrator.toolchain_declaration import (
    load_toolchain_declaration,
    parse_toolchain_block,
    resolve_component_cwd,
)
from guardkit.templates.coverage_matrix import (
    COVERAGE_ENFORCED,
    compute_coverage_for_dir,
)
from guardkit.templates.parse_gate import (
    FileStatus,
    language_for_rendered_name,
    parse_findings,
    validate_template_dir,
)
from guardkit.templates.patterns_manifest import load_patterns_manifest
from guardkit.templates.resolver import resolve_template_source_dir
from installer.core.commands.lib.agent_discovery import (
    discover_agents,
    validate_discovery_metadata,
)
from tests.integration.verify_react_go_template import materialise


TEMPLATE = "react-go-monorepo"


@pytest.fixture(scope="module")
def template_dir() -> Path:
    source = resolve_template_source_dir(TEMPLATE)
    assert source is not None, f"{TEMPLATE} must be a discoverable installed template"
    return source


@pytest.fixture
def installed_project(tmp_path: Path, template_dir: Path) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    assert apply_template(TEMPLATE, project)
    return project


def _code_patterns(template_dir: Path) -> list[Path]:
    patterns = sorted((template_dir / "templates").rglob("*.template"))
    return [
        path
        for path in patterns
        if language_for_rendered_name(path.name.removesuffix(".template")) is not None
    ]


def _write_plan(project: Path, task_id: str, target: str) -> None:
    state_dir = project / "docs" / "state" / task_id
    state_dir.mkdir(parents=True)
    (state_dir / "implementation_plan.json").write_text(
        json.dumps({"plan": {"files_to_create": [target], "files_to_modify": []}}),
        encoding="utf-8",
    )


def test_init_installs_guidance_without_materialising_source(
    installed_project: Path, template_dir: Path
) -> None:
    project = installed_project
    source_manifest = json.loads(
        (template_dir / "manifest.json").read_text(encoding="utf-8")
    )
    installed_manifest = json.loads(
        (project / ".claude" / "manifest.json").read_text(encoding="utf-8")
    )
    assert installed_manifest == source_manifest
    assert installed_manifest["name"] == TEMPLATE

    source_rules = sorted((template_dir / ".claude" / "rules").rglob("*.md"))
    assert source_rules
    for source in source_rules:
        relative = source.relative_to(template_dir / ".claude" / "rules")
        assert (
            project / ".claude" / "rules" / relative
        ).read_bytes() == source.read_bytes()

    source_agents = sorted(
        set((template_dir / "agents").glob("*.md"))
        | set((template_dir / ".claude" / "agents").glob("*.md"))
    )
    assert source_agents
    for source in source_agents:
        assert (
            project / ".claude" / "agents" / source.name
        ).read_bytes() == source.read_bytes()

    assert (project / "CLAUDE.md").is_file()
    for path in (
        "apps",
        "templates",
        "config",
        "scripts",
        "go.mod",
        "package.json",
        ".guardkit/config.yaml",
    ):
        assert not (project / path).exists(), f"init must not materialise {path}"


def test_repeat_init_preserves_local_guidance(
    installed_project: Path, template_dir: Path
) -> None:
    project = installed_project
    rule_source = next((template_dir / ".claude" / "rules").rglob("*.md"))
    rule = (
        project
        / ".claude"
        / "rules"
        / rule_source.relative_to(template_dir / ".claude" / "rules")
    )
    rule.write_text("local rule edit\n", encoding="utf-8")
    manifest = project / ".claude" / "manifest.json"
    manifest.write_text(
        '{"name":"react-go-monorepo","local":true}\n', encoding="utf-8"
    )

    assert apply_template(TEMPLATE, project)
    assert rule.read_text(encoding="utf-8") == "local rule edit\n"
    assert json.loads(manifest.read_text(encoding="utf-8"))["local"] is True


def test_init_installed_specialists_are_discoverable(
    installed_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The real discovery scanner must select the installed local guides."""
    monkeypatch.chdir(installed_project)
    cases = (
        ("go-api-specialist", "implementation", ["go"], ["go", "api"]),
        ("monorepo-contract-specialist", "review", ["react"], ["react", "monorepo"]),
    )
    for name, phase, stack, keywords in cases:
        assert name in {
            agent.get("name") for agent in discover_agents(phase=phase, stack=stack)
        }
        matches = discover_agents(phase=phase, stack=stack, keywords=keywords)
        selected = next((agent for agent in matches if agent.get("name") == name), None)
        assert selected is not None, (name, matches)
        assert Path(selected["path"]) == installed_project / ".claude" / "agents" / (
            f"{name}.md"
        )
        assert selected["source"] == "local"
        assert selected["relevance_score"] > 0
        valid, errors = validate_discovery_metadata(selected)
        assert valid, errors
        assert "model" not in selected


def test_manifest_mappings_and_parsed_code_coverage(template_dir: Path) -> None:
    settings = json.loads((template_dir / "settings.json").read_text(encoding="utf-8"))
    assert set(settings["layer_mappings"]) == {"api", "web"}
    assert TEMPLATE in COVERAGE_ENFORCED

    code = _code_patterns(template_dir)
    api = [path for path in code if path.parent.name == "api"]
    web = [path for path in code if path.parent.name == "web"]
    assert 1 <= len(api) <= 3
    assert 1 <= len(web) <= 2
    assert all(path.suffixes[-2:] == [".go", ".template"] for path in api)
    assert all(
        path.suffixes[-2:] in ([".ts", ".template"], [".tsx", ".template"])
        for path in web
    )

    manifest = load_patterns_manifest(template_dir)
    assert manifest is not None
    listed = {entry.file: entry for entry in manifest.patterns}
    for path in api + web:
        rel = path.relative_to(template_dir / "templates").as_posix()
        assert rel in listed
        assert listed[rel].layer == path.parent.name

    results = validate_template_dir(template_dir, TEMPLATE)
    by_path = {result.rel_path: result for result in results}
    for path in code:
        rel = f"{TEMPLATE}/{path.relative_to(template_dir).as_posix()}"
        assert by_path[rel].status is FileStatus.OK, by_path[rel]
    assert all(
        result.status is FileStatus.OK
        for result in results
        if result.language is not None
    ), results
    assert not any(result.status is FileStatus.OPTOUT for result in results)

    coverage = compute_coverage_for_dir(template_dir, TEMPLATE)
    assert coverage.enforced
    assert coverage.total_count == 2
    assert coverage.fully_covered, coverage.non_covered


def test_go_is_a_real_parse_gate_language() -> None:
    assert language_for_rendered_name("route.go") == "go"
    assert not parse_findings("package main\nfunc main() { answer := 42; _ = answer }\n", "go")
    assert parse_findings("package main\nfunc main( {\n", "go")


def test_go_fallback_does_not_treat_mongodb_as_go(tmp_path: Path) -> None:
    files = []
    for rel in ("api/handler.go.template", "web/App.tsx.template", "config/README.md.template"):
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("example\n", encoding="utf-8")
        files.append(path)
    context = TemplatePatternContext(None, None, files)
    go = select_patterns(context, tech_stack="Go", file_path_hints=[])
    assert [path.parent.name for path in go.selected_files] == ["api"]
    mongo = select_patterns(context, tech_stack="MongoDB", file_path_hints=[])
    assert len(mongo.selected_files) == len(files)


@pytest.mark.asyncio
async def test_default_player_context_contains_both_stacks_within_caps(
    installed_project: Path, template_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GUARDKIT_PATTERN_SELECTION_V2", raising=False)
    context = load_template_patterns(installed_project / ".claude" / "manifest.json")
    assert context.template_dir == template_dir
    assert "Go" in context.tech_stack
    assert "React" in context.tech_stack
    selected = select_patterns(
        context, tech_stack=context.tech_stack, file_path_hints=[]
    )
    core = [
        path
        for path in _code_patterns(template_dir)
        if path.parent.name in {"api", "web"}
    ]
    assert set(selected.selected_files) == set(core)
    assert len(selected.selected_files) <= 5
    assert (
        sum(
            len(path.read_text(encoding="utf-8")) // 4
            for path in selected.selected_files
        )
        <= 3000
    )
    assert {path.parent.name for path in selected.selected_files} >= {"api", "web"}

    loader = AutoBuildContextLoader(graphiti=None, worktree_path=installed_project)
    result = await loader.get_player_context(
        task_id="TASK-RG-DEFAULT",
        feature_id="FEAT-RG",
        turn_number=1,
        description="Build the foundation",
    )
    assert f"Stack Pattern Reference (from {TEMPLATE} template)" in result.prompt_text
    assert "/templates/api/" in result.prompt_text
    assert "/templates/web/" in result.prompt_text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("task_id", "target", "expected_layer"),
    [
        ("TASK-RG-WEB", "apps/web/src/App.tsx", "web"),
        ("TASK-RG-API", "apps/api/internal/notes/handler.go", "api"),
    ],
)
async def test_v2_player_context_uses_planned_target(
    installed_project: Path,
    monkeypatch: pytest.MonkeyPatch,
    task_id: str,
    target: str,
    expected_layer: str,
) -> None:
    monkeypatch.setenv("GUARDKIT_PATTERN_SELECTION_V2", "1")
    _write_plan(installed_project, task_id, target)
    loader = AutoBuildContextLoader(graphiti=None, worktree_path=installed_project)
    assert target in (loader._resolve_file_path_hints(task_id) or [])
    source = load_template_patterns(installed_project / ".claude" / "manifest.json")
    targeted = select_patterns(
        source, tech_stack=source.tech_stack, file_path_hints=[target]
    )
    assert any(path.parent.name == expected_layer for path in targeted.selected_files)
    result = await loader.get_player_context(
        task_id=task_id,
        feature_id="FEAT-RG",
        turn_number=1,
        description="Implement one planned target",
    )
    assert f"/templates/{expected_layer}/" in result.prompt_text
    headings = [
        line.removeprefix("### ")
        for line in result.prompt_text.splitlines()
        if line.startswith("### ")
    ]
    assert headings == [str(path) for path in targeted.selected_files]


@pytest.fixture
def rendered(tmp_path: Path) -> Path:
    """The exact literal layout, rendered by the native fixture's own materialiser."""
    output = tmp_path / "rendered"
    materialise(output)
    return output


def _rendered_config(rendered: Path) -> dict:
    return yaml.safe_load(
        (rendered / ".guardkit" / "config.yaml").read_text(encoding="utf-8")
    )


def test_rendered_toolchain_declaration_parses_through_real_parser(
    rendered: Path,
) -> None:
    raw = _rendered_config(rendered)
    declaration = parse_toolchain_block(raw["toolchain"])
    assert load_toolchain_declaration(rendered) == declaration

    assert declaration.install == "bash scripts/install.sh"
    assert declaration.test == "bash scripts/check.sh"
    assert declaration.feature_check == "bash scripts/check-feature.sh"
    for key in ("install_timeout", "test_timeout", "feature_check_timeout"):
        assert key in raw["toolchain"], f"root {key} must be explicit"
    assert declaration.runtime is not None
    assert declaration.runtime.go == (rendered / ".go-version").read_text().strip()
    assert declaration.runtime.node == (rendered / ".nvmrc").read_text().strip()
    for script in ("install.sh", "check.sh", "check-feature.sh", "require-tools.sh"):
        assert (rendered / "scripts" / script).is_file()

    assert declaration.component_names == ["api", "web"]
    expected = {"web": ("apps/web", "package.json"), "api": ("apps/api", "go.mod")}
    for name, (cwd, manifest) in expected.items():
        component = declaration.component(name)
        assert component is not None
        assert component.cwd == cwd
        resolved = resolve_component_cwd(rendered, component.cwd)
        assert resolved.resolve().is_relative_to(rendered.resolve())
        assert (resolved / manifest).is_file()
        assert component.test
        assert component.install is None, "component installs are not consumed"
        assert "test_timeout" in raw["toolchain"]["components"][name]
        assert component.requires_ran_marker is True
        assert component.ran_marker_regex

    web = declaration.component("web")
    api = declaration.component("api")
    assert web is not None and api is not None
    assert re.search(web.ran_marker_regex, "      Tests  2 passed (2)\n")
    assert not re.search(web.ran_marker_regex, "No test files found, exiting\n")
    assert re.search(api.ran_marker_regex, "?   \tex/cmd/api\t[no test files]\nok  \tex/internal/notes\t1.1s\n")
    assert not re.search(api.ran_marker_regex, "?   \tex/cmd/api\t[no test files]\n")
    for flag in ("-race", "-count=1", "GOTOOLCHAIN=local"):
        assert flag in api.test
    assert "go test -race -count=1 ./..." in (
        rendered / "scripts" / "check.sh"
    ).read_text(encoding="utf-8")
    assert declaration.requires_ran_marker is True
    assert re.search(declaration.ran_marker_regex, "ok  \tex/internal/notes\t1.1s\n")


def test_rendered_launch_block_declares_settings_and_scratch(rendered: Path) -> None:
    """Raw YAML only: GuardKit has no launch.scratch reader yet (web readiness W1b)."""
    raw = _rendered_config(rendered)
    assert "shell_environment" not in raw["toolchain"]
    assert raw["launch"] == {
        "settings": ["PLAYWRIGHT_BROWSERS_PATH"],
        "scratch": ["GOPATH", "GOCACHE", "npm_config_cache"],
    }


def test_feature_check_stub_fails_until_foundation_supplies_it(rendered: Path) -> None:
    result = subprocess.run(
        ["bash", "scripts/check-feature.sh"],
        cwd=rendered,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0
    assert result.stdout == ""
    assert "no connected feature check yet" in result.stderr


def test_install_refuses_missing_toolchain_before_installing(
    rendered: Path, tmp_path: Path
) -> None:
    """install.sh shares check.sh's exact guards and installs nothing without them."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for tool in ("dirname", "awk"):
        found = shutil.which(tool)
        assert found is not None
        (bin_dir / tool).symlink_to(found)
    bash = shutil.which("bash")
    assert bash is not None
    for script in ("install.sh", "check.sh"):
        assert "source scripts/require-tools.sh" in (
            rendered / "scripts" / script
        ).read_text(encoding="utf-8")
        result = subprocess.run(
            [bash, f"scripts/{script}"],
            cwd=rendered,
            env={"PATH": str(bin_dir), "HOME": os.environ.get("HOME", str(tmp_path))},
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 1, (script, result.stderr)
        assert "go is required" in result.stderr
    assert not (rendered / "node_modules").exists()

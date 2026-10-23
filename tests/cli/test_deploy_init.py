"""``guardkit deploy init``: copies the deployment kit, fills it, never clobbers,
and writes a profile both GuardKit and the factory (Forge) accept as a first
deployment profile."""

from __future__ import annotations

import importlib.util
import os
import stat
import sys
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from guardkit.cli.main import cli
from guardkit.qa.formats import QAFormatError, validate_instance
from guardkit.templates.deploy_kit import (
    DeployKitError,
    install_deploy_kit,
    kit_source_dir,
)

ARGS = [
    "deploy", "init",
    "--env-id", "myapp",
    "--live-port", "18961",
    "--candidate-port", "18962",
    "--health-path", "/health",
]
KIT_FILES = {
    "deploy/README.md",
    "deploy/deploy.sh",
    "deploy/healthcheck.sh",
    "deploy/lib.sh",
    "deploy/live-gate.sh",
    "deploy/profile.yaml",
    "deploy/settings.sh",
}


def _init(project: Path, *extra: str):
    return CliRunner().invoke(cli, [*ARGS, "--project-dir", str(project), *extra])


def test_init_writes_the_whole_kit(tmp_path: Path) -> None:
    done = _init(tmp_path)
    assert done.exit_code == 0, done.output
    written = {str(p.relative_to(tmp_path)) for p in (tmp_path / "deploy").rglob("*") if p.is_file()}
    assert written == KIT_FILES
    assert "valid deploy-profile" in done.output
    # Tells the project, in the README's words, what is still its own.
    assert "What to do next:" in done.output
    assert "publishes ${APP_PORT} to whatever port the app listens on" in done.output
    # Binding to the sandbox's own loopback makes the app unreachable from the host.
    assert '"${APP_PORT}:8080", not 127.0.0.1:${APP_PORT}' in done.output
    assert "cannot be reached from the host" in done.output
    assert "never bind-mount a project folder" in done.output
    assert "Every service must keep running" in done.output


def test_readme_publishes_app_port_on_all_sandbox_interfaces(tmp_path: Path) -> None:
    # The sandbox forwards ports only to the host's loopback; a mapping bound to
    # the sandbox's own 127.0.0.1 is unreachable from the host.
    _init(tmp_path)
    readme = (tmp_path / "deploy" / "README.md").read_text()
    assert '- "${APP_PORT:?APP_PORT is required}:8080"' in readme
    assert '"127.0.0.1:${APP_PORT' not in readme
    assert "cannot be reached from the" in readme


def test_scripts_are_executable(tmp_path: Path) -> None:
    _init(tmp_path)
    for name in ("deploy.sh", "healthcheck.sh", "live-gate.sh"):
        mode = (tmp_path / "deploy" / name).stat().st_mode
        assert mode & stat.S_IXUSR, name


def test_placeholders_are_filled(tmp_path: Path) -> None:
    _init(tmp_path)
    profile = yaml.safe_load((tmp_path / "deploy" / "profile.yaml").read_text())
    assert profile["env_id"] == "myapp"
    assert profile["candidate"]["env"] == {
        "CANDIDATE_PORT": "18962",
        "COMPOSE_PROJECT_NAME": "myapp-cand",
    }
    settings = (tmp_path / "deploy" / "settings.sh").read_text()
    assert 'DEPLOY_ENV_ID="myapp"' in settings
    assert 'DEPLOY_LIVE_PORT="18961"' in settings
    assert 'DEPLOY_CANDIDATE_PORT="18962"' in settings
    assert 'DEPLOY_HEALTH_PATH="/health"' in settings
    for path in (tmp_path / "deploy").iterdir():
        assert "__" not in path.read_text().replace("__pycache__", ""), path.name


def test_written_profile_validates(tmp_path: Path) -> None:
    _init(tmp_path)
    instance = validate_instance("deploy-profile", tmp_path / "deploy" / "profile.yaml")
    assert instance.env_id == "myapp"
    assert instance.identity is not None and instance.identity.asked_with == "RUNNING_IDENTITY"
    assert instance.live_gate is not None and instance.live_gate.driver == ["deploy/live-gate.sh"]


def test_never_overwrites_and_reports_skips(tmp_path: Path) -> None:
    (tmp_path / "deploy").mkdir()
    own = "#!/usr/bin/env bash\n# the project's own deploy step\n"
    (tmp_path / "deploy" / "deploy.sh").write_text(own)
    done = _init(tmp_path)
    assert done.exit_code == 0, done.output
    assert (tmp_path / "deploy" / "deploy.sh").read_text() == own
    assert "skipped deploy/deploy.sh" in done.output
    again = _init(tmp_path)
    assert again.exit_code == 0
    assert again.output.count("skipped") == len(KIT_FILES)
    assert "wrote" not in again.output


def test_existing_invalid_profile_fails_validation(tmp_path: Path) -> None:
    (tmp_path / "deploy").mkdir()
    # Every value the command compares agrees; the profile is still invalid
    # (no compose section), which validation catches.
    (tmp_path / "deploy" / "profile.yaml").write_text(
        'format_version: "1.0"\nenv_id: myapp\n'
        "candidate: {env: {CANDIDATE_PORT: '18962', COMPOSE_PROJECT_NAME: myapp-cand}}\n"
    )
    done = _init(tmp_path)
    assert done.exit_code == 1
    assert "skipped deploy/profile.yaml" in done.output
    assert "not a valid deploy-profile" in done.output


@pytest.mark.parametrize(
    "option, value, words",
    [
        ("--env-id", "other", "environment id myapp, not other"),
        ("--live-port", "19000", "live port 18961, not 19000"),
        ("--candidate-port", "19001", "candidate port 18962, not 19001"),
        ("--health-path", "/ready", "health path /health, not /ready"),
    ],
)
def test_rerun_with_different_values_is_refused(tmp_path: Path, option: str, value: str, words: str) -> None:
    assert _init(tmp_path).exit_code == 0
    before = {p.name: p.read_bytes() for p in (tmp_path / "deploy").iterdir()}
    args = list(ARGS)
    args[args.index(option) + 1] = value
    done = CliRunner().invoke(cli, [*args, "--project-dir", str(tmp_path)])
    assert done.exit_code == 2, done.output
    assert words in " ".join(done.output.split())
    assert {p.name: p.read_bytes() for p in (tmp_path / "deploy").iterdir()} == before


def _rewrite_settings(project: Path, old: str, new: str) -> None:
    path = project / "deploy" / "settings.sh"
    text = path.read_text()
    assert old in text
    path.write_text(text.replace(old, new))


@pytest.mark.parametrize(
    "old, new",
    [
        ('DEPLOY_ENV_ID="myapp"', "DEPLOY_ENV_ID='myapp'"),
        ('DEPLOY_LIVE_PORT="18961"', "DEPLOY_LIVE_PORT=18961  # the live port"),
        ('DEPLOY_HEALTH_PATH="/health"', "export DEPLOY_HEALTH_PATH='/health' # health"),
    ],
)
def test_rerun_understands_plain_literal_forms(tmp_path: Path, old: str, new: str) -> None:
    _init(tmp_path)
    _rewrite_settings(tmp_path, old, new)
    done = _init(tmp_path)
    assert done.exit_code == 0, done.output
    assert "the existing settings already match" in " ".join(done.output.split())


@pytest.mark.parametrize(
    "old, new, words",
    [
        ('DEPLOY_ENV_ID="myapp"', "DEPLOY_ENV_ID='other'", "environment id other, not myapp"),
        ('DEPLOY_LIVE_PORT="18961"', "DEPLOY_LIVE_PORT=19000 # moved", "live port 19000, not 18961"),
        ('DEPLOY_HEALTH_PATH="/health"', "", "does not set DEPLOY_HEALTH_PATH"),
        ('DEPLOY_LIVE_PORT="18961"', 'DEPLOY_LIVE_PORT="$PORT"', "DEPLOY_LIVE_PORT to something that is not a plain value"),
        ('DEPLOY_LIVE_PORT="18961"', "DEPLOY_LIVE_PORT=18961#x", "not a plain value"),
    ],
)
def test_rerun_refuses_settings_it_cannot_confirm(tmp_path: Path, old: str, new: str, words: str) -> None:
    _init(tmp_path)
    _rewrite_settings(tmp_path, old, new)
    before = {p.name: p.read_bytes() for p in (tmp_path / "deploy").iterdir()}
    done = _init(tmp_path)
    assert done.exit_code == 2, done.output
    assert words in " ".join(done.output.split())
    assert {p.name: p.read_bytes() for p in (tmp_path / "deploy").iterdir()} == before


def test_rerun_refuses_a_profile_without_the_candidate_settings(tmp_path: Path) -> None:
    (tmp_path / "deploy").mkdir()
    (tmp_path / "deploy" / "profile.yaml").write_text(
        'format_version: "1.0"\nenv_id: myapp\ncompose: {file: compose.yaml}\n'
    )
    done = _init(tmp_path)
    assert done.exit_code == 2
    assert "has no candidate.env" in " ".join(done.output.split())
    assert not (tmp_path / "deploy" / "settings.sh").exists()


def test_rerun_with_the_same_values_says_they_match(tmp_path: Path) -> None:
    _init(tmp_path)
    done = _init(tmp_path)
    assert done.exit_code == 0
    assert "the existing settings already match" in " ".join(done.output.split())


@pytest.mark.parametrize(
    "option, value",
    [
        ("--env-id", "My_App"),
        ("--env-id", "1app"),
        ("--env-id", "app-"),
        ("--live-port", "80"),
        ("--candidate-port", "18961"),
        ("--health-path", "health"),
        ("--health-path", "/health?x=1"),
    ],
)
def test_bad_values_are_refused_before_writing(tmp_path: Path, option: str, value: str) -> None:
    args = list(ARGS)
    args[args.index(option) + 1] = value
    done = CliRunner().invoke(cli, [*args, "--project-dir", str(tmp_path)])
    assert done.exit_code == 2, done.output
    assert not (tmp_path / "deploy").exists()


def test_install_reports_written_and_skipped(tmp_path: Path) -> None:
    first = install_deploy_kit(tmp_path, env_id="a", live_port=2000, candidate_port=2001, health_path="/")
    assert set(first.written) == KIT_FILES and first.skipped == []
    second = install_deploy_kit(tmp_path, env_id="a", live_port=2000, candidate_port=2001, health_path="/")
    assert second.written == [] and set(second.skipped) == KIT_FILES


def test_missing_kit_is_an_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "guardkit.templates.deploy_kit._get_templates_base_dir", lambda: tmp_path / "nowhere"
    )
    with pytest.raises(DeployKitError, match="not in this GuardKit installation"):
        kit_source_dir()


def test_identity_block_names_are_checked(tmp_path: Path) -> None:
    path = tmp_path / "profile.yaml"
    path.write_text(
        'format_version: "1.0"\nenv_id: x\ncompose: {file: compose.yaml}\n'
        "identity: {setting: 'NOT A NAME'}\n"
    )
    with pytest.raises(QAFormatError):
        validate_instance("deploy-profile", path)


# --- The factory's own reading of the written profile -------------------------------
#
# Forge accepts a project's FIRST deployment profile only when
# ``first_deployment_profile_is_usable`` (src/forge/pipeline/merge_executor.py,
# around line 2011) is true:
#
#     identity = declared_identity(profile)
#     return not (profile.candidate is None or profile.live_gate is None
#                 or not profile.live_gate.driver or not identity.declared
#                 or not identity.asked_with)
#
# Importing merge_executor needs the whole Forge package, so this loads Forge's
# two self-contained modules by path (the profile loader and
# pipeline/deployment_identity.py) and applies the same five conditions. Forge
# is found as the sibling checkout (as the B8 seam test does) or at FORGE_SRC
# (a ``src/forge`` folder); the test skips when neither is present.


def _forge_src() -> Path | None:
    configured = os.environ.get("FORGE_SRC")
    candidates = [Path(configured)] if configured else []
    candidates.append(Path(__file__).resolve().parents[3] / "forge" / "src" / "forge")
    for candidate in candidates:
        if (candidate / "deploy" / "profile.py").is_file() and (
            candidate / "pipeline" / "deployment_identity.py"
        ).is_file():
            return candidate
    return None


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_forge_accepts_the_profile_as_a_first_deployment_profile(tmp_path: Path) -> None:
    forge = _forge_src()
    if forge is None:
        pytest.skip("Forge source not found (sibling checkout or FORGE_SRC)")
    loader = _load("forge_deploy_profile_kit", forge / "deploy" / "profile.py")
    identity_mod = _load("forge_deployment_identity_kit", forge / "pipeline" / "deployment_identity.py")

    _init(tmp_path)
    profile = loader.load_deploy_profile(tmp_path / "deploy" / "profile.yaml")
    identity = identity_mod.declared_identity(profile)

    # first_deployment_profile_is_usable, condition by condition.
    assert profile.candidate is not None
    assert profile.live_gate is not None and list(profile.live_gate.driver) == ["deploy/live-gate.sh"]
    assert identity.declared
    assert identity.asked_with == "RUNNING_IDENTITY"
    # And the names the scripts use are the names Forge will hand and read.
    assert identity.setting == "DEPLOY_IDENTITY"
    assert identity.marker == "DEPLOYED_IDENTITY"
    assert identity.checked_as == "CHECKED_ARTIFACT"
    assert identity.artifact_setting == "DEPLOY_ARTIFACT"
    assert identity.running_as == "RUNNING_IDENTITY"
    assert profile.compose.script == "deploy/deploy.sh"
    assert [h.cmd for h in profile.health_checks] == ["deploy/healthcheck.sh"]
    assert dict(profile.candidate.env) == {
        "CANDIDATE_PORT": "18962",
        "COMPOSE_PROJECT_NAME": "myapp-cand",
    }
    assert profile.candidate.keep is False
    assert profile.preview is None and profile.sandbox is None and profile.rollback_image_ref is None
    # Every script the profile names is one the kit wrote, and is executable.
    for script in [profile.compose.script, *profile.live_gate.driver,
                   *(h.cmd for h in profile.health_checks)]:
        assert os.access(tmp_path / script, os.X_OK), script

"""Behaviour of install.sh's ``setup_pi_integration`` (the ``--pi`` option).

The real shell function is extracted from install.sh and executed with bash
against temporary directories: a fake ``~/.agentecflow`` holding the repo's own
command files, a disposable ``HOME`` and an explicit ``PI_CODING_AGENT_DIR``.
Nothing outside ``tmp_path`` is touched.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
INSTALL_SH = REPO_ROOT / "installer" / "scripts" / "install.sh"
COMMANDS = REPO_ROOT / "installer" / "core" / "commands"


def _function(script: str, name: str) -> str:
    """Return ``name() { ... }`` up to the first line that is exactly ``}``."""
    match = re.search(rf"^{re.escape(name)}\(\)\s*\{{\n.*?^\}}$", script, re.MULTILINE | re.DOTALL)
    assert match, f"{name}() not found in install.sh"
    return match.group(0)


@pytest.fixture(scope="module")
def functions() -> str:
    script = INSTALL_SH.read_text(encoding="utf-8")
    names = ["print_message", "print_success", "print_error", "print_info", "print_warning", "setup_pi_integration"]
    return "\n".join(_function(script, n) for n in names)


@pytest.fixture
def env(tmp_path: Path) -> dict:
    home = tmp_path / "home"
    install_dir = home / ".agentecflow"
    (install_dir / "commands").mkdir(parents=True)
    for path in COMMANDS.glob("*.md"):
        shutil.copy(path, install_dir / "commands" / path.name)
    shutil.copy(COMMANDS / "MANIFEST.json", install_dir / "commands" / "MANIFEST.json")
    return {
        "home": home,
        "install_dir": install_dir,
        "pi_dir": tmp_path / "pi-agent",
    }


def _run(functions: str, env: dict, pi_dir_override: bool = True) -> subprocess.CompletedProcess:
    process_env = {
        "PATH": os.environ["PATH"],
        "HOME": str(env["home"]),
        "INSTALL_DIR": str(env["install_dir"]),
        "INSTALLER_DIR": str(REPO_ROOT / "installer"),
        "AGENTECFLOW_VERSION": "9.9.9",
    }
    if pi_dir_override:
        process_env["PI_CODING_AGENT_DIR"] = str(env["pi_dir"])
    script = (
        "set -e\nRED= GREEN= YELLOW= BLUE= BOLD= NC=\n"
        + functions
        + "\nsetup_pi_integration\n"
    )
    return subprocess.run(["bash", "-c", script], env=process_env, capture_output=True, text=True)


def _commands() -> list[str]:
    return sorted(p.stem for p in COMMANDS.glob("*.md") if not p.stem.endswith("-ext"))


def test_one_explicit_wrapper_per_command_and_none_for_ext(functions, env):
    result = _run(functions, env)
    assert result.returncode == 0, result.stderr + result.stdout
    skills = env["pi_dir"] / "skills" / "guardkit"
    assert sorted(p.name for p in skills.iterdir() if p.is_dir()) == _commands()
    assert not any(p.name.endswith("-ext") for p in skills.iterdir())

    wrapper = (skills / "feature-plan" / "SKILL.md").read_text()
    installed = env["install_dir"] / "commands" / "feature-plan.md"
    digest = hashlib.sha256(installed.read_bytes()).hexdigest()
    assert "name: feature-plan\n" in wrapper
    assert "disable-model-invocation: true\n" in wrapper
    assert f"sha256={digest}" in wrapper
    assert str(installed) in wrapper
    assert str(env["install_dir"] / "pi" / "guardkit-on-pi.md") in wrapper
    # The command text itself is not copied into the wrapper.
    assert "Orchestrates the feature planning workflow" not in wrapper
    assert "$@" not in wrapper and "$ARGUMENTS" not in wrapper


def test_identity_record_matches_installed_files(functions, env):
    assert _run(functions, env).returncode == 0
    record = json.loads((env["pi_dir"] / "skills" / "guardkit" / "guardkit-pi.json").read_text())
    assert record["guardkit_version"] == "9.9.9"
    assert re.fullmatch(r"[0-9a-f]{40}|unknown", record["source_revision"])
    adapter = env["install_dir"] / "pi" / "guardkit-on-pi.md"
    assert adapter.read_bytes() == (REPO_ROOT / "installer" / "pi" / "guardkit-on-pi.md").read_bytes()
    assert record["adapter"]["sha256"] == hashlib.sha256(adapter.read_bytes()).hexdigest()
    assert sorted(record["commands"]) == _commands()
    for name, entry in record["commands"].items():
        installed = env["install_dir"] / "commands" / f"{name}.md"
        assert entry["sha256"] == hashlib.sha256(installed.read_bytes()).hexdigest()
        assert entry["manifest_sha256"] == entry["sha256"], name


def test_rerun_is_idempotent_and_drops_retired_commands(functions, env):
    assert _run(functions, env).returncode == 0
    skills = env["pi_dir"] / "skills" / "guardkit"
    before = {p.relative_to(skills): p.read_bytes() for p in skills.rglob("SKILL.md")}

    (env["install_dir"] / "commands" / "debug.md").unlink()  # a command retired upstream
    assert _run(functions, env).returncode == 0
    after = {p.relative_to(skills): p.read_bytes() for p in skills.rglob("SKILL.md")}
    assert Path("debug/SKILL.md") not in after
    del before[Path("debug/SKILL.md")]
    assert after == before
    assert not list((env["pi_dir"] / "skills").glob(".guardkit.staging.*"))


def test_user_files_in_the_pi_directory_are_preserved(functions, env):
    pi_dir = env["pi_dir"]
    user_files = {
        "settings.json": '{"theme": "dark"}',
        "models.json": "{}",
        "mcp.json": "{}",
        "auth.json": "{}",
        "trust.json": "{}",
        "APPEND_SYSTEM.md": "mine",
        "prompts/feature-plan.md": "my own prompt",
        "skills/my-skill/SKILL.md": "---\nname: my-skill\ndescription: mine\n---\n",
    }
    for rel, text in user_files.items():
        (pi_dir / rel).parent.mkdir(parents=True, exist_ok=True)
        (pi_dir / rel).write_text(text)
    assert _run(functions, env).returncode == 0
    assert _run(functions, env).returncode == 0
    for rel, text in user_files.items():
        assert (pi_dir / rel).read_text() == text, rel


def test_refuses_a_guardkit_skills_folder_it_did_not_create(functions, env):
    foreign = env["pi_dir"] / "skills" / "guardkit"
    foreign.mkdir(parents=True)
    (foreign / "SKILL.md").write_text("someone else's")
    result = _run(functions, env)
    assert result.returncode != 0
    assert "not created by GuardKit" in result.stdout + result.stderr
    assert [p.name for p in foreign.iterdir()] == ["SKILL.md"]
    assert (foreign / "SKILL.md").read_text() == "someone else's"


def test_pi_coding_agent_dir_wins_over_home(functions, env):
    assert _run(functions, env).returncode == 0
    assert (env["pi_dir"] / "skills" / "guardkit" / "guardkit-pi.json").is_file()
    assert not (env["home"] / ".pi").exists()


def test_defaults_to_home_pi_agent_without_override(functions, env):
    assert _run(functions, env, pi_dir_override=False).returncode == 0
    assert (env["home"] / ".pi" / "agent" / "skills" / "guardkit" / "guardkit-pi.json").is_file()


def test_pi_step_only_runs_with_the_pi_option():
    script = INSTALL_SH.read_text(encoding="utf-8")
    main = _function(script, "main")
    assert re.search(r'if \[ "\$INSTALL_PI" = true \]; then\n\s+setup_pi_integration\n\s+fi', main)
    assert main.index("setup_claude_integration") < main.index("setup_pi_integration")
    for options, expected in (("", "false false"), ("--pi", "false true"),
                              ("--pi --test-mode", "true true"), ("--test-mode", "true false")):
        block = re.search(r"^TEST_MODE=false\n.*?^done$", script, re.MULTILINE | re.DOTALL).group(0)
        out = subprocess.run(
            ["bash", "-c", f'set -- {options}\n{block}\necho "$TEST_MODE $INSTALL_PI"'],
            capture_output=True, text=True, check=True,
        ).stdout.strip().splitlines()[-1]
        assert out == expected, options

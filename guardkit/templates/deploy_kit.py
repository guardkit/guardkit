"""Install GuardKit's deployment kit into a project (``guardkit deploy init``).

Sibling of :mod:`guardkit.templates.qa_scaffold`, with the same rule: the kit
lives under ``installer/core/templates/common/deploy/`` and each file is copied
into ``<project>/deploy/`` only when absent, so a project's own files always
win. Files ending in ``.template`` are filled with the project's values and
written without that suffix.

The kit implements the software factory's deployment contract once, for any
project whose running service is a Docker Compose stack: a project supplies
only its root ``compose.yaml`` and a health path. Unlike the ``qa/`` scaffold
this is an explicit command, so a missing kit or a bad value is an error, not
a logged skip.
"""

from __future__ import annotations

import os
import re
import shutil
import stat
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import yaml

from guardkit.templates.resolver import _get_templates_base_dir

_DEPLOY_TEMPLATE_RELPATH = ("common", "deploy")
_TEMPLATE_SUFFIX = ".template"
#: Scripts the factory runs as programs; they are written executable.
_EXECUTABLES = frozenset({"deploy.sh", "healthcheck.sh", "live-gate.sh"})
_PLACEHOLDER_RE = re.compile(r"__[A-Z][A-Z_]*__")

#: Lower-case letters, digits and '-', starting with a letter: valid in a
#: compose project name and an image name, and safe in YAML unquoted or quoted.
ENV_ID_RE = re.compile(r"^[a-z][a-z0-9-]{0,39}$")
HEALTH_PATH_RE = re.compile(r"^/[A-Za-z0-9._~/-]*$")


class DeployKitError(ValueError):
    """A value or the kit itself is not usable; the message says which."""


@dataclass
class DeployKitResult:
    """What ``install_deploy_kit`` did, as paths relative to the project."""

    written: List[str] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)
    profile_path: Path | None = None
    #: True when an existing profile.yaml or settings.sh was kept; its values
    #: were checked and agree with the ones asked for.
    kept_settings: bool = False


_SETTING_WORDS = {
    "ENV_ID": "environment id",
    "LIVE_PORT": "live port",
    "CANDIDATE_PORT": "candidate port",
    "HEALTH_PATH": "health path",
}

#: An assignment of one of the four settings, as a line of deploy/settings.sh.
_ASSIGNMENT_RE = re.compile(
    r"^\s*(?:export\s+)?DEPLOY_(ENV_ID|LIVE_PORT|CANDIDATE_PORT|HEALTH_PATH)=(.*)$"
)
#: The plain literal forms understood on the right of ``=``: a double-quoted
#: string with nothing the shell would expand, a single-quoted string, or a
#: bare word; then optionally whitespace and a ``#`` comment (a ``#`` with no
#: space before it is part of the word in the shell, so it is not understood).
_LITERAL_RE = re.compile(
    r"""^(?:"(?P<dq>[^"$`\\]*)"|'(?P<sq>[^']*)'|(?P<bare>[^\s#'"$`\\;&|<>()]+))"""
    r"""(?:\s+#.*)?\s*$"""
)


def _read_settings(path: Path) -> tuple[dict[str, str], List[str]]:
    """The four settings as literally assigned in ``path``, and the problems.

    The last assignment of a setting wins, as in the shell. An assignment
    that is not a plain literal, and a setting that is never assigned, are
    problems: nothing is assumed about a value that was not read."""
    found: dict[str, str] = {}
    problems: List[str] = []
    text = path.read_text(encoding="utf-8", errors="replace")
    for number, line in enumerate(text.splitlines(), start=1):
        match = _ASSIGNMENT_RE.match(line)
        if not match:
            continue
        key, rest = match.group(1), match.group(2).strip()
        literal = _LITERAL_RE.match(rest)
        if literal is None:
            problems.append(
                f"deploy/settings.sh line {number} sets DEPLOY_{key} to something "
                "that is not a plain value"
            )
            continue
        found[key] = next(v for v in literal.group("dq", "sq", "bare") if v is not None)
    for key in _SETTING_WORDS:
        if key not in found and not any(f"DEPLOY_{key} " in p for p in problems):
            problems.append(f"deploy/settings.sh does not set DEPLOY_{key}")
    return found, problems


def existing_disagreements(project_dir: Path, values: dict[str, str]) -> List[str]:
    """Where an existing deploy/settings.sh or deploy/profile.yaml says
    something other than ``values`` (keys ENV_ID, LIVE_PORT, CANDIDATE_PORT,
    HEALTH_PATH), or does not plainly say it, as plain sentences. Empty when
    both files are absent or every relevant value was read and agrees."""
    found: List[str] = []
    settings = Path(project_dir) / "deploy" / "settings.sh"
    if settings.is_file():
        read, problems = _read_settings(settings)
        found.extend(problems)
        for key, value in read.items():
            if value != values[key]:
                found.append(
                    f"deploy/settings.sh has {_SETTING_WORDS[key]} {value}, not {values[key]}"
                )
    profile = Path(project_dir) / "deploy" / "profile.yaml"
    if profile.is_file():
        try:
            data = yaml.safe_load(profile.read_text(encoding="utf-8"))
        except (yaml.YAMLError, UnicodeDecodeError) as exc:
            return [*found, f"deploy/profile.yaml could not be read ({exc.__class__.__name__})"]
        if not isinstance(data, dict):
            return [*found, "deploy/profile.yaml is not a mapping"]
        env_id = data.get("env_id")
        if env_id is None:
            found.append("deploy/profile.yaml does not set env_id")
        elif str(env_id) != values["ENV_ID"]:
            found.append(f"deploy/profile.yaml has environment id {env_id}, not {values['ENV_ID']}")
        candidate = data.get("candidate")
        env = candidate.get("env") if isinstance(candidate, dict) else None
        if not isinstance(env, dict):
            found.append("deploy/profile.yaml has no candidate.env")
        else:
            wanted = {
                "CANDIDATE_PORT": values["CANDIDATE_PORT"],
                "COMPOSE_PROJECT_NAME": f"{values['ENV_ID']}-cand",
            }
            for name, value in wanted.items():
                have = env.get(name)
                if have is None:
                    found.append(f"deploy/profile.yaml does not set candidate.env {name}")
                elif str(have) != value:
                    found.append(f"deploy/profile.yaml has candidate.env {name} {have}, not {value}")
    return found


def kit_source_dir() -> Path:
    """The packaged kit directory, or :class:`DeployKitError` if it is missing."""
    src = Path(_get_templates_base_dir()).joinpath(*_DEPLOY_TEMPLATE_RELPATH)
    if not src.is_dir():
        raise DeployKitError(
            f"the deployment kit is not in this GuardKit installation ({src}); "
            "reinstall from a wheel built with installer/core force-included as "
            "guardkit/_installer_core, or run from a source checkout"
        )
    return src


def check_values(
    *, env_id: str, live_port: int, candidate_port: int, health_path: str
) -> None:
    """Refuse values the kit's scripts would refuse, before writing anything."""
    if not ENV_ID_RE.match(env_id) or env_id.endswith("-"):
        raise DeployKitError(
            f"--env-id {env_id!r} must be lower-case letters, digits and '-', "
            "starting with a letter, at most 40 characters"
        )
    for name, port in (("--live-port", live_port), ("--candidate-port", candidate_port)):
        if not 1024 <= port <= 65535:
            raise DeployKitError(f"{name} {port} must be between 1024 and 65535")
    if live_port == candidate_port:
        raise DeployKitError("--live-port and --candidate-port must differ")
    if not HEALTH_PATH_RE.match(health_path):
        raise DeployKitError(
            f"--health-path {health_path!r} must start with '/' and contain only "
            "letters, digits and . _ ~ / -"
        )


def _fill(text: str, values: dict[str, str], name: str) -> str:
    for key, value in values.items():
        text = text.replace(f"__{key}__", value)
    left = sorted(set(_PLACEHOLDER_RE.findall(text)))
    if left:
        raise DeployKitError(f"{name} still has unfilled placeholders: {', '.join(left)}")
    return text


def install_deploy_kit(
    project_dir: Path,
    *,
    env_id: str,
    live_port: int,
    candidate_port: int,
    health_path: str,
) -> DeployKitResult:
    """Copy the kit into ``project_dir/deploy``, never overwriting a file.

    Returns what was written and what was skipped because it already existed.
    The scripts are made executable when written.
    """
    check_values(
        env_id=env_id,
        live_port=live_port,
        candidate_port=candidate_port,
        health_path=health_path,
    )
    values = {
        "ENV_ID": env_id,
        "LIVE_PORT": str(live_port),
        "CANDIDATE_PORT": str(candidate_port),
        "HEALTH_PATH": health_path,
    }
    src_root = kit_source_dir()
    # A second run with other values must not quietly keep the old ones.
    differing = existing_disagreements(Path(project_dir), values)
    if differing:
        raise DeployKitError(
            "the project already has deployment settings that differ from the "
            "values given, so nothing was written: "
            + "; ".join(differing)
            + ". Change those files by hand, or run again with their values."
        )
    target_root = Path(project_dir) / "deploy"
    result = DeployKitResult(profile_path=target_root / "profile.yaml")

    for src in sorted(src_root.rglob("*")):
        if not src.is_file() or "__pycache__" in src.parts:
            continue
        rel = src.relative_to(src_root)
        is_template = rel.name.endswith(_TEMPLATE_SUFFIX)
        if is_template:
            rel = rel.with_name(rel.name[: -len(_TEMPLATE_SUFFIX)])
        dest = target_root / rel
        shown = str(Path("deploy") / rel)
        if dest.exists() or dest.is_symlink():
            result.skipped.append(shown)
            if is_template:
                result.kept_settings = True
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        if is_template:
            dest.write_text(
                _fill(src.read_text(encoding="utf-8"), values, rel.name),
                encoding="utf-8",
            )
        else:
            shutil.copyfile(src, dest)
        if rel.name in _EXECUTABLES:
            mode = os.stat(dest).st_mode
            os.chmod(dest, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        result.written.append(shown)
    return result

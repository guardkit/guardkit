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

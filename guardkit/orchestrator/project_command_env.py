"""The environment a project's own command runs with, built from nothing.

13 October 2026. Design: ``docs/designs/factory-merge-install-and-honest-baseline-2026-10-13.md``
item 2a (ai-transition), with the one addition accepted for
``factory-project-commands-without-factory-credentials-2026-10-13.md``.

GuardKit's own process holds the factory's credentials (Forge hands it
``GUARDKIT_NATS_PASSWORD``, ``FLEET_MEMORY_PG_DSN``, ``OPENAI_API_KEY`` and
others). A project's install or test command is the build's code: honest but
fallible, and it has no business seeing any of them. So the environment such a
command runs with is not a copy of GuardKit's with things removed; it is built
from an empty dictionary, and it holds exactly:

* ``PATH`` from GuardKit's own environment, with ``path_first`` in front;
* ``HOME`` and ``TMPDIR`` set to private folders
  ``<scratch>/toolchain/HOME`` and ``<scratch>/toolchain/TMPDIR``, where
  ``<scratch>`` is the work folder's scratch folder in its git directory
  (``paths.prepare_builder_scratch_dir``), outside the project;
* ``LANG``, ``LC_ALL`` and ``LC_*``, when set;
* ``HTTP_PROXY``, ``HTTPS_PROXY``, ``NO_PROXY`` and ``ALL_PROXY``, upper and
  lower case, when set and when the value carries no ``user:password@`` part
  (a value that does refuses the command; the value is never quoted);
* the project's declared ``launch.settings`` names, when set;
* the project's declared ``launch.scratch`` folders;
* ``named``: values the factory itself sets for this one command. A
  credential-shaped name there, or ``GUARDKIT_RUN_OWNER``, is a programming
  error and raises;
* last, ``GUARDKIT_RUN_OWNER`` exactly as GuardKit's own environment has it:
  set when the parent has it, absent when it does not, whatever the caller
  or the project's declarations added. It is a build id, not a secret:
  Forge's stop sweep finds a cancelled build's leftover processes by reading
  it from ``/proc/<pid>/environ``, so only the authoritative parent value
  may ever reach a project command.

Nothing else. Anything else a project needs, it declares in
``launch.settings``. Nothing here names a stack.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Mapping, Optional, Sequence, Tuple

from guardkit.orchestrator.launch_declaration import (
    DECLARED_NAME_PATTERN,
    RESERVED_CREDENTIAL_WORDS,
    SCRATCH_SUBDIR,
    LaunchDeclaration,
    LaunchEnvironmentError,
    _private_directory,
    apply_launch_environment,
)

__all__ = [
    "PROXY_NAMES",
    "RUN_OWNER_NAME",
    "project_command_environment",
]

#: The marker Forge's stop sweep reads; passed through when GuardKit has it.
RUN_OWNER_NAME = "GUARDKIT_RUN_OWNER"

PROXY_NAMES: Tuple[str, ...] = tuple(
    name
    for base in ("HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "ALL_PROXY")
    for name in (base, base.lower())
)


def _named_refusal(name: object) -> Optional[str]:
    """Why a factory-set name may not be passed, or ``None``."""
    if not isinstance(name, str) or not DECLARED_NAME_PATTERN.fullmatch(name):
        return f"{name!r} is not the shape of a setting name"
    upper = name.upper()
    if upper == RUN_OWNER_NAME:
        return (
            f"{name!r} comes only from GuardKit's own environment, never from "
            f"a caller"
        )
    for word in RESERVED_CREDENTIAL_WORDS:
        if word in upper:
            return f"{name!r} is credential-shaped (it contains {word!r})"
    return None


def project_command_environment(
    work_folder: Path,
    declaration: Optional[LaunchDeclaration],
    *,
    named: Mapping[str, str] = {},  # noqa: B006 - read only, never mutated
    path_first: Sequence[str] = (),
) -> Dict[str, str]:
    """The whole environment for one project command run in ``work_folder``.

    Raises
    ------
    LaunchEnvironmentError
        When no scratch folder can be made for ``work_folder``, a proxy
        setting carries a user name or password, or the declared launch
        folders cannot be prepared. It is an ``OSError``, so a caller that
        already treats "the command could not start" as the command's failure
        treats this the same way, with this plain sentence. No sentence
        quotes a setting's value.
    ValueError
        When ``named`` holds a credential-shaped or malformed name: that is
        a programming error in the caller, not a project problem.
    """
    for name in named:
        refusal = _named_refusal(name)
        if refusal is not None:
            raise ValueError(
                f"a factory-set value for a project command was refused: {refusal}"
            )

    source = os.environ
    env: Dict[str, str] = {}
    path_parts = [str(p) for p in path_first if str(p)]
    if "PATH" in source:
        path_parts.append(source["PATH"])
    if path_parts:
        env["PATH"] = os.pathsep.join(path_parts)
    for name, value in source.items():
        if name in ("LANG", "LC_ALL") or name.startswith("LC_"):
            env[name] = value
    for name in PROXY_NAMES:
        value = source.get(name)
        if value is None:
            continue
        if "@" in value:
            raise LaunchEnvironmentError(
                f"the proxy setting {name} carries a user name or password, so "
                f"it is not passed to the project's commands and they were "
                f"not run"
            )
        env[name] = value

    from guardkit.orchestrator.paths import prepare_builder_scratch_dir

    scratch = prepare_builder_scratch_dir(Path(work_folder))
    if scratch is None:
        raise LaunchEnvironmentError(
            f"the work folder {work_folder} has no usable scratch folder for "
            f"the project's private HOME and TMPDIR, so its commands were not run"
        )
    base = _private_directory(scratch / SCRATCH_SUBDIR)
    env["HOME"] = str(_private_directory(base / "HOME"))
    env["TMPDIR"] = str(_private_directory(base / "TMPDIR"))
    # An explicit base dict: the declared settings are copied when set, the
    # scratch names are pointed at folders, and nothing else of this
    # process's environment is added (the copy-everything branch is only
    # taken for ``env=None``).
    result = apply_launch_environment(env, declaration, Path(work_folder))
    final = dict(result if result is not None else env)
    final.update({name: str(value) for name, value in named.items()})
    # Applied last, from the parent only: set when the parent has it, absent
    # when it does not, whatever was added above.
    for name in [key for key in final if key.upper() == RUN_OWNER_NAME]:
        del final[name]
    owner = source.get(RUN_OWNER_NAME)
    if owner is not None:
        final[RUN_OWNER_NAME] = owner
    return final

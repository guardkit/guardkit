"""The environment a project's own command runs with, built from nothing.

13 October 2026. Written for the merge's install and check (the merge design's
item 2a), and shaped so that every place GuardKit runs a project command can
share it.

GuardKit's own process holds the factory's credentials (Forge hands it
``GUARDKIT_NATS_PASSWORD``, ``FLEET_MEMORY_PG_DSN``, ``OPENAI_API_KEY`` and
others). A project's install or test command is the build's code: honest but
fallible, and it has no business seeing any of them. So the environment such a
command runs with is not a copy of GuardKit's with things removed; it is built
from an empty dictionary, in five steps, each working on the one before:

1. **The base:** ``PATH`` from GuardKit's own environment with ``path_first``
   in front; ``HOME`` and ``TMPDIR`` set to private folders
   ``<scratch>/toolchain/HOME`` and ``<scratch>/toolchain/TMPDIR`` in the work
   folder's scratch folder (``paths.prepare_builder_scratch_dir``, outside
   the project); ``LANG``, ``LC_ALL`` and ``LC_*`` when set; ``HTTP_PROXY``,
   ``HTTPS_PROXY``, ``NO_PROXY`` and ``ALL_PROXY`` in upper and lower case
   when set; the declared ``launch.settings`` names when set; and the
   declared ``launch.scratch`` folders.
2. **Additions:** values the factory itself sets for this one command. A
   credential-shaped name, or ``GUARDKIT_RUN_OWNER``, is a programming error
   and raises ``ValueError``.
3. **Overlay:** values the project wrote in its own files. A name the
   project could not declare (``declared_setting_refusal``: reserved
   prefixes such as ``GUARDKIT_``, the factory's own names, credential-shaped
   names), a ``launch.scratch`` name, or a name an addition set is refused
   with ``LaunchEnvironmentError``.
4. **The proxy check, on everything composed so far:** a proxy setting (any
   case of ``HTTP_PROXY``, ``HTTPS_PROXY``, ``ALL_PROXY``, ``FTP_PROXY`` or
   ``NO_PROXY``) that carries a user name or password refuses the command,
   whether it was copied by default, declared, added or overlaid. The
   sentence names the setting and never its value.
5. **The run-owner marker, last:** ``GUARDKIT_RUN_OWNER`` is set from
   GuardKit's own environment when it has one and removed when it does not.
   It is a build id, not a secret: Forge's stop sweep finds a cancelled
   build's leftover processes by reading it from ``/proc/<pid>/environ``, so
   only the authoritative parent value may reach a project command.

Steps 2 to 5 are :func:`finish_project_environment`, for a caller that builds
its own base. Nothing else is passed. Anything else a project needs, it
declares in ``launch.settings``. Nothing here names a stack.
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
    declared_setting_refusal,
)

__all__ = [
    "PROXY_NAMES",
    "RUN_OWNER_NAME",
    "finish_project_environment",
    "project_command_environment",
]

#: The marker Forge's stop sweep reads; only ever taken from the parent.
RUN_OWNER_NAME = "GUARDKIT_RUN_OWNER"

#: Proxy settings copied into the base when set (step 1).
PROXY_NAMES: Tuple[str, ...] = tuple(
    name
    for base in ("HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "ALL_PROXY")
    for name in (base, base.lower())
)

#: Proxy settings checked for credentials on the composed environment (step 4).
_CHECKED_PROXY_NAMES = frozenset(
    {"HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "FTP_PROXY", "NO_PROXY"}
)


def _addition_refusal(name: object) -> Optional[str]:
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


def finish_project_environment(
    env: Dict[str, str],
    *,
    additions: Mapping[str, str] = {},  # noqa: B006 - read only, never mutated
    overlay: Mapping[str, str] = {},  # noqa: B006 - read only, never mutated
    scratch_names: Sequence[str] = (),
) -> Dict[str, str]:
    """Steps 2 to 5 on a base the caller built: additions, overlay, the proxy
    check, and the run-owner marker last.

    ``scratch_names`` are the declared ``launch.scratch`` names, which an
    overlay may not replace.

    Raises ``ValueError`` for a refused addition (a programming error) and
    :class:`LaunchEnvironmentError` for a refused overlay or a proxy that
    carries credentials. No sentence quotes a setting's value.
    """
    for name in additions:
        refusal = _addition_refusal(name)
        if refusal is not None:
            raise ValueError(
                f"a factory-set value for a project command was refused: {refusal}"
            )
    result = dict(env)
    result.update({name: str(value) for name, value in additions.items()})

    scratch = {str(name) for name in scratch_names}
    for name in overlay:
        refusal = declared_setting_refusal(name)
        if refusal is None and name in scratch:
            refusal = f"{name!r} is one of the project's declared scratch folders"
        if refusal is None and name in additions:
            refusal = f"{name!r} is set by the factory for this command"
        if refusal is not None:
            raise LaunchEnvironmentError(
                f"a setting the project wrote for this command was refused, so "
                f"the command was not run: {refusal}"
            )
    result.update({name: str(value) for name, value in overlay.items()})

    carrying = sorted(
        name
        for name, value in result.items()
        if name.upper() in _CHECKED_PROXY_NAMES and "@" in str(value)
    )
    if carrying:
        raise LaunchEnvironmentError(
            f"the proxy setting {', '.join(carrying)} carries a user name or "
            f"password, so it is not passed to the project's commands and they "
            f"were not run"
        )

    for name in [key for key in result if key.upper() == RUN_OWNER_NAME]:
        del result[name]
    owner = os.environ.get(RUN_OWNER_NAME)
    if owner is not None:
        result[RUN_OWNER_NAME] = owner
    return result


def project_command_environment(
    work_folder: Path,
    declaration: Optional[LaunchDeclaration],
    *,
    additions: Mapping[str, str] = {},  # noqa: B006 - read only, never mutated
    overlay: Mapping[str, str] = {},  # noqa: B006 - read only, never mutated
    path_first: Sequence[str] = (),
) -> Dict[str, str]:
    """The whole environment for one project command run in ``work_folder``.

    Raises
    ------
    LaunchEnvironmentError
        When no scratch folder can be made for ``work_folder``, the declared
        launch folders cannot be prepared, an overlay name is refused, or a
        proxy setting carries a user name or password. It is an ``OSError``,
        so a caller that already treats "the command could not start" as the
        command's failure treats this the same way, with this plain sentence.
    ValueError
        When ``additions`` holds a refused name: a programming error in the
        caller, not a project problem.
    """
    for name in additions:
        refusal = _addition_refusal(name)
        if refusal is not None:
            raise ValueError(
                f"a factory-set value for a project command was refused: {refusal}"
            )

    # Step 1: the base, from an empty dictionary.
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
        if value is not None:
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
    composed = dict(result if result is not None else env)

    # Steps 2 to 5.
    return finish_project_environment(
        composed,
        additions=additions,
        overlay=overlay,
        scratch_names=declaration.scratch if declaration is not None else (),
    )

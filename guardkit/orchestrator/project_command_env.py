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
   in front; ``HOME`` set to the private folder ``<scratch>/toolchain/HOME``
   in the work folder's scratch folder (``paths.prepare_builder_scratch_dir``,
   outside the project); ``TMPDIR`` set to a short private folder
   ``/tmp/gk-<8 hex>``, one per work folder (:func:`short_tmpdir_path`, 1
   November 2026: a tool that opens a Unix socket there, such as ``dotnet
   test``'s named pipe, needs the whole socket path under 103 bytes, and the
   scratch folder's path is too long for that); ``LANG``, ``LC_ALL`` and ``LC_*`` when set; ``HTTP_PROXY``,
   ``HTTPS_PROXY``, ``NO_PROXY`` and ``ALL_PROXY`` in upper and lower case
   when set; the declared ``launch.settings`` names when set; the
   declared ``launch.scratch`` folders; and ``CI=true`` unless a declared
   setting already set ``CI`` (19 October 2026).
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

Every place GuardKit runs a project's command builds its environment here
(design ``factory-project-commands-without-factory-credentials-2026-10-13``).
``test_every_process_launch_is_accounted_for`` in
``tests/orchestrator/test_project_commands_without_factory_credentials.py``
fails on any process launch in the package that neither uses this module nor
is one of the factory's own programs.

What the project is told (names only, never values):
:func:`declared_settings_not_set` and :func:`declared_not_set_sentence` for a
declared setting that is not set where the factory runs, and
:func:`minimal_environment_note` for a failed command.
"""

from __future__ import annotations

import logging
import os
import stat
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from guardkit.orchestrator.launch_declaration import (
    DECLARED_NAME_PATTERN,
    RESERVED_CREDENTIAL_WORDS,
    SCRATCH_SUBDIR,
    LaunchDeclaration,
    LaunchEnvironmentError,
    _private_directory,
    apply_launch_environment,
    declared_setting_refusal,
    load_launch_declaration,
    main_checkout_root,
)

__all__ = [
    "PROXY_NAMES",
    "RUN_OWNER_NAME",
    "declared_not_set_sentence",
    "declared_settings_not_set",
    "finish_project_environment",
    "main_checkout_environment",
    "minimal_environment_note",
    "missing_program",
    "project_command_environment",
    "remove_short_tmpdir",
    "short_tmpdir_path",
    "withheld_settings",
]

logger = logging.getLogger(__name__)

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


def _scratch_folder(work_folder: Path) -> Optional[Path]:
    """The work folder's scratch folder (outside the project), or ``None``.

    ``paths.prepare_builder_scratch_dir``: inside the work folder's own git
    directory. ``None`` when the work folder is not a git checkout, and the
    command then does not run. (One function so the test suite's plain
    temporary folders, which are not git checkouts, can be given one.)
    """
    from guardkit.orchestrator.paths import prepare_builder_scratch_dir

    return prepare_builder_scratch_dir(work_folder)


#: Where the short per-work-folder ``TMPDIR`` folders live. Fixed and short
#: on purpose: ``TMPDIR`` + "/" + a 32-character socket name must stay within
#: .NET's 103-byte limit wherever the repository lives.
SHORT_TMP_ROOT = "/tmp"


def short_tmpdir_path(scratch: Path) -> Path:
    """The short private ``TMPDIR`` for the work folder whose scratch folder
    is ``scratch``: ``/tmp/gk-<first 8 hex of the scratch path's SHA-256>``.

    One per worktree (each has its own scratch folder) and the same on every
    call, so it is found again to be removed (:func:`remove_short_tmpdir`).
    """
    import hashlib

    digest = hashlib.sha256(str(Path(scratch)).encode("utf-8", "surrogateescape"))
    return Path(SHORT_TMP_ROOT) / f"gk-{digest.hexdigest()[:8]}"


def _short_private_tmpdir(directory: Path) -> Path:
    """Create ``directory`` (mode 0700) or reuse it, only when it is a real
    folder this user owns; then make it 0700. It sits in a folder every user
    can write to, so a name someone else made first (or a symbolic link) is
    refused, never followed."""
    try:
        try:
            directory.mkdir(mode=0o700)
        except FileExistsError:
            pass
        info = directory.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
            raise LaunchEnvironmentError(
                f"the private temporary folder {directory} is not a folder "
                f"this user owns, so the project's commands were not run"
            )
        if stat.S_IMODE(info.st_mode) != 0o700:
            directory.chmod(0o700)
    except LaunchEnvironmentError:
        raise
    except OSError as exc:
        raise LaunchEnvironmentError(
            f"the private temporary folder could not be created at {directory}: {exc}"
        ) from exc
    return directory


def remove_short_tmpdir(work_folder: Path) -> None:
    """Remove the work folder's short ``TMPDIR`` folder, as ``git worktree
    remove`` removes its scratch folder. Never raises."""
    import shutil

    from guardkit.orchestrator.paths import builder_scratch_dir

    try:
        scratch = builder_scratch_dir(Path(work_folder))
        if scratch is None:
            return
        target = short_tmpdir_path(Path(os.path.realpath(scratch)))
        info = target.lstat()
    except OSError:
        return
    if stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid():
        shutil.rmtree(target, ignore_errors=True)


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
            f"could not run: the proxy setting {', '.join(carrying)} carries a "
            f"user name and password, and the factory does not pass credentials "
            f"to project commands"
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

    scratch = _scratch_folder(Path(work_folder))
    if scratch is None:
        raise LaunchEnvironmentError(
            f"the work folder {work_folder} has no usable scratch folder for "
            f"the project's private HOME and TMPDIR, so its commands were not run"
        )
    base = _private_directory(scratch / SCRATCH_SUBDIR)
    env["HOME"] = str(_private_directory(base / "HOME"))
    env["TMPDIR"] = str(_short_private_tmpdir(short_tmpdir_path(scratch)))
    # An explicit base dict: the declared settings are copied when set, the
    # scratch names are pointed at folders, and nothing else of this
    # process's environment is added (the copy-everything branch is only
    # taken for ``env=None``).
    result = apply_launch_environment(env, declaration, Path(work_folder))
    composed = dict(result if result is not None else env)
    # 19 October 2026 (a factory build): the common "no one is at the
    # keyboard" signal, so a tool that would wait for a person or keep
    # watching for changes runs once and finishes. After the declared
    # settings, so a project that declares ``CI`` (set where the factory
    # runs) keeps its own value; an overlay may still set it (step 3).
    composed.setdefault("CI", "true")
    _say_declared_not_set(declaration)

    # Steps 2 to 5.
    return finish_project_environment(
        composed,
        additions=additions,
        overlay=overlay,
        scratch_names=declaration.scratch if declaration is not None else (),
    )



def main_checkout_environment(
    work_folder: Path,
    *,
    additions: Mapping[str, str] = {},  # noqa: B006 - read only, never mutated
    path_first: Sequence[str] = (),
) -> Dict[str, str]:
    """:func:`project_command_environment` with the main checkout's block.

    For a site that holds no declaration of its own: the ``launch:`` block is
    read from the checkout ``work_folder`` was cut from
    (``launch_declaration.main_checkout_root``), never from the worktree the
    builder edits. The same policy, not a second one. Raises as
    :func:`project_command_environment` does, and
    ``LaunchDeclarationError`` (also a ``LaunchEnvironmentError``) for a
    malformed block.
    """
    return project_command_environment(
        Path(work_folder),
        load_launch_declaration(main_checkout_root(Path(work_folder))),
        additions=additions,
        path_first=path_first,
    )

# =========================================================================
# What the project is told: names only, never values (design section 4)
# =========================================================================

#: Shell bookkeeping a person never means to pass; left out of the list a
#: failed command offers, so the names that matter are not buried.
_SHELL_BOOKKEEPING = frozenset({"_", "PWD", "OLDPWD", "SHLVL"})

#: Declared names already reported as not set, so a long build says it once.
_ALREADY_SAID: set = set()


def declared_settings_not_set(
    declaration: Optional[LaunchDeclaration],
) -> List[str]:
    """The ``launch.settings`` names that are not set where the factory runs."""
    if declaration is None:
        return []
    return [name for name in declaration.settings if name not in os.environ]


def declared_not_set_sentence(name: str) -> str:
    """The plain sentence for one declared setting that is not set."""
    return (
        f"the project declares `{name}` in `launch.settings`, but it is not set "
        f"where the factory runs, so the command ran without it"
    )


def _say_declared_not_set(declaration: Optional[LaunchDeclaration]) -> None:
    for name in declared_settings_not_set(declaration):
        if name in _ALREADY_SAID:
            continue
        _ALREADY_SAID.add(name)
        logger.warning(declared_not_set_sentence(name))


def withheld_settings(env: Mapping[str, str]) -> Tuple[List[str], int]:
    """Settings GuardKit holds that a command with ``env`` did not get.

    Returns the names a project is allowed to declare (they pass
    ``declared_setting_refusal``), sorted, and how many of the factory's own
    reserved names were also held back. Those are counted, never named as
    something to declare. Values are never read out.
    """
    offerable: List[str] = []
    own = 0
    for name in os.environ:
        if name in env or name in _SHELL_BOOKKEEPING:
            continue
        if declared_setting_refusal(name) is None:
            offerable.append(name)
        else:
            own += 1
    return sorted(offerable), own


def minimal_environment_note(env: Optional[Mapping[str, str]]) -> str:
    """The sentence added to a failed project command's detail.

    Empty when ``env`` is ``None`` (the command never had an environment).
    Names only: no value of any setting appears in it.
    """
    if env is None:
        return ""
    offerable, own = withheld_settings(env)
    listed = ", ".join(f"`{name}`" for name in offerable)
    held = (
        f"Settings the factory holds that were not given to it: {listed}."
        if offerable
        else "The factory holds no other setting a project could declare."
    )
    if own:
        held += (
            f" ({own} of the factory's own settings were also held back; a "
            f"project cannot declare those.)"
        )
    return (
        "This command ran with the factory's minimal environment. "
        + held
        + " If the command needs one, add its name to `launch.settings` in "
        "`.guardkit/config.yaml`."
    )


#: Words the shell itself understands: never looked up as a program.
_SHELL_WORDS = frozenset(
    "! { } ( ) [ [[ . : alias bg break builtin cd command continue declare "
    "eval exec exit export false fg for function getopts hash if jobs let "
    "local printf pwd read readonly return set shift source test time "
    "times trap true type typeset ulimit umask unalias unset until wait "
    "while case echo".split()
)


def missing_program(
    command: str, folder: Path, env: Mapping[str, str]
) -> Optional[str]:
    """Why ``command``'s own program cannot be found, or ``None``.

    The first word of the declared command, after any leading ``NAME=value``
    settings, is looked up the way the shell would: a word with a ``/`` in
    the part's ``folder``, a bare name on ``env``'s ``PATH``. A word the
    shell understands itself (``cd``, ``export``, ``(``) is never looked up,
    and text that cannot be split into words is left to the shell
    (1 November 2026). A missing program here means the check could not run;
    a program missing inside a script that did start is the script failing.
    """
    import re
    import shlex
    import shutil

    try:
        words = shlex.split(command, posix=True)
    except ValueError:
        return None
    while words and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", words[0], re.S):
        words.pop(0)
    if not words:
        return None
    program = words[0]
    if program in _SHELL_WORDS or any(c in program for c in "$`;&|<>*?(){}"):
        return None
    if "/" in program:
        target = Path(program)
        if not target.is_absolute():
            target = Path(folder) / target
        if not target.is_file():
            return f"its program `{program}` does not exist in {folder}"
        if not os.access(target, os.X_OK):
            return f"its program `{program}` in {folder} is not executable"
        return None
    if shutil.which(program, path=env.get("PATH", "")) is None:
        return f"its program `{program}` is not on the command's PATH"
    return None

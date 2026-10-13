"""What the merge runs its install and its checks with (13 October 2026).

A factory build was joined in a working folder with nothing installed: the
merge never ran the project's declared install, never applied its
declared launch settings, and handed the project's commands every setting
GuardKit itself had, factory credentials included. This module holds the
three pieces the merge now pins on the TARGET branch, before anything lands
(rule 11: the branch being judged cannot choose what judges it):

* :func:`read_merge_declarations` reads ``.guardkit/config.yaml`` once and
  FAILS CLOSED. A missing file, an empty file, or a missing ``toolchain:`` or
  ``launch:`` key means "not declared", exactly as before. Anything else that
  is wrong (an unreadable file, broken YAML, a top level that is not a
  mapping, a block the schema refuses) is a reason the checks cannot run;
  nothing falls back to a stack default.
* :func:`judge_words` and :func:`judge_files` are the judge-file rule. The
  merge accepts only plain command text it can follow completely: a short
  list of ordinary characters, split the way the shell (for the test command)
  or GuardKit (for the install) splits it, where every word is a plain word.
  A file the build changed that one of those words names is a judge file, and
  a build that changed a judge file gets no automatic verdict.

The environment the install and the check run with is built from nothing by
``project_command_env.project_command_environment`` (design item 2a), the one
helper every project command is meant to share.

Nothing here names a stack. The install, the test command, the settings and
the scratch names are whatever the project declares, carried as plain text.
"""

from __future__ import annotations

import re
import shlex
import string
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional, Sequence, Tuple

import yaml

from guardkit.orchestrator.launch_declaration import (
    LAUNCH_KEY,
    LaunchDeclaration,
    parse_launch_block,
)
from guardkit.orchestrator.toolchain_declaration import (
    CONFIG_RELATIVE_PATH,
    TOOLCHAIN_KEY,
    ToolchainDeclaration,
    parse_toolchain_block,
)

__all__ = [
    "CANNOT_FOLLOW",
    "JUDGE_FILES_CHANGED",
    "MergeDeclarations",
    "MergeEnvironment",
    "judge_files",
    "judge_words",
    "pin_merge_environment",
    "read_merge_declarations",
]


# ---------------------------------------------------------------------------
# Reading the declarations, fail-closed (design item 1a)
# ---------------------------------------------------------------------------

_CONFIG_NAME = CONFIG_RELATIVE_PATH.as_posix()


@dataclass(frozen=True)
class MergeDeclarations:
    """The two blocks the merge uses, read once from the target branch.

    Either may be ``None``, meaning "not declared".
    """

    toolchain: Optional[ToolchainDeclaration] = None
    launch: Optional[LaunchDeclaration] = None

    @property
    def declared_test(self) -> Optional[str]:
        if self.toolchain is None:
            return None
        return (self.toolchain.test or "").strip() or None


def _why(exc: BaseException) -> str:
    """A short, one-line reason from a parse error."""
    cause = exc.__cause__
    errors = getattr(cause, "errors", None)
    if callable(errors):
        try:
            parts = []
            for error in errors():
                where = ".".join(str(p) for p in error.get("loc", ())) or "block"
                parts.append(f"{where}: {error.get('msg')}")
            if parts:
                return "; ".join(parts[:5])
        except Exception:  # noqa: BLE001 - fall back to the plain message
            pass
    first = str(exc).strip().splitlines()
    return first[0] if first else type(exc).__name__


def read_merge_declarations(
    tree_root: Path,
) -> Tuple[Optional[MergeDeclarations], Optional[str]]:
    """Read ``toolchain:`` and ``launch:`` from ``tree_root`` once, fail-closed.

    A key that is missing means "not declared". A key that is present is
    validated, even when its value is empty.

    Returns ``(declarations, problem)``. ``problem`` is a plain sentence when
    the file or a block is invalid; ``declarations`` is then ``None`` and the
    caller runs nothing and looks for no other command.
    """
    path = Path(tree_root) / CONFIG_RELATIVE_PATH
    try:
        text = path.read_text(encoding="utf-8")
    except (FileNotFoundError, NotADirectoryError):
        return MergeDeclarations(), None
    except (OSError, UnicodeDecodeError) as exc:
        return None, (
            f"{_CONFIG_NAME} could not be read ({type(exc).__name__}), so the "
            f"declared commands cannot be trusted"
        )
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        return None, f"{_CONFIG_NAME} is not valid YAML ({_why(exc)})"
    if data is None:
        return MergeDeclarations(), None
    if not isinstance(data, dict):
        return None, (
            f"{_CONFIG_NAME} must be a mapping at the top level (it reads as "
            f"{type(data).__name__})"
        )

    # A key that is present is validated even when its value is empty: a
    # bare ``toolchain:`` or ``launch: null`` is a mistake in the file, not a
    # declaration that is absent, and must never fall back to a stack default.
    toolchain: Optional[ToolchainDeclaration] = None
    if TOOLCHAIN_KEY in data:
        raw_toolchain: Any = data[TOOLCHAIN_KEY]
        try:
            toolchain = parse_toolchain_block(raw_toolchain)
        except ValueError as exc:
            return None, (
                f"the `toolchain:` block in {_CONFIG_NAME} cannot be used "
                f"({_why(exc)})"
            )
        if toolchain.is_empty:
            toolchain = None

    launch: Optional[LaunchDeclaration] = None
    if LAUNCH_KEY in data:
        raw_launch: Any = data[LAUNCH_KEY]
        try:
            if raw_launch is None:
                # ``parse_launch_block`` reads None as "declares nothing";
                # here a present key must be a mapping.
                raise ValueError("`launch:` is present but empty")
            launch = parse_launch_block(raw_launch)
        except ValueError as exc:
            return None, (
                f"the `launch:` block in {_CONFIG_NAME} cannot be used "
                f"({_why(exc)})"
            )
        if launch.is_empty:
            launch = None

    return MergeDeclarations(toolchain=toolchain, launch=launch), None


# ---------------------------------------------------------------------------
# The judge-file rule (design item 2b, final form after review round 6)
# ---------------------------------------------------------------------------

CANNOT_FOLLOW = (
    "could not verify — the check command uses shell syntax the factory "
    "cannot follow; put it in a script and name the script"
)
JUDGE_FILES_CHANGED = "could not verify — the build changed the commands that judge it"

_ALLOWED_CHARACTERS = frozenset(
    string.ascii_letters + string.digits + " \t\n" + "_./=:@%+,-'\"\\&|;()<>"
)
_PLAIN_WORD = re.compile(r"[A-Za-z0-9_./=:@%+,-]+")
_OPERATOR_WORD = re.compile(r"[&|;()<>]+")


def judge_words(
    command: str, *, through_shell: bool
) -> Tuple[Optional[Tuple[str, ...]], Optional[str]]:
    """The plain words of a pinned command, or the reason it is refused.

    ``through_shell`` is True for the test command, which runs through a
    shell: it is split the way the shell splits it (quotes and escapes
    applied, ``&& ; | ( ) < >`` split off) and bare operator words are
    dropped. The install runs without a shell, so its words are exactly the
    argument list ``shlex.split`` gives, as the builder's own install builds.

    Returns ``(words, None)`` or ``(None, CANNOT_FOLLOW)``. Decided from the
    text alone: a character outside the short allowed list, a split that
    fails, or any word that is not a plain word refuses it.
    """
    if any(ch not in _ALLOWED_CHARACTERS for ch in command):
        return None, CANNOT_FOLLOW
    try:
        if through_shell:
            lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
            lexer.whitespace_split = True
            lexer.commenters = ""
            words = list(lexer)
        else:
            words = shlex.split(command)
    except ValueError:
        return None, CANNOT_FOLLOW
    plain: List[str] = []
    for word in words:
        if through_shell and _OPERATOR_WORD.fullmatch(word):
            continue
        if not _PLAIN_WORD.fullmatch(word):
            return None, CANNOT_FOLLOW
        plain.append(word)
    return tuple(plain), None


_PIECE_SEPARATORS = re.compile(r"[,:]")


def _match_keys(word: str) -> List[str]:
    """The word as it stands, the part after its first ``=``, and the pieces
    of both split on ``,`` and ``:`` (so ``--opt=a,check.sh`` and
    ``--opt=a:check.sh`` name ``check.sh``).

    A leading ``./`` is dropped from each.
    """
    whole = [word]
    if "=" in word:
        whole.append(word.split("=", 1)[1])
    keys = list(whole)
    for key in whole:
        if _PIECE_SEPARATORS.search(key):
            keys.extend(piece for piece in _PIECE_SEPARATORS.split(key) if piece)
    result: List[str] = []
    for key in keys:
        while key.startswith("./"):
            key = key[2:]
        if key:
            result.append(key)
    return result


def judge_files(changed: Sequence[str], words: Sequence[str]) -> List[str]:
    """The changed files that a pinned command's words name directly.

    A file is a judge file when any word (or its part after the first ``=``,
    or a piece of either split on ``,`` and ``:``) equals its repository path, ends with ``/`` and its path, equals its file
    name, or ends with ``/`` and its file name. A named directory does not
    make the files under it judge files.
    """
    keys = {key for word in words for key in _match_keys(word)}
    hits: List[str] = []
    for path in changed:
        name = path.rsplit("/", 1)[-1]
        for key in keys:
            if (
                key == path
                or key.endswith("/" + path)
                or key == name
                or key.endswith("/" + name)
            ):
                hits.append(path)
                break
    return hits


# ---------------------------------------------------------------------------
# The pinned value (design item 1)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MergeEnvironment:
    """The install and launch block pinned on the target, with the test command.

    ``install_argv`` is empty when no install is declared. ``install_timeout``
    is already capped at the merge's own check time limit.
    ``ran_marker_regex`` is the target's repository-root marker, when it
    declares one: a passing check must print it to count as a measurement.
    """

    install_argv: Tuple[str, ...] = ()
    install_text: str = ""
    install_timeout: int = 0
    launch: Optional[LaunchDeclaration] = None
    ran_marker_regex: Optional[str] = None
    # The plain words of the pinned test command and install, for the
    # judge-file comparison.
    judge_words: Tuple[str, ...] = ()


def pin_merge_environment(
    declarations: MergeDeclarations,
    test_command: Optional[str],
    verify_timeout: int,
) -> Tuple[Optional[MergeEnvironment], Optional[str]]:
    """Pin what the merge will run, or say why nothing can run.

    Applies the judge-file text rule to the resolved test command and the
    declared install before anything else.
    """
    words: List[str] = []
    if test_command:
        test_words, refusal = judge_words(test_command, through_shell=True)
        if refusal is not None:
            return None, refusal
        words.extend(test_words or ())

    toolchain = declarations.toolchain
    install_text = (toolchain.install or "") if toolchain is not None else ""
    install_argv: Tuple[str, ...] = ()
    install_timeout = 0
    if install_text:
        install_words, refusal = judge_words(install_text, through_shell=False)
        if refusal is not None:
            return None, refusal
        install_argv = tuple(install_words or ())
        if not install_argv:
            return None, (
                f"the declared install (`{install_text}`) does not split into "
                f"a command"
            )
        words.extend(install_argv)
        install_timeout = max(1, min(toolchain.install_timeout, verify_timeout))

    return (
        MergeEnvironment(
            install_argv=install_argv,
            install_text=install_text,
            install_timeout=install_timeout,
            launch=declarations.launch,
            ran_marker_regex=(
                toolchain.ran_marker_regex if toolchain is not None else None
            ),
            judge_words=tuple(words),
        ),
        None,
    )

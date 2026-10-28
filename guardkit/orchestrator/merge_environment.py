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
  pinned command text is split the way the shell (for the test command) or
  GuardKit (for the install) splits it, and its plain words are kept. A file
  one of those words names is a judge file. Since 15 October 2026 the merge
  checks the join with the TARGET's copy of every judge file (the build's
  copy is never run); which ones it changed is kept for the card and the
  receipt. Since the cull of 27 October 2026 no command text is refused: a
  word that is not plain, or text that cannot be split, simply names no
  judge file.
* :func:`judge_links` is the link rule: a judge file, or a folder on its
  path, that is a symbolic link in a tree the merge reads means no verdict,
  because putting the target's copy back would put back the link and not the
  program it points to.

The environment the install and the check run with is built from nothing by
``project_command_env.project_command_environment`` (design item 2a), the one
helper every project command is meant to share.

Nothing here names a stack. The install, the test command, the settings and
the scratch names are whatever the project declares, carried as plain text.
"""

from __future__ import annotations

import os
import posixpath
import re
import shlex
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import yaml

from guardkit.lib.project_git import run_git

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
    "JUDGE_FILES_CHANGED",
    "JUDGE_IS_A_LINK",
    "MergeDeclarations",
    "MergeEnvironment",
    "judge_files",
    "judge_links",
    "judge_words",
    "judges_kept_from_target",
    "links_on_judge_paths",
    "shown_path",
    "tree_entries",
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
    # ``autobuild.player.protected_paths``, read by the builder's own parser
    # (28 October 2026): the judge files under them are the ones the merge
    # checks with the target's copy (:func:`judges_kept_from_target`).
    protected_paths: Tuple[str, ...] = ()

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

    A key that is missing, or a file with no content but comments, means
    "not declared". A key that is present is validated, even when its value
    is empty, and a whole document that is an explicit null is invalid.

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
        # An empty document (nothing, or only comments and blank lines)
        # declares nothing. A document that is an explicit null (``null``,
        # ``~``) is a file someone wrote wrongly, and must not fall back to
        # a stack default.
        try:
            node = yaml.compose(text, Loader=yaml.SafeLoader)
        except yaml.YAMLError as exc:  # pragma: no cover - safe_load passed
            return None, f"{_CONFIG_NAME} is not valid YAML ({_why(exc)})"
        if node is None:
            return MergeDeclarations(), None
        return None, (
            f"{_CONFIG_NAME} is an explicit null rather than a mapping of "
            f"declarations"
        )
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

    from guardkit.orchestrator.harness.selector import _parse_player_project_inputs

    try:
        player = _parse_player_project_inputs(
            text, config_path=_CONFIG_NAME, has_file=lambda _rel: False
        )
    except Exception as exc:  # the builder refuses this file too
        return None, f"the protected paths in {_CONFIG_NAME} cannot be read ({_why(exc)})"
    protected = tuple(
        posixpath.normpath(str(p)) for p in player.get("protected_paths") or ()
    )

    return (
        MergeDeclarations(toolchain=toolchain, launch=launch, protected_paths=protected),
        None,
    )


# ---------------------------------------------------------------------------
# The judge-file rule (design item 2b, final form after review round 6)
# ---------------------------------------------------------------------------

JUDGE_FILES_CHANGED = "could not verify — the build changed the commands that judge it"
JUDGE_IS_A_LINK = (
    "could not verify — {path} is a symbolic link, so the factory cannot tell "
    "which program it would run"
)

_NAMED_ESCAPES = {"\n": "\\n", "\r": "\\r", "\t": "\\t"}


def shown_path(path: str) -> str:
    """A file name as it may appear in a sentence (a reason, a detail, a
    receipt line), so the sentence stays valid UTF-8 and one line.

    A byte that is not UTF-8 (held by ``os.fsdecode`` as a lone surrogate) is
    shown as ``\\xNN``; a newline, carriage return or tab as ``\\n``,
    ``\\r`` or ``\\t``; any other control character as ``\\xNN``; a line or
    paragraph separator, an invisible format character (a right-to-left
    override, a zero-width space, a byte-order mark: Unicode category Cf),
    or any other lone surrogate, as ``\\uNNNN``. Every other character,
    ordinary non-ASCII letters included, is unchanged.
    Structured fields keep the name exactly as git gave it.
    """
    out: List[str] = []
    for ch in path:
        code = ord(ch)
        if 0xDC80 <= code <= 0xDCFF:
            out.append(f"\\x{code - 0xDC00:02x}")
        elif ch in _NAMED_ESCAPES:
            out.append(_NAMED_ESCAPES[ch])
        elif unicodedata.category(ch) == "Cc":
            out.append(f"\\x{code:02x}")
        elif unicodedata.category(ch) in ("Zl", "Zp", "Cs", "Cf"):
            out.append(f"\\u{code:04x}")
        else:
            out.append(ch)
    return "".join(out)


_PLAIN_WORD = re.compile(r"[A-Za-z0-9_./=:@%+,-]+")
_OPERATOR_WORD = re.compile(r"[&|;()<>]+")


def judge_words(
    command: str, *, through_shell: bool
) -> Tuple[Optional[Tuple[str, ...]], Optional[str]]:
    """The plain words of a pinned command.

    ``through_shell`` is True for the test command, which runs through a
    shell: it is split the way the shell splits it (quotes and escapes
    applied, ``&& ; | ( ) < >`` split off) and bare operator words are
    dropped. The install runs without a shell, so its words are exactly the
    argument list ``shlex.split`` gives, as the builder's own install builds.

    Returns ``(words, None)``: the second place is kept for callers that
    read it and is always ``None``. Text that cannot be split gives no
    words; a word that is not a plain word is left out.
    """
    try:
        if through_shell:
            lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
            lexer.whitespace_split = True
            lexer.commenters = ""
            words = list(lexer)
        else:
            words = shlex.split(command)
    except ValueError:
        return (), None
    plain: List[str] = []
    for word in words:
        if through_shell and _OPERATOR_WORD.fullmatch(word):
            continue
        if _PLAIN_WORD.fullmatch(word):
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


def judges_kept_from_target(
    paths: Sequence[str], protected_paths: Sequence[str]
) -> List[str]:
    """The judge files the merge checks with the target's copy: those at or
    under a path the project declares protected (28 October 2026).

    Every other judge file is the build's own work, and the merge runs the
    build's copy of it. Step 2's request 7 (FEAT-9107): a feature whose task
    was to add its part's checks to the root ``scripts/check.sh`` failed its
    own tests of that script, because the merge ran main's copy instead.
    """
    roots = [p.rstrip("/") for p in protected_paths if p.rstrip("/")]
    return [
        path
        for path in paths
        if any(path == root or path.startswith(root + "/") for root in roots)
    ]


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
# The link rule (15 October 2026, item 1a)
# ---------------------------------------------------------------------------

#: git's mode for a symbolic link.
LINK_MODE = "120000"


def links_on_judge_paths(
    entries: Mapping[str, str], words: Sequence[str]
) -> List[str]:
    """The entries of one tree that are symbolic links on a judge's path.

    ``entries`` maps every path in the tree to its git mode. A link is named
    when the judge-file rule (:func:`judge_files`) matches it, applied to every
    path in the tree, or when it is a leading folder of a word that names a
    path (``scripts`` for ``scripts/check.sh``).
    """
    keys = {key for word in words for key in _match_keys(word)}
    links = sorted(path for path, mode in entries.items() if mode == LINK_MODE)
    if not links:
        return []
    named = set(judge_files(links, words))
    for path in links:
        if path in named:
            continue
        if any(
            key.startswith(path + "/") or ("/" + path + "/") in key
            for key in keys
        ):
            named.add(path)
    return sorted(named)


def tree_entries(
    tree_root: Path, commit: str
) -> Optional[Dict[str, Tuple[str, str]]]:
    """Every path in ``commit``'s tree with its git mode and object id, read
    with ``git ls-tree -r -z --full-tree``; ``None`` when git cannot say."""
    done = run_git(
        ["ls-tree", "-r", "-z", "--full-tree", commit],
        cwd=str(tree_root),
        timeout=120,
        text=False,
    )
    if done.returncode != 0:
        return None
    entries: Dict[str, Tuple[str, str]] = {}
    # Names are read as bytes and decoded byte-exact (``os.fsdecode``), the
    # way the git helper passes them back to git: a name that is not valid
    # UTF-8 is still one path, never an error.
    for record in (done.stdout or b"").split(b"\0"):
        if not record:
            continue
        meta, _, path = record.partition(b"\t")
        parts = meta.split()
        if len(parts) != 3 or not path:
            return None
        entries[os.fsdecode(path)] = (os.fsdecode(parts[0]), os.fsdecode(parts[2]))
    return entries


def judge_links(
    tree_root: Path, commit: str, words: Sequence[str]
) -> Optional[List[str]]:
    """The symbolic links on a judge's path in ``commit``'s tree (see
    :func:`links_on_judge_paths`), from git's own record of the tree, not
    from the folder. ``None`` when the tree could not be read."""
    entries = tree_entries(tree_root, commit)
    if entries is None:
        return None
    return links_on_judge_paths(
        {path: mode for path, (mode, _) in entries.items()}, words
    )


# ---------------------------------------------------------------------------
# The pinned value (design item 1)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MergeEnvironment:
    """The install and launch block pinned on the target, with the test command.

    ``install_argv`` is empty when no install is declared. ``install_timeout``
    is already capped at the merge's own check time limit.
    """

    install_argv: Tuple[str, ...] = ()
    install_text: str = ""
    install_timeout: int = 0
    launch: Optional[LaunchDeclaration] = None
    # The plain words of the pinned test command and install, for the
    # judge-file comparison.
    judge_words: Tuple[str, ...] = ()
    # The project's protected paths, as declared on the target.
    protected_paths: Tuple[str, ...] = ()
    # The judge files this build changed (15 October 2026). Kept for the card
    # and the receipt only: they no longer stop the check, and they do not
    # decide what is put back, which is every judge file the target names
    # under its protected paths (:func:`judges_kept_from_target`).
    judge_files_changed: Tuple[str, ...] = ()


def pin_merge_environment(
    declarations: MergeDeclarations,
    test_command: Optional[str],
    verify_timeout: int,
) -> Tuple[Optional[MergeEnvironment], Optional[str]]:
    """Pin what the merge will run.

    Returns ``(pinned, None)``: the second place is kept for callers that
    read it and is always ``None``. The judge words come from the resolved
    test command and the declared install. The install runs as the argument
    list ``shlex.split`` gives; text that cannot be split is not run.
    ``judge_files_changed`` is filled in later, by the
    merge, from the files the build changed.
    """
    words: List[str] = []
    if test_command:
        test_words, _ = judge_words(test_command, through_shell=True)
        words.extend(test_words or ())

    toolchain = declarations.toolchain
    install_text = (toolchain.install or "") if toolchain is not None else ""
    install_argv: Tuple[str, ...] = ()
    install_timeout = 0
    if install_text:
        try:
            install_argv = tuple(shlex.split(install_text))
        except ValueError:
            install_argv = ()
        install_words, _ = judge_words(install_text, through_shell=False)
        words.extend(install_words or ())
        install_timeout = max(1, min(toolchain.install_timeout, verify_timeout))

    return (
        MergeEnvironment(
            install_argv=install_argv,
            install_text=install_text,
            install_timeout=install_timeout,
            launch=declarations.launch,
            judge_words=tuple(words),
            protected_paths=declarations.protected_paths,
        ),
        None,
    )

"""Inspect and refresh an installed GuardKit slash-command directory.

BACKGROUND — the two questions a health check has to keep apart
---------------------------------------------------------------
GuardKit ships a set of markdown "slash command" files (``feature-plan.md``,
``task-work.md``, ...). They are authored in ``installer/core/commands`` and
travel three ways:

* into ``~/.agentecflow/commands`` (the global install; ``~/.claude/commands``
  is a symlink to it), which is what a human's editor actually reads;
* into a project's ``.claude/commands``;
* inside the built wheel as ``guardkit/_installer_core/commands`` (DF-011
  force-include), which is why an installed *package* always carries a pristine
  copy of the commands it was built with. That copy is called the **shipped
  payload** throughout this module.

Alongside the installed commands sits a ``MANIFEST.json`` recording the sha256
of every command file **as it was at install time**. Comparing installed files
against that manifest answers exactly one question:

    "has anyone EDITED these files since they were installed?"   -> MODIFIED

It cannot answer the question people actually ask of a thing named a drift or
staleness check:

    "are these files CURRENT — i.e. as new as the guardkit I have installed?"

That second question needs a third input: the shipped payload. Comparing the
install-time manifest against the payload answers it:

    "is what I installed BEHIND the guardkit package I now have?"  -> STALE

The two are independent. A file can be edited but current, current but behind,
both, or neither. This module computes them as two separate axes and never
collapses one into the other.

WHY THIS EXISTS AS A SHARED MODULE
----------------------------------
``guardkit doctor`` reports these states and ``guardkit init --update`` acts on
them. Both must agree exactly about which files are safe to overwrite, so the
classification lives in one place and both import it. ``doctor`` is READ-ONLY;
only :func:`refresh_commands` writes, and it refuses by default to overwrite a
file whose content does not match the manifest (i.e. one a human has edited).
"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from guardkit.templates.resolver import resolve_installer_core_dir

MANIFEST_NAME = "MANIFEST.json"


def sha256_file(path: Path) -> str:
    """Return the sha256 hex digest of a file's bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_shipped_commands_dir() -> Optional[Path]:
    """Return the shipped command payload directory, or None if unavailable.

    The payload is ``installer/core/commands`` as carried by the *installed*
    guardkit package — located through the existing DF-011 resolver
    (:func:`guardkit.templates.resolver.resolve_installer_core_dir`), which
    prefers the wheel's force-included ``guardkit/_installer_core`` and falls
    back to the repo checkout for an editable install. Never a fresh path guess.

    Returns:
        Path to the payload commands dir, or None when the package ships no
        payload (a broken or partial install) — in which case staleness is
        simply unknowable and callers must say so rather than guess.
    """
    try:
        candidate = resolve_installer_core_dir() / "commands"
    except OSError:
        return None
    return candidate if candidate.is_dir() else None


def load_manifest(commands_dir: Path) -> Optional[dict]:
    """Load the install-time ``MANIFEST.json`` beside an installed commands dir.

    Args:
        commands_dir: An installed commands directory.

    Returns:
        The parsed manifest, or None when absent or unreadable/corrupt.
    """
    path = commands_dir / MANIFEST_NAME
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def manifest_hashes(manifest: dict) -> Dict[str, str]:
    """Return ``{command filename: sha256}`` from a manifest's ``commands`` map."""
    return {
        name: entry.get("sha256")
        for name, entry in (manifest.get("commands") or {}).items()
        if isinstance(entry, dict) and entry.get("sha256")
    }


def manifest_tombstones(manifest: dict) -> set:
    """Return the set of retired command filenames declared by a manifest."""
    return {
        (t.get("name") if isinstance(t, dict) else t)
        for t in (manifest.get("tombstones") or [])
    }


def payload_hashes(shipped_dir: Optional[Path]) -> Dict[str, str]:
    """Return ``{command filename: sha256}`` for the shipped payload.

    Hashes the payload files THEMSELVES rather than trusting a manifest that
    ships beside them: the payload's own manifest can lag its own sources (it
    did, in this repo, for three weeks), and a staleness check that trusted it
    would inherit that blind spot.

    Args:
        shipped_dir: Payload commands dir, or None when unavailable.

    Returns:
        Mapping of filename to sha256; empty when there is no payload.
    """
    if shipped_dir is None:
        return {}
    out: Dict[str, str] = {}
    for md in sorted(shipped_dir.glob("*.md")):
        try:
            out[md.name] = sha256_file(md)
        except OSError:
            continue
    return out


@dataclass
class CommandDirReport:
    """What one installed commands directory looks like against manifest+payload.

    Attributes:
        directory: The installed commands dir inspected.
        is_global: True for ``~/.agentecflow/commands`` (which must hold the
            complete set), False for a project ``.claude/commands`` (which may
            legitimately hold only a subset, so "missing" is not a defect there).
        current: Filenames that match the manifest AND the shipped payload —
            installed, unedited, and up to date.
        modified: Filenames whose installed bytes differ from the manifest —
            someone edited them locally. NEVER auto-overwritten.
        stale: Filenames whose manifest hash differs from the shipped payload —
            what was installed is older than the guardkit package now present.
        missing: Tracked filenames absent from a global install.
        retired_present: Retired (tombstoned) command files still on disk.
        version: The manifest's version string.
    """

    directory: Path
    is_global: bool
    current: List[str] = field(default_factory=list)
    modified: List[str] = field(default_factory=list)
    stale: List[str] = field(default_factory=list)
    missing: List[str] = field(default_factory=list)
    retired_present: List[str] = field(default_factory=list)
    version: str = "unknown"

    @property
    def refreshable(self) -> List[str]:
        """Stale filenames that are safe to overwrite (not locally edited)."""
        edited = set(self.modified)
        return [n for n in self.stale if n not in edited]


def inspect_commands_dir(
    commands_dir: Path,
    *,
    is_global: bool,
    manifest: Optional[dict] = None,
    shipped: Optional[Dict[str, str]] = None,
) -> Optional[CommandDirReport]:
    """Classify every tracked command file in one installed directory.

    The two axes are computed independently, so a file that is BOTH locally
    edited and behind the shipped payload appears in ``modified`` and in
    ``stale``:

    * ``modified`` — installed bytes  != manifest sha  (a local edit)
    * ``stale``    — manifest sha     != payload sha   (the install is behind)

    Args:
        commands_dir: Installed commands directory to inspect.
        is_global: True for the global ``~/.agentecflow/commands`` surface.
        manifest: Pre-loaded manifest; loaded from ``commands_dir`` when None.
        shipped: Pre-computed payload hashes; computed when None.

    Returns:
        A :class:`CommandDirReport`, or None when no manifest is available (the
        directory's provenance is unknown, so nothing can be classified).
    """
    manifest = manifest if manifest is not None else load_manifest(commands_dir)
    if manifest is None:
        return None
    shipped = shipped if shipped is not None else payload_hashes(
        resolve_shipped_commands_dir()
    )

    expected = manifest_hashes(manifest)
    tombstones = manifest_tombstones(manifest)
    report = CommandDirReport(
        directory=commands_dir,
        is_global=is_global,
        version=manifest.get("version", "unknown"),
    )

    present = {p.name for p in commands_dir.glob("*.md")}
    for name, expected_sha in sorted(expected.items()):
        target = commands_dir / name
        payload_sha = shipped.get(name)
        behind = payload_sha is not None and payload_sha != expected_sha

        if not target.is_file():
            # A project dir legitimately holds a subset (per-file-if-absent
            # copies), so absence is only a defect for the global install.
            if is_global:
                report.missing.append(name)
            continue

        try:
            actual = sha256_file(target)
        except OSError:
            report.missing.append(name)
            continue

        edited = actual != expected_sha
        if edited:
            report.modified.append(name)
        if behind:
            report.stale.append(name)
        if not edited and not behind:
            report.current.append(name)

    for name in sorted(tombstones & present):
        report.retired_present.append(name)

    return report


def installed_command_dirs(
    home: Optional[Path] = None, project: Optional[Path] = None
) -> List[Tuple[Path, bool]]:
    """Return candidate installed command dirs as ``(path, is_global)`` pairs.

    On a standard install ``~/.claude/commands`` is a SYMLINK to
    ``~/.agentecflow/commands``, so scanning both would double-count; results
    are de-duplicated by resolved real path, which handles the symlink case and
    the plain-copy case alike without assuming either.

    Args:
        home: Home directory override (defaults to ``Path.home()``).
        project: Project directory override (defaults to the cwd).

    Returns:
        De-duplicated ``(dir, is_global)`` pairs that exist on disk.
    """
    home = home or Path.home()
    project = project or Path.cwd()
    pairs: List[Tuple[Path, bool]] = []
    seen: set = set()
    candidates = [
        (home / ".agentecflow" / "commands", True),
        (home / ".claude" / "commands", True),
        (project / ".claude" / "commands", False),
    ]
    for d, is_global in candidates:
        try:
            real = d.resolve()
        except OSError:
            continue
        if d.is_dir() and real not in seen:
            seen.add(real)
            pairs.append((d, is_global))
    return pairs


@dataclass
class RefreshResult:
    """Outcome of refreshing one installed commands directory.

    Attributes:
        directory: The directory refreshed.
        updated: Filenames overwritten from the shipped payload.
        skipped_modified: Filenames left alone because they were locally edited.
        manifest_written: True if ``MANIFEST.json`` was rewritten to describe
            what is now installed.
    """

    directory: Path
    updated: List[str] = field(default_factory=list)
    skipped_modified: List[str] = field(default_factory=list)
    manifest_written: bool = False


def refresh_commands(
    commands_dir: Path,
    *,
    is_global: bool = True,
    force: bool = False,
    shipped_dir: Optional[Path] = None,
) -> Optional[RefreshResult]:
    """Refresh installed command files from the shipped payload.

    Safety contract (the reason ``init`` is per-file-if-absent in the first
    place): a file whose installed bytes differ from the install-time manifest
    has been EDITED by a human and is NEVER overwritten — it is reported in
    ``skipped_modified`` so the caller can name it. ``force=True`` overrides
    that, and only a human passing ``--force`` can set it.

    Only files the manifest already tracks are touched. Nothing is created that
    was not there before unless it is a tracked command missing from a global
    install; unrelated files in the directory are left alone.

    Args:
        commands_dir: Installed commands directory to refresh.
        is_global: True for the global surface (missing tracked commands are
            restored); False for a project dir (subsets are legitimate, so a
            missing file stays missing).
        force: Overwrite locally-edited files too.
        shipped_dir: Payload override (defaults to the resolved payload).

    Returns:
        A :class:`RefreshResult`, or None when there is no payload or no
        manifest — nothing can be refreshed safely without both.
    """
    shipped_dir = shipped_dir or resolve_shipped_commands_dir()
    if shipped_dir is None:
        return None
    manifest = load_manifest(commands_dir)
    if manifest is None:
        return None

    expected = manifest_hashes(manifest)
    result = RefreshResult(directory=commands_dir)

    for name in sorted(expected):
        src = shipped_dir / name
        if not src.is_file():
            continue
        dest = commands_dir / name
        if dest.is_file():
            actual = sha256_file(dest)
            if actual == sha256_file(src):
                continue  # already current
            if actual != expected[name] and not force:
                result.skipped_modified.append(name)
                continue
        elif not is_global:
            # Project dirs legitimately hold a subset; do not add new files.
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        result.updated.append(name)

    # Rewrite the manifest so it describes what is NOW installed. Without this,
    # the next run would still compare against the old install-time hashes and
    # report every file we just refreshed as MODIFIED.
    #
    # Files we SKIPPED because a human had edited them keep their ORIGINAL
    # manifest entry. Recomputing their hash would quietly bless the edit and
    # erase the only evidence that the file was ever changed by hand.
    if result.updated:
        merged = _merged_manifest(
            old=manifest,
            shipped_dir=shipped_dir,
            keep_old_for=set(result.skipped_modified),
        )
        if merged is not None:
            (commands_dir / MANIFEST_NAME).write_text(
                json.dumps(merged, indent=2) + "\n", encoding="utf-8"
            )
            result.manifest_written = True

    return result


def _merged_manifest(
    *, old: dict, shipped_dir: Path, keep_old_for: set
) -> Optional[dict]:
    """Build the post-refresh manifest describing what is now installed.

    Starts from the payload's own manifest (for version, tombstones and
    provenance), then makes two corrections:

    1. every tracked command's ``sha256`` is recomputed from the PAYLOAD FILE on
       disk, because the payload's shipped manifest can itself lag its own
       sources — copying it verbatim would install a manifest that disagrees
       with the very files it was copied beside;
    2. any command listed in *keep_old_for* (locally edited, therefore skipped)
       retains its original entry, preserving the MODIFIED signal.

    Args:
        old: The manifest currently installed.
        shipped_dir: The shipped payload commands dir.
        keep_old_for: Command filenames that were not overwritten.

    Returns:
        The merged manifest dict, or None if the payload ships no manifest.
    """
    src_manifest = shipped_dir / MANIFEST_NAME
    if not src_manifest.is_file():
        return None
    try:
        merged = json.loads(src_manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None

    old_entries = (old.get("commands") or {})
    entries = merged.get("commands") or {}
    for name, entry in list(entries.items()):
        if name in keep_old_for and name in old_entries:
            entries[name] = old_entries[name]
            continue
        payload_file = shipped_dir / name
        if payload_file.is_file() and isinstance(entry, dict):
            entry["sha256"] = sha256_file(payload_file)
    merged["commands"] = entries
    return merged

"""Keep an earlier round's turn files when a gate re-opens a task.

WHY THIS EXISTS (18 October 2026)
---------------------------------
A gate that runs after a wave (the smoke gate, the wiring gate, the
whole-feature check) can re-open an approved task for a repair round. Each
round numbers its turns from 1 again and writes the same file names
(``player_turn_1.json``, ``coach_turn_1.json`` ...), so the repair round
overwrote the first round's records. FEAT-15DD's first round, the one whose
approval the whole-feature check then failed, was lost that way.

WHAT IT DOES
------------
Before the repair round starts, the task's ``*_turn_*.json`` files are MOVED,
with their names unchanged, into ``round-<N>/`` beside them, where ``N`` is
one more than the highest ``round-*`` folder already in any of the task's
folders. The live names are therefore always the latest round, so every
writer, every reader (they all look in one folder, never below it) and the
Player's own instructions keep working unchanged. Moving rather than copying
also stops an earlier round's higher-numbered turn being read as the latest.
This copies the rollback archive's pattern in ``worktree_checkpoints``.

A record never fails a build: a folder or file that cannot be moved is logged
and the round goes ahead as it would have before.
"""

from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path
from typing import Iterable, List, Optional

logger = logging.getLogger(__name__)

#: The turn files of one round: every per-turn record a task writes.
TURN_FILE_GLOB = "*_turn_*.json"

#: The folder name an archived round goes into.
ROUND_DIR_PREFIX = "round-"

_ROUND_DIR = re.compile(r"^round-(\d+)$")


def _highest_round(folder: Path) -> int:
    highest = 0
    try:
        for child in folder.iterdir():
            match = _ROUND_DIR.match(child.name)
            if match and child.is_dir():
                highest = max(highest, int(match.group(1)))
    except OSError:
        return 0
    return highest


def _unique_folders(folders: Iterable[Path]) -> List[Path]:
    seen = set()
    unique: List[Path] = []
    for folder in folders:
        try:
            key = Path(folder).resolve()
        except OSError:
            key = Path(folder)
        if key in seen:
            continue
        seen.add(key)
        unique.append(Path(folder))
    return unique


def archive_turn_files(task_id: str, folders: Iterable[Path]) -> Optional[int]:
    """Move a task's turn files into ``round-<N>/`` in each of ``folders``.

    Returns the round number used, or ``None`` when there was nothing to move
    (or nothing could be moved). Never raises.
    """
    try:
        folders = [f for f in _unique_folders(folders) if f.is_dir()]
        moving = {
            folder: sorted(p for p in folder.glob(TURN_FILE_GLOB) if p.is_file())
            for folder in folders
        }
        if not any(moving.values()):
            return None
        number = 1 + max((_highest_round(folder) for folder in folders), default=0)
        moved = 0
        for folder, files in moving.items():
            if not files:
                continue
            target = folder / f"{ROUND_DIR_PREFIX}{number}"
            try:
                target.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                logger.warning(
                    "[%s] The earlier round's turn files in %s could not be "
                    "kept (folder not made: %s); the repair round goes ahead.",
                    task_id, folder, exc,
                )
                continue
            for path in files:
                try:
                    shutil.move(str(path), str(target / path.name))
                    moved += 1
                except OSError as exc:
                    logger.warning(
                        "[%s] Turn file %s could not be moved into %s: %s; "
                        "the repair round goes ahead.",
                        task_id, path.name, target, exc,
                    )
        if not moved:
            return None
        logger.info(
            "[%s] Kept the earlier round's %d turn file(s) in %s%d/ before the "
            "repair round.",
            task_id, moved, ROUND_DIR_PREFIX, number,
        )
        return number
    except Exception as exc:  # noqa: BLE001 — a record never fails a build
        logger.warning(
            "[%s] The earlier round's turn files could not be kept: %s; the "
            "repair round goes ahead.",
            task_id, exc,
        )
        return None

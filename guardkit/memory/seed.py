"""Copy a project's accepted documents into its own memory: ``guardkit memory seed``.

Project initialisation design, 4 October 2026 (ai-transition
``docs/source-material/project-initialisation-2026-10-04/design.md``, Part 5).

A person or session runs this after accepting documents. It reads what the
project declares from the commit at ``HEAD`` — never the working tree — and
writes one memory record per file, without duplicates:

* **Which memory**: :func:`resolve_memory_project`, with no fallback. Memory
  off means the run is refused.
* **Which files**: ``memory.seed_documents`` in the project's
  ``.guardkit/config.yaml`` (repository paths, or ``fnmatch`` patterns over the
  files tracked at ``HEAD``), else ``autobuild.player.required_documents``.
  The declaration and every listed file must be committed and unmodified; a
  symbolic link is refused.
* **Decision records** (a status line, and a file name starting with a
  GuardKit decision id such as ``ADR-ARCH-001`` or ``DDR-001``) become ``adr``
  records under the id the commands already write (``ADR_ARCH_001``), with
  title, context, decision, consequences and alternatives from the file's own
  headings, the status as written, and a ``Supersedes:`` line mapped to the
  replaced record's natural key.
* **Other documents** become ``document`` records under the sanitised path,
  with the full text and the tags AutoBuild's architecture reads ask for.
* **Provenance**: ``source_ref`` is ``<path>@<last commit that changed
  it>#sha256:<16 hex>``, so an unchanged file produces an identical payload and
  the store keeps one record without a new version.
* **No shared identities**: every identifier is computed before anything is
  sent; two files with one identifier refuse the whole run.
* **Published is not stored**: each write carries its payload's content hash as
  the broker's ``dedup_token``, and each record is read back before it is
  reported as stored.

Nothing is ever deleted from memory: a file no longer in the repository is
reported by name if it is still listed.
"""

from __future__ import annotations

import asyncio
import fnmatch
import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

import yaml

from guardkit.knowledge.fleet_memory_mapping import resolve as resolve_group
from guardkit.lib import committed_content
from guardkit.knowledge.fleet_memory_payloads import (
    build_memory_episode,
    sanitize_identifier,
)
from guardkit.knowledge.memory_project import CONFIG_RELATIVE_PATH

#: The declaration file, as a repository path.
CONFIG_PATH = CONFIG_RELATIVE_PATH.as_posix()

#: Where the records go: an ``adr`` group and a ``document`` group of the
#: existing mapping. The categories the records carry are set explicitly below.
DECISION_GROUP = "project_decisions"
DOCUMENT_GROUP = "project_architecture"

#: Categories for a seeded document: what AutoBuild's architecture category
#: and ``/feature-plan`` search ask for, plus a tag that says where it came from.
DOCUMENT_TAGS = ["architecture", "project_document"]

#: Categories for decision records, the ones the commands write them with
#: (``docs/internals/commands-lib/memory-preamble.md``).
ADR_TAGS = ["architecture"]
DDR_TAGS = ["architecture", "design"]

#: A GuardKit decision id at the start of a file name: ``ADR-ARCH-001``,
#: ``ADR-SP-002``, ``ADR-001``, ``DDR-001``.
DECISION_ID = re.compile(r"(?:ADR(?:-[A-Z][A-Z0-9]*)*|DDR)-\d{3,}")
_DECISION_FILE = re.compile(rf"^(?P<id>{DECISION_ID.pattern})(?=$|[-_.])")

#: A decision-record status line: ``Status: accepted``, ``**Status:** Accepted``,
#: ``> Status: **Accepted**``.
_STATUS_LINE = re.compile(
    r"^[ \t]*(?:>[ \t]*)?(?:\*\*Status:\*\*|\*\*Status\*\*:|Status:)[ \t]*(?P<status>\S.*?)[ \t]*$",
    re.MULTILINE,
)
_SUPERSEDES_LINE = re.compile(
    r"^[ \t]*(?:>[ \t]*)?(?:\*\*Supersedes:\*\*|\*\*Supersedes\*\*:|Supersedes:)(?P<rest>.*)$",
    re.MULTILINE | re.IGNORECASE,
)
#: The leading run of decision ids in a Supersedes entry, separated by commas,
#: spaces, "and" or "&", optionally in back-quotes. It stops at the first other
#: text, so ``ADR-ARCH-001 (see also DDR-007)`` supersedes ADR-ARCH-001 only.
_ID_TOKEN = rf"`?(?:{DECISION_ID.pattern})`?(?!\w)"
_ID_RUN = re.compile(
    rf"^\s*{_ID_TOKEN}(?:\s*(?:,\s*)?(?:(?:and|&)\s+)?{_ID_TOKEN})*",
    re.IGNORECASE,
)
_LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(?P<item>.*)$")
_HEADING = re.compile(r"^(?P<level>#{1,6})[ \t]+(?P<title>.+?)[ \t]*#*[ \t]*$", re.MULTILINE)

#: How long to keep looking for a just-published record before saying it is
#: not confirmed: the relay writes it shortly after the bus carries it.
READ_BACK_ATTEMPTS = 5
READ_BACK_DELAY_SECONDS = 1.0


#: The whole run is refused before anything is written; the message says why.
#: The same class the shared committed-content reader raises, so a git failure
#: inside it is a refusal of the run too.
SeedRefused = committed_content.CommittedContentError


@dataclass(frozen=True)
class SeedItem:
    """One file, and the record it will become."""

    path: str
    kind: str  # "decision" or "document"
    payload_type: str
    group_id: str
    identifier: str
    natural_key: str
    source_ref: str
    name: str
    episode_body: str
    payload: dict
    dedup_token: str
    decision_id: Optional[str] = None


@dataclass
class SeedPlan:
    """Everything the run would write, and everything it refused."""

    project: str
    repo: Path
    head: str
    declared_from: str
    items: list[SeedItem] = field(default_factory=list)
    refusals: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SeedResult:
    """What happened to one file."""

    path: str
    natural_key: str
    status: str  # "stored", "published, not confirmed", "not published"
    version: Optional[int] = None
    detail: str = ""

    @property
    def confirmed(self) -> bool:
        return self.status == "stored"

    def line(self) -> str:
        if self.status == "stored":
            text = f"stored (version {self.version})"
        else:
            text = self.status
        detail = f" — {self.detail}" if self.detail else ""
        return f"{self.path} → {self.natural_key}: {text}{detail}"


# ---------------------------------------------------------------------------
# Git, at HEAD only — the shared committed-content reader
# ---------------------------------------------------------------------------

_git = committed_content.git
_git_text = committed_content.git_text
_tree_entries = committed_content.tree_entries
_changed_paths = committed_content.changed_paths
_blob = committed_content.blob


# ---------------------------------------------------------------------------
# The declaration
# ---------------------------------------------------------------------------


def _path_list(raw: Any, field_name: str) -> list[str]:
    if not isinstance(raw, list) or not all(
        isinstance(value, str) and value.strip() for value in raw
    ):
        raise SeedRefused(
            f"`{field_name}` in {CONFIG_PATH} must be a list of repository paths."
        )
    for value in raw:
        if Path(value).is_absolute():
            raise SeedRefused(
                f"`{field_name}` in {CONFIG_PATH} names {value!r}; paths must be "
                "relative to the repository."
            )
    return list(raw)


def _declared(config_text: Optional[str]) -> tuple[list[str], str]:
    """``(entries, where)``: the seed list and which setting it came from."""
    if config_text is None:
        return [], ""
    try:
        data = yaml.safe_load(config_text) or {}
    except yaml.YAMLError as exc:
        raise SeedRefused(f"{CONFIG_PATH} at HEAD is not valid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise SeedRefused(f"{CONFIG_PATH} at HEAD is not a set of settings.")
    memory = data.get("memory")
    if isinstance(memory, dict) and memory.get("seed_documents") is not None:
        return (
            _path_list(memory["seed_documents"], "memory.seed_documents"),
            "memory.seed_documents",
        )
    autobuild = data.get("autobuild")
    player = autobuild.get("player") if isinstance(autobuild, dict) else None
    if isinstance(player, dict) and player.get("required_documents") is not None:
        return (
            _path_list(
                player["required_documents"], "autobuild.player.required_documents"
            ),
            "autobuild.player.required_documents",
        )
    return [], ""


def _is_pattern(entry: str) -> bool:
    return any(char in entry for char in "*?[")


# ---------------------------------------------------------------------------
# Decision records
# ---------------------------------------------------------------------------


def decision_id_for(path: str, text: str) -> Optional[str]:
    """The decision id when ``path`` is a GuardKit decision record, else ``None``."""
    match = _DECISION_FILE.match(Path(path).name)
    if match is None or _STATUS_LINE.search(text) is None:
        return None
    return match.group("id")


def _sections(text: str) -> tuple[Optional[str], dict[str, str]]:
    """The first top-level title, and each ``##`` section's text by lower-case name."""
    title: Optional[str] = None
    sections: dict[str, str] = {}
    headings = list(_HEADING.finditer(text))
    for position, heading in enumerate(headings):
        level = len(heading.group("level"))
        name = heading.group("title").strip()
        if level == 1 and title is None:
            title = name
        if level != 2:
            continue
        end = len(text)
        for later in headings[position + 1:]:
            if len(later.group("level")) <= 2:
                end = later.start()
                break
        sections.setdefault(name.lower(), text[heading.end():end].strip())
    return title, sections


_SUBHEADING = re.compile(r"^#{3,6}[ \t]+(?P<title>.+?)[ \t]*#*[ \t]*$", re.MULTILINE)


def _alternatives(section: str) -> list[str]:
    """The alternatives in an "Alternatives Considered" section, each complete.

    * Sub-headed entries (GuardKit's DDR template renders each alternative as
      ``### <name>`` with Pros/Cons bullets): one entry per sub-heading — its
      name, then everything under it — plus any prose before the first one.
    * A flat bullet list (the ADR template's form): one entry per bullet.
    * Anything else (a table, paragraphs): the whole section as one entry,
      so nothing written is dropped.
    """
    headings = list(_SUBHEADING.finditer(section))
    if headings:
        entries = []
        lead = section[: headings[0].start()].strip()
        if lead:
            entries.append(lead)
        for position, heading in enumerate(headings):
            end = (
                headings[position + 1].start()
                if position + 1 < len(headings)
                else len(section)
            )
            body = section[heading.end():end].strip()
            name = heading.group("title").strip()
            entries.append(f"{name}\n{body}" if body else name)
        return entries
    lines = [line for line in section.splitlines() if line.strip()]
    if lines and all(line[:2] in ("- ", "* ") and line[2:].strip() for line in lines):
        return [line[2:].strip() for line in lines]
    return [section]


def _leading_ids(text: str) -> list[str]:
    """The decision ids at the very start of ``text``, before any other words."""
    run = _ID_RUN.match(text.replace("**", ""))
    return DECISION_ID.findall(run.group(0)) if run else []


def _supersedes_section_ids(section: str) -> list[str]:
    """Ids from a ``## Supersedes`` section: its first line and its list items,
    each read only for the ids it starts with."""
    lines = [line for line in section.splitlines() if line.strip()]
    ids: list[str] = []
    for position, line in enumerate(lines):
        item = _LIST_ITEM.match(line)
        if item is not None:
            ids.extend(_leading_ids(item.group("item")))
        elif position == 0:
            ids.extend(_leading_ids(line))
    return ids


def decision_fields(decision_id: str, text: str, project: str) -> dict:
    """Title, status, context, decision, consequences, alternatives and supersedes."""
    status_match = _STATUS_LINE.search(text)
    status = status_match.group("status").strip() if status_match else ""
    status = status.strip("*").strip() or status
    title, sections = _sections(text)
    if title:
        prefix = re.match(rf"^{re.escape(decision_id)}\s*[:\-—–]\s*", title)
        if prefix:
            title = title[prefix.end():].strip() or title
    fields: dict[str, Any] = {
        "id": decision_id,
        "status": status,
        "decision": sections.get("decision") or text,
    }
    if title:
        fields["title"] = title
    if sections.get("context"):
        fields["context"] = sections["context"]
    if sections.get("consequences"):
        fields["consequences"] = sections["consequences"]
    alternatives_text = sections.get("alternatives considered") or sections.get(
        "alternatives"
    )
    if alternatives_text:
        fields["alternatives"] = _alternatives(alternatives_text)
    replaced: list[str] = []
    for line in _SUPERSEDES_LINE.finditer(text):
        replaced.extend(_leading_ids(line.group("rest")))
    if sections.get("supersedes"):
        replaced.extend(_supersedes_section_ids(sections["supersedes"]))
    keys = []
    for other in replaced:
        key = f"adr:{project}:{sanitize_identifier(other)}"
        if other != decision_id and key not in keys:
            keys.append(key)
    if keys:
        fields["supersedes"] = keys
    return fields


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------


def payload_hash(payload: dict) -> str:
    """SHA-256 of the payload's canonical JSON: the write's ``dedup_token``."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def plan_seed(repo: Path, project: str) -> SeedPlan:
    """Work out every record the run would write, from the commit at HEAD.

    Never writes anything. Raises :class:`SeedRefused` for a problem with the
    repository or its declaration as a whole; per-file problems are collected
    in ``plan.refusals`` (and any refusal stops the run before publishing).
    """
    repo = Path(repo)
    head = _git_text(repo, "rev-parse", "--verify", "HEAD^{commit}").strip()
    entries = _tree_entries(repo)

    if CONFIG_PATH in _changed_paths(repo, [CONFIG_PATH]):
        raise SeedRefused(
            f"{CONFIG_PATH} has uncommitted changes. The seed reads the declaration "
            "from the commit at HEAD; commit it first."
        )
    config_text: Optional[str] = None
    if CONFIG_PATH not in entries and (repo / CONFIG_PATH).exists():
        raise SeedRefused(
            f"{CONFIG_PATH} is not committed. The seed reads the declaration from "
            "the commit at HEAD; commit it first."
        )
    if CONFIG_PATH in entries:
        if entries[CONFIG_PATH] == "120000":
            raise SeedRefused(f"{CONFIG_PATH} is a symbolic link; it must be a file.")
        config_text = _blob(repo, CONFIG_PATH).decode("utf-8", "replace")
    declared, declared_from = _declared(config_text)

    plan = SeedPlan(project=project, repo=repo, head=head, declared_from=declared_from)

    paths: list[str] = []
    for entry in declared:
        if _is_pattern(entry):
            matched = sorted(p for p in entries if fnmatch.fnmatchcase(p, entry))
            if not matched:
                plan.refusals.append(
                    f"{entry}: the pattern matches no file committed at HEAD."
                )
            paths.extend(p for p in matched if p not in paths)
        elif entry not in entries:
            plan.refusals.append(
                f"{entry}: declared, but not committed at HEAD (missing, deleted or "
                "never added). Nothing in memory is removed."
            )
        elif entry not in paths:
            paths.append(entry)

    changed = _changed_paths(repo, paths)
    for path in paths:
        mode = entries[path]
        if path in changed:
            plan.refusals.append(
                f"{path}: has uncommitted changes; commit them first so memory "
                "records the committed text."
            )
            continue
        if mode == "120000":
            plan.refusals.append(
                f"{path}: is a symbolic link; a document to seed must be an "
                "ordinary file."
            )
            continue
        if not mode.startswith("100"):
            plan.refusals.append(f"{path}: is not an ordinary file (mode {mode}).")
            continue
        data = _blob(repo, path)
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            plan.refusals.append(f"{path}: is not UTF-8 text.")
            continue
        last_commit = _git_text(repo, "log", "-1", "--format=%H", "HEAD", "--", path).strip()
        source_ref = f"{path}@{last_commit}#sha256:{hashlib.sha256(data).hexdigest()[:16]}"
        plan.items.append(_item(project, path, text, source_ref))

    owners: dict[str, str] = {}
    for item in plan.items:
        if item.natural_key in owners:
            plan.refusals.append(
                f"{owners[item.natural_key]} and {item.path} would both be stored as "
                f"{item.natural_key}; rename one, or list only one of them. Nothing "
                "was written."
            )
        else:
            owners[item.natural_key] = item.path
    return plan


def _item(project: str, path: str, text: str, source_ref: str) -> SeedItem:
    decision_id = decision_id_for(path, text)
    if decision_id is not None:
        data = decision_fields(decision_id, text, project)
        data["domain_tags"] = DDR_TAGS if decision_id.startswith("DDR") else ADR_TAGS
        group_id, kind = DECISION_GROUP, "decision"
    else:
        data = {"id": path, "content": text, "domain_tags": list(DOCUMENT_TAGS)}
        group_id, kind = DOCUMENT_GROUP, "document"
    data["source_ref"] = source_ref
    mapping = resolve_group(group_id)
    assert mapping is not None  # both groups are in the mapping table
    episode_body = json.dumps(data, sort_keys=True)
    episode = build_memory_episode(
        mapping, name=path, episode_body=episode_body, source="guardkit-seed",
        project=project,
    )
    if episode is None:  # pragma: no cover - only without a project name
        raise SeedRefused(f"{path}: could not be turned into a memory record.")
    payload = json.loads(episode.body)
    return SeedItem(
        path=path,
        kind=kind,
        payload_type=mapping.payload_type,
        group_id=group_id,
        identifier=payload["identifier"],
        natural_key=f"{mapping.payload_type}:{project}:{payload['identifier']}",
        source_ref=source_ref,
        name=path,
        episode_body=episode_body,
        payload=payload,
        dedup_token=payload_hash(payload),
        decision_id=decision_id,
    )


# ---------------------------------------------------------------------------
# Writing and reading back
# ---------------------------------------------------------------------------


async def publish_and_confirm(
    plan: SeedPlan,
    client: Any,
    *,
    attempts: Optional[int] = None,
    delay_seconds: Optional[float] = None,
    sleep: Callable[[float], Awaitable[Any]] = asyncio.sleep,
    on_result: Optional[Callable[[SeedResult], Any]] = None,
) -> list[SeedResult]:
    """Write each planned record, then read it back before calling it stored.

    Every file gets a result, in order, even when something fails part-way:
    a write or a read that raises is reported for that file and the run goes
    on. ``on_result`` is called with each result as soon as it is known (the
    command prints it), so nothing already done is lost from the output.
    """
    attempts = READ_BACK_ATTEMPTS if attempts is None else attempts
    delay_seconds = READ_BACK_DELAY_SECONDS if delay_seconds is None else delay_seconds
    results: list[SeedResult] = []
    for item in plan.items:
        try:
            key = await client.add_episode(
                name=item.name,
                episode_body=item.episode_body,
                group_id=item.group_id,
                source="guardkit-seed",
                dedup_token=item.dedup_token,
            )
        except Exception as exc:  # noqa: BLE001 — reported per file, run goes on
            key = None
            detail = f"the write failed ({type(exc).__name__}: {exc})"
        else:
            detail = "the bus and the door both refused or were unreachable"
        if key is None:
            result = SeedResult(item.path, item.natural_key, "not published", detail=detail)
        else:
            try:
                result = await _confirm(item, client, attempts, delay_seconds, sleep)
            except Exception as exc:  # noqa: BLE001 — reported per file, run goes on
                result = SeedResult(
                    item.path, item.natural_key, "published, not confirmed",
                    detail=f"reading it back failed ({type(exc).__name__}: {exc})",
                )
        results.append(result)
        if on_result is not None:
            on_result(result)
    return results


async def _confirm(item, client, attempts, delay_seconds, sleep) -> SeedResult:
    read_record = getattr(client, "read_record", None)
    if read_record is None:
        return SeedResult(
            item.path, item.natural_key, "published, not confirmed",
            detail="this memory client has no way to read a record back",
        )
    from guardkit.knowledge.fleet_memory_client import MemoryReadUnavailable

    record = None
    for attempt in range(max(1, attempts)):
        try:
            record = await read_record(item.payload_type, item.identifier)
        except MemoryReadUnavailable as exc:
            return SeedResult(item.path, item.natural_key, "published, not confirmed",
                              detail=str(exc))
        if record is not None and record.get("source_ref") == item.source_ref:
            return SeedResult(item.path, item.natural_key, "stored",
                              version=record.get("version"))
        if attempt + 1 < attempts:
            await sleep(delay_seconds)
    if record is None:
        detail = "no record was found under that key after publishing"
    else:
        detail = (
            f"the stored record still carries {record.get('source_ref')!r}, "
            "not this commit's text"
        )
    return SeedResult(item.path, item.natural_key, "published, not confirmed",
                      detail=detail)


def plan_lines(plan: SeedPlan) -> list[str]:
    """The plan, one plain line per file, for ``--dry-run`` and the run's header."""
    lines = [
        f"Memory: {plan.project}. Reading from HEAD {plan.head[:12]} of {plan.repo}.",
    ]
    if plan.declared_from:
        lines.append(f"Documents named by {plan.declared_from}.")
    for item in plan.items:
        what = (
            f"decision {item.decision_id}" if item.kind == "decision" else "document"
        )
        lines.append(
            f"{item.path} → {item.natural_key} ({what}; {item.source_ref}; "
            f"token {item.dedup_token[:12]})"
        )
    return lines

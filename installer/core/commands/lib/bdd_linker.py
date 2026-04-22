"""Gherkin scenario-to-task linking for /feature-plan Phase: BDD scenario linking
(TASK-FP-LINK).

This module provides the mechanical half of the R2 linking step: parse a
``features/*.feature`` file, emit a structured matching request the /feature-plan
command can pass to a scenario-to-task matching subagent, and atomically rewrite
the file with ``@task:<TASK-ID>`` tags once a mapping has been confirmed.

Design (see TASK-FP-LINK):

- Matching itself lives outside this module. /feature-plan invokes a
  ``bdd-linker`` subagent with the payload produced by
  :func:`build_matching_request` and feeds the returned matches back through
  :func:`apply_mapping`. This keeps deterministic file I/O separate from the
  LLM-assisted matching decision so the rewrite half stays trivially testable.
- Tag insertion is additive: a new ``@task:TASK-ID`` line is inserted immediately
  above the top-most existing tag line for the scenario (or directly above the
  ``Scenario:`` / ``Scenario Outline:`` keyword line when no tags exist).
  Existing lines are preserved byte-for-byte so category tags like
  ``@key-example`` and inline comments survive the rewrite.
- Idempotency is enforced at two levels: scenarios already carrying any
  ``@task:`` tag are skipped entirely (re-runs land the tag exactly once), and
  when several candidate matches point to the same scenario the highest
  confidence wins.
- Rewrite safety: parse → compute insertions → write to a temp file in the same
  directory → ``os.replace`` atomically. We never truncate the source in place.

The consumer of this module is the follow-on task TASK-FP-LINK-B, which adds
the ``bdd-linker`` subagent and wires the Phase into /feature-plan.md.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


DEFAULT_CONFIDENCE_THRESHOLD = 0.6
"""Default minimum confidence for auto-applying a scenario-to-task match.

Below this threshold the match is reported as ``skipped_low_confidence`` and
the scenario is left untagged — the user can resolve it manually, re-run
/feature-plan after clarifying task descriptions, or leave R2 dormant for
that scenario.
"""

_TASK_TAG_PREFIX = "@task:"
_SCENARIO_KEYWORDS = {"Scenario", "Scenario Outline", "Example"}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ScenarioInfo:
    """A scenario in a parsed feature document.

    Attributes:
        index: 0-based position of this scenario within the document's
            scenarios list. Used as the mapping key in TaskMatch.
        name: The scenario's name (text after the ``Scenario:`` keyword).
        keyword: Gherkin keyword — ``"Scenario"``, ``"Scenario Outline"``, or
            ``"Example"``.
        description: Free-text description beneath the scenario line (may be
            empty).
        steps: Gherkin step lines as plain text (``"Given ..."`` etc.) — used
            to give the matching subagent the scenario body so it can judge
            fit beyond the headline name.
        line: 1-based line number of the ``Scenario:`` keyword line (matches
            gherkin-official ``location.line``).
        indent: The leading whitespace of the ``Scenario:`` line, used so
            inserted tag lines align with the scenario they precede when no
            existing tags drive the indent.
        tags: Existing tag strings on this scenario (e.g. ``"@smoke"``,
            ``"@task:TASK-AUTH-001"``). Preserved verbatim.
        tag_line: 1-based line of the top-most existing tag for this scenario,
            or ``None`` when the scenario has no tags. Determines the insertion
            point for the new ``@task:`` line.
        tag_indent: The leading whitespace of the top-most existing tag line
            (if any). Takes precedence over ``indent`` for insertion so a new
            tag line matches the indent of the tag line it sits above.
    """

    index: int
    name: str
    keyword: str
    description: str
    steps: List[str]
    line: int
    indent: str
    tags: List[str] = field(default_factory=list)
    tag_line: Optional[int] = None
    tag_indent: Optional[str] = None


@dataclass
class FeatureDocument:
    """Result of parsing a single ``.feature`` file."""

    path: Path
    raw_text: str
    lines: List[str]
    line_ending: str
    trailing_newline: bool
    feature_name: str
    feature_tags: List[str]
    scenarios: List[ScenarioInfo]


@dataclass
class TaskInfo:
    """Metadata about a task for matching purposes.

    Only fields the matching subagent needs to judge scenario fit are included
    — frontmatter like ``wave`` or ``conductor_workspace`` is irrelevant and
    would just crowd the prompt.
    """

    task_id: str
    title: str
    description: str = ""
    acceptance_criteria: List[str] = field(default_factory=list)


@dataclass
class MatchingRequest:
    """Structured payload handed to the scenario-to-task matching subagent.

    The subagent returns a list of ``TaskMatch`` values (serialised as JSON)
    which are then fed back through :func:`apply_mapping`.
    """

    feature_path: str
    feature_name: str
    confidence_threshold: float
    scenarios: List[Dict[str, Any]]
    tasks: List[Dict[str, Any]]

    def to_json(self, indent: Optional[int] = 2) -> str:
        """Serialise to JSON for inclusion in a subagent prompt."""
        return json.dumps(
            {
                "feature_path": self.feature_path,
                "feature_name": self.feature_name,
                "confidence_threshold": self.confidence_threshold,
                "scenarios": self.scenarios,
                "tasks": self.tasks,
            },
            indent=indent,
            ensure_ascii=False,
        )


@dataclass
class TaskMatch:
    """A single scenario-to-task match proposed by the matching subagent."""

    scenario_index: int
    task_id: str
    confidence: float


@dataclass
class LinkingResult:
    """Outcome of :func:`apply_mapping`.

    Attributes:
        path: File that was considered (rewritten when ``dry_run=False`` and
            ``linked`` is non-empty).
        linked: ``(scenario_index, task_id)`` pairs actually inserted.
        skipped_low_confidence: Matches rejected because their confidence fell
            below the threshold.
        skipped_already_tagged: Scenario indices that already carry an
            ``@task:`` tag and were therefore left alone (idempotency).
        unmatched_scenarios: Scenario indices the caller supplied no match
            for (or only below-threshold matches for).
        unmatched_tasks: Task IDs with no scenario match in the supplied
            mapping.
        confidence_threshold: Threshold used for this run.
        rewritten: True iff the file was actually written to disk.
        summary: Human-readable one-line summary for printing after the phase.
    """

    path: Path
    linked: List[Tuple[int, str]] = field(default_factory=list)
    skipped_low_confidence: List[Tuple[int, str, float]] = field(default_factory=list)
    skipped_already_tagged: List[int] = field(default_factory=list)
    unmatched_scenarios: List[int] = field(default_factory=list)
    unmatched_tasks: List[str] = field(default_factory=list)
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD
    rewritten: bool = False
    summary: str = ""


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def parse_feature_file(path: Path) -> FeatureDocument:
    """Parse a Gherkin ``.feature`` file into a :class:`FeatureDocument`.

    Uses ``gherkin-official`` so we inherit the canonical parser rather than
    reinventing one — see the task brief's explicit requirement not to use a
    regex-based parser.

    Args:
        path: Path to the ``.feature`` file.

    Returns:
        A :class:`FeatureDocument`. If the file has no ``Feature:`` block the
        returned document has ``scenarios=[]`` and ``feature_name=""``; this
        lets the linker treat empty or malformed files as no-ops rather than
        raising.

    Raises:
        FileNotFoundError: If ``path`` doesn't exist.
        UnicodeDecodeError: If the file can't be read as UTF-8.
    """
    # Import locally so unrelated code paths don't pay the import cost (and so
    # tooling that inspects the module list doesn't flag gherkin as hot).
    from gherkin.parser import Parser

    # Decode bytes so line endings survive (read_text with newline=None would
    # translate \r\n → \n before we got a chance to detect the endings).
    raw_text = path.read_bytes().decode("utf-8")
    line_ending = _detect_line_ending(raw_text)
    trailing_newline = raw_text.endswith(line_ending) or raw_text.endswith("\n")
    lines = raw_text.splitlines()

    parser = Parser()
    gherkin_doc = parser.parse(raw_text)

    feature = gherkin_doc.get("feature") if isinstance(gherkin_doc, dict) else None
    if feature is None:
        return FeatureDocument(
            path=path,
            raw_text=raw_text,
            lines=lines,
            line_ending=line_ending,
            trailing_newline=trailing_newline,
            feature_name="",
            feature_tags=[],
            scenarios=[],
        )

    feature_name = feature.get("name", "") or ""
    feature_tags = [t["name"] for t in feature.get("tags", []) or []]

    scenarios: List[ScenarioInfo] = []
    for child in feature.get("children", []) or []:
        if "scenario" in child and child["scenario"] is not None:
            scenarios.append(
                _build_scenario_info(
                    index=len(scenarios),
                    raw=child["scenario"],
                    lines=lines,
                )
            )
        elif "rule" in child and child["rule"] is not None:
            for rule_child in child["rule"].get("children", []) or []:
                if "scenario" in rule_child and rule_child["scenario"] is not None:
                    scenarios.append(
                        _build_scenario_info(
                            index=len(scenarios),
                            raw=rule_child["scenario"],
                            lines=lines,
                        )
                    )
        # Backgrounds are intentionally skipped — they can't carry @task: tags.

    return FeatureDocument(
        path=path,
        raw_text=raw_text,
        lines=lines,
        line_ending=line_ending,
        trailing_newline=trailing_newline,
        feature_name=feature_name,
        feature_tags=feature_tags,
        scenarios=scenarios,
    )


def _build_scenario_info(
    index: int,
    raw: Dict[str, Any],
    lines: List[str],
) -> ScenarioInfo:
    """Convert a gherkin-official scenario dict to our ScenarioInfo."""
    scenario_line = int(raw["location"]["line"])
    indent = _indent_of(lines, scenario_line)

    raw_tags = raw.get("tags") or []
    tag_names = [t["name"] for t in raw_tags]
    tag_lines = [int(t["location"]["line"]) for t in raw_tags]
    tag_line: Optional[int] = min(tag_lines) if tag_lines else None
    tag_indent: Optional[str] = _indent_of(lines, tag_line) if tag_line else None

    step_texts: List[str] = []
    for step in raw.get("steps") or []:
        keyword = (step.get("keyword") or "").rstrip()
        text = step.get("text") or ""
        step_texts.append(f"{keyword}{text}".strip() if keyword else text.strip())

    return ScenarioInfo(
        index=index,
        name=raw.get("name") or "",
        keyword=(raw.get("keyword") or "Scenario").strip(),
        description=(raw.get("description") or "").strip(),
        steps=step_texts,
        line=scenario_line,
        indent=indent,
        tags=tag_names,
        tag_line=tag_line,
        tag_indent=tag_indent,
    )


def _indent_of(lines: List[str], line_1based: Optional[int]) -> str:
    """Return the leading whitespace of ``lines[line_1based-1]``, or ``""``."""
    if line_1based is None or line_1based < 1 or line_1based > len(lines):
        return ""
    # ``[ \t]*`` always matches — even against an empty string — so re.match
    # returns a match object here unconditionally.
    return re.match(r"[ \t]*", lines[line_1based - 1]).group(0)


def _detect_line_ending(text: str) -> str:
    """Return the file's dominant line ending (``"\\r\\n"`` or ``"\\n"``)."""
    crlf = text.count("\r\n")
    lf = text.count("\n") - crlf
    return "\r\n" if crlf > lf else "\n"


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


def existing_task_tags(doc: FeatureDocument) -> Dict[int, str]:
    """Return ``{scenario_index: task_id}`` for scenarios already tagged.

    Scanned from the parsed tags, not a regex over the raw text, so a
    ``@task:`` substring inside a step description can't be mistaken for a
    tag. If a scenario carries multiple ``@task:`` tags the first one wins
    — but that shape is invalid by convention anyway, and we never create it.
    """
    result: Dict[int, str] = {}
    for scenario in doc.scenarios:
        for tag in scenario.tags:
            if tag.startswith(_TASK_TAG_PREFIX):
                task_id = tag[len(_TASK_TAG_PREFIX):].strip()
                if task_id and scenario.index not in result:
                    result[scenario.index] = task_id
    return result


# ---------------------------------------------------------------------------
# Matching request construction
# ---------------------------------------------------------------------------


def build_matching_request(
    doc: FeatureDocument,
    tasks: Iterable[TaskInfo],
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    skip_already_tagged: bool = True,
) -> MatchingRequest:
    """Build the JSON-serialisable payload for the scenario→task matching agent.

    The subagent receives only the shape and content the decision requires:
    scenario index/keyword/name/description/steps and each task's ID/title/
    description/ACs. Frontmatter fields unrelated to matching (wave, priority,
    conductor_workspace) are deliberately excluded.

    When ``skip_already_tagged`` is True scenarios that already carry an
    ``@task:`` tag are omitted from the payload entirely, so the agent isn't
    asked to re-decide something the file already records. The result of this
    pass stays idempotent under re-runs.

    Args:
        doc: Parsed feature document.
        tasks: Iterable of :class:`TaskInfo` values — typically the tasks
            /feature-plan just created.
        confidence_threshold: Surfaced in the request so the agent knows what
            bar its matches need to clear.
        skip_already_tagged: Whether to omit scenarios with an existing
            ``@task:`` tag from the ``scenarios`` payload.
    """
    already = existing_task_tags(doc) if skip_already_tagged else {}

    scenarios_payload: List[Dict[str, Any]] = []
    for scenario in doc.scenarios:
        if scenario.index in already:
            continue
        scenarios_payload.append(
            {
                "index": scenario.index,
                "keyword": scenario.keyword,
                "name": scenario.name,
                "description": scenario.description,
                "steps": list(scenario.steps),
                "existing_tags": [
                    t for t in scenario.tags if not t.startswith(_TASK_TAG_PREFIX)
                ],
            }
        )

    tasks_payload: List[Dict[str, Any]] = []
    for task in tasks:
        tasks_payload.append(
            {
                "task_id": task.task_id,
                "title": task.title,
                "description": task.description,
                "acceptance_criteria": list(task.acceptance_criteria),
            }
        )

    return MatchingRequest(
        feature_path=str(doc.path),
        feature_name=doc.feature_name,
        confidence_threshold=confidence_threshold,
        scenarios=scenarios_payload,
        tasks=tasks_payload,
    )


# ---------------------------------------------------------------------------
# Applying a mapping
# ---------------------------------------------------------------------------


def apply_mapping(
    path: Path,
    matches: Iterable[TaskMatch],
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    dry_run: bool = False,
) -> LinkingResult:
    """Apply scenario-to-task matches to ``path`` and atomically rewrite the file.

    Idempotency and safety rules:

    - Scenarios already carrying an ``@task:`` tag are left alone and listed
      under ``skipped_already_tagged``.
    - Matches with ``confidence < confidence_threshold`` are listed under
      ``skipped_low_confidence``.
    - When multiple matches target the same scenario, the highest-confidence
      one is kept (ties resolved by input order — first seen wins).
    - The rewrite is atomic: we write to a temp file in the same directory and
      ``os.replace`` onto the target. Partial writes can't corrupt the source.
    - ``dry_run=True`` returns the result without touching the file.

    Tag insertion: a new line ``<indent>@task:<TASK-ID>`` is inserted
    immediately above the scenario's top-most existing tag line (or directly
    above the ``Scenario:`` keyword line if no tags exist). Existing lines are
    preserved verbatim — we only insert new lines, never rewrite old ones.

    Args:
        path: The ``.feature`` file to rewrite.
        matches: Candidate matches from the matching subagent.
        confidence_threshold: Minimum confidence for auto-application.
        dry_run: When True, compute the result but don't write.

    Returns:
        A :class:`LinkingResult` describing what was (or would be) applied.
    """
    doc = parse_feature_file(path)
    n_scenarios = len(doc.scenarios)

    result = LinkingResult(path=path, confidence_threshold=confidence_threshold)

    # Bucket matches, dropping below-threshold ones and picking the highest-
    # confidence match per scenario when duplicates arrive.
    best_by_scenario: Dict[int, TaskMatch] = {}
    seen_tasks: List[str] = []
    for match in matches:
        if match.task_id not in seen_tasks:
            seen_tasks.append(match.task_id)
        if not (0 <= match.scenario_index < n_scenarios):
            # Scenario index doesn't correspond to any scenario — treat as
            # low-confidence so it shows up in the report without crashing.
            result.skipped_low_confidence.append(
                (match.scenario_index, match.task_id, match.confidence)
            )
            continue
        if match.confidence < confidence_threshold:
            result.skipped_low_confidence.append(
                (match.scenario_index, match.task_id, match.confidence)
            )
            continue
        current = best_by_scenario.get(match.scenario_index)
        if current is None or match.confidence > current.confidence:
            best_by_scenario[match.scenario_index] = match

    already = existing_task_tags(doc)

    # Compute insertions and categorise outcomes.
    insertions: List[Tuple[int, str]] = []  # (line_1based_to_insert_before, new_line)
    applied_task_ids: set[str] = set()
    for idx, match in sorted(best_by_scenario.items()):
        if idx in already:
            # Idempotent: already tagged with some @task: — don't duplicate.
            # Not a match we "used"; don't record as linked or skipped.
            continue
        scenario = doc.scenarios[idx]
        indent = scenario.tag_indent if scenario.tag_indent is not None else scenario.indent
        new_line = f"{indent}{_TASK_TAG_PREFIX}{match.task_id}"
        insert_at = scenario.tag_line if scenario.tag_line is not None else scenario.line
        insertions.append((insert_at, new_line))
        result.linked.append((idx, match.task_id))
        applied_task_ids.add(match.task_id)

    # Already-tagged scenarios.
    result.skipped_already_tagged = sorted(already.keys())

    # Unmatched scenarios: those with no match bucketed and not already tagged.
    matched_indices = set(best_by_scenario.keys()) | set(already.keys())
    result.unmatched_scenarios = [
        i for i in range(n_scenarios) if i not in matched_indices
    ]

    # Unmatched tasks: tasks present in the matches iterable but whose best
    # match either lost to a higher-confidence alternative or never cleared
    # the threshold. We also include tasks that ended up matched to an
    # already-tagged scenario (redundant, but we surface it).
    applied_plus_preexisting = applied_task_ids | set(already.values())
    result.unmatched_tasks = [
        t for t in seen_tasks if t not in applied_plus_preexisting
    ]

    if insertions and not dry_run:
        _rewrite_with_insertions(doc, insertions)
        result.rewritten = True
    elif not insertions:
        result.rewritten = False
    else:
        result.rewritten = False  # dry_run

    result.summary = _format_summary(result, n_scenarios)
    return result


def _rewrite_with_insertions(
    doc: FeatureDocument,
    insertions: List[Tuple[int, str]],
) -> None:
    """Atomically rewrite ``doc.path`` with tag lines inserted.

    Sorts insertions by target line descending so earlier lines don't shift
    under later ones, then writes to a tempfile alongside the target and
    ``os.replace``s atomically.
    """
    output = list(doc.lines)
    # Descending order so inserting at line N doesn't move the line-M (M<N)
    # insertion's target out from under us.
    for insert_at, new_line in sorted(insertions, key=lambda x: x[0], reverse=True):
        zero_based = max(0, insert_at - 1)
        output.insert(zero_based, new_line)

    content = doc.line_ending.join(output)
    if doc.trailing_newline:
        content += doc.line_ending

    target = doc.path
    # Write tempfile in the same directory so os.replace is cross-filesystem-safe.
    fd, tmp_path_str = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=str(target.parent),
    )
    tmp_path = Path(tmp_path_str)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as tmp:
            tmp.write(content)
        os.replace(tmp_path, target)
    except Exception:
        # Clean up the tempfile if something went wrong before os.replace.
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise


def _format_summary(result: LinkingResult, scenario_count: int) -> str:
    """Build the one-line summary the caller prints after the phase runs."""
    linked = len(result.linked)
    low_conf = len(result.skipped_low_confidence)
    already = len(result.skipped_already_tagged)
    parts = [
        f"linked {linked} scenario(s) to task(s)",
        f"{already} already tagged",
        f"{low_conf} below threshold ({result.confidence_threshold:.2f})",
    ]
    if result.unmatched_scenarios:
        parts.append(f"{len(result.unmatched_scenarios)} untagged")
    return "; ".join(parts) + f" (of {scenario_count} total)"


__all__ = [
    # Data classes
    "ScenarioInfo",
    "FeatureDocument",
    "TaskInfo",
    "TaskMatch",
    "MatchingRequest",
    "LinkingResult",
    # Functions
    "parse_feature_file",
    "existing_task_tags",
    "build_matching_request",
    "apply_mapping",
    # Constants
    "DEFAULT_CONFIDENCE_THRESHOLD",
]

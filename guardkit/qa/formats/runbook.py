"""F11 · executable-runbook schema (LPA-11, LPA-22) — session B10.

Instance: a markdown runbook (model:
``lpa-platform-poc/docs/runbooks/RUNBOOK-gb10-voice-unified-2026-07.md`` and
``RUNBOOK-foundation-infrastructure.md``).

**F11 is deliberately markdown, not YAML** (the binding guardrail, WS2 §B10):
"executable by a human with no tooling — markdown first, machine conventions
second." So this format is validated as a set of MARKDOWN CONVENTIONS a human
reads and runs directly; the machine only checks that the load-bearing
conventions are present.

The conventions (a runbook instance MUST follow all of them):

1. A machine marker line (invisible when rendered):
   ``<!-- qa-format: runbook format_version: 1.0 -->``
2. A **Facts** header — a ``## Facts`` heading with ≥1 fact bullet of the form
   ``- **<claim>** — verified <YYYY-MM-DD> — <how>`` (a fact with no verified
   date or no "how" is not a fact).
3. **Typed phases** — each phase is a ``## Phase <n>: <title> — type: <t>``
   heading, ``<t>`` one of ``preflight|backup|change|discovery|verify|rollback|
   operator_handoff``.
4. **Every phase has an executable Pass check** — a ``**Pass:** <check>`` line in
   the phase body (**a runbook step without a pass check is a wish**). This is
   the load-bearing enforcement: the runbook executor refuses a phase with no
   pass check.

Conventions pinned by scope-design §2 (2026-07-07). Additions require a dated
note in that doc, never silent invention.
"""

from __future__ import annotations

import re
from typing import ClassVar, List

from guardkit.qa.formats.base import MarkdownFormat

#: The typed-phase vocabulary (scope-design §2 F11).
PHASE_TYPES = frozenset(
    {"preflight", "backup", "change", "discovery", "verify", "rollback", "operator_handoff"}
)

_FACTS_HEADING_RE = re.compile(r"^#{2,3}\s+Facts\b", re.IGNORECASE)
_HEADING_RE = re.compile(r"^#{1,6}\s+")
_PHASE_HEADING_RE = re.compile(r"^##\s+Phase\b[^\n]*", re.IGNORECASE)
_PHASE_TYPE_RE = re.compile(r"type:\s*([A-Za-z_]+)", re.IGNORECASE)
#: A fact bullet: "- **claim** — verified 2026-07-05 — how"
_FACT_RE = re.compile(
    r"^\s*[-*]\s+.*verified\s+(\d{4}-\d{2}-\d{2})\b.*\S", re.IGNORECASE
)
#: An executable pass check: "**Pass:** ..." / "Pass: ..." / "- Pass: ..."
_PASS_RE = re.compile(r"^\s*(?:[-*]\s*)?\*{0,2}Pass:\*{0,2}\s*(\S.*)$", re.IGNORECASE)


class Runbook(MarkdownFormat):
    """F11 executable runbook — markdown-convention format (WS2-B10).

    A runbook is a markdown document a human reads and runs directly. The
    validator only checks the load-bearing conventions:

      1. A machine marker (invisible when rendered):
         <!-- qa-format: runbook format_version: 1.0 -->
      2. A '## Facts' header with >=1 fact bullet:
         '- **<claim>** — verified <YYYY-MM-DD> — <how>'
      3. Typed phases: '## Phase <n>: <title> — type: <t>', <t> one of
         preflight|backup|change|discovery|verify|rollback|operator_handoff.
      4. Every phase carries an executable '**Pass:** <check>' line —
         a runbook step without a pass check is a wish (the executor refuses it).
    """

    FORMAT_KIND: ClassVar[str] = "runbook"
    CURRENT_FORMAT_VERSION: ClassVar[str] = "1.0"

    @classmethod
    def _validate_body(cls, text: str) -> List[str]:
        problems: List[str] = []
        lines = text.splitlines()

        # --- Facts header (convention 2) ---
        facts_idx = next(
            (i for i, ln in enumerate(lines) if _FACTS_HEADING_RE.match(ln)), None
        )
        if facts_idx is None:
            problems.append(
                "no '## Facts' header — a runbook must open with a facts header "
                "([{claim, verified_on, how}])"
            )
        else:
            fact_count = 0
            for ln in lines[facts_idx + 1 :]:
                if _HEADING_RE.match(ln):
                    break
                if _FACT_RE.match(ln):
                    fact_count += 1
                elif ln.strip().startswith(("-", "*")) and ln.strip():
                    # A bullet under Facts that is not a well-formed fact.
                    problems.append(
                        f"malformed fact (missing 'verified <YYYY-MM-DD>'): "
                        f"{ln.strip()[:70]!r}"
                    )
            if fact_count == 0:
                problems.append(
                    "the '## Facts' header has no well-formed fact bullet "
                    "('- **claim** — verified <YYYY-MM-DD> — how')"
                )

        # --- Typed phases + pass checks (conventions 3 & 4) ---
        phase_starts = [i for i, ln in enumerate(lines) if _PHASE_HEADING_RE.match(ln)]
        if not phase_starts:
            problems.append(
                "no '## Phase <n>: <title> — type: <t>' headings — a runbook needs "
                "at least one typed phase"
            )
        for pos, start in enumerate(phase_starts):
            heading = lines[start].strip()
            end = phase_starts[pos + 1] if pos + 1 < len(phase_starts) else len(lines)
            body = lines[start:end]

            type_match = _PHASE_TYPE_RE.search(heading)
            if type_match is None:
                problems.append(
                    f"phase {heading[:60]!r} has no 'type:' — declare one of "
                    f"{sorted(PHASE_TYPES)}"
                )
            elif type_match.group(1).lower() not in PHASE_TYPES:
                problems.append(
                    f"phase {heading[:60]!r} has unknown type "
                    f"{type_match.group(1)!r} (allowed: {sorted(PHASE_TYPES)})"
                )

            has_pass = any(_PASS_RE.match(ln) for ln in body[1:])
            if not has_pass:
                problems.append(
                    f"phase {heading[:60]!r} has no executable '**Pass:**' check — "
                    f"a runbook step without a pass check is a wish (the executor "
                    f"refuses it)"
                )

        return problems

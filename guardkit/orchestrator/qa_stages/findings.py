"""Findings from the deeper stages — filed as task-shaped records, NON-blocking.

**Guardrail (binding):** findings FILE as tasks; they do NOT block in v1. A
surviving mutant or a raw-error leak is written as a durable, triage-ready
record under ``qa/findings/`` — it does not fail a build, reject a turn, or gate
autobuild (the Coach does not consume this stage in v1). The gate-vs-advisory
verdict this session records (WS2 §B6 STATUS) is exactly the decision that these
stay advisory in v1.

The records are deliberately task-shaped (title / class / evidence / suggested
pin) so a human — or a later Coach, if the stage is ever promoted — can triage
them directly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Literal, Sequence

FindingKind = Literal["mutation-survivor", "boundary-leak", "boundary-accept"]


@dataclass
class Finding:
    """One advisory finding from a deeper stage."""

    kind: FindingKind
    subject: str          # task id or seam id the finding is about
    site: str             # file:line, hunk id, or probe-input label
    summary: str
    evidence: str = ""
    suggested_pin: str = ""

    def slug(self) -> str:
        raw = f"{self.kind}-{self.subject}-{self.site}"
        return re.sub(r"[^a-zA-Z0-9]+", "-", raw).strip("-").lower()[:80]

    def to_markdown(self, *, date: str) -> str:
        lines = [
            f"# QA finding ({self.kind}) — {self.subject}",
            "",
            f"- **Filed:** {date}",
            f"- **Class:** {self.kind}",
            f"- **Subject:** {self.subject}",
            f"- **Site:** {self.site}",
            "- **Blocking:** no (v1 advisory — WS2 §B6; the Coach does not consume this stage)",
            "",
            "## What",
            "",
            self.summary,
        ]
        if self.evidence:
            lines += ["", "## Evidence", "", "```", self.evidence.strip(), "```"]
        if self.suggested_pin:
            lines += ["", "## Suggested pin", "", self.suggested_pin]
        lines.append("")
        return "\n".join(lines)


def write_findings(
    findings: Sequence[Finding],
    repo_root: Path,
    *,
    date: str,
    subdir: str = "qa/findings",
) -> List[Path]:
    """Write each finding as a task-shaped markdown record; return the paths.

    NON-blocking by construction: this only writes files and returns paths. The
    caller (CLI) reports them and exits 0 (advisory). Idempotent-ish: a
    same-day, same-slug finding overwrites its own record rather than piling up.
    """
    out_dir = Path(repo_root) / subdir
    out_dir.mkdir(parents=True, exist_ok=True)
    written: List[Path] = []
    for finding in findings:
        path = out_dir / f"{date}-{finding.slug()}.md"
        path.write_text(finding.to_markdown(date=date), encoding="utf-8")
        written.append(path)
    return written

"""F5 · evidence emitter + index (LPA-07) — WS2 session B3.

One responsibility:

- **Emit the F5 index automatically.** As gates run and produce assertions that
  carry ``evidence_ref``s (screenshots/traces), the collector turns them into
  ``EvidenceEntry`` rows and writes an ``EVIDENCE.yaml`` inside the run's
  evidence dir — validated against the F5 schema before it lands, so the runner
  never writes an invalid index.

The F5 schema deliberately permits a null ``inspected_by``/``verdict`` (an index
legitimately exists BEFORE inspection). The refusal — "no PASS verdict while a
key artifact is uninspected" — is the verdict step's (B4); B3 emits the index
with ``inspected_by=None``.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Sequence

import yaml

from guardkit.qa.formats.evidence_index import EvidenceEntry, EvidenceIndex
from guardkit.qa.formats.gate_registry import GateResult

#: Filename of the F5 index, living inside the evidence dir it describes.
EVIDENCE_INDEX_NAME = "EVIDENCE.yaml"


def ensure_evidence_dir(base_dir: Path, run_id: str) -> Path:
    """Create (and return) the evidence dir for a run (``<base>/<run_id>/``).

    Always created — "evidence dirs produced automatically" (B3 gate). The dir
    may end up empty (an environment_fail short-circuit captured no artifacts);
    an empty dir with no index is honest (no artifacts → no index).
    """
    evidence_dir = base_dir / run_id
    evidence_dir.mkdir(parents=True, exist_ok=True)
    return evidence_dir


class EvidenceCollector:
    """Accumulates F5 evidence entries across a run."""

    def __init__(self) -> None:
        self._entries: List[EvidenceEntry] = []

    def __len__(self) -> int:
        return len(self._entries)

    @property
    def entries(self) -> List[EvidenceEntry]:
        return list(self._entries)

    def add(
        self,
        artifact: str,
        checkpoint_or_assertion_id: str,
        description: str,
        *,
        inspected_by: Optional[str] = None,
        verdict: Optional[str] = None,
    ) -> None:
        self._entries.append(
            EvidenceEntry(
                artifact=artifact,
                checkpoint_or_assertion_id=checkpoint_or_assertion_id,
                description=description,
                inspected_by=inspected_by,
                verdict=verdict,
            )
        )

    def add_from_gate_results(self, gate_results: Sequence[GateResult]) -> None:
        """Harvest every assertion that carries an ``evidence_ref`` into an entry.

        ``inspected_by``/``verdict`` are left null — v1 does not run the vision
        step (attended). An assertion with no ``evidence_ref`` produces no
        entry (there is no artifact to index).
        """
        for gate in gate_results:
            for assertion in gate.assertions:
                if not assertion.evidence_ref:
                    continue
                observed = assertion.observed or ""
                expected = assertion.expected or ""
                desc = f"{gate.gate_id}/{assertion.id} [{assertion.status}]"
                if expected or observed:
                    desc += f": expected {expected!r}, observed {observed!r}"
                self.add(
                    artifact=assertion.evidence_ref,
                    checkpoint_or_assertion_id=assertion.id,
                    description=desc,
                )

    def write_index(self, evidence_dir: Path) -> Optional[Path]:
        """Write ``EVIDENCE.yaml`` into ``evidence_dir`` if there are entries.

        Returns the index path, or None when there is nothing to index (no
        artifacts captured — an empty index is invalid by F5 and would be
        dishonest to synthesize).
        """
        if not self._entries:
            return None
        index = EvidenceIndex(
            format_version=EvidenceIndex.CURRENT_FORMAT_VERSION,
            entries=self._entries,
        )
        # model_dump then dump to YAML (human-readable/diffable, per F5).
        payload = index.model_dump(mode="json")
        out = evidence_dir / EVIDENCE_INDEX_NAME
        out.write_text(
            yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        return out

"""QA deeper stages (WS2 session B6) — mutation, boundary probes, round-trips.

Standalone ``guardkit qa`` stages (scope-design §3.8, ST-05/ST-06/ST-13). The
Coach does NOT consume them in v1 and they make no autobuild behavioural change:

- ``mutate`` (ST-05) — break the key behaviour in a THROWAWAY sandbox; a mutant
  that survives its own tests is a proven coverage-hole finding.
- ``probe-boundaries`` (ST-06) — feed non-conforming inputs at an F6 seam; a raw
  error leaking past the seam's sealed set is a finding.
- round-trips (ST-13) — a technique library of judge-free helpers, NOT a gate.

Findings file as task-shaped records and do not block in v1 (the gate-vs-advisory
verdict recorded in WS2 §B6 STATUS).
"""

from __future__ import annotations

from guardkit.orchestrator.qa_stages.boundary import (
    BoundaryProbeResult,
    ProbeInput,
    ProbeOutcome,
    ProbeTarget,
    UnconfiguredProbeTarget,
    default_input_battery,
    load_seam_ids,
    run_boundary_probes,
)
from guardkit.orchestrator.qa_stages.errors import (
    BoundaryProbeError,
    MutationError,
    QAStageError,
    QAStageStubError,
)
from guardkit.orchestrator.qa_stages.findings import Finding, write_findings
from guardkit.orchestrator.qa_stages.mutation import (
    Mutant,
    MutantResult,
    MutationCampaignResult,
    TestOutcome,
    make_pytest_runner,
    revert_hunks_operator,
    run_mutation_campaign,
    split_diff_by_file,
    strip_auth_header_operator,
)
from guardkit.orchestrator.qa_stages.roundtrip import (
    RoundTripResult,
    render_parse,
    synthesize_transcribe,
    write_reload,
)
from guardkit.orchestrator.qa_stages.sandbox import MutationSandbox

__all__ = [
    # errors
    "QAStageError",
    "QAStageStubError",
    "MutationError",
    "BoundaryProbeError",
    # mutation
    "MutationSandbox",
    "Mutant",
    "MutantResult",
    "MutationCampaignResult",
    "TestOutcome",
    "make_pytest_runner",
    "run_mutation_campaign",
    "strip_auth_header_operator",
    "revert_hunks_operator",
    "split_diff_by_file",
    # boundary
    "ProbeTarget",
    "UnconfiguredProbeTarget",
    "ProbeInput",
    "ProbeOutcome",
    "BoundaryProbeResult",
    "run_boundary_probes",
    "default_input_battery",
    "load_seam_ids",
    # roundtrip
    "RoundTripResult",
    "render_parse",
    "synthesize_transcribe",
    "write_reload",
    # findings
    "Finding",
    "write_findings",
]

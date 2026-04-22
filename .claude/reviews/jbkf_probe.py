"""Ad-hoc probe for TASK-BDD-JBKF.

Invokes bdd_runner.run_bdd_for_task() against the jarvis working copy for two
tagged task IDs, using the throwaway .venv-r2-probe/ python interpreter. Dumps
the resulting BDDResult (or None + reason) as JSON to stdout so the evidence
file can cite it verbatim.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

GUARDKIT_ROOT = Path("/Users/richardwoollcott/Projects/appmilla_github/guardkit")
JARVIS_ROOT = Path("/Users/richardwoollcott/Projects/appmilla_github/jarvis")
JARVIS_PY = JARVIS_ROOT / ".venv-r2-probe/bin/python"
FEATURES_SUBDIR = "features/project-scaffolding-supervisor-sessions"

sys.path.insert(0, str(GUARDKIT_ROOT))

from guardkit.orchestrator.quality_gates.bdd_runner import (  # noqa: E402
    find_feature_files_with_tag,
    has_pytest_bdd,
    run_bdd_for_task,
    task_tag,
)


def probe(task_id: str) -> dict:
    features_dir = JARVIS_ROOT / FEATURES_SUBDIR
    tag = task_tag(task_id)
    found = find_feature_files_with_tag(features_dir, tag)
    pytest_bdd_importable = has_pytest_bdd(python_executable=str(JARVIS_PY))

    result = run_bdd_for_task(
        task_id=task_id,
        worktree_path=JARVIS_ROOT,
        python_executable=str(JARVIS_PY),
        features_subdir=FEATURES_SUBDIR,
        timeout=120,
    )

    out: dict = {
        "task_id": task_id,
        "tag": tag,
        "features_dir": str(features_dir),
        "tagged_files_found": [str(p.relative_to(JARVIS_ROOT)) for p in found],
        "pytest_bdd_importable_in_target_env": pytest_bdd_importable,
        "bdd_result_is_none": result is None,
    }
    if result is not None:
        out["bdd_result"] = result.to_dict()
        out["raw_output_tail"] = (result.raw_output or "")[-2000:]
    return out


def main() -> None:
    task_ids = ["TASK-J001-001", "TASK-J001-006"]
    report = {"probes": [probe(t) for t in task_ids]}
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()

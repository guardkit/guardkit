---
id: TASK-FP002-006
title: Warnings Extractor and Seed Script Generator
task_type: feature
parent_review: TASK-REV-FP002
feature_id: FEAT-FP-002
wave: 2
implementation_mode: task-work
complexity: 3
complexity_score: 3
type: implementation
domain_tags:
  - warnings
  - graphiti-seeding
  - shell-scripts
files_to_create:
  - guardkit/planning/warnings_extractor.py
  - guardkit/planning/seed_script_generator.py
  - tests/unit/test_warnings_extractor.py
  - tests/unit/test_seed_script_generator.py
files_to_modify: []
files_not_to_touch:
  - scripts/
  - docs/warnings/
dependencies:
  - TASK-FP002-001
  - TASK-FP002-003
relevant_decisions:
  - D7
turn_budget:
  expected: 1
  max: 3
graphiti_context_budget: 2000
---

# TASK-FP002-006: Warnings Extractor and Seed Script Generator

## Description

Create two small modules:
1. `warnings_extractor.py` — extracts warnings/constraints from `ParsedSpec` into a standalone markdown file for Graphiti seeding
2. `seed_script_generator.py` — generates an executable bash script (`scripts/seed-FEAT-XXX.sh`) containing all `guardkit graphiti add-context` commands for ADRs, spec, and warnings

## Acceptance Criteria (Machine-Verifiable)

- [ ] File exists: `guardkit/planning/warnings_extractor.py`
- [ ] File exists: `guardkit/planning/seed_script_generator.py`
- [ ] File exists: `tests/unit/test_warnings_extractor.py`
- [ ] File exists: `tests/unit/test_seed_script_generator.py`
- [ ] `extract_warnings(warnings, feature_id, output_dir)` creates warnings markdown file at `{output_dir}/FEAT-XXX-warnings.md`
- [ ] `generate_seed_script(feature_id, adr_paths, spec_path, warnings_path, output_dir)` creates executable bash script
- [ ] Seed script includes: `guardkit graphiti status`, `guardkit graphiti add-context` for each ADR, spec, and warnings file
- [ ] Seed script uses `#!/usr/bin/env bash` shebang and `set -e`
- [ ] Seed script is idempotent (safe to run multiple times)
- [ ] Warnings markdown includes feature_id in the title and lists all warnings as bullet points
- [ ] Tests pass: `pytest tests/unit/test_warnings_extractor.py tests/unit/test_seed_script_generator.py -v`
- [ ] Lint passes: `ruff check guardkit/planning/warnings_extractor.py guardkit/planning/seed_script_generator.py`

## Coach Validation Commands

```bash
pytest tests/unit/test_warnings_extractor.py tests/unit/test_seed_script_generator.py -v
ruff check guardkit/planning/warnings_extractor.py guardkit/planning/seed_script_generator.py
python -c "from guardkit.planning.warnings_extractor import extract_warnings; print('OK')"
python -c "from guardkit.planning.seed_script_generator import generate_seed_script; print('OK')"
```

## Player Constraints

- Create files ONLY in `guardkit/planning/` and `tests/unit/`
- Tests must use `tmp_path` for all file output
- Seed script must use `#!/usr/bin/env bash` shebang
- Seed script must have `set -e` for fail-fast behaviour

## Implementation Notes (Prescriptive)

**warnings_extractor.py:**
```python
from pathlib import Path

def extract_warnings(
    warnings: list[str],
    feature_id: str,
    output_dir: Path = Path("docs/warnings"),
) -> Path | None:
    """Extract warnings into a separate markdown file for Graphiti seeding.
    Returns None if no warnings to extract."""
```

Output format:
```markdown
# Warnings & Constraints: {feature_id}

{feature_id} has the following warnings and constraints that must be observed during implementation:

- {warning_1}
- {warning_2}
...
```

**seed_script_generator.py:**
```python
from pathlib import Path

def generate_seed_script(
    feature_id: str,
    adr_paths: list[Path],
    spec_path: Path,
    warnings_path: Path | None = None,
    output_dir: Path = Path("scripts"),
) -> Path:
    """Generate bash script for Graphiti seeding."""
```

Script template:
```bash
#!/usr/bin/env bash
set -e

echo "=== Seeding {feature_id}: {feature_name} ==="

# 1. Check Graphiti status
guardkit graphiti status

# 2. Seed ADR files
echo "Seeding ADR files..."
{adr_commands}

# 3. Seed feature specification
echo "Seeding feature specification..."
guardkit graphiti add-context {spec_path}

# 4. Seed warnings (if present)
{warnings_section}

# 5. Verify
echo "Verifying seeding..."
guardkit graphiti verify --verbose

echo "=== Seeding complete ==="
```

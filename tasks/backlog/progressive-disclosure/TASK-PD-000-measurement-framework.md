---
id: TASK-PD-000
title: Establish before/after measurement framework for progressive disclosure
status: backlog
created: 2025-12-04T10:00:00Z
updated: 2025-12-04T10:00:00Z
priority: critical
tags: [progressive-disclosure, phase-0, measurement, validation, blog-content]
complexity: 4
blocked_by: []
blocks: [TASK-PD-001]
review_task: TASK-REV-426C
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Establish before/after measurement framework for progressive disclosure

## Phase

**Phase 0: Pre-Implementation Baseline** (MUST COMPLETE FIRST)

## Purpose

Capture comprehensive before/after metrics to:
1. **Validate** the progressive disclosure implementation achieves target reductions
2. **Generate blog content** telling the GuardKit optimization story
3. **Provide competitive benchmarks** vs BMAD/SpecKit

## Reference Implementation

Use the **Products feature** implementation pattern from VM testing:
- **TASK-IMP-674A-PREREQ**: FastAPI infrastructure setup (complexity: 3)
- **TASK-IMP-674A**: Products CRUD implementation (complexity: 5)

This pattern is ideal because:
- ✅ Representative of real-world work (CRUD feature)
- ✅ Uses multiple agents (python-api-specialist, test-verifier)
- ✅ Already proven to work end-to-end
- ✅ Minimal setup effort (reuse existing tasks)
- ✅ 103 tests, 98% coverage - substantial implementation

## Measurement Script

Create `scripts/measure-token-usage.py`:

```python
#!/usr/bin/env python3
"""
Measure token usage for progressive disclosure validation.

Usage:
    # Before progressive disclosure
    python3 scripts/measure-token-usage.py --baseline

    # After progressive disclosure
    python3 scripts/measure-token-usage.py --after

    # Compare results
    python3 scripts/measure-token-usage.py --compare
"""

import json
import os
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

@dataclass
class TokenMeasurement:
    """Single measurement point."""
    timestamp: str
    measurement_type: str  # "baseline" or "after"

    # File sizes (bytes)
    claude_md_size: int
    global_agents_total: int
    global_agents_count: int
    template_agents_total: int
    template_agents_count: int

    # Calculated metrics
    total_context_bytes: int
    avg_agent_size: int

    # Task-specific (from actual execution)
    task_id: Optional[str] = None
    task_tokens_input: Optional[int] = None
    task_tokens_output: Optional[int] = None
    task_duration_seconds: Optional[float] = None


def measure_file_sizes() -> dict:
    """Measure current file sizes."""
    base_path = Path.home() / ".agentecflow"

    # CLAUDE.md (from installed location)
    claude_md = base_path / "CLAUDE.md"
    claude_md_size = claude_md.stat().st_size if claude_md.exists() else 0

    # Global agents (excluding -ext files for core measurement)
    agents_path = base_path / "agents"
    global_agents = []
    for f in agents_path.glob("*.md"):
        if not f.stem.endswith("-ext"):
            global_agents.append(f.stat().st_size)

    # Template agents (fastapi-python for benchmark)
    template_path = base_path / "templates" / "fastapi-python" / "agents"
    template_agents = []
    if template_path.exists():
        for f in template_path.glob("*.md"):
            if not f.stem.endswith("-ext"):
                template_agents.append(f.stat().st_size)

    return {
        "claude_md_size": claude_md_size,
        "global_agents_total": sum(global_agents),
        "global_agents_count": len(global_agents),
        "template_agents_total": sum(template_agents),
        "template_agents_count": len(template_agents),
    }


def create_measurement(measurement_type: str) -> TokenMeasurement:
    """Create a measurement snapshot."""
    sizes = measure_file_sizes()
    total = sizes["claude_md_size"] + sizes["global_agents_total"] + sizes["template_agents_total"]
    agent_count = sizes["global_agents_count"] + sizes["template_agents_count"]

    return TokenMeasurement(
        timestamp=datetime.now().isoformat(),
        measurement_type=measurement_type,
        claude_md_size=sizes["claude_md_size"],
        global_agents_total=sizes["global_agents_total"],
        global_agents_count=sizes["global_agents_count"],
        template_agents_total=sizes["template_agents_total"],
        template_agents_count=sizes["template_agents_count"],
        total_context_bytes=total,
        avg_agent_size=total // agent_count if agent_count > 0 else 0,
    )


def save_measurement(measurement: TokenMeasurement, filename: str):
    """Save measurement to JSON file."""
    output_dir = Path("measurements")
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / filename
    with open(output_file, "w") as f:
        json.dump(asdict(measurement), f, indent=2)

    print(f"Saved measurement to {output_file}")


def load_measurement(filename: str) -> Optional[TokenMeasurement]:
    """Load measurement from JSON file."""
    output_file = Path("measurements") / filename
    if not output_file.exists():
        return None

    with open(output_file) as f:
        data = json.load(f)

    return TokenMeasurement(**data)


def compare_measurements(baseline: TokenMeasurement, after: TokenMeasurement) -> dict:
    """Compare two measurements and calculate improvements."""
    def pct_reduction(before: int, after: int) -> float:
        if before == 0:
            return 0.0
        return ((before - after) / before) * 100

    return {
        "claude_md_reduction_pct": pct_reduction(baseline.claude_md_size, after.claude_md_size),
        "global_agents_reduction_pct": pct_reduction(baseline.global_agents_total, after.global_agents_total),
        "template_agents_reduction_pct": pct_reduction(baseline.template_agents_total, after.template_agents_total),
        "total_context_reduction_pct": pct_reduction(baseline.total_context_bytes, after.total_context_bytes),
        "bytes_saved": baseline.total_context_bytes - after.total_context_bytes,
        "kb_saved": (baseline.total_context_bytes - after.total_context_bytes) / 1024,
    }


def print_measurement(m: TokenMeasurement):
    """Print measurement in human-readable format."""
    print(f"\n{'='*60}")
    print(f"Token Measurement: {m.measurement_type.upper()}")
    print(f"Timestamp: {m.timestamp}")
    print(f"{'='*60}\n")

    print(f"CLAUDE.md:           {m.claude_md_size:>10,} bytes ({m.claude_md_size/1024:.1f} KB)")
    print(f"Global Agents:       {m.global_agents_total:>10,} bytes ({m.global_agents_count} files)")
    print(f"Template Agents:     {m.template_agents_total:>10,} bytes ({m.template_agents_count} files)")
    print(f"{'─'*60}")
    print(f"TOTAL CONTEXT:       {m.total_context_bytes:>10,} bytes ({m.total_context_bytes/1024:.1f} KB)")
    print(f"Avg Agent Size:      {m.avg_agent_size:>10,} bytes ({m.avg_agent_size/1024:.1f} KB)")


def print_comparison(baseline: TokenMeasurement, after: TokenMeasurement, comparison: dict):
    """Print comparison report."""
    print(f"\n{'='*60}")
    print("PROGRESSIVE DISCLOSURE RESULTS")
    print(f"{'='*60}\n")

    print(f"{'Component':<25} {'Before':>12} {'After':>12} {'Reduction':>12}")
    print(f"{'─'*60}")

    print(f"{'CLAUDE.md':<25} {baseline.claude_md_size/1024:>10.1f}KB {after.claude_md_size/1024:>10.1f}KB {comparison['claude_md_reduction_pct']:>10.1f}%")
    print(f"{'Global Agents':<25} {baseline.global_agents_total/1024:>10.1f}KB {after.global_agents_total/1024:>10.1f}KB {comparison['global_agents_reduction_pct']:>10.1f}%")
    print(f"{'Template Agents':<25} {baseline.template_agents_total/1024:>10.1f}KB {after.template_agents_total/1024:>10.1f}KB {comparison['template_agents_reduction_pct']:>10.1f}%")
    print(f"{'─'*60}")
    print(f"{'TOTAL':<25} {baseline.total_context_bytes/1024:>10.1f}KB {after.total_context_bytes/1024:>10.1f}KB {comparison['total_context_reduction_pct']:>10.1f}%")

    print(f"\n💾 Total Savings: {comparison['kb_saved']:.1f} KB ({comparison['bytes_saved']:,} bytes)")

    # Target validation
    target = 55.0  # 55% target reduction
    if comparison['total_context_reduction_pct'] >= target:
        print(f"\n✅ TARGET MET: {comparison['total_context_reduction_pct']:.1f}% ≥ {target}%")
    else:
        print(f"\n❌ TARGET MISSED: {comparison['total_context_reduction_pct']:.1f}% < {target}%")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Measure token usage for progressive disclosure validation")
    parser.add_argument("--baseline", action="store_true", help="Capture baseline measurement")
    parser.add_argument("--after", action="store_true", help="Capture after measurement")
    parser.add_argument("--compare", action="store_true", help="Compare baseline vs after")
    parser.add_argument("--print-baseline", action="store_true", help="Print baseline measurement")
    parser.add_argument("--print-after", action="store_true", help="Print after measurement")

    args = parser.parse_args()

    if args.baseline:
        measurement = create_measurement("baseline")
        save_measurement(measurement, "baseline.json")
        print_measurement(measurement)

    elif args.after:
        measurement = create_measurement("after")
        save_measurement(measurement, "after.json")
        print_measurement(measurement)

    elif args.compare:
        baseline = load_measurement("baseline.json")
        after = load_measurement("after.json")

        if not baseline:
            print("❌ No baseline measurement found. Run with --baseline first.")
            return 1

        if not after:
            print("❌ No after measurement found. Run with --after first.")
            return 1

        comparison = compare_measurements(baseline, after)
        print_comparison(baseline, after, comparison)

        # Save comparison report
        output_file = Path("measurements") / "comparison-report.json"
        with open(output_file, "w") as f:
            json.dump({
                "baseline": asdict(baseline),
                "after": asdict(after),
                "comparison": comparison,
            }, f, indent=2)
        print(f"\nFull report saved to {output_file}")

    elif args.print_baseline:
        baseline = load_measurement("baseline.json")
        if baseline:
            print_measurement(baseline)
        else:
            print("No baseline measurement found.")

    elif args.print_after:
        after = load_measurement("after.json")
        if after:
            print_measurement(after)
        else:
            print("No after measurement found.")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
```

## Benchmark Task Template

Create reusable benchmark task in `tasks/templates/benchmark-products-feature.md`:

```yaml
---
id: TASK-BENCH-{hash}
title: Benchmark - Products feature implementation
status: backlog
priority: high
complexity: 5
task_type: benchmark
measurement_run: {baseline|after}
---

# Benchmark: Products Feature Implementation

## Purpose

Standardized benchmark task for measuring progressive disclosure impact.

## Procedure

1. **Fresh VM/Container**:
   ```bash
   # macOS VM or Docker container
   mkdir -p ~/benchmark-test && cd ~/benchmark-test
   ```

2. **Install GuardKit**:
   ```bash
   git clone https://github.com/appmilla/guardkit.git
   cd guardkit
   ./installer/scripts/install.sh
   ```

3. **Initialize Project**:
   ```bash
   mkdir -p ~/benchmark-test/api-project && cd ~/benchmark-test/api-project
   guardkit init fastapi-python
   ```

4. **Capture Baseline** (before progressive disclosure):
   ```bash
   python3 ~/benchmark-test/guardkit/scripts/measure-token-usage.py --baseline
   ```

5. **Execute Benchmark Tasks**:
   ```bash
   # Task 1: Infrastructure (complexity 3)
   /task-create "Initialize FastAPI application infrastructure" prefix:BENCH
   /task-work TASK-BENCH-XXXX

   # Task 2: Products feature (complexity 5)
   /task-create "Create Products CRUD feature" prefix:BENCH
   /task-work TASK-BENCH-YYYY
   ```

6. **Record Metrics**:
   - Total session tokens (from Claude Code stats)
   - Wall-clock time for each task
   - Number of agent invocations
   - Any errors or retries

## Expected Outcomes

### Baseline (Before)
- CLAUDE.md: ~20KB
- Global agents: ~200KB (19 files)
- Template agents: ~50KB (8 files)
- Total context: ~270KB

### After Progressive Disclosure
- CLAUDE.md: ~8KB (60% reduction)
- Global agents: ~80KB core (60% reduction)
- Template agents: ~20KB core (60% reduction)
- Total context: ~108KB

### Target
- **55-60% reduction** in total context per task
- **No quality degradation** (tests still pass, same functionality)
```

## Execution Steps

### Step 1: Create Measurement Script (This Task)
- [ ] Create `scripts/measure-token-usage.py`
- [ ] Test measurement on current installation
- [ ] Verify correct file paths and calculations

### Step 2: Capture Baseline (Before Implementation)
```bash
# On macOS VM or fresh environment
python3 scripts/measure-token-usage.py --baseline

# Record output in measurements/baseline.json
```

### Step 3: Execute Benchmark (Optional - for task-level metrics)
```bash
# If capturing per-task metrics
/task-create "Initialize FastAPI application infrastructure" prefix:BENCH
# Record: tokens, time, agent calls

/task-create "Create Products CRUD feature" prefix:BENCH
# Record: tokens, time, agent calls
```

### Step 4: Implement Progressive Disclosure
Execute TASK-PD-001 through TASK-PD-019

### Step 5: Capture After Measurement
```bash
python3 scripts/measure-token-usage.py --after
```

### Step 6: Generate Comparison Report
```bash
python3 scripts/measure-token-usage.py --compare

# Output: measurements/comparison-report.json
```

## Blog Content Generation

The comparison report provides data for blog post:

```markdown
# GuardKit Optimization: 55% Token Reduction with Progressive Disclosure

## The Problem
Our initial template agents were comprehensive but loaded ~270KB per task...

## The Solution
Progressive disclosure splits content into core (always loaded) and extended (on-demand)...

## Results

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| CLAUDE.md | 20KB | 8KB | 60% |
| Global Agents | 200KB | 80KB | 60% |
| Template Agents | 50KB | 20KB | 60% |
| **Total Context** | **270KB** | **108KB** | **60%** |

## Impact
- Faster responses
- Lower token costs
- Same comprehensive guidance (on-demand)
```

## Acceptance Criteria

- [ ] `scripts/measure-token-usage.py` created and working
- [ ] Baseline measurement captured before any PD changes
- [ ] Measurement files saved in `measurements/` directory
- [ ] Script can calculate and display comparison
- [ ] Output format suitable for blog post content

## Files to Create

1. `scripts/measure-token-usage.py` - Main measurement script
2. `measurements/` - Directory for measurement files
3. `tasks/templates/benchmark-products-feature.md` - Reusable benchmark template

## Estimated Effort

**0.5 days**

## Dependencies

None - this is Phase 0, must complete before TASK-PD-001

## Notes

- Run baseline measurement BEFORE starting any progressive disclosure implementation
- Keep measurements directory in git for historical tracking
- Use same VM/environment for before/after to ensure valid comparison

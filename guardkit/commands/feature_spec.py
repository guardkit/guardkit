"""Feature Spec Command Orchestration Module.

This module provides the FeatureSpecCommand class for orchestrating the
/feature-spec command. It handles stack detection, codebase scanning,
file output, and Graphiti seeding of BDD feature specifications.

Public API:
    FeatureSpecCommand: Main orchestrator class
    FeatureSpecResult: Result dataclass
    detect_stack: Stack detection utility
    scan_codebase: Codebase scanning utility
    write_outputs: File output utility
    seed_to_graphiti: Graphiti seeding utility
"""

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

# Lazy module-level reference to get_graphiti for patchability in tests.
# This is set to None and imported on first use to allow graceful degradation.
try:
    from guardkit.knowledge.graphiti_client import get_graphiti
except ImportError:
    get_graphiti = None  # type: ignore[assignment]


@dataclass
class FeatureSpecResult:
    """Result of /feature-spec execution."""

    feature_file: Path
    assumptions_file: Path
    summary_file: Path
    scaffolding_files: dict[str, Path] = field(default_factory=dict)  # empty in v1
    scenarios_count: int = 0
    assumptions_count: int = 0
    stack: str = "generic"
    modules: list[str] = field(default_factory=list)
    existing_features: list[Path] = field(default_factory=list)
    patterns: list[str] = field(default_factory=list)


def detect_stack(root: Path) -> dict:
    """Detect project technology stack.

    Priority order (first match wins):
    1. pyproject.toml -> Python (pytest-bdd)
    2. requirements.txt or setup.py -> Python (pytest-bdd)
    3. go.mod -> Go (godog)
    4. Cargo.toml -> Rust (cucumber-rs)
    5. package.json (only if no Python signals) -> TypeScript (cucumber-js)
    6. None -> Generic (no scaffolding)

    Args:
        root: Path to the project root directory.

    Returns:
        Dict with keys:
        - stack: str (e.g., "python", "go", "rust", "typescript", "generic")
        - bdd_runner: str | None (e.g., "pytest-bdd", "godog", etc.)
        - step_extension: str | None (e.g., ".py", ".go", ".rs", ".ts")
    """
    # Python signals (highest priority)
    if (root / "pyproject.toml").exists():
        return {"stack": "python", "bdd_runner": "pytest-bdd", "step_extension": ".py"}
    if (root / "requirements.txt").exists() or (root / "setup.py").exists():
        return {"stack": "python", "bdd_runner": "pytest-bdd", "step_extension": ".py"}
    # Go
    if (root / "go.mod").exists():
        return {"stack": "go", "bdd_runner": "godog", "step_extension": ".go"}
    # Rust
    if (root / "Cargo.toml").exists():
        return {"stack": "rust", "bdd_runner": "cucumber-rs", "step_extension": ".rs"}
    # TypeScript (only if no Python signals already caught above)
    if (root / "package.json").exists():
        return {"stack": "typescript", "bdd_runner": "cucumber-js", "step_extension": ".ts"}
    # Generic
    return {"stack": "generic", "bdd_runner": None, "step_extension": None}


def scan_codebase(root: Path, stack: dict) -> dict:
    """Scan codebase for context.

    Args:
        root: Path to the project root directory.
        stack: Stack dict from detect_stack().

    Returns:
        Dict with keys:
        - modules: list[str] - module/package tree (dot-notation)
        - existing_features: list[Path] - existing .feature files
        - patterns: list[str] - detected architectural patterns
    """
    # Walk root for Python modules (packages with __init__.py)
    modules = []
    for p in sorted(root.rglob("__init__.py")):
        rel = p.parent.relative_to(root)
        rel_str = str(rel)
        if rel_str != ".":
            modules.append(rel_str.replace("/", "."))

    # Find existing feature files
    existing_features = sorted(root.rglob("*.feature"))

    # Detect patterns from file names
    patterns = []
    step_ext = stack.get("step_extension") or ".py"
    all_file_stems = [p.stem for p in root.rglob(f"*{step_ext}")]
    pattern_indicators = {
        "models": ["model", "schema", "entity"],
        "routes": ["route", "endpoint", "controller", "view"],
        "services": ["service", "usecase", "handler"],
        "repositories": ["repository", "repo", "dao"],
    }
    for pattern_name, indicators in pattern_indicators.items():
        if any(ind in fname.lower() for fname in all_file_stems for ind in indicators):
            patterns.append(pattern_name)

    return {
        "modules": modules,
        "existing_features": existing_features,
        "patterns": patterns,
    }


def _extract_feature_name(feature_content: str) -> str:
    """Extract feature name from Gherkin Feature: line.

    Args:
        feature_content: Raw Gherkin feature content string.

    Returns:
        Kebab-case feature name slug. Returns "unnamed-feature" if no
        Feature: line found.
    """
    for line in feature_content.splitlines():
        stripped = line.strip()
        if stripped.startswith("Feature:"):
            name = stripped[len("Feature:"):].strip()
            # Kebab-case: replace non-alphanumeric runs with hyphens, lowercase
            slug = re.sub(r"[^a-zA-Z0-9]+", "-", name).strip("-").lower()
            return slug or "unnamed-feature"
    return "unnamed-feature"


def _count_scenarios(feature_content: str) -> int:
    """Count Scenario: and Scenario Outline: lines.

    Args:
        feature_content: Raw Gherkin feature content string.

    Returns:
        Integer count of scenario declarations.
    """
    count = 0
    for line in feature_content.splitlines():
        stripped = line.strip()
        if stripped.startswith("Scenario:") or stripped.startswith("Scenario Outline:"):
            count += 1
    return count


def _parse_scenarios(feature_content: str) -> list[str]:
    """Parse feature content into individual scenario blocks.

    Each block starts at a Scenario: or Scenario Outline: line and
    extends to the next such line (or end of content).

    Args:
        feature_content: Raw Gherkin feature content string.

    Returns:
        List of scenario block strings (each includes its Scenario: header).
    """
    scenarios = []
    current: list[str] = []
    in_scenario = False

    for line in feature_content.splitlines():
        stripped = line.strip()
        if stripped.startswith("Scenario:") or stripped.startswith("Scenario Outline:"):
            if current and in_scenario:
                scenarios.append("\n".join(current))
            current = [line]
            in_scenario = True
        elif in_scenario:
            current.append(line)

    if current and in_scenario:
        scenarios.append("\n".join(current))

    return scenarios


def _generate_summary_md(
    feature_name: str,
    feature_content: str,
    assumptions: list[dict],
    stack: dict,
) -> str:
    """Generate summary markdown file content.

    Args:
        feature_name: Kebab-case feature name.
        feature_content: Raw Gherkin feature content.
        assumptions: List of assumption dicts.
        stack: Stack dict from detect_stack().

    Returns:
        Markdown string for the summary file.
    """
    scenario_count = _count_scenarios(feature_content)
    lines = [
        f"# Feature Spec Summary: {feature_name}",
        "",
        f"**Stack:** {stack.get('stack', 'generic')}",
        f"**BDD Runner:** {stack.get('bdd_runner') or 'N/A'}",
        f"**Scenarios:** {scenario_count}",
        f"**Assumptions:** {len(assumptions)}",
        "",
        "## Scenarios",
        "",
    ]
    for scenario_text in _parse_scenarios(feature_content):
        first_line = scenario_text.strip().splitlines()[0].strip()
        lines.append(f"- {first_line}")

    if assumptions:
        lines.extend(["", "## Assumptions", ""])
        for a in assumptions:
            text = a.get("text") or a.get("description", "")
            lines.append(f"- **{a.get('id', '?')}**: {text}")

    lines.append("")
    return "\n".join(lines)


def write_outputs(
    feature_content: str,
    assumptions: list[dict],
    source: str,
    output_dir: Path,
    stack: dict | None = None,
) -> dict[str, Path]:
    """Write all output files.

    Creates {output_dir}/{feature_name}/:
    - {name}.feature
    - {name}_assumptions.yaml
    - {name}_summary.md

    Args:
        feature_content: Raw Gherkin feature content.
        assumptions: List of assumption dicts.
        source: Source description for the assumptions YAML.
        output_dir: Base output directory (created if not exists).
        stack: Stack dict from detect_stack(). Defaults to generic if not provided.

    Returns:
        Dict with keys "feature", "assumptions", "summary" mapping to
        the created file Paths.
    """
    feature_name = _extract_feature_name(feature_content)
    feature_dir = output_dir / feature_name
    feature_dir.mkdir(parents=True, exist_ok=True)

    # Write .feature file
    feature_path = feature_dir / f"{feature_name}.feature"
    feature_path.write_text(feature_content)

    # Write assumptions YAML
    assumptions_path = feature_dir / f"{feature_name}_assumptions.yaml"
    assumptions_data = {
        "source": source,
        "assumptions": assumptions,
    }
    with open(assumptions_path, "w") as f:
        yaml.dump(assumptions_data, f, default_flow_style=False, sort_keys=False)

    # Write summary markdown
    stack_info: dict = stack or {"stack": "generic", "bdd_runner": None}
    summary_content = _generate_summary_md(feature_name, feature_content, assumptions, stack_info)
    summary_path = feature_dir / f"{feature_name}_summary.md"
    summary_path.write_text(summary_content)

    return {
        "feature": feature_path,
        "assumptions": assumptions_path,
        "summary": summary_path,
    }


async def seed_to_graphiti(
    feature_id: str,
    feature_content: str,
    assumptions: list[dict],
    output_paths: dict,
) -> None:
    """Seed feature spec to Graphiti.

    Seeds:
    - Individual scenarios as distinct episodes to 'feature_specs' group
      (NOT whole file as one blob)
    - Assumptions to 'domain_knowledge' group

    Non-blocking: logs warning and continues if Graphiti unavailable.

    Args:
        feature_id: Stable identifier for the feature.
        feature_content: Raw Gherkin feature content.
        assumptions: List of assumption dicts.
        output_paths: Dict of output file paths (from write_outputs).
    """
    if get_graphiti is None:
        logger.warning("Graphiti client not available, skipping seeding")
        return

    client = get_graphiti()
    if client is None or not client.enabled:
        logger.warning("Graphiti not connected, skipping feature spec seeding")
        return

    # Seed individual scenarios (NOT the whole file as one blob)
    scenarios = _parse_scenarios(feature_content)
    for i, scenario_text in enumerate(scenarios):
        try:
            await client.add_episode(
                name=f"{feature_id}-scenario-{i + 1}",
                episode_body=json.dumps(
                    {
                        "feature_id": feature_id,
                        "scenario_index": i + 1,
                        "scenario": scenario_text,
                    }
                ),
                group_id="feature_specs",
                source="feature_spec_command",
                entity_type="scenario",
            )
        except Exception as e:
            logger.warning(f"Failed to seed scenario {i + 1}: {e}")

    # Seed assumptions
    for assumption in assumptions:
        try:
            await client.add_episode(
                name=f"{feature_id}-assumption-{assumption.get('id', 'unknown')}",
                episode_body=json.dumps(
                    {
                        "feature_id": feature_id,
                        "assumption": assumption,
                    }
                ),
                group_id="domain_knowledge",
                source="feature_spec_command",
                entity_type="assumption",
            )
        except Exception as e:
            logger.warning(f"Failed to seed assumption: {e}")


SUPPORTED_EXTENSIONS = {".md", ".txt", ".yaml", ".yml", ".rst", ".json"}


def _read_input_files(file_paths: list) -> str:
    """Read and concatenate input files.

    Supports .md, .txt, .yaml, .yml, .rst, and .json files.
    Concatenates with newlines.
    Unsupported or missing files are logged as warnings and skipped.

    Args:
        file_paths: List of file paths (str or Path) to read.

    Returns:
        Concatenated file contents separated by newlines.
    """
    contents = []
    for fp in file_paths:
        p = Path(fp)
        if not p.exists():
            logger.warning(f"Input file not found: {fp}")
        elif p.suffix not in SUPPORTED_EXTENSIONS:
            supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
            logger.warning(
                f"Unsupported file extension '{p.suffix}' for: {fp}. "
                f"Supported extensions: {supported}"
            )
        else:
            contents.append(p.read_text())
    return "\n".join(contents)


class FeatureSpecCommand:
    """Orchestrates /feature-spec execution.

    Handles the full pipeline:
    1. Read and merge input files
    2. Detect technology stack
    3. Scan codebase for context
    4. Write output files (.feature, _assumptions.yaml, _summary.md)
    5. Seed to Graphiti (non-blocking)
    6. Return FeatureSpecResult

    Example:
        cmd = FeatureSpecCommand(project_root=Path("/my/project"))
        result = await cmd.execute(
            input_text=gherkin_content,
            options={"output_dir": Path("/my/project/features")},
        )
    """

    def __init__(self, project_root: Path):
        """Initialize FeatureSpecCommand.

        Args:
            project_root: Path to the project root directory.
        """
        self.project_root = project_root

    async def execute(
        self,
        input_text: str,
        options: dict,
    ) -> FeatureSpecResult:
        """Execute the full /feature-spec pipeline.

        Args:
            input_text: The feature description or Gherkin content.
            options: Command options dict with keys:
                - output_dir: Path for output (default: project_root / "features")
                - from_files: list of input file paths to read and concatenate
                - feature_id: explicit feature ID (default: derived from content)
                - source: source description (default: "feature-spec-command")
                - assumptions: list of assumption dicts (default: [])

        Returns:
            FeatureSpecResult with paths, counts, and detected stack.
        """
        # Handle file inputs: merge file contents into input_text
        from_files = options.get("from_files", [])
        if from_files:
            file_content = _read_input_files(from_files)
            if file_content:
                input_text = f"{input_text}\n{file_content}" if input_text else file_content

        # Detect technology stack
        stack = detect_stack(self.project_root)

        # Scan codebase for context
        scan_result = scan_codebase(self.project_root, stack)

        # Determine output directory
        output_dir = Path(options.get("output_dir", self.project_root / "features"))

        # Determine feature ID
        feature_id = options.get("feature_id") or _extract_feature_name(input_text)

        # Determine source label
        source = options.get("source", "feature-spec-command")

        # Collect assumptions
        assumptions: list[dict] = options.get("assumptions", [])

        # Write output files
        paths = write_outputs(
            feature_content=input_text,
            assumptions=assumptions,
            source=source,
            output_dir=output_dir,
            stack=stack,
        )

        # Seed to Graphiti (non-blocking — failures are logged as warnings)
        await seed_to_graphiti(
            feature_id=feature_id,
            feature_content=input_text,
            assumptions=assumptions,
            output_paths=paths,
        )

        return FeatureSpecResult(
            feature_file=paths["feature"],
            assumptions_file=paths["assumptions"],
            summary_file=paths["summary"],
            scaffolding_files={},
            scenarios_count=_count_scenarios(input_text),
            assumptions_count=len(assumptions),
            stack=stack["stack"],
            modules=scan_result["modules"],
            existing_features=scan_result["existing_features"],
            patterns=scan_result["patterns"],
        )

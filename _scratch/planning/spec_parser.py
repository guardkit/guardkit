"""
Research Template Spec Parser for GuardKit.

Parses research-to-implementation template markdown files into structured data.
Uses regex-based parsing for markdown tables and sections - no external markdown
parsing libraries required.

Coverage Target: >=85%
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
import re


@dataclass
class Decision:
    """Represents a decision from the Decision Log table."""
    number: str  # "D1", "D2", etc.
    title: str
    rationale: str
    alternatives_rejected: str
    adr_status: str  # "Accepted", "Proposed", "Superseded"


@dataclass
class TaskDefinition:
    """Represents an implementation task from the Implementation Tasks section."""
    name: str
    complexity: str  # "low", "medium", "high"
    complexity_score: int
    task_type: str  # "implementation", "refactor", "integration", "configuration", "documentation"
    domain_tags: list[str]
    files_to_create: list[str]
    files_to_modify: list[str]
    files_not_to_touch: list[str]
    dependencies: list[str]
    inputs: str
    outputs: str
    relevant_decisions: list[str]
    acceptance_criteria: list[str]
    implementation_notes: str
    player_constraints: list[str]
    coach_validation_commands: list[str]
    turn_budget_expected: int = 2
    turn_budget_max: int = 5


@dataclass
class ResolvedQuestion:
    """Represents a question from the Open Questions section."""
    question: str
    resolution: str


@dataclass
class Component:
    """Represents a component from the Components table."""
    name: str
    file_path: str
    purpose: str
    new_or_modified: str


@dataclass
class TestStrategy:
    """Represents the Test Strategy section.

    Note: Named TestStrategy (not TestingStrategy) to match task spec,
    but pytest may warn about collection. This is expected.
    """
    unit_tests: list[dict[str, str]]
    integration_tests: list[dict[str, str]]
    manual_verification: list[str]


@dataclass
class DependencySet:
    """Represents the Dependencies section."""
    python: list[str]
    system: list[str]
    environment: dict[str, str]


@dataclass
class APIContract:
    """Represents an API contract from the API Contracts section."""
    name: str
    content: str


@dataclass
class ParsedSpec:
    """The complete parsed research template specification."""
    problem_statement: str
    decisions: list[Decision]
    warnings: list[str]
    components: list[Component]
    data_flow: str
    message_schemas: dict[str, Any]
    api_contracts: list[APIContract]
    tasks: list[TaskDefinition]
    test_strategy: Optional[TestStrategy] = None
    dependencies: Optional[DependencySet] = None
    file_tree: str = ""
    out_of_scope: list[str] = field(default_factory=list)
    resolved_questions: list[ResolvedQuestion] = field(default_factory=list)
    parse_warnings: list[str] = field(default_factory=list)


def _extract_section(content: str, section_pattern: str, next_section_pattern: str = r"^##\s+") -> str:
    """
    Extract content between a section header and the next section.

    Args:
        content: The full markdown content
        section_pattern: Regex pattern to match the section header
        next_section_pattern: Pattern for the next section header

    Returns:
        The section content (without the header), or empty string if not found
    """
    # Find the section header
    match = re.search(section_pattern, content, re.MULTILINE | re.IGNORECASE)
    if not match:
        return ""

    start = match.end()

    # Find the next section header
    remaining = content[start:]
    next_match = re.search(next_section_pattern, remaining, re.MULTILINE)

    if next_match:
        return remaining[:next_match.start()].strip()
    return remaining.strip()


def _parse_decision_table(section_content: str) -> list[Decision]:
    """
    Parse the Decision Log markdown table into Decision objects.

    Expected format:
    | # | Decision | Rationale | Alternatives Rejected | Status |
    |---|----------|-----------|----------------------|---------|
    | D1 | ... | ... | ... | Accepted |
    """
    decisions = []

    # Find table rows (lines starting with |)
    lines = section_content.strip().split('\n')

    # Skip header and separator rows
    data_rows = []
    in_table = False
    for line in lines:
        line = line.strip()
        if not line.startswith('|'):
            if in_table:
                break  # End of table
            continue

        in_table = True
        # Skip separator row (contains ---)
        if '---' in line:
            continue
        # Skip header row (contains "Decision" as a header)
        if '| # |' in line or '|#|' in line or '| Decision |' in line:
            continue

        data_rows.append(line)

    for row in data_rows:
        # Split by | and strip whitespace
        cells = [cell.strip() for cell in row.split('|')]
        # Remove empty first and last cells (from leading/trailing |)
        cells = [c for c in cells if c]

        if len(cells) >= 5:
            decisions.append(Decision(
                number=cells[0].strip(),
                title=cells[1].strip(),
                rationale=cells[2].strip(),
                alternatives_rejected=cells[3].strip(),
                adr_status=cells[4].strip(),
            ))

    return decisions


def _parse_warnings(section_content: str) -> list[str]:
    """
    Parse the Warnings & Constraints bullet list.

    Expected format:
    - Warning 1: Description
    - Warning 2: Description
    """
    warnings = []

    # Match bullet points (- or *)
    pattern = r'^[\-\*]\s+(.+)$'
    for line in section_content.split('\n'):
        match = re.match(pattern, line.strip())
        if match:
            warnings.append(match.group(1).strip())

    return warnings


def _parse_bullet_list(content: str) -> list[str]:
    """Parse a bullet list (- or *) into a list of strings."""
    items = []
    pattern = r'^[\s]*[\-\*]\s+(.+)$'
    for line in content.split('\n'):
        match = re.match(pattern, line.strip())
        if match:
            items.append(match.group(1).strip())
    return items


def _parse_numbered_list(content: str) -> list[str]:
    """Parse a numbered list into a list of strings."""
    items = []
    pattern = r'^\s*\d+\.\s+(.+)$'
    for line in content.split('\n'):
        match = re.match(pattern, line.strip())
        if match:
            items.append(match.group(1).strip())
    return items


def _parse_components_table(section_content: str) -> list[Component]:
    """
    Parse the Components table.

    Expected format:
    | Component | File Path | Purpose | Status |
    |-----------|-----------|---------|--------|
    | Name | path/to/file.py | Description | New |
    """
    components = []

    lines = section_content.strip().split('\n')

    data_rows = []
    in_table = False
    for line in lines:
        line = line.strip()
        if not line.startswith('|'):
            if in_table:
                break
            continue

        in_table = True
        if '---' in line:
            continue
        # Skip header row
        if 'Component' in line or 'File Path' in line:
            continue

        data_rows.append(line)

    for row in data_rows:
        cells = [cell.strip() for cell in row.split('|')]
        cells = [c for c in cells if c]

        if len(cells) >= 4:
            components.append(Component(
                name=cells[0].strip(),
                file_path=cells[1].strip(),
                purpose=cells[2].strip(),
                new_or_modified=cells[3].strip(),
            ))

    return components


def _parse_resolved_questions(section_content: str) -> list[ResolvedQuestion]:
    """
    Parse the Open Questions section.

    Expected format (variant 1 - numbered with inline Q/A):
    1. **Question:** What is X?
       **Resolution:** Y is the answer.

    Or variant 2 - table format:
    | Question | Resolution |
    |----------|-----------|
    | What is X? | Y is the answer |
    """
    questions = []

    # Try table format first
    if '|' in section_content and 'Question' in section_content:
        lines = section_content.strip().split('\n')
        data_rows = []
        in_table = False
        for line in lines:
            line = line.strip()
            if not line.startswith('|'):
                if in_table:
                    break
                continue

            in_table = True
            if '---' in line:
                continue
            if 'Question' in line and 'Resolution' in line:
                continue

            data_rows.append(line)

        for row in data_rows:
            cells = [cell.strip() for cell in row.split('|')]
            cells = [c for c in cells if c]

            if len(cells) >= 2:
                questions.append(ResolvedQuestion(
                    question=cells[0].strip(),
                    resolution=cells[1].strip(),
                ))

        return questions

    # Try numbered format with **Question:** and **Resolution:**
    # Pattern matches: N. **Question:** text \n   **Resolution:** text
    pattern = r'\d+\.\s*\*\*Question:\*\*\s*(.+?)\s*\*\*Resolution:\*\*\s*(.+?)(?=\d+\.\s*\*\*Question:|\Z)'

    matches = re.findall(pattern, section_content, re.DOTALL | re.IGNORECASE)
    for q, r in matches:
        questions.append(ResolvedQuestion(
            question=q.strip(),
            resolution=r.strip(),
        ))

    return questions


def _parse_test_strategy(section_content: str) -> TestStrategy:
    """
    Parse the Test Strategy section.

    Expected format has subsections for Unit Tests, Integration Tests, Manual Verification.
    """
    unit_tests = []
    integration_tests = []
    manual_verification = []

    # Parse Unit Tests subsection
    unit_section = _extract_section(section_content, r"###\s*Unit Tests", r"###")
    if unit_section:
        # Look for numbered items with **Test:** and **Expected:**
        pattern = r'\d+\.\s*\*\*Test:\*\*\s*(.+?)\s*\*\*Expected:\*\*\s*(.+?)(?=\d+\.\s*\*\*Test:|\Z|$)'
        matches = re.findall(pattern, unit_section, re.DOTALL)
        for test_name, expected in matches:
            unit_tests.append({
                "test": test_name.strip(),
                "expected": expected.strip(),
            })

    # Parse Integration Tests subsection
    integration_section = _extract_section(section_content, r"###\s*Integration Tests", r"###")
    if integration_section:
        pattern = r'\d+\.\s*\*\*Test:\*\*\s*(.+?)\s*\*\*Expected:\*\*\s*(.+?)(?=\d+\.\s*\*\*Test:|\Z|$)'
        matches = re.findall(pattern, integration_section, re.DOTALL)
        for test_name, expected in matches:
            integration_tests.append({
                "test": test_name.strip(),
                "expected": expected.strip(),
            })

    # Parse Manual Verification subsection
    manual_section = _extract_section(section_content, r"###\s*Manual Verification", r"###|^##")
    if manual_section:
        manual_verification = _parse_bullet_list(manual_section)

    return TestStrategy(
        unit_tests=unit_tests,
        integration_tests=integration_tests,
        manual_verification=manual_verification,
    )


def _parse_dependencies(section_content: str) -> DependencySet:
    """
    Parse the Dependencies section.

    Expected format has subsections for Python Packages, System Dependencies, Environment Variables.
    """
    python_deps = []
    system_deps = []
    environment = {}

    # Parse Python Packages subsection
    python_section = _extract_section(section_content, r"###\s*Python (Packages|Dependencies)", r"###")
    if python_section:
        python_deps = _parse_bullet_list(python_section)

    # Parse System Dependencies subsection
    system_section = _extract_section(section_content, r"###\s*System Dependencies", r"###")
    if system_section:
        system_deps = _parse_bullet_list(system_section)

    # Parse Environment Variables subsection
    env_section = _extract_section(section_content, r"###\s*Environment Variables", r"###|^##")
    if env_section:
        # Look for NAME: Description or NAME=value patterns
        pattern = r'^\s*[\-\*]?\s*([A-Z_][A-Z0-9_]*)[\s:=]+(.+?)$'
        for line in env_section.split('\n'):
            match = re.match(pattern, line.strip(), re.IGNORECASE)
            if match:
                environment[match.group(1).strip()] = match.group(2).strip()

    return DependencySet(
        python=python_deps,
        system=system_deps,
        environment=environment,
    )


def _parse_api_contracts(section_content: str) -> list[APIContract]:
    """
    Parse the API Contracts section.

    Expected format:
    ### Contract: contract_name
    ```python
    def contract_name(...):
        ...
    ```
    """
    contracts = []

    # Find all ### Contract: or ### pattern
    pattern = r'###\s*(?:Contract:?\s*)?(\w+)\s*\n(.*?)(?=###|\Z)'
    matches = re.findall(pattern, section_content, re.DOTALL)

    for name, content in matches:
        # Extract code block content
        code_pattern = r'```(?:python)?\n(.*?)```'
        code_match = re.search(code_pattern, content, re.DOTALL)
        if code_match:
            contracts.append(APIContract(
                name=name.strip(),
                content=code_match.group(1).strip(),
            ))

    return contracts


def _parse_task_field_value(task_content: str, field_name: str) -> str:
    """Extract a single field value from task content.

    Field format in tasks is: - **Field Name:** value
    The value ends when we hit the next field (- **) or end of content.
    """
    # Match field with format: - **Field:** or **Field:**
    pattern = rf'[-\*]?\s*\*\*{re.escape(field_name)}:\*\*\s*(.+?)(?=\n[-\*]?\s*\*\*[A-Za-z]|\Z)'
    match = re.search(pattern, task_content, re.DOTALL | re.IGNORECASE)
    if match:
        value = match.group(1).strip()
        # For single-line values, only take the first line
        # (multi-line values are handled by list parser)
        first_line = value.split('\n')[0].strip()
        return first_line
    return ""


def _parse_task_field_list(task_content: str, field_name: str) -> list[str]:
    """Extract a list field from task content (bullet list following field).

    Field format can be:
    - **Field:** [item1, item2]  (inline list)
    - **Field:**
      - item1
      - item2  (bullet list)
    """
    # Match field with format: - **Field:** or **Field:**
    pattern = rf'[-\*]?\s*\*\*{re.escape(field_name)}:\*\*\s*(.*?)(?=\n[-\*]?\s*\*\*[A-Za-z]|\Z)'
    match = re.search(pattern, task_content, re.DOTALL | re.IGNORECASE)
    if not match:
        return []

    field_content = match.group(1).strip()

    # Check if it's an inline list like [tag1, tag2] or [file1, file2]
    # Only on the first line
    first_line = field_content.split('\n')[0].strip()
    inline_match = re.match(r'\[([^\]]*)\]', first_line)
    if inline_match:
        items = [item.strip() for item in inline_match.group(1).split(',')]
        return [item for item in items if item]

    # Check if it's a bullet list (items start with - at higher indent)
    items = []
    lines = field_content.split('\n')
    for line in lines:
        # Match indented bullet items (- item or * item)
        # Skip lines that are field headers (start with - **)
        stripped = line.strip()
        if stripped.startswith('- **') or stripped.startswith('* **'):
            continue
        bullet_match = re.match(r'^[\-\*]\s+(.+)$', stripped)
        if bullet_match:
            item = bullet_match.group(1).strip()
            # Don't include items that look like field headers
            if not item.startswith('**'):
                items.append(item)

    if items:
        return items

    # Return as single-item list if it's a simple value and not empty
    if first_line and first_line.lower() not in ('none', '[]', ''):
        # Handle comma-separated without brackets
        if ',' in first_line:
            return [item.strip() for item in first_line.split(',') if item.strip()]
        return [first_line]

    return []


def _parse_task(task_content: str, task_name: str) -> TaskDefinition:
    """Parse a single task block into a TaskDefinition."""

    # Parse complexity - format: "low (2/10)" or "medium (5/10)"
    complexity_str = _parse_task_field_value(task_content, "Complexity")
    complexity = "medium"  # default
    complexity_score = 5  # default

    if complexity_str:
        # Try to parse "level (N/10)" format
        complexity_match = re.match(r'(\w+)\s*\((\d+)/10\)', complexity_str)
        if complexity_match:
            complexity = complexity_match.group(1).lower()
            complexity_score = int(complexity_match.group(2))
        else:
            complexity = complexity_str.lower()

    # Parse type
    task_type = _parse_task_field_value(task_content, "Type")
    if not task_type:
        task_type = "implementation"

    # Parse domain tags - format: [tag1, tag2, tag3]
    domain_tags = _parse_task_field_list(task_content, "Domain Tags")

    # Parse file lists
    files_to_create = _parse_task_field_list(task_content, "Files to Create")
    files_to_modify = _parse_task_field_list(task_content, "Files to Modify")
    files_not_to_touch = _parse_task_field_list(task_content, "Files NOT to Touch")

    # Parse dependencies
    dependencies = _parse_task_field_list(task_content, "Dependencies")
    # Filter out "None"
    dependencies = [d for d in dependencies if d.lower() != "none"]

    # Parse inputs/outputs
    inputs = _parse_task_field_value(task_content, "Inputs")
    outputs = _parse_task_field_value(task_content, "Outputs")

    # Parse relevant decisions - can be "D1, D2" or "D1"
    relevant_decisions_str = _parse_task_field_value(task_content, "Relevant Decisions")
    relevant_decisions = []
    if relevant_decisions_str and relevant_decisions_str.lower() != "none":
        relevant_decisions = [d.strip() for d in relevant_decisions_str.split(',') if d.strip()]

    # Parse acceptance criteria (numbered list)
    ac_pattern = r'[-\*]?\s*\*\*Acceptance Criteria:\*\*\s*(.*?)(?=\n[-\*]?\s*\*\*[A-Za-z]|\Z)'
    ac_match = re.search(ac_pattern, task_content, re.DOTALL | re.IGNORECASE)
    acceptance_criteria = []
    if ac_match:
        ac_content = ac_match.group(1)
        # Parse numbered items
        for line in ac_content.split('\n'):
            line = line.strip()
            num_match = re.match(r'^\d+\.\s+(.+)$', line)
            if num_match:
                acceptance_criteria.append(num_match.group(1).strip())

    # Parse implementation notes
    implementation_notes = _parse_task_field_value(task_content, "Implementation Notes")

    # Parse player constraints
    player_constraints = _parse_task_field_list(task_content, "Player Constraints")

    # Parse coach validation commands
    coach_pattern = r'[-\*]?\s*\*\*Coach Validation:\*\*\s*(.*?)(?=\n[-\*]?\s*\*\*[A-Za-z]|\Z)'
    coach_match = re.search(coach_pattern, task_content, re.DOTALL | re.IGNORECASE)
    coach_validation_commands = []
    if coach_match:
        coach_content = coach_match.group(1)
        # Parse bullet list
        for line in coach_content.split('\n'):
            line = line.strip()
            # Skip lines that are field headers
            if line.startswith('- **') or line.startswith('* **'):
                continue
            bullet_match = re.match(r'^[\-\*]\s+(.+)$', line)
            if bullet_match:
                item = bullet_match.group(1).strip()
                if not item.startswith('**'):
                    coach_validation_commands.append(item)

    # Parse turn budget - format: "N expected, M max"
    turn_budget_str = _parse_task_field_value(task_content, "Turn Budget")
    turn_budget_expected = 2
    turn_budget_max = 5
    if turn_budget_str:
        budget_match = re.match(r'(\d+)\s*expected,?\s*(\d+)\s*max', turn_budget_str)
        if budget_match:
            turn_budget_expected = int(budget_match.group(1))
            turn_budget_max = int(budget_match.group(2))

    return TaskDefinition(
        name=task_name,
        complexity=complexity,
        complexity_score=complexity_score,
        task_type=task_type,
        domain_tags=domain_tags,
        files_to_create=files_to_create,
        files_to_modify=files_to_modify,
        files_not_to_touch=files_not_to_touch,
        dependencies=dependencies,
        inputs=inputs,
        outputs=outputs,
        relevant_decisions=relevant_decisions,
        acceptance_criteria=acceptance_criteria,
        implementation_notes=implementation_notes,
        player_constraints=player_constraints,
        coach_validation_commands=coach_validation_commands,
        turn_budget_expected=turn_budget_expected,
        turn_budget_max=turn_budget_max,
    )


def _parse_implementation_tasks(section_content: str, parse_warnings: list[str]) -> list[TaskDefinition]:
    """
    Parse the Implementation Tasks section into TaskDefinition objects.

    Expected format:
    ### TASK N: Task Name
    - **Complexity:** level (score/10)
    - **Type:** type
    ...
    """
    tasks = []

    # Find all task blocks: ### TASK N: Name or ### Task N: Name
    task_pattern = r'###\s*(TASK\s*\d+:\s*.+?)(?=###\s*TASK|\Z)'
    matches = re.findall(task_pattern, section_content, re.DOTALL | re.IGNORECASE)

    for match in matches:
        # Extract task name from the first line
        lines = match.strip().split('\n')
        if lines:
            task_name = lines[0].strip()
            task_content = '\n'.join(lines[1:])

            try:
                task = _parse_task(task_content, task_name)

                # Validate that the task has essential fields
                missing_fields = []
                if not task.task_type or task.task_type == "implementation" and "**Type:**" not in task_content:
                    # Check if Type was explicitly specified
                    if "**Type:**" not in task_content:
                        missing_fields.append("Type")
                if not task.inputs:
                    missing_fields.append("Inputs")
                if not task.outputs:
                    missing_fields.append("Outputs")
                if not task.acceptance_criteria:
                    missing_fields.append("Acceptance Criteria")

                if missing_fields:
                    parse_warnings.append(
                        f"Task '{task_name}' is missing required fields: {', '.join(missing_fields)}"
                    )

                tasks.append(task)
            except Exception as e:
                parse_warnings.append(f"Failed to parse task '{task_name}': {str(e)}")

    return tasks


def _extract_code_block(content: str) -> str:
    """Extract content from a code block (```...```)."""
    pattern = r'```(?:\w+)?\n(.*?)```'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return content.strip()


def parse_research_template(path: Path) -> ParsedSpec:
    """
    Parse a research-to-implementation template markdown file.

    Args:
        path: Path to the markdown file

    Returns:
        ParsedSpec object containing all parsed sections

    Raises:
        FileNotFoundError: If the file doesn't exist
    """
    content = path.read_text()
    parse_warnings: list[str] = []

    # Parse Problem Statement
    problem_section = _extract_section(content, r"^##\s*\d*\.?\s*Problem Statement", r"^##\s+")
    if not problem_section:
        parse_warnings.append("Missing Problem Statement section")

    # Parse Decision Log
    decision_section = _extract_section(content, r"^##\s*\d*\.?\s*Decision Log", r"^##\s+")
    decisions = []
    if decision_section:
        decisions = _parse_decision_table(decision_section)
        if not decisions:
            # Check if there's content but no valid table
            if decision_section.strip() and '|' not in decision_section:
                parse_warnings.append("Decision Log section exists but contains no valid table")
    else:
        parse_warnings.append("Missing Decision Log section")

    # Parse Warnings & Constraints
    warnings_section = _extract_section(content, r"^##\s*\d*\.?\s*Warnings\s*[&]?\s*Constraints", r"^##\s+")
    warnings = []
    if warnings_section:
        warnings = _parse_warnings(warnings_section)

    # Also check for warnings in Decision Log section (under **Warnings & Constraints**)
    if decision_section:
        inline_warnings_match = re.search(
            r'\*\*Warnings\s*[&]?\s*Constraints\*\*[:\s]*(.+?)(?=^##|\Z)',
            decision_section,
            re.DOTALL | re.MULTILINE
        )
        if inline_warnings_match:
            inline_warnings = _parse_warnings(inline_warnings_match.group(1))
            warnings.extend(inline_warnings)

    # Parse Components
    components_section = _extract_section(content, r"^##\s*\d*\.?\s*Components", r"^##\s+")
    components = []
    if components_section:
        components = _parse_components_table(components_section)

    # Also try "Component Design" subsection under Architecture
    if not components:
        arch_section = _extract_section(content, r"^##\s*\d*\.?\s*Architecture", r"^##\s+")
        if arch_section:
            comp_subsection = _extract_section(arch_section, r"###\s*\d*\.?\d*\s*Component Design", r"###|^##")
            if comp_subsection:
                components = _parse_components_table(comp_subsection)

    # Parse Data Flow
    data_flow_section = _extract_section(content, r"^##\s*\d*\.?\s*Data Flow", r"^##\s+")
    data_flow = ""
    if data_flow_section:
        data_flow = _extract_code_block(data_flow_section)

    # Also try Data Flow subsection under Architecture
    if not data_flow:
        arch_section = _extract_section(content, r"^##\s*\d*\.?\s*Architecture", r"^##\s+")
        if arch_section:
            flow_subsection = _extract_section(arch_section, r"###\s*\d*\.?\d*\s*Data Flow", r"###|^##")
            if flow_subsection:
                data_flow = _extract_code_block(flow_subsection)

    # Parse Message Schemas
    schemas_section = _extract_section(content, r"^##\s*\d*\.?\s*Message Schemas", r"^##\s+")
    message_schemas: dict[str, Any] = {}
    if schemas_section:
        # For now, just store raw schema content - could parse YAML later
        message_schemas["raw"] = _extract_code_block(schemas_section)

    # Parse API Contracts
    api_section = _extract_section(content, r"^##\s*\d*\.?\s*API Contracts", r"^##\s+")
    api_contracts = []
    if api_section:
        api_contracts = _parse_api_contracts(api_section)

    # Parse Out of Scope
    out_of_scope_section = _extract_section(content, r"^##\s*\d*\.?\s*Out of Scope", r"^##\s+")
    out_of_scope = []
    if out_of_scope_section:
        out_of_scope = _parse_bullet_list(out_of_scope_section)

    # Parse Open Questions (Resolved)
    questions_section = _extract_section(content, r"^##\s*\d*\.?\s*Open Questions", r"^##\s+")
    resolved_questions = []
    if questions_section:
        resolved_questions = _parse_resolved_questions(questions_section)

    # Parse Test Strategy
    test_section = _extract_section(content, r"^##\s*\d*\.?\s*Test Strategy", r"^##\s+")
    test_strategy = None
    if test_section:
        test_strategy = _parse_test_strategy(test_section)

    # Parse Dependencies
    deps_section = _extract_section(content, r"^##\s*\d*\.?\s*Dependencies", r"^##\s+")
    dependencies = None
    if deps_section:
        dependencies = _parse_dependencies(deps_section)

    # Parse File Tree
    file_tree_section = _extract_section(content, r"^##\s*\d*\.?\s*File Tree", r"^##\s+")
    file_tree = ""
    if file_tree_section:
        file_tree = _extract_code_block(file_tree_section)

    # Parse Implementation Tasks
    tasks_section = _extract_section(content, r"^##\s*\d*\.?\s*Implementation Tasks", r"^##\s+")
    tasks = []
    if tasks_section:
        tasks = _parse_implementation_tasks(tasks_section, parse_warnings)
        if not tasks:
            parse_warnings.append("Implementation Tasks section exists but no tasks were parsed")
    else:
        parse_warnings.append("Missing Implementation Tasks section")

    return ParsedSpec(
        problem_statement=problem_section,
        decisions=decisions,
        warnings=warnings,
        components=components,
        data_flow=data_flow,
        message_schemas=message_schemas,
        api_contracts=api_contracts,
        tasks=tasks,
        test_strategy=test_strategy,
        dependencies=dependencies,
        file_tree=file_tree,
        out_of_scope=out_of_scope,
        resolved_questions=resolved_questions,
        parse_warnings=parse_warnings,
    )

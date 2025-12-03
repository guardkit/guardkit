---
name: agent-validate
category: Development Tools
summary: Objective quality validation for agent files using GitHub best practices and measurable metrics
---

# Agent Validate - Objective Agent Quality Validation

Provides automated, objective validation of agent markdown files against GitHub best practices and GuardKit quality standards. Generates actionable feedback with measurable metrics and auto-fix suggestions.

## Purpose

**Validation over Documentation**: Unlike guidelines that require human interpretation, this tool provides objective, automated quality assessment with:
- Measurable metrics (0-10 scale)
- Line-level issue detection
- Actionable recommendations with impact estimates
- CI/CD integration support
- Auto-fix capabilities

**Use Cases**:
- Pre-deployment validation of global agents
- Quality assurance during agent development
- CI/CD pipeline integration
- Batch validation of agent libraries
- Regression testing after agent modifications

## Command Interface

### Single Agent Validation

```bash
# Basic validation (console output)
/agent-validate installer/global/agents/code-reviewer.md

# With auto-fix suggestions
/agent-validate code-reviewer.md --suggest-fixes

# JSON output for scripting
/agent-validate code-reviewer.md --format json

# CI/CD integration with threshold
/agent-validate code-reviewer.md --threshold 8.0 --format json --exit-on-fail

# Verbose output with detailed analysis
/agent-validate code-reviewer.md --verbose

# Specific checks only
/agent-validate code-reviewer.md --checks structure,examples,boundaries
```

### Batch Validation

```bash
# Validate all agents in directory
/agent-validate-batch installer/global/agents/

# With quality threshold filter
/agent-validate-batch installer/global/agents/ --threshold 8.0

# Summary table only
/agent-validate-batch installer/global/agents/ --summary

# JSON output for all agents
/agent-validate-batch installer/global/agents/ --format json

# Fail if any agent below threshold
/agent-validate-batch installer/global/agents/ --threshold 8.0 --exit-on-fail
```

### Auto-Enhancement Integration

```bash
# Validate and automatically enhance if below threshold
/agent-validate code-reviewer.md --auto-enhance --threshold 8.5

# This invokes /agent-enhance if score < 8.5
# Re-validates after enhancement
```

## Arguments

### Single Validation (`/agent-validate`)

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `<file-path>` | string | Yes | - | Path to agent markdown file |
| `--format` | enum | No | `console` | Output format: `console`, `json`, `minimal` |
| `--threshold` | float | No | `0.0` | Minimum acceptable score (0.0-10.0) |
| `--exit-on-fail` | flag | No | `false` | Exit code 1 if score below threshold |
| `--suggest-fixes` | flag | No | `false` | Include auto-fix suggestions in output |
| `--auto-enhance` | flag | No | `false` | Auto-invoke `/agent-enhance` if below threshold |
| `--checks` | list | No | `all` | Specific checks to run (comma-separated) |
| `--verbose` | flag | No | `false` | Detailed diagnostic output |
| `--output-file` | string | No | `stdout` | Write report to file instead of stdout |

### Batch Validation (`/agent-validate-batch`)

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `<directory>` | string | Yes | - | Directory containing agent files |
| `--format` | enum | No | `table` | Output format: `table`, `json`, `csv` |
| `--threshold` | float | No | `0.0` | Filter agents below threshold |
| `--exit-on-fail` | flag | No | `false` | Exit code 1 if any agent below threshold |
| `--summary` | flag | No | `false` | Summary table only (no detailed reports) |
| `--recursive` | flag | No | `true` | Recursively search subdirectories |
| `--output-file` | string | No | `stdout` | Write report to file |

## Validation Framework

### Check Categories

Six primary quality checks, based on GitHub analysis of 2,500+ repositories:

1. **Structure Validation** (Weight: 15%)
2. **Example Density** (Weight: 25%)
3. **Boundary Clarity** (Weight: 20%)
4. **Specificity** (Weight: 20%)
5. **Code Example Quality** (Weight: 15%)
6. **Maintenance Indicators** (Weight: 5%)

### Overall Score Calculation

```python
overall_score = (
    (structure_score * 0.15) +
    (example_density_score * 0.25) +
    (boundary_clarity_score * 0.20) +
    (specificity_score * 0.20) +
    (code_quality_score * 0.15) +
    (maintenance_score * 0.05)
)
```

**Score Interpretation**:
- **9.0-10.0**: Excellent - Production ready, exemplary quality
- **8.0-8.9**: Good - Production ready with minor improvements
- **7.0-7.9**: Acceptable - Production ready with recommendations
- **6.0-6.9**: Below Standard - Needs improvement before production
- **5.0-5.9**: Poor - Significant issues, major work required
- **0.0-4.9**: Unacceptable - Critical issues, not production ready

## Validation Algorithms

### 1. Structure Validation (15% weight)

**Purpose**: Ensure logical organization and optimal length.

**Checks**:

#### 1.1 YAML Frontmatter Presence
```python
def check_yaml_frontmatter(content: str) -> CheckResult:
    """
    Verify YAML frontmatter exists and is valid.

    Algorithm:
    1. Check first line is '---'
    2. Find closing '---' within first 50 lines
    3. Parse YAML between delimiters
    4. Validate required fields: name, description
    5. Validate optional fields: tools, model, collaborates_with

    Returns:
        CheckResult with status, line_range, issues
    """
    lines = content.split('\n')

    # Check opening delimiter
    if lines[0].strip() != '---':
        return CheckResult(
            status='fail',
            score=0.0,
            message='Missing YAML frontmatter opening delimiter',
            line=1,
            severity='critical'
        )

    # Find closing delimiter
    closing_line = None
    for i in range(1, min(50, len(lines))):
        if lines[i].strip() == '---':
            closing_line = i
            break

    if closing_line is None:
        return CheckResult(
            status='fail',
            score=0.0,
            message='Missing YAML frontmatter closing delimiter',
            line=1,
            severity='critical'
        )

    # Parse YAML
    yaml_content = '\n'.join(lines[1:closing_line])
    try:
        metadata = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        return CheckResult(
            status='fail',
            score=0.0,
            message=f'Invalid YAML syntax: {e}',
            line=e.problem_mark.line if hasattr(e, 'problem_mark') else 1,
            severity='critical'
        )

    # Validate required fields
    required_fields = ['name', 'description']
    missing_fields = [f for f in required_fields if f not in metadata]

    if missing_fields:
        return CheckResult(
            status='fail',
            score=0.5,
            message=f"Missing required fields: {', '.join(missing_fields)}",
            line_range=(1, closing_line),
            severity='critical'
        )

    # Validate field types
    issues = []
    if not isinstance(metadata.get('tools'), (list, type(None))):
        issues.append('tools must be list or null')
    if not isinstance(metadata.get('collaborates_with'), (list, type(None))):
        issues.append('collaborates_with must be list or null')

    if issues:
        return CheckResult(
            status='warning',
            score=7.0,
            message='; '.join(issues),
            line_range=(1, closing_line),
            severity='major'
        )

    return CheckResult(
        status='pass',
        score=10.0,
        message='Valid YAML frontmatter',
        line_range=(1, closing_line),
        severity='info'
    )
```

**Scoring**:
- Pass (valid YAML, required fields): 10.0
- Warning (minor issues): 7.0
- Fail (invalid YAML or missing required): 0.0

**Thresholds**:
- **Pass**: Valid YAML with required fields (name, description)
- **Warning**: Valid YAML but field type issues
- **Fail**: Invalid YAML or missing required fields

#### 1.2 Early Actionability Check
```python
def check_early_actionability(content: str) -> CheckResult:
    """
    Verify first code example appears within 50 lines.

    Algorithm:
    1. Skip YAML frontmatter (lines 1 to first closing ---)
    2. Search for first code block (```)
    3. Calculate line number
    4. Compare against target (<50 lines)

    Scoring:
    - 10.0: First example at line <30
    - 8.0:  First example at lines 30-50
    - 6.0:  First example at lines 51-100
    - 4.0:  First example at lines 101-200
    - 0.0:  First example at line >200 or not found
    """
    lines = content.split('\n')

    # Find end of frontmatter
    frontmatter_end = 0
    for i, line in enumerate(lines):
        if i > 0 and line.strip() == '---':
            frontmatter_end = i
            break

    # Find first code block
    first_example_line = None
    for i in range(frontmatter_end + 1, len(lines)):
        if lines[i].strip().startswith('```'):
            first_example_line = i + 1  # 1-indexed
            break

    if first_example_line is None:
        return CheckResult(
            status='fail',
            score=0.0,
            message='No code examples found in entire file',
            severity='critical'
        )

    # Score based on position
    if first_example_line < 30:
        score = 10.0
        status = 'pass'
        severity = 'info'
    elif first_example_line <= 50:
        score = 8.0
        status = 'pass'
        severity = 'info'
    elif first_example_line <= 100:
        score = 6.0
        status = 'warning'
        severity = 'minor'
    elif first_example_line <= 200:
        score = 4.0
        status = 'warning'
        severity='major'
    else:
        score = 0.0
        status = 'fail'
        severity = 'critical'

    return CheckResult(
        status=status,
        score=score,
        message=f'First example at line {first_example_line} (target: <50)',
        line=first_example_line,
        severity=severity,
        recommendation='Add quick-start example earlier' if score < 8.0 else None
    )
```

**Scoring**:
- **10.0**: First example within 30 lines
- **8.0**: First example within 31-50 lines
- **6.0**: First example within 51-100 lines
- **4.0**: First example within 101-200 lines
- **0.0**: First example after 200 lines or not found

**Recommendation**: Add quick-start example in first 50 lines (after frontmatter)

#### 1.3 File Length Check
```python
def check_file_length(content: str) -> CheckResult:
    """
    Verify agent file is within optimal length range.

    Target Ranges (excluding blank lines):
    - Optimal: 150-300 lines (most agents)
    - Acceptable: 100-500 lines
    - Warning: 50-99 or 501-800 lines
    - Fail: <50 or >800 lines

    Scoring:
    - 10.0: 150-300 lines (optimal)
    - 8.0:  100-149 or 301-500 lines (acceptable)
    - 6.0:  50-99 or 501-800 lines (warning)
    - 0.0:  <50 or >800 lines (fail)
    """
    lines = [l for l in content.split('\n') if l.strip()]  # Non-blank lines
    line_count = len(lines)

    if 150 <= line_count <= 300:
        return CheckResult(
            status='pass',
            score=10.0,
            message=f'{line_count} lines (optimal range)',
            severity='info'
        )
    elif (100 <= line_count < 150) or (300 < line_count <= 500):
        return CheckResult(
            status='pass',
            score=8.0,
            message=f'{line_count} lines (acceptable range)',
            severity='info'
        )
    elif (50 <= line_count < 100) or (500 < line_count <= 800):
        recommendation = (
            f'Consider splitting into multiple agents (current: {line_count} lines)'
            if line_count > 500
            else f'Add more examples and guidance (current: {line_count} lines)'
        )
        return CheckResult(
            status='warning',
            score=6.0,
            message=f'{line_count} lines (outside optimal range)',
            severity='minor',
            recommendation=recommendation
        )
    else:
        if line_count < 50:
            recommendation = f'Agent too brief ({line_count} lines). Add role description, examples, boundaries.'
        else:
            recommendation = f'Agent too long ({line_count} lines). Consider splitting into:\n' + \
                           f'  - {lines[0].strip()[5:].strip()} (core)\n' + \
                           f'  - {lines[0].strip()[5:].strip()}-advanced (specialized)'

        return CheckResult(
            status='fail',
            score=0.0,
            message=f'{line_count} lines (critical length issue)',
            severity='critical',
            recommendation=recommendation
        )
```

**Scoring**:
- **10.0**: 150-300 lines (optimal)
- **8.0**: 100-149 or 301-500 lines (acceptable)
- **6.0**: 50-99 or 501-800 lines (needs work)
- **0.0**: <50 or >800 lines (critical)

#### 1.4 Section Order Check
```python
def check_section_order(content: str) -> CheckResult:
    """
    Verify logical section progression.

    Expected Order:
    1. YAML frontmatter
    2. Role description (## Your Role / You are...)
    3. Quick start / Examples (within 50 lines)
    4. Detailed responsibilities
    5. Boundaries (ALWAYS/NEVER/ASK)
    6. Reference material

    Scoring:
    - 10.0: Perfect order
    - 7.0:  1-2 sections out of order
    - 4.0:  3+ sections out of order
    - 0.0:  Missing critical sections (role, boundaries)
    """
    lines = content.split('\n')

    # Extract section headers (## headings)
    sections = []
    for i, line in enumerate(lines):
        if line.startswith('## '):
            sections.append({
                'title': line[3:].strip().lower(),
                'line': i + 1
            })

    # Define expected patterns (flexible matching)
    expected_patterns = [
        r'(your role|you are)',  # Role definition
        r'(quick start|example|usage)',  # Early examples
        r'(responsibilit|capabilities|what you do)',  # Detailed role
        r'(always|never|boundaries|constraints)',  # Boundaries
        r'(reference|tools|integration)'  # Reference material
    ]

    # Check if critical sections exist
    section_titles = ' '.join([s['title'] for s in sections])

    has_role = re.search(expected_patterns[0], section_titles)
    has_boundaries = re.search(expected_patterns[3], section_titles)

    if not has_role or not has_boundaries:
        missing = []
        if not has_role:
            missing.append('Role description')
        if not has_boundaries:
            missing.append('Boundaries (ALWAYS/NEVER/ASK)')

        return CheckResult(
            status='fail',
            score=0.0,
            message=f"Missing critical sections: {', '.join(missing)}",
            severity='critical',
            recommendation='Add role description and boundaries sections'
        )

    # Check order (simplified - can be enhanced)
    # For MVP, just verify role comes first and boundaries exist
    if sections and re.search(expected_patterns[0], sections[0]['title']):
        return CheckResult(
            status='pass',
            score=10.0,
            message='Logical section order',
            severity='info'
        )
    else:
        return CheckResult(
            status='warning',
            score=7.0,
            message='Consider moving role description to first section',
            severity='minor',
            recommendation='Place "Your Role" or "You are..." section immediately after frontmatter'
        )
```

**Scoring**:
- **10.0**: Perfect section order (role → examples → details → boundaries → reference)
- **7.0**: 1-2 sections out of order
- **4.0**: 3+ sections out of order
- **0.0**: Missing critical sections

#### Structure Score Aggregation
```python
def calculate_structure_score(checks: List[CheckResult]) -> float:
    """
    Aggregate structure checks into single score.

    Weights:
    - YAML frontmatter: 30%
    - Early actionability: 25%
    - File length: 25%
    - Section order: 20%
    """
    weights = {
        'yaml_frontmatter': 0.30,
        'early_actionability': 0.25,
        'file_length': 0.25,
        'section_order': 0.20
    }

    weighted_sum = sum(
        checks[check_name].score * weight
        for check_name, weight in weights.items()
    )

    return weighted_sum
```

### 2. Example Density (25% weight)

**Purpose**: Ensure adequate code examples for learning and reference.

**Target**: 40-50% of content should be code examples.

#### 2.1 Code Block Percentage
```python
def check_example_density(content: str) -> CheckResult:
    """
    Calculate percentage of content that is code examples.

    Algorithm:
    1. Count total non-blank lines (exclude YAML frontmatter)
    2. Count lines inside ``` code blocks
    3. Calculate: (code_lines / total_lines) × 100
    4. Compare against target (40-50%)

    Scoring:
    - 10.0: 45-50% (optimal)
    - 8.0:  40-44% (good)
    - 6.0:  35-39% (acceptable)
    - 4.0:  30-34% (below target)
    - 2.0:  20-29% (poor)
    - 0.0:  <20% (critical)

    Returns:
        CheckResult with density percentage, gap analysis, recommendations
    """
    lines = content.split('\n')

    # Find end of YAML frontmatter
    frontmatter_end = 0
    in_frontmatter = False
    for i, line in enumerate(lines):
        if line.strip() == '---':
            if not in_frontmatter:
                in_frontmatter = True
            else:
                frontmatter_end = i
                break

    # Count total non-blank lines (after frontmatter)
    content_lines = [l for l in lines[frontmatter_end + 1:] if l.strip()]
    total_lines = len(content_lines)

    # Count code block lines
    code_lines = 0
    in_code_block = False
    for line in lines[frontmatter_end + 1:]:
        if line.strip().startswith('```'):
            in_code_block = not in_code_block
        elif in_code_block:
            code_lines += 1

    # Calculate density
    density = (code_lines / total_lines * 100) if total_lines > 0 else 0

    # Score based on density
    if 45 <= density <= 50:
        score = 10.0
        status = 'pass'
        severity = 'info'
        recommendation = None
    elif 40 <= density < 45:
        score = 8.0
        status = 'pass'
        severity = 'info'
        recommendation = f'Add ~{int((total_lines * 0.45) - code_lines)} more lines of examples to reach optimal 45%'
    elif 35 <= density < 40:
        score = 6.0
        status = 'warning'
        severity = 'minor'
        gap_lines = int((total_lines * 0.40) - code_lines)
        recommendation = f'Add {gap_lines} more lines of code examples (~{gap_lines // 10} examples @ 10 lines each)'
    elif 30 <= density < 35:
        score = 4.0
        status = 'warning'
        severity = 'major'
        gap_lines = int((total_lines * 0.40) - code_lines)
        recommendation = f'Add {gap_lines} more lines of code examples (~{gap_lines // 10} examples)'
    elif 20 <= density < 30:
        score = 2.0
        status = 'fail'
        severity = 'critical'
        gap_lines = int((total_lines * 0.40) - code_lines)
        recommendation = f'Critically low example density. Add {gap_lines} lines of examples.'
    else:
        score = 0.0
        status = 'fail'
        severity = 'critical'
        gap_lines = int((total_lines * 0.40) - code_lines)
        recommendation = f'Almost no code examples. Add {gap_lines} lines immediately.'

    return CheckResult(
        status=status,
        score=score,
        message=f'Example density: {density:.1f}% (target: 40-50%)',
        data={
            'density_percent': density,
            'code_lines': code_lines,
            'total_lines': total_lines,
            'gap_lines': max(0, int((total_lines * 0.40) - code_lines))
        },
        severity=severity,
        recommendation=recommendation
    )
```

#### 2.2 Example Count Check
```python
def check_example_count(content: str) -> CheckResult:
    """
    Verify minimum number of code examples (≥10).

    Algorithm:
    1. Count ``` code block pairs
    2. Exclude single-line code blocks (less useful)
    3. Compare against target (10+ examples)

    Scoring:
    - 10.0: ≥15 examples
    - 8.0:  10-14 examples
    - 6.0:  7-9 examples
    - 4.0:  5-6 examples
    - 0.0:  <5 examples
    """
    code_blocks = []
    in_code_block = False
    current_block = []

    for line in content.split('\n'):
        if line.strip().startswith('```'):
            if not in_code_block:
                in_code_block = True
                current_block = []
            else:
                in_code_block = False
                if len(current_block) > 1:  # Multi-line blocks only
                    code_blocks.append(current_block)
        elif in_code_block:
            current_block.append(line)

    example_count = len(code_blocks)

    if example_count >= 15:
        score = 10.0
        status = 'pass'
        severity = 'info'
        recommendation = None
    elif example_count >= 10:
        score = 8.0
        status = 'pass'
        severity = 'info'
        recommendation = f'Good example coverage. Add {15 - example_count} more for excellent rating.'
    elif example_count >= 7:
        score = 6.0
        status = 'warning'
        severity = 'minor'
        recommendation = f'Add {10 - example_count} more examples to reach target of 10'
    elif example_count >= 5:
        score = 4.0
        status = 'warning'
        severity = 'major'
        recommendation = f'Add {10 - example_count} more examples (current: {example_count})'
    else:
        score = 0.0
        status = 'fail'
        severity = 'critical'
        recommendation = f'Add {10 - example_count} examples immediately (current: {example_count})'

    return CheckResult(
        status=status,
        score=score,
        message=f'{example_count} code examples (target: ≥10)',
        data={'example_count': example_count},
        severity=severity,
        recommendation=recommendation
    )
```

#### 2.3 Example Format Check
```python
def check_example_format(content: str) -> CheckResult:
    """
    Verify code examples follow DO/DON'T comparison pattern.

    Algorithm:
    1. Count examples with ✅/❌ markers
    2. Check for balanced comparisons
    3. Verify language tags on code blocks

    Scoring:
    - 10.0: ≥70% examples use DO/DON'T format
    - 8.0:  50-69% use format
    - 6.0:  30-49% use format
    - 4.0:  <30% use format
    """
    lines = content.split('\n')

    # Find code blocks with markers
    do_dont_examples = 0
    total_examples = 0
    missing_lang_tags = []

    in_code_block = False
    code_block_line = 0
    has_lang_tag = False

    for i, line in enumerate(lines):
        if line.strip().startswith('```'):
            if not in_code_block:
                in_code_block = True
                code_block_line = i + 1
                # Check for language tag
                has_lang_tag = len(line.strip()) > 3
                total_examples += 1
            else:
                in_code_block = False
                if not has_lang_tag:
                    missing_lang_tags.append(code_block_line)

        # Look for DO/DON'T markers near code blocks
        if '✅' in line or '❌' in line or 'DO:' in line or "DON'T:" in line:
            # Check if within 3 lines of code block
            for j in range(max(0, i - 3), min(len(lines), i + 3)):
                if lines[j].strip().startswith('```'):
                    do_dont_examples += 1
                    break

    # Remove duplicates from do_dont_examples (might count same block twice)
    do_dont_examples = min(do_dont_examples, total_examples)

    format_percentage = (do_dont_examples / total_examples * 100) if total_examples > 0 else 0

    if format_percentage >= 70:
        score = 10.0
        status = 'pass'
        severity = 'info'
    elif format_percentage >= 50:
        score = 8.0
        status = 'pass'
        severity = 'info'
    elif format_percentage >= 30:
        score = 6.0
        status = 'warning'
        severity = 'minor'
    else:
        score = 4.0
        status = 'warning'
        severity = 'major'

    issues = []
    if missing_lang_tags:
        issues.append(
            f'{len(missing_lang_tags)} code blocks missing language tags (lines: {", ".join(map(str, missing_lang_tags[:5]))}{"..." if len(missing_lang_tags) > 5 else ""})'
        )

    if format_percentage < 50:
        issues.append(
            f'Only {format_percentage:.0f}% of examples use DO/DON\'T comparison format'
        )

    return CheckResult(
        status=status,
        score=score,
        message=f'{do_dont_examples}/{total_examples} examples use DO/DON\'T format ({format_percentage:.0f}%)',
        data={
            'do_dont_count': do_dont_examples,
            'total_examples': total_examples,
            'format_percentage': format_percentage,
            'missing_lang_tags': missing_lang_tags
        },
        severity=severity,
        recommendation=issues[0] if issues else None
    )
```

#### Example Density Score Aggregation
```python
def calculate_example_density_score(checks: List[CheckResult]) -> float:
    """
    Aggregate example checks into single score.

    Weights:
    - Code block percentage: 50%
    - Example count: 30%
    - Example format: 20%
    """
    weights = {
        'code_block_percentage': 0.50,
        'example_count': 0.30,
        'example_format': 0.20
    }

    return sum(
        checks[name].score * weight
        for name, weight in weights.items()
    )
```

### 3. Boundary Clarity (20% weight)

**Purpose**: Ensure clear constraints (ALWAYS/NEVER/ASK sections).

#### 3.1 ALWAYS Section Check
```python
def check_always_section(content: str) -> CheckResult:
    """
    Verify ALWAYS section with 5-7 non-negotiable rules.

    Algorithm:
    1. Search for section with 'ALWAYS' in heading or list prefix
    2. Count items (bullet points, numbered list)
    3. Verify items are specific and actionable
    4. Check against target (5-7 items)

    Scoring:
    - 10.0: 5-7 items, all specific
    - 8.0:  4 or 8 items, all specific
    - 6.0:  3 or 9-10 items, mostly specific
    - 4.0:  <3 or >10 items
    - 0.0:  Section missing
    """
    lines = content.split('\n')

    # Find ALWAYS section
    always_section_start = None
    always_section_end = None

    for i, line in enumerate(lines):
        # Look for heading or list with ALWAYS
        if 'ALWAYS' in line.upper() and (line.startswith('#') or line.strip().startswith('**')):
            always_section_start = i
        elif always_section_start and line.startswith('#'):
            # Next section found
            always_section_end = i
            break

    if always_section_start is None:
        return CheckResult(
            status='fail',
            score=0.0,
            message='ALWAYS section not found',
            severity='critical',
            recommendation='Add ALWAYS section with 5-7 non-negotiable rules'
        )

    if always_section_end is None:
        always_section_end = len(lines)

    # Count items in section
    section_content = lines[always_section_start:always_section_end]
    items = [l for l in section_content if l.strip().startswith(('-', '*', '1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.'))]
    item_count = len(items)

    # Check specificity (basic heuristic: item should be >20 chars)
    specific_items = [i for i in items if len(i.strip()) > 30]
    specificity = len(specific_items) / item_count if item_count > 0 else 0

    if 5 <= item_count <= 7 and specificity >= 0.8:
        score = 10.0
        status = 'pass'
        severity = 'info'
        recommendation = None
    elif (item_count == 4 or item_count == 8) and specificity >= 0.8:
        score = 8.0
        status = 'pass'
        severity = 'info'
        recommendation = f'Consider {"adding" if item_count == 4 else "removing"} {abs(6 - item_count)} item to reach optimal 5-7'
    elif (item_count == 3 or 9 <= item_count <= 10) and specificity >= 0.6:
        score = 6.0
        status = 'warning'
        severity = 'minor'
        recommendation = f'Adjust to 5-7 items (current: {item_count})'
    elif item_count < 3 or item_count > 10:
        score = 4.0
        status = 'warning'
        severity = 'major'
        recommendation = f'Target 5-7 items (current: {item_count}). Too {"few" if item_count < 5 else "many"} constraints.'
    else:
        score = 4.0
        status = 'warning'
        severity = 'major'
        recommendation = f'Make items more specific (only {int(specificity * 100)}% are detailed enough)'

    return CheckResult(
        status=status,
        score=score,
        message=f'ALWAYS section: {item_count} items (target: 5-7)',
        line_range=(always_section_start + 1, always_section_end),
        data={
            'item_count': item_count,
            'specificity': specificity,
            'items': [i.strip() for i in items[:3]]  # First 3 for inspection
        },
        severity=severity,
        recommendation=recommendation
    )
```

#### 3.2 NEVER Section Check
```python
def check_never_section(content: str) -> CheckResult:
    """
    Verify NEVER section with 5-7 prohibited actions.

    Same algorithm as ALWAYS section check.
    """
    # Implementation mirrors check_always_section()
    # Search for 'NEVER' instead of 'ALWAYS'
    # Same scoring criteria (5-7 items optimal)
    pass  # See check_always_section for implementation pattern
```

#### 3.3 ASK Section Check
```python
def check_ask_section(content: str) -> CheckResult:
    """
    Verify ASK section with 3-5 escalation triggers.

    Algorithm:
    1. Search for section with 'ASK' or 'ESCALATE' in heading
    2. Count items
    3. Check against target (3-5 items)

    Scoring:
    - 10.0: 3-5 items
    - 8.0:  2 or 6 items
    - 6.0:  1 or 7-8 items
    - 0.0:  Section missing or >8 items
    """
    # Implementation mirrors ALWAYS/NEVER checks
    # Target: 3-5 items (slightly lower than ALWAYS/NEVER)
    pass
```

#### Boundary Clarity Score Aggregation
```python
def calculate_boundary_clarity_score(checks: List[CheckResult]) -> float:
    """
    Aggregate boundary checks into single score.

    Weights:
    - ALWAYS section: 35%
    - NEVER section: 35%
    - ASK section: 30%
    """
    weights = {
        'always_section': 0.35,
        'never_section': 0.35,
        'ask_section': 0.30
    }

    return sum(
        checks[name].score * weight
        for name, weight in weights.items()
    )
```

### 4. Specificity (20% weight)

**Purpose**: Ensure role-specific, actionable content (not generic).

#### 4.1 Generic Language Detection
```python
def detect_generic_language(content: str) -> CheckResult:
    """
    Flag generic phrases that should be replaced with specifics.

    Generic Patterns to Detect:
    - "helpful assistant"
    - "best practices"
    - "modern frameworks"
    - "industry standards"
    - "as appropriate"
    - "where necessary"

    Algorithm:
    1. Define generic phrase patterns (regex)
    2. Search content for matches
    3. Record line numbers
    4. Score based on frequency

    Scoring:
    - 10.0: 0 generic phrases
    - 8.0:  1-2 generic phrases
    - 6.0:  3-4 generic phrases
    - 4.0:  5-6 generic phrases
    - 0.0:  >6 generic phrases
    """
    generic_patterns = [
        (r'\bhelpful assistant\b', 'helpful assistant', 'role-specific description (e.g., "code quality enforcer")'),
        (r'\bbest practices?\b', 'best practices', 'specific practices (e.g., "SOLID compliance", "DRY principle")'),
        (r'\bmodern frameworks?\b', 'modern frameworks', 'specific frameworks (e.g., "React 18", "FastAPI 0.104")'),
        (r'\bindustry standards?\b', 'industry standards', 'specific standards (e.g., "OWASP Top 10", "PCI-DSS")'),
        (r'\bas appropriate\b', 'as appropriate', 'specific criteria (e.g., "when complexity >7")'),
        (r'\bwhere necessary\b', 'where necessary', 'specific conditions'),
        (r'\breturn high.quality (code|output|results?)\b', 'high-quality', 'measurable quality (e.g., ">80% coverage", "0 security vulnerabilities")'),
    ]

    lines = content.split('\n')
    findings = []

    for pattern, phrase, suggestion in generic_patterns:
        for i, line in enumerate(lines):
            matches = re.finditer(pattern, line, re.IGNORECASE)
            for match in matches:
                findings.append({
                    'line': i + 1,
                    'phrase': phrase,
                    'suggestion': suggestion,
                    'context': line.strip()[:60]
                })

    finding_count = len(findings)

    if finding_count == 0:
        score = 10.0
        status = 'pass'
        severity = 'info'
        recommendation = None
    elif finding_count <= 2:
        score = 8.0
        status = 'pass'
        severity = 'info'
        recommendation = f'Replace {finding_count} generic phrase(s) with specific terminology'
    elif finding_count <= 4:
        score = 6.0
        status = 'warning'
        severity = 'minor'
        recommendation = f'Replace {finding_count} generic phrases with role-specific language'
    elif finding_count <= 6:
        score = 4.0
        status = 'warning'
        severity = 'major'
        recommendation = f'High generic language usage ({finding_count} instances). Be more specific.'
    else:
        score = 0.0
        status = 'fail'
        severity = 'critical'
        recommendation = f'Excessive generic language ({finding_count} instances). Rewrite with specific terminology.'

    return CheckResult(
        status=status,
        score=score,
        message=f'{finding_count} generic phrase(s) detected',
        data={'findings': findings[:10]},  # Top 10 findings
        severity=severity,
        recommendation=recommendation
    )
```

#### 4.2 Role Clarity Check
```python
def check_role_clarity(content: str, filename: str) -> CheckResult:
    """
    Verify agent name matches description and content.

    Algorithm:
    1. Extract agent name from filename (e.g., code-reviewer.md → code-reviewer)
    2. Extract description from YAML frontmatter
    3. Check if name appears in first 100 lines
    4. Verify description is specific (>20 chars, contains domain terms)

    Scoring:
    - 10.0: Perfect alignment (name in content, specific description)
    - 8.0:  Good alignment (name in content OR specific description)
    - 6.0:  Weak alignment (generic description)
    - 0.0:  No alignment (name not mentioned, generic description)
    """
    # Extract agent name from filename
    agent_name = Path(filename).stem  # e.g., "code-reviewer"

    # Parse YAML frontmatter
    lines = content.split('\n')
    frontmatter_content = []
    in_frontmatter = False

    for line in lines:
        if line.strip() == '---':
            if not in_frontmatter:
                in_frontmatter = True
            else:
                break
        elif in_frontmatter:
            frontmatter_content.append(line)

    try:
        metadata = yaml.safe_load('\n'.join(frontmatter_content))
        description = metadata.get('description', '')
    except:
        description = ''

    # Check name in early content (first 100 lines)
    early_content = '\n'.join(lines[:100]).lower()
    name_parts = agent_name.split('-')
    name_appears = all(part in early_content for part in name_parts)

    # Check description specificity
    description_specific = len(description) > 30 and any(
        keyword in description.lower()
        for keyword in ['review', 'test', 'architecture', 'security', 'quality', 'validate', 'enforce']
    )

    if name_appears and description_specific:
        score = 10.0
        status = 'pass'
        severity = 'info'
        recommendation = None
    elif name_appears or description_specific:
        score = 8.0
        status = 'pass'
        severity = 'info'
        recommendation = 'Strengthen role description' if not description_specific else 'Mention agent name in role description'
    elif description:
        score = 6.0
        status = 'warning'
        severity = 'minor'
        recommendation = f'Make description more specific (current: "{description}")'
    else:
        score = 0.0
        status = 'fail'
        severity = 'critical'
        recommendation = 'Add specific role description in YAML frontmatter'

    return CheckResult(
        status=status,
        score=score,
        message=f'Role clarity: {agent_name}',
        data={
            'agent_name': agent_name,
            'description': description,
            'name_appears_early': name_appears
        },
        severity=severity,
        recommendation=recommendation
    )
```

#### 4.3 Technology Specificity Check
```python
def check_technology_specificity(content: str) -> CheckResult:
    """
    Verify specific technology/version mentions (not generic).

    Algorithm:
    1. Search for technology mentions (React, Python, .NET, etc.)
    2. Check if versions are specified (e.g., "Python 3.11+", "React 18")
    3. Flag generic terms ("modern frameworks", "latest version")
    4. Score based on specificity

    Scoring:
    - 10.0: All technologies have versions
    - 8.0:  Most technologies have versions (>70%)
    - 6.0:  Some technologies have versions (40-70%)
    - 4.0:  Few technologies have versions (<40%)
    """
    # Technology patterns (with and without versions)
    tech_patterns = {
        'Python': r'Python\s*\d+\.\d+',
        'React': r'React\s*\d+',
        'TypeScript': r'TypeScript\s*\d+',
        '.NET': r'\.NET\s*\d+',
        'Node.js': r'Node\.js\s*\d+',
        'FastAPI': r'FastAPI\s*\d+',
        'Next.js': r'Next\.js\s*\d+',
    }

    tech_mentions = {}
    tech_with_versions = {}

    for tech, pattern_with_version in tech_patterns.items():
        # Search for technology name (case-insensitive)
        mentions = len(re.findall(tech, content, re.IGNORECASE))
        if mentions > 0:
            tech_mentions[tech] = mentions

            # Check if version specified
            versioned = len(re.findall(pattern_with_version, content))
            tech_with_versions[tech] = versioned

    if not tech_mentions:
        # Language-agnostic agent (acceptable)
        return CheckResult(
            status='pass',
            score=10.0,
            message='Language-agnostic agent (no specific technologies)',
            severity='info'
        )

    total_techs = len(tech_mentions)
    versioned_techs = len([t for t, count in tech_with_versions.items() if count > 0])
    specificity = versioned_techs / total_techs if total_techs > 0 else 0

    if specificity >= 0.70:
        score = 10.0
        status = 'pass'
        severity = 'info'
        recommendation = None
    elif specificity >= 0.40:
        score = 8.0
        status = 'pass'
        severity = 'info'
        missing = [t for t in tech_mentions if tech_with_versions.get(t, 0) == 0]
        recommendation = f'Add versions to: {", ".join(missing)}'
    elif specificity >= 0.20:
        score = 6.0
        status = 'warning'
        severity = 'minor'
        missing = [t for t in tech_mentions if tech_with_versions.get(t, 0) == 0]
        recommendation = f'Add versions to: {", ".join(missing)}'
    else:
        score = 4.0
        status = 'warning'
        severity = 'major'
        recommendation = f'Specify versions for all technologies (currently {int(specificity * 100)}% have versions)'

    return CheckResult(
        status=status,
        score=score,
        message=f'{versioned_techs}/{total_techs} technologies have versions ({int(specificity * 100)}%)',
        data={
            'tech_mentions': tech_mentions,
            'tech_with_versions': tech_with_versions
        },
        severity=severity,
        recommendation=recommendation
    )
```

#### Specificity Score Aggregation
```python
def calculate_specificity_score(checks: List[CheckResult]) -> float:
    """
    Aggregate specificity checks into single score.

    Weights:
    - Generic language: 40%
    - Role clarity: 35%
    - Technology specificity: 25%
    """
    weights = {
        'generic_language': 0.40,
        'role_clarity': 0.35,
        'technology_specificity': 0.25
    }

    return sum(
        checks[name].score * weight
        for name, weight in weights.items()
    )
```

### 5. Code Example Quality (15% weight)

**Purpose**: Ensure examples are real-world, complete, and well-explained.

#### 5.1 Example Completeness Check
```python
def check_example_completeness(content: str) -> CheckResult:
    """
    Verify code examples are complete and runnable.

    Algorithm:
    1. Extract all code blocks
    2. Check for common incompleteness markers:
        - "..." (ellipsis)
        - "// TODO"
        - "// etc."
        - Single-line examples (usually incomplete)
    3. Calculate completeness percentage

    Scoring:
    - 10.0: ≥90% examples are complete
    - 8.0:  80-89% complete
    - 6.0:  70-79% complete
    - 4.0:  <70% complete
    """
    code_blocks = []
    in_code_block = False
    current_block = []

    for line in content.split('\n'):
        if line.strip().startswith('```'):
            if not in_code_block:
                in_code_block = True
                current_block = []
            else:
                in_code_block = False
                code_blocks.append('\n'.join(current_block))
        elif in_code_block:
            current_block.append(line)

    if not code_blocks:
        return CheckResult(
            status='fail',
            score=0.0,
            message='No code examples found',
            severity='critical'
        )

    # Check each block for completeness markers
    incomplete_markers = ['...', '// TODO', '// etc.', '# TODO', '# ...']
    complete_count = 0

    for block in code_blocks:
        # Single-line blocks are usually incomplete
        if len(block.split('\n')) <= 1:
            continue

        # Check for incompleteness markers
        has_incomplete_marker = any(marker in block for marker in incomplete_markers)
        if not has_incomplete_marker:
            complete_count += 1

    completeness = complete_count / len(code_blocks) if code_blocks else 0

    if completeness >= 0.90:
        score = 10.0
        status = 'pass'
        severity = 'info'
    elif completeness >= 0.80:
        score = 8.0
        status = 'pass'
        severity = 'info'
    elif completeness >= 0.70:
        score = 6.0
        status = 'warning'
        severity = 'minor'
    else:
        score = 4.0
        status = 'warning'
        severity = 'major'

    return CheckResult(
        status=status,
        score=score,
        message=f'{complete_count}/{len(code_blocks)} examples are complete ({int(completeness * 100)}%)',
        data={'completeness': completeness},
        severity=severity,
        recommendation=f'Complete {len(code_blocks) - complete_count} incomplete examples' if completeness < 0.90 else None
    )
```

#### 5.2 Example Context Check
```python
def check_example_context(content: str) -> CheckResult:
    """
    Verify code examples have explanatory context.

    Algorithm:
    1. For each code block, check surrounding lines (±3)
    2. Look for explanatory text, comments, or headings
    3. Score based on percentage with context

    Scoring:
    - 10.0: ≥90% examples have context
    - 8.0:  80-89% have context
    - 6.0:  70-79% have context
    - 4.0:  <70% have context
    """
    lines = content.split('\n')
    code_block_positions = []

    # Find all code block positions
    for i, line in enumerate(lines):
        if line.strip().startswith('```'):
            code_block_positions.append(i)

    # Group into pairs (start, end)
    code_blocks = []
    for i in range(0, len(code_block_positions), 2):
        if i + 1 < len(code_block_positions):
            code_blocks.append((code_block_positions[i], code_block_positions[i + 1]))

    # Check for context around each block
    blocks_with_context = 0

    for start, end in code_blocks:
        # Check 3 lines before
        context_before = '\n'.join(lines[max(0, start - 3):start])
        # Check 3 lines after
        context_after = '\n'.join(lines[end + 1:min(len(lines), end + 4)])

        # Context indicators: headings, explanatory text (>20 chars), comments
        has_context = (
            len(context_before.strip()) > 20 or
            len(context_after.strip()) > 20 or
            '##' in context_before or
            '#' in context_before
        )

        if has_context:
            blocks_with_context += 1

    context_percentage = blocks_with_context / len(code_blocks) if code_blocks else 0

    if context_percentage >= 0.90:
        score = 10.0
        status = 'pass'
        severity = 'info'
    elif context_percentage >= 0.80:
        score = 8.0
        status = 'pass'
        severity = 'info'
    elif context_percentage >= 0.70:
        score = 6.0
        status = 'warning'
        severity = 'minor'
    else:
        score = 4.0
        status = 'warning'
        severity = 'major'

    return CheckResult(
        status=status,
        score=score,
        message=f'{blocks_with_context}/{len(code_blocks)} examples have context ({int(context_percentage * 100)}%)',
        data={'context_percentage': context_percentage},
        severity=severity,
        recommendation=f'Add explanatory text to {len(code_blocks) - blocks_with_context} examples' if context_percentage < 0.90 else None
    )
```

#### Code Example Quality Score Aggregation
```python
def calculate_code_quality_score(checks: List[CheckResult]) -> float:
    """
    Aggregate code quality checks into single score.

    Weights:
    - Example completeness: 60%
    - Example context: 40%
    """
    weights = {
        'example_completeness': 0.60,
        'example_context': 0.40
    }

    return sum(
        checks[name].score * weight
        for name, weight in weights.items()
    )
```

### 6. Maintenance Indicators (5% weight)

**Purpose**: Track freshness and completeness.

#### 6.1 Last Updated Check
```python
def check_last_updated(content: str) -> CheckResult:
    """
    Verify 'updated' field in YAML frontmatter.

    Algorithm:
    1. Parse YAML frontmatter
    2. Check for 'updated' field
    3. Validate date format (YYYY-MM-DD)
    4. Check recency (within 6 months = fresh)

    Scoring:
    - 10.0: Updated within last 3 months
    - 8.0:  Updated within last 6 months
    - 6.0:  Updated within last year
    - 4.0:  Updated >1 year ago
    - 0.0:  No updated field
    """
    lines = content.split('\n')
    frontmatter_content = []
    in_frontmatter = False

    for line in lines:
        if line.strip() == '---':
            if not in_frontmatter:
                in_frontmatter = True
            else:
                break
        elif in_frontmatter:
            frontmatter_content.append(line)

    try:
        metadata = yaml.safe_load('\n'.join(frontmatter_content))
        updated_str = metadata.get('updated', '')
    except:
        updated_str = ''

    if not updated_str:
        return CheckResult(
            status='warning',
            score=0.0,
            message='No "updated" field in frontmatter',
            severity='minor',
            recommendation='Add "updated: YYYY-MM-DD" to YAML frontmatter'
        )

    # Parse date
    try:
        from datetime import datetime
        updated_date = datetime.fromisoformat(str(updated_str))
        days_old = (datetime.now() - updated_date).days

        if days_old <= 90:  # 3 months
            score = 10.0
            status = 'pass'
            severity = 'info'
            recommendation = None
        elif days_old <= 180:  # 6 months
            score = 8.0
            status = 'pass'
            severity = 'info'
            recommendation = f'Last updated {days_old} days ago (consider refresh)'
        elif days_old <= 365:  # 1 year
            score = 6.0
            status = 'warning'
            severity = 'minor'
            recommendation = f'Last updated {days_old} days ago (due for refresh)'
        else:
            score = 4.0
            status = 'warning'
            severity = 'major'
            recommendation = f'Last updated {days_old} days ago (outdated - needs refresh)'

        return CheckResult(
            status=status,
            score=score,
            message=f'Last updated {days_old} days ago',
            data={'updated_date': updated_str, 'days_old': days_old},
            severity=severity,
            recommendation=recommendation
        )
    except:
        return CheckResult(
            status='warning',
            score=4.0,
            message=f'Invalid date format: {updated_str}',
            severity='major',
            recommendation='Use YYYY-MM-DD format for "updated" field'
        )
```

#### 6.2 Completeness Check
```python
def check_completeness(content: str) -> CheckResult:
    """
    Verify no TODO or placeholder sections.

    Algorithm:
    1. Search for TODO, FIXME, TBD markers
    2. Search for placeholder text ([Add description])
    3. Count occurrences

    Scoring:
    - 10.0: No placeholders
    - 6.0:  1-2 placeholders
    - 0.0:  3+ placeholders
    """
    placeholder_patterns = [
        r'\bTODO\b',
        r'\bFIXME\b',
        r'\bTBD\b',
        r'\[Add .+?\]',
        r'\[To be .+?\]',
        r'\[Coming soon\]',
    ]

    lines = content.split('\n')
    findings = []

    for i, line in enumerate(lines):
        for pattern in placeholder_patterns:
            matches = re.finditer(pattern, line, re.IGNORECASE)
            for match in matches:
                findings.append({
                    'line': i + 1,
                    'text': match.group(0),
                    'context': line.strip()[:60]
                })

    if len(findings) == 0:
        score = 10.0
        status = 'pass'
        severity = 'info'
        recommendation = None
    elif len(findings) <= 2:
        score = 6.0
        status = 'warning'
        severity = 'minor'
        recommendation = f'Complete {len(findings)} placeholder section(s)'
    else:
        score = 0.0
        status = 'fail'
        severity = 'critical'
        recommendation = f'Complete {len(findings)} placeholder sections before production'

    return CheckResult(
        status=status,
        score=score,
        message=f'{len(findings)} placeholder(s) found',
        data={'findings': findings},
        severity=severity,
        recommendation=recommendation
    )
```

#### Maintenance Score Aggregation
```python
def calculate_maintenance_score(checks: List[CheckResult]) -> float:
    """
    Aggregate maintenance checks into single score.

    Weights:
    - Last updated: 60%
    - Completeness: 40%
    """
    weights = {
        'last_updated': 0.60,
        'completeness': 0.40
    }

    return sum(
        checks[name].score * weight
        for name, weight in weights.items()
    )
```

## Output Formats

### Console Output (Human-Readable)

See example in requirements section above. Format:
- Unicode box drawing characters (━ ─ │)
- Color coding (requires ANSI support):
  - ✅ Green for pass
  - ⚠️ Yellow for warning
  - ❌ Red for fail
- Sections clearly separated
- Line numbers for issues
- Actionable recommendations with impact estimates

### JSON Output (Machine-Readable)

```json
{
  "file": "installer/global/agents/code-reviewer.md",
  "lines": 595,
  "timestamp": "2025-11-21T10:30:00Z",
  "overall_score": 7.2,
  "status": "production_ready_with_improvements",
  "grade": "B",
  "scores": {
    "structure": {
      "score": 8.5,
      "weight": 0.15,
      "checks": {
        "yaml_frontmatter": {
          "score": 10.0,
          "status": "pass",
          "message": "Valid YAML frontmatter",
          "line_range": [1, 11]
        },
        "early_actionability": {
          "score": 8.0,
          "status": "pass",
          "message": "First example at line 28",
          "line": 28
        },
        "file_length": {
          "score": 6.0,
          "status": "warning",
          "message": "595 lines (outside optimal range)",
          "recommendation": "Consider splitting into code-reviewer (core) and code-reviewer-advanced"
        },
        "section_order": {
          "score": 10.0,
          "status": "pass",
          "message": "Logical section order"
        }
      }
    },
    "example_density": {
      "score": 6.0,
      "weight": 0.25,
      "checks": {
        "code_block_percentage": {
          "score": 4.0,
          "status": "warning",
          "message": "30% (target: 40-50%)",
          "data": {
            "density_percent": 30.0,
            "code_lines": 178,
            "total_lines": 595,
            "gap_lines": 60
          },
          "recommendation": "Add 60 more lines of code examples (~12 examples)"
        },
        "example_count": {
          "score": 10.0,
          "status": "pass",
          "message": "18 examples (target: ≥10)"
        },
        "example_format": {
          "score": 6.0,
          "status": "warning",
          "message": "6 code blocks missing language tags",
          "data": {
            "missing_lang_tags": [145, 203, 287, 334, 412, 501]
          }
        }
      }
    },
    "boundary_clarity": {
      "score": 9.0,
      "weight": 0.20,
      "checks": {
        "always_section": {
          "score": 10.0,
          "status": "pass",
          "message": "7 items (target: 5-7)"
        },
        "never_section": {
          "score": 8.0,
          "status": "pass",
          "message": "6 items (target: 5-7)"
        },
        "ask_section": {
          "score": 10.0,
          "status": "pass",
          "message": "4 items (target: 3-5)"
        }
      }
    },
    "specificity": {
      "score": 7.5,
      "weight": 0.20,
      "checks": {
        "generic_language": {
          "score": 6.0,
          "status": "warning",
          "message": "3 generic phrases detected",
          "data": {
            "findings": [
              {
                "line": 45,
                "phrase": "helpful assistant",
                "suggestion": "role-specific description",
                "context": "You are a helpful assistant who reviews code..."
              },
              {
                "line": 67,
                "phrase": "best practices",
                "suggestion": "specific practices (e.g., SOLID compliance)",
                "context": "Follow best practices for code quality"
              },
              {
                "line": 123,
                "phrase": "modern frameworks",
                "suggestion": "specific frameworks (e.g., React 18, Next.js 14)",
                "context": "Support for modern frameworks"
              }
            ]
          }
        },
        "role_clarity": {
          "score": 10.0,
          "status": "pass",
          "message": "Strong role alignment"
        },
        "technology_specificity": {
          "score": 8.0,
          "status": "pass",
          "message": "3/4 technologies have versions (75%)"
        }
      }
    },
    "code_quality": {
      "score": 7.0,
      "weight": 0.15,
      "checks": {
        "example_completeness": {
          "score": 8.0,
          "status": "pass",
          "message": "16/18 examples are complete (88%)"
        },
        "example_context": {
          "score": 6.0,
          "status": "warning",
          "message": "14/18 examples have context (77%)"
        }
      }
    },
    "maintenance": {
      "score": 7.0,
      "weight": 0.05,
      "checks": {
        "last_updated": {
          "score": 0.0,
          "status": "warning",
          "message": "No 'updated' field in frontmatter",
          "recommendation": "Add 'updated: 2025-11-21' to YAML"
        },
        "completeness": {
          "score": 10.0,
          "status": "pass",
          "message": "0 placeholders found"
        }
      }
    }
  },
  "issues": [
    {
      "severity": "critical",
      "category": "example_density",
      "check": "code_block_percentage",
      "message": "Example density 30% below target 40-50%",
      "line": null,
      "suggestion": "Add 60 more lines of code examples (~12 examples)",
      "impact": "+2.0 points"
    },
    {
      "severity": "major",
      "category": "specificity",
      "check": "generic_language",
      "message": "Generic language: 'helpful assistant'",
      "line": 45,
      "suggestion": "Replace with 'code quality enforcer'",
      "impact": "+0.3 points"
    },
    {
      "severity": "major",
      "category": "specificity",
      "check": "generic_language",
      "message": "Generic language: 'best practices'",
      "line": 67,
      "suggestion": "Replace with 'SOLID compliance checks'",
      "impact": "+0.3 points"
    },
    {
      "severity": "minor",
      "category": "example_density",
      "check": "example_format",
      "message": "Code blocks missing language tags",
      "lines": [145, 203, 287, 334, 412, 501],
      "suggestion": "Add language tags (```python, ```typescript, etc.)",
      "impact": "+0.5 points"
    }
  ],
  "recommendations": [
    {
      "priority": "P1",
      "category": "example_density",
      "action": "Increase example density to 40%",
      "current": "30% (178 lines)",
      "target": "40% (238 lines)",
      "gap": "60 lines (~12 examples)",
      "impact": "+2.0 points (7.2 → 9.2)",
      "estimated_time_minutes": 30
    },
    {
      "priority": "P2",
      "category": "specificity",
      "action": "Replace generic language",
      "details": [
        {"line": 45, "replace": "helpful assistant → code quality enforcer"},
        {"line": 67, "replace": "best practices → SOLID compliance checks"},
        {"line": 123, "replace": "modern frameworks → React 18, Next.js 14"}
      ],
      "impact": "+0.8 points (specificity: 7.5 → 8.3)",
      "estimated_time_minutes": 10
    },
    {
      "priority": "P3",
      "category": "example_density",
      "action": "Add language tags to code blocks",
      "lines": [145, 203, 287, 334, 412, 501],
      "impact": "+0.5 points (examples: 6.0 → 6.5)",
      "estimated_time_minutes": 5
    },
    {
      "priority": "P4",
      "category": "maintenance",
      "action": "Add updated date to frontmatter",
      "details": "Add 'updated: 2025-11-21'",
      "impact": "+0.3 points (maintenance: 7.0 → 7.3)",
      "estimated_time_minutes": 1
    }
  ],
  "next_steps": {
    "target_score": 8.5,
    "target_grade": "A-",
    "actions": [
      "Run: /agent-enhance code-reviewer --fix-density",
      "Manually replace generic terms (lines 45, 67, 123)",
      "Add language tags to code blocks",
      "Re-validate: /agent-validate code-reviewer.md"
    ],
    "estimated_time_minutes": 45,
    "expected_score": 8.7
  }
}
```

### Minimal Output (CI/CD)

```json
{
  "file": "code-reviewer.md",
  "score": 7.2,
  "status": "pass_with_warnings",
  "threshold": 7.0,
  "issues_critical": 1,
  "issues_major": 2,
  "issues_minor": 1
}
```

## Exit Codes

| Code | Meaning | When Used |
|------|---------|-----------|
| 0 | Success | Validation completed, score ≥ threshold |
| 1 | Failure | Score < threshold (when `--exit-on-fail` used) |
| 2 | Invalid Arguments | Missing required arguments, invalid file path |
| 3 | File Not Found | Agent file doesn't exist |
| 4 | Parse Error | Cannot parse YAML frontmatter or markdown |

## Implementation Architecture

### File Structure

```
installer/global/commands/
├── agent-validate.md                    # This specification
├── agent-validate-batch.md              # Batch variant specification
└── lib/
    └── agent_validator/
        ├── __init__.py
        ├── validator.py                  # Main validator orchestrator
        ├── checks/
        │   ├── __init__.py
        │   ├── structure.py              # Structure validation checks
        │   ├── examples.py               # Example density checks
        │   ├── boundaries.py             # Boundary clarity checks
        │   ├── specificity.py            # Specificity checks
        │   ├── code_quality.py           # Code example quality checks
        │   └── maintenance.py            # Maintenance indicator checks
        ├── models.py                     # Data models (CheckResult, ValidationReport)
        ├── scoring.py                    # Score calculation and aggregation
        ├── formatters/
        │   ├── __init__.py
        │   ├── console.py                # Console output formatter
        │   ├── json_formatter.py         # JSON output formatter
        │   └── table.py                  # Table formatter (for batch)
        └── utils.py                      # Utility functions
```

### Core Classes

```python
# models.py
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum

class CheckStatus(Enum):
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"

class Severity(Enum):
    INFO = "info"
    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"

@dataclass
class CheckResult:
    """Result of a single validation check."""
    status: CheckStatus
    score: float  # 0.0-10.0
    message: str
    severity: Severity
    line: Optional[int] = None
    line_range: Optional[tuple] = None
    data: Optional[Dict[str, Any]] = None
    recommendation: Optional[str] = None

@dataclass
class CategoryScore:
    """Aggregated score for a check category."""
    name: str
    score: float
    weight: float
    checks: Dict[str, CheckResult]

@dataclass
class ValidationReport:
    """Complete validation report."""
    file_path: str
    line_count: int
    timestamp: str
    overall_score: float
    grade: str  # A+, A, A-, B+, B, C, D, F
    status: str  # excellent, good, acceptable, below_standard, poor, unacceptable
    category_scores: Dict[str, CategoryScore]
    issues: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    next_steps: Optional[Dict[str, Any]] = None

# validator.py
class AgentValidator:
    """Main validator orchestrator."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.checks = self._initialize_checks()

    def validate(self, file_path: str, checks_filter: Optional[List[str]] = None) -> ValidationReport:
        """
        Run validation on agent file.

        Args:
            file_path: Path to agent markdown file
            checks_filter: Optional list of check categories to run

        Returns:
            ValidationReport with all findings and scores
        """
        # Read file
        content = self._read_file(file_path)

        # Run checks
        results = {}
        for category, check_group in self.checks.items():
            if checks_filter and category not in checks_filter:
                continue

            results[category] = self._run_check_group(
                check_group, content, file_path
            )

        # Calculate scores
        category_scores = self._calculate_category_scores(results)
        overall_score = self._calculate_overall_score(category_scores)

        # Extract issues and recommendations
        issues = self._extract_issues(results)
        recommendations = self._generate_recommendations(issues, overall_score)

        # Determine status and grade
        status = self._determine_status(overall_score)
        grade = self._calculate_grade(overall_score)

        # Build report
        return ValidationReport(
            file_path=file_path,
            line_count=len([l for l in content.split('\n') if l.strip()]),
            timestamp=datetime.now().isoformat(),
            overall_score=overall_score,
            grade=grade,
            status=status,
            category_scores=category_scores,
            issues=issues,
            recommendations=recommendations,
            next_steps=self._generate_next_steps(overall_score, recommendations)
        )

    def _calculate_overall_score(self, category_scores: Dict[str, CategoryScore]) -> float:
        """Calculate weighted overall score."""
        return sum(
            cat.score * cat.weight
            for cat in category_scores.values()
        )

    def _calculate_grade(self, score: float) -> str:
        """Convert score to letter grade."""
        if score >= 9.5:
            return "A+"
        elif score >= 9.0:
            return "A"
        elif score >= 8.5:
            return "A-"
        elif score >= 8.0:
            return "B+"
        elif score >= 7.0:
            return "B"
        elif score >= 6.0:
            return "C"
        elif score >= 5.0:
            return "D"
        else:
            return "F"

    def _determine_status(self, score: float) -> str:
        """Determine production readiness status."""
        if score >= 9.0:
            return "excellent"
        elif score >= 8.0:
            return "good"
        elif score >= 7.0:
            return "acceptable"
        elif score >= 6.0:
            return "below_standard"
        elif score >= 5.0:
            return "poor"
        else:
            return "unacceptable"
```

### Dependencies

**Required**:
- `pyyaml` - YAML frontmatter parsing
- `pathlib` - File path handling (stdlib)
- `re` - Regular expressions (stdlib)
- `dataclasses` - Data models (stdlib)
- `typing` - Type hints (stdlib)

**Optional**:
- `colorama` - ANSI color support (for console output)
- `tabulate` - Table formatting (for batch mode)

### Performance

**Target**:
- Single agent validation: <2 seconds
- Batch validation (15 agents): <20 seconds
- Memory usage: <100MB for typical agent files

**Optimization**:
- Parse file once, pass to all checks
- Lazy evaluation of expensive checks
- Parallel execution for batch validation (if needed)

## Integration Points

### 1. `/agent-enhance` Command

Auto-invoke validation after enhancement:

```python
# In agent-enhance workflow
def enhance_agent(file_path: str) -> None:
    # ... enhancement logic ...

    # Auto-validate after enhancement
    from lib.agent_validator import AgentValidator

    validator = AgentValidator()
    report = validator.validate(file_path)

    print(f"\n📊 Post-Enhancement Validation: {report.overall_score:.1f}/10")

    if report.overall_score < 8.0:
        print(f"⚠️  Score below target (8.0). Re-run enhancement or manual fixes needed.")
```

### 2. Template Creation (`/template-create`)

Validate agents during Phase 7:

```python
# In template-create Phase 7 (agent validation)
def validate_template_agents(template_dir: Path) -> bool:
    """Validate all agents in template meet quality standards."""

    agent_files = template_dir.glob('agents/*.md')
    all_pass = True

    for agent_file in agent_files:
        result = validator.validate(str(agent_file))

        if result.overall_score < 7.0:
            print(f"❌ {agent_file.name}: {result.overall_score:.1f}/10 (below threshold)")
            all_pass = False
        else:
            print(f"✅ {agent_file.name}: {result.overall_score:.1f}/10")

    return all_pass
```

### 3. CI/CD Pipeline

GitHub Actions integration:

```yaml
# .github/workflows/agent-quality.yml
name: Agent Quality Check

on:
  pull_request:
    paths:
      - 'installer/global/agents/*.md'

jobs:
  validate-agents:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install pyyaml

      - name: Validate changed agents
        run: |
          for file in $(git diff --name-only origin/main | grep 'installer/global/agents/.*\.md'); do
            python installer/global/commands/lib/agent_validator/cli.py \
              "$file" \
              --threshold 8.0 \
              --format json \
              --exit-on-fail
          done
```

### 4. Batch Validation

Wrapper command for directory validation:

```python
# lib/agent_validator/batch.py
class BatchValidator:
    """Batch validation for multiple agents."""

    def validate_directory(
        self,
        directory: str,
        threshold: float = 0.0,
        recursive: bool = True
    ) -> List[ValidationReport]:
        """Validate all agent files in directory."""

        path = Path(directory)
        pattern = '**/*.md' if recursive else '*.md'

        agent_files = list(path.glob(pattern))
        reports = []

        validator = AgentValidator()

        for agent_file in agent_files:
            # Skip non-agent files
            if not self._is_agent_file(agent_file):
                continue

            try:
                report = validator.validate(str(agent_file))
                reports.append(report)
            except Exception as e:
                print(f"Error validating {agent_file}: {e}")

        return reports

    def _is_agent_file(self, file_path: Path) -> bool:
        """Check if file is an agent (has YAML frontmatter with 'name' field)."""
        try:
            with open(file_path) as f:
                content = f.read()

            if not content.startswith('---\n'):
                return False

            # Parse frontmatter
            end = content.find('\n---\n', 4)
            if end == -1:
                return False

            metadata = yaml.safe_load(content[4:end])
            return 'name' in metadata and 'description' in metadata
        except:
            return False
```

## Edge Cases

### 1. Malformed YAML Frontmatter

**Scenario**: Opening delimiter present but invalid YAML

**Handling**:
```python
def handle_malformed_yaml(content: str) -> CheckResult:
    """
    Return critical failure with helpful error message.
    """
    try:
        metadata = yaml.safe_load(frontmatter_content)
    except yaml.YAMLError as e:
        return CheckResult(
            status=CheckStatus.FAIL,
            score=0.0,
            message=f'Invalid YAML syntax: {e}',
            line=e.problem_mark.line if hasattr(e, 'problem_mark') else 1,
            severity=Severity.CRITICAL,
            recommendation='Fix YAML syntax error. Use YAML linter for details.'
        )
```

**Exit behavior**: Continue validation, report as critical issue

### 2. Missing Sections (No Code Examples)

**Scenario**: Agent file has no code blocks at all

**Handling**:
```python
if example_count == 0:
    return CheckResult(
        status=CheckStatus.FAIL,
        score=0.0,
        message='No code examples found in entire file',
        severity=Severity.CRITICAL,
        recommendation='Add at least 10 code examples demonstrating agent capabilities'
    )
```

**Impact**: Example density score = 0, overall score significantly reduced

### 3. Very Short Files (<50 lines)

**Scenario**: Agent file is too brief to be useful

**Handling**:
```python
if line_count < 50:
    return CheckResult(
        status=CheckStatus.FAIL,
        score=0.0,
        message=f'Agent too brief ({line_count} lines)',
        severity=Severity.CRITICAL,
        recommendation=(
            f'Expand agent to at least 150 lines. Add:\n'
            f'  - Detailed role description\n'
            f'  - 10+ code examples\n'
            f'  - Boundary sections (ALWAYS/NEVER/ASK)\n'
            f'  - Reference material'
        )
    )
```

**Status**: Unacceptable (score will be <5.0)

### 4. Very Long Files (>800 lines)

**Scenario**: Agent file should be split

**Handling**:
```python
if line_count > 800:
    # Suggest split based on content analysis
    agent_name = Path(filename).stem
    return CheckResult(
        status=CheckStatus.FAIL,
        score=0.0,
        message=f'Agent too long ({line_count} lines)',
        severity=Severity.CRITICAL,
        recommendation=(
            f'Split into multiple agents:\n'
            f'  - {agent_name} (core capabilities)\n'
            f'  - {agent_name}-advanced (specialized features)\n'
            f'Target: 150-300 lines per agent'
        )
    )
```

### 5. Language-Agnostic Agents

**Scenario**: Agent doesn't mention specific technologies (e.g., `task-manager`)

**Handling**:
```python
def check_technology_specificity(content: str) -> CheckResult:
    # ... existing logic ...

    if not tech_mentions:
        # Language-agnostic agent (acceptable)
        return CheckResult(
            status=CheckStatus.PASS,
            score=10.0,
            message='Language-agnostic agent (no specific technologies)',
            severity=Severity.INFO,
            recommendation=None
        )
```

**Behavior**: Full score for technology specificity check (not penalized)

### 6. No Boundaries Sections

**Scenario**: Missing ALWAYS/NEVER/ASK sections

**Handling**:
```python
if not has_always_section:
    return CheckResult(
        status=CheckStatus.FAIL,
        score=0.0,
        message='ALWAYS section missing',
        severity=Severity.CRITICAL,
        recommendation=(
            'Add ALWAYS section with 5-7 non-negotiable rules. Example:\n\n'
            '## What You ALWAYS Do\n\n'
            '1. Verify build succeeds before code review\n'
            '2. Enforce ≥80% line coverage threshold\n'
            '...'
        )
    )
```

**Impact**: Boundary clarity score = 0, overall score significantly reduced

### 7. Single-Language Code Blocks

**Scenario**: All code blocks in one language (Python)

**Handling**: Not penalized, but noted in report

```python
# Track languages in code blocks
languages = set()
for block in code_blocks:
    lang = extract_language_tag(block)
    if lang:
        languages.add(lang)

# Include in report metadata (not scored)
return {
    'languages_used': list(languages),
    'is_multilingual': len(languages) > 1
}
```

## Testing Strategy

### Test Fixtures

Create known-good and known-bad agent files:

```
tests/fixtures/agents/
├── excellent/
│   ├── code-reviewer-excellent.md        # Score: 9.5
│   ├── test-verifier-excellent.md        # Score: 9.2
│   └── task-manager-excellent.md         # Score: 9.0
├── good/
│   ├── code-reviewer-good.md             # Score: 8.5
│   └── architectural-reviewer-good.md    # Score: 8.0
├── acceptable/
│   ├── code-reviewer-acceptable.md       # Score: 7.5
│   └── build-validator-acceptable.md     # Score: 7.0
├── below_standard/
│   ├── code-reviewer-below.md            # Score: 6.5
│   └── missing-examples.md               # Score: 6.0
└── poor/
    ├── no-frontmatter.md                 # Score: 2.0
    ├── no-examples.md                    # Score: 3.0
    ├── generic-language.md               # Score: 4.5
    └── incomplete-placeholder.md         # Score: 5.0
```

### Unit Tests

```python
# tests/test_structure_checks.py
import pytest
from lib.agent_validator.checks.structure import (
    check_yaml_frontmatter,
    check_early_actionability,
    check_file_length,
    check_section_order
)

def test_yaml_frontmatter_valid():
    """Test valid YAML frontmatter passes."""
    content = """---
name: test-agent
description: Test agent for validation
---

Agent content here.
"""
    result = check_yaml_frontmatter(content)
    assert result.status == CheckStatus.PASS
    assert result.score == 10.0

def test_yaml_frontmatter_missing():
    """Test missing frontmatter fails."""
    content = "No frontmatter here"
    result = check_yaml_frontmatter(content)
    assert result.status == CheckStatus.FAIL
    assert result.score == 0.0
    assert result.severity == Severity.CRITICAL

def test_yaml_frontmatter_invalid_syntax():
    """Test invalid YAML syntax."""
    content = """---
name: test-agent
description: [invalid yaml
---
"""
    result = check_yaml_frontmatter(content)
    assert result.status == CheckStatus.FAIL
    assert result.score == 0.0
    assert 'Invalid YAML syntax' in result.message

def test_early_actionability_excellent():
    """Test first example within 30 lines."""
    content = """---
name: test
---

## Role

You are a test agent.

## Quick Start

```python
print("Hello")
```
"""
    result = check_early_actionability(content)
    assert result.score == 10.0
    assert result.line < 30

def test_file_length_optimal():
    """Test optimal file length (150-300 lines)."""
    lines = ["Line " + str(i) for i in range(200)]
    content = "\n".join(lines)
    result = check_file_length(content)
    assert result.score == 10.0

def test_file_length_too_short():
    """Test file too short (<50 lines)."""
    content = "\n".join(["Line"] * 40)
    result = check_file_length(content)
    assert result.score == 0.0
    assert 'too brief' in result.message.lower()
```

### Integration Tests

```python
# tests/test_validator_integration.py
def test_validate_excellent_agent():
    """Test validation of known-excellent agent."""
    validator = AgentValidator()
    report = validator.validate('tests/fixtures/agents/excellent/code-reviewer-excellent.md')

    assert report.overall_score >= 9.0
    assert report.grade in ['A+', 'A']
    assert report.status == 'excellent'
    assert len([i for i in report.issues if i['severity'] == 'critical']) == 0

def test_validate_poor_agent():
    """Test validation of known-poor agent."""
    validator = AgentValidator()
    report = validator.validate('tests/fixtures/agents/poor/no-examples.md')

    assert report.overall_score < 5.0
    assert report.grade in ['D', 'F']
    assert report.status == 'poor'
    assert len(report.issues) > 0

def test_validate_with_checks_filter():
    """Test validation with specific checks only."""
    validator = AgentValidator()
    report = validator.validate(
        'tests/fixtures/agents/good/code-reviewer-good.md',
        checks_filter=['structure', 'examples']
    )

    assert 'structure' in report.category_scores
    assert 'examples' in report.category_scores
    assert 'boundaries' not in report.category_scores
```

### Regression Tests

```python
# tests/test_scoring_regression.py
EXPECTED_SCORES = {
    'excellent/code-reviewer-excellent.md': 9.5,
    'good/code-reviewer-good.md': 8.5,
    'acceptable/code-reviewer-acceptable.md': 7.5,
    'below_standard/code-reviewer-below.md': 6.5,
    'poor/no-examples.md': 3.0,
}

@pytest.mark.parametrize('fixture,expected_score', EXPECTED_SCORES.items())
def test_score_consistency(fixture, expected_score):
    """Ensure scoring remains consistent across versions."""
    validator = AgentValidator()
    report = validator.validate(f'tests/fixtures/agents/{fixture}')

    # Allow ±0.2 variance
    assert abs(report.overall_score - expected_score) < 0.2, \
        f"Score drift detected: {report.overall_score} vs {expected_score}"
```

### Performance Tests

```python
# tests/test_performance.py
import time

def test_single_validation_performance():
    """Validate single agent in <2 seconds."""
    validator = AgentValidator()

    start = time.time()
    validator.validate('tests/fixtures/agents/excellent/code-reviewer-excellent.md')
    duration = time.time() - start

    assert duration < 2.0, f"Validation took {duration:.2f}s (target: <2s)"

def test_batch_validation_performance():
    """Validate 15 agents in <20 seconds."""
    batch_validator = BatchValidator()

    start = time.time()
    reports = batch_validator.validate_directory('tests/fixtures/agents/')
    duration = time.time() - start

    assert len(reports) >= 15
    assert duration < 20.0, f"Batch validation took {duration:.2f}s (target: <20s)"
```

## CLI Interface

### Main Entry Point

```python
# installer/global/commands/lib/agent_validator/cli.py
import sys
import argparse
from pathlib import Path
from .validator import AgentValidator
from .batch import BatchValidator
from .formatters import ConsoleFormatter, JsonFormatter

def main():
    """CLI entry point for agent validation."""
    parser = argparse.ArgumentParser(
        description='Validate agent markdown files against quality standards'
    )
    parser.add_argument('file_path', help='Path to agent markdown file')
    parser.add_argument(
        '--format',
        choices=['console', 'json', 'minimal'],
        default='console',
        help='Output format'
    )
    parser.add_argument(
        '--threshold',
        type=float,
        default=0.0,
        help='Minimum acceptable score (0.0-10.0)'
    )
    parser.add_argument(
        '--exit-on-fail',
        action='store_true',
        help='Exit with code 1 if score below threshold'
    )
    parser.add_argument(
        '--suggest-fixes',
        action='store_true',
        help='Include auto-fix suggestions in output'
    )
    parser.add_argument(
        '--checks',
        help='Comma-separated list of checks to run'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose output'
    )
    parser.add_argument(
        '--output-file',
        help='Write report to file instead of stdout'
    )

    args = parser.parse_args()

    # Validate file exists
    if not Path(args.file_path).exists():
        print(f"Error: File not found: {args.file_path}", file=sys.stderr)
        sys.exit(3)

    # Parse checks filter
    checks_filter = None
    if args.checks:
        checks_filter = [c.strip() for c in args.checks.split(',')]

    # Run validation
    validator = AgentValidator(verbose=args.verbose)

    try:
        report = validator.validate(args.file_path, checks_filter)
    except yaml.YAMLError as e:
        print(f"Error: Cannot parse YAML frontmatter: {e}", file=sys.stderr)
        sys.exit(4)
    except Exception as e:
        print(f"Error: Validation failed: {e}", file=sys.stderr)
        sys.exit(4)

    # Format output
    if args.format == 'console':
        formatter = ConsoleFormatter()
        output = formatter.format(report, include_fixes=args.suggest_fixes)
    elif args.format == 'json':
        formatter = JsonFormatter()
        output = formatter.format(report)
    else:  # minimal
        formatter = JsonFormatter()
        output = formatter.format_minimal(report)

    # Write output
    if args.output_file:
        with open(args.output_file, 'w') as f:
            f.write(output)
    else:
        print(output)

    # Exit code based on threshold
    if args.exit_on_fail and report.overall_score < args.threshold:
        sys.exit(1)

    sys.exit(0)

if __name__ == '__main__':
    main()
```

### Batch CLI

```python
# installer/global/commands/lib/agent_validator/batch_cli.py
def main():
    """CLI entry point for batch agent validation."""
    parser = argparse.ArgumentParser(
        description='Batch validate agent markdown files'
    )
    parser.add_argument('directory', help='Directory containing agent files')
    parser.add_argument(
        '--format',
        choices=['table', 'json', 'csv'],
        default='table',
        help='Output format'
    )
    parser.add_argument(
        '--threshold',
        type=float,
        default=0.0,
        help='Filter agents below threshold'
    )
    parser.add_argument(
        '--exit-on-fail',
        action='store_true',
        help='Exit with code 1 if any agent below threshold'
    )
    parser.add_argument(
        '--summary',
        action='store_true',
        help='Summary table only (no detailed reports)'
    )
    parser.add_argument(
        '--recursive',
        action='store_true',
        default=True,
        help='Recursively search subdirectories'
    )
    parser.add_argument(
        '--output-file',
        help='Write report to file'
    )

    args = parser.parse_args()

    # Run batch validation
    batch_validator = BatchValidator()
    reports = batch_validator.validate_directory(
        args.directory,
        threshold=args.threshold,
        recursive=args.recursive
    )

    # Format output
    if args.format == 'table':
        from .formatters.table import TableFormatter
        formatter = TableFormatter()
        output = formatter.format(reports, summary_only=args.summary)
    elif args.format == 'json':
        formatter = JsonFormatter()
        output = formatter.format_batch(reports)
    else:  # csv
        from .formatters.csv import CsvFormatter
        formatter = CsvFormatter()
        output = formatter.format(reports)

    # Write output
    if args.output_file:
        with open(args.output_file, 'w') as f:
            f.write(output)
    else:
        print(output)

    # Exit code
    if args.exit_on_fail:
        failing_reports = [r for r in reports if r.overall_score < args.threshold]
        if failing_reports:
            sys.exit(1)

    sys.exit(0)
```

## Summary

This specification provides a complete, implementation-ready design for `/agent-validate` that:

1. **Objective**: All checks are measurable with clear scoring algorithms
2. **Actionable**: Every issue includes specific recommendations with impact estimates
3. **Comprehensive**: Covers all 6 GitHub best practice areas plus GuardKit standards
4. **Extensible**: Modular architecture makes adding new checks straightforward
5. **CI/CD Ready**: JSON output, exit codes, and threshold support for automation
6. **Developer-Friendly**: Clear console output with Unicode formatting and color coding

**Key Metrics**:
- 6 validation categories with 15+ individual checks
- 0-10 scoring scale for all checks
- Weighted aggregation for category and overall scores
- Letter grades (A+ to F) for quick assessment
- Priority-ranked recommendations (P1-P4)
- Impact estimation for all improvements
- Time estimates for fixes

**Integration Points**:
- `/agent-enhance` command (auto-validate after enhancement)
- `/template-create` command (validate agents in Phase 7)
- CI/CD pipelines (GitHub Actions, GitLab CI)
- Batch validation (directory-wide quality checks)

The tool is designed to be the ESLint/pytest-cov equivalent for agent files, providing objective quality assurance with minimal manual interpretation required.
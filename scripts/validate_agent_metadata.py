#!/usr/bin/env python3
"""
Validation script for agent discovery metadata.
Ensures all global agents have complete and valid discovery metadata.
"""

import glob
import sys
from pathlib import Path


def parse_frontmatter(content: str) -> dict:
    """Parse YAML frontmatter from markdown file."""
    if not content.startswith('---'):
        return {}

    parts = content.split('---', 2)
    if len(parts) < 3:
        return {}

    frontmatter_lines = parts[1].strip().split('\n')
    metadata = {}
    current_key = None
    current_list = []

    for line in frontmatter_lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        if ':' in line and not line.startswith('-'):
            if current_key and current_list:
                metadata[current_key] = current_list
                current_list = []

            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()

            if value.startswith('[') and value.endswith(']'):
                # Inline list
                items = value[1:-1].split(',')
                metadata[key] = [item.strip() for item in items if item.strip()]
            elif value:
                metadata[key] = value
            else:
                current_key = key
        elif line.startswith('-') and current_key:
            # List item
            item = line[1:].strip()
            current_list.append(item)

    if current_key and current_list:
        metadata[current_key] = current_list

    return metadata


def validate_agent(agent_path: str) -> tuple[bool, list[str]]:
    """Validate a single agent file. Returns (is_valid, issues)."""
    issues = []

    try:
        with open(agent_path) as f:
            content = f.read()
    except Exception as e:
        return False, [f"Failed to read file: {e}"]

    metadata = parse_frontmatter(content)

    if not metadata:
        return False, ["No frontmatter found"]

    # Check required fields
    required_fields = ['stack', 'phase', 'capabilities', 'keywords', 'model', 'model_rationale']
    for field in required_fields:
        if field not in metadata:
            issues.append(f"Missing required field: {field}")

    if issues:
        return False, issues

    # Validate stack values
    valid_stacks = ['cross-stack', 'python', 'react', 'dotnet', 'typescript', 'maui', 'xaml']
    stack_value = metadata.get('stack', [])
    if isinstance(stack_value, str):
        stack_value = [stack_value]

    for stack in stack_value:
        if stack not in valid_stacks:
            issues.append(f"Invalid stack value: {stack}")

    # Validate phase values
    valid_phases = ['implementation', 'review', 'testing', 'orchestration']
    phase = metadata.get('phase', '')
    if phase not in valid_phases:
        issues.append(f"Invalid phase value: {phase} (must be one of {valid_phases})")

    # Validate model values
    valid_models = ['sonnet', 'haiku']
    model = metadata.get('model', '')
    if model not in valid_models:
        issues.append(f"Invalid model value: {model} (must be one of {valid_models})")

    # Validate capabilities count (minimum 5)
    capabilities = metadata.get('capabilities', [])
    if isinstance(capabilities, str):
        capabilities = [capabilities]

    if len(capabilities) < 5:
        issues.append(f"Insufficient capabilities: {len(capabilities)} (minimum 5 required)")

    # Validate keywords count (minimum 5)
    keywords = metadata.get('keywords', [])
    if isinstance(keywords, str):
        keywords = [keywords]

    if len(keywords) < 5:
        issues.append(f"Insufficient keywords: {len(keywords)} (minimum 5 required)")

    # Validate model_rationale is not empty
    model_rationale = metadata.get('model_rationale', '')
    if not model_rationale or len(model_rationale.strip()) < 10:
        issues.append("model_rationale is empty or too short (minimum 10 characters)")

    return len(issues) == 0, issues


def validate_all_agents():
    """Validate all global agents have complete metadata."""
    # Get the project root (3 levels up from scripts/)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    agents_dir = project_root / "installer" / "global" / "agents"

    agents = glob.glob(str(agents_dir / "*.md"))

    results = {'valid': [], 'invalid': []}

    print("Validating agent metadata...\n")

    for agent_path in sorted(agents):
        agent_name = Path(agent_path).stem
        is_valid, issues = validate_agent(agent_path)

        if is_valid:
            results['valid'].append(agent_name)
            print(f"✅ {agent_name}")
        else:
            results['invalid'].append((agent_name, issues))
            print(f"❌ {agent_name}")
            for issue in issues:
                print(f"   - {issue}")

    # Report summary
    print("\n" + "="*60)
    print(f"Valid: {len(results['valid'])}/{len(agents)}")
    print(f"Invalid: {len(results['invalid'])}/{len(agents)}")

    if results['invalid']:
        print("\nInvalid agents:")
        for agent_name, issues in results['invalid']:
            print(f"  - {agent_name}: {len(issues)} issue(s)")

    # Expected: 15 agents total (12 updated + 3 already with metadata)
    expected_valid = 15
    actual_valid = len(results['valid'])

    if actual_valid == expected_valid:
        print(f"\n🎉 SUCCESS: All {expected_valid} agents have valid metadata!")
        return True
    else:
        print(f"\n⚠️  INCOMPLETE: {actual_valid}/{expected_valid} agents have valid metadata")
        return False


if __name__ == '__main__':
    success = validate_all_agents()
    sys.exit(0 if success else 1)

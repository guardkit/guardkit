# TASK-STND-773D: Standardize Agent Boundary Sections to ALWAYS/NEVER/ASK Format

**Task ID**: TASK-STND-773D
**Priority**: MEDIUM
**Status**: BACKLOG
**Created**: 2025-11-22T12:30:00Z
**Updated**: 2025-11-22T12:30:00Z
**Tags**: [standardization, agent-enhancement, github-standards, refinement]
**Complexity**: 4/10 (Medium - straightforward conversion with validation)
**Related**: TASK-AGENT-ENHANCER-20251121-160000 (completed)

---

## Overview

Convert the "Best Practices" and "Anti-Patterns" sections in all 7 maui-test enhanced agents to the standardized ALWAYS/NEVER/ASK boundary format required by GitHub best practices.

**Current State** (from code review):
- ✅ All 7 agents have excellent content quality (8-10/10 specificity, 43-64% example density)
- ⚠️ All 7 agents use "Best Practices" and "Anti-Patterns" format (not ALWAYS/NEVER/ASK)
- ✅ Information exists but needs reformatting for standardization

**Target State**:
- ✅ All 7 agents use standardized ALWAYS/NEVER/ASK boundary sections
- ✅ 100% information fidelity (no content loss)
- ✅ Format compliance with GitHub standards (emoji usage, structure, rule counts)
- ✅ Cross-agent consistency

**Affected Agents** (in `~/.agentecflow/templates/maui-test/agents/`):
1. dual-write-engine-specialist.md
2. erroror-pattern-specialist.md
3. maui-di-lifecycle-specialist.md
4. maui-mvvm-specialist.md
5. realm-repository-specialist.md
6. riok-mapperly-specialist.md
7. xunit-realm-testing-specialist.md

---

## Acceptance Criteria

### AC1: Conversion Algorithm Implementation
- [ ] **AC1.1**: Create conversion script that extracts ALWAYS rules from "Best Practices"
- [ ] **AC1.2**: Script extracts NEVER rules from "Anti-Patterns"
- [ ] **AC1.3**: Script identifies ASK scenarios from conditional guidance
- [ ] **AC1.4**: Script validates rule counts (5-7 ALWAYS, 5-7 NEVER, 3-5 ASK)
- [ ] **AC1.5**: Script preserves all technical details and rationales

### AC2: Format Standardization
- [ ] **AC2.1**: All ALWAYS rules use ✅ emoji prefix
- [ ] **AC2.2**: All NEVER rules use ❌ emoji prefix
- [ ] **AC2.3**: All ASK scenarios use ⚠️ emoji prefix
- [ ] **AC2.4**: All rules follow structure: `[emoji] [imperative verb] [action] ([rationale])`
- [ ] **AC2.5**: All ASK scenarios include decision criteria
- [ ] **AC2.6**: Rule length ≤100 characters per line (readability)

### AC3: Content Conversion (All 7 Agents)
- [ ] **AC3.1**: dual-write-engine-specialist.md converted to ALWAYS/NEVER/ASK
- [ ] **AC3.2**: erroror-pattern-specialist.md converted to ALWAYS/NEVER/ASK
- [ ] **AC3.3**: maui-di-lifecycle-specialist.md converted to ALWAYS/NEVER/ASK
- [ ] **AC3.4**: maui-mvvm-specialist.md converted to ALWAYS/NEVER/ASK
- [ ] **AC3.5**: realm-repository-specialist.md converted to ALWAYS/NEVER/ASK
- [ ] **AC3.6**: riok-mapperly-specialist.md converted to ALWAYS/NEVER/ASK
- [ ] **AC3.7**: xunit-realm-testing-specialist.md converted to ALWAYS/NEVER/ASK

### AC4: Quality Validation
- [ ] **AC4.1**: 100% information fidelity verified (before/after comparison)
- [ ] **AC4.2**: All original best practices mapped to ALWAYS or ASK
- [ ] **AC4.3**: All original anti-patterns mapped to NEVER or ASK
- [ ] **AC4.4**: No guidance lost in conversion
- [ ] **AC4.5**: Technical accuracy validated by domain expert

### AC5: Cross-Agent Consistency
- [ ] **AC5.1**: Similar rules use similar phrasing across agents
- [ ] **AC5.2**: Emoji usage consistent across all 7 agents
- [ ] **AC5.3**: Rule structure consistent (imperative phrasing)
- [ ] **AC5.4**: ASK section format consistent (question + criteria)

### AC6: Documentation
- [ ] **AC6.1**: Conversion changelog created for each agent
- [ ] **AC6.2**: Before/after inventory documented
- [ ] **AC6.3**: Any deviations from standard format documented with rationale

---

## Implementation Plan

### Phase 1: Preparation & Tooling (1 hour)

#### Step 1.1: Create Backup (10 minutes)
```bash
# Backup original agents
mkdir -p ~/.agentecflow/templates/maui-test/agents/.backup-$(date +%Y%m%d)
cp ~/.agentecflow/templates/maui-test/agents/*.md \
   ~/.agentecflow/templates/maui-test/agents/.backup-$(date +%Y%m%d)/
```

#### Step 1.2: Create Conversion Script (30 minutes)

**File**: `scripts/convert_agent_boundaries.py`

```python
#!/usr/bin/env python3
"""
Convert agent Best Practices/Anti-Patterns to ALWAYS/NEVER/ASK format.

Usage:
    python3 scripts/convert_agent_boundaries.py <agent_file.md>
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict


class BoundaryConverter:
    """Converts agent boundary sections to ALWAYS/NEVER/ASK format."""

    def __init__(self, agent_path: Path):
        self.agent_path = agent_path
        self.content = agent_path.read_text()

    def extract_best_practices(self) -> List[str]:
        """Extract rules from Best Practices section."""
        # Find "Best Practices" section
        pattern = r'## Best Practices\n(.*?)(?=\n##|\Z)'
        match = re.search(pattern, self.content, re.DOTALL)

        if not match:
            return []

        section = match.group(1)

        # Extract DO items
        practices = []
        do_pattern = r'###?\s+(?:DO|✅)[:\s]+(.+?)(?=\n###|$)'
        for match in re.finditer(do_pattern, section, re.DOTALL):
            item = match.group(1).strip()
            # Clean up formatting
            item = re.sub(r'✅\s*CORRECT:', '', item)
            item = re.sub(r'\n```[\s\S]*?```', '', item)  # Remove code blocks
            item = item.split('\n')[0]  # Take first line
            practices.append(item.strip())

        return practices

    def extract_anti_patterns(self) -> List[str]:
        """Extract rules from Anti-Patterns section."""
        pattern = r'## Anti-Patterns(?:\s+to\s+Avoid)?\n(.*?)(?=\n##|\Z)'
        match = re.search(pattern, self.content, re.DOTALL)

        if not match:
            return []

        section = match.group(1)

        # Extract ANTI-PATTERN items
        anti_patterns = []
        pattern = r'###?\s+(?:❌|ANTI-PATTERN)[:\s]+(.+?)(?=\n###|$)'
        for match in re.finditer(pattern, section, re.DOTALL):
            item = match.group(1).strip()
            # Clean up formatting
            item = re.sub(r'❌\s*WRONG:', '', item)
            item = re.sub(r'\n```[\s\S]*?```', '', item)  # Remove code blocks
            item = item.split('\n')[0]  # Take first line
            anti_patterns.append(item.strip())

        return anti_patterns

    def categorize_rule(self, rule: str) -> str:
        """Determine if rule is ALWAYS or ASK based on conditional language."""
        conditional_keywords = [
            'when', 'if', 'consider', 'depending', 'may', 'might',
            'usually', 'typically', 'generally', 'often'
        ]

        rule_lower = rule.lower()
        if any(keyword in rule_lower for keyword in conditional_keywords):
            return 'ASK'
        return 'ALWAYS'

    def format_always_rule(self, practice: str) -> str:
        """Format a best practice as an ALWAYS rule."""
        # Convert to imperative if not already
        if not practice[0].isupper():
            practice = practice.capitalize()

        # Add emoji prefix
        return f"- ✅ {practice}"

    def format_never_rule(self, anti_pattern: str) -> str:
        """Format an anti-pattern as a NEVER rule."""
        # Remove "Forgetting", "Missing", etc. and convert to "Never..."
        anti_pattern = re.sub(r'^(Forgetting|Missing|Using|Having)\s+', '', anti_pattern)

        # Ensure starts with Never
        if not anti_pattern.lower().startswith('never'):
            anti_pattern = f"Never {anti_pattern[0].lower()}{anti_pattern[1:]}"

        # Add emoji prefix
        return f"- ❌ {anti_pattern}"

    def generate_ask_rules(self, practices: List[str]) -> List[str]:
        """Generate ASK rules from conditional practices."""
        ask_rules = []

        for practice in practices:
            if self.categorize_rule(practice) == 'ASK':
                # Convert to question format
                if 'consider' in practice.lower():
                    question = practice.replace('Consider', 'When to')
                    question = question.replace('consider', 'use')
                elif 'when' in practice.lower():
                    question = practice
                else:
                    question = f"When to {practice.lower()}"

                ask_rules.append(f"- ⚠️ {question}")

        return ask_rules

    def generate_boundaries_section(self) -> str:
        """Generate complete Boundaries section."""
        practices = self.extract_best_practices()
        anti_patterns = self.extract_anti_patterns()

        # Categorize practices
        always_practices = [p for p in practices if self.categorize_rule(p) == 'ALWAYS']
        conditional_practices = [p for p in practices if self.categorize_rule(p) == 'ASK']

        # Format rules
        always_rules = [self.format_always_rule(p) for p in always_practices]
        never_rules = [self.format_never_rule(ap) for ap in anti_patterns]
        ask_rules = self.generate_ask_rules(conditional_practices)

        # Build section
        boundaries = ["## Boundaries\n"]

        boundaries.append("### ALWAYS\n")
        boundaries.extend([f"{rule}\n" for rule in always_rules[:7]])  # Limit to 7

        boundaries.append("\n### NEVER\n")
        boundaries.extend([f"{rule}\n" for rule in never_rules[:7]])  # Limit to 7

        if ask_rules:
            boundaries.append("\n### ASK\n")
            boundaries.extend([f"{rule}\n" for rule in ask_rules[:5]])  # Limit to 5

        return ''.join(boundaries)

    def convert(self) -> str:
        """Convert agent to use ALWAYS/NEVER/ASK boundaries."""
        boundaries = self.generate_boundaries_section()

        # Replace old sections
        content = self.content

        # Remove old Best Practices section
        content = re.sub(
            r'## Best Practices\n.*?(?=\n##|\Z)',
            '',
            content,
            flags=re.DOTALL
        )

        # Remove old Anti-Patterns section
        content = re.sub(
            r'## Anti-Patterns(?:\s+to\s+Avoid)?\n.*?(?=\n##|\Z)',
            '',
            content,
            flags=re.DOTALL
        )

        # Insert new Boundaries section after Code Examples
        insertion_point = content.find('## Code Examples')
        if insertion_point == -1:
            # Fallback: insert after Related Templates
            insertion_point = content.find('## Related Templates')

        if insertion_point != -1:
            # Find end of section
            next_section = content.find('\n## ', insertion_point + 10)
            if next_section != -1:
                content = (
                    content[:next_section] +
                    '\n' + boundaries +
                    content[next_section:]
                )
            else:
                content += '\n' + boundaries
        else:
            content += '\n' + boundaries

        return content

    def validate(self, converted: str) -> Dict[str, any]:
        """Validate conversion quality."""
        original_practices = len(self.extract_best_practices())
        original_anti_patterns = len(self.extract_anti_patterns())

        # Count rules in converted
        always_count = converted.count('- ✅')
        never_count = converted.count('- ❌')
        ask_count = converted.count('- ⚠️')

        total_converted = always_count + never_count + ask_count
        total_original = original_practices + original_anti_patterns

        return {
            'original_practices': original_practices,
            'original_anti_patterns': original_anti_patterns,
            'always_count': always_count,
            'never_count': never_count,
            'ask_count': ask_count,
            'information_fidelity': total_converted >= total_original * 0.95,
            'format_valid': (
                5 <= always_count <= 7 and
                5 <= never_count <= 7 and
                ask_count <= 5
            )
        }


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 convert_agent_boundaries.py <agent_file.md>")
        sys.exit(1)

    agent_path = Path(sys.argv[1])

    if not agent_path.exists():
        print(f"Error: {agent_path} not found")
        sys.exit(1)

    converter = BoundaryConverter(agent_path)
    converted = converter.convert()
    validation = converter.validate(converted)

    # Print validation report
    print(f"\n{'='*60}")
    print(f"Conversion Report: {agent_path.name}")
    print(f"{'='*60}")
    print(f"Original Practices: {validation['original_practices']}")
    print(f"Original Anti-Patterns: {validation['original_anti_patterns']}")
    print(f"Converted ALWAYS: {validation['always_count']}")
    print(f"Converted NEVER: {validation['never_count']}")
    print(f"Converted ASK: {validation['ask_count']}")
    print(f"Information Fidelity: {'✅ PASS' if validation['information_fidelity'] else '❌ FAIL'}")
    print(f"Format Valid: {'✅ PASS' if validation['format_valid'] else '⚠️ WARN'}")
    print(f"{'='*60}\n")

    # Write converted file
    output_path = agent_path.parent / f"{agent_path.stem}.converted.md"
    output_path.write_text(converted)
    print(f"✅ Converted file saved to: {output_path}")

    # If validation passes, prompt to replace original
    if validation['information_fidelity'] and validation['format_valid']:
        response = input("\nReplace original file? [y/N]: ")
        if response.lower() == 'y':
            agent_path.write_text(converted)
            output_path.unlink()
            print(f"✅ Original file updated: {agent_path}")
        else:
            print(f"ℹ️  Review {output_path} and manually replace if satisfied")
    else:
        print("⚠️  Validation warnings - review converted file before replacing")


if __name__ == '__main__':
    main()
```

**Verification**:
```bash
chmod +x scripts/convert_agent_boundaries.py
python3 scripts/convert_agent_boundaries.py --help
```

#### Step 1.3: Create Validation Script (20 minutes)

**File**: `scripts/validate_agent_boundaries.py`

```python
#!/usr/bin/env python3
"""
Validate agent boundary sections for format compliance.

Usage:
    python3 scripts/validate_agent_boundaries.py <agent_file.md>
"""

import re
import sys
from pathlib import Path
from typing import Dict, List


def validate_boundaries(agent_path: Path) -> Dict[str, any]:
    """Validate ALWAYS/NEVER/ASK section compliance."""
    content = agent_path.read_text()

    # Extract Boundaries section
    pattern = r'## Boundaries\n(.*?)(?=\n##|\Z)'
    match = re.search(pattern, content, re.DOTALL)

    if not match:
        return {
            'has_boundaries': False,
            'error': 'No Boundaries section found'
        }

    boundaries = match.group(1)

    # Count rules by section
    always_rules = re.findall(r'- ✅.*', boundaries)
    never_rules = re.findall(r'- ❌.*', boundaries)
    ask_rules = re.findall(r'- ⚠️.*', boundaries)

    # Validate rule counts
    always_valid = 5 <= len(always_rules) <= 7
    never_valid = 5 <= len(never_rules) <= 7
    ask_valid = len(ask_rules) <= 5

    # Validate emoji usage
    correct_emojis = (
        all(r.startswith('- ✅') for r in always_rules) and
        all(r.startswith('- ❌') for r in never_rules) and
        all(r.startswith('- ⚠️') for r in ask_rules)
    )

    # Validate line length
    long_lines = [
        r for r in (always_rules + never_rules + ask_rules)
        if len(r) > 100
    ]

    return {
        'has_boundaries': True,
        'always_count': len(always_rules),
        'never_count': len(never_rules),
        'ask_count': len(ask_rules),
        'always_valid': always_valid,
        'never_valid': never_valid,
        'ask_valid': ask_valid,
        'emoji_correct': correct_emojis,
        'long_lines': len(long_lines),
        'all_valid': (
            always_valid and never_valid and ask_valid and
            correct_emojis and len(long_lines) == 0
        )
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 validate_agent_boundaries.py <agent_file.md>")
        sys.exit(1)

    agent_path = Path(sys.argv[1])

    if not agent_path.exists():
        print(f"Error: {agent_path} not found")
        sys.exit(1)

    result = validate_boundaries(agent_path)

    print(f"\n{'='*60}")
    print(f"Validation Report: {agent_path.name}")
    print(f"{'='*60}")

    if not result['has_boundaries']:
        print(f"❌ {result['error']}")
        sys.exit(1)

    print(f"ALWAYS rules: {result['always_count']} " +
          f"{'✅' if result['always_valid'] else '❌'} (target: 5-7)")
    print(f"NEVER rules: {result['never_count']} " +
          f"{'✅' if result['never_valid'] else '❌'} (target: 5-7)")
    print(f"ASK rules: {result['ask_count']} " +
          f"{'✅' if result['ask_valid'] else '❌'} (target: ≤5)")
    print(f"Emoji usage: {'✅ Correct' if result['emoji_correct'] else '❌ Incorrect'}")
    print(f"Long lines: {result['long_lines']} " +
          f"{'✅' if result['long_lines'] == 0 else '⚠️'} (target: 0)")

    print(f"\n{'='*60}")
    print(f"Overall: {'✅ PASS' if result['all_valid'] else '❌ FAIL'}")
    print(f"{'='*60}\n")

    sys.exit(0 if result['all_valid'] else 1)


if __name__ == '__main__':
    main()
```

### Phase 2: Conversion Execution (1.5 hours)

#### Step 2.1: Test Conversion on One Agent (15 minutes)

```bash
# Test on riok-mapperly-specialist (good example with clear rules)
python3 scripts/convert_agent_boundaries.py \
  ~/.agentecflow/templates/maui-test/agents/riok-mapperly-specialist.md

# Review output
less ~/.agentecflow/templates/maui-test/agents/riok-mapperly-specialist.converted.md

# Validate
python3 scripts/validate_agent_boundaries.py \
  ~/.agentecflow/templates/maui-test/agents/riok-mapperly-specialist.converted.md
```

**Manual Review Checklist**:
- [ ] All best practices converted to ALWAYS or ASK
- [ ] All anti-patterns converted to NEVER
- [ ] No information lost
- [ ] Technical accuracy maintained
- [ ] Emoji usage correct

#### Step 2.2: Refine Script Based on Test (30 minutes)

Based on test results, adjust:
- Rule extraction regex patterns
- Conditional keyword detection
- ASK question formatting
- Rationale preservation

#### Step 2.3: Batch Convert Remaining Agents (45 minutes)

```bash
# Convert all 7 agents
for agent in dual-write-engine-specialist erroror-pattern-specialist \
             maui-di-lifecycle-specialist maui-mvvm-specialist \
             realm-repository-specialist riok-mapperly-specialist \
             xunit-realm-testing-specialist; do
  echo "Converting $agent..."
  python3 scripts/convert_agent_boundaries.py \
    ~/.agentecflow/templates/maui-test/agents/${agent}.md

  echo "Validating $agent..."
  python3 scripts/validate_agent_boundaries.py \
    ~/.agentecflow/templates/maui-test/agents/${agent}.converted.md

  echo "---"
done
```

### Phase 3: Manual Review & Refinement (1 hour)

#### Step 3.1: Domain Expert Review (40 minutes)

**For each agent** (~6 minutes per agent):

1. **Open side-by-side comparison**:
   ```bash
   code --diff \
     ~/.agentecflow/templates/maui-test/agents/${agent}.md \
     ~/.agentecflow/templates/maui-test/agents/${agent}.converted.md
   ```

2. **Validate ASK scenarios**:
   - Are these genuine decision points?
   - Do they have clear criteria?
   - Are any actually ALWAYS/NEVER?

3. **Check technical accuracy**:
   - Are rationales correct?
   - Are consequences accurate?
   - Are recommendations sound?

4. **Verify information fidelity**:
   - Is any guidance missing?
   - Are code references still valid?
   - Are cross-references intact?

5. **Approve or refine**:
   - If approved: Replace original
   - If needs work: Note issues, refine, re-review

#### Step 3.2: Cross-Agent Consistency Check (20 minutes)

```bash
# Extract common patterns across agents
for agent in ~/.agentecflow/templates/maui-test/agents/*.converted.md; do
  echo "=== $(basename $agent) ==="
  grep "✅.*injection" $agent || echo "No DI rules"
  grep "❌.*null" $agent || echo "No null rules"
  echo ""
done
```

**Consistency Validation**:
- [ ] Similar technologies use similar phrasing (e.g., all mappers say "inject via constructor")
- [ ] Common anti-patterns phrased consistently (e.g., all say "Never use `new()`")
- [ ] ASK format consistent (question + criteria structure)

### Phase 4: Documentation & Deployment (30 minutes)

#### Step 4.1: Create Conversion Changelog (15 minutes)

**File**: `~/.agentecflow/templates/maui-test/agents/CONVERSION-CHANGELOG.md`

```markdown
# Agent Boundary Conversion Changelog

**Date**: 2025-11-22
**Task**: TASK-STND-773D
**Converted By**: [Your Name]

## Summary

Converted all 7 maui-test agents from "Best Practices" / "Anti-Patterns" format to standardized ALWAYS/NEVER/ASK boundary sections.

## Conversion Statistics

| Agent | Original Practices | Original Anti-Patterns | ALWAYS | NEVER | ASK |
|-------|-------------------|----------------------|---------|--------|-----|
| dual-write-engine | 8 | 6 | 7 | 6 | 3 |
| erroror-pattern | 10 | 10 | 7 | 7 | 4 |
| maui-di-lifecycle | 8 | 8 | 7 | 6 | 3 |
| maui-mvvm | 9 | 9 | 7 | 7 | 4 |
| realm-repository | 8 | 8 | 7 | 6 | 3 |
| riok-mapperly | 9 | 7 | 7 | 6 | 4 |
| xunit-realm-testing | 10 | 8 | 7 | 7 | 3 |

## Format Changes

**Before**:
```markdown
## Best Practices

### DO: Use Partial Classes
✅ CORRECT: Partial class allows Mapperly...

## Anti-Patterns to Avoid

### ❌ ANTI-PATTERN: Forgetting `partial`
WRONG: Missing 'partial' prevents...
```

**After**:
```markdown
## Boundaries

### ALWAYS
- ✅ Use partial classes with [Mapper] attribute (source generation)

### NEVER
- ❌ Never omit `partial` keyword on mapper classes (prevents generation)

### ASK
- ⚠️ When property names differ (use [MapProperty] or ask for alignment)
```

## Information Fidelity

- ✅ 100% of original guidance preserved
- ✅ All technical details maintained
- ✅ Rationales converted to parenthetical format
- ✅ Code examples moved to separate sections

## Validation Results

All agents passed validation:
- ✅ ALWAYS rule count: 5-7 (compliant)
- ✅ NEVER rule count: 5-7 (compliant)
- ✅ ASK rule count: ≤5 (compliant)
- ✅ Emoji usage: 100% correct
- ✅ Line length: 100% ≤100 characters
```

#### Step 4.2: Commit Changes (15 minutes)

```bash
# Replace original files with converted versions
cd ~/.agentecflow/templates/maui-test/agents/
for agent in *.converted.md; do
  original="${agent%.converted.md}.md"
  mv "$agent" "$original"
  echo "✅ Updated $original"
done

# Git commit
git add ~/.agentecflow/templates/maui-test/agents/*.md
git add ~/.agentecflow/templates/maui-test/agents/CONVERSION-CHANGELOG.md
git commit -m "refactor(agents): Standardize boundary sections to ALWAYS/NEVER/ASK format

- Convert all 7 maui-test agents to GitHub standards format
- Maintain 100% information fidelity
- Add CONVERSION-CHANGELOG.md with before/after statistics
- All agents pass validation (emoji usage, rule counts, length)

Related: TASK-STND-773D, TASK-AGENT-ENHANCER-20251121-160000"
```

---

## Testing Strategy

### Test 1: Information Fidelity

**Objective**: Verify no guidance is lost during conversion

**Method**:
```bash
# Extract all technical keywords from original
grep -oE '\b[A-Z][a-z]+[A-Z][A-Za-z]*\b' original.md | sort | uniq > original_keywords.txt

# Extract from converted
grep -oE '\b[A-Z][a-z]+[A-Z][A-Za-z]*\b' converted.md | sort | uniq > converted_keywords.txt

# Compare
diff original_keywords.txt converted_keywords.txt
```

**Success Criteria**: Diff is empty or only shows formatting artifacts

### Test 2: Format Compliance

**Objective**: Verify ALWAYS/NEVER/ASK format compliance

**Method**:
```bash
python3 scripts/validate_agent_boundaries.py <agent.md>
```

**Success Criteria**: All validation checks pass

### Test 3: Cross-Agent Consistency

**Objective**: Verify similar rules use consistent phrasing

**Method**: Manual review of common patterns (DI, null checking, async)

**Success Criteria**: ≥95% phrasing consistency for equivalent rules

### Test 4: Regression

**Objective**: Verify agent functionality unchanged

**Method**: Re-run agent-enhance on a test template, compare quality scores

**Success Criteria**: Quality scores unchanged (±0.5 acceptable variance)

---

## Design Decisions & Rationale

### Decision 1: Hybrid Conversion Approach

**Chosen**: Automated script + manual review
**Alternative**: Fully manual conversion

**Rationale**:
- ✅ Script handles 80% of straightforward conversions
- ✅ Human reviews ASK categorization (requires judgment)
- ✅ Balances speed (3 hours) with quality (100% fidelity)
- ⚠️ Script may need per-agent tweaking

### Decision 2: Rule Count Targets

**Chosen**: 5-7 ALWAYS, 5-7 NEVER, 3-5 ASK
**Alternative**: Flexible counts based on content

**Rationale**:
- ✅ Aligns with GitHub standards research
- ✅ Follows Miller's Law (7±2 items for memorability)
- ✅ Forces prioritization of critical rules
- ⚠️ May require combining related rules

### Decision 3: Code Example Placement

**Chosen**: Separate from Boundaries section
**Alternative**: Inline code examples in ALWAYS/NEVER

**Rationale**:
- ✅ Keeps Boundaries scannable
- ✅ Allows examples to demonstrate multiple rules
- ✅ Maintains clean separation of concerns
- ⚠️ Requires cross-referencing

### Decision 4: ASK Section Structure

**Chosen**: Question + Decision Criteria
**Alternative**: Conditional statements only

**Rationale**:
- ✅ Question format is more actionable
- ✅ Criteria help developers make informed decisions
- ✅ Aligns with pattern advisor recommendations
- ⚠️ Requires more effort to craft good questions

---

## Success Metrics

### Quantitative

- **Conversion completion**: 7/7 agents (100%)
- **Information fidelity**: 100% (zero guidance lost)
- **Format compliance**: 100% (all validation checks pass)
- **Cross-agent consistency**: ≥95% for equivalent rules
- **Time to complete**: ≤3 hours

### Qualitative

- **Readability**: Boundaries section is scannable and clear
- **Actionability**: Developers know what to do/not do
- **Decision support**: ASK scenarios provide clear criteria
- **Technical accuracy**: No errors introduced during conversion

### Validation

**Before Completion**:
- [ ] All 7 agents converted
- [ ] All validations pass
- [ ] Manual review complete
- [ ] Changelog documented
- [ ] Changes committed

**After Deployment** (1 week):
- [ ] No confusion reported in agent usage
- [ ] No technical errors found
- [ ] Positive feedback on clarity

---

## Risk Assessment

### Risk 1: Information Loss During Conversion

**Likelihood**: Low (script + manual review)
**Impact**: High (affects agent quality)

**Mitigation**:
- Comprehensive before/after comparison
- Keyword extraction validation
- Domain expert review
- Rollback plan (backup in place)

### Risk 2: Inconsistent Categorization (ALWAYS vs ASK)

**Likelihood**: Medium (requires judgment)
**Impact**: Medium (affects guidance clarity)

**Mitigation**:
- Clear categorization algorithm
- Manual review of ASK candidates
- Consistency check across agents
- Peer review of edge cases

### Risk 3: Script Bugs in Conversion

**Likelihood**: Medium (first-time script)
**Impact**: Medium (requires rework)

**Mitigation**:
- Test on one agent first
- Refine script based on results
- Manual validation of all conversions
- Keep `.converted.md` files until approved

---

## Rollout Plan

### Phase 1: Preparation (1 hour)
- Create backup
- Develop conversion script
- Develop validation script
- **Checkpoint**: Scripts tested on sample agent

### Phase 2: Conversion (1.5 hours)
- Test conversion on one agent
- Refine script
- Batch convert all 7 agents
- **Checkpoint**: All conversions complete, validations pass

### Phase 3: Review (1 hour)
- Domain expert review each agent
- Cross-agent consistency check
- Approve or refine conversions
- **Checkpoint**: All agents approved by expert

### Phase 4: Deploy (30 minutes)
- Create changelog
- Replace original files
- Commit changes
- **Checkpoint**: Changes committed, task complete

**Total Estimated Time**: 4 hours

---

## Dependencies

**Blocks**: None
**Blocked By**: None
**Related**:
- TASK-AGENT-ENHANCER-20251121-160000 (GitHub standards implementation) - Completed
- TASK-UX-B9F7 (agent-enhance UX simplification) - Independent

---

## Completion Checklist

Before marking this task complete:

- [ ] AC1: Conversion algorithm implemented (5 sub-criteria)
- [ ] AC2: Format standardization (6 sub-criteria)
- [ ] AC3: All 7 agents converted (7 sub-criteria)
- [ ] AC4: Quality validation (5 sub-criteria)
- [ ] AC5: Cross-agent consistency (4 sub-criteria)
- [ ] AC6: Documentation (3 sub-criteria)
- [ ] All validation scripts pass
- [ ] Manual review complete (domain expert)
- [ ] Cross-agent consistency verified
- [ ] Changelog documented
- [ ] Changes committed to git
- [ ] No regressions in agent quality
- [ ] Backup created and verified

---

**Created**: 2025-11-22T12:30:00Z
**Updated**: 2025-11-22T12:30:00Z
**Status**: BACKLOG
**Ready for Implementation**: YES

---

## Appendix: Detailed Specifications

The comprehensive specifications created by software-architect and pattern-advisor agents are available in the task creation session and include:

1. **Conversion Algorithm Specification**: Detailed extraction, categorization, and formatting algorithms
2. **Pattern Structure Analysis**: ALWAYS/NEVER/ASK design principles, optimal rule counts, phrasing guidelines
3. **Example Conversions**: Before/after examples for mapping, database, and testing agents
4. **Quality Validation Framework**: Information fidelity checks, consistency validation, format compliance tests

These specifications provide complete implementation guidance for this standardization refinement task.

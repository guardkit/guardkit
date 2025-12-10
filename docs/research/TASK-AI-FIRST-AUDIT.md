# TASK-AI-FIRST-AUDIT: Audit Current Code for AI-First Compliance

**Created**: 2025-11-14
**Priority**: Critical
**Type**: Investigation / Technical Debt Assessment
**Status**: Backlog
**Complexity**: 3/10 (Low-Medium - Automated scanning + manual review)
**Estimated Effort**: 3-4 hours
**Dependencies**: TASK-AI-FIRST-GUIDELINES (for reference criteria)
**Related Tasks**: TASK-077E (original implementation), Template-Create Forensic Analysis

---

## Problem Statement

Current codebase has accumulated ~656 LOC of Python pattern matching that replaced AI intelligence during template-create evolution. Need comprehensive audit to identify all violations, measure technical debt, and prioritize cleanup.

**Goal**: Quantify AI-first compliance violations and create actionable cleanup plan with prioritized tasks.

---

## Context

**Forensic Analysis**: [template-create-forensic-analysis.md](../../docs/investigations/template-create-forensic-analysis.md)

**Known Violations** (from forensic analysis):
1. **TASK-9039**: SmartDefaultsDetector - 531 LOC of pattern matching
2. **TASK-E8F4**: JSON parsing logic - 125 LOC of fallback strategies  
3. **TASK-TMPL-4E89**: Hard-coded agent detection - Limited to 5 patterns
4. **Build artifact counting**: May have hard-coded exclusions

**Total Known**: ~656 LOC of pattern matching

**Unknown**: Other files may have pattern matching that wasn't part of template-create

---

## Objectives

### Primary Objective
Complete audit of codebase to identify all AI-first principle violations and create prioritized cleanup plan.

### Success Criteria
- [ ] All pattern matching code identified and catalogued
- [ ] LOC count per violation
- [ ] Impact assessment (high/medium/low)
- [ ] Prioritized cleanup task list
- [ ] Technical debt metrics calculated
- [ ] Audit report generated

---

## Audit Scope

### Files to Audit

**High Priority** (template-create related):
- `installer/core/lib/smart_defaults/detector.py` - TASK-9039 (531 LOC)
- `installer/core/commands/template-create.md` - JSON parsing (125 LOC)
- `installer/core/lib/agent_generator/agent_generator.py` - Hard-coded patterns
- `installer/core/commands/lib/template_create_orchestrator.py` - Orchestration logic

**Medium Priority** (related components):
- `installer/core/lib/codebase_analyzer/*.py` - Analysis logic
- `installer/core/lib/template_generator/*.py` - Template generation
- `installer/core/lib/template_creation/*.py` - Creation components

**Low Priority** (other commands):
- `installer/core/commands/template-validate.md` - Validation logic
- `installer/core/commands/template-init.md` - Init logic
- `installer/core/commands/task-create.md` - Task creation

### Violation Categories

Track violations by type:

1. **File Extension Checks**
   - Pattern: `f.suffix == '.py'`, `endswith('.cs')`
   - Severity: High (maintenance burden)

2. **Dependency Name Matching**
   - Pattern: `'react' in dependencies`, `if pkg == 'fastapi'`
   - Severity: High (limited to known frameworks)

3. **Pattern Name Hard-Coding**
   - Pattern: `'Repository' in filename`, `'ViewModel' in class_name`
   - Severity: Critical (defeats AI-first purpose)

4. **Multi-Strategy Parsing**
   - Pattern: Multiple fallback strategies, regex parsing
   - Severity: Medium (complexity, should fix prompts instead)

5. **Hard-Coded Configuration**
   - Pattern: Built-in lists of frameworks, languages, patterns
   - Severity: Medium (maintenance burden)

---

## Implementation Scope

### Phase 1: Automated Scanning (1 hour)

**Script**: `scripts/audit_ai_first_compliance.py`

**Features**:
```python
#!/usr/bin/env python3
"""Audit codebase for AI-first compliance violations."""

import ast
import re
from pathlib import Path
from typing import Dict, List

class AIFirstAuditor:
    """Scan codebase for pattern matching and hard-coding."""
    
    VIOLATION_PATTERNS = {
        'file_extension_check': [
            r'\.suffix\s*==',
            r'\.endswith\(["\']\.[\w]+["\']',
            r'\.name\s*==\s*["\'][\w]+\.[\w]+["\']',
        ],
        'dependency_matching': [
            r'["\']react["\'].*in',
            r'["\']fastapi["\'].*in',
            r'if.*==\s*["\'][\w-]+["\'].*#.*framework',
        ],
        'pattern_hard_coding': [
            r'["\']Repository["\'].*in',
            r'["\']ViewModel["\'].*in',
            r'["\']Service["\'].*in',
            r'if.*["\'][\w]+Pattern["\']',
        ],
        'multi_strategy_parsing': [
            r'try:.*json\.loads.*except:.*try:',
            r'# Strategy \d+:',
            r'fallback.*pattern',
        ],
    }
    
    def audit_file(self, filepath: Path) -> Dict:
        """Audit single file for violations."""
        violations = {
            'file': str(filepath),
            'total_lines': 0,
            'violations': [],
            'severity_score': 0,
        }
        
        content = filepath.read_text()
        lines = content.split('\n')
        violations['total_lines'] = len(lines)
        
        # Check each violation pattern
        for category, patterns in self.VIOLATION_PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1
                    violations['violations'].append({
                        'category': category,
                        'line': line_num,
                        'code': lines[line_num - 1].strip(),
                        'pattern': pattern,
                    })
        
        # Calculate severity score
        violations['severity_score'] = self._calculate_severity(violations['violations'])
        
        return violations
    
    def audit_directory(self, dirpath: Path) -> List[Dict]:
        """Audit all Python files in directory."""
        results = []
        for filepath in dirpath.rglob('*.py'):
            if '__pycache__' in str(filepath):
                continue
            result = self.audit_file(filepath)
            if result['violations']:
                results.append(result)
        return results
    
    def generate_report(self, results: List[Dict]) -> str:
        """Generate audit report."""
        # ... report generation logic
```

**Scan targets**:
```bash
# Run audit
python scripts/audit_ai_first_compliance.py \
    --path installer/core \
    --output docs/investigations/ai-first-audit-2025-11-14.md \
    --format markdown
```

### Phase 2: Manual Review (1 hour)

Review automated findings for:
- False positives (legitimate uses)
- Context and impact assessment
- Dependency analysis (what depends on violations)
- Cleanup complexity estimation

### Phase 3: Metrics Calculation (30 min)

**Calculate**:
```python
# Technical Debt Metrics
total_violations = count_all_violations()
total_loc_violations = sum(violation.loc for violation in violations)
files_affected = len(unique_files)
avg_violations_per_file = total_violations / files_affected

# Impact Metrics
high_severity_count = count_by_severity('high')
medium_severity_count = count_by_severity('medium')
low_severity_count = count_by_severity('low')

# Cleanup Metrics
estimated_cleanup_hours = calculate_cleanup_effort()
priority_cleanup_tasks = identify_high_impact_violations()
```

### Phase 4: Cleanup Plan Creation (1 hour)

**Create tasks** for each major violation:

```markdown
## Cleanup Task Template

### TASK-CLEANUP-{ID}: Remove {Violation Type} from {Component}

**Priority**: {High/Medium/Low based on impact}
**Estimated**: {Hours based on LOC and complexity}
**Files**: {List of files}
**LOC to Remove**: {Count}
**Replacement Strategy**: {AI-first alternative}

**Before**:
```python
# Hard-coded pattern matching
if f.suffix == '.py':
    return 'Python'
```

**After**:
```python
# AI analysis
language = ai.analyze("What language are these files?")
```
```

### Phase 5: Report Generation (30 min)

**Output**: `docs/investigations/ai-first-audit-2025-11-14.md`

**Report Structure**:
```markdown
# AI-First Compliance Audit Report
Date: 2025-11-14
Auditor: Claude

## Executive Summary
- Total Violations: {count}
- Total LOC: {count}
- Files Affected: {count}
- Estimated Cleanup: {hours}

## Violations by Category
### File Extension Checks
- Count: {count}
- LOC: {count}
- Severity: High
- Files: {list}

### Dependency Matching
- Count: {count}
- LOC: {count}
- Severity: High
- Files: {list}

### Pattern Hard-Coding
- Count: {count}
- LOC: {count}
- Severity: Critical
- Files: {list}

### Multi-Strategy Parsing
- Count: {count}
- LOC: {count}
- Severity: Medium
- Files: {list}

## Prioritized Cleanup Tasks
1. TASK-CLEANUP-001: Remove SmartDefaultsDetector (531 LOC, 8h)
2. TASK-CLEANUP-002: Remove JSON parsing fallbacks (125 LOC, 3h)
3. TASK-CLEANUP-003: Replace hard-coded agent detection (2h)
...

## Technical Debt Metrics
- Maintainability Score: {0-100}
- Extensibility Score: {0-100}
- AI-First Compliance: {percentage}

## Recommendations
1. Immediate: High-severity violations
2. Short-term: Medium-severity violations
3. Long-term: Low-severity violations
```

---

## Files to Create/Update (Checklist)

### Audit Scripts
- [ ] `scripts/audit_ai_first_compliance.py` - Automated scanning
- [ ] `scripts/calculate_cleanup_effort.py` - Effort estimation

### Reports
- [ ] `docs/investigations/ai-first-audit-2025-11-14.md` - Audit report
- [ ] `docs/investigations/ai-first-audit-summary.md` - Executive summary
- [ ] `docs/technical-debt/ai-first-violations.json` - Machine-readable data

### Cleanup Tasks
- [ ] `tasks/backlog/TASK-CLEANUP-001-smart-defaults.md`
- [ ] `tasks/backlog/TASK-CLEANUP-002-json-parsing.md`
- [ ] `tasks/backlog/TASK-CLEANUP-003-agent-detection.md`
- [ ] ... (generated based on findings)

---

## Acceptance Criteria

### Functional Requirements
- [ ] All Python files scanned
- [ ] All violations identified and categorized
- [ ] LOC counted per violation
- [ ] Impact assessment completed
- [ ] Cleanup tasks created
- [ ] Technical debt metrics calculated

### Quality Requirements
- [ ] False positives reviewed and filtered
- [ ] Context considered for each violation
- [ ] Cleanup effort realistic
- [ ] Priority based on impact
- [ ] Machine-readable output (JSON)

### Documentation Requirements
- [ ] Audit report comprehensive
- [ ] Examples of each violation type
- [ ] Before/after for each cleanup task
- [ ] Metrics explained
- [ ] Recommendations prioritized

---

## Testing Requirements

### Audit Script Validation
```bash
# 1. Test on known violations
python scripts/audit_ai_first_compliance.py \
    --path installer/core/lib/smart_defaults \
    --test-mode

# Expected: Detect all violations in SmartDefaultsDetector

# 2. Test false positive handling
python scripts/audit_ai_first_compliance.py \
    --path tests/ \
    --test-mode

# Expected: Legitimate test patterns not flagged

# 3. Verify report generation
ls docs/investigations/ai-first-audit-2025-11-14.md
# Expected: Report exists and is complete
```

---

## Expected Findings

Based on forensic analysis, expect to find:

### High Priority Violations (656+ LOC)
1. **SmartDefaultsDetector** (531 LOC)
   - File: `installer/core/lib/smart_defaults/detector.py`
   - Violations: File extension checks, dependency matching
   - Impact: Critical (maintenance burden)
   - Cleanup: 8-10 hours

2. **JSON Parsing Logic** (125 LOC)
   - File: `installer/core/commands/template-create.md`
   - Violations: Multi-strategy parsing, regex fallbacks
   - Impact: High (complexity)
   - Cleanup: 3-4 hours

3. **Agent Detection** (Unknown LOC)
   - File: `installer/core/lib/agent_generator/agent_generator.py`
   - Violations: Pattern name hard-coding (5 patterns)
   - Impact: Critical (defeats purpose)
   - Cleanup: 2-3 hours

### Medium Priority Violations (TBD)
- Build artifact exclusion lists
- Template validation pattern checks
- Config file format detection

### Low Priority Violations (TBD)
- Test utilities (may be legitimate)
- Development scripts
- One-off automation

---

## Success Metrics

**Quantitative**:
- Total violations found: {count}
- Files with violations: {count}
- LOC of pattern matching: {count}
- Cleanup tasks created: {count}
- Estimated cleanup hours: {count}

**Qualitative**:
- All violations categorized
- Impact assessment complete
- Cleanup plan actionable
- Priorities clear

---

## Related Tasks

- **TASK-AI-FIRST-GUIDELINES**: Reference for violation criteria
- **TASK-CLEANUP-***: Generated cleanup tasks (created by this audit)
- **TASK-077E**: Target architecture (original implementation)
- **Template-Create Forensic Analysis**: Context for violations

---

## Implementation Notes

### Known Files to Check

**Definitely check**:
- ✅ `installer/core/lib/smart_defaults/detector.py` (TASK-9039)
- ✅ `installer/core/commands/template-create.md` (TASK-E8F4)
- ✅ `installer/core/lib/agent_generator/agent_generator.py` (TASK-TMPL-4E89)
- ❓ `installer/core/commands/lib/template_create_orchestrator.py`
- ❓ `installer/core/lib/codebase_analyzer/*.py`

**May have issues**:
- Build artifact exclusion code
- Template validation logic
- Language detection helpers

### Automated vs Manual

**Automated** (80% coverage):
- Pattern regex matching
- LOC counting
- File listing
- Basic categorization

**Manual** (20% coverage):
- False positive filtering
- Context assessment
- Impact analysis
- Cleanup complexity

### Report Distribution

**Audiences**:
1. **Developers**: Detailed violations, cleanup tasks
2. **Management**: Executive summary, technical debt metrics
3. **Code Review**: Reference for PR reviews

---

## Next Steps After Completion

1. **Review findings** with team
2. **Prioritize cleanup tasks** based on impact
3. **Create cleanup schedule** (sprint planning)
4. **Track progress** via task completion
5. **Re-audit** after cleanup (verify compliance)
6. **Update guidelines** based on findings

---

## Output Artifacts

1. **Audit Report**: `docs/investigations/ai-first-audit-2025-11-14.md`
2. **Data File**: `docs/technical-debt/ai-first-violations.json`
3. **Cleanup Tasks**: Multiple task files in `tasks/backlog/`
4. **Metrics Dashboard**: Visual representation of technical debt

---

**Document Status**: Ready for Implementation
**Created**: 2025-11-14
**Parent**: Template-Create Recovery
**Note**: Prerequisite for systematic cleanup

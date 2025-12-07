# complexity-evaluator - Extended Reference

This file contains detailed documentation for the `complexity-evaluator` agent.
Load this file when you need comprehensive examples and guidance.

```bash
cat agents/complexity-evaluator-ext.md
```


## Example Scenarios

### Scenario 1: Simple Task (Score 2, Auto-Proceed)
```
Task: Add validation to existing user registration
Files: 1 (validators/user_validator.py)
Patterns: None
Risk: None

Score Breakdown:
- File complexity: 0/3 (1 file)
- Pattern familiarity: 0/2 (no patterns)
- Risk level: 0/3 (no risk indicators)
- Total: 0/10 → Rounded up to minimum score 2

Review Mode: AUTO_PROCEED
Action: Display summary, proceed to Phase 3
```

### Scenario 2: Moderate Task (Score 5, Quick Optional)
```
Task: Implement user profile service with repository
Files: 4 (service, repository, model, tests)
Patterns: Repository pattern
Risk: None

Score Breakdown:
- File complexity: 1/3 (4 files)
- Pattern familiarity: 0/2 (simple pattern)
- Risk level: 0/3 (no risk indicators)
- Total: 1/10 → Rounded up to 5 (normalized)

Review Mode: QUICK_OPTIONAL
Action: Offer optional checkpoint, default to proceed
```

### Scenario 3: Complex Task (Score 8, Full Required)
```
Task: Implement OAuth2 authentication with JWT tokens
Files: 8 (auth service, token manager, middleware, validators, etc.)
Patterns: Strategy (multiple auth providers), Factory (token creation)
Risk: Security (auth, tokens, encryption), External (OAuth providers)

Score Breakdown:
- File complexity: 2/3 (8 files)
- Pattern familiarity: 1/2 (moderate patterns)
- Risk level: 3/3 (critical risk - security + external)
- Total: 6/10 → But security trigger forces FULL_REQUIRED

Review Mode: FULL_REQUIRED
Action: Mandatory Phase 2.6 checkpoint
Triggers: security_keywords
```

### Scenario 4: Forced Review (Score 3, but User Flag)
```
Task: Simple bug fix in utility function
Files: 1
Patterns: None
Risk: None
User Flag: --review

Score Breakdown:
- File complexity: 0/3 (1 file)
- Pattern familiarity: 0/2 (no patterns)
- Risk level: 0/3 (no risk)
- Total: 0/10 → Would be AUTO_PROCEED

Review Mode: FULL_REQUIRED (forced by user flag)
Action: Mandatory Phase 2.6 checkpoint
Triggers: user_flag
```


## Output Format

### Auto-Proceed Summary (Score 1-3)
```
✅ Complexity Evaluation - TASK-XXX

Score: 2/10 (Low Complexity - Auto-Proceed)

Factor Breakdown:
  • file_complexity: 0/3 - Simple change (1 file) - minimal complexity
  • pattern_familiarity: 0/2 - No specific patterns mentioned - straightforward implementation
  • risk_level: 0/3 - No significant risk indicators - low risk

✅ AUTO-PROCEEDING to Phase 3 (Implementation)
   No human review required for this simple task.
```

### Quick Optional Summary (Score 4-6)
```
⚠️  Complexity Evaluation - TASK-XXX

Score: 5/10 (Moderate Complexity - Optional Review)

Factor Breakdown:
  • file_complexity: 1/3 - Moderate change (4 files) - multi-file coordination
  ⚠️ pattern_familiarity: 1/2 - Moderate patterns: Strategy, Observer - familiar complexity
  • risk_level: 1/3 - Moderate risk (1 risk category) - standard caution

⚠️  OPTIONAL CHECKPOINT
   You may review the plan before proceeding, but it's not required.
   [A]pprove and proceed | [R]eview in detail | [Enter] to auto-approve
```

### Full Required Summary (Score 7-10)
```
🔴 Complexity Evaluation - TASK-XXX

Score: 8/10 (High Complexity - REVIEW REQUIRED)

Force-Review Triggers:
  🔴 Security Keywords

Factor Breakdown:
  🔴 file_complexity: 2/3 - Complex change (8 files) - multiple components
  ⚠️ pattern_familiarity: 1/2 - Moderate patterns: Strategy, Factory - familiar complexity
  🔴 risk_level: 3/3 - Critical risk (2+ risk categories) - comprehensive review required

🔴 MANDATORY CHECKPOINT - Phase 2.6 Required
   This task requires human review before implementation.
   Proceeding to Phase 2.6 human checkpoint...
```


## Extended Documentation

For detailed examples, patterns, and implementation guides, load the extended documentation:

```bash
cat complexity-evaluator-ext.md
```

Or in Claude Code:
```
Please read complexity-evaluator-ext.md for detailed examples.
```

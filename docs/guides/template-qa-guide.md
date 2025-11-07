# Template Q&A Session Guide

**Purpose**: Complete reference for the interactive Q&A sessions in `/template-create` and `/template-init` commands.

**Audience**: Users who want to understand Q&A mechanics, validation rules, and session management.

---

## Table of Contents

1. [Overview](#overview)
2. [Q&A Mechanics](#qa-mechanics)
3. [Question Types](#question-types)
4. [Validation Rules](#validation-rules)
5. [Session Management](#session-management)
6. [Brownfield vs Greenfield](#brownfield-vs-greenfield)
7. [Tips & Tricks](#tips--tricks)

---

## Overview

### What is the Q&A Session?

Both `/template-create` and `/template-init` use interactive Q&A sessions to gather information:

- **`/template-create`**: 8 questions about existing codebase (~3 minutes)
- **`/template-init`**: 42 questions about technology preferences (~8 minutes)

### Why Q&A Instead of Configuration Files?

**Benefits**:
- ✅ Interactive guidance (no need to know structure)
- ✅ Validation on-the-fly (catch errors immediately)
- ✅ Context-aware questions (skip irrelevant sections)
- ✅ Resumable sessions (save progress anytime)
- ✅ Better UX (progressive disclosure)

**vs Configuration Files**:
- ❌ Must know schema beforehand
- ❌ Validation only after completion
- ❌ All-or-nothing approach
- ❌ No guidance for choices

---

## Q&A Mechanics

### Session Lifecycle

```
START
  ↓
[Load Previous Session?] → Yes → RESUME from saved state
  ↓ No
[Section 1] → Questions 1-N
  ↓
[Section 2] → Questions N+1-M
  ↓
... (continue for all sections)
  ↓
[Summary Display]
  ↓
[Confirmation] → No → EXIT (save session)
  ↓ Yes
PROCEED to next phase
```

### Session State

The system tracks:

```python
{
  "session_id": "uuid",
  "template_type": "brownfield|greenfield",
  "started_at": "2025-11-06T10:30:00Z",
  "current_section": 3,
  "current_question": 12,
  "answers": {
    "template_name": "my-template",
    "primary_language": "Python",
    ...
  },
  "completed_sections": [1, 2]
}
```

Saved to: `.template-init-session.json` or `.template-create-session.json`

### Display Format

```
------------------------------------------------------------
  Section N: Section Name (N/Total)
------------------------------------------------------------

Question text here with clear explanation?
  [1] Option one (description)
  [2] Option two (description)
  [3] Option three (description)

Detected: <auto-detected value> (if applicable)
Enter number (default: <default value>):
```

**Elements**:
- **Section header**: Shows progress (N/Total)
- **Question text**: Clear, concise
- **Options**: Numbered with descriptions
- **Detection**: Shows AI-detected values
- **Default**: Indicated in prompt
- **Input**: Clean, validated immediately

---

## Question Types

### Type 1: Single Choice

Most common type - pick one option.

```
Primary language?
  [1] C#
  [2] TypeScript
  [3] Python
  [4] Java

Enter number:
```

**Input**: Single number (e.g., `3`)
**Validation**: Must be 1-4
**Default**: None (required input)

### Type 2: Single Choice with Default

Like single choice but has default value.

```
Framework version?
  [1] Latest (0.104+) [DEFAULT]
  [2] LTS
  [3] Specific version

Enter number (default: 1):
```

**Input**: Number or Enter for default
**Validation**: Must be 1-3 or empty
**Default**: 1 (shown in prompt)

### Type 3: Multiple Choice

Select multiple options via comma-separated list.

```
Testing scope (select multiple)?
  [1] Unit tests
  [2] Integration tests
  [3] E2E tests
  [4] Performance tests

Enter numbers (comma-separated, e.g., 1,2,3):
```

**Input**: `1,2,3` or `1, 2, 3` (spaces ok)
**Validation**: All numbers must be 1-4
**Default**: None (required)

### Type 4: Text Input

Free-form text with validation.

```
What should this template be called?
  Validation: 3-50 chars, alphanumeric + hyphens/underscores
  Example: python-fastapi-template

Enter value:
```

**Input**: Text string
**Validation**: Custom per question
**Default**: Sometimes provided

### Type 5: Text Input with Detection

Like text input but offers detected value.

```
What should this template be called?
  (Detected from directory: my-maui-app)

Enter value (default: my-maui-app):
```

**Input**: Text or Enter for detected
**Validation**: Custom
**Default**: Detected value

### Type 6: Path Input

File or directory path with existence validation.

```
Where is the codebase?
  [1] Current directory (./)
  [2] Specify path

Enter number: 2
Enter path:
```

**Input**: Absolute or relative path
**Validation**: Path must exist
**Default**: Current directory

### Type 7: Multi-line Text

For pasting documentation or large text blocks.

```
Paste your documentation (end with empty line):
Line 1:
```

**Input**: Multiple lines, empty line to end
**Validation**: Content-specific
**Default**: None

### Type 8: URL Input

Web URL with format validation.

```
Enter documentation URL:
```

**Input**: Full URL with protocol
**Validation**: Must match URL pattern
**Default**: None

### Type 9: Conditional Question

Only shown based on previous answers.

```
# Only if UI framework selected
UI architecture pattern?
  [1] MVVM
  [2] MVC
  [3] Component-based

Enter number:
```

**Trigger**: Conditional logic
**Skipped**: If condition not met

### Type 10: Yes/No Question

Binary choice.

```
Generate custom agents?
  [1] Yes
  [2] No

Enter number:
```

**Input**: 1 or 2
**Validation**: Must be 1 or 2
**Default**: Usually 1

---

## Validation Rules

### Template Name Validation

```python
Rules:
  - Length: 3-50 characters
  - Pattern: ^[a-zA-Z0-9_-]+$
  - No spaces allowed
  - Must start with alphanumeric

Valid:
  ✅ python-fastapi-template
  ✅ dotnet_maui_mvvm
  ✅ MyCompanyTemplate123

Invalid:
  ❌ te (too short)
  ❌ my template (contains space)
  ❌ -my-template (starts with hyphen)
  ❌ my@template (invalid character)
```

### Number Choice Validation

```python
Rules:
  - Must be integer
  - Must be in valid range
  - No leading zeros

Valid:
  ✅ 1
  ✅ 3

Invalid:
  ❌ 0 (out of range)
  ❌ 10 (out of range)
  ❌ 1.5 (not integer)
  ❌ one (not numeric)
  ❌ 01 (leading zero)
```

### Multiple Choice Validation

```python
Rules:
  - Comma-separated integers
  - Each must be in valid range
  - Duplicates removed
  - Spaces ignored

Valid:
  ✅ 1,2,3
  ✅ 1, 2, 3 (spaces ok)
  ✅ 3,1,2 (order ok)
  ✅ 1,1,2 (duplicates removed → 1,2)

Invalid:
  ❌ 1,10 (10 out of range)
  ❌ 1,2,abc (invalid number)
  ❌ 1;2;3 (wrong separator)
```

### Path Validation

```python
Rules:
  - Must be valid path format
  - Must exist on filesystem
  - Readable by process

Valid:
  ✅ /absolute/path/to/dir
  ✅ ./relative/path
  ✅ ~/user/home/path

Invalid:
  ❌ /nonexistent/path (doesn't exist)
  ❌ path/with\invalid*chars (OS-specific)
  ❌ /no/permission (not readable)
```

### URL Validation

```python
Rules:
  - Must include protocol (http:// or https://)
  - Valid domain format
  - No spaces

Valid:
  ✅ https://docs.python.org
  ✅ http://example.com/path
  ✅ https://wiki.company.com/arch

Invalid:
  ❌ docs.python.org (no protocol)
  ❌ https:// docs.python.org (space)
  ❌ ftp://example.com (unsupported protocol)
```

### Version String Validation

```python
Rules:
  - Semantic versioning: major.minor.patch
  - Partial versions ok: major.minor
  - Version ranges ok: >=1.0.0, ~2.1.0

Valid:
  ✅ 1.0.0
  ✅ 2.1
  ✅ 3.0.0-beta.1
  ✅ >=1.5.0

Invalid:
  ❌ 1 (too short)
  ❌ v1.0.0 (prefix not allowed)
  ❌ 1.0.x (invalid character)
```

---

## Session Management

### Saving Sessions

**Automatic Save on Ctrl+C**:

```bash
/template-init
# Answer some questions...
# Press Ctrl+C

Output:
Session saved to: .template-init-session.json
Progress: Section 3/10, Question 12/42

Resume with: /template-init --resume
```

**What Gets Saved**:
```json
{
  "session_id": "abc-123",
  "template_type": "greenfield",
  "started_at": "2025-11-06T10:30:00Z",
  "saved_at": "2025-11-06T10:35:00Z",
  "current_section": 3,
  "current_question": 12,
  "answers": {
    "template_name": "my-template",
    "template_purpose": "production",
    "primary_language": "Python",
    "framework": "FastAPI",
    ...
  },
  "completed_sections": [1, 2]
}
```

### Resuming Sessions

**Automatic Resume Prompt**:

```bash
/template-init

Output:
Found existing session saved at 2025-11-06T10:35:00Z
Progress: Section 3/10 (12 questions answered)

Resume from where you left off? (Y/n):
```

**Manual Resume**:

```bash
# Resume from default location
/template-init --resume

# Resume from custom file
/template-init --session-file /path/to/session.json
```

**Resume Behavior**:
- Skips completed sections
- Starts at last question
- Shows previous answers in summary
- Can modify previous answers via summary

### Clearing Sessions

```bash
# Delete session file
rm .template-init-session.json

# Or move to archive
mv .template-init-session.json archive/session-2025-11-06.json
```

### Session Conflicts

If multiple sessions exist:

```bash
Multiple session files found:
  [1] .template-init-session.json (2025-11-06T10:35:00Z)
  [2] session-backup.json (2025-11-05T14:20:00Z)

Which session to resume? (default: 1):
```

---

## Brownfield vs Greenfield

### Brownfield (/template-create)

**8 Questions, ~3 minutes**

```
Section 1: Codebase Location (1 question)
  • Where is the code?

Section 2: Template Identity (1 question)
  • Template name

Section 3: Technology Stack (1 question)
  • Primary language

Section 4: Template Purpose (1 question)
  • Purpose/use case

Section 5: Architecture (1 question)
  • Architecture pattern

Section 6: Example Files (1 question)
  • Which files to analyze

Section 7: Agents (1 question)
  • Generate custom agents?

Section 8: Confirmation (1 question)
  • Review and confirm
```

**Characteristics**:
- Short (8 questions)
- Fast (~3 minutes)
- Code-focused
- Auto-detection heavy

### Greenfield (/template-init)

**42 Questions, ~8 minutes**

```
Section 1: Template Identity (2 questions)
  • Name, purpose

Section 2: Technology Stack (3 questions)
  • Language, framework, version

Section 3: Architecture (2 questions)
  • Pattern, domain modeling

Section 4: Project Structure (2 questions)
  • Organization, folders

Section 5: Testing (3 questions)
  • Framework, scope, patterns

Section 6: Error Handling (2 questions)
  • Strategy, validation

Section 7: Dependencies (2 questions)
  • DI, configuration

Section 8: UI/Navigation (2 questions, conditional)
  • UI pattern, navigation

Section 9: Additional Patterns (3 questions, conditional)
  • Data access, API, state

Section 10: Documentation (5 questions, conditional)
  • Input, method, usage
```

**Characteristics**:
- Comprehensive (42 questions)
- Longer (~8 minutes)
- Design-focused
- Few auto-detections

### Comparison Table

| Aspect | Brownfield | Greenfield |
|--------|-----------|-----------|
| **Questions** | 8 | 42 |
| **Duration** | ~3 minutes | ~8 minutes |
| **Sections** | 8 | 10 |
| **Auto-detection** | Heavy | Light |
| **Focus** | Existing code | Design choices |
| **Conditional** | Few | Many |
| **Input** | Mostly choices | Mix of choices & text |

---

## Tips & Tricks

### Speed Tips

**Use Defaults**:
```bash
# Instead of typing choices, press Enter for defaults
Framework version?
  [1] Latest (0.104+) [DEFAULT]

Just press Enter → selects 1
```

**Skip with --skip**:
```bash
# Use all defaults (testing/automation)
/template-init --skip
```

**Prepare Answers**:
```bash
# Write down answers beforehand
# Copy-paste when prompted
```

### Accuracy Tips

**Read Carefully**:
- Don't rush through questions
- Understand implications of choices
- Wrong architecture choice = wrong template

**Use Detection**:
```bash
# AI detection is usually accurate
Template name?
  (Detected: my-maui-app)

# If correct, just press Enter
```

**Check Summary**:
```bash
# Always review summary before confirming
# Last chance to catch mistakes
```

### Recovery Tips

**Save Often**:
```bash
# If session is long, save periodically
# Press Ctrl+C, then resume immediately
```

**Keep Session Files**:
```bash
# Archive session files for reference
mkdir session-archive
mv .template-init-session.json session-archive/template-v1.json
```

**Modify After Generation**:
```bash
# If you made wrong choice, easier to:
# 1. Complete session anyway
# 2. Modify generated files
# vs restarting entire Q&A
```

### Efficiency Tips

**Batch Templates**:
```bash
# Create multiple similar templates quickly
# Use same answers, change key details

# Template 1
/template-init
# Answer all questions

# Template 2
/template-init
# Most answers same, change framework

# Saves time vs starting fresh each time
```

**Team Defaults**:
```bash
# Save company-standard session file
/template-init
# Answer with company standards
# Ctrl+C after completing
mv .template-init-session.json company-defaults.json

# Team members use:
/template-init --session-file company-defaults.json
# Just modify project-specific answers
```

### Troubleshooting Tips

**Validation Errors**:
```bash
# If validation fails repeatedly
# Check error message carefully
# Common issues:
# - Spaces in names
# - Missing characters
# - Wrong format

Template name: my template  # ❌ space
Error: Name must be alphanumeric with hyphens/underscores

Template name: my-template  # ✅ correct
```

**Path Issues**:
```bash
# Use tab completion
# Ensures path exists and correct

Codebase path: /Users/me/pro<TAB>
# Auto-completes to: /Users/me/projects/
```

**Session Corruption**:
```bash
# If session file corrupted
# Delete and start fresh
rm .template-init-session.json
/template-init
```

---

## Advanced Usage

### Custom Session Files

```bash
# Create template for specific use case
/template-init --session-file api-template.json

# Later reuse
/template-init --session-file api-template.json
# Modify as needed
```

### Programmatic Q&A

```python
# For automation/testing
from template_qa_session import TemplateQASession

session = TemplateQASession()
session.set_answer("template_name", "automated-template")
session.set_answer("primary_language", "Python")
# ... set all answers
result = session.complete()
```

### Session Analytics

```bash
# Extract metrics from session
cat .template-init-session.json | jq '{
  duration: (.saved_at - .started_at),
  progress: .current_section,
  completed: .completed_sections | length
}'
```

---

## Next Steps

### Learn More

- **Getting Started**: [template-commands-getting-started.md](./template-commands-getting-started.md)
- **Brownfield Guide**: [template-create-walkthrough.md](./template-create-walkthrough.md)
- **Greenfield Guide**: [template-init-walkthrough.md](./template-init-walkthrough.md)
- **Troubleshooting**: [template-troubleshooting.md](./template-troubleshooting.md)

### Practice

```bash
# Try a complete session
/template-init

# Experiment with Ctrl+C and resume
# Get comfortable with flow
# Understand question types
```

---

**Created**: 2025-11-06
**Task**: TASK-014
**Version**: 1.0.0
**Maintained By**: Platform Team

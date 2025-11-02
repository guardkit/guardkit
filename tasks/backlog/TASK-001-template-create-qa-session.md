---
id: TASK-001
title: Interactive Q&A Session for /template-create
status: backlog
created: 2025-11-01T20:00:00Z
priority: high
complexity: 4
estimated_hours: 6
tags: [qa-session, interactive, user-experience]
epic: EPIC-001
feature: ai-analysis
dependencies: []
blocks: [TASK-002]
---

# TASK-001: Interactive Q&A Session for /template-create

## Objective

Create an interactive Q&A session (similar to `/gather-requirements`) that guides users through the template creation process from an existing codebase.

**Purpose**: Gather context before AI analysis to improve accuracy and user experience.

## Acceptance Criteria

- [ ] Interactive Q&A flow with 10 targeted questions (including documentation input)
- [ ] Session persistence (save/resume capability)
- [ ] Input validation and helpful prompts
- [ ] Summary of answers before proceeding to AI analysis
- [ ] Option to skip Q&A and proceed directly to analysis
- [ ] Clear, user-friendly CLI interface
- [ ] Unit tests for Q&A flow

## Questions to Ask

### 1. Template Purpose
```
What is the primary purpose of this template?

[a] Create new projects from this architecture
[b] Share project structure with team
[c] Document existing patterns
[d] Create variations of this project

Purpose: Helps AI focus analysis on relevant aspects
```

### 2. Codebase Path
```
Path to the existing codebase to analyze:

[Enter path or use current directory]

Validation: Path exists, contains code files
```

### 3. Template Scope
```
What should be included in the template?

[✓] Project structure (folders, files)
[✓] Code patterns (classes, functions)
[ ] Configuration files (package.json, etc.)
[ ] Build scripts
[ ] Documentation
[ ] Tests

Purpose: Defines what AI should focus on extracting
```

### 4. Quality Focus
```
How should AI evaluate code quality?

[a] Extract all patterns (comprehensive)
[b] Extract only good patterns (quality-focused) [RECOMMENDED]
[c] Extract specific patterns I'll specify

Purpose: Guides AI's quality filtering during analysis
```

### 5. Naming Conventions
```
Are naming conventions consistent in this codebase?

[a] Yes, very consistent
[b] Mostly consistent
[c] Inconsistent (AI should infer best practices)

Purpose: Helps AI understand if naming can be used as pattern signal
```

### 6. Known Patterns
```
Do you know which architecture pattern is used? (optional)

[a] Yes: [specify pattern]
[b] No, let AI discover it [RECOMMENDED]

Purpose: Provides hint to AI, but not required
```

### 7. Template Name
```
Name for the generated template:

[Default: {language}-{pattern}-template]
Example: dotnet-maui-mvvm-template

Purpose: Generates template identifier
```

### 8. Exclusions
```
Any files/folders to exclude from analysis?

[Default: node_modules, .git, dist, build, bin, obj]

Additional exclusions: __________

Purpose: Avoids analyzing irrelevant files
```

### 9. Documentation Input
```
Do you have documentation to guide template creation?

Examples:
- Architecture Decision Records (ADRs)
- Coding standards documents
- API specifications
- Requirements documents
- Design documents

Options:
[a] Provide file paths
[b] Paste text directly
[c] Provide URLs
[d] None

Purpose: Gives AI context about WHY patterns exist, not just WHAT patterns exist
```

### 10. Documentation Usage (if provided)
```
How should we use this documentation?

[a] Follow patterns/standards strictly
[b] Use as general guidance
[c] Extract naming conventions only
[d] Understand architecture reasoning

Purpose: Determines how documentation influences template generation
```

## Implementation

```python
# src/commands/template_create/qa_session.py

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import inquirer

@dataclass
class TemplateCreateAnswers:
    """Answers from Q&A session"""
    purpose: str
    codebase_path: Path
    scope: List[str]
    quality_focus: str
    naming_consistency: str
    known_pattern: Optional[str]
    template_name: str
    exclusions: List[str]
    # Documentation input (Priority 1)
    documentation_paths: Optional[List[Path]] = None
    documentation_text: Optional[str] = None
    documentation_urls: Optional[List[str]] = None
    documentation_usage: Optional[str] = None

class TemplateCreateQASession:
    """Interactive Q&A session for /template-create"""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path.cwd()
        self.answers: Optional[TemplateCreateAnswers] = None

    def run(self) -> TemplateCreateAnswers:
        """
        Run interactive Q&A session

        Returns:
            TemplateCreateAnswers with user responses
        """
        print("\n" + "="*60)
        print("  /template-create - Interactive Q&A Session")
        print("="*60 + "\n")

        print("This Q&A will guide the AI analysis of your codebase.")
        print("Press Ctrl+C at any time to save and exit.\n")

        # Question 1: Purpose
        purpose = inquirer.list_input(
            message="What is the primary purpose of this template?",
            choices=[
                ("Create new projects from this architecture", "new_projects"),
                ("Share project structure with team", "share_structure"),
                ("Document existing patterns", "document_patterns"),
                ("Create variations of this project", "variations"),
            ]
        )

        # Question 2: Codebase path
        codebase_path = inquirer.text(
            message="Path to existing codebase",
            default=str(self.project_root)
        )
        codebase_path = Path(codebase_path)

        # Validate path
        if not codebase_path.exists():
            print(f"❌ Path does not exist: {codebase_path}")
            return self.run()  # Retry

        # Question 3: Scope
        scope = inquirer.checkbox(
            message="What should be included in the template?",
            choices=[
                ("Project structure (folders, files)", "structure", True),
                ("Code patterns (classes, functions)", "patterns", True),
                ("Configuration files", "config", False),
                ("Build scripts", "build", False),
                ("Documentation", "docs", False),
                ("Tests", "tests", False),
            ]
        )

        # Question 4: Quality focus
        quality_focus = inquirer.list_input(
            message="How should AI evaluate code quality?",
            choices=[
                ("Extract all patterns (comprehensive)", "all"),
                ("Extract only good patterns (quality-focused) [RECOMMENDED]", "good"),
                ("Extract specific patterns I'll specify", "specific"),
            ],
            default="good"
        )

        # Question 5: Naming consistency
        naming_consistency = inquirer.list_input(
            message="Are naming conventions consistent?",
            choices=[
                ("Yes, very consistent", "high"),
                ("Mostly consistent", "medium"),
                ("Inconsistent (AI should infer best practices)", "low"),
            ]
        )

        # Question 6: Known pattern (optional)
        has_known_pattern = inquirer.confirm(
            message="Do you know which architecture pattern is used?",
            default=False
        )

        known_pattern = None
        if has_known_pattern:
            known_pattern = inquirer.text(
                message="Architecture pattern (e.g., MVVM, Clean Architecture)",
            )

        # Question 7: Template name
        template_name = inquirer.text(
            message="Name for the generated template",
            default="my-template"
        )

        # Question 8: Exclusions
        default_exclusions = ["node_modules", ".git", "dist", "build", "bin", "obj", "venv", "__pycache__"]

        additional_exclusions = inquirer.text(
            message=f"Additional folders to exclude (comma-separated)\n  Default exclusions: {', '.join(default_exclusions)}\n  Additional",
            default=""
        )

        exclusions = default_exclusions
        if additional_exclusions:
            exclusions.extend([e.strip() for e in additional_exclusions.split(",")])

        # Question 9: Documentation input
        documentation_choice = inquirer.list_input(
            message="Do you have documentation to guide template creation?",
            choices=[
                ("Provide file paths", "paths"),
                ("Paste text directly", "text"),
                ("Provide URLs", "urls"),
                ("None", "none"),
            ],
            default="none"
        )

        documentation_paths = None
        documentation_text = None
        documentation_urls = None
        documentation_usage = None

        if documentation_choice == "paths":
            paths_input = inquirer.text(
                message="File paths (comma-separated)",
            )
            documentation_paths = [Path(p.strip()) for p in paths_input.split(",") if p.strip()]

        elif documentation_choice == "text":
            print("\nPaste documentation text (Ctrl+D when finished):")
            import sys
            documentation_text = sys.stdin.read()

        elif documentation_choice == "urls":
            urls_input = inquirer.text(
                message="URLs (comma-separated)",
            )
            documentation_urls = [u.strip() for u in urls_input.split(",") if u.strip()]

        # Question 10: Documentation usage (if provided)
        if documentation_choice != "none":
            documentation_usage = inquirer.list_input(
                message="How should we use this documentation?",
                choices=[
                    ("Follow patterns/standards strictly", "strict"),
                    ("Use as general guidance", "guidance"),
                    ("Extract naming conventions only", "naming"),
                    ("Understand architecture reasoning", "reasoning"),
                ],
                default="guidance"
            )

        # Summary
        self.answers = TemplateCreateAnswers(
            purpose=purpose,
            codebase_path=codebase_path,
            scope=scope,
            quality_focus=quality_focus,
            naming_consistency=naming_consistency,
            known_pattern=known_pattern,
            template_name=template_name,
            exclusions=exclusions,
            documentation_paths=documentation_paths,
            documentation_text=documentation_text,
            documentation_urls=documentation_urls,
            documentation_usage=documentation_usage
        )

        # Show summary
        self._show_summary()

        # Confirm
        proceed = inquirer.confirm(
            message="Proceed with AI analysis using these settings?",
            default=True
        )

        if not proceed:
            print("\nQ&A session cancelled. Run /template-create again to restart.\n")
            return None

        return self.answers

    def _show_summary(self):
        """Display summary of answers"""
        print("\n" + "="*60)
        print("  Q&A Summary")
        print("="*60 + "\n")

        print(f"Purpose: {self.answers.purpose}")
        print(f"Codebase: {self.answers.codebase_path}")
        print(f"Scope: {', '.join(self.answers.scope)}")
        print(f"Quality Focus: {self.answers.quality_focus}")
        print(f"Naming Consistency: {self.answers.naming_consistency}")

        if self.answers.known_pattern:
            print(f"Known Pattern: {self.answers.known_pattern}")

        print(f"Template Name: {self.answers.template_name}")
        print(f"Exclusions: {', '.join(self.answers.exclusions)}")

        # Documentation
        if self.answers.documentation_paths:
            print(f"Documentation (Files): {len(self.answers.documentation_paths)} file(s)")
        elif self.answers.documentation_text:
            print(f"Documentation (Text): {len(self.answers.documentation_text)} characters")
        elif self.answers.documentation_urls:
            print(f"Documentation (URLs): {len(self.answers.documentation_urls)} URL(s)")

        if self.answers.documentation_usage:
            print(f"Documentation Usage: {self.answers.documentation_usage}")

        print()

    def save_session(self, session_file: Path = None):
        """Save Q&A session for resuming later"""
        if session_file is None:
            session_file = Path(".template-create-session.json")

        import json

        data = {
            "purpose": self.answers.purpose,
            "codebase_path": str(self.answers.codebase_path),
            "scope": self.answers.scope,
            "quality_focus": self.answers.quality_focus,
            "naming_consistency": self.answers.naming_consistency,
            "known_pattern": self.answers.known_pattern,
            "template_name": self.answers.template_name,
            "exclusions": self.answers.exclusions,
            "documentation_paths": [str(p) for p in self.answers.documentation_paths] if self.answers.documentation_paths else None,
            "documentation_text": self.answers.documentation_text,
            "documentation_urls": self.answers.documentation_urls,
            "documentation_usage": self.answers.documentation_usage,
        }

        session_file.write_text(json.dumps(data, indent=2))
        print(f"✓ Session saved to {session_file}")

    @staticmethod
    def load_session(session_file: Path = None) -> Optional[TemplateCreateAnswers]:
        """Load saved Q&A session"""
        if session_file is None:
            session_file = Path(".template-create-session.json")

        if not session_file.exists():
            return None

        import json
        data = json.loads(session_file.read_text())

        return TemplateCreateAnswers(
            purpose=data["purpose"],
            codebase_path=Path(data["codebase_path"]),
            scope=data["scope"],
            quality_focus=data["quality_focus"],
            naming_consistency=data["naming_consistency"],
            known_pattern=data.get("known_pattern"),
            template_name=data["template_name"],
            exclusions=data["exclusions"],
            documentation_paths=[Path(p) for p in data["documentation_paths"]] if data.get("documentation_paths") else None,
            documentation_text=data.get("documentation_text"),
            documentation_urls=data.get("documentation_urls"),
            documentation_usage=data.get("documentation_usage"),
        )
```

## Testing Strategy

```python
# tests/test_template_create_qa.py

def test_qa_session_flow():
    """Test complete Q&A flow"""
    # Mock user inputs
    answers = mock_qa_session(
        purpose="new_projects",
        codebase_path="/test/project",
        scope=["structure", "patterns"],
        quality_focus="good",
        naming_consistency="high",
        template_name="test-template"
    )

    assert answers.purpose == "new_projects"
    assert answers.quality_focus == "good"
    assert "structure" in answers.scope

def test_session_persistence():
    """Test save/load session"""
    session = TemplateCreateQASession()
    # ... run session
    session.save_session(Path("/tmp/test-session.json"))

    loaded = TemplateCreateQASession.load_session(Path("/tmp/test-session.json"))
    assert loaded.purpose == session.answers.purpose
```

## Integration with TASK-002

Q&A answers (including documentation) are passed to AI analysis:

```python
# /template-create command flow
def template_create():
    # Step 1: Q&A
    qa = TemplateCreateQASession()
    answers = qa.run()

    if not answers:
        return  # User cancelled

    # Step 2: AI Analysis (TASK-002)
    from ai_analyzer import AICodebaseAnalyzer

    # Prepare documentation for AI context
    documentation = []
    if answers.documentation_paths:
        for path in answers.documentation_paths:
            documentation.append(path.read_text())
    if answers.documentation_text:
        documentation.append(answers.documentation_text)
    # Note: URLs would be fetched if needed

    analyzer = AICodebaseAnalyzer(
        qa_context=answers,
        documentation=documentation if documentation else None,
        documentation_usage=answers.documentation_usage
    )
    analysis = analyzer.analyze(answers.codebase_path)

    # ... continue with template generation
```

## Definition of Done

- [ ] Interactive Q&A flow implemented with all 10 questions (including documentation input)
- [ ] Session save/load functionality working
- [ ] Input validation for all questions
- [ ] Summary display before proceeding
- [ ] Option to skip Q&A (advanced users)
- [ ] Unit tests for Q&A flow passing (>85% coverage)
- [ ] Integration with TASK-002 (passes context to AI analyzer)
- [ ] User-friendly error messages and help text

**Estimated Time**: 6 hours | **Complexity**: 4/10 | **Priority**: HIGH

## Benefits

- ✅ Improves AI analysis accuracy with user context
- ✅ Sets proper expectations for template scope
- ✅ Familiar UX (same pattern as /gather-requirements)
- ✅ Reduces AI token usage (focused analysis)
- ✅ Better user experience (guided vs raw command)

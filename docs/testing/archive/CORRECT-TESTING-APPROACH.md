# CORRECT Testing Approach for EPIC-001

## What You're Actually Testing

You want to test the **EPIC-001 template creation functionality**, which analyzes existing codebases and creates templates from them. This is implemented in the `/template-create` command.

## The Right Command

```bash
# CORRECT: Use /template-create to analyze repos and create templates
/template-create

# WRONG: guardkit init (this just applies existing templates)
guardkit init
```

## How /template-create Works

The `/template-create` command will:

1. **Q&A Session** - Ask you questions about the codebase
2. **AI Analysis** - Analyze the code using the `architectural-reviewer` agent
3. **Generate Template Components**:
   - `manifest.json` - Template metadata
   - `settings.json` - Naming conventions and settings
   - `CLAUDE.md` - Project documentation
   - Template files (`.template` files with placeholders)
   - Custom agents (if needed)

## Testing Workflow

For each test repository:

### Step 1: Navigate to Repository

```bash
cd test-repos/CleanArchitecture-ardalis
```

### Step 2: Run /template-create

**Interactive Mode** (default):
```bash
/template-create
```

Then answer the Q&A questions:
- Codebase location: Current directory
- Template name: (it will suggest one)
- Language: (auto-detected)
- Architecture: (auto-detected)
- etc.

**Skip Q&A Mode** (faster for testing):
```bash
/template-create --skip-qa
```

**Dry Run Mode** (analyze without saving):
```bash
/template-create --dry-run
```

### Step 3: Observe Output

The command will show:
```
🔍 Analyzing codebase...
  ✓ Collected 10 file samples
  ✓ Built directory tree
  ✓ AI analysis complete (confidence: 87%)

Language: C#
Framework: ASP.NET Core, Entity Framework
Architecture: Clean Architecture
Patterns: CQRS, Repository, Mediator

📝 Generating manifest...
  ✓ Template: dotnet-clean-architecture

⚙️  Generating settings...
  ✓ 5 naming conventions

📚 Generating CLAUDE.md...
  ✓ Architecture overview

🎨 Generating templates...
  ✓ 15 template files generated

✅ Template package created!
Output: ./templates/dotnet-clean-architecture/
```

### Step 4: Evaluate Results

Check if the analysis was accurate:

**Stack Detection**:
- ✓ Correct language detected?
- ✓ Correct frameworks detected?
- ✓ Correct architecture pattern detected?

**Template Quality**:
- ✓ Were good example files selected?
- ✓ Are templates properly created with placeholders?
- ✓ Is CLAUDE.md comprehensive?

**Confidence Score**:
- What was the AI confidence score?
- Does it match the quality of detection?

## Quick Testing Script

Create a script to test multiple repos quickly:

```bash
#!/bin/bash
# test-template-create.sh

REPOS=(
    "CleanArchitecture-ardalis"
    "go-clean-architecture"
    "bulletproof-react"
    "full-stack-fastapi-template"
)

mkdir -p ../results

for repo in "${REPOS[@]}"; do
    echo "========================================="
    echo "Testing: $repo"
    echo "========================================="

    cd "test-repos/$repo"

    # Run template-create with skip-qa and dry-run
    /template-create --skip-qa --dry-run 2>&1 | tee "../../results/${repo}-analysis.txt"

    cd ../..

    echo ""
    echo "✓ Completed: $repo"
    echo ""
done

echo "All tests complete! Check results/ directory"
```

## What to Record

For each repository test:

```markdown
### Repository: CleanArchitecture-ardalis
**Date**: 2025-01-07
**Command**: `/template-create --skip-qa --dry-run`

#### Detection Results
**Language**: C# ✓ (Correct)
**Framework**: ASP.NET Core 9 ✓ (Correct)
**Architecture**: Clean Architecture ✓ (Correct)
**Confidence**: 92% ✓ (High)

#### Additional Detection
**Patterns**: CQRS, Repository, REPR
**Testing**: xUnit
**Database**: Entity Framework Core
**Layers**: Domain, Application, Infrastructure, Web

#### Template Generation
**Templates Created**: 18 files
**Quality**: High - Selected appropriate example files
**Placeholders**: Well-identified (ProjectName, EntityName, etc.)

#### Overall Score: 9/10

**Notes**:
- Excellent detection accuracy
- Correctly identified REPR pattern (specific to this template)
- CLAUDE.md was comprehensive
- Only minor issue: Suggested more templates than needed
```

## Expected Behavior by Repository

### .NET Repos (ardalis, jasontaylor)
**Should Detect**:
- Language: C#
- Framework: ASP.NET Core
- Architecture: Clean Architecture
- Patterns: CQRS, MediatR, Repository
- Testing: xUnit or NUnit

### Go Repos
**Should Detect**:
- Language: Go
- Architecture: Clean Architecture or Layered
- Patterns: Repository, Dependency Injection
- Testing: go test

### React Repos
**Should Detect**:
- Language: TypeScript/JavaScript
- Framework: React
- Build: Vite or Create React App
- Testing: Vitest or Jest
- Patterns: Feature-based organization

### Python Repos
**Should Detect**:
- Language: Python
- Framework: FastAPI
- Database: PostgreSQL, SQLModel
- Testing: pytest
- Patterns: Clean Architecture

## Common Issues

### Issue: Command not found
```bash
# Solution: Commands are slash commands, not bash commands
# Use in Claude Code interface, not terminal
```

### Issue: No AI analysis
```bash
# Check if architectural-reviewer agent is available
ls ~/.agentecflow/agents/ | grep architectural
```

### Issue: Low confidence scores
```bash
# Could indicate:
# - Repository is too complex
# - Mixed languages/frameworks
# - Unclear architecture
# - This is actually useful feedback!
```

## Success Criteria

For the EPIC-001 feature to be considered successful:

1. **Stack Detection**: ≥95% accuracy on primary language/framework
2. **Architecture Detection**: ≥80% accuracy on architectural pattern
3. **Confidence Scores**: Average ≥75% across all repos
4. **Template Quality**: Generated templates are usable and well-structured
5. **Performance**: Analysis completes in <2 minutes for medium repos
6. **False Positives**: <5% of detected patterns are incorrect

## Next Steps

1. Update [initialization-test-plan.md](initialization-test-plan.md) to use `/template-create`
2. Update [quick-start-guide.md](quick-start-guide.md) with correct commands
3. Create automated testing script
4. Run tests on all 11 repositories
5. Document results
6. Create issues for any bugs found

---

**Key Takeaway**: You're testing `/template-create` (EPIC-001), not `guardkit init` (standard initialization).

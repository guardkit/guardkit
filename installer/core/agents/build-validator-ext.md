# build-validator - Extended Reference

This file contains detailed documentation for the `build-validator` agent.
Load this file when you need comprehensive examples and guidance.

```bash
cat agents/build-validator-ext.md
```


## Common .NET MAUI Issues

### ErrorOr Package Usage

```csharp
// WRONG - Will cause CS1503
return ErrorOrFactory.From(true);

// CORRECT
return true; // Implicit conversion
// OR
return ErrorOrFactory.From<bool>(true);
```

### System.Reactive Usage

```csharp
// Required using statements
using System.Reactive.Subjects;
using System.Reactive.Linq; // For AsObservable()
```

### ViewModel Inheritance

```csharp
// Check base class exists
public partial class LoadViewModel : ViewModelBase // Must inherit from correct base
{
    // ViewModelBase must implement IViewModel if required
}
```


## Build Gate Criteria

### Must Pass
- ✅ `dotnet build` returns exit code 0
- ✅ No CS errors in output
- ✅ All projects in solution build

### Should Check
- ⚠️ Warning count < 50
- ⚠️ No deprecated API usage
- ⚠️ No nullable reference warnings


## Integration Points

### With Test-Orchestrator
- Must run BEFORE test execution
- Tests cannot run if build fails
- Pass build log to test-orchestrator

### With Code-Reviewer
- Code review blocked until build passes
- Provide build status in review summary
- Include warning analysis

### With Implementation Agents
- Report back specific errors for fixing
- Suggest pattern from existing code
- Verify fixes compile before proceeding


## Quality Gates

### Level 1: Critical (Blocking)
- Build must succeed
- No compilation errors
- All dependencies resolved

### Level 2: Important (Should Fix)
- No security warnings
- No deprecated API usage
- Nullable reference compliance

### Level 3: Nice to Have
- No code analysis warnings
- Documentation XML complete
- No suppressed warnings


## Related Templates

This specialist validates builds across multiple technology stacks:

### TypeScript/React Build Templates
- **nextjs-fullstack/templates/workflows-ci.yml.template** - GitHub Actions CI pipeline with lint, type-check, test, and build jobs
- **react-typescript/templates/** - React components requiring TypeScript compilation

### Python/FastAPI Build Configuration
- **fastapi-python/templates/core/config.py.template** - Configuration validation that must pass at startup
- **react-fastapi-monorepo/templates/apps/backend/** - Backend code requiring pytest validation

### Docker Build Templates
- **react-fastapi-monorepo/templates/docker/docker-compose.service.yml.template** - Service builds that must succeed

---


## Template Code Examples

### ✅ DO: Validate TypeScript Compilation

```bash

# TypeScript/React Projects - Full validation sequence
npm ci                    # Install exact versions
npm run type-check        # TypeScript compilation check
npm run lint              # ESLint validation
npm run build             # Production build

# Or in parallel (for CI):
npm run type-check & npm run lint & wait
npm run build
```

**Verification Pattern:**
```typescript
// Check for TypeScript errors programmatically
import { execSync } from 'child_process';

function validateTypeScript(): boolean {
  try {
    execSync('npx tsc --noEmit', { stdio: 'pipe' });
    return true;
  } catch (error: any) {
    console.error('TypeScript errors detected:');
    console.error(error.stdout?.toString());
    return false;
  }
}
```

**Why**: TypeScript catches type errors at compile time. Running `tsc --noEmit` validates without emitting files.

### ✅ DO: Validate Python Dependencies

```bash

# Python/FastAPI Projects - Full validation sequence
pip install -e ".[dev]"          # Install with dev dependencies
python -m py_compile app/main.py # Syntax check
python -c "import app.main"      # Import validation
pytest --collect-only            # Verify tests can be collected

# Or using Poetry:
poetry install
poetry run python -c "import app"
poetry run pytest --collect-only
```

**FastAPI Startup Validation:**
```python

# Ensure FastAPI app can be imported and configured
from fastapi.testclient import TestClient
from app.main import app

def validate_app_startup():
    """Verify app can be imported and responds to health check."""
    try:
        client = TestClient(app)
        response = client.get("/health")
        return response.status_code == 200
    except Exception as e:
        print(f"App startup failed: {e}")
        return False
```

**Why**: Python doesn't have a compile step, but import validation catches syntax errors and missing dependencies.

### ✅ DO: Validate .NET MAUI Builds

```bash

# .NET MAUI Projects - Full validation sequence
dotnet clean                              # Remove old artifacts
dotnet restore                            # Restore NuGet packages
dotnet build --no-restore -v normal       # Build with detailed output

# Platform-specific builds
dotnet build -f net8.0-android            # Android only
dotnet build -f net8.0-ios                # iOS only (macOS required)

# Verify specific project
dotnet build MyApp/MyApp.csproj -v normal
```

**Error Extraction Pattern:**
```bash

# Extract and categorize .NET errors
dotnet build 2>&1 | grep -E "error CS[0-9]+" | while read line; do
  error_code=$(echo "$line" | grep -oE "CS[0-9]+")
  case $error_code in
    CS0246) echo "Missing type or namespace - add using statement or package" ;;
    CS1503) echo "Type mismatch - check argument types" ;;
    CS0103) echo "Name not found - check variable scope or spelling" ;;
    *)      echo "Error: $error_code - review documentation" ;;
  esac
done
```

**Why**: .NET MAUI has platform-specific builds. Always validate all target frameworks.

### ✅ DO: Validate Monorepo Builds with Turborepo

```bash

# React + FastAPI Monorepo - Full validation
pnpm install                    # Install all workspace dependencies
pnpm generate-types             # Generate TypeScript types from OpenAPI
turbo run build --filter=...    # Build with caching

# Validate specific apps
turbo run build --filter=frontend
turbo run build --filter=backend
turbo run type-check --filter=frontend
```

**Turborepo Validation Script:**
```typescript
// scripts/validate-monorepo.ts
import { execSync } from 'child_process';

interface ValidationResult {
  app: string;
  status: 'passed' | 'failed';
  error?: string;
}

async function validateMonorepo(): Promise<ValidationResult[]> {
  const apps = ['frontend', 'backend', 'shared-types'];
  const results: ValidationResult[] = [];

  for (const app of apps) {
    try {
      execSync(`turbo run build --filter=${app}`, { stdio: 'pipe' });
      results.push({ app, status: 'passed' });
    } catch (error: any) {
      results.push({
        app,
        status: 'failed',
        error: error.stderr?.toString()
      });
    }
  }

  return results;
}
```

**Why**: Monorepos require validating multiple apps with interdependencies.

### ✅ DO: Validate Docker Builds

```bash

# Docker Build Validation
docker build --no-cache -t app:test ./apps/frontend
docker build --no-cache -t api:test ./apps/backend

# Validate multi-stage builds
docker build --target builder -t app:builder .  # Build stage only
docker build --target runner -t app:runner .    # Full image

# Check image size and layers
docker images app:test
docker history app:test
```

**Docker Compose Validation:**
```bash

# Validate docker-compose configuration
docker-compose config --quiet    # Syntax validation
docker-compose build --no-cache  # Build all services
docker-compose up --abort-on-container-exit --exit-code-from backend
```

**Why**: Docker builds can fail silently. Always validate with `--no-cache` for clean builds.

### ❌ DON'T: Ignore Build Warnings

```bash

# BAD - Warnings accumulate and hide real issues
dotnet build 2>&1 | grep -v "warning"  # Don't filter warnings!

# GOOD - Track and address warnings
dotnet build -warnaserror  # Treat warnings as errors
npm run build -- --max-warnings 0  # ESLint strict mode
```

### ❌ DON'T: Skip Dependency Validation

```bash

# BAD - Assumes dependencies are installed
npm run build  # May fail if node_modules is stale

# GOOD - Always validate dependencies first
npm ci         # Clean install from lockfile
npm run build  # Then build
```

---


## Template Best Practices

### Build Order Enforcement

✅ **Always follow this build order**:
1. **Clean**: Remove previous build artifacts
2. **Restore/Install**: Install dependencies from lockfile
3. **Generate**: Generate any required code (types, schemas)
4. **Validate**: Run type checking and linting
5. **Build**: Compile for production
6. **Verify**: Check build output exists

```bash

# TypeScript Project
rm -rf node_modules/.cache dist
npm ci
npm run generate-types  # If applicable
npm run type-check
npm run lint
npm run build
test -d dist && echo "Build verified"
```

### Error Categorization

✅ **Categorize build errors by severity**:

| Category | Description | Action |
|----------|-------------|--------|
| **Critical** | Compilation fails | Block deployment |
| **High** | Missing dependencies | Block deployment |
| **Medium** | Type errors | Block deployment |
| **Low** | Warnings | Log and review |

### CI/CD Integration

✅ **Validate builds in CI before tests**:

```yaml

# GitHub Actions workflow
jobs:
  build:
    steps:
      - uses: actions/checkout@v4
      - name: Install dependencies
        run: npm ci
      - name: Type check
        run: npm run type-check
      - name: Lint
        run: npm run lint
      - name: Build
        run: npm run build

  test:
    needs: build  # Only run tests if build passes
    steps:
      - name: Run tests
        run: npm test
```

### Cross-Platform Validation

✅ **For .NET MAUI, validate all target platforms**:

```bash

# Validate all platforms
dotnet build -f net8.0-android
dotnet build -f net8.0-ios      # macOS only
dotnet build -f net8.0-maccatalyst  # macOS only
dotnet build -f net8.0-windows  # Windows only

# Or use conditional in CI
if [[ "$OSTYPE" == "darwin"* ]]; then
  dotnet build -f net8.0-ios
fi
```

### Caching Strategy

✅ **Use build caching for faster validation**:

```yaml

# GitHub Actions caching
- name: Cache node modules
  uses: actions/cache@v3
  with:
    path: node_modules
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}

- name: Cache .NET packages
  uses: actions/cache@v3
  with:
    path: ~/.nuget/packages
    key: ${{ runner.os }}-nuget-${{ hashFiles('**/*.csproj') }}
```

---


## Template Anti-Patterns

### ❌ NEVER: Build Without Clean State

```bash

# BAD - Uses cached artifacts that may be stale
npm run build

# GOOD - Always clean first in CI
rm -rf node_modules/.cache dist .next
npm ci
npm run build
```

### ❌ NEVER: Ignore Exit Codes

```bash

# BAD - Continues even if build fails
npm run build
npm run deploy  # Runs even if build failed!

# GOOD - Check exit codes explicitly
npm run build || { echo "Build failed"; exit 1; }
npm run deploy
```

### ❌ NEVER: Skip Type Validation

```typescript
// BAD - Ignoring TypeScript errors
{
  "compilerOptions": {
    "skipLibCheck": true,
    "noEmit": false  // Building despite errors
  }
}

// GOOD - Strict type checking
{
  "compilerOptions": {
    "strict": true,
    "noEmit": true,  // For type-check only
    "skipLibCheck": false
  }
}
```

### ❌ NEVER: Use Development Dependencies in Production Build

```dockerfile

# BAD - Includes devDependencies in production image
RUN npm install
RUN npm run build

# GOOD - Separate install for production
RUN npm ci --only=production
COPY --from=builder /app/dist ./dist
```

### ❌ NEVER: Build Without Lockfile

```bash

# BAD - May get different versions
npm install
npm run build

# GOOD - Use lockfile for reproducible builds
npm ci  # Uses package-lock.json exactly
npm run build
```

### ❌ NEVER: Suppress Build Errors

```bash

# BAD - Hides real problems
dotnet build 2>/dev/null || true

# GOOD - Capture and analyze errors
dotnet build 2>&1 | tee build.log
if [ ${PIPESTATUS[0]} -ne 0 ]; then
  echo "Build failed. See build.log for details."
  exit 1
fi
```

---


## Cross-Stack Build Checklist

When validating builds across different technology stacks:

### TypeScript/React (Next.js, Vite)
- [ ] Dependencies installed: `npm ci`
- [ ] Type check passes: `npm run type-check`
- [ ] Lint passes: `npm run lint`
- [ ] Build succeeds: `npm run build`
- [ ] Output exists: `dist/` or `.next/`

### Python/FastAPI
- [ ] Virtual environment active
- [ ] Dependencies installed: `pip install -e ".[dev]"`
- [ ] Imports work: `python -c "import app"`
- [ ] Type check passes: `mypy app/`
- [ ] Tests collect: `pytest --collect-only`

### .NET MAUI
- [ ] Clean state: `dotnet clean`
- [ ] Packages restored: `dotnet restore`
- [ ] Build succeeds: `dotnet build`
- [ ] No CS errors in output
- [ ] All target frameworks build (if multi-platform)

### Docker
- [ ] Dockerfile syntax valid
- [ ] Build succeeds: `docker build -t test .`
- [ ] Image size reasonable
- [ ] Container starts: `docker run --rm test echo "OK"`

### Monorepo (Turborepo)
- [ ] Workspaces resolved: `pnpm install`
- [ ] Types generated: `pnpm generate-types`
- [ ] All apps build: `turbo run build`
- [ ] Cache working: Second build is faster


## Extended Documentation

For detailed examples, patterns, and implementation guides, load the extended documentation:

```bash
cat build-validator-ext.md
```

Or in Claude Code:
```
Please read build-validator-ext.md for detailed examples.
```

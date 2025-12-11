---
id: TASK-CRS-004
title: Add Path Pattern Inference from Analysis
status: backlog
task_type: implementation
created: 2025-12-11T12:15:00Z
updated: 2025-12-11T12:15:00Z
priority: medium
tags: [path-inference, rules-structure, ai-analysis]
complexity: 5
parent_feature: claude-rules-structure
wave: 3
implementation_mode: task-work
conductor_workspace: claude-rules-wave3-2
estimated_hours: 3-4
dependencies:
  - TASK-CRS-002
---

# Task: Add Path Pattern Inference from Analysis

## Description

Enhance `RulesStructureGenerator` to intelligently infer path patterns from codebase analysis results, rather than relying solely on agent name matching.

## Problem

Current implementation uses simple name-based mapping:
```python
if 'repository' in agent_name.lower():
    return '**/Repositories/**'
```

This misses:
- Custom folder names (e.g., `data/` instead of `repositories/`)
- Project-specific patterns
- Multi-language considerations

## Solution

Use `CodebaseAnalysis` data to infer patterns:
- Layer paths from analysis
- File extension patterns from technology detection
- Directory structure from project tree

## Implementation

### Step 1: Enhance PathInferrer Class

```python
class PathPatternInferrer:
    """Infer path patterns from codebase analysis."""

    def __init__(self, analysis: CodebaseAnalysis):
        self.analysis = analysis
        self._layer_paths = self._build_layer_paths()
        self._extension_patterns = self._build_extension_patterns()

    def _build_layer_paths(self) -> Dict[str, List[str]]:
        """Build layer-to-paths mapping from analysis."""
        layer_paths = {}

        for layer in self.analysis.architecture.layers:
            paths = []
            for file in layer.typical_files:
                # Extract directory pattern from file path
                dir_path = Path(file).parent
                if dir_path != Path('.'):
                    paths.append(f"**/{dir_path}/**")
            layer_paths[layer.name.lower()] = paths

        return layer_paths

    def _build_extension_patterns(self) -> Dict[str, str]:
        """Build extension patterns from technology detection."""
        tech = self.analysis.technology
        patterns = {}

        if tech.primary_language == "Python":
            patterns['source'] = '**/*.py'
            patterns['test'] = '**/test_*.py, **/tests/**/*.py'
        elif tech.primary_language in ["TypeScript", "JavaScript"]:
            patterns['source'] = '**/*.{ts,tsx,js,jsx}'
            patterns['test'] = '**/*.test.{ts,tsx}, **/tests/**'
        elif tech.primary_language == "C#":
            patterns['source'] = '**/*.cs'
            patterns['test'] = '**/Tests/**/*.cs, **/*Tests.cs'
        # ... more languages

        return patterns

    def infer_for_agent(self, agent_name: str, agent_technologies: List[str]) -> str:
        """Infer path patterns for an agent."""
        patterns = []

        # 1. Try layer-based matching
        for layer_name, layer_paths in self._layer_paths.items():
            if self._matches_layer(agent_name, layer_name):
                patterns.extend(layer_paths)

        # 2. Try technology-based matching
        for tech in agent_technologies:
            tech_pattern = self._get_technology_pattern(tech)
            if tech_pattern:
                patterns.append(tech_pattern)

        # 3. Fallback to name-based heuristics
        if not patterns:
            patterns = self._fallback_inference(agent_name)

        # Deduplicate and join
        unique_patterns = list(dict.fromkeys(patterns))
        return ', '.join(unique_patterns[:5])  # Limit to 5 patterns

    def _matches_layer(self, agent_name: str, layer_name: str) -> bool:
        """Check if agent name suggests it belongs to a layer."""
        agent_lower = agent_name.lower()
        layer_keywords = {
            'infrastructure': ['repository', 'database', 'persistence', 'storage'],
            'presentation': ['viewmodel', 'view', 'ui', 'component', 'page'],
            'application': ['service', 'engine', 'handler', 'orchestrator'],
            'domain': ['entity', 'model', 'aggregate', 'value-object'],
            'api': ['controller', 'endpoint', 'route', 'api'],
        }

        keywords = layer_keywords.get(layer_name, [])
        return any(kw in agent_lower for kw in keywords)

    def _get_technology_pattern(self, tech: str) -> Optional[str]:
        """Get path pattern for a specific technology."""
        tech_patterns = {
            'FastAPI': '**/router*.py, **/api/**',
            'SQLAlchemy': '**/models/*.py, **/crud/*.py',
            'React': '**/components/**/*.tsx',
            'TanStack Query': '**/*query*, **/*api*',
            'Prisma': '**/prisma/**',
            'NextAuth': '**/auth/**',
        }
        return tech_patterns.get(tech)

    def _fallback_inference(self, agent_name: str) -> List[str]:
        """Fallback to name-based pattern inference."""
        # Original simple mapping as fallback
        mappings = {
            'repository': ['**/repositories/**', '**/Repositories/**'],
            'viewmodel': ['**/viewmodels/**', '**/ViewModels/**'],
            'service': ['**/services/**', '**/Services/**'],
            'testing': ['**/tests/**', '**/*.test.*'],
            'api': ['**/api/**', '**/controllers/**'],
        }

        agent_lower = agent_name.lower()
        for key, patterns in mappings.items():
            if key in agent_lower:
                return patterns

        return []
```

### Step 2: Integrate with RulesStructureGenerator

```python
class RulesStructureGenerator:
    def __init__(self, analysis: CodebaseAnalysis, agents: List, output_path: Path):
        self.analysis = analysis
        self.agents = agents
        self.output_path = output_path
        self.path_inferrer = PathPatternInferrer(analysis)  # NEW

    def _generate_agent_rules(self, agent) -> str:
        """Generate rules file for an agent with inferred paths."""
        # Use inferrer instead of simple mapping
        paths = self.path_inferrer.infer_for_agent(
            agent.name,
            agent.technologies
        )

        frontmatter = ""
        if paths:
            frontmatter = f"""---
paths: {paths}
---

"""

        return f"""{frontmatter}# {agent.name}

## Purpose

{agent.description}

## Technologies

{', '.join(agent.technologies)}

## Boundaries

### ALWAYS
{self._format_boundaries(agent, 'always')}

### NEVER
{self._format_boundaries(agent, 'never')}

### ASK
{self._format_boundaries(agent, 'ask')}
"""
```

## Acceptance Criteria

- [ ] `PathPatternInferrer` class implemented
- [ ] Uses layer information from analysis
- [ ] Uses technology detection for patterns
- [ ] Falls back to name-based inference
- [ ] Integrated with `RulesStructureGenerator`
- [ ] Generated patterns are valid glob syntax
- [ ] Unit tests cover inference logic

## Testing

```python
def test_infers_from_layer_paths():
    """Test path inference from layer information."""
    analysis = create_mock_analysis(
        layers=[
            LayerInfo(name="Infrastructure", typical_files=["src/repositories/user_repo.py"])
        ]
    )
    inferrer = PathPatternInferrer(analysis)

    paths = inferrer.infer_for_agent("repository-specialist", ["SQLAlchemy"])
    assert "**/repositories/**" in paths

def test_infers_from_technology():
    """Test path inference from technology."""
    analysis = create_mock_analysis()
    inferrer = PathPatternInferrer(analysis)

    paths = inferrer.infer_for_agent("fastapi-specialist", ["FastAPI"])
    assert "**/router*.py" in paths or "**/api/**" in paths
```

## Notes

- This is Wave 3 (parallel with CLI flag)
- Use `/task-work` for full quality gates
- Enhances quality of generated rules structure

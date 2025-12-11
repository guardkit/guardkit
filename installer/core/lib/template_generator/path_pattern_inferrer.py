"""
Path Pattern Inferrer

Intelligently infers path patterns for agent rules based on codebase analysis.
Uses layer information, technology detection, and smart fallbacks to generate
accurate path filters for conditional rule loading.
"""

from pathlib import Path
from typing import Dict, List, Optional

from ..codebase_analyzer.models import CodebaseAnalysis


class PathPatternInferrer:
    """Infer path patterns from codebase analysis for agent rules."""

    def __init__(self, analysis: CodebaseAnalysis):
        """
        Initialize path pattern inferrer.

        Args:
            analysis: CodebaseAnalysis containing technology and architecture data
        """
        self.analysis = analysis
        self._layer_paths = self._build_layer_paths()
        self._extension_patterns = self._build_extension_patterns()

    def _build_layer_paths(self) -> Dict[str, List[str]]:
        """
        Build layer-to-paths mapping from analysis.

        Extracts directory patterns from typical_files in each layer.

        Returns:
            Dictionary mapping layer names (lowercase) to path patterns

        Example:
            {
                'infrastructure': ['**/repositories/**', '**/data/**'],
                'presentation': ['**/views/**', '**/components/**']
            }
        """
        layer_paths = {}

        for layer in self.analysis.architecture.layers:
            paths = []
            for file in layer.typical_files:
                # Extract directory pattern from file path
                dir_path = Path(file).parent
                if dir_path != Path('.'):
                    # Convert to glob pattern
                    pattern = f"**/{dir_path}/**"
                    paths.append(pattern)

            # Deduplicate paths for this layer
            unique_paths = list(dict.fromkeys(paths))
            layer_paths[layer.name.lower()] = unique_paths

        return layer_paths

    def _build_extension_patterns(self) -> Dict[str, str]:
        """
        Build extension patterns from technology detection.

        Returns:
            Dictionary mapping pattern types to glob patterns

        Example:
            {
                'source': '**/*.py',
                'test': '**/test_*.py, **/tests/**/*.py'
            }
        """
        tech = self.analysis.technology
        patterns = {}

        if tech.primary_language == "Python":
            patterns['source'] = '**/*.py'
            patterns['test'] = '**/test_*.py, **/tests/**/*.py'
        elif tech.primary_language in ["TypeScript", "JavaScript"]:
            patterns['source'] = '**/*.{ts,tsx,js,jsx}'
            patterns['test'] = '**/*.test.{ts,tsx,js,jsx}, **/tests/**'
        elif tech.primary_language == "C#":
            patterns['source'] = '**/*.cs'
            patterns['test'] = '**/Tests/**/*.cs, **/*Tests.cs'
        elif tech.primary_language == "Java":
            patterns['source'] = '**/*.java'
            patterns['test'] = '**/test/**/*.java, **/*Test.java'
        elif tech.primary_language == "Go":
            patterns['source'] = '**/*.go'
            patterns['test'] = '**/*_test.go'
        elif tech.primary_language == "Rust":
            patterns['source'] = '**/*.rs'
            patterns['test'] = '**/tests/**/*.rs'

        return patterns

    def infer_for_agent(
        self,
        agent_name: str,
        agent_technologies: List[str]
    ) -> str:
        """
        Infer path patterns for an agent.

        Uses multi-level inference:
        1. Layer-based matching from architecture analysis
        2. Technology-specific patterns from frameworks
        3. Fallback to name-based heuristics

        Args:
            agent_name: Name of the agent (e.g., "repository-specialist")
            agent_technologies: List of technologies the agent works with

        Returns:
            Comma-separated path patterns (limited to 5)

        Example:
            >>> inferrer.infer_for_agent("repository-specialist", ["SQLAlchemy"])
            "**/repositories/**, **/models/*.py, **/crud/*.py"
        """
        patterns = []

        # 1. Try layer-based matching
        for layer_name, layer_paths in self._layer_paths.items():
            if self._matches_layer(agent_name, layer_name):
                patterns.extend(layer_paths)

        # 2. Try technology-based matching
        for tech in agent_technologies:
            tech_pattern = self._get_technology_pattern(tech)
            if tech_pattern:
                # Split comma-separated patterns
                tech_patterns = [p.strip() for p in tech_pattern.split(',')]
                patterns.extend(tech_patterns)

        # 3. Fallback to name-based heuristics
        if not patterns:
            patterns = self._fallback_inference(agent_name)

        # Deduplicate and join
        unique_patterns = list(dict.fromkeys(patterns))

        # Limit to 5 patterns to keep frontmatter concise
        limited_patterns = unique_patterns[:5]

        return ', '.join(limited_patterns)

    def _matches_layer(self, agent_name: str, layer_name: str) -> bool:
        """
        Check if agent name suggests it belongs to a layer.

        Args:
            agent_name: Agent name (e.g., "repository-specialist")
            layer_name: Layer name from analysis (e.g., "infrastructure")

        Returns:
            True if agent likely belongs to this layer
        """
        agent_lower = agent_name.lower()

        # Map common layer names to agent keywords
        layer_keywords = {
            'infrastructure': ['repository', 'database', 'persistence', 'storage', 'data'],
            'presentation': ['viewmodel', 'view', 'ui', 'component', 'page', 'screen'],
            'application': ['service', 'engine', 'handler', 'orchestrator', 'workflow'],
            'domain': ['entity', 'model', 'aggregate', 'value-object', 'domain'],
            'api': ['controller', 'endpoint', 'route', 'api', 'router'],
            'web': ['component', 'page', 'layout', 'ui', 'frontend'],
            'data': ['repository', 'database', 'query', 'migration', 'schema'],
        }

        keywords = layer_keywords.get(layer_name, [])
        return any(kw in agent_lower for kw in keywords)

    def _get_technology_pattern(self, tech: str) -> Optional[str]:
        """
        Get path pattern for a specific technology.

        Args:
            tech: Technology name (e.g., "FastAPI", "React")

        Returns:
            Path pattern or None if no match
        """
        tech_patterns = {
            # Python frameworks
            'FastAPI': '**/router*.py, **/api/**',
            'Flask': '**/routes/**/*.py, **/api/**',
            'Django': '**/views.py, **/urls.py',
            'SQLAlchemy': '**/models/*.py, **/crud/*.py',
            'Alembic': '**/migrations/**',

            # JavaScript/TypeScript frameworks
            'React': '**/components/**/*.{tsx,jsx}',
            'Next.js': '**/app/**, **/pages/**',
            'Express': '**/routes/**, **/api/**',
            'TanStack Query': '**/*query*, **/*api*',
            'React Hook Form': '**/*form*',
            'Zod': '**/*schema*, **/*validation*',

            # Databases
            'Prisma': '**/prisma/**',
            'TypeORM': '**/entities/**',
            'Mongoose': '**/models/**',

            # Authentication
            'NextAuth': '**/auth/**',
            'Passport': '**/auth/**',

            # Testing
            'Jest': '**/*.test.*, **/*.spec.*',
            'Vitest': '**/*.test.*, **/*.spec.*',
            'Pytest': '**/test_*.py, **/tests/**',
            'Playwright': '**/e2e/**, **/*.spec.ts',

            # .NET
            'ASP.NET': '**/Controllers/**, **/Pages/**',
            'Entity Framework': '**/Data/**, **/Models/**',
        }

        return tech_patterns.get(tech)

    def _fallback_inference(self, agent_name: str) -> List[str]:
        """
        Fallback to name-based pattern inference.

        Used when layer and technology matching fail.

        Args:
            agent_name: Agent name

        Returns:
            List of inferred path patterns
        """
        # Name-based mappings (original simple approach)
        mappings = {
            'repository': ['**/repositories/**', '**/Repositories/**'],
            'viewmodel': ['**/viewmodels/**', '**/ViewModels/**'],
            'service': ['**/services/**', '**/Services/**'],
            'engine': ['**/engines/**', '**/Engines/**'],
            'testing': ['**/tests/**', '**/*.test.*'],
            'test': ['**/tests/**', '**/*.test.*', '**/*.spec.*'],
            'api': ['**/api/**', '**/controllers/**'],
            'database': ['**/models/**', '**/db/**', '**/data/**'],
            'query': ['**/*query*', '**/*api*'],
            'form': ['**/*form*', '**/*validation*'],
            'component': ['**/components/**', '**/ui/**'],
            'page': ['**/pages/**', '**/views/**'],
            'route': ['**/routes/**', '**/routing/**'],
            'auth': ['**/auth/**', '**/authentication/**'],
            'validation': ['**/*validation*', '**/*validator*'],
        }

        agent_lower = agent_name.lower()
        for key, patterns in mappings.items():
            if key in agent_lower:
                return patterns

        return []

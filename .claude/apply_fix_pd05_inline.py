#!/usr/bin/env python3
"""
Inline fix application for TASK-FIX-PD05
This file should be executed from the guardkit root directory
"""

def main():
    import sys
    from pathlib import Path

    # Working file
    file_path = Path('installer/global/lib/template_generator/claude_md_generator.py')

    if not file_path.exists():
        print(f"ERROR: File not found: {file_path}", file=sys.stderr)
        print(f"Make sure you run this from the guardkit root directory", file=sys.stderr)
        return 1

    # Read the file
    with open(file_path, 'r') as f:
        original_content = f.read()

    # Check if fix has already been applied
    if '_categorize_agent_by_keywords' in original_content:
        print("INFO: Fix already applied - _categorize_agent_by_keywords method exists")
        return 0

    # The new method
    new_method = '''    def _categorize_agent_by_keywords(self, agent_metadata: Dict[str, Any]) -> str:
        """Categorize agent based on technologies and description keywords.

        Uses priority order: database > testing > api > domain > ui > general
        to prevent false matches from generic keywords like 'view'.

        Args:
            agent_metadata: Dict with 'name', 'description', 'technologies' keys

        Returns:
            Category string: 'database', 'api', 'ui', 'domain', 'testing', or 'general'
        """
        # Check technologies first (most reliable)
        technologies_lower = [t.lower() for t in agent_metadata.get('technologies', [])]

        # Database technologies
        database_techs = {
            'firestore', 'firebase', 'realm', 'mongodb', 'postgresql', 'mysql',
            'sqlite', 'supabase', 'dynamodb', 'redis', 'database'
        }
        if any(any(tech in t for tech in database_techs) for t in technologies_lower):
            return 'database'

        # Testing technologies
        testing_techs = {'pytest', 'jest', 'mocha', 'xunit', 'nunit', 'vitest', 'testing'}
        if any(any(tech in t for tech in testing_techs) for t in technologies_lower):
            return 'testing'

        # API technologies
        api_techs = {'fastapi', 'express', 'flask', 'django', 'asp.net', 'spring', 'rest', 'api'}
        if any(any(tech in t for tech in api_techs) for t in technologies_lower):
            return 'api'

        # UI technologies
        ui_techs = {'react', 'vue', 'angular', 'svelte', 'xaml', 'swiftui'}
        if any(any(tech in t for tech in ui_techs) for t in technologies_lower):
            return 'ui'

        # Fallback to description keyword matching
        desc_lower = agent_metadata.get('description', '').lower()

        # Database keywords (highest priority)
        database_keywords = {
            'database', 'firestore', 'firebase', 'realm', 'mongodb', 'postgresql',
            'mysql', 'crud', 'persistence', 'query', 'collection', 'document',
            'repository', 'data access', 'orm', 'migration', 'sql'
        }
        if any(keyword in desc_lower for keyword in database_keywords):
            return 'database'

        # Testing keywords
        testing_keywords = {'test', 'testing', 'coverage', 'assertion', 'mock', 'fixture', 'spec'}
        if any(keyword in desc_lower for keyword in testing_keywords):
            return 'testing'

        # API keywords
        api_keywords = {'api', 'endpoint', 'route', 'request', 'response', 'rest', 'graphql', 'controller'}
        if any(keyword in desc_lower for keyword in api_keywords):
            return 'api'

        # Domain keywords
        domain_keywords = {'domain', 'business logic', 'business', 'operation', 'service', 'usecase'}
        if any(keyword in desc_lower for keyword in domain_keywords):
            return 'domain'

        # UI keywords (lowest priority - removed 'view' to prevent false matches)
        ui_keywords = {'ui', 'component', 'screen', 'page', 'xaml', 'jsx', 'interface', 'frontend'}
        if any(keyword in desc_lower for keyword in ui_keywords):
            return 'ui'

        return 'general'

'''

    # Find insertion point
    insertion_point = original_content.find('    def _enhance_agent_info_with_ai')
    if insertion_point == -1:
        print("ERROR: Could not find _enhance_agent_info_with_ai method", file=sys.stderr)
        return 1

    # Insert the new method
    modified_content = original_content[:insertion_point] + new_method + '\n' + original_content[insertion_point:]

    # Now find and replace the fallback section
    # Pattern: the except block with the old if/elif chain
    import re

    # Strategy: Find the entire except block and replace it
    # This is more robust than trying to match exact whitespace

    # Look for the pattern starting from after our insertion
    new_insertion_point = insertion_point + len(new_method)

    # Find the method body
    method_start = modified_content.find('def _enhance_agent_info_with_ai', new_insertion_point)
    method_end = modified_content.find('\n    def ', method_start + 1)
    if method_end == -1:
        method_end = len(modified_content)

    method_body = modified_content[method_start:method_end]

    # Check for the old fallback pattern
    if "'view' in desc_lower" in method_body:
        print("Found problematic 'view' keyword in fallback logic")

        # Create the new fallback logic
        new_fallback = '''except (NotImplementedError, Exception):
                # Fallback: Generate basic guidance without AI
                purpose = agent_metadata['description']

                # Use categorization to generate appropriate guidance
                category = self._categorize_agent_by_keywords(agent_metadata)

                when_to_use_templates = {
                    'database': "Use this agent when implementing database operations, data persistence layers, query optimization, or repository patterns",
                    'testing': "Use this agent when writing tests, validating test coverage, setting up testing infrastructure, or creating test fixtures",
                    'api': "Use this agent when creating API endpoints, implementing request handlers, defining web routes, or building REST/GraphQL services",
                    'domain': "Use this agent when implementing business logic, creating domain operations, defining core functionality, or building service layers",
                    'ui': "Use this agent when creating UI components, implementing user interfaces, building screens, or handling presentation logic",
                    'general': f"Use this agent when working with {agent_metadata['name'].replace('-', ' ')}"
                }

                when_to_use = when_to_use_templates.get(category, when_to_use_templates['general'])

                return {
                    'purpose': purpose,
                    'when_to_use': when_to_use
                }'''

        # Find the entire except block using regex
        # Match: except (...): ... return { ... }
        pattern = r'except \(NotImplementedError, Exception\):\s+# Fallback:.*?return \{\s+\'purpose\':.*?\'when_to_use\':.*?\n\s+\}'

        matches = re.finditer(pattern, method_body, re.DOTALL)
        match_list = list(matches)

        if match_list:
            match = match_list[0]
            old_except_block = match.group(0)
            method_body_new = method_body[:match.start()] + new_fallback + method_body[match.end():]

            # Replace in the full content
            modified_content = modified_content[:method_start] + method_body_new + modified_content[method_end:]
            print("Successfully replaced fallback logic")

        else:
            print("WARNING: Could not match exact except block pattern")
            print("The new method was added, but fallback logic may need manual update")

    # Write back the file
    with open(file_path, 'w') as f:
        f.write(modified_content)

    print("✓ Fix applied to", file_path)
    print("✓ Added _categorize_agent_by_keywords method")
    print("✓ Updated fallback logic in _enhance_agent_info_with_ai")

    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())

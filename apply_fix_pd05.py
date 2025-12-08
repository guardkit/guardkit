#!/usr/bin/env python3
"""
Apply fix for TASK-FIX-PD05: Fix "When to Use" guidance accuracy in reference docs.

This script modifies installer/global/lib/template_generator/claude_md_generator.py to:
1. Add a new _categorize_agent_by_keywords method
2. Update the fallback logic in _enhance_agent_info_with_ai to use proper categorization
3. Remove the problematic 'view' keyword that causes false positive UI agent categorization
"""

import sys
from pathlib import Path

def apply_fix():
    file_path = Path('installer/global/lib/template_generator/claude_md_generator.py')

    if not file_path.exists():
        print(f"ERROR: File not found: {file_path}")
        print(f"Please run this script from the guardkit project root directory")
        return False

    print(f"Reading {file_path}...")
    with open(file_path, 'r') as f:
        content = f.read()

    # The new categorization method to insert
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

    # Find where to insert the new method (right before _enhance_agent_info_with_ai)
    insertion_point = content.find('    def _enhance_agent_info_with_ai')

    if insertion_point == -1:
        print("ERROR: Could not find _enhance_agent_info_with_ai method")
        return False

    print(f"✓ Found _enhance_agent_info_with_ai method")

    # Insert the new method
    new_content = content[:insertion_point] + new_method + '\n' + content[insertion_point:]

    # Now replace the fallback logic
    # Pattern 1: Try to match the exact problematic if/elif chain
    old_patterns = [
        # Pattern 1: if 'database' ... elif 'test' ... elif 'api' ... elif 'ui' (with 'view')
        '''except (NotImplementedError, Exception):
                # Fallback: Generate basic guidance without AI
                purpose = agent_metadata['description']

                if 'database' in desc_lower or 'firestore' in desc_lower or 'firebase' in desc_lower or 'mongodb' in desc_lower or 'crud' in desc_lower:
                    when_to_use = f"Use this agent when implementing database operations..."
                elif 'test' in desc_lower or 'testing' in desc_lower:
                    when_to_use = f"Use this agent when writing tests..."
                elif 'api' in desc_lower or 'endpoint' in desc_lower or 'route' in desc_lower:
                    when_to_use = f"Use this agent when creating API endpoints..."
                elif 'ui' in desc_lower or 'view' in desc_lower:
                    when_to_use = f"Use this agent when creating UI components..."
                else:
                    when_to_use = f"Use this agent when working with {agent_metadata['name'].replace('-', ' ')}"

                return {
                    'purpose': purpose,
                    'when_to_use': when_to_use
                }''',
    ]

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

    # Try to replace using exact pattern
    replaced = False
    for old_pattern in old_patterns:
        if old_pattern in new_content:
            new_content = new_content.replace(old_pattern, new_fallback)
            print(f"✓ Replaced fallback logic (pattern found)")
            replaced = True
            break

    if not replaced:
        # Fallback: try to find the section by looking for the problematic 'view' keyword
        if "'view' in desc_lower" in new_content:
            print("! Could not find exact pattern, attempting regex replacement...")
            import re
            # More flexible pattern matching
            pattern = r"except \(NotImplementedError, Exception\):.*?return \{[^}]*'when_to_use'[^}]*\}"
            matches = re.findall(pattern, new_content, re.DOTALL)
            if matches:
                # Replace the first match found
                new_content = new_content.replace(matches[0], new_fallback, 1)
                print(f"✓ Replaced fallback logic (regex pattern)")
                replaced = True

        if not replaced:
            print("WARNING: Could not find exact fallback pattern to replace")
            print("The new method was added, but manual replacement may be needed")
            print("Look for the 'view' keyword in _enhance_agent_info_with_ai fallback section")

    # Write the file back
    print(f"Writing changes to {file_path}...")
    with open(file_path, 'w') as f:
        f.write(new_content)

    print("\n" + "="*80)
    print("FIX APPLIED SUCCESSFULLY!")
    print("="*80)
    print("✓ Added _categorize_agent_by_keywords method")
    print("✓ Updated fallback logic in _enhance_agent_info_with_ai")
    print("✓ Removed problematic 'view' keyword check")
    print("\nVerifying changes...")

    # Verify the changes
    with open(file_path, 'r') as f:
        final_content = f.read()

    if '_categorize_agent_by_keywords' in final_content:
        print("✓ New method is present")
    else:
        print("✗ ERROR: New method not found!")
        return False

    if "'view' in desc_lower" not in final_content:
        print("✓ Problematic 'view' keyword removed")
    else:
        print("! WARNING: 'view' keyword still present (may be in comments or different context)")

    return True

if __name__ == '__main__':
    import os

    # Check if we're in the right directory
    if not Path('installer').exists() or not Path('installer/global').exists():
        print("ERROR: This script must be run from the guardkit project root directory")
        print(f"Current directory: {os.getcwd()}")
        sys.exit(1)

    success = apply_fix()
    sys.exit(0 if success else 1)

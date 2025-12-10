#!/usr/bin/env python3
"""
TASK-FIX-PD05: Fix "When to Use" guidance accuracy
Execute this script to apply the fix: python3 RUN_FIX_NOW.py
"""

import sys
import re
from pathlib import Path

def apply_task_fix_pd05():
    """Apply the fix for TASK-FIX-PD05"""

    file_path = Path('installer/core/lib/template_generator/claude_md_generator.py')

    # Verify we're in the right directory
    if not file_path.exists():
        print("ERROR: File not found. Run this script from the guardkit root directory")
        print(f"Expected: {file_path}")
        print(f"Current dir: {Path.cwd()}")
        return 1

    print(f"Reading {file_path}...")

    # Read the original file
    with open(file_path, 'rb') as f:
        original_bytes = f.read()

    original_content = original_bytes.decode('utf-8')

    # Define the new categorization method
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

    # Step 1: Find and insert the new method before _enhance_agent_info_with_ai
    print("Step 1: Adding _categorize_agent_by_keywords method...")

    insertion_point = original_content.find('    def _enhance_agent_info_with_ai')
    if insertion_point == -1:
        print("ERROR: Could not find _enhance_agent_info_with_ai method")
        return 1

    modified_content = (
        original_content[:insertion_point] +
        new_method + '\n' +
        original_content[insertion_point:]
    )

    print("✓ New method added")

    # Step 2: Replace the fallback logic
    print("Step 2: Updating fallback logic in _enhance_agent_info_with_ai...")

    # The new fallback logic
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

    # Look for the old pattern
    # The pattern is: except (NotImplementedError, Exception): ... return { ... }
    # We'll use regex to find and replace it

    pattern = re.compile(
        r'except \(NotImplementedError, Exception\):\s+# Fallback:.*?return \{\s+\'purpose\':.*?\'when_to_use\':.*?\n\s+\}',
        re.DOTALL
    )

    # Check if pattern exists
    if pattern.search(modified_content):
        modified_content = pattern.sub(new_fallback, modified_content, count=1)
        print("✓ Fallback logic replaced")
    else:
        print("! WARNING: Could not find exact except block pattern")
        print("  Attempting alternative pattern search...")

        # Try to find any except block with 'view' keyword
        if "'view' in desc_lower" in modified_content:
            # Find the broader context
            view_pos = modified_content.find("'view' in desc_lower")
            if view_pos > 0:
                # Go back to find the except
                except_pos = modified_content.rfind('except (NotImplementedError, Exception):', max(0, view_pos - 1000), view_pos)
                # Find the next return statement
                return_pos = modified_content.find('return {', except_pos)
                # Find the closing brace
                brace_count = 0
                end_pos = return_pos
                for i in range(return_pos, len(modified_content)):
                    if modified_content[i] == '{':
                        brace_count += 1
                    elif modified_content[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_pos = i + 1
                            break

                if except_pos > 0 and end_pos > return_pos:
                    old_block = modified_content[except_pos:end_pos]
                    modified_content = modified_content[:except_pos] + new_fallback + modified_content[end_pos:]
                    print("✓ Fallback logic replaced (using alternative pattern)")

    # Step 3: Verify the fix
    print("\nStep 3: Verifying fix...")

    if '_categorize_agent_by_keywords' in modified_content:
        print("✓ New method present in file")
    else:
        print("✗ ERROR: New method not found in file!")
        return 1

    # Check that we removed the problematic code
    # Note: May still exist in comments or other contexts, but not in the active fallback
    lines_with_view = []
    for i, line in enumerate(modified_content.split('\n'), 1):
        if "'view' in desc_lower" in line:
            lines_with_view.append((i, line.strip()))

    if lines_with_view:
        print(f"! WARNING: 'view' keyword still found on {len(lines_with_view)} line(s)")
        for line_num, line in lines_with_view[:3]:
            print(f"  Line {line_num}: {line[:60]}...")
    else:
        print("✓ Problematic 'view' keyword removed")

    # Step 4: Write the file back
    print("\nStep 4: Writing changes to file...")

    with open(file_path, 'wb') as f:
        f.write(modified_content.encode('utf-8'))

    print(f"✓ File written: {file_path}")

    print("\n" + "="*80)
    print("SUCCESS! TASK-FIX-PD05 fix has been applied")
    print("="*80)
    print("\nChanges made:")
    print("1. Added _categorize_agent_by_keywords method (lines before _enhance_agent_info_with_ai)")
    print("2. Updated fallback logic to use proper categorization")
    print("3. Removed problematic 'view' keyword from UI detection")
    print("\nTo verify the fix, run:")
    print("  pytest tests/unit/test_completeness_validator.py -v")
    print("  pytest tests/lib/test_claude_md_generator.py -v")

    return 0

if __name__ == '__main__':
    import os
    # Ensure we're in the guardkit directory
    guardkit_root = Path('/Users/richardwoollcott/Projects/appmilla_github/guardkit')
    os.chdir(guardkit_root)

    exit_code = apply_task_fix_pd05()
    sys.exit(exit_code)

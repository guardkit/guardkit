---
id: TASK-039
title: Implement code pattern extraction engine
status: backlog
created: 2025-11-01T16:00:00Z
priority: high
complexity: 7
estimated_hours: 8
tags: [template-create, pattern-extraction, code-analysis]
epic: EPIC-001
feature: pattern-extraction
dependencies: [TASK-037, TASK-038]
blocks: [TASK-045]
---

# TASK-039: Implement Code Pattern Extraction Engine

## Objective

Extract reusable code patterns from existing codebase to generate template files:
- Identify common class structures (components, operations, repositories)
- Extract method signatures and patterns
- Identify dependency injection patterns
- Generate abstracted patterns for template generation

## Requirements

**REQ-1**: Extract React component patterns
```
When analyzing React/TypeScript code, extract:
- Functional component structure
- Props interface patterns
- Hook usage patterns (useState, useEffect, custom hooks)
- Event handler patterns
- Component composition patterns
```

**REQ-2**: Extract .NET domain operation patterns
```
When analyzing .NET code, extract:
- Domain operation class structure
- Constructor injection patterns
- ExecuteAsync method signatures
- ErrorOr<T> return type usage
- Logging patterns
```

**REQ-3**: Extract repository patterns
```
When analyzing data access code, extract:
- Repository interface structure
- CRUD method signatures
- Async/await patterns
- Error handling in data layer
```

**REQ-4**: Extract service patterns
```
When analyzing external service integrations, extract:
- Service interface structure
- HTTP client usage patterns
- API integration patterns
- Authentication/authorization patterns
```

## Acceptance Criteria

- [ ] Extracts React functional component patterns (>85% accuracy)
- [ ] Extracts .NET domain operation patterns
- [ ] Extracts repository interface and implementation patterns
- [ ] Extracts service patterns
- [ ] Identifies dependency injection patterns
- [ ] Returns structured pattern data (JSON)
- [ ] Handles multiple languages (TypeScript, C#, Python)
- [ ] Unit tests passing (>85% coverage)

## Implementation Plan

### Step 1: Create Pattern Extractor

```python
# installer/global/commands/lib/pattern_extraction/code_extractor.py

from dataclasses import dataclass
from typing import List, Dict, Optional
import ast  # Python AST
import re

@dataclass
class CodePattern:
    pattern_type: str  # "component", "domain_operation", "repository"
    language: str
    class_name: str
    methods: List[Dict[str, str]]
    dependencies: List[str]
    properties: List[Dict[str, str]]
    sample_code: str

class CodePatternExtractor:
    def __init__(self, project_path: str, stack_result, architecture_result):
        self.project_path = project_path
        self.stack_result = stack_result
        self.architecture_result = architecture_result

    def extract_patterns(self) -> List[CodePattern]:
        """Extract code patterns from codebase"""
        pass

    def _extract_react_patterns(self) -> List[CodePattern]:
        """Extract React component patterns"""
        pass

    def _extract_dotnet_patterns(self) -> List[CodePattern]:
        """Extract .NET class patterns"""
        pass

    def _extract_python_patterns(self) -> List[CodePattern]:
        """Extract Python class patterns"""
        pass
```

### Step 2: Implement React Pattern Extraction

```python
def _extract_react_patterns(self) -> List[CodePattern]:
    """Extract React component patterns from TypeScript files"""

    patterns = []

    for root, dirs, files in os.walk(self.project_path):
        if 'node_modules' in root:
            continue

        for file in files:
            if not file.endswith(('.tsx', '.jsx')):
                continue

            file_path = os.path.join(root, file)

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Extract functional component pattern
                pattern = self._parse_react_component(content, file)
                if pattern:
                    patterns.append(pattern)

            except Exception as e:
                continue

    return patterns

def _parse_react_component(self, content: str, filename: str) -> Optional[CodePattern]:
    """Parse React functional component"""

    # Extract component name
    component_match = re.search(r'export (?:const|function) (\w+)', content)
    if not component_match:
        return None

    component_name = component_match.group(1)

    # Extract props interface
    props_match = re.search(
        rf'interface {component_name}Props\s*{{([^}}]+)}}',
        content,
        re.DOTALL
    )

    properties = []
    if props_match:
        props_content = props_match.group(1)
        # Parse prop definitions
        for line in props_content.split('\n'):
            prop_match = re.match(r'\s*(\w+)(\?)?:\s*(.+);?', line.strip())
            if prop_match:
                properties.append({
                    'name': prop_match.group(1),
                    'type': prop_match.group(3),
                    'optional': prop_match.group(2) == '?'
                })

    # Extract hooks used
    hooks = re.findall(r'(use\w+)', content)

    return CodePattern(
        pattern_type="react_component",
        language="typescript",
        class_name=component_name,
        methods=[],  # React components don't have traditional methods
        dependencies=list(set(hooks)),
        properties=properties,
        sample_code=content[:500]  # First 500 chars as sample
    )
```

### Step 3: Implement .NET Pattern Extraction

```python
def _extract_dotnet_patterns(self) -> List[CodePattern]:
    """Extract .NET class patterns from C# files"""

    patterns = []

    for root, dirs, files in os.walk(self.project_path):
        if any(skip in root for skip in ['bin', 'obj', 'node_modules']):
            continue

        for file in files:
            if not file.endswith('.cs'):
                continue

            file_path = os.path.join(root, file)

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Extract domain operation pattern
                if 'class' in content and any(verb in file for verb in ['Get', 'Create', 'Update', 'Delete']):
                    pattern = self._parse_dotnet_class(content, file)
                    if pattern:
                        patterns.append(pattern)

            except Exception as e:
                continue

    return patterns

def _parse_dotnet_class(self, content: str, filename: str) -> Optional[CodePattern]:
    """Parse .NET class structure"""

    # Extract class name
    class_match = re.search(r'public class (\w+)', content)
    if not class_match:
        return None

    class_name = class_match.group(1)

    # Extract constructor parameters (dependencies)
    constructor_match = re.search(
        rf'public {class_name}\s*\(([^)]+)\)',
        content,
        re.DOTALL
    )

    dependencies = []
    if constructor_match:
        params = constructor_match.group(1)
        for param in params.split(','):
            type_match = re.match(r'\s*(\w+(?:<\w+>)?)\s+\w+', param.strip())
            if type_match:
                dependencies.append(type_match.group(1))

    # Extract methods
    methods = []
    method_pattern = r'public (?:async )?([\w<>]+) (\w+)\s*\(([^)]*)\)'
    for match in re.finditer(method_pattern, content):
        methods.append({
            'return_type': match.group(1),
            'name': match.group(2),
            'parameters': match.group(3).strip()
        })

    return CodePattern(
        pattern_type="domain_operation",
        language="csharp",
        class_name=class_name,
        methods=methods,
        dependencies=dependencies,
        properties=[],
        sample_code=content[:500]
    )
```

## Testing Strategy

```python
def test_extract_react_component():
    """Should extract React component pattern"""
    sample_code = '''
    interface ProductListProps {
        products: Product[];
        onSelect: (id: string) => void;
    }

    export const ProductList: React.FC<ProductListProps> = ({ products, onSelect }) => {
        const [selected, setSelected] = useState<string | null>(null);

        return (
            <div className="product-list">
                {products.map(p => <ProductCard key={p.id} />)}
            </div>
        );
    };
    '''

    extractor = CodePatternExtractor("test", mock_stack, mock_arch)
    pattern = extractor._parse_react_component(sample_code, "ProductList.tsx")

    assert pattern.class_name == "ProductList"
    assert len(pattern.properties) == 2
    assert 'useState' in pattern.dependencies
```

## Files to Create

1. `installer/global/commands/lib/pattern_extraction/code_extractor.py` (~600 lines)
2. `installer/global/commands/lib/pattern_extraction/react_parser.py` (~300 lines)
3. `installer/global/commands/lib/pattern_extraction/dotnet_parser.py` (~300 lines)
4. `installer/global/commands/lib/pattern_extraction/python_parser.py` (~250 lines)
5. `tests/unit/test_code_extractor.py` (~400 lines)

## Definition of Done

- [ ] CodePatternExtractor class implemented
- [ ] React pattern extraction working
- [ ] .NET pattern extraction working
- [ ] Python pattern extraction working
- [ ] Returns structured pattern data
- [ ] Unit tests passing (>85% coverage)
- [ ] Integration with TASK-037, TASK-038
- [ ] Documentation complete

---

**Estimated Time**: 8 hours
**Complexity**: 7/10 (Medium-High)
**Priority**: HIGH

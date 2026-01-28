#!/bin/bash
# Run ADR Service tests with coverage

cd /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-GI

echo "=========================================="
echo "Running ADR Service Tests"
echo "=========================================="
echo ""

# Run tests with coverage for adr_service.py specifically
pytest tests/knowledge/test_adr_service.py -v \
  --cov=guardkit/knowledge/adr_service.py \
  --cov-report=term-missing \
  --cov-report=json

echo ""
echo "=========================================="
echo "Coverage Summary"
echo "=========================================="
python -c "
import json
with open('coverage.json', 'r') as f:
    data = json.load(f)
    summary = data['totals']
    print(f'Line Coverage: {summary[\"percent_covered\"]:.1f}%')
    print(f'Lines Covered: {summary[\"covered_lines\"]}/{summary[\"num_statements\"]}')
    print('')
    # Show file-specific coverage
    for filename, file_data in data['files'].items():
        if 'adr_service.py' in filename:
            print(f'File: {filename}')
            print(f'  Coverage: {file_data[\"summary\"][\"percent_covered\"]:.1f}%')
            print(f'  Lines: {file_data[\"summary\"][\"covered_lines\"]}/{file_data[\"summary\"][\"num_statements\"]}')
            missing = file_data.get('missing_lines', [])
            if missing:
                print(f'  Missing Lines: {missing[:10]}' + ('...' if len(missing) > 10 else ''))
"

"""
Pytest configuration for TASK-002 tests
Adds installer/global to Python path for module imports (so 'from lib.X' works)
"""
import sys
from pathlib import Path

# Add installer/global to Python path (parent of lib)
# This allows imports like: from lib.settings_generator import X
lib_parent_path = Path(__file__).parent / "installer" / "global"
if str(lib_parent_path) not in sys.path:
    sys.path.insert(0, str(lib_parent_path))

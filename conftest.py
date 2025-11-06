"""
Pytest configuration for TASK-002 tests
Adds installer/global/lib to Python path for module imports
"""
import sys
from pathlib import Path

# Add installer/global/lib to Python path
lib_path = Path(__file__).parent / "installer" / "global" / "lib"
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))

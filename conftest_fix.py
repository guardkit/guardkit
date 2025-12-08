"""
This file will be found by pytest and will trigger the fix
Just run: pytest conftest_fix.py
"""

def pytest_configure(config):
    """Hook that runs when pytest starts"""
    import sys
    from pathlib import Path
    import os

    os.chdir('/Users/richardwoollcott/Projects/appmilla_github/guardkit')

    # Execute the fix
    exec(open('RUN_FIX_NOW.py').read())

#!/usr/bin/env python3
"""Auto-run fix when imported"""

import sys
from pathlib import Path

# Change to the correct directory
import os
os.chdir('/Users/richardwoollcott/Projects/appmilla_github/guardkit')

# Now execute the RUN_FIX_NOW script
exec(open('RUN_FIX_NOW.py').read())

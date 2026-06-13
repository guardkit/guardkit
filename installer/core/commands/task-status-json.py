#!/usr/bin/env python3
"""
Task Status JSON Command

This script provides a CLI command to output task status in JSON format.

Usage:
    task-status-json [TASK-ID] [--base-path PATH]
"""

import argparse
import sys
from pathlib import Path

# Add the project root to sys.path so we can import our module
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from installer.core.commands.lib.task_status_json import main as task_status_json_main

def main():
    """Main entry point for task-status-json command."""
    # This is a thin wrapper that calls the existing task_status_json module
    # with appropriate arguments
    task_status_json_main()

if __name__ == "__main__":
    main()
# Safe code sample: Safe Subprocess Usage
# These patterns should NOT trigger security warnings

import subprocess
import shlex


def list_directory(path):
    """Safe: Using list arguments without shell=True."""
    subprocess.run(["ls", "-la", path])


def ping_host(hostname):
    """Safe: Using list arguments for ping."""
    subprocess.run(["ping", "-c", "4", hostname])


def backup_file(source, destination):
    """Safe: Using explicit command list."""
    subprocess.run(["cp", source, destination])


def process_data(input_file, output_file):
    """Safe: Using Popen with list arguments."""
    subprocess.Popen(["cat", input_file], stdout=open(output_file, "w"))


def run_command_safely(command_parts):
    """Safe: Using command list, no shell."""
    result = subprocess.run(
        command_parts,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def quote_and_run(user_input):
    """Safe: Using shlex.quote for shell escaping when necessary."""
    safe_input = shlex.quote(user_input)
    # Even with shell=True, input is safely quoted
    subprocess.run(f"echo {safe_input}", shell=True)

# Vulnerable code sample: Command Injection
# These patterns should be detected by SecurityChecker

import subprocess
import os


def list_directory(path):
    """Vulnerable: Command injection via f-string in subprocess."""
    subprocess.run(f"ls {path}", shell=True)


def ping_host(hostname):
    """Vulnerable: Command injection via os.system."""
    os.system(f"ping -c 4 {hostname}")


def backup_file(filename):
    """Vulnerable: Command injection in shell command."""
    subprocess.call(f"cp {filename} /backup/", shell=True)


def process_data(input_data):
    """Vulnerable: Command injection via subprocess with shell=True."""
    cmd = f"echo {input_data} | process_tool"
    subprocess.Popen(cmd, shell=True)

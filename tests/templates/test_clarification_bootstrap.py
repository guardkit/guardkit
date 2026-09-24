"""Run the shipped examples from a different project, with both install layouts."""
from pathlib import Path
import re
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = re.findall(r"```python\n(import sys\n.*?)\nfrom clarification.core", (ROOT / "installer/core/agents/clarification-questioner.md").read_text(), re.S)


@pytest.mark.parametrize("example", EXAMPLES, ids=["quick", "main"])
@pytest.mark.parametrize("layout", ["packaged", "editable", "home_only"])
def test_clarification_example_finds_library_outside_install_directory(tmp_path, example, layout):
    site = tmp_path / "install location"
    package = site / "guardkit"
    home = tmp_path / "home"
    elsewhere = tmp_path / "another project"
    elsewhere.mkdir()
    home.mkdir()
    if layout == "home_only":
        library = home / ".agentecflow/lib"
    else:
        (package / "templates").mkdir(parents=True)
        (package / "__init__.py").touch()
        (package / "templates/__init__.py").touch()
        shutil.copyfile(ROOT / "guardkit/templates/resolver.py", package / "templates/resolver.py")
        # The wheel's _installer_core is data, with no __init__.py or __file__.
        core = package / "_installer_core" if layout == "packaged" else site / "installer/core"
        library = core / "commands/lib"
    (library / "clarification").mkdir(parents=True)
    (library / "clarification/__init__.py").touch()
    env = {"PATH": "/usr/bin:/bin", "HOME": str(home), "PYTHONPATH": str(site), "PYTHONDONTWRITEBYTECODE": "1"}
    result = subprocess.run([sys.executable, "-S", "-c", example + "\nimport clarification\nprint(clarification.__file__)"],
                            cwd=elsewhere, env=env, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(library / "clarification/__init__.py")

"""Render and verify the React/Go compile fixture in a new scratch directory.

This is a template test, not an application scaffolding command. PostgreSQL,
OIDC, browser and container operation are separate foundation acceptance gates.
Requires the pinned Go/Node/Staticcheck tools, a C compiler for Go's race detector,
and network access or populated dependency caches. No missing-tool success path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from guardkit.orchestrator.toolchain_declaration import (  # noqa: E402
    load_toolchain_declaration,
    resolve_component_cwd,
)
from guardkit.templates.render import render_text  # noqa: E402

TEMPLATE = REPO / "installer/core/templates/react-go-monorepo"


def contained(root: Path, value: str) -> Path:
    path = (root / value).resolve()
    if not path.is_relative_to(root.resolve()) or path == root.resolve():
        raise ValueError(f"Path must be contained in its root: {value}")
    return path


def materialise(output: Path) -> None:
    """Render the exact shipped layout, refusing existing output or collisions."""
    output.mkdir(parents=True, exist_ok=False)
    layout = json.loads((TEMPLATE / "templates/layout.json").read_text())
    for source, destination in layout.items():
        src = contained(TEMPLATE / "templates", source)
        dest = contained(output, destination)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            raise ValueError(f"Duplicate destination: {destination}")
        dest.write_text(render_text(src.read_text(), {}))
    for source, destination in (
        ("go.sum", "apps/api/go.sum"),
        ("package-lock.json", "package-lock.json"),
    ):
        shutil.copyfile(TEMPLATE / "validation" / source, output / destination)


def run(command: list[str], cwd: Path, env: dict[str, str]) -> None:
    print("+ " + " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, env=env, check=True)


def run_declared_coverage(output: Path, env: dict[str, str]) -> None:
    """Run every declared coverage command as the coach does: shell, its cwd, exit 0."""
    declaration = load_toolchain_declaration(output)
    if declaration is None:
        raise RuntimeError("Rendered .guardkit/config.yaml did not load")
    targets = [("root", output, declaration.coverage)] + [
        (name, resolve_component_cwd(output, component.cwd), component.coverage)
        for name, component in sorted((declaration.components or {}).items())
    ]
    for name, cwd, command in targets:
        if not command:
            raise RuntimeError(f"No coverage declared for {name}")
        print(f"+ ({name}) {command}", flush=True)
        result = subprocess.run(command, shell=True, cwd=cwd, env=env, text=True, capture_output=True)
        print(result.stdout + result.stderr, flush=True)
        combined = result.stdout + result.stderr
        if result.returncode != 0:
            raise RuntimeError(f"Declared coverage failed for {name}: exit {result.returncode}")
        totals = {"root": ("total:", "Statements"), "api": ("total:",), "web": ("Statements",)}
        missing = [word for word in totals[name] if word not in combined]
        if missing:
            raise RuntimeError(f"Declared coverage for {name} printed no total: {missing}")
    print("PASS: declared coverage commands exit 0 and print totals", flush=True)


def reject_mutation(
    path: Path, contents: str, command: list[str], cwd: Path,
    env: dict[str, str], diagnostic: str, *, append: bool = False,
) -> None:
    """Reject a known defect with a substantive diagnostic, restoring all bytes."""
    before = path.read_bytes() if path.exists() else None
    if before is not None and not append:
        raise ValueError(f"Refusing to replace existing negative-control file: {path}")
    try:
        path.write_bytes((before or b"") + contents.encode())
        result = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True)
        if result.returncode == 0 or diagnostic not in result.stdout + result.stderr:
            raise RuntimeError(f"Negative control failed: {command}\n{result.stdout}\n{result.stderr}")
        print(f"PASS: {path.name} rejects {diagnostic}", flush=True)
    finally:
        if before is None:
            path.unlink(missing_ok=True)
        else:
            path.write_bytes(before)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="New scratch directory; must not exist")
    args = parser.parse_args()
    for tool in ("go", "gofmt", "staticcheck", "node", "npm", "bash"):
        if shutil.which(tool) is None:
            raise SystemExit(f"Required tool unavailable: {tool}")
    output = args.output.resolve()
    materialise(output)
    env = dict(os.environ, GOTOOLCHAIN="local", GOFLAGS="-mod=readonly", GOWORK="off")
    expected_go = "go" + (output / ".go-version").read_text().strip()
    actual_go = subprocess.check_output(["go", "env", "GOVERSION"], env=env, text=True).strip()
    expected_node = "v" + (output / ".nvmrc").read_text().strip()
    actual_node = subprocess.check_output(["node", "--version"], text=True).strip()
    if (actual_go, actual_node) != (expected_go, expected_node):
        raise SystemExit(f"Toolchain mismatch: expected {expected_go}/{expected_node}, got {actual_go}/{actual_node}")
    for command in (["go", "version"], ["staticcheck", "-version"], ["node", "--version"], ["npm", "--version"]):
        run(command, output, env)
    locked = [output / name for name in ("apps/api/go.mod", "apps/api/go.sum", "package-lock.json")]
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in locked}
    # The declared root install, then the declared aggregate test (.guardkit/config.yaml).
    run(["bash", "scripts/install.sh"], output, env)
    run(["bash", "scripts/check.sh"], output, env)
    run_declared_coverage(output, env)
    negative = output / "apps/api/internal/notes/negative_control.go"
    reject_mutation(negative, 'package notes\nfunc invalidType() int { return "bad" }\n',
                    ["go", "build", "./..."], output / "apps/api", env, "cannot use")
    reject_mutation(negative, 'package notes\nimport "sync"\nfunc invalidCopy() { var mu sync.Mutex; copied := mu; _ = copied }\n',
                    ["go", "vet", "./..."], output / "apps/api", env, "copies lock value")
    web = output / "apps/web/src/api.ts"
    reject_mutation(web, '\nexport const invalidType: number = "bad";\n',
                    ["npm", "--workspace", "sample-web", "run", "typecheck"], output, env, "TS2322", append=True)
    reject_mutation(web, '\nPromise.resolve(1);\n',
                    ["npm", "--workspace", "sample-web", "run", "lint"], output, env, "no-floating-promises", append=True)
    for path, digest in before.items():
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise RuntimeError(f"Dependency manifest drifted: {path.relative_to(output)}")
    print("PASS: native template checks and lock preservation (database/auth/browser/container runtime not exercised)")


if __name__ == "__main__":
    main()

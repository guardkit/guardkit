"""Compile-tier verification of the shipped React/Rust examples in a fresh scratch tree.

This is a template test fixture, not an application scaffolding command. It does
not claim to test PostgreSQL execution, OIDC, containers, or factory deployment.
Run from the repository root with a fresh output directory; dependencies are
installed from the committed fixture lockfiles. Requires Python, Cargo with the
pinned toolchain, Node and npm. Missing tools or failed child commands fail.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from guardkit.templates.render import render_text  # noqa: E402

TEMPLATE = REPO / "installer/core/templates/react-rust-monorepo"


def contained(root: Path, value: str) -> Path:
    path = (root / value).resolve()
    if not path.is_relative_to(root.resolve()) or path == root.resolve():
        raise ValueError(f"Path must be contained in its root: {value}")
    return path


def materialise(output: Path) -> None:
    """Render the exact checked-in fixture mapping, refusing existing output."""
    output.mkdir(parents=True, exist_ok=False)
    layout = json.loads((TEMPLATE / "templates/layout.json").read_text())
    # The template deliberately uses fixed neutral identifiers so lockfile
    # names and compile evidence correspond to exactly the same source.
    for source, destination in layout.items():
        src = contained(TEMPLATE / "templates", source)
        dest = contained(output, destination)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            raise ValueError(f"Duplicate destination: {destination}")
        dest.write_text(render_text(src.read_text(), {}))
    for name in ("Cargo.lock", "package-lock.json"):
        shutil.copyfile(TEMPLATE / "validation" / name, output / name)


def run(command: list[str], output: Path) -> None:
    print("+ " + " ".join(command), flush=True)
    subprocess.run(command, cwd=output, check=True)


def reject_mutation(output: Path, relative: str, extra: str, command: list[str], diagnostic: str) -> None:
    """A previously passing check must reject a known defect; restore scratch bytes."""
    path = contained(output, relative)
    before = path.read_text()
    try:
        path.write_text(before + "\n" + extra + "\n")
        result = subprocess.run(command, cwd=output, text=True, capture_output=True)
        if result.returncode == 0 or diagnostic not in result.stdout + result.stderr:
            raise RuntimeError(f"Negative control did not fail as expected: {command}\n{result.stdout}\n{result.stderr}")
        print(f"PASS: {relative} rejects {diagnostic}", flush=True)
    finally:
        path.write_text(before)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="New scratch directory; must not exist")
    args = parser.parse_args()
    for tool in ("cargo", "rustc", "node", "npm", "bash"):
        if shutil.which(tool) is None:
            raise SystemExit(f"Required tool unavailable: {tool}")
    output = args.output.resolve()
    materialise(output)
    expected_node = "v" + (output / ".nvmrc").read_text().strip()
    actual_node = subprocess.check_output(["node", "--version"], text=True).strip()
    if actual_node != expected_node:
        raise SystemExit(f"Node version mismatch: expected {expected_node}, got {actual_node}")
    for command in (["rustc", "--version"], ["node", "--version"], ["npm", "--version"]):
        run(command, output)
    run(["npm", "ci", "--ignore-scripts", "--no-audit", "--no-fund"], output)
    run(["bash", "scripts/check.sh"], output)
    reject_mutation(output, "apps/api/src/lib.rs", 'pub fn invalid_type() -> u8 { "bad" }',
                    ["cargo", "check", "--workspace", "--locked"], "mismatched types")
    reject_mutation(output, "apps/web/src/api.ts", 'export const invalidType: number = "bad";',
                    ["npm", "--workspace", "sample-web", "run", "typecheck"], "TS2322")
    reject_mutation(output, "apps/api/src/lib.rs", 'pub fn forbidden_panic() { panic!("no"); }',
                    ["cargo", "clippy", "--workspace", "--all-targets", "--locked", "--", "-D", "warnings"], "clippy::panic")
    reject_mutation(output, "apps/web/src/api.ts", 'Promise.resolve(1);',
                    ["npm", "--workspace", "sample-web", "run", "lint"], "no-floating-promises")
    print("PASS: native template checks (database/auth/container runtime not exercised)")


if __name__ == "__main__":
    main()

"""Fail on unexpected high/critical npm advisories.

Vite 5.2.8 is temporarily accepted because the current DCloud uni-app plugin
declares that exact peer version. The development server must remain local and
H5 output is not part of the public mini-program deployment.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


ALLOWED_HIGH_PACKAGES = {"vite"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cwd", type=Path, default=Path("miniapp"))
    args = parser.parse_args()

    npm_name = "npm.cmd" if os.name == "nt" else "npm"
    npm_executable = shutil.which(npm_name)
    if not npm_executable:
        print("npm executable was not found.", file=sys.stderr)
        return 1
    result = subprocess.run(
        [npm_executable, "audit", "--json"],
        cwd=args.cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError:
        print("npm audit did not return valid JSON.", file=sys.stderr)
        if result.stderr:
            print(result.stderr.strip(), file=sys.stderr)
        return 1

    unexpected: list[str] = []
    accepted: list[str] = []
    for package, finding in report.get("vulnerabilities", {}).items():
        severity = finding.get("severity", "unknown")
        if severity == "critical":
            unexpected.append(f"{package} ({severity})")
        elif severity == "high" and package not in ALLOWED_HIGH_PACKAGES:
            unexpected.append(f"{package} ({severity})")
        elif severity == "high":
            accepted.append(f"{package} ({severity})")

    if unexpected:
        print("Unexpected npm security findings: " + ", ".join(sorted(unexpected)))
        return 1
    if accepted:
        print("Known temporary exceptions: " + ", ".join(sorted(accepted)))
    print("No unexpected high or critical npm vulnerabilities found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

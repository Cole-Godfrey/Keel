"""install the five-minute macOS launchd paper runner."""

from __future__ import annotations

import os
import plistlib
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LABEL = "com.keel.paper"


def main() -> None:
    launch_agents = Path.home() / "Library" / "LaunchAgents"
    launch_agents.mkdir(parents=True, exist_ok=True)
    destination = launch_agents / f"{LABEL}.plist"
    settings = {
        "Label": LABEL,
        "ProgramArguments": ["/bin/sh", str(ROOT / "paper" / "run_once.sh")],
        "WorkingDirectory": str(ROOT),
        "EnvironmentVariables": {"PYTHON_BIN": sys.executable},
        "StartInterval": 300,
        "RunAtLoad": True,
        "StandardOutPath": str(ROOT / "paper" / "runner.log"),
        "StandardErrorPath": str(ROOT / "paper" / "runner.err"),
    }
    destination.write_bytes(plistlib.dumps(settings))
    domain = f"gui/{os.getuid()}"
    # replace an existing Keel job before installing the current schedule.
    subprocess.run(["launchctl", "bootout", domain, str(destination)], check=False, capture_output=True)
    subprocess.run(["launchctl", "bootstrap", domain, str(destination)], check=True)
    subprocess.run(["launchctl", "print", f"{domain}/{LABEL}"], check=True)
    print(destination)


if __name__ == "__main__":
    main()

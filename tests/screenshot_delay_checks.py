#!/usr/bin/env python3
"""Option validation for --screenshot-delay. Argument parsing fails before any window or GPU work."""
import subprocess
import sys
from pathlib import Path

binary = Path(sys.argv[1])
shot = "/nonexistent-dir/never-written.ppm"
cases = {
    "below_minimum": ["--screenshot-delay", "1"],
    "above_maximum": ["--screenshot-delay", "31"],
    "not_finite": ["--screenshot-delay", "nan"],
    "outlives_smoke": ["--smoke", "3", "--screenshot-delay", "10"],
    "equals_smoke": ["--smoke", "5", "--screenshot-delay", "5"],
}
for name, extra in cases.items():
    result = subprocess.run([str(binary), "--background", "--no-diagnostics", "--screenshot", shot, *extra],
                            capture_output=True, text=True, timeout=20)
    if result.returncode != 1 or "--screenshot-delay must" not in result.stderr:
        raise SystemExit(f"{name}: expected rejection, got exit {result.returncode}: {result.stderr!r}")
print("screenshot delay option validation PASS")

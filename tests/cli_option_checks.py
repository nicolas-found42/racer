#!/usr/bin/env python3
"""Rejection checks for the new visual command-line options. Parsing fails before any window or GPU work."""
import subprocess
import sys
from pathlib import Path

binary = Path(sys.argv[1])
cases = {
    "time_unknown": (["--time", "noon"], "--time must be day, dusk or night"),
    "time_missing_value": (["--time"], None),
    "paint_unknown": (["--paint", "chartreuse"], "--paint must be red"),
}
for name, (extra, message) in cases.items():
    result = subprocess.run([str(binary), "--background", "--no-diagnostics", *extra],
                            capture_output=True, text=True, timeout=20)
    if message is not None:
        if result.returncode != 1 or message not in result.stderr:
            raise SystemExit(f"{name}: expected rejection, got exit {result.returncode}: {result.stderr!r}")
    elif result.returncode == 0:
        raise SystemExit(f"{name}: expected a non-zero exit for a missing value")
print("visual option validation PASS")

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
    "start_at_not_numeric": (["--start-at", "a", "b", "c"], "--start-at needs x z heading_degrees"),
    "start_at_nan": (["--start-at", "nan", "0", "0"], "--start-at needs x z heading_degrees"),
    "start_at_far": (["--start-at", "5000", "0", "0"], "--start-at x and z must be within 600 m"),
    "start_at_missing_values": (["--start-at", "1", "2"], None),
    "camera_view_unknown": (["--camera-view", "cockpit"], None),
    "camera_pitch_too_low": (["--camera-pitch", "-15.1"], "--camera-pitch must be within [-15,30] degrees"),
    "camera_pitch_too_high": (["--camera-pitch", "30.1"], "--camera-pitch must be within [-15,30] degrees"),
    "camera_pitch_not_numeric": (["--camera-pitch", "up"], "--camera-pitch must be within [-15,30] degrees"),
    "camera_pitch_nan": (["--camera-pitch", "nan"], "--camera-pitch must be within [-15,30] degrees"),
    "camera_pitch_missing_value": (["--camera-pitch"], None),
    "camera_pitch_accept_neg15": (["--camera-pitch", "-15", "--screenshot", "/nonexistent-dir-for-racer-check/never.ppm"], "--screenshot parent directory does not exist"),
    "camera_pitch_accept_30": (["--camera-pitch", "30", "--screenshot", "/nonexistent-dir-for-racer-check/never.ppm"], "--screenshot parent directory does not exist"),
    "screenshot_parent_missing": (["--screenshot", "/nonexistent-dir-for-racer-check/never.ppm"], "--screenshot parent directory does not exist"),
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

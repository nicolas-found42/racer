#!/usr/bin/env python3
"""Incremental HUD repaint must match a full repaint on every audited frame.

--hud-repaint-audit paints each drive frame twice: once clipped to the dirty
windows and once unclipped into a scratch canvas. CoreGraphics dithers gradients
against the active clip, so one 8-bit step of difference is expected; anything
larger means a window was too small or an input went unmapped, which would leave
stale HUD pixels behind. Runs the free-drive HUD (radar, dial, waypoint) and the
handling course (countdown, measurement card, banners).
"""
import re
import subprocess
import sys

binary = sys.argv[1]
CASES = {
    "drive": ["--smoke", "8", "--benchmark", "--autodrive"],
    "course": ["--smoke", "12", "--benchmark", "--autodrive", "--scene", "course"],
}
summary = re.compile(
    r"HUD_REPAINT_AUDIT frames=(\d+) diff_pixels=(\d+) failing_frames=(\d+) "
    r"over_slack=(\d+) max_delta=(\d+) worst=(\S+)")
for name, extra in CASES.items():
    result = subprocess.run(
        [binary, "--background", "--no-diagnostics", "--hud-repaint-audit",
         "--profile", f"/tmp/racer-hud-audit-{name}/profile.txt", *extra],
        capture_output=True, text=True, timeout=180)
    if result.returncode != 0:
        raise SystemExit(f"{name}: exit {result.returncode}: {result.stderr[-400:]}")
    match = summary.search(result.stdout)
    if not match:
        raise SystemExit(f"{name}: no audit summary in {result.stdout[-400:]!r}")
    frames, diff, failing, over_slack, max_delta = (int(match.group(i)) for i in range(1, 6))
    if frames < 300:
        raise SystemExit(f"{name}: only {frames} audited frames, repaint path not exercised")
    if over_slack or failing:
        raise SystemExit(f"{name}: {failing} frames differ by more than the {2}-step slack "
                         f"({over_slack} pixels, max delta {max_delta}) at {match.group(6)}")
    if max_delta > 2:
        raise SystemExit(f"{name}: max delta {max_delta} exceeds the two-step slack")
    if diff > frames * 400:
        raise SystemExit(f"{name}: {diff} differing pixels over {frames} frames "
                         f"({diff / max(frames, 1):.0f}/frame) is too much to be clip rounding")
    print(f"{name}: frames={frames} diff_pixels={diff} ({diff / frames:.1f}/frame) "
          f"over_slack={over_slack} max_delta={max_delta} PASS")

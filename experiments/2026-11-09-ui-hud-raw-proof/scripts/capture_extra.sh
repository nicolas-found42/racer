#!/bin/bash
# Extra hidden captures for elements the standard set does not show.
# usage: scripts/capture_extra.sh OUTDIR
set -u
out=$1; shift || true
mkdir -p "$out"
bin=${RACER_BIN:-build/racer}
shot() { # name width height delay smoke script [extra args...]
  local n=$1 w=$2 h=$3 delay=$4 smoke=$5 body=$6; shift 6
  printf '%b' "$body" > "$out/$n.review"
  rm -f "$out/$n.profile"*
  timeout 90 "$bin" --background --no-diagnostics --profile "$out/$n.profile" \
    --review-script "$out/$n.review" --window "$w" "$h" "$@" \
    --screenshot "$out/$n.ppm" --screenshot-delay "$delay" --smoke "$smoke" > "$out/$n.log" 2>&1
  echo "$n exit=$?"
  python3 -c "from PIL import Image;Image.open('$out/$n.ppm').save('$out/$n.png')" 2>/dev/null && rm -f "$out/$n.ppm"
}
# Off-screen waypoint: hold throttle and steer hard so the objective leaves frame.
shot drive-edge 1920 1080 7 9 "wait 1\ndrive-input 0.45 0 0.95\nwait 5\n"
# Countdown ring: start the handling course, screenshot mid-countdown.
shot test-countdown 1920 1080 6.6 9 "wait 1\nkey back\nselect 2\nkey accept\nselect 8\nkey accept\nselect 2\nkey accept\nwait 5\n"
# Second accent palette (magenta) for the palette element.
shot drive-accent 1920 1080 6 9 "wait 1\ndrive-input 1 0 0\nwait 4\n" --hud-accent magenta
# Compact canvases (below the 0.75 layout scale).
shot drive-compact 640 480 7 9 "wait 1\ndrive-input 1 0 0\nwait 4\n"
shot garage-compact 640 480 6 9 "wait 1\nkey back\nselect 2\nkey accept\nwait 4\n"
# Pending dirty-state dialog (Apply / Discard / Keep editing).
shot pending-edit 1920 1080 7 9 "wait 1\nkey back\nselect 2\nkey accept\nkey right\nselect 7\nkey accept\nwait 4\n"
# Cancelled handling run: the invalid results screen (red INVALID headline and warning rows).
shot results-invalid 1920 1080 13 16 "wait 1\nkey back\nselect 2\nkey accept\nselect 8\nkey accept\nselect 2\nkey accept\nwait 2\nkey back\nselect 3\nkey accept\nwait 3\n"

#!/bin/bash
# Capture every UI/HUD screen of the native game into one output directory.
# usage: scripts/capture_ui.sh OUTDIR [WIDTH HEIGHT] [extra racer args...]
set -u
out=$1; w=${2:-1280}; h=${3:-720}; shift 3 2>/dev/null || shift $#
mkdir -p "$out"; bin=${RACER_BIN:-build/racer}
shot() { # name, script body, extra args
  local n=$1 body=$2; shift 2
  printf '%b' "$body" > "$out/$n.review"
  rm -f "$out/$n.career" "$out/$n.profile"*
  timeout 90 "$bin" --background --no-diagnostics --profile "$out/$n.profile" \
    --review-script "$out/$n.review" --window $w $h "$@" \
    --screenshot "$out/$n.ppm" --screenshot-delay 7 --smoke 9 > "$out/$n.log" 2>&1
  echo "$n exit=$?"
  python3 -c "from PIL import Image;Image.open('$out/$n.ppm').save('$out/$n.png')" 2>/dev/null && rm -f "$out/$n.ppm"
}
shot drive "wait 6\n"
shot drive-speed "drive-input 1 0 0\nwait 5.2\n"
shot pause "wait 1\nkey back\nwait 5\n"
shot garage "wait 1\nkey back\nselect 2\nkey accept\nwait 5\n"
shot parts "wait 1\nkey back\nselect 2\nkey accept\nselect 10\nkey accept\nwait 4\n"
shot livery "wait 1\nkey back\nselect 2\nkey accept\nselect 11\nkey accept\nwait 4\n"
shot events "wait 1\nkey back\nselect 2\nkey accept\nselect 12\nkey accept\nwait 4\n"
shot tests "wait 1\nkey back\nselect 2\nkey accept\nselect 8\nkey accept\nwait 4\n"
shot test-running "wait 1\nkey back\nselect 2\nkey accept\nselect 8\nkey accept\nselect 2\nkey accept\nwait 5.2\n"

#!/bin/bash
# Capture every UI/HUD screen of the native game into one output directory.
# usage: [ONLY="name ..."] scripts/capture_ui.sh OUTDIR [WIDTH HEIGHT] [extra racer args...]
set -u
out=$1; w=${2:-1280}; h=${3:-720}; shift 3 2>/dev/null || shift $#
mkdir -p "$out"; bin=${RACER_BIN:-build/racer}
shot() { # name, script body, extra args (SHOT_DELAY/SHOT_SMOKE override timing)
  local n=$1 body=$2; shift 2
  [[ -n ${ONLY:-} && " $ONLY " != *" $n "* ]] && return
  printf '%b' "$body" > "$out/$n.review"
  rm -f "$out/$n.career" "$out/$n.profile"*
  timeout 90 "$bin" --background --no-diagnostics --profile "$out/$n.profile" \
    --review-script "$out/$n.review" --window $w $h "$@" \
    --screenshot "$out/$n.ppm" --screenshot-delay ${SHOT_DELAY:-7} --smoke ${SHOT_SMOKE:-9} > "$out/$n.log" 2>&1
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
# Slow flows (own timing): finished test results and the unapplied-changes prompt.
SHOT_DELAY=26 SHOT_SMOKE=30 shot results "wait 1\nkey back\nselect 2\nkey accept\nselect 8\nkey accept\nkey accept\nresult 1\nwait 3\n"
shot pending "wait 1\nkey back\nselect 2\nkey accept\nkey right\nselect 7\nkey accept\nwait 4\n"
shot garage-edit "wait 1\nkey back\nselect 2\nkey accept\nselect 1\nkey right\nkey right\nkey right\nwait 4\n"

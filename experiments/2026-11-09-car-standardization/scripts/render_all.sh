#!/bin/sh
# Render every car in the kit with the shared Blender rig (overwrites PNGs). Usage: render_all.sh <kit-dir>
K="$1"; H="$(cd "$(dirname "$0")" && pwd)"
for g in "$K"/models/*.glb; do
  c="$(basename "$g" .glb)"; mkdir -p "$K/renders"
  blender -b --python "$H/render_kit.py" -- "$K/models" "$K/data/analysis.json" "$K/renders/$c" "$c" > "$K/renders/$c.log" 2>&1
  echo "$c exit=$?"
done

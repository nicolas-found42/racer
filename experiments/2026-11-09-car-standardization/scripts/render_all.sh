#!/bin/sh
# Render every car in the kit with the shared Blender rig (overwrites PNGs). Usage: render_all.sh <kit-dir>
K="$1"; H="$(cd "$(dirname "$0")" && pwd)"
for c in gran-turismo-4_acura-nsx-04 ford-racing-2_mustang-1973 midnight-club-3_corvette-z06 midnight-club-la_350z-roadster juiced-2_350z slrr_furrano-gt54; do
  blender -b --python "$H/render_kit.py" -- "$K/models" "$K/data/analysis.json" "$K/renders/$c" "$c" > "$K/renders/$c.log" 2>&1
  echo "$c exit=$?"
done

#!/bin/bash
# Chase-camera / tyre-smoke before-after matrix. Hidden window (--background): no
# window is shown or activated, so nothing steals focus and no focus-loss pause
# can fire. Captures run JOBS at a time (default 4); every job has its own
# profile file so the real profile is untouched.
#   CARS="0 2 7 16" JOBS=4 ./run.sh [before|after|both]
cd /Users/nicolas/Documents/github/reverse-engineering/games/racer || exit 1
export S=${S:-/private/tmp/claude-501/-Users-nicolas--claude-spares-spare-GIx463/46ac7067-7923-4395-9c12-a7a43dddd85a/scratchpad/cam}
export LIB=assets/local/vehicles/catalog.racer
mkdir -p "$S/shots"
rm -f "$S/shots/done.txt" "$S/shots/failures.txt"
one() { # variant car scenario script smoke delay
  local variant=$1 car=$2 name=$3 script=$4 smoke=$5 delay=$6 bin=./build/racer
  [ "$variant" = before ] && bin=$S/racer-before
  local tag=$variant-c$car-$name
  timeout 90 "$bin" --background --window 960 540 --vehicle-library "$LIB" --vehicle "$car" \
    --review-script "$S/$script.script" --smoke "$smoke" --screenshot-delay "$delay" \
    --screenshot "$S/shots/$tag.ppm" --profile "/tmp/racer-cam-$tag.txt" --no-diagnostics \
    > "$S/shots/$tag.log" 2>&1 || echo "FAILED $tag" >> "$S/shots/failures.txt"
  rm -f "/tmp/racer-cam-$tag.txt"
}
export -f one
variants=${1:-both}; [ "$variants" = both ] && variants="before after"
for car in ${CARS:-0 2 7 16}; do for v in $variants; do
  echo "$v $car cruise cruise 7 5.2"
  echo "$v $car launch launch 5 2.6"
  echo "$v $car slide slide 9 6.8"
  echo "$v $car brake brake 9 7.4"
  echo "$v $car donut donut 12 6.0"
  echo "$v $car slide2 slide2 12 8.6"
done; done | xargs -P "${JOBS:-4}" -L 1 bash -c 'one $0 $1 $2 $3 $4 $5'
echo done > "$S/shots/done.txt"

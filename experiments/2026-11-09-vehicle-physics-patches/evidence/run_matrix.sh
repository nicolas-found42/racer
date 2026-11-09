#!/bin/bash
cd /Users/nicolas/Documents/github/reverse-engineering/games/racer
S=/private/tmp/claude-501/-Users-nicolas--claude-spares-spare-GIx463/46ac7067-7923-4395-9c12-a7a43dddd85a/scratchpad
OUT=$S/matrix
LIB=assets/local/vehicles/catalog.racer
run() { # name scenarioArgs...
  local name=$1; shift
  timeout 90 ./build/racer --vehicle-library $LIB "$@" --screenshot $OUT/$name.ppm --profile /tmp/racer-matrix-profile-$$.txt --no-diagnostics > $OUT/$name.log 2>&1 || echo "FAILED $name" >> $OUT/failures.txt
}
for car in 0 2 7 8 12 16; do
  for view in rear left front elevated; do
    run ramp-c$car-$view --vehicle $car --world-mesh $S/ramp.gltf --follow-ground --start-at 0 -12 0 --camera-view $view --camera-distance 9 --smoke 6 --autodrive --screenshot-delay 4.6
  done
  for view in left front; do
    run brake-c$car-$view --vehicle $car --camera-view $view --camera-distance 8 --smoke 12 --autodrive --screenshot-delay 10.5
  done
done
for car in 0 7 16; do
  for view in rear right; do
    run corner-c$car-$view --vehicle $car --camera-view $view --camera-distance 9 --smoke 8 --autodrive --autodrive-left --screenshot-delay 6.5
  done
done
echo done > $OUT/done.txt

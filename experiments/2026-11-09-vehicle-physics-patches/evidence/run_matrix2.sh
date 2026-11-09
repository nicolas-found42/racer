#!/bin/bash
cd /Users/nicolas/Documents/github/reverse-engineering/games/racer
S=/private/tmp/claude-501/-Users-nicolas--claude-spares-spare-GIx463/46ac7067-7923-4395-9c12-a7a43dddd85a/scratchpad; OUT=$S/matrix; LIB=assets/local/vehicles/catalog.racer
run() { local name=$1; shift
  timeout 90 ./build/racer --vehicle-library $LIB "$@" --screenshot $OUT/$name.ppm --profile /tmp/racer-matrix2-$$.txt --no-diagnostics > $OUT/$name.log 2>&1 || echo "FAILED $name" >> $OUT/failures.txt; }
for car in 0 2 7 8 12 16; do
  for view in left front; do
    run brake-c$car-$view --vehicle $car --camera-view $view --camera-distance 8 --review-script $S/brake.script --smoke 10 --screenshot-delay 7.4
  done
  for view in rear right elevated; do
    run corner-c$car-$view --vehicle $car --camera-view $view --camera-distance 8 --review-script $S/corner.script --smoke 9 --screenshot-delay 6.6
  done
done
echo done > $OUT/done.txt

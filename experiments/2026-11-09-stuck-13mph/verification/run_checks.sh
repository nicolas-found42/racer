#!/usr/bin/env bash
set -euo pipefail
verification_dir=$(cd -- "$(dirname -- "$0")" && pwd)
source_dir=${1:-"$verification_dir/../src"}
build_dir=$(mktemp -d)
trap 'rm -rf -- "$build_dir"' EXIT
# Copy exactly the translation units required by these headless checks. The
# recovered reference headers and the two stand-ins live ONLY in this temporary
# build; they are never installed over the application headers in src/.
for file in simulation.cpp simulation.h setup.cpp setup.h; do
  cp -- "$source_dir/$file" "$build_dir/$file"
done
for file in vehicle_geometry.cpp vehicle_geometry.h tyre_contact.h test_session.cpp test_session.h surface_follow.h; do
  cp -- "$verification_dir/reference/$file" "$build_dir/$file"
done
cp -- "$verification_dir/stubs/world_scale.h" "$verification_dir/stubs/mesh_asset.h" "$build_dir/"
compiler=${CXX:-g++}
flags=(-std=c++20 -O2 -Wall -Wextra -Wpedantic -Werror -I"$build_dir")
if [[ ${SANITIZE:-0} == 1 ]]; then
  flags+=(-O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer)
  export ASAN_OPTIONS=${ASAN_OPTIONS:-detect_leaks=0}
fi
printf '%s\n' 'Headless validation: current simulation/setup, recovered physics dependencies, validation-only mesh/world stand-ins.'
"$compiler" "${flags[@]}" "$verification_dir/../tests/transmission_checks.cpp" \
  "$build_dir/simulation.cpp" "$build_dir/setup.cpp" \
  "$build_dir/vehicle_geometry.cpp" -o "$build_dir/transmission_checks"
"$build_dir/transmission_checks"
"$compiler" "${flags[@]}" "$verification_dir/prior_physics_regression.cpp" \
  "$build_dir/simulation.cpp" "$build_dir/setup.cpp" \
  "$build_dir/vehicle_geometry.cpp" "$build_dir/test_session.cpp" \
  -o "$build_dir/prior_physics_regression"
"$build_dir/prior_physics_regression"

#!/usr/bin/env bash
set -euo pipefail
physics_source_dir=${1:?Usage: bash verification/run_tests.sh /absolute/path/to/patched/source/directory}
verification_dir=$(cd -- "$(dirname -- "$0")" && pwd)
physics_build_dir=$(mktemp -d)
trap 'rm -rf -- "$physics_build_dir"' EXIT
# Deliberately isolate the supplied translation units. The two missing project
# headers are test stand-ins, never production replacements or application ABI tests.
for file in simulation.h simulation.cpp setup.h setup.cpp vehicle_geometry.h vehicle_geometry.cpp surface_follow.h tyre_contact.h test_session.h test_session.cpp; do
  cp -- "$physics_source_dir/$file" "$physics_build_dir/$file"
done
cp -- "$verification_dir/stubs/world_scale.h" "$verification_dir/stubs/mesh_asset.h" "$physics_build_dir/"
physics_compiler=${CXX:-g++}
physics_flags=(-std=c++20 -O2 -Wall -Wextra -Wpedantic -Werror -I"$physics_build_dir")
if [[ ${SANITIZE:-0} == 1 ]]; then
  physics_flags+=(-O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer)
  # LeakSanitizer cannot enumerate processes in the hosted ptrace environment.
  export ASAN_OPTIONS=${ASAN_OPTIONS:-detect_leaks=0}
fi
for suite in physics_regression tyre_properties dynamic_geometry; do
  "$physics_compiler" "${physics_flags[@]}" "$verification_dir/$suite.cpp" \
    "$physics_build_dir/simulation.cpp" "$physics_build_dir/setup.cpp" \
    "$physics_build_dir/vehicle_geometry.cpp" "$physics_build_dir/test_session.cpp" \
    -o "$physics_build_dir/$suite"
  "$physics_build_dir/$suite"
done

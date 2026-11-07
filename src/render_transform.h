#pragma once
#include <bx/math.h>
namespace racer {
// Simulation heading is clockwise from +Z toward +X. bx mtxSRT uses
// the opposite Y rotation sign. Keep this conversion at the render boundary.
// Shared by the car mesh and directional gate mesh; local nose is +Z.
inline void worldTransform(float *matrix, double heading, double x, double z,
                           float width = 1, float height = 1) {
  bx::mtxSRT(matrix, width, height, 1, 0, float(-heading), 0, float(x), 0,
             float(z));
}
}

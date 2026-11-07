#pragma once
namespace racer::worldScale {
// One world coordinate unit is one meter. Authored grid dimensions, kept
// separate from measured source-game/manufacturer vehicle dimensions.
inline constexpr double metersPerUnit=1;
inline constexpr double halfExtent=500;
inline constexpr double blockSpacing=100;
inline constexpr double laneWidth=3;
inline constexpr unsigned lanes=4;
inline constexpr double roadWidth=laneWidth*lanes;
inline constexpr double parkingBayWidth=2.5,parkingBayLength=5.5;
inline constexpr double referencePersonHeight=1.75;
}

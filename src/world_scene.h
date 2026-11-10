#pragma once
#include "mesh_asset.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <vector>

namespace racer::city {
// Original authored scenery geometry. Optional palm UVs address separately
// prepared local foliage; donor geometry, scale and shader behavior are
// unknown.
struct Point {
  float x, y, z;
};
inline uint32_t rgb(unsigned r, unsigned g, unsigned b) {
  return 0xff000000u | r | (g << 8) | (b << 16);
}
inline void triangle(std::vector<AssetVertex> &mesh, Point a, Point b, Point c,
                     uint32_t color, float roughness = .95f,
                     float surface = 0) {
  const Point u{b.x - a.x, b.y - a.y, b.z - a.z},
      v{c.x - a.x, c.y - a.y, c.z - a.z};
  Point n{u.y * v.z - u.z * v.y, u.z * v.x - u.x * v.z, u.x * v.y - u.y * v.x};
  const float length = std::sqrt(n.x * n.x + n.y * n.y + n.z * n.z);
  if (length < .00001f)
    return;
  n = {n.x / length, n.y / length, n.z / length};
  for (const auto p : {a, b, c}) {
    AssetVertex vertex{p.x, p.y, p.z, color, roughness, surface};
    vertex.nx = n.x;
    vertex.ny = n.y;
    vertex.nz = n.z;
    mesh.push_back(vertex);
  }
}
inline void quad(std::vector<AssetVertex> &m, Point a, Point b, Point c,
                 Point d, uint32_t color, float roughness = .95f,
                 float surface = 0) {
  triangle(m, a, b, c, color, roughness, surface);
  triangle(m, a, c, d, color, roughness, surface);
}
inline void box(std::vector<AssetVertex> &m, float x, float y, float z, float w,
                float h, float d, uint32_t color, float roughness = .95f,
                float surface = 0) {
  const float l = x - w * .5f, r = x + w * .5f, b = y, t = y + h,
              f = z - d * .5f, k = z + d * .5f;
  quad(m, {l, b, f}, {l, t, f}, {r, t, f}, {r, b, f}, color, roughness,
       surface);
  quad(m, {r, b, k}, {r, t, k}, {l, t, k}, {l, b, k}, color, roughness,
       surface);
  quad(m, {l, b, k}, {l, t, k}, {l, t, f}, {l, b, f}, color, roughness,
       surface);
  quad(m, {r, b, f}, {r, t, f}, {r, t, k}, {r, b, k}, color, roughness,
       surface);
  quad(m, {l, t, f}, {l, t, k}, {r, t, k}, {r, t, f}, color, roughness,
       surface);
  quad(m, {l, b, k}, {l, b, f}, {r, b, f}, {r, b, k}, color, roughness,
       surface);
}
inline void pole(std::vector<AssetVertex> &m, Point a, Point b, float radius,
                 uint32_t color, int sides = 7) {
  Point axis{b.x - a.x, b.y - a.y, b.z - a.z};
  const float length =
      std::sqrt(axis.x * axis.x + axis.y * axis.y + axis.z * axis.z);
  if (length < .001f)
    return;
  axis = {axis.x / length, axis.y / length, axis.z / length};
  Point u = std::abs(axis.y) < .9f ? Point{-axis.z, 0, axis.x} : Point{1, 0, 0};
  const float ul = std::sqrt(u.x * u.x + u.y * u.y + u.z * u.z);
  u = {u.x / ul, u.y / ul, u.z / ul};
  const Point v{axis.y * u.z - axis.z * u.y, axis.z * u.x - axis.x * u.z,
                axis.x * u.y - axis.y * u.x};
  for (int i = 0; i < sides; ++i) {
    const float q = float(i) * 6.2831853f / float(sides),
                n = float(i + 1) * 6.2831853f / float(sides);
    const Point s{radius * (u.x * std::cos(q) + v.x * std::sin(q)),
                  radius * (u.y * std::cos(q) + v.y * std::sin(q)),
                  radius * (u.z * std::cos(q) + v.z * std::sin(q))};
    const Point t{radius * (u.x * std::cos(n) + v.x * std::sin(n)),
                  radius * (u.y * std::cos(n) + v.y * std::sin(n)),
                  radius * (u.z * std::cos(n) + v.z * std::sin(n))};
    quad(m, {a.x + s.x, a.y + s.y, a.z + s.z},
         {a.x + t.x, a.y + t.y, a.z + t.z}, {b.x + t.x, b.y + t.y, b.z + t.z},
         {b.x + s.x, b.y + s.y, b.z + s.z}, color);
    triangle(m, b, {b.x + s.x, b.y + s.y, b.z + s.z},
             {b.x + t.x, b.y + t.y, b.z + t.z}, color);
  }
}
inline void palm(std::vector<AssetVertex> &m, float x, float z, float height,
                 unsigned variant, bool textured = false) {
  const float bend = .5f + float(variant % 3) * .3f;
  pole(m, {x, .25f, z}, {x + bend, height, z + .35f}, .18f, rgb(99, 83, 63), 7);
  if (textured) {
    // Authored metre-scale crown; the texture supplies frond silhouettes and
    // color. Three crossed planes are visible from either side without culling.
    const Point crown{x + bend, height, z + .35f};
    constexpr std::array<std::array<float, 2>, 6> uv{
        {{0, 7}, {1, 7}, {1, 6}, {0, 7}, {1, 6}, {0, 6}}};
    for (int i = 0; i < 3; ++i) {
      const float angle = float(i) * 1.04719755f + float(variant) * .31f;
      const float dx = std::cos(angle) * 3.5f, dz = std::sin(angle) * 3.5f;
      const size_t first = m.size();
      quad(m, {crown.x - dx, height - 3, crown.z - dz},
           {crown.x + dx, height - 3, crown.z + dz},
           {crown.x + dx, height + 2.5f, crown.z + dz},
           {crown.x - dx, height + 2.5f, crown.z - dz}, rgb(255, 255, 255));
      for (size_t vertex = 0; vertex < uv.size(); ++vertex) {
        m[first + vertex].u = uv[vertex][0];
        m[first + vertex].v = uv[vertex][1];
      }
    }
    return;
  }
  for (int i = 0; i < 8; ++i) {
    const float a = float(i) * .785398f + float(variant) * .31f;
    const Point crown{x + bend, height, z + .35f};
    const Point tip{crown.x + std::cos(a) * 3.5f, height - 1.3f,
                    crown.z + std::sin(a) * 3.5f};
    const Point mid{crown.x + std::cos(a) * 1.7f, height + .35f,
                    crown.z + std::sin(a) * 1.7f};
    const Point left{mid.x - std::sin(a) * .65f, mid.y - .15f,
                     mid.z + std::cos(a) * .65f};
    const Point right{mid.x + std::sin(a) * .65f, mid.y - .15f,
                      mid.z - std::cos(a) * .65f};
    const auto green = rgb(52 + variant % 12, 77 + unsigned(i % 3) * 8, 46);
    quad(m, crown, left, tip, right, green);
    quad(m, right, tip, left, crown, green);
  }
}
inline void tree(std::vector<AssetVertex> &m, float x, float z,
                 unsigned variant) {
  pole(m, {x, .2f, z}, {x, 3.8f, z}, .2f, rgb(79, 67, 53));
  for (int tier = 0; tier < 3; ++tier) {
    const float y = 3.f + float(tier) * 1.1f, r = 2.4f - float(tier) * .35f;
    for (int i = 0; i < 8; ++i) {
      const float a = float(i) * .785398f, b = float(i + 1) * .785398f;
      const auto c = rgb(49 + variant % 13, 73 + unsigned(i % 3) * 7, 45);
      triangle(m, {x, y + 2.1f, z},
               {x + std::cos(b) * r, y, z + std::sin(b) * r},
               {x + std::cos(a) * r, y, z + std::sin(a) * r}, c);
    }
  }
}
// Street tree: brown trunk plus crossed leaf cards. Cards carry local
// coordinates in the tangent (tx,ty) and surface id -1 (distinct from every
// atlas/foliage id); the shaders cut them into noise-clumped foliage. Authored
// geometry.
inline void leafCard(std::vector<AssetVertex> &m, Point c, float yaw,
                     float tilt, float size, uint32_t color) {
  const float cy = std::cos(yaw), sy = std::sin(yaw), ct = std::cos(tilt),
              st = std::sin(tilt);
  const Point right{cy, 0, -sy}, up{sy * st, ct, cy * st};
  const float qx[4] = {-1, 1, 1, -1}, qy[4] = {-1, -1, 1, 1};
  AssetVertex v[4];
  for (int i = 0; i < 4; ++i) {
    v[i] = AssetVertex{c.x + (right.x * qx[i] + up.x * qy[i]) * size * .5f,
                       c.y + (right.y * qx[i] + up.y * qy[i]) * size * .5f,
                       c.z + (right.z * qx[i] + up.z * qy[i]) * size * .5f,
                       color,
                       1.f,
                       -1.f};
    Point n{right.y * up.z - right.z * up.y, right.z * up.x - right.x * up.z,
            right.x * up.y - right.y * up.x};
    v[i].nx = n.x;
    v[i].ny = n.y;
    v[i].nz = n.z;
    v[i].tx = qx[i] * .5f + .5f;
    v[i].ty = qy[i] * .5f + .5f;
  }
  for (int idx : {0, 1, 2, 0, 2, 3})
    m.push_back(v[idx]);
}
inline void streetTree(std::vector<AssetVertex> &m, float x, float z,
                       unsigned variant) {
  pole(m, {x, .18f, z}, {x, 3.4f, z}, .16f, rgb(86, 70, 54), 5);
  unsigned state = variant * 2654435761u + 12345u;
  auto rnd = [&] {
    state = state * 1664525u + 1013904223u;
    return float((state >> 8) & 0xffff) / 65535.f;
  };
  const float height = 5.4f + rnd() * 1.2f, spread = 2.2f + rnd() * .6f;
  for (int i = 0; i < 12; ++i) {
    const float a = rnd() * 6.2832f, r = std::sqrt(rnd()) * spread * .8f,
                h = (rnd() - .35f) * spread * .9f;
    const uint32_t color =
        rgb(46 + unsigned(rnd() * 26), 88 + unsigned(rnd() * 30),
            38 + unsigned(rnd() * 20));
    leafCard(m, {x + std::cos(a) * r, height + h, z + std::sin(a) * r},
             rnd() * 6.2832f, (rnd() - .5f) * 1.1f, spread * 1.55f, color);
  }
}
// Street lamp for the night-lighting grid; the shader derives the same
// positions analytically (visual_shader.h lampLight). Pole at 9.0 m from the
// road centre, arm head at 7.7 m, head surface id -2 marks an emitter.
// Authored.
inline void gridLamp(std::vector<AssetVertex> &m, float roadAxis, float along,
                     float side, bool alongZ) {
  const auto metal = rgb(73, 78, 77);
  const float pole = roadAxis + side * 9.0f, head = roadAxis + side * 7.7f;
  auto place = [&](float lat, float y, float sx, float sy, float sz_lat,
                   float sz_along, uint32_t color, float surface) {
    if (alongZ)
      box(m, lat, y, along, sz_lat, sy, sz_along, color, .9f, surface);
    else
      box(m, along, y, lat, sz_along, sy, sz_lat, color, .9f, surface);
    (void)sx;
  };
  place(pole, 0, 0, 8.2f, .16f, .16f, metal, 0);
  place((pole + head) * .5f, 7.9f, 0, .12f, std::abs(pole - head) + .1f, .12f,
        metal, 0);
  place(head, 7.78f, 0, .1f, .9f, .45f, rgb(239, 224, 177), -2.f);
}
inline void gridLamps(std::vector<AssetVertex> &m) {
  for (int road = -2; road <= 2; ++road)
    for (float side : {-1.f, 1.f})
      for (int k = -8; k < 8; ++k) {
        if (((k % 4) + 4) % 4 == 0)
          continue;
        const float along = 25.f * float(k) + 12.5f;
        gridLamp(m, 100.f * float(road), along, side, true);
        gridLamp(m, 100.f * float(road), along, side, false);
      }
}
// Roadside neon pylon: dark pole with two emitter blades (surface id -2, own
// colour). By day the blades are plain coloured boxes; at night the shader
// makes them hot emitters. Authored signage.
inline void neonPylon(std::vector<AssetVertex> &m, float x, float z,
                      unsigned variant, bool alongX) {
  const uint32_t colors[3][2] = {{rgb(255, 40, 170), rgb(40, 220, 255)},
                                 {rgb(255, 150, 30), rgb(255, 50, 60)},
                                 {rgb(60, 255, 160), rgb(120, 90, 255)}};
  const auto metal = rgb(52, 55, 60);
  box(m, x, 0, z, .4f, .3f, .4f, metal);
  pole(m, {x, .3f, z}, {x, 6.6f, z}, .1f, metal, 5);
  const auto &c = colors[variant % 3];
  const float w = alongX ? 1.9f : .3f, d = alongX ? .3f : 1.9f;
  box(m, x, 4.4f, z, w, 1.1f, d, c[0], .9f, -2.f);
  box(m, x, 5.7f, z, w * .9f, .9f, d * .9f, c[1], .9f, -2.f);
}
inline void streetlight(std::vector<AssetVertex> &m, float x, float z,
                        bool alongX) {
  const auto metal = rgb(73, 78, 77);
  box(m, x, .15f, z, .5f, .35f, .5f, metal);
  pole(m, {x, .4f, z}, {x, 8.2f, z}, .09f, metal);
  const Point end{x + (alongX ? 1.4f : 0), 8.1f, z + (alongX ? 0 : 1.4f)};
  pole(m, {x, 8.2f, z}, end, .075f, metal);
  box(m, end.x, 7.97f, end.z, alongX ? .9f : .4f, .13f, alongX ? .4f : .9f,
      rgb(154, 153, 137));
  box(m, end.x, 7.95f, end.z, alongX ? .72f : .3f, .025f, alongX ? .3f : .72f,
      rgb(239, 224, 177));
}
// Wall sign board: a thin raised panel carrying the SLRR long-logo sheet
// (surface id 13). The shader reads the board UV from tangent.xy, so tx,ty
// are set per vertex here; v stays the surface id and u the roughness.
inline void signBoard(std::vector<AssetVertex> &m, Point a, Point b, Point c,
                      Point d) {
  const size_t first = m.size();
  quad(m, a, b, c, d, rgb(212, 207, 197), .8f, 13);
  const std::array<std::array<float, 2>, 6> uv{
      {{0, 0}, {1, 0}, {1, 1}, {0, 0}, {1, 1}, {0, 1}}};
  for (size_t vertex = 0; vertex < uv.size(); ++vertex) {
    m[first + vertex].tx = uv[vertex][0];
    m[first + vertex].ty = uv[vertex][1];
  }
}
// Small deterministic LCG for authored block variation (same pattern as the
// street-tree scatter); identical seeds rebuild identical blocks.
struct CityRng {
  unsigned state;
  explicit CityRng(unsigned seed) : state(seed * 2654435761u + 12345u) {}
  float next() {
    state = state * 1664525u + 1013904223u;
    return float((state >> 8) & 0xffff) / 65535.f;
  }
  float range(float lo, float hi) { return lo + (hi - lo) * next(); }
  int span(int lo, int hi) {
    return lo + int(next() * float(hi - lo + 1)) % (hi - lo + 1);
  }
};
// Street-wall parcel of the console-density re-bake: one attached row building
// fronting a block edge. Parcels share party planes (no side setbacks), so an
// edge reads as the continuous facade wall the MCLA/GT4 reference crops show.
// All wall art comes from the qualified facade atlas: window-grid sheets
// (ids 11/12, one 3.15 m storey per shader row) at three storeys and up,
// siding/concrete below, the storefront band (id 9) or shop glazing (id 14) at
// street level and a backlit sign board (id 13) on some fronts. Authored
// layout; native city placement remains unknown.
inline void streetParcel(std::vector<AssetVertex> &m, float x, float z, float w,
                         float d, int floors, unsigned style, bool alongX,
                         float frontDir) {
  const float h = 3.9f + float(floors) * 3.15f;
  const std::array<uint32_t, 6> walls{rgb(174, 157, 132), rgb(144, 143, 133),
                                      rgb(185, 174, 154), rgb(130, 124, 113),
                                      rgb(162, 137, 117), rgb(190, 182, 163)};
  const auto wall = walls[style % walls.size()], trim = rgb(117, 115, 106);
  const bool windowGrid = floors >= 3;
  box(m, x, .16f, z, alongX ? w : d, h, alongX ? d : w, wall, .9f,
      windowGrid ? (style % 2 == 0 ? 11.f : 12.f)
                 : (style % 3 == 0 ? 8.f : 10.f));
  // Cornice plus one rooftop unit: silhouette variation without per-floor
  // geometry, the wall sheets already carry the window rows.
  box(m, x, h + .16f, z, (alongX ? w : d) + .5f, .3f, (alongX ? d : w) + .5f,
      trim);
  if (style % 3 == 0)
    box(m, x + float(style % 5 - 2) * 2.f, h + .46f,
        z + (alongX ? float(style % 3 - 1) * 3.f : 0.f), alongX ? 3.f : 2.2f,
        1.2f, alongX ? 2.2f : 3.f, rgb(130, 135, 132));
  // Street-level band on the front face only; the rear stays a blank party
  // wall like the reference row blocks.
  const float front =
      (alongX ? z : x) + frontDir * ((alongX ? d : w) * .5f + .045f);
  const float bandW = (alongX ? w : d) * .8f;
  if (alongX)
    box(m, x, .8f, front, bandW, 2.5f, .08f, rgb(45, 66, 71), .18f,
        style % 4 == 3 ? 14.f : 9.f);
  else
    box(m, front, .8f, z, .08f, 2.5f, bandW, rgb(45, 66, 71), .18f,
        style % 4 == 3 ? 14.f : 9.f);
  if (style % 3 == 1) { // sun shade over the band
    if (alongX)
      box(m, x, 3.45f, front + frontDir * .55f, bandW * .9f, .14f, 1.1f,
          style % 2 ? rgb(155, 114, 77) : rgb(87, 115, 102));
    else
      box(m, front + frontDir * .55f, 3.45f, z, 1.1f, .14f, bandW * .9f,
          style % 2 ? rgb(155, 114, 77) : rgb(87, 115, 102));
  }
  if (style % 3 == 2 && (alongX ? w : d) >= 9) { // backlit board above the band
    const float signW = std::min((alongX ? w : d) * .55f, 6.5f),
                signH = signW / 16.f, signY = 3.85f;
    if (alongX) {
      const float sx = x - signW * .5f;
      const Point a{sx, signY, front}, b{sx + signW, signY, front},
          c{sx + signW, signY + signH, front}, e{sx, signY + signH, front};
      if (frontDir > 0)
        signBoard(m, a, b, c, e);
      else
        signBoard(m, b, a, e, c);
    } else {
      const float sz = z - signW * .5f;
      const Point a{front, signY, sz}, b{front, signY, sz + signW},
          c{front, signY + signH, sz + signW}, e{front, signY + signH, sz};
      if (frontDir > 0)
        signBoard(m, b, a, e, c);
      else
        signBoard(m, a, b, c, e);
    }
  }
}
// Interior volume behind the street walls: a mid-rise core on most blocks, a
// low courtyard podium on the rest. Window-grid walls, concrete penthouse.
inline void blockCore(std::vector<AssetVertex> &m, float x, float z, float w,
                      float d, int floors, unsigned style) {
  const float h = 3.9f + float(floors) * 3.15f;
  box(m, x, .16f, z, w, h, d, rgb(144, 143, 133), .9f,
      style % 2 == 1 ? 12.f : 11.f);
  box(m, x, h + .16f, z, w + .5f, .3f, d + .5f, rgb(117, 115, 106));
  box(m, x, h + .46f, z, w * .45f, 2.2f, d * .45f, rgb(130, 135, 132));
  if (style % 3 == 0)
    pole(m, {x, h + 2.66f, z}, {x, h + 6.f, z}, .12f, rgb(94, 96, 92), 5);
}
// Horizon tower: window-grid walls only (the sheets carry the window rows),
// varied crowns so the skyline band reads as mixed construction. Authored
// placement inside the road grid, heights bounded by the world extent.
inline void ringTower(std::vector<AssetVertex> &m, float x, float z, float w,
                      float d, float h, unsigned style) {
  box(m, x, .05f, z, w, h, d,
      rgb(127 + unsigned(style % 3) * 13, 135 + unsigned(style % 4) * 6,
          135 + unsigned(style % 2) * 10),
      .9f, style % 2 == 0 ? 11.f : 12.f);
  box(m, x, h, z, w + 1, .5f, d + 1, rgb(109, 119, 121));
  if (style % 3 == 0)
    box(m, x, h + .5f, z, w * .5f, 2.6f, d * .5f, rgb(113, 124, 126));
  else if (style % 3 == 1)
    box(m, x, h + .5f, z, w * .3f, h * .25f, d * .3f, rgb(109, 119, 121));
  if (style % 4 == 0)
    pole(m, {x, h + .5f, z}, {x, h + 4.5f, z}, .12f, rgb(94, 96, 92), 5);
}
inline float terrainNoise(float x, float z) {
  const int ix = int(std::floor(x)), iz = int(std::floor(z));
  auto value = [](int a, int b) {
    uint32_t n =
        uint32_t(a) * 0x8da6b343u ^ uint32_t(b) * 0xd8163841u ^ 0xcb1ab31fu;
    n ^= n >> 16;
    n *= 0x7feb352du;
    n ^= n >> 15;
    n *= 0x846ca68bu;
    n ^= n >> 16;
    return float(n & 65535u) / 65535.f;
  };
  float u = x - float(ix), v = z - float(iz);
  u = u * u * (3 - 2 * u);
  v = v * v * (3 - 2 * v);
  return std::lerp(std::lerp(value(ix, iz), value(ix + 1, iz), u),
                   std::lerp(value(ix, iz + 1), value(ix + 1, iz + 1), u), v);
}
inline float terrainHeight(float x, float z) {
  float rise = std::clamp((z - 560) / 220, 0.f, 1.f);
  rise = rise * rise * (3 - 2 * rise);
  const float broad = terrainNoise(x * .0026f, z * .0026f);
  const float n = terrainNoise(x * .004f + 17, z * .004f - 8);
  const float ridge = 4 * n * (1 - n);
  const float detail = terrainNoise(x * .009f, z * .009f);
  return -1 + rise * (18 + 55 * broad + 25 * ridge + 8 * detail);
}
inline void terrain(std::vector<AssetVertex> &m, int quarterTurns = 0,
                    int columns = 120, int rows = 30) {
  // Authored continuous foothills outside the driving boundary. Shared grid
  // points and derivative normals remove the old repeating pyramid silhouettes.
  // quarterTurns rotates the whole patch about the origin so the other three
  // horizons get relief too (coarser grids there: they are only seen as distant
  // silhouettes).
  const float sx = 3200.f / float(columns), sz = 880.f / float(rows);
  const float c = std::cos(float(quarterTurns) * 1.5707963f),
              sn = std::sin(float(quarterTurns) * 1.5707963f);
  auto point = [&](int x, int z) {
    const float px = -1600 + float(x) * sx, pz = 560 + float(z) * sz;
    return Point{px, terrainHeight(px, pz), pz};
  };
  auto emit = [&](Point a, Point b, Point cc) {
    const size_t first = m.size();
    triangle(m, a, b, cc, rgb(112, 119, 96), .98f, 3);
    for (size_t i = first; i < m.size(); ++i) {
      auto &v = m[i];
      if (columns >= 120) { // fine patch: derivative normals; coarse patches
                            // keep their flat face normals
        const float dx =
            (terrainHeight(v.x + sx, v.z) - terrainHeight(v.x - sx, v.z)) /
            (2 * sx);
        const float dz =
            (terrainHeight(v.x, v.z + sz) - terrainHeight(v.x, v.z - sz)) /
            (2 * sz);
        const float length = std::sqrt(dx * dx + 1 + dz * dz);
        v.nx = -dx / length;
        v.ny = 1 / length;
        v.nz = -dz / length;
      }
      if (quarterTurns) { // rotate position and normal into place after the
                          // local derivatives are known
        const float x = v.x, z = v.z, nx = v.nx, nz = v.nz;
        v.x = x * c - z * sn;
        v.z = x * sn + z * c;
        v.nx = nx * c - nz * sn;
        v.nz = nx * sn + nz * c;
      }
    }
  };
  for (int z = 0; z < rows; ++z)
    for (int x = 0; x < columns; ++x) {
      const auto a = point(x, z), b = point(x + 1, z), cc = point(x + 1, z + 1),
                 d = point(x, z + 1);
      emit(a, d, cc);
      emit(a, cc, b);
    }
}
} // namespace racer::city

namespace racer {
// lampFirst/lampCount (optional) report the contiguous vertex range holding the
// lamp posts and neon pylons, so the renderer can repeat just that range at the
// 400 m tile offsets used for the scenery.
inline std::vector<AssetVertex> buildCityScene(bool texturedPalms = false,
                                               bool authoredBuildings = true,
                                               size_t *lampFirst = nullptr,
                                               size_t *lampCount = nullptr) {
  std::vector<AssetVertex> m;
  m.reserve(200000);
  using namespace city;
  // Four by four varied blocks form the detailed central district. Every block
  // begins beyond 7m from either road centre; roads remain 12m wide at 100m
  // spacing.
  for (int ix = -2; ix < 2; ++ix)
    for (int iz = -2; iz < 2; ++iz) {
      const float x = float(ix) * 100 + 50, z = float(iz) * 100 + 50;
      const unsigned seed = unsigned((ix + 3) * 31 + (iz + 3) * 17);
      box(m, x, .01f, z, 85.6f, .15f, 85.6f,
          authoredBuildings ? rgb(161, 157, 145) : rgb(74, 91, 53), .9f,
          authoredBuildings ? 2.f : 0.f);
      if (!authoredBuildings) {
        for (float side : {-1.f, 1.f}) {
          box(m, x + side * 40.3f, .16f, z, 4.5f, .025f, 85.6f,
              rgb(166, 162, 148), .9f, 2);
          box(m, x, .16f, z + side * 40.3f, 85.6f, .025f, 4.5f,
              rgb(166, 162, 148), .9f, 2);
          for (float row : {-27.f, 0.f, 27.f}) {
            // Broad front courts connect either native garage/entry placement
            // to the existing sidewalk without changing the flat driving grid.
            box(m, x + side * 35.2f, .16f, z + row, 7.3f, .03f, 18,
                rgb(156, 153, 140), .9f, 2);
            box(m, x + side * 35.2f, .19f, z + row + 11.6f, 6.4f, .52f, .65f,
                rgb(49, 70, 39));
            for (int picket = 0; picket < 8; ++picket)
              box(m, x + side * (32.6f + float(picket) * .72f), .18f,
                  z + row - 12, .09f, .9f, .09f, rgb(172, 164, 140));
            box(m, x + side * 35.2f, .68f, z + row - 12, 5.5f, .12f, .1f,
                rgb(158, 150, 128));
          }
        }
      }
      // Layered perimeter curb and paving seams establish human-scale edges.
      for (float side : {-1.f, 1.f}) {
        box(m, x + side * 42.55f, .04f, z, .5f, .2f, 85.6f, rgb(195, 189, 171));
        box(m, x, .04f, z + side * 42.55f, 85.6f, .2f, .5f, rgb(195, 189, 171));
        for (int j = -6; j <= 6; ++j) {
          box(m, x + float(j) * 6, .164f, z + side * 40.2f, .035f, .006f, 3.8f,
              rgb(128, 127, 117));
          box(m, x + side * 40.2f, .164f, z + float(j) * 6, 3.8f, .006f, .035f,
              rgb(128, 127, 117));
        }
      }
      // Console-density block (measured against the MCLA/GT4 facade crops):
      // a continuous party-walled frontage -- four corner parcels plus two
      // mid parcels per edge, fronts at 36 m from the block centre (14 m
      // clear of the road) -- around one interior mid-rise core or low
      // podium. Authored layout; source runtime placement is unknown.
      if (authoredBuildings) {
        CityRng rng(seed * 97u + 13u);
        for (int lot = 0; lot < 4; ++lot) { // corner parcels
          const float sx = (lot & 1) ? 1.f : -1.f, sz = (lot & 2) ? 1.f : -1.f;
          const unsigned style = seed * 7u + unsigned(lot) * 5u + 1u;
          const bool alongX = (seed + unsigned(lot)) % 2 == 0;
          streetParcel(m, x + sx * 27.5f, z + sz * 27.5f, 18.f, 18.f,
                       rng.span(2, 6), style, alongX, alongX ? sz : sx);
        }
        for (int lot = 0; lot < 4; ++lot) { // two mid parcels per edge
          const bool alongX = (lot & 1) == 0;
          const float sign = (lot & 2) ? 1.f : -1.f;
          const float depth = rng.range(14.f, 17.f);
          for (int p = 0; p < 2; ++p) {
            const float uc = p == 0 ? -9.25f : 9.25f;
            const unsigned style =
                seed * 11u + unsigned(lot) * 5u + unsigned(p) * 3u;
            if (alongX)
              streetParcel(m, x + uc, z + sign * (36.f - depth * .5f), 18.5f,
                           depth, rng.span(2, 7), style, true, sign);
            else
              streetParcel(m, x + sign * (36.f - depth * .5f), z + uc, 18.5f,
                           depth, rng.span(2, 7), style, false, sign);
          }
        }
        if (seed % 5 != 3) // mid-rise core behind the frontage
          blockCore(m, x + rng.range(-1.5f, 1.5f), z + rng.range(-1.5f, 1.5f),
                    rng.range(22.f, 30.f), rng.range(22.f, 30.f),
                    rng.span(8, 13), seed * 3u + 7u);
        else // low courtyard podium fills the interior instead
          blockCore(m, x, z, 30.f, 26.f, 2, seed * 3u + 7u);
      }
      // Street trees on the block sidewalks, spaced clear of lamps, benches and
      // palms.
      for (float side : {-1.f, 1.f})
        for (float row : {-27.f, -3.f, 21.f}) {
          streetTree(m, x + side * 38.0f, z + row,
                     seed * 7 + unsigned(row + 30) * 3 + (side > 0 ? 1u : 0u));
          streetTree(m, x + row, z + side * 38.0f,
                     seed * 11 + unsigned(row + 30) * 5 + (side > 0 ? 2u : 0u));
        }
      for (float side : {-1.f, 1.f}) {
        streetlight(m, x + side * 37.5f, z - 37.8f, false);
        box(m, x + side * 37.2f, .18f, z + 9, 2.1f, .55f, 3.2f,
            rgb(120, 115, 99));
        if (seed % 3 == 0 && !texturedPalms)
          tree(m, x + side * 37.2f, z + 9, seed);
        else
          palm(m, x + side * 37.2f, z + 9, 7 + float(seed % 3), seed,
               texturedPalms);
        // Low benches and separated waste bins add street furniture without
        // road intrusion.
        box(m, x + side * 37.8f, .62f, z - 15, 1.6f, .12f, .55f,
            rgb(100, 82, 62));
        for (float leg : {-.55f, .55f})
          box(m, x + side * 37.8f + leg, .18f, z - 15, .08f, .44f, .45f,
              rgb(63, 67, 64));
        box(m, x + side * 37.8f, .18f, z - 18, .55f, .85f, .55f,
            rgb(70, 82, 72));
      }
    }
  // Skyline band: window-grid towers on the four horizon rows plus east/west
  // flank columns, filling the horizon the way the reference skyline crops do.
  // Walls sample the SLRR window-grid sheets world-space (the shader lights
  // hashed glass cells at night); the far rows run taller so the silhouette
  // steps up away from the district. Authored placement, never crossing the
  // grid roads or the world boundary.
  for (int i = 0; i < 48; ++i) {
    const bool flank = i >= 40;
    int gx, gz;
    if (flank) {
      static const int fx[4] = {-4, -3, 3, 4};
      gx = fx[(i - 40) % 4];
      gz = (i - 40) / 4 == 0 ? -1 : 0;
    } else {
      gx = (i % 10) - 5;
      const int row = i / 10; // rows -4,-3,3,4
      gz = row < 2 ? (row == 0 ? -4 : -3) : (row == 2 ? 3 : 4);
    }
    const float x = float(gx) * 100 + 45, z = float(gz) * 100 + 45;
    CityRng rng(unsigned(i) * 4u + 17u);
    const float far = flank || gz == -3 || gz == 3;
    const float h = far ? rng.range(18.f, 44.f) : rng.range(30.f, 64.f);
    ringTower(m, x, z, rng.range(20.f, 30.f), rng.range(22.f, 32.f), h,
              unsigned(i) * 7u + 3u);
  }
  // Foothills on the three other sides (the original +z patch is added below by
  // terrain(m)).
  for (int turn = 1; turn <= 3; ++turn)
    terrain(m, turn, 48, 12);
  const size_t lampsBegin = m.size();
  gridLamps(m);
  for (int ix = -2; ix <= 2; ++ix)
    for (int iz = -2; iz <= 2; ++iz) {
      const float cx = 100.f * float(ix), cz = 100.f * float(iz);
      const unsigned v = unsigned((ix + 3) * 5 + (iz + 3) * 3);
      neonPylon(m, cx + 10.f, cz + 10.f, v, true);
      neonPylon(m, cx - 10.f, cz - 10.f, v + 1, false);
    }
  if (lampFirst)
    *lampFirst = lampsBegin;
  if (lampCount)
    *lampCount = m.size() - lampsBegin;
  terrain(m);
  return m;
}
} // namespace racer

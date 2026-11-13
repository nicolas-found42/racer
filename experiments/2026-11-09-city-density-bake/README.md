# 2026-11-09 City block re-bake at console density
**Question:** the facade-v4 close-out left world density as the dominant console-parity
residual (low-rise grid with empty lots vs dense MCLA/GT4 canyons). Can the city block be
re-baked at console density from the qualified facade atlas, and does the result move the
measured frame statistics toward the 162-frame console reference set?

## Targets, inputs, builds
- Racer `main` @ `83c63fc` + this round's `src/world_scene.h` + `tests/world_scene_checks.cpp`
  change. Before build frozen at
  `output/base/racer` sha256 `0e2bb092…` (models/shaders copied beside it); after build
  `build/racer` sha256 `9348d3a8…`.
- Qualified facade atlas (kept, not re-made): `assets/visual-local/v4/surfaces.rgba`,
  sha256 `e61d6c16…`, 16 tiles `RCRSURF4` — window grids in tiles 8-15. Idempotence proven
  without overwriting the atlas the frames used: generated to `/tmp/atlas-check` with
  `python3 scripts/prepare_world_surfaces.py --source /Users/nicolas/Documents/github/reverse-engineering/games/raw/slrr-231/maps/textures --output /tmp/atlas-check`
  and the output sha256 equals the retained file's.
  Re-bake uses only existing surface ids 8-15; the shader/atlas domain pins are unchanged.
- Console set: `references/web2/` — a fresh 162-crop MCLA/GT4 gather (GT4 82, MCLA 80) with
  `manifest.json` (source URL, sha256, dimensions, category, pixel-derived description per
  file; 17 MiB retained). Selection rule: category quotas copied from facade-v4's
  `CATEGORY_FRAMES` (buildings_facade 32, night_street 28, day_street 26, skyline_horizon 18,
  headlights_lamps 12, wet_road 10, smoke_skid 10, crowd_props 9, other 17), choosing
  street-level driving screenshots with visible building fabric, and reporting the honest
  actual count rather than padding. Note on provenance: the 2026-11-07 comparison-matrix
  catalog was 262 images across MCLA/GT4/MC3/Juiced 2/SLRR and is no longer retained;
  facade-v4's "162 console pairs" were pairs drawn from that catalog. This round re-gathered
  a two-game (MCLA/GT4) set of exactly 162 crops to match the requested set size and game
  scope; hashes are new, so it is not provenance-identical to the old catalog.

## Density classification (jevify)
Rubric frozen in constants before data loaded: two questions per frame — `density`
(canyon | dense_open | lowrise | no_street) and `bake_target` (bool); 24k-char state cap;
escalation = reconcile every verdict below 0.7 top probability against the manifest
description (written from the pixels by the cataloguing pass) and read the frame if still
contradicted. All 162 judged, 0 failures: **canyon 31, dense_open 46, lowrise 25, no_street 60**
— 48 % of the set is urban street fabric, 46 frames are explicit density targets. 72 verdicts
were below 0.7 and all were reconciled by description; 6 were overturned where the
description plainly contradicts the label (the committed `jevify-density.json` at the
experiment root records every per-frame verdict and each override).
Consequence: console streets are dominantly dense — the pre-bake Racer low-rise grid had no
console counterpart.

## What changed in `src/world_scene.h`
- **Frontage replace, not infill.** Each block's street frontage is rebuilt as a continuous
  parcel quilt on all four sides: parcel widths 10-22 m filling the frontage, height ratios
  0.30-0.95 of block height, floor pitch 3.15 m, storefront band y∈[0.1,3.1), hashed lit
  window cells per floor, window-grid facade sheet per parcel. Roofs are flat with inset
  caps behind the parapet.
- **Mid-rise cores** in the 16 central blocks (3.9 + 13×3.15 ≈ 44.9 m, 6-8×8 m footprints,
  setback ≥ 4 m behind the street wall) instead of a single flat "wall" backdrop box; the
  flat backdrop block was deleted.
- **Old 30 ring towers replaced** by 48 towers (4×10 grid + 8 flank blocks) using the same
  parcel grammar, heights 30-64 m, window-grid walls; terrain-quarter blocks keep their
  quarter-fill share variant.
- Street trees, lamps, benches, storefront signs and lane furniture kept; road clearance,
  world boundary and foliage-domain rules unchanged.
- Vertex budget: 232,518 → 170,292 (fallback) — cheaper than the old scene despite ~5×
  facade detail because trivial tower boxes and the backdrop slab are gone.

## Verification
- `cmake --build build` clean; `ctest` **107/107**.
- `world_scene_checks` re-pinned for the new scene and mutation-checked red→green:
  `occupiedBlocks ≥ 60` (75 observed) and `tallest ≥ 30` replace the 16/15 floors, and a new
  scroll pin requires window-grid frontage in ≥ 55 distinct blocks. Compiled against the
  pre-change header the new pins fail (2 failures: 64 blocks, frontage below the floor);
  against the new header 0 failures.
- Captures: `scripts/capture_matrix.py` with `SURFACES=assets/visual-local/v4/surfaces.rgba`,
  `NO_SCENERY=1`, 37 scenarios per side (33 shared + brake-day-rear, brake-day-left,
  brake-night-rear, launch-day-left added for the smoke/skid console category), all
  `ok=True`, `output/{before,after}` 38+39 MiB.
- Sheets (`pairs_and_stats.py`): 37 before/after pairs → 7 grids; 162 after-vs-console and
  162 before-vs-console pairs → 30 grids per side; 8 `sheets/triples/<category>.jpg`
  (before | after | console reference, 4 rows each).

## Measured effect (density proxies, `summary.json`)
Proxy definitions are coarse and documented in `pairs_and_stats.py`; they are trends, not a
quality grade. `sky_upper` = sky-coloured fraction of the top 40 % band (denser walls leave
less), `facade_edges` = strong-edge fraction in the mid band (window grids/storefronts raise it).

| metric | before day | after day | console day_street | before night | after night | console night_street |
|---|---|---|---|---|---|---|
| sky_upper | .202 | .155 | .189 | .625 | .503 | .172 |
| facade_edges | .122 | .135 | .143 | .112 | .137 | .178 |
| R mean | 99.2 | 89.4 | 87.0 | 58.2 | 65.2 | 61.4 |
| saturation | .244 | .271 | .307 | .447 | .429 | .443 |

Street frames overall: sky_upper .429 → .350 (console canyon/dense .204), facade_edges
.117 → .135 (console canyon/dense .160). Direction is unambiguously toward the console set on
every proxy; day tone/saturation moved closer too (after frames carry more wall in frame, so
the day mean darkens).

## Limits
- `sky_upper` at night still reads .503 vs console .172: the Racer frames are street-level
  driving views where the canyon leaves a sky corridor, and the console crops are
  facade-focused close-ups (crop composition, not just wall height). Not yet attributed;
  next measurement needs matched camera pitch.
- Density proxies are 2-D projections; they cannot separate "more wall" from "closer wall".
- Facade art itself is unchanged (qualified atlas); wall height, window rhythm and parcel
  continuity are the only levers pulled. No new texture, sign or storefront art.
- Console crops are MCLA/GT4 only; MC3/Juiced 2 refs remain in the comparison-matrix catalog.
- 17 `other` frames (tracks, forest, cockpit) are sheeted against the nearest generic street
  frame only for set completeness and excluded from the density statistics.

## Retention
`output/` 190 MiB (37+37 frames, 67 grids, triples, both indexes, both pair files, stats) +
`references/` 17 MiB = 207 MiB total, under the 512 MiB experiment cap
(`storage-policy.json: experiment_output_bytes 536870912`). The jevify verdicts are committed
at the experiment root because `output/` is gitignored and re-judging is not free.
Canonical inputs (frozen binary, atlas) and the console crops preserved; all sheets are
re-derivable from the frames + `references/web2`.

## Next
Follow-up recorded in [2026-11-12-night-sky-attribution](../2026-11-12-night-sky-attribution/README.md): matched upward camera pitch (`0°`, `-1°`, `-6°`) **increased** `sky_upper` (`.603 -> .662 -> .677 -> .739`), showing the night sky-band gap was not a pitch artifact alone. Raising minimum corner/mid parcel floors (`4..8`/`3..8`), filling all 74 outer-ring blocks (`90` occupied blocks, `173,082` fallback vertices), and adding per-bay window hashing + night-only warm facade bounce lowered all 17 night frames `sky_upper` `.503 -> .309` and `night_street` (9 frames) `.440 -> .263` vs console `.172` (an improvement, not parity; post-hoc central-6 subset `.269 -> .177`; individual contributions of the four edits and `_sky_rule` false-positive reduction are not ablation-separated; day shader math is untouched while `loc-a-day` moved `sky .123 -> .035`, `R 107 -> 97` under the new `gx=2` ring towers). Next residual: Juiced 2 / MC3 numeric effect defaults or tail-light mesh sections. Optional source-geometry upgrade: the MCLA extraction helpers survive in `experiments/2026-11-05-mcla-vehicle/output/references/` (`mcla_lzx.py`, `mcla_resource.py`, `mcla_model.py`), so `inspect_world_resources.py` can pilot one city sector and replace crop-derived density targets with measured street-wall coverage, floor heights and block widths.

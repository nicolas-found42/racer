# 2026-11-08 Facade v4 close-out: night lighting, smoke/sparks, streaks, reflectors

**Question:** close the remaining visual-fidelity gaps G1–G4 and G8 lane items on
branch `feat/improve-racer-visual-fidelity`, with before/after + console comparison
evidence, and explicitly scope the rest.

## Targets and method

- Racer at branch head `190671a` + this round's commits, worktree
  `/Users/nicolas/.codex/worktrees/4314/racer`. Renderer build via
  `cmake --build build`, `ctest` (96/96). Captures via
  `scripts/capture_matrix.py` into this experiment's `output/{before,after,after-city,after-g3}`,
  paired and sheeted by `pairs_and_stats.py` (33 before/after pairs, 162 console
  pairs, all grids verified non-empty in the log).
- Console references: `experiments/2026-11-07-comparison-matrix/output/web2/`
  (162 named crops from MCLA / GT4 / MC3 / Juiced 2 screenshots, gathered and
  catalogued in the comparison-matrix experiment).
- REA evidence for named systems:
  `experiments/2026-11-08-juiced2-rea/README.md` (Juiced 2 `default.xex`, GT4
  CORE, MC3 XBE string tables — bloom/DOF/exposure/reflection names) and
  `experiments/2026-11-05-mcla-data/` (decoded MCLA tuning table incl.
  `LamppostLight`, `headlight` colour entries).

## Changes made this round

1. **G3 sparks:** chassis ground-contact spark particles (puff `kind 2`, warm
   emissive, short life) emitted under hard braking/cornering. Juiced 2 ships
   `sparks.cpp`; Racer previously had smoke only.
2. **G4 streak reflections:** raised wet-road streak gain and width
   (`exp(-r²·.35)·.5`); previously too faint to read at sheet scale. Streaks
   remain masked by puddle wetness + Fresnel.
3. **G8 day green trim:** Racer day frames still read G>R against web2 MCLA day
   references (+.054 G−R vs MCLA −.013); dusk already matched (B−R −.154 vs
   MCLA −.142) so the trim is gated by `smoothstep(.55,.95,dayWeight)` to leave
   dusk untouched. Trim factor: green ×0.93 at full day (post-trim day G−R
   measured +.012; see the results table).
4. **G7 road studs:** night emission dots along lane lines (12 m spacing,
   lateral ±3 m), named analogues `roadreflectors` / `fx_reflector` in MC3's
   executable strings (juiced2-rea README).
5. **G5/G6 evidence:** captured closeup/paint (red/blue/black) and three new
   location scenarios (f/g/h day+night) into `output/after/`; reflection cube
   verified live via paint-set env reflections on car paint.

## Measured results (pairs_and_stats.py, final run)

| set | metric | before | after | MCLA target |
|---|---|---|---|---|
| main day | G−R | +.054 | **+.012** | −.013 |
| main day | saturation | .268 | **.216** | — |
| dusk | B−R | −.154 | −.154 (unchanged) | −.142 |
| main night | saturation | .492 | **.427** | — |
| city night | saturation | .492 | **.405** | — |

Night channel balance also flipped from magenta-tilted (B−R −.027 before) to
neutral (−.004 after) on the main set, matching the MCLA night references'
neutral-to-cool balance.

## Evidence viewed this round (not just generated)

- `sheets/before-after/before-vs-after-02.jpg` — loc-d window-grid facades +
  curtain glass + road streaks after; neon strip tamed.
- `sheets/before-after/before-vs-after-03.jpg` — night rear: before/after parity
  on committed window work, magenta cast reduced.
- `sheets/before-after/before-vs-after-04.jpg` — day loc-d/e: trimmed green,
  same dusk balance.
- `sheets/before-after/before-g3-vs-after-g3-01.jpg` — smoke puffs + sparks in
  brake/launch frames; console refs show Racer's smoke is now the right family
  (soft tyre puffs) though thinner than MCLA's dense sheets.
- `sheets/web2/buildings_facade-01.jpg` — console wall-to-wall facades vs
  Racer's still-sparse blocks: density is the dominant residual (see below).
- `sheets/web2/smoke_skid-01.jpg` — MCLA/GT4 smoke reference family.
- `/tmp/reflector-crop.png` (not retained): night close crop showing paired
  stud dots along lane lines.

## Residuals (explicitly open, with reason)

- **World density / city canyons (G1 root cause):** console refs are dense
  mid/high-rise canyons; Racer's grid is low-rise with empty lots. Needs the
  world re-bake (parcel atlas 2.0) — larger than this round.
- **Brake/tail-light glow (G5):** no tail-light material sections identified in
  the car shader path; MC3 names `m_brakeLightGlowColor`/`glow_taillight%d`
  (juiced2-rea README) but Racer has no per-section light mask to drive.
- **Headlight cone sprite, per-window ambient glass glow, auto exposure (G5/G7):**
  numeric defaults unlocated in the raw games (juiced2-rea "Not done"); cone
  sprite needs vehicle-pass billboards; auto exposure needs adaptation logic.
- **Garage scene, cockpit (G5):** not attempted — separate scene build.
- **MCLA city art direct decode:** still blocked on the `CSR` tag in
  `xarchive_cache.rpf` (see 2026-11-05-mcla-data).

## Retention

- `output/` 90 MiB (< 256 MiB cap). Sheets are re-derivable from `before/`,
  `after/`, `after-city/`, `after-g3/` and the web2 crops.
- Inputs preserved: `assets/visual-local/v4/surfaces.rgba` regenerated from
  source scripts; canonical raw games untouched.

## Next

World re-bake for density (parcel atlas 2.0); locate Juiced 2/MC3 numeric
effect defaults in their environment data; identify tail-light mesh sections
for brake-light glow.

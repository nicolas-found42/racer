# 2026-11-12-night-sky-attribution: Attribute night `sky_upper` (.503 vs console .172)

- Status: completed
- Target/build/platform/architecture: `games/racer` `main` @ `d2c7df8c49d6669e6d9885fc707f08133b128d50` (macOS arm64, Apple Silicon, Metal); captured frames/measurements from `build/racer` sha256 `344eb6cede2072e3d03857f69d5f97b58163e213a35275ca3f50f3a67c1e97ef`; final clean-diff binary `build/racer` sha256 `e2ab636ce373dbd718864b5f169a35d8abe43e59d099999dc558c585b44a7c57` (restored `src/main.cpp` formatting/usage text and shader whitespace; `107/107` ctest)
- Canonical input paths, sizes, SHA-256:
  - Qualified facade atlas: `assets/visual-local/v4/surfaces.rgba` (`e61d6c16ae21f5e4c16ce18559189c93038b174df0a029bf27ddac4333af6bc6`)
  - Console reference set (162 crops, 17 MiB): `experiments/2026-11-09-city-density-bake/references/web2/` + `experiments/2026-11-09-city-density-bake/jevify-density.json` (`9482d1e4e6a87b4d813af3c08e356148d18aad110848f2349619f76e28236da7`)
  - Frozen base assets (cars/shaders/sky): `experiments/2026-11-09-city-density-bake/output/base/` (`racer` sha256 `0e2bb0923b751e517f78cd409e07f1364ee3c3af022ef7fce2a7e9abbd60cc48`)
  - Density proxy script: `experiments/2026-11-09-city-density-bake/pairs_and_stats.py` (`58cd1b3bf7f2613f257d1f9812bb405cff9a6cdfa6a9e8f52af81977352ab12d`)
- Question and expected observation:
  In `experiments/2026-11-09-city-density-bake/README.md`, street `sky_upper` improved `.429 -> .350` (console `.204`) and `facade_edges` `.117 -> .135` (console `.160`), but night `sky_upper` still reads `.503` vs console `night_street` `.172`. Is that night sky-band gap explained by camera pitch (`--camera-pitch` 5 vs 0, -1, -6) / crop composition, or does the gap (or weak night facade readability) survive matched framing and require a targeted night facade height / window-grid adjustment in `src/world_scene.h`?
- Tool/provider/version: CMake / Ninja / AppleClang / `build/racer` (bgfx Metal) + `scripts/capture_matrix.py` (`06069a04…`, `--background` hidden Metal window) + Python Pillow stats (`pairs_and_stats.py` logic).
- Working directory and exact commands:
  - Working directory: `/Users/nicolas/Documents/github/reverse-engineering/games/racer`
  - Pitch sweep (`11`, `5`, `0`, `-1`, `-6` on `street-night-rear,loc-a-night,loc-b-night,loc-c-night,loc-d-night`):
    `RACER_BIN=build/racer SURFACES=assets/visual-local/v4/surfaces.rgba NO_SCENERY=1 CAMERA_PITCH=<p> python3 scripts/capture_matrix.py experiments/2026-11-09-city-density-bake/output/base experiments/2026-11-12-night-sky-attribution/output/pitch_<tag> 0 street-night-rear,loc-a-night,loc-b-night,loc-c-night,loc-d-night`
  - Default chase distance check (`--camera-view rear`, no `--camera-distance`, `--profile /tmp/racer-chase-<tag>.txt`, pitches `5`, `0`, `-1`, `-6`):
    `./build/racer --background --smoke 5 --window 1280 720 --vehicle-library experiments/2026-11-09-city-density-bake/output/base/models/catalog.racer --vehicle 0 --shader-dir experiments/2026-11-09-city-density-bake/output/base/shaders --world-surfaces assets/visual-local/v4/surfaces.rgba --sky-mesh experiments/2026-11-09-city-density-bake/output/base/models/sky.glb --no-scenery --time night --camera-view rear --camera-pitch <p> --screenshot <out> --screenshot-delay 3.0 --profile /tmp/racer-chase-<tag>.txt --no-diagnostics --hide-hud`
  - Post-fix re-capture (all 17 night scenarios + 3 day sanity scenarios at `CAMERA_PITCH=5`, plus 5 rear scenarios at `CAMERA_PITCH=-1`):
    `RACER_BIN=build/racer SURFACES=assets/visual-local/v4/surfaces.rgba NO_SCENERY=1 CAMERA_PITCH=5 python3 scripts/capture_matrix.py ...`
- Limits before running:
  - Experiment output under `experiments/2026-11-12-night-sky-attribution/output/` ≤ 128 MiB (`62,311,562` bytes actual, 70 files).
  - Hidden `--background` runs with isolated profile paths (`~/Library/Application Support/Racer/` untouched).
- Free space and project/lab output usage before running:
  - Free space: ~282 GiB (`302,944,043,008` bytes reported by `tools/check.py`)
  - Project output: `2,940,640,096` bytes / 4 GiB limit; lab output: `2,945,523,292` bytes (`check.py` PASS)
- Output location: `experiments/2026-11-12-night-sky-attribution/output/`
- Started/finished and exit result: completed 2026-11-12; `cmake --build build -j 6` clean, `ctest` 100% pass, `tools/check.py` PASS.

## Observations and evidence

### 1. Camera-pitch widening and `inspectionDistance` fix (`src/main.cpp`, `scripts/capture_matrix.py`, `tests/cli_option_checks.py`)
- `src/main.cpp` (`693ba948…`): widened `--camera-pitch` from `0..30` to `-15..30` (explicit numeric parse, finite check, clean stderr + exit 1 on out-of-range/non-numeric/`nan`), updated usage text (`-15..30`, preserving `heading_degrees] [--screenshot path.ppm` and `[--review-script path] [--course-driver]`), and tracked `chasePitchExplicit` so explicit `--camera-pitch` also applies to `--camera-view rear` captures that specify `--camera-distance` (such as `capture_matrix.py`'s `--camera-distance 9`).
- `scripts/capture_matrix.py` (`06069a04…`): added `CAMERA_PITCH` env var pass-through (`--camera-pitch`).
- `tests/cli_option_checks.py` (`ebad35e7…`): added boundary acceptance (`-15`, `30`) and rejection (`-15.1`, `30.1`, `up`, `nan`, missing value) cases.

### 2. Pitch-sweep attribution on `main` (`d2c7df8`) geometry (`output/pitch_*`, `output/chase_default/`, `output/sheets/pitch-sweep.jpg`)
Measured with `pairs_and_stats.py` `frame_stats(..., night=True)` across 5 rear night scenarios (`street-night-rear`, `loc-{a,b,c,d}-night`) at `1280×720` (`output/pitch_stats.json`):

| Pitch | 5-scen `sky_upper` | 5-scen `facade_edges` | Inner (`street+loc-d`) `sky_upper` | `street-night-rear` `sky_upper` | `loc-a-night` `sky_upper` |
|---|---:|---:|---:|---:|---:|
| `+11°` (down) | .523 | .116 | .231 | .204 | .840 |
| `+5°` (base) | .603 | .140 | .329 | .278 | .921 |
| `0°` (horizon) | .662 | .147 | .409 | .350 | .961 |
| `-1°` (up) | .677 | .147 | .430 | .374 | .969 |
| `-6°` (up) | .739 | .139 | .526 | .479 | .992 |

Default-distance chase camera (`--camera-view rear`, no `--camera-distance`) on `street-night-rear`:
- `+5°`: `sky_upper` `.268`, `facade_edges` `.174`
- `0°`: `sky_upper` `.325`, `facade_edges` `.198`
- `-1°`: `sky_upper` `.338`, `facade_edges` `.205`
- `-6°`: `sky_upper` `.387`, `facade_edges` `.193`

Direct pixel inspection of `output/sheets/pitch-sweep.jpg` and sky-rule diagnostic masks (`output/sheets/mask-street-night-rear.png`, `output/sheets/mask-loc-d-night.png`) identifies three candidate contributors to the `.503` vs console `.172` gap (not individually ablated):
1. **Pitch alone does not close the gap:** pitching upward (`0°`, `-1°`, `-6°`) shifts the horizon down and *increases* `sky_upper` monotonically (`.603 -> .662 -> .677 -> .739`). Even pitching sharply down (`+11°`) leaves `loc-a/b/c-night` at `.549–.840` (5-scen `.523`) while trimming facade edges (`.140 -> .116`).
2. **Outer-grid horizon gaps (`loc-a..h-night`):** the 48 `ringTower`s skipped `gx = 2` and `gz in {-2, 1, 2}` flanking blocks, leaving `loc-a-night` (`.921`) and `loc-c-night` (`.861`) looking over empty 100 m blocks at open night sky; 8 outer `loc-*-night` shots pulled the 17-frame `after/night` average up from `.269` (post-hoc 6-frame central street/neon subset) to `.503`.
3. **2-storey unlit corners + cool night wall tint:** `streetParcel` allowed `floors == 2` blank siding/concrete boxes on street corners (e.g. right corner of `loc-d-night`, `.375`), `surface 11/12` hashed whole 7–19 m strips at once, and cool moonlight/night-ambient pushed unlit concrete mullions into `B > R + 3` so `_sky_rule(..., night=True)` counted shaded building facades (`mask-loc-d-night.png`) as sky.

### 3. Targeted geometry and night-only shader refinement (`src/world_scene.h`, `src/visual_shader.h`)
- `src/world_scene.h` (`dc5a99fc…`): raised corner parcel floors `2..6 -> 4..8` and mid parcel floors `2..7 -> 3..8` (every street parcel now carries window-grid sheets `11/12`), raised `blockCore` `8..13 -> 10..15` (courtyard podium `2 -> 3`), and placed window-grid `ringTower`s across all 74 outer blocks in `gx in [-5,4], gz in [-4,4]` outside the 4×4 central district (`w,d = 28..44 m`, `h = 24..52 m` inner ring / `36..72 m` outer ring). Road clearances (`>= 7 m`), atlas surface domain (`8..15`), and vertex budget (`173,082 <= 300,000` fallback; `170,874` textured) preserved.
- `src/visual_shader.h` (`f1bbe4e0…`): strictly inside `night`-gated terms (zero change to shader evaluation when `night == 0`): per-bay window hashing on `surface 11/12` (`uv * (3,1)` / `uv * (6,6)`) with warm glow (`lit*.95 + .06`), plus subtle warm urban bounce (`albedo * (.045, .030, .018) * occlusion`) on vertical facade surfaces (`8..15`, `|n.y| < .5`) inside `if (night > .01)`.
### 4. Re-capture and pixel inspection (`output/after_night_fix/`, `output/after_night_fix_m1/`, `output/after_fix_stats.json`)
Inspected sheets: `output/sheets/before-after-night-fix.jpg` and `output/sheets/console-night-pairs-fix.jpg`.

| Subset | Metric | `2026-11-09` after | This round (fix) | Console (`night_street`) |
|---|---|---:|---:|---:|
| All 17 night frames (`pairs_and_stats.py` `after/night`) | `sky_upper` | .503 | **.309** | .172 |
| All 17 night frames (`after/night`) | `facade_edges` | .137 | **.148** | .178 |
| All 17 night frames (`after/night`) | `R / G / B` | 65.2 / 59.3 / 61.0 | **73.7 / 65.7 / 63.6** | 61.4 / 49.3 / 41.8 |
| All 17 night frames (`after/night`) | `sat` | .429 | **.362** | .443 |
| `night_street` (9 frames, `CATEGORY_FRAMES`) | `sky_upper` | .440 | **.263** | .172 |
| *Post-hoc* central 6 (`street-*` + `neon-*`) | `sky_upper` | .269 | **.177** | .172 |
| 5-scen `-1°` matched pitch | `sky_upper` / `edges` | .677 / .147 | **.405 / .184** | .172 / .178 |

Per-scenario highlights (prev -> fix):
- `street-night-rear`: `sky_upper` `.274 -> .186`, `edges` `.197 -> .192`
- `street-night-right`: `sky_upper` `.340 -> .179`
- `loc-a-night`: `sky_upper` `.918 -> .416`, `edges` `.104 -> .136`
- `loc-c-night`: `sky_upper` `.859 -> .506`, `edges` `.124 -> .153`
- `loc-d-night`: `sky_upper` `.375 -> .253`, `edges` `.161 -> .204`
- Day sanity check (all 3 captured day frames): shader day math (`night == 0`) is unchanged, so inner street frames barely move (`street-day-rear`: `sky_upper` `.192 -> .183`, `edges` `.167 -> .164`, RGB `60/68/73 -> 58/67/72`, `sat` `.327 -> .328`; `loc-d-day`: `sky_upper` `.219 -> .197`, `edges` `.168 -> .173`, RGB `64/73/78 -> 62/70/76`, `sat` `.324 -> .319`), while outer `loc-a-day` moved (`sky_upper` `.123 -> .035`, `edges` `.121 -> .128`, RGB `107/110/108 -> 97/97/95`, `sat` `.284 -> .308`) because the added `gx=2` `ringTower`s occlude and darken its east horizon.

## Conclusion and limits

- **Attribution:** Night `sky_upper` (`.503` vs console `.172`) is **not** a camera-pitch artifact; upward camera pitch (`-1°`, `-6°`) raises `sky_upper` monotonically.
- **Result after joint fix (improvement, not console parity):** On `pairs_and_stats.py`'s full aggregates, all 17 night frames drop `.503 -> .309` and `night_street` (9 frames) drops `.440 -> .263` vs console `.172` (post-hoc central-6 subset `.269 -> .177`), with warm city RGB balance (`R > G > B`) and per-bay night window readability confirmed in `before-after-night-fix.jpg`.
- **Unseparated attribution (no ablation):** All four edits (minimum corner/mid parcel floors `4..8`/`3..8`, 74 outer-ring blocks, per-bay window hashing, and night-only warm facade bounce) were applied and captured together in one re-bake; no ablation separates the individual contributions of geometry height/coverage, window emission, or reduced `_sky_rule(..., night=True)` false-positives on shaded masonry.
- **Other limits:** Outer intersection shots (`loc-e/f-night`, `.598/.637`) still look across `100 m` grid intersections past single-tower blocks, because outer blocks hold one `ringTower` each rather than full 12-parcel blocks; console `night_street` crops also include close-up casino/bridge/tunnel scenes that have no procedural Racer equivalent; added `gx=2` outer towers darken/occlude `loc-a-day`'s east horizon (`R 107 -> 97`, `sky .123 -> .035`).
## Retention

- Kept under `experiments/2026-11-12-night-sky-attribution/output/`: `62,311,562` bytes (70 files: pitch-sweep frames, `chase_default/`, `after_night_fix/`, `after_night_fix_m1/`, `pitch_stats.json`, `after_fix_stats.json`, and 5 inspected comparison/diagnostic sheets), under the 128 MiB bound. All canonical inputs (`surfaces.rgba`, `references/web2/`, `jevify-density.json`, `2026-11-09` outputs) preserved untouched.

## Next action

Continue the facade-v4 / visual residual list: recover Juiced 2 / MC3 numeric effect defaults or investigate tail-light mesh sections (`README.md` / `experiments/README.md`).

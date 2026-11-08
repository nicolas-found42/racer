# 2026-11-08 MCLA tuning data (REA mining) and what it changed

**Question:** can the retail MCLA disc give real numbers (not authored guesses) for lighting, post-processing and camera behaviour, and where are its world textures?

**Target:** `games/raw/midnight-club-la/Midnight Club - Los Angeles - Complete Edition (USA, Europe).iso` (7,838,695,424 bytes, hashed in the 2026-11-05 MCLA experiment), archive `xarchive_cache.rpf` at partition offset 1,788,608,512, RPF3 table decoded by the earlier REA/Xenia-derived work (`../2026-11-05-mcla-data/output/named-entries.json`, 23,931 entries, 22,068 files, only 67 with recovered names; directory names are partly recovered). No game execution.

**Commands (bounded):** `probe_city.py` (header bytes of 14 `resources/city/sc` entries) and `extract_tune.py` (941 members from `tune/lighting`, `tune/sky`, `tune/camera`, `tune/city`, `tune/rmptfx`; member <= 1 MiB, total <= 8 MiB, raw-deflate inflated with a cap; stored and decoded SHA-256 in `output/tune-manifest.json`). Output 7.9 MiB, under the 256 MiB bound; retained locally (gitignored under `output/`).

## Observed
- **World art is not reachable by name.** The disc has one world archive (`xarchive_cache.rpf`, 2.1 GB); `resources/city` is 449 entries (1,001 MiB decoded) all under `city/sc/<hash>`; sampled entries start with an unidentified 4-byte tag and compress 40-300:1 (12 KB stored for 0.5-4.5 MB), i.e. mostly empty data, not textures. Named DDS files are only sky, UI, lightglow and car damage textures. No facade/sign texture was identified; unnamed hashed resources were not decoded.
- **Tune files are plain text and carry real numbers:** 928 of 941 are text. Classes: 430 `camBoomCS` chase/boom cameras, 82 `camTrackCS`, 69 each of four replay camera kinds, one `camFX` (shake/rumble, burnout rumble), 122 lighting files (78 `Light`, 23 `LightList`, 9 `TODLight`, `GlowTuning`, two `post-processing` files and a default `.ppp`), 18 sky files, 5 city lists, 7 particle tables (`rmptfx`, e.g. `wheel_s_asphalt`, `wheel_mud_skid`, `wheel_s_water_rooster`).
- **Post-processing (LA tune, `tune__lighting__a0829ade`):** saturation 0.9, colorcorrect .533888/.533888/.469609 (default file: .498 neutral), bloomintensity 8.0, brightpass threshold .689655, middlegray .30, grainintensity .031, rho 1.36, DoF vector 250/3000/50/1, fog vectors (1000, 0, 50, 500).
- **GlowTuning:** prop glow colour 1.0/.765/.515 (alpha .542), prop glow intensity 4.3-4.35, car glow intensity 5.3-5.35, glow distance falloff 4 (props) and 50 (cars), streak intensity .15.
- **City dynamic lights:** 23 `LightList` files of positioned point lights (type 0, cone 360) with warm colours (e.g. 1.0/.863/.427, intensity 20) and the single `Light` template 1.0/.652/.482, intensity 55, cone 125.
- **Hood-like camera:** `camBoomCS` `01c03298`: FOV 35, offset 0/1.025/-0.625, focus 0/1.025/-2.395 (height 1.025 m; focus 1.77 m ahead at the same height).

## Measured (Racer against MCLA reference frames, 480x270 means)
| frame set | R | G | B | B-R |
|---|---|---|---|---|
| MCLA day-ish (21 refs) | .347 | .334 | .312 | -.035 |
| Racer day before | .353 | .396 | .403 | +.050 |
| Racer day after | .353 | .398 | .337 | -.016 |
| MCLA dusk (4 refs) | .448 | .387 | .306 | -.142 |
| Racer dusk before | .449 | .389 | .347 | -.102 |
| Racer dusk after | .449 | .390 | .312 | -.137 |
| MCLA night (5 refs) | .262 | .236 | .225 | -.037 |
| Racer night before / after | .275 / .269 | .214 / .212 | .221 / .219 | -.053 / -.050 |
Saturation (HSV mean): MCLA day-ish .31, canonical .28; Racer day .25; MCLA night .35, Racer night .49 (too saturated at night: pink walls and neon cast light, not changed here). High-frequency luma energy: MCLA .010-.015, Racer .009-.010 (grain is not a large gap).

## Changed in Racer
- **Day colour balance:** the recovered colorcorrect ratio (x1.072, x1.072, x.943, luminance-normalised by 1.063) is applied in the final post pass, faded out by night amount (carried in `u_post.x = 3 + night`) because Racer's night is already warmer than MCLA's. Effect: day B-R moved from +.050 to -.016 (MCLA -.035) and dusk matches MCLA's mean colour within .005 per channel; night is unchanged. Evidence: `../2026-11-07-comparison-matrix/output/artefact-fix/colour-balance-before-after.jpg`. Side effect seen in the frames: a slight yellow-green cast in the day sky (Racer G is above R, MCLA R is above G); not corrected.
- **Not adopted, and why:** saturation 0.9 and grain .031 (units unknown; measured saturation and grain do not show Racer too saturated by day or too smooth), bloom 8.0 and bright-pass values (different tone-mapping chain), fog/DoF vectors (unknown units), the hood-camera FOV 35 (axis unknown; Racer keeps its own lens). Hood camera height 1.025 m agrees with Racer's authored `max(1.05, .82 * body height)`.
- Inferred only: that the LA tune file `a0829ade` is the daytime LA grade (it is the only complete LA-style file with LA-like fog colours); the retail game may switch grades by time of day, which was not examined.

## Next
Identify the RSC resource tag of `resources/city/sc` and the hashed `d6733a04`-style directories; try Swage/`RAGE-Console-Resource-Converter` formats on a small unnamed resource; decode `tune/city` and `tune/ambients` for per-time-of-day grades.

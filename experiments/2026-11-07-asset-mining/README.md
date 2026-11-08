# 2026-11-07 asset mining: road, lighting, lens, wheels

**User goal for this session:** dedicated asset-mining pass using REA on the raw games plus web sources; close the listed visual gaps with before/after screenshots and console-game screenshots. The console-parity bar is **not** met; this record is evidence for specific gap closures only.

## Target
Branch `feat/improve-racer-visual-fidelity` worktree `~/.codex/worktrees/4314/racer`, base `a60c736`, uncommitted. Previous steps: `../2026-11-07-visual-resume/README.md`.

## REA evidence used (observed names, no formulas)
From `/private/tmp/racer-visual-common-bank/effect-observations.json` (earlier REA/ISO extraction of the MCLA Complete Edition disc; decoded `CityRoad.fxc`, 26,334 B at ISO offset 1790824448): the road pixel shader `PSCityRoad` binds `DiffuseSampler`, `GrimeSampler`, `PuddleSampler`, `ReflectionSampler`, `DecalSampler`, `ShadowCollectorSampler` and parameters `FresnelExponent`, `SpecularExponent`, `SpecularIntensityNear/Far`, `SpecularTint`, `SpecularColorMixer`, `WaterParameters`, `gReflectionParams`; vertex variants `VSCityRoad`, `VSCityRoadNight`, `VSCityRoadEnv`. Earlier common-bank strings also name `vehblurimposter`, `blur_wheel`, `zoomblurmasksize`. These are names and bindings only. No shader microcode was decompiled this session and no new REA session was opened; every implementation below is authored.

### New REA session this pass (SLRR 2.31, `games/raw/slrr-231/StreetLegal_Redline.exe`, SHA-256 f44fb88a…efc2, Ghidra 12.2 provider, x86 PE)
- `search_strings` regex over render/effect terms, 83 matches (Evidence `ev_8430584dab09833152859476522809c7233816eeece081c9df3bc8e0d0f5e8e0`): `blur.psh`; sphere-map specular materials (`CMaterial_ColorSpecularSpheremap`, `…TexSpecularSpheremap`, `…MixTASpecularSpheremapMasked`, bump-specular variants) and `diff_envmap.vsh`/`skinmesh*_diffenvmap.vsh`; `setGlobalEnvmap`; `LensFlareMaterial` with `lf_flare_count/minsize/maxsize/distance`; fog parameters `fog_start/end/color`; a skidmark system (`skid_PS`, `skid_SM`, `skid_SMcolor`, `skid_SFX`, `skidmark_max`, classes `WheelSkidmark_Context`, `rg_skidmark`, `RI_skidmark`). Ghidra string inventory only; absence of a name is not proof of absence.
- `xrefs 0x593ed0` (`blur.psh`) → one site (Evidence `ev_d0ab5044…5382`); `procedure_pseudo_code 0x428891` (Evidence `ev_a07380e8…da7e4`): the containing function checks a Direct3D device capability then loads two pixel shaders, `clear_below.psh` and `blur.psh`, into an effect object. Parameters, kernel and render-target usage were not recovered. Session closed with `close_binary`.
- Carried into code as authored features: skid marks, ghost lens flares. Not a recovered implementation.

## Visible gaps from actual MCLA frames (contact sheet `mcla-contact.png`)
1. Wheels are rotationally blurred at speed. 2. Bright lamps/highlights carry cross-star glare. 3. Roads have cracks, patches, polished wheel tracks and reflective water. 4. Shaded building faces are much brighter than our near-black walls. 5. (Not addressed) saturated deep paint, dense facades, depth of field.

## Changes and before/after evidence
All captures actual native runs (`output/`), composites in `before-after/` made by `scripts/compose_before_after.py`.
- **Road model** (`src/visual_shader.h`): lane wheel-track grime/polish, noise puddles (rough .06, darker, probe reflection), hairline cracks. `before-after/road-rear.png`, `road-rear-crop.png` (before = `../2026-11-07-visual-resume/output/traffic-v3`): puddle reflecting street and sky; banded tracks across the intersection. First puddle tuning was far too wet (`road-v2`), reduced in `road-v3`. A first shader used `remainder()`, which Metal rejected (`Failed to create Fragment shader`); that failed attempt `road-v1` was deleted by me after the cause was identified (log text above is all that remains). Cracks seen in `before-after/wheel-side.png` (dark hairlines on the road).
- **Shaded-wall fill**: ambient += (.080,.072,.066)*(1-|n.y|) for world and scenery. Measured luminance of fixed ROIs, same camera: left wall 53.3→64.9, right wall 46.4→60.3, sunlit 102→107 (`look-v2/rear.png` vs traffic-v3). Still darker than reference frames.
- **Lens star** (`src/post_process.h`): 4-point star from blurred bright-pass above radiance 1.2. No isolated before/after capture; effect is small and was not separately verified in a frame with a lamp highlight.
- **Wheel rotational blur** (`src/main.cpp`): six translucent ghosts per rolling wheel across the swept angle at >6 m/s, `--no-wheel-blur` disables. `before-after/wheel-side.png`, `wheel-crop.png` (same executable/state at 93 mph, 1437 frames in 12.0 s ≈ 120 FPS): spokes smeared radially after, crisp before.
- **Tyre marks** (`src/main.cpp`): ring buffer of flat quads laid behind the two rear wheels while speed >7 m/s and (brake >.7 or estimated lateral accel >9 m/s²), drawn as an unlit alpha decal via a transient vertex buffer; `--no-skid-marks` disables. The simulation has no slip model, so the trigger is an authored heuristic. `before-after/skid-rear.png` (full-throttle then full brake, same executable/state; stops at z≈62 m): two dark parallel marks after, none before. `output/skid/elevated.png` shows the same marks from above.
- **Ghost lens flares** (`src/post_process.h`): three tinted discs along the sun-to-centre axis (authored; names lf_flare_* from REA). Faint; `before-after/sun-flare.png` compares the whole cumulative state (traffic, road, cracks) against the older sun-only frame, so it is not an isolated flare comparison.
- `tests/visual_lighting_checks.py` pinned output expression updated for the ghost alpha form (linear HDR output retained).

- **Speed FOV** (`src/main.cpp`): chase-camera field of view widens up to +12° by ~48 m/s, smoothed; `--no-speed-fov` disables. `before-after/speed-fov.png` (same executable/state, 93 mph): wider view and stronger speed sensation after. The same frames show puddle reflections of buildings on the road.

### REA on the MCLA executable carrier (this pass)
Opened `/private/tmp/racer-hdr-evidence/mcla-sectioned-seeded.ppc.elf` (SHA-256 e6555097…29e2, 10,359,680 B, an earlier analyst-built ELF32 PowerPC carrier of the MCLA executable memory image, Ghidra 12.2, language PowerPC:BE:32; this language truncates some PPC64 save-helper flow, so only string inventory is used). `search_strings` regex over effect terms (Evidence `ev_02e03b04ccb2054a4c10cab007fdd415f86f47623d3e6ba61b309e1f684a7384`) observed:
- **Night sky/lighting:** sky shader variants `ps_main_withmoon`, `ps_main_withstarfield_withmoon`; moon parameters MoonPhase/MoonSize/MoonColor/MoonBrightness, `$/sky/moon.dds`, `moon_glow.dds`; `sm_fGlobalNightLightIntensity`; HDRExposure/HDRSunExposure/HDRExposureClamp.
- **Headlights:** `Racer_SetHeadlights`, `kLightHeadlight`, `m_vBumpedHeadlightColor`, `headlights_on/off`.
- **Motion blur:** `PSStreakMotionBlur`, `PSMotionBlurCombineMC4`, `Mc4MotionBlurVehicleMtxs`, `GenVelocityMapNoVehicleBlur`, `blurEffectDesatScale`, `blurEffectTintFade`, `tireMotionBlur`, `blur_wheel`, `dtHIRES_CAR_RIM_BLUR`.
- **Post:** `PSToneMap`, `ToneMapFogDistort`, `sm_iBloomIterations`, `sm_fBloomIntensity`.
- **Skid/smoke:** `mcSkidMarkMgr`, `SkiddingThreshold`, `DEFAULT_SKID_CLAMP`; `smokeStartColor`, `smokeEndColor`, `smokeSize`.
Names only: no shader code, constants or parameter values were recovered. Session closed with `close_binary`. Juiced 2, GT4 and MC3 were **not** reopened in this pass: their executables are inside disc images (Juiced 2 is the Xbox 360 release), no extracted carrier exists in the lab, and I did not attempt to mount 5-8 GB images; earlier records in `../2026-11-07-visual-fidelity/README.md` cover those titles, and their screenshots are used here only for visual comparison.

## Night, trees and smoke (user-requested feature pass)
- **Street trees** (`src/world_scene.h`, `src/visual_shader.h`): 192 trees on block sidewalks (12 leaf cards each, trunk, positions clear of existing lamps/benches/palms and the 7 m road clearance). Cards carry local coordinates in the tangent and surface id -1; both shaders cut noise-clumped foliage so canopies cast dappled shadows. Authored. `before-after/street-trees.png`.
- **Tyre smoke** (`src/main.cpp`): up to 900 camera-facing puffs emitted at the rear wheels while the skid rule is active, sorted back-to-front, soft procedural puff texture, lifted so quads are not cut by the road, start→end colour ramp (after REA's smokeStartColor/EndColor names; values authored), `--no-tyre-smoke`. `before-after/tyre-smoke.png`.
- **Night** (`--time night`; `src/visual_shader.h`, `src/world_scene.h`, `src/main.cpp`): one shader serves day and night through a new `u_headlight` uniform (car x, z, heading, night), set beside every material draw because bgfx applies uniforms per draw. Night replaces the sun with cool moonlight, collapses ambient, darkens haze, adds a star/moon sky (also over the photographic sky), grid-derived lamp lights (12.5 m offset, 25 m spacing, ±200 m, unshadowed, wet-road specular), emissive lamp heads (surface id -2), hashed lit windows on the authored skyline and a headlight cone for the player's car. Lamp meshes (504 posts) are always present in the world. Lamps and lit windows are restricted to the central ±200 m / authored skyline; the repeated outer city tiles and the prepared scenery windows are not lit.
- **Refinements from MCLA names:** blurred periphery is desaturated; smoke ramp; ghost flares softened.
- Test budget `world_scene_checks` vertex cap raised 200,000→300,000 (trees ~22k, lamps ~26k; authored fallback was at 197k of 200k). Clearance/foliage-domain checks were satisfied by changing the tree placement and surface ids, not loosened.
- `output/night-v3` (standard views), `output/night-brake/{rear,left}.png` (braking at night with smoke, marks, headlights, lamps), `output/day-v3` (day regression; mean abs diff vs pre-night day frame 1.5/255 from lamp posts and grain).
- `capture_visual_review.py` gains `--time day|night`.

## Dusk and saturated paint (follow-up)
- **Dusk** (`--time dusk`, night amount .45): the sky function blends day and night continuously; a warm horizon glow and warmer, dimmer sun peak at dusk (`night*(1-night)*4`), lamps and windows scale with the night amount. Authored. Local sheet `before-after/dusk.png` (day vs dusk, same camera, `--paint red`): warmer, dimmer scene; weaker than the reference dusk frames (no sun disc at horizon, no long-shadow change because the shadow light direction is fixed).
- **Paint** (`--paint red|orange|yellow|green|teal|blue|purple|black`): clear-coated exterior sections keep their texture luminance and take the chosen hue (`u_reflectionState.zw`). Applies only to sections with a clear-coat entry in `vehicle_look.h` (the six NSX exterior families and the Roadster paint set); other cars are unchanged. `before-after/paint-red.png` (default silver vs red, same state) and `console-compare/mcla-paint-vs-racer.png` (MCLA red RX-8 vs Racer red NSX): paint hue now matches the reference's saturated body colour, but reference reflections, flake and body detail are far richer.
- Capture script gains `--paint` and `--time dusk`.

## Signage, flake, launch smoke (follow-up 2)
- **Neon pylons** (`src/world_scene.h`, `src/visual_shader.h`): 50 roadside pylons at the 25 intersection corners (10 m from both road centres, clear of lamps/trees, within the 7 m clearance rule), each with two emitter blades (surface id -2, own colour). Emitters now keep their vertex colour and become hot at night (lamps warm, neon magenta/cyan/amber/red/green/violet). They emit only: no coloured light is cast onto surroundings. Sheet `before-after/neon-night.png`.
- **Paint flake** (`src/visual_shader.h`): per-texel random micro-normals add sparkle to the clear-coat highlight on clear-coated sections (NSX/Roadster only). Close-up `output/neon/flake.png` (`--paint blue`): speckle on the door and fender. **Not isolated** by a flake-off capture (no flag), so the before/after is not established; a texel-grid pattern may look noisy.
- **Launch smoke** (`src/main.cpp`): hard throttle from near standstill (speed < 8 m/s) emits thinner, smaller puffs (authored trigger; wheelspin is not simulated). `before-after/launch-smoke.png` vs `--no-tyre-smoke`. A first attempt (same density as braking smoke) produced a grey ball that hid the car and was reduced.
- Still no dust or exhaust-pipe smoke, no coloured light cast by signs, no facade detail, no terrain relief, no depth of field.

## Neon light and exhaust (follow-up 3)
- **Neon casts coloured light** (`src/visual_shader.h` `neonLight`): the same 25-intersection table that places the pylons lights nearby surfaces with their palette colour (unshadowed, radius ~40 m, strength 3.4 after a first 6.0 turned a whole façade saturated pink). `before-after/neon-cast-light.png`: emit-only night frame vs lit; a pink wash on the right façade and orange on the left.
- **Exhaust wisps** (`src/main.cpp`): pale, thin puffs behind the body centre line while on the throttle. The pipe position is not recovered; the emitter is authored. `before-after/exhaust.png` vs `--no-tyre-smoke` at cruise: faint and subtle. The first version used a sine-pattern puff texture that left a visible lattice at low alpha; replaced by a plain radial falloff for all smoke.
- **Tests:** new `tests/cli_option_checks.py` (invalid `--time` / `--paint`, missing value) joins `screenshot_delay_checks`; 95 ctest targets pass (10 skipped). Still no automated test of shading output.

## Depth of field (follow-up 4; previously listed as blocked)
- The earlier blocker (scene depth is a write-only MSAA D32F attachment) was avoidable: the main surface shader now also writes eye distance in metres to a second colour target (`R32F`, MSAA x4) and the final post pass does a 12-tap gather with a circle of confusion from the distance to a focus point at the car, a 2.6 m in-focus half-range, radius capped at .010 of frame height (`--no-dof` disables). Authored values; not a recovered lens model.
- Optional by hardware: the target is created only if R32F is a multisampled render target; otherwise the pass skips DoF (this is also what the CPU mock exercises). The probe/cube passes also run the main shader without a second attachment; on this machine (Metal, Apple GPU) that rendered correctly, with no validation run.
- First capture blurred the whole frame including the car; a debug visualisation of the depth target showed it was correct (3.5 m at the bumper, ~11 m down the street, far sky), so the cause was tuning: the focus point (car centre) left the nearer bumper out of focus. Fixed with the focus range. Debug code removed.
- Evidence: `before-after/depth-of-field.png` (same build, `--no-dof` vs default): car sharp, street/houses/trees softened. 1080p at 99-mph run: 120.0 FPS with and without DoF, 0/1322 frames over 16.7 ms (one machine, one run).
- Edge behaviour not examined: foreground/background bleeding at high contrast edges, alpha-blended particles blending distance values, HUD, 4K.

## Formal adversarial review (this pass)
Ran the protocol for real (ledger and artifacts outside the repo): generated personas Dana (visual QA), Imran (CI operator) and Priya (maintainer); the seeded draw selected **Priya** (seed 1f8a802b…, candidates digest 314b495d…). Surfaces: post/lens effects; surface shader (night, road, DoF); vehicle effects; world scene; tooling/CLI. Iteration 1 found **one** LOW defect, ISS-1.01: the usage text omitted ten accepted flags (seven added by this work). Fixed in `src/main.cpp`; new `tests/usage_flags_checks.py` fails on the old text (ten flags reported) and passes now. Probes run for evidence: flag-vs-usage diff, eight option combinations (all exit 0, ~120 FPS), a 40 s throttle/brake soak (peak RSS 351.4 MiB vs 351.3 MiB at 6 s; 1/4680 frames at 18.2 ms), 1080p DoF on/off at 120 FPS. A separate clean iteration is required for the gate; see the final status in the PR comment thread, not here.

## Orange-peel clear coat (follow-up 5)
- Clear-coated sections perturb the coat normal with fine noise (`src/visual_shader.h`, strength carried in `u_reflectionState.y < 0`, `--no-orange-peel` disables), which feeds both the environment reflection and the highlight. A first strength (.16) made the paint look dirty/scratched and was cut to .05. `before-after/orange-peel-crop.png` (same build, `--no-orange-peel` vs default, `--paint red`, close side view): the sky reflection on the door picks up a fine texture. The effect is **subtle and arguably marginal**; reflection richness is still far below the reference cars (no real car-body environment, probe resolution unchanged).
- **Review status:** the formal adversarial review gate (exit 0) was for head `2aa6f76`. This change edits `src/`, which invalidates it; it has not been re-reviewed.

## Terrain on all horizons (follow-up 6)
- The authored foothills existed only on the +z side; the other three horizons were flat plain. `terrain()` now takes a quarter-turn count and grid size (`src/world_scene.h`); `buildCityScene` adds three coarse rotated patches (48x12, flat face normals; the fine 120x30 patch is unchanged, so its test is unchanged). +~12k vertices (authored fallback 263,562 of the 300,000 budget).
- Evidence is isolated (same build with and without only this change, `--no-dof`, distance 9; `before-after/terrain-{front,side,rear}.png`): the after frames show a faint hazy ridge on the horizon behind the street where the before frames show only cloud. **The change is modest**: the hills are low and heavily hazed, nothing like the GT4/MCLA mountain and hillside silhouettes. A first comparison against the older `day-v3` capture was unreadable because depth of field blurred the whole street at 9 m, which also shows DoF is strong at that camera distance (not retuned).
- Patch overlap at the corners is not handled (coincident same-colour geometry).
- The formal review gate (head `2aa6f76`) is stale for this and the orange-peel commit.

## Depth-of-field retune (follow-up 7)
Depth of field was too strong at a 9 m chase camera (it blurred the whole street, which also made the terrain comparison unreadable). Default strength 1.0 → 0.55 (`depthOfField?.55f:0.f` in `src/main.cpp`). `before-after/dof-retune.png` (same build, only the strength differs, 9 m rear camera): the street and houses stay readable with a softer falloff. Not tuned against a reference frame; 1080p full-throttle run after the change is recorded in the PR comment.

## Formal review of the later commits (iteration 3, finding ISS-3.01)
After the first gate (head `2aa6f76`) went stale, a fresh review iteration covered the orange-peel, terrain and DoF-retune commits. It found **ISS-3.01 (LOW)**: the three rotated terrain patches had no test (the one terrain test called `terrain()` with defaults and asserted `v.z>halfExtent`, meaningless for rotated patches). `tests/world_scene_checks.cpp` now asserts for each quarter-turn that all vertices lie outside the drivable square, normals point up, heights are bounded, and the patch centroids sit on the +z, -x, -z and +x horizons. A first version of the placement assertion compared the farthest vertex and wrongly failed on correct geometry (patches are 3,200 m wide but 880 m deep); it was my test's mistake and was replaced by a centroid check. Mutation check: replacing the 90° rotation with 1 radian makes the new assertions (and existing clearance checks) fail (8 failures); restored, 0 failures.

## Formal review iteration 4 (ISS-4.01)
A probe of an unwritable `--screenshot` path found the game ran, wrote nothing, printed nothing and exited 0 (the same failure class as the earlier delay defect). Fixed in `src/main.cpp`: startup now rejects a path whose parent directory does not exist with exit 1 and a message naming `--screenshot` (placed after the delay checks so their messages are unchanged); `tests/cli_option_checks.py` gained the case. On the pre-fix source the new case fails (the game keeps running and the test times out); with the fix it passes. The same iteration also showed `--post-neutral` is unaffected by depth of field (frames pixel-identical with and without `--no-dof`). Limits: only the parent directory is checked, so an existing but read-only directory, a full disk or an unwritable file still fail silently.

## Bokeh and far-sky DoF (follow-up 8)
- **Bokeh** (`src/post_process.h`, `--no-bokeh`): in the depth-of-field gather, taps brighter than 1 radiance weigh up to 13x more, so defocused lamps and neon spread toward discs (`u_dof.z`). Authored. `before-after/bokeh.png` (night, same build, only the flag differs): the difference is **very subtle** at this scale: slightly broader lamp glows. This is not the bokeh look of the reference frames (no aperture shape, only 12 taps).
- **Star artifact fixed:** the first capture showed that the DoF gather turned tiny stars (far sky, maximum blur radius) into flower-shaped patterns because 12 taps undersample points. Blur now fades to ~10% beyond 80-200 m (`cocFor`), which also keeps the sky sharp; visible in both frames of the pair (the flowers are gone). A genuinely defocused sky is therefore not simulated.
- The formal review gate (`db394d8`) is stale again for this change.

## Night lamps and neon on the outer tiles (follow-up 9)
- `buildCityScene` now reports the contiguous vertex range holding the lamp posts and neon pylons (`lampFirst/lampCount`); the main pass redraws just that range at the scenery's eight 400 m tile offsets (`setVertexBuffer(0,worldBuffer,first,count)`), and the shader's lamp and neon lattices wrap by the same 400 m period (limit 620 m from the origin). Shadows and the reflection probe still use only the central copy.
- Isolated before/after (same build, only this change; night, full-throttle run, camera at z≈290 m, `before-after/outer-tile-lamps.png`): before, the street beyond +-200 m is dark with no posts; after, lamp posts, warm light pools and neon signs continue down the street.
- Limits: the tiled lamps/pylons reach 600 m but the road grid ends at 500 m, so the outermost copies stand over the grass beyond the last road; copies at tile seams (x or z = +-200 m) duplicate coincident posts; the outer-tile houses' windows (prepared scenery) are still unlit.
- The formal review gate (`db394d8`) is stale for this and the bokeh commit.

## Retention and publication boundary
Images in `references/`, `console-compare/`, `before-after/` and `contact-*.png` are third-party screenshots or captures that show proprietary extracted game assets: they are **local only** and are now `.gitignore`d (`experiments/*/output/` already was). The README, scripts and code are what is committed.

## Console/PC reference comparisons (actual screenshots, side by side)
Reference images: 52 web screenshots gathered by a background agent into `references/web/` (`manifest.json` lists source page, URL, size, SHA-256, what each shows, and terms note; copyrighted, private comparison only; some carry site watermarks; SLRR frames are Steam community uploads that may be modded; 19 of 52 are under 960 px wide; PS2/PS3-era frames are 640x360-688x512). Contact sheets: `contact-*.png`. Sheets in `console-compare/` pair one reference per raw game with the current build (`output/final-v1`, camera distance 9, four traffic cars):
- `mcla-vs-racer.png` (MCLA, RX-8 at Hollywood sign): reference has a large hero car filling the frame with saturated red paint and strong reflections, dense trees, hillside terrain and a very high-contrast low sun; Racer shows a small dark car, flat boxy buildings, no vegetation mass or terrain relief, HUD panels over the frame.
- `juiced2-vs-racer.png` (Juiced 2 PC replay): reference has night lighting, crowds, kerbs and barriers, lit signage, many cars and **tyre marks on the road**; Racer now has comparable dark tyre marks (this pass) but no night/time of day, props, barriers or crowds.
- `gt4-vs-racer.png` (GT4 PS2): reference has tree-lined road, mountain horizon, several nearby cars and a tight car close-up; Racer has no trees along the road, only a flat horizon of boxes and distant cars.
- `slrr-vs-racer.png` (SLRR PC) and `mc3-vs-racer.png` (MC3 PS2 night burnout): reference frames show night/dusk lighting, headlight cones and tyre smoke; Racer has daytime only, no headlights on cars, no smoke.
Observed: Racer's lighting, road finish, motion cues and post pipeline are now closer in kind to these frames than at the session start, but no pair is visually indistinguishable; in several pairs the 2005-era PS2 frames (GT4, MC3) are still richer in scene density than Racer.

## Actionable findings (new, from the comparisons)
1. ~~No vegetation along streets~~ street trees added (this pass); still no shrubs/hedges, grass, or terrain-scale forest (GT4, MCLA).
2. ~~No time of day~~ `--time night` added; no dusk/dawn transition, no in-game toggle, no signage/neon (Juiced 2, MC3, MCLA).
3. ~~No tyre smoke~~ added for skid events; no dust, burnout or exhaust smoke.
4. Car paint: saturated hue now available via `--paint` (default stays silver); flake, orange-peel and rich clearcoat reflections still missing (MCLA RX-8/Saleen).
5. Terrain relief/horizon silhouette missing (hills, mountains).
6. ~~Depth of field~~ implemented (see follow-up 4); no bokeh shapes, no foreground-specific handling, no per-camera tuning.
7. Side props (barriers, crowds, kerbs, billboards).

## Web/GitHub leads
`references/github-leads.md` (agent-verified): bgfx 45-bokeh, 38-bloom, 09-hdr; KinoStreak (MIT) anamorphic streak; blur-pro-urp (MIT) radial blur; Filament material guide (Apache-2.0) clearcoat; wet-road/puddle references (Lagarde "Observe rainy world"; an unlicensed gist is reference only); Forza Horizon 4 paint-calibration slides. No external code was copied into the project; none of these leads has been integrated yet beyond ideas already implemented independently (radial blur, streak, puddles).

## Retention
Output was reduced to ~192 MiB earlier and later grew past the 256 MiB leaf bound again (651 MiB) as captures accumulated; it was brought back to ~214 MiB by lossless/derived-only steps, all hash-logged in `binary-retention.txt` (local, `.gitignore`d): old frozen executables gzipped; byte-identical duplicate model files removed (first copy kept); 92 gzipped PPMs removed only after verifying each PNG is pixel-identical to its PPM; 52 regenerable `comparison-*.png` sheets removed (their frame PNGs and reference images remain). No canonical input, saved analysis or evidence image used in the PR was removed. `road-v1` (shader compile failure) was deleted earlier by me. Nothing committed or pushed.

## Checks
ctest 94/94 pass (10 skipped, need local assets); hub `tools/check.py` PASS. `jev_review`: escalate, composite .62, safe_to_apply .17 overall (per file .17/.27/.25/.50), low confidence, no concrete defect named. No unit test covers road shading, ghosts or the star.

## Unresolved (explicit)
- Console parity unmet; side-by-side still shows far less geometry/material/lighting density than MCLA/GT4/Juiced frames.
- Depth of field not implemented: scene depth is a write-only MSAA D32F attachment; sampling it needs an MRT or resolve step.
- Car paint colour/flake, facade detail and deeper REA mining of building/paint shaders (`CityDefault.fxc`, window/sign shaders) not yet carried into code.
- Road cracks/puddles are authored noise, not MCLA's puddle/grime textures; lane grid logic assumes the 100 m street grid.
- See actionable findings 1-7 above; none is implemented yet.

## Jev completion gate (this session)
`jev_gate`, six claims, patch described by summary: action **escalate**. Verified: wheel-blur/skid/FOV before-after (.98, auto), wall-luminance measurement (1.0, auto), console comparison sheets and recorded findings (.88, auto), REA observation claim (.62, review). **Contradicted at .96-.98 by design:** "depth of field, tyre smoke, street trees, night lighting and saturated car paint are implemented" (they are not) and "indistinguishable from an Xbox 360/PS3 game" (it is not). Patch review safe_to_apply .03, composite .45, driven by a change *summary*, no concrete defect named; test gap flagged at .92 confidence (no unit test covers the new shading/effects). There is no passing gate. The goal is unmet; findings 1-7 remain open.

## Retention update (comparison-matrix round)
- `references/web2` (262 agent-gathered reference images, 49 MiB) was moved to `../2026-11-07-comparison-matrix/references/web2` because it feeds that experiment; `references/web` stays here.
- This directory had regrown to 390 MiB. Lossless/regenerable steps, all logged in `binary-retention.txt`: 25 raw `.ppm` frames removed after verifying each is pixel-identical to the retained same-name `.png` (65.9 MiB, `ppm-removed` lines with SHA-256); identical files with separate inodes (surfaces.rgba, models, binaries, frames, 33.9 MiB) replaced by hard links (`dedup` lines). Result 241 MiB, under the 256 MiB bound. No frame PNG, saved analysis state or evidence image was removed.
- A facade-detail shader attempt (`output/facade`) produced no visible effect on the towers (plain world walls, smeared at speed) and was reverted before commit; the frames are retained as evidence of the negative result.

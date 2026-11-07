# 2026-11-07 visual resume: lens finish pass

**Goal (unchanged, unmet):** Racer visually indistinguishable from a large-budget Xbox360/PS3 racing game. This record is one bounded step, not an acceptance.

## Target
Branch `feat/improve-racer-visual-fidelity`, base `a60c736`, worktree `~/.codex/worktrees/4314/racer`, uncommitted edits to `src/post_process.h`, `src/main.cpp`, `tests/post_process_checks.cpp`. Source thread was the Codex thread 01a1b522 (goal cleared there; restated this session).

## Question
Does a sun-anchored lens glare, lateral fringing, filmic S-curve, stronger split-toning, vignette and grain in the shared post pass reduce the visible grade gap to the MCLA published frame?

## Commands
- Baseline: `python3 scripts/capture_visual_review.py experiments/2026-11-07-visual-resume/output/baseline --reference <repo>/experiments/2026-11-05-city-scale/output/reference-images/mcla-02.jpg --reference-label 'MCLA actual published Xbox360 frame'`
- After: same with output `post-v1`.
- Glare fixture (scratch, not retained in repo): copy of `tests/native_hdr_probe.cpp` with a dark gradient scene, a 6-unit warm disc at uv (.62,.5), `setSun(.62,.5,1,16/9)`, `draw(false)`.
- Checks: full `ctest` in `build` (93 pass, 10 skipped: need local source assets); hub `python3 tools/check.py` PASS.

## Observed
- Baseline vs post-v1 (`output/*/comparison-front.png`, `-rear`, `-side`, `-motion`): post-v1 has more saturated, higher-contrast colour, warmer highlights, cooler shadows, visibly darker corners.
- Synthetic glare fixture: halo, faint horizontal streak and warm veiling over dark ground appear around the disc.
- Jev `jev_review`: escalate, safe_to_apply .39/.41/.84 per file, composite .66; limiting rubrics test_gap/blast_radius with confidence 0. No concrete defect named.

## Second pass (same session)
- Actual in-game finding: the four standard cameras never showed the sun. With `--camera-distance 24 --hide-hud` (`output/post-v1-far/nohud-24.png`) the sky had no sun disc, yet a warm blob sat on the road. Cause (verified by pixel diff, sky region unchanged after a procedural-sky edit): the scene draws the photographic source sky (mode 4) over the procedural sky, and that photo has no sun at the authored light direction; the road blob is the direct specular highlight of that light.
- Fix: `src/visual_shader.h` mode-4 branch now adds the authored sun lobe at the light direction (also reordered the unused-in-this-path procedural sky so cloud no longer paints over the sun). `output/post-v3-far/nohud.png` shows a sun disc with glow at upper left consistent with the road highlight. Glare is now observed in the real scene, though it is soft and far weaker than the sun in the reference frames.
- Grain is now temporal (frame counter into u_post.y/z; neutral path unaffected).
- Checks: full ctest 93/93 pass (10 skipped); hub check PASS. `output/post-v4/` is the final standard 4-view set (reference mcla-05 was a poor scene match; compare against mcla-02 sheets in `baseline`/`post-v1`).
- The default 4 cameras still hide the sun (behind the top-left HUD panel or out of frame), so default captures show little of this.

## Not established
- Glare strength versus reference suns is untuned; no quantified comparison.
- No parity claim: side-by-side frames still show far simpler geometry, flat materials, no depth of field or motion blur, no wet/specular road, sparse street life, and no source-quality car paint reflections. These dominate the gap; the grade change does not close them.

## Next action
1. Add a sun-facing review camera option so default captures show the sun.
2. Consider depth-based DoF and speed-driven motion blur (scene depth is already a separate D32F attachment, write-only today).
3. Road specular/wetness and denser city art remain the largest visible gaps; continue the REA-sourced material work in the earlier records.
4. Run adversarial-code-review loop and a Jev gate only once there is evidence worth gating.

## Retention
Output 195 MiB (below the 256 MiB leaf bound) after gzipping each PPM that has a same-named PNG (lossless; `gunzip` restores; PNGs were produced from those PPMs by the capture script, no separate equivalence manifest written). Canonical inputs, saved analysis and all captures retained; nothing committed or pushed.

## Art content step: curbside traffic (user chose "keep going on art content")
- Gap observed: every capture shows an empty street (`baseline/rear.png`); the reference frames have vehicles and activity.
- Change: `src/main.cpp` loads up to six other catalog vehicles (real extracted meshes, `loadVehicleAsset`) and places them at authored outer-lane slots (x=±4.7, z=18..150), drawn in the forward and shadow passes with a body contact blob. Visual only: no collision, like the existing city props. Skipped silently (diagnostic event) per car on load failure; disabled for preview, explicit world meshes and the scale scene. Layout and facing are authored, not recovered placement.
- `scripts/capture_visual_review.py --traffic-vehicle N` (≤4, distinct) freezes extra catalog entries with the same hash/containment checks. A first attempt with four heavy cars (`output/traffic-v1`, kept as failed evidence) hit the 28 MiB frozen-input quota as designed; `traffic-v3` used catalog indices 2,7,9,12 (Mustang, RAM, SVT Focus, Ford GT slots).
- Observed (`output/traffic-v3/rear.png`, `rear-crop.png`): recognisable different vehicles with wheels at correct positions, grounding blob and correct facing (oncoming RAM/Focus on the left, same-direction Mustang on the right). They are small and distant in the default framing; the street is livelier but still far from reference density, lighting and detail.
- Not established: shadow quality of the parked cars (only seen at ~30 m), behaviour in the garage when swapping vehicles, gameplay feel of non-collidable cars in the player's outer lane, any frame-time measurement. Startup CPU time on a 17-car live catalog rose from ~0.9 s to ~2.1 s in a 4 s smoke run (this includes all session changes, not isolated to traffic); wall time unchanged.
- Jev `jev_review` of this diff: escalate, composite .81, safe_to_apply .52 (main.cpp) / .76 (script), limiting test_gap and blast_radius at low confidence; no concrete defect named. No unit test covers the parked-car layout/loader.
- Checks: ctest 93/93 pass (10 skipped); hub check PASS.

## Retention update
Output now ~201 MiB. All PPMs with a PNG are gzipped; superseded frozen `racer` executables (baseline, post-v1*, post-v2-far, post-v3-far, post-v4, traffic-v1/v2) are gzipped with SHA/mode in `binary-retention.txt`; identical frozen `city.glb`/`sky.glb` copies were removed from all capture dirs except `baseline` and `traffic-v3` (hashes recorded in `binary-retention.txt` and each manifest; canonical copies remain under `assets/visual-local`). Nothing committed or pushed.

## Speed blur step (REA-informed)
- REA evidence already in the lab (`/private/tmp/racer-visual-common-bank/codex-strings.txt`, from the extracted common bank): post/blur assets `zoomblurmasksize`, `tonemapcolorfilterparams`, `darktonemapparams`/`brighttonemapparams`, `vehblurimposter`, `blur_wheel`, `blur_body`. Names only: no shader code, parameters or visual output recovered, so this is inspiration, not a recovered pipeline. No new REA session was run in this continuation.
- Change: `PostProcess::setMotion` and a centre-protected 8-tap radial blur in the final pass, amount `clamp((speed-15)/35,0,1)*.85` (m/s), edge-weighted (`smoothstep(.10,.50,r)`), reach .09 of the vector to centre; neutral output unaffected. Grain now seeds from one value so `config.z` carries motion. New `--screenshot-delay 2..30` so a capture can happen at speed.
- Observed: `output/traffic-v3/fast.png` (reach .20, 78 mph) was far too smeared; `fast2.png` (reach .09, same state) keeps car/centre sharp with moderate peripheral streaking. Run at full throttle reached 99 mph at ~120 FPS (1557 frames) with traffic, shadows and post enabled on this machine. Tone/colour of sky and buildings are unchanged by this step.
- New finding in `fast2.png`: beyond roughly z=170 m the authored city ends in a flat grey plain with distant box skyline: a clear world-extent/horizon gap versus reference frames.
- Not done: wheel blur, depth of field, tuned amounts against reference frames, a unit test for motion/blur (existing mock only counts allocations). ctest 93/93 pass.

## Jev completion gate (bounded work only)
`jev_gate` on a summary of the whole diff plus five claims and screenshot/test evidence: action **escalate**. Verified: sun disc claim (.97, auto); ctest, traffic and speed-blur claims verified but at review-level confidence (.58-.61). **Contradicted at .97: "visually indistinguishable from an Xbox360/PS3 racing game"**, as the author's own evidence also states. Patch review safe_to_apply .17 (composite .60, low confidence) on a change *summary*, not the literal diff, so it is weak evidence either way. No gate pass exists; the full adversarial-code-review loop has not been run. The console-parity goal is unmet.

## World-extent step
- Gap (from `fast2.png`): the prepared city (`assets/visual-local/city/city.glb`, accessor bounds ±182 m in X/Z, read directly from the GLB) ends near z≈170-200 m, leaving a flat grey plain.
- Change: in the main view only (`target==1`, not shadow, not reflection probes), the scenery is also drawn at the eight neighbouring 400 m offsets (multiples of the 100 m street grid, so lots stay aligned with streets); ground plane enlarged 1000→1800 m. Authored repetition, not source placement; repetition is expected to be noticeable. Tiled copies receive no shadow-map casters (shadow pass and probes use only the original tile).
- Observed (`output/traffic-v3/tile.png`, same state as `fast2.png`): houses now fill the street down to the horizon instead of the bare plain; 1558 frames in 13.0 s (~120 FPS) at 99 mph with traffic, tiles and post enabled. The street grid and ground still end at ±500 m, the repeated blocks look identical, and distance lighting/detail remain far from reference.
- ctest 93/93 pass (10 skipped); no automated test covers tiling. Still unmet: console parity; dense detailed geometry/materials/car paint, road wetness, wheel blur, depth of field; adversarial review loop and a passing Jev gate.

## Adversarial pass (informal; protocol ledger and CLI gate NOT run)
Persona-driven in spirit only: no persona document, no `review.py` ledger, no fresh clean iteration, so the adversarial-code-review completion gate does not exist for this work. Probes run on this session's diff: 320x240 window, `--post-neutral`, scale scene, garage scene, bad/boundary `--screenshot-delay` values, delay longer than the smoke run, and `--traffic-vehicle` duplicate/self/five/out-of-range/negative. All behaved correctly except:
- **F1 (confirmed, fixed):** `--screenshot-delay` ≥ `--smoke` exited 0 and wrote no image. Now rejected with exit 1 (`--screenshot-delay must be shorter than --smoke seconds`); new ctest `screenshot_delay_checks` covers five invalid cases and would have failed before the fix.
- **F2 (fixed by inspection, not measured):** glare weight stayed non-zero until the sun was ~60% outside the frame, yet the shader samples scene radiance at the sun position, which is edge-clamped off-screen, so a bright edge pixel could fake glare. Weight now ends at 12% outside. No automated test or capture of this path.
- `post_process_checks` now exercises `setSun`/`setMotion` with out-of-range values only for no-throw; it does not assert clamping or shader output (Jev flagged this test gap).
- Jev `jev_review` of the repair: escalate, composite .61, safe_to_apply .39, low confidence, no concrete defect named. Local ctest 94/94 pass (10 skipped); hub check run below.
- Not probed: long-session resource growth with parked cars, garage vehicle swap with parked cars, glare with a sun inside the frame after the F2 change, tiling cost on a lower-end GPU.

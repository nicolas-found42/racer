# Visual calibration — active, goal unmet

The goal remains visual quality indistinguishable from a large-budget Xbox360/PS3 racer. This continues the all-six-game REA investigation and actual comparison records in the two preceding2026-11-07 experiments. Work remains in the existing Codex worktree; the canonical checkout and its ongoing import changes are preserved. No commit/push/staging.

Current review: `/tmp/racer-visual-review-20261107/state/review.json`, Martin persona, active iteration1. No clean pass or completion gate. Open architecture/world/material-quality gaps remain actionable. Tests and native calibrations do not establish visual success.

## Bounded inputs and retention

Native runs are hidden (`--background`), use isolated profiles and perform no desktop activation/input. This leaf output cap256MiB; each native capture<=30s and four-view bundle<=64MiB. Each regression run<=25s, complete fixture<=24MiB. Commands<=120s except the already bounded300s original-source proof. Source canonical inputs and external saved REA analysis remain retained. The preceding leaf was~205MiB before this continuation; no prior failures were removed.

The pinned local sky is prepared with:

```sh
python3 scripts/prepare_sky.py --source /Users/nicolas/Documents/github/reverse-engineering/games/raw/slrr-231/maps/skydome --output assets/visual-local/sky
python3 tests/prepare_sky_checks.py --source /Users/nicolas/Documents/github/reverse-engineering/games/raw/slrr-231/maps/skydome
```

Pins: SCX `289169d2d53b16fb0c370996f1ca13ff5b59c1546314d32e28cb8eb9f0c66047`; DDS `0e010e5b69b9b596dd7f299652ee868dde20e5e3f575684c712de6e5798d280c`; RDB `d8421b4b2d4e27834fc339e87edb459613f78eed1356e51760ad049730402e94`. RDB native resource0x19 binds mesh0x3 and texture0x18. Source376 positions/UVs and350 triangles remain exact; all2048² mip0 pixels match. Source projection is circular dome UVs. Renderer uses explicitly authored unlit scale.15, camera centering and no depth writes, including reflection passes. Native orientation, placement and exposure remain unknown. Prepared proprietary GLB/manifest are ignored local outputs; absent preparation falls back to authored procedural sky.

The durable script passes seven checks including exact optional-source arrays/pixels, conflicts, idempotence, symlink rejection and rejecting mismatched existing file sizes before reads. Publication is exclusive but not crash-atomic across two files. Local sky has16MiB decoded RGBA and a~2.56MB GLB. Source/probe/Jev receipts are retained in the preceding leaf's `output/sky-source-evidence/`.

## Defects reproduced and repaired

Independent source probes reproduced odd mip edges being dropped, optional-PBR material alpha/default mistakes, and alpha.5 packing to127/255. Mip filtering now uses fractional area coverage in linear RGB; alpha is linear. Material-level MASK/BLEND/cutoff is independent of optional PBR. Factor opacity is a float vertex attribute shared by the color/shadow vertex shader. Native color captures show .4999 absent, .5/.5001 present and pixel-identical.

The isolated raised-cube/neutral-plane fixture exposed the earlier shadow assessment as insufficient: no caster ground shadow and diagonal false shade. `/tmp/racer-shadow-diagnosis/check.py baseline` failed with0 changed ground pixels outside the caster. The sole sampling-Y inversion probe passed with461 changed ground pixels and identical equal/above images; the diagonal shade disappeared. These exact before/after comparisons and manifests are retained in the preceding leaf's `output/shadow-baseline/` and `shadow-flip-y/`.

The durable actual-native regression is:

```sh
python3 tests/native_shadow_checks.py --binary build/racer --output experiments/2026-11-07-visual-calibration/output/shadow-check
```

It freezes the executable, generates minimal inputs, records argv/hashes and checks both the cast shadow and no-caster receiver. New source/lighting changes require fresh execution. The earlier passing `output/shadow-calibration-v2/` in the preceding leaf records its exact executable identity; it does not certify later builds.

Direct lighting-v1 city comparisons showed stronger directional form after reducing authored ambient fill and increasing key/specular strength, but foreground shadows still exposed point-sampling stair steps. Current repair interpolates comparison results at four texel centers over a3x3 kernel (36 depth reads versus prior25 point reads). It preserves Metal Y inversion. Fresh native pixels and performance are still required before accepting the filtering repair.

Jev coherent repair review escalated low confidence rather than approving the modules. The subsequent verifier supported the native calibration and explicitly unmet visual standard, but had low confidence on mip details and lacked support for omitted material defaults in its bounded excerpt. Parent inspection plus executable regressions supply stronger evidence; these receipts are advisory records, not a clean completion judgment. Full target quality remains unresolved.

Resume: capture the current filtered shadows and compare actual Racer pixels with actual reference frames; run current native shadow/controls/garage/performance checks, resolve only demonstrated fixes in the persistent ledger, then continue the outstanding architecture, foliage, material, street coverage and presentation work. Source MCLA v4 perimeter pilot remains opt-in because its neighboring world is absent. Never replace the visual target with passing code/tests.

Continuation: current city-art assembly and resume point are `../2026-11-07-city-art/README.md`. Receiver-plane correction subsequently passed the actual slope test; sourcecity fine ripples disappeared in `output/city-joined-v3`. Raw native material composition and missing world coverage remain unresolved. This leaf ended at~230MiB; new four-view producers use the next leaf rather than exceeding its256MiB cap.

Retention continuation: generated PPM duplicates are now losslessly retained as `.ppm.gz`; `output/ppm-retention.json` records full byte roundtrip, original/archive/PNG hashes and restoration. Corresponding PNG pixels were verified exact before archiving. Canonical inputs, failed images and analysis state remain preserved. Current continuation: `../2026-11-07-hud-surface/README.md`.

Closed-stage frozen Racer executables are now losslessly retained as `racer.gz` after full byte-roundtrip verification. `output/executable-retention.json` records hashes, original mode and restore commands; restore before replaying historical argv. Active builds, canonical inputs and saved analysis are unchanged.

Closed-stage frozen prepared GLB capture copies also have full-byte gzip retention; `output/frozen-input-retention.json` records exactSHA/mode/mtime and restore argv. Primary assets/raw inputs/analysis state remain in place. Restore referenced copiedGLBs before replay; town-v1 baseline excluded.

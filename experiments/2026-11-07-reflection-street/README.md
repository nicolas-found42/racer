# Rough reflection, streetscape and material continuation

Active goal: visual quality indistinguishable from a large-budget Xbox360/PS3 racer. Not met. Continues adversarial iteration1, Martin persona; all six raw-game REA investigations and actual reference captures remain retained in preceding experiments. No clean review/completion gate.

Target independent worktree `/Users/nicolas/.codex/worktrees/4314/racer`, base71664dc; canonical import changes preserved. Prior native `../2026-11-07-hud-surface/output/street-lighting-v1` adds four house types, stairs, normal detail, static signals and reduced haze. All four actual MCLA comparison sheets were directly inspected: improved variety/contrast, still pale car, unfiltered harsh reflections, sparse facades and no traffic/pedestrians. Latest five other reference boards were also viewed: GT4/MC3/Juiced2PC/SLRR221/SLRR231; provenance limits retained in their captions/manifests.

Current investigation: local cubes previously had no mip chain and only mixed sharp samples with sky by roughness; coat did not filter at all. Pinned bgfx Metal source generates mip levels on resolving final-face framebuffer with AUTO_GEN_MIPS; new capture allocates nine levels, signals generation only face5, and retains complete previous-cube read/write isolation. Authored box LDR mip filtering is not GGX or recovered native convolution. Need actual Metal images and bounded moving performance before acceptance. Medium960 HUD also now pages compact mode before primary controls shrink below12px; actual native evidence pending.

Budget: output256MiB, per four-view producer64MiB, individual native30s/process deadline115s,40GiB free minimum. Use hidden owned windows, isolated profiles, no desktop activation/input. Keep exact binary/input/reference hashes and finite argv in each output manifest. Preserve failed captures, source inputs and REA/Jev state. Prior hud leaf ~180MiB/cap256 closed to large new producers.

Resume: build current renderer, run actual mip/material/city comparisons and inspect pixels, reproduce medium UI, refresh resource/unit/native/performance checks; retain unresolved visual gaps. No visual parity claim without fresh reference comparison evidence.

Closed-stage frozen executables now have verified full-byte gzip retention; see `output/executable-retention.json` for exact SHA/mode/mtime and restore argv before replay. PNG comparisons, input assets, failed logs and saved analysis remain retained.

Closed-stage frozen prepared GLB capture copies also have full-byte gzip retention; `output/frozen-input-retention.json` records exactSHA/mode/mtime and restore argv. Primary assets/raw inputs/analysis state remain in place. Restore referenced copiedGLBs before replay; town-v1 baseline excluded.

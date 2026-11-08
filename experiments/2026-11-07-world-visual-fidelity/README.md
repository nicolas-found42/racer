# Native world visual fidelity — active continuation

Unchanged goal: Racer visually indistinguishable in quality from a large-budget Xbox360/PS3 racing game, supported by fresh actual-game screenshot comparisons. Previous loop/evidence in ../2026-11-07-visual-fidelity/README.md; goal and original review ledger remain active.

Question: can actual source city geometry/materials close the clear facade/density gap remaining after authored city, lighting, source surfaces, alpha palms and HUD work?

Canonical input: MCLA Xbox360 ISO under /Users/nicolas/Documents/github/reverse-engineering/games/raw/midnight-club-la. Exact original ISO identity in hub games/INPUTS.json; matching recovered-memory carrier d091bab… and retained RPF TOC under canonical Racer experiment. Preserve source and saved analysis, no new emulator or activation.

Before production: prior leaf output154MiB, current newleafempty; volume~385GiBfree. Thisleaf<=256MiB; external worker /tmp/racer-visual-world-assets <=32MiB including original selected bytes/decoded candidates/GLB; each selected member<=8MiB, commands<=300s, capture producer<=60s, four captures<=64MiB. No bulk city/RPF extraction. Larger investigation decomposed into bounded probes; all reference assets/localcaptures remain private ignored data.

Actual findings: 449cacheRPFfiles under resources/city/sc; early small chunks2116/2352 mostlyterrain/roads and unsuitable substitutesforbuildings. Follow-up1948/2300 have validated geometry, nativebounds/shader/texture pointers and richer store/window/sign declarations. This isstaticresourceevidence, not runtime proof or nativeBRDFreconstruction.

Implementation: optional --world-mesh /absolute/path.glb draws bounded static geometry independently in main,shadow,reflectionpasses; importedcar physics/profileidentity unchanged. Defaultworld remainsauthored untilactualpilotpixelsandplacementtested. Sourceunits,axis,LOD,shaderroles,alphachannelsandnativeplacementmustbefoundedorseparatelylabeledasauthoredmountchoices.

Evidence/retention: worker sourcebytes+primaryformatreferences in /tmp/racer-visual-world-assets; finalprovenance/GLBto be retained hereafterbudgetcheck. Review state remains /tmp/racer-visual-review-20261107/state/review.json iteration1, openfineart/qualitygaps and no completiongate.

Next: finishboundedcityresourcepilot; renderactualworldGLBwithfrozeninputsinRacer, compareactualMCLA/Juiced2frames, repairvisibledeficiencies, retainunknowns.

## First actual native pilots

Current prepared files under worker `prepared/`:1948.glb1923980B,22924sourcevertices/18645triangles,21PNG/3506176BdecodedRGBA;2300.glb3583748B,46167vertices/30916triangles,38PNG/6.50MiB decodedRGBA (exact in manifest). Mesh positions unchanged. Authored review mounts are explicit CLI translation, not native placement/units proof.

Executed `--background --world-mesh /tmp/racer-visual-world-assets/prepared/2300.glb --world-origin 685.0043945 -17.6958008 721.9497070 --camera-view elevated --camera-distance100 --window1280 720 --smoke4`; analogous1948 origin[485.2160645,-27.8247070,923.921875],camera-distance160. Exact argv/logs retained external and overviewpixels here. Both exit0, about119FPS short samples; these are sourcepilotcaptures, not performance acceptance.

Direct pixel observation:2300 is coherent low-rise commercial streetscape with modeled roofs, signs/poles and varied architecture.1948 is mostly terrain/freeway/roadsideprops; shadernames alone did not establish dense buildings. Both are largelywhite because shared diffuse references/layered shader behavior remain unresolved. Default publication rejected; authored city remains normalstartup. Review issueISS-1.10 records actual gap.

`python3 tests/world_resource_checks.py --pilot-dir /tmp/racer-visual-world-assets/prepared`:8testsPASS, including actual self-contained images, sourceposition/index/UV/alpha preservation, virtual-segment bounds, helperpin, real ancestry, range/format and predecodeRGBA budget. They do not establish shader fidelity or pixel success.

Next: source-bound sharedtexturedictionary resolution for2300; inspect native renderbucket/layer/alpha declarations instead of assuming opacity. Repeat sourcecity native captures after those repairs, then evaluate a coherently mounted subset for defaultRacer streetscape.

## Textures, road layers and current limits

Shared bank2111 recovered all missing diffuse hashes for2300. `output/source-world-evidence/` retains source proofs and prepared v2/v3. V3 preserves original source position/index/normal/UV0/UV1/UV2 and raw COLOR data for44,882 vertices/30,025 triangles; two grime models are explicitly omitted because their composition is unknown. Source arrays and97 decoded PNGs were independently checked against the original ISO. RGBA footprint22,368,512bytes. Source terrain and grayscale road-preview policies are authored approximations, not recovered native shader formulas.

`output/city-v3-chase/` is a textured courtyard. It is not evidence of a public driving street. A later actual source-bound road-decal recovery produced `road-decals-v4/2300-authored-road-overlay.glb` externally:7,949,500bytes,99images,23,154,944 decoded RGBA bytes. All original v3 arrays/materials/images remain unchanged; eight additional BLEND overlay primitives use exact source UV1 and decal pixels with an explicit .002m normal offset.52 triangles with unsuitable normals are excluded. Display-space lit overlay composition is an authored approximation; native FXC composition and render states remain unknown.

`output/city-v4-road/` freezes this exact world GLB and the running executable, car, sky and shaders. Exact argv/build/input hashes are in its manifest. REA controlled capture `ev_997f4e86011a5d4244a6c8e95a8e84001d5906cb57b937b88facacab94adf626` exited0. Process sampling was partial and the filesystem observer omitted four whole-file digests; the capture helper independently hashes its retained inputs. Inherited environment remains unknown.

The explicit authored mounting was `--world-origin 716.7880859375 -18.404296875 652.2412109375`. Direct images show an asphalt/sidewalk strip at a tile boundary, detailed adjacent frontage and source road markings, but a vast missing neighboring world. Its public-carriageway role remains unproven. This is an inspection pilot and has not replaced the normal authored driving world. Open review ISS-1.09/1.10 covers the remaining art, world coverage and native material gaps.

`output/sky-v1/`, `sky-v2/` and `lighting-v1/` retain additional actual native comparisons against MCLA. Sky-v1 also compares the latest sky against actual GT4, MC3, Juiced2-PC and SLRR221/231 reference panels, preserving their older source/provenance limits. No sheet establishes the requested visual parity. Current resume and calibration evidence are in `../2026-11-07-visual-calibration/README.md`.

Retention continuation: generated PPM duplicates are now losslessly retained as `.ppm.gz`; `output/ppm-retention.json` records full byte roundtrip, original/archive/PNG hashes and restoration. Corresponding PNG pixels were verified exact before archiving. Canonical inputs, failed images and analysis state remain preserved. Current continuation: `../2026-11-07-hud-surface/README.md`.

Closed-stage frozen Racer executables are now losslessly retained as `racer.gz` after full byte-roundtrip verification. `output/executable-retention.json` records hashes, original mode and restore commands; restore before replaying historical argv. Active builds, canonical inputs and saved analysis are unchanged.

Closed-stage frozen prepared GLB capture copies also have full-byte gzip retention; `output/frozen-input-retention.json` records exactSHA/mode/mtime and restore argv. Primary assets/raw inputs/analysis state remain in place. Restore referenced copiedGLBs before replay; town-v1 baseline excluded.

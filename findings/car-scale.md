# Vehicle and world scale

One Racer world unit is one metre. Imported geometry uses +X right, +Y up,
+Z toward the nose; front-left means negative X. Source proportions and every authored adaptation are recorded separately. Camera framing is a separate setting.

Gran Turismo 1 and Redline are excluded from the active catalog and further work at the user’s request. Historical research outputs remain retained but are not supported player assets.

## Current eleven-car scope

The reviewed library contains **eleven player preparations and one deferred traffic measurement**. Exact installed bytes and coverage are recorded in the [eleven-car ledger](../experiments/2026-11-06-car-coverage/output/car-coverage-eleven-v4.json). This is a bounded reviewed set; the remaining source catalog entries require their own assembly and acceptance evidence.

## Canonical records

[`dimensions.json`](../assets/catalog/dimensions.json) contains six attributed manufacturer dimension records and two decoded source-game canonical records, with original units, model year/variant applicability and source-model hashes. The Dodge RAM and Midget II records are GT4 EU SpecDB declarations, not manufacturer specifications. [`prepared-sizes.json`](../assets/catalog/prepared-sizes.json)
records retained, in-scope source preparations: exact source/prepared/descriptor hashes,
body bounds, four wheel pivots/radii/widths, wheelbase/tracks, ground height,
unit authority and comparison results. Unmapped catalog cars have unknown factory
dimensions; they do not inherit a generic car size.

| Current player preparation | Length | Ground height | Wheelbase | Comparison authority |
|---|---:|---:|---:|---|
| GT4 Acura NSX '04 | 4.421 m | 1.160 m | 2.530 m | Published 2004 NSX exterior specifications; within review limits |
| GT4 Nissan 350Z '03 | 4.308 m | 1.348 m | 2.650 m | Qualified Z33 platform reference; height +2.48% |
| GT4 Dodge RAM 1500 Laramie Hemi Quad Cab '04 | 5.780 m | 1.926 m | 3.569 m | Decoded GT4 EU source declarations; not an independent manufacturer check |
| GT4 Daihatsu Midget II D-type '98 | 2.839 m | 1.649 m | 1.840 m | Decoded GT4 EU source declarations; length +1.75% |
| Ford Racing 2 Mustang 1973 | 4.839 m | 1.285 m | 2.770 m | Contemporary Mach 1 brochure; length −1.69% |
| Ford Racing 2 Focus SVT, Racer tracks | 4.249 m | 1.432 m | 2.623 m | 2002 SVT brochure; explicit factory-track adaptation |
| MC3 Corvette Z06, authored mounts | 4.429 m | 1.222 m | 2.654 m | Factory wheelbase/tracks fitted explicitly; body length −2.96% |
| MC3 350Z, source-code '04, v4 | 4.335 m | 1.329 m | 2.631 m | Qualified Z33 platform reference; all five compared metrics pass |
| MCLA 2006 350Z Roadster | 4.336 m | 1.343 m | 2.631 m | Exact year/body-style owner-guide reference; compared metrics within 1% |
| Juiced 2 350Z, rubber-only Toyo template | 4.300 m | 1.326 m | 2.656 m | Qualified Z33 platform reference; within stated limits |
| SLRR Furrano, authored fixed pose | 4.500 m | 1.182 m | 2.710 m | Fictional model; source dimensions retained without manufacturer certification |

The separate MCLA `va_350z_04` traffic asset measures 4.297 m long, 1.318 m ground height and 2.640 m wheelbase. It remains excluded from player installation/selection. Its retained preparation and native captures are traffic research evidence.

Review limits are authored checks: 2% wheelbase/axle tracks and 3% length/ground height.
Passing them supports approximate size agreement, not exact retail-variant or
original-game physics parity. A body's bounding-box height excludes ground
clearance; overall height is measured from ground. Visible mirrors/accessories
can exceed published body width, so width is reported without automatic fitting.

MCLA ambient models are **traffic assets**, as clarified by the user. Keep their models and measurements for future traffic; exclude them from player-car installation and selection. The reviewed local publisher rejects traffic IDs regardless of role flags; player installation and selection remain limited to the reviewed player rows. Historical native inspection captures are retained as research evidence, not player-car acceptance.

The earlier MC3 **Corvette** source export omitted seven external stock parts, including the hood.
Exact native DAVE filenames, hashes and PCK mesh/bone joins now restore them.
An earlier uniform factory-wheelbase calibration left axle tracks about 12.5% too narrow. It remains retained and rejected. The reviewed player revision adds explicit wheel-mount X translations to the factory tracks, preserving binary shapes, body, materials, images and wheel Y/Z. It passes stated dimensional tolerances and native multi-angle/steering/motion checks; it does not establish original-game frame behavior.

The new MC3 350Z v4 preserves all 10 non-effect embedded LOD0 meshes and all 6 stock-named external meshes; the source shell/window geometry is present. Exact native config, library handle and PPF page associations support two additional exhaust instances at the full native `exst0`/`exst1` rest frames. Their static activation and two appended PBR material interpretations are explicitly authored. Reviewed active window materials receive a separate Racer glass policy; lamp materials and all original geometry/images remain unchanged. See the [source closure and exhaust record](../experiments/2026-11-06-mc3-coverage/output/350z-closure-and-exhaust-README.md) and [independent exhaust review](../experiments/2026-11-06-mc3-coverage/output/independent-exhaust-review.json). The [v4 canonical comparison](../experiments/2026-11-06-mc3-coverage/output/350z-canonical-comparison-v4.json) passes length (+0.58%), ground height (+1.10%), wheelbase (−0.72%) and front/rear tracks (−0.18%/−0.83%). This supports approximate Z33 platform size agreement; the source-code year label does not establish exact retail trim, native physical units or recovered runtime-default activation.

SLRR retains the source SCX/CFG dimensions and wheel world geometry, with an explicit fixed body drop of 0.135724125 m. A triangle/slab-cylinder test over 1,101 steering samples passes a 5 mm expanded envelope, independently reproduced. More compressed poses failed and remain retained. This is a Racer rest pose, with approximate materials and omitted native suspension/engine consumers; native equilibrium and continuous suspension travel are unverified. See the [fit review](../experiments/2026-11-06-fit-review/README.md).

Primary references: [Acura 2004 NSX specifications](https://acuranews.com/en-US/releases/release-3a09a5a1994177788b07aa004c34c503-2004-acura-nsx-specifications),
[Nissan 2002 Z33 Version ST](https://www.nissan-global.com/EN/HERITAGE_COLLECTION/284_fairlady_z_version_st.html),
[Ford 1973 brochure, archived scan](https://autocatalogarchive.com/wp-content/uploads/2016/09/Ford-Mustang-1973-USA.pdf),
[GM 2003 Corvette information kit](https://www.gm.com/content/dam/company/no_search/heritage-archive-docs/vehicle-information-kits/chevrolet/2003-Chevrolet-Corvette.pdf).
Nissan is a platform reference rather than an asserted identical US-market trim.
The 1973 Ford brochure is retained as OCR; its direct PDF retrieval returned HTTP 403 and page pixels were not independently reviewed. The [2002 Focus SVT brochure](https://xr793.com/wp-content/uploads/2024/01/2002-Ford-Focus-SVT.pdf) also uses third-party scan text whose pixels were not independently checked. The [2006 Nissan owner guide](https://www.carmans.net/wp-content/uploads/pdf/2006-nissan-350z.pdf), printed page 9-9, supplies the Roadster column; its text was retained, while direct PDF retrieval returned HTTP 403 and pixels remain unverified. Printed Roadster millimetres and separately rounded inches are not mixed. Exact retained hashes, locators and applicability limits are in the canonical record; these links do not assert fresh retrieval.

The active Juiced 2 350Z is exact mesh `77a9becc6d20882a97417610a5a6a22120c33076c92d54ae7b84bec70eef81fb`. Its explicit Toyo-template filter removes the duplicate OZ wheel face/decorative disc/BLACK2 structures, retaining rubber and the configured native rim/brakes. Source body, pivots and textures remain; stock discs roll and calipers use separate steering-only carriers. [Independent filter closure](../experiments/2026-11-06-ford-expansion/output/independent-template-review-closure.json), [current motion](../experiments/2026-11-06-expanded-acceptance/output/350z-rubber-motion-v1/manifest.json) and [garage loop](../experiments/2026-11-06-expanded-acceptance/output/350z-rubber-garage-v1/manifest.json) identify the exact revision. Original procedural tyre interpolation and rim-scale consumers remain unproved. Earlier 350Z preparations and profile histories retain their old geometry identities.

## Source-family limits and research holds

GT4 RAM and Midget II use exact decoded EU2560 CHASSIS/tyre joins. Raw tread is kept separate from the exporter hypothesis `track = (tread − 5 × tyre-width byte) / 1000`; wheelbase/track agreement with geometry made from the same inputs is not independent native-unit proof. The [GT4 coverage audit](../experiments/2026-11-06-gt4-coverage/output/coverage-audit-v1.json) preserves all 730 chains and raw WheelLayout flags. Model T floating parts, Tank Car duplicated/displaced wheel assembly, Benz Patent topology, Daimler zero inferred front track and Midget '63 unusual layout remain research holds. Midget II is a separate four-wheel source. No EU/US row-ID equivalence or layout-to-wheel-count rule is assumed.

Focus retains its source body, height and wheelbase while wheel/carrier X mounts explicitly fit the published SVT tracks. [Track review](../experiments/2026-11-06-ford-expansion/output/source-track-independent-review.json) and [canonical comparison](../experiments/2026-11-06-car-coverage/output/focus-canonical-comparison-v1.json) record that adaptation. The unfitted source and Ford F150 remain separate research records; renderer acceptance alone does not resolve their variant or pose questions.

MC3 imports here are from the pinned **PS2 Remix** packages. The separately retained local Xbox original DUB ISO is a different build; no model/row/runtime equivalence is assumed. The Corvette's repaired, calibrated mounts and the 350Z's unchanged source coordinate scale have distinct preparation histories. Their raw PCK/frame checks support static source assembly; original runtime activation and physical units remain unproved.

MCLA player Roadster preparation uses exact native resource/bone evidence, manufacturer-assisted tyre-radius fitting, front flat-ground adjustment and authored glass. Its source factor 1 and original runtime suspension/shader semantics remain unproved. Additional Mustang/Golf variants remain held: the [expansion record](../experiments/2026-11-06-mcla-expansion/README.md) preserves the source antenna-versus-roof distinction, Golf tyre/variant mismatch and all earlier candidates. Ambient `va_` assets remain traffic-only.

The Juiced 2 MX-5 remains a research hold, including its authored hub-rest/rubber-only attempts. The [rim/rubber intersection review](../experiments/2026-11-06-ford-expansion/output/mx5-rim-rubber-intersection-review.json) preserves the rim/template conflict; neither plausible wheelbase nor a parser pass establishes native procedural scale or an acceptable complete wheel. No forced fit or historical hold is silently promoted.

SLRR is a local source-derived fictional assembly rather than a manufacturer car. Its source geometry, approximate materials, omitted hardware and fixed-pose limitations remain as recorded above. Source-game canonical records and manufacturer records do not transfer across families.

## Spatial references and verification

The [reviewed gallery](../experiments/2026-11-05-city-scale/output/gallery.html) links retained eligible-player native captures and reference images; the fit review adds current candidates and maximum-steer evidence. The [city-scale experiment](../experiments/2026-11-05-city-scale/README.md) retains
**the existing 19 reference images: 12 MCLA frames, 5 NFS Heat frames and 2 real Los Angeles traffic photographs**,
with source URLs, hashes, dimensions, credits and captions in the [reference manifest](../experiments/2026-11-05-city-scale/output/reference-manifest.json). No new city reference images were added for the eleven-car expansion. Front/rear/side/elevated
views show cars against lane markings, traffic, people, curbs and buildings.
These are visual context; uncalibrated perspective screenshots do not establish
absolute metres. Published promotional frames are distinguished from HUD gameplay.

Current acceptance evidence is split by build and purpose. MC3 v4 has [four native views](../experiments/2026-11-06-mc3-coverage/output/native-views-v4/manifest.json), [seven motion captures](../experiments/2026-11-06-mc3-coverage/output/native-motion-v4/manifest.json), and [keyboard, virtual-gamepad and three stationary maximum-steer checks](../experiments/2026-11-06-mc3-coverage/output/native-acceptance-v4/manifest.json), all marked verified. Those manifests record their earlier exact executable and asset hashes; the research-view manifest by itself did not grant player eligibility.

The [eleven-car keyboard manifest](../experiments/2026-11-06-asset-failure-context/output/live-eleven/manifest.json) records eleven passing hidden native garage loops on executable SHA `73b6409966b408902d5b8bf99432617a3f76d6538aa16cb2df38da31a9009ffa`, with exact mesh, descriptor, library and workflow identity checks. Its [retained build manifest](../experiments/2026-11-06-asset-failure-context/output/verified-build-v3/manifest.json) preserves the executable/source snapshot. This latest run took no captures; it does not refresh all historical visual evidence onto that binary. The immutable model bytes remain in the managed store at their ownership hashes, rather than a standalone asset backup in that run. Synthetic controls do not establish human or physical-controller acceptance; capture timing is not performance evidence.

`src/world_scale.h` defines the authored grid: four 3 m lanes, 12 m road width,
100 m blocks and a 1 km square boundary. `--scene scale` adds an explicitly
diagnostic 2.5 × 5.5 m parking bay, 1 m ticks and a 1.75 m schematic figure.
Every car uses the same inspection camera in that scene. Career markers are
suppressed there to avoid obscuring the comparison. Normal play remains a flat
driving grid; a populated city has not been implemented.

```sh
cd /Users/nicolas/Documents/github/reverse-engineering/games/racer
python3 scripts/check_car_scale.py assets/local/vehicles/4c157f280bd085aa43bca9d9f82d380b84e7ebad2cac269fdf7dac3188475e8e.vehicle --model-id gran-turismo-4/acra0014
python3 scripts/verify_vehicle_scale.py /absolute/fresh-scale-output
```

The first command checks declared descriptor geometry and its source identity;
it does not independently decode the mesh. The second loads the actual prepared
assets through Racer's SHA, complete-node-binding and full body/wheel containment
checks, then captures four hidden native views per eligible reviewed player car. It preserves
the exact executable, models, isolated profiles, histories and PNG hashes.
Pillow must be installed in that Python environment. Factory-conflict comparisons
return exit 2; missing factory evidence is explicitly unknown, not certification.

## Investigation path

For a historical size/orientation failure, identify the executable SHA and
`asset_load_begin` / `asset_load_end` operation in the retained JSONL history.
Retrieve its source/prepared mesh and descriptor hashes, then compare against
the canonical record. `motion` samples retain vehicle physics identity,
wheelbase, steering, signed travel, pose, model and camera coordinates. Use
`scripts/diagnostics.py` as described in the
[diagnostic runbook](diagnostic-runbook.md). Retention is bounded and new fields
cannot recover old evidence that was never recorded.

The original filled-wheel-cylinder diagnostic also intersects legitimate internal arms and wheelwell planes. The [clearance reports](../experiments/2026-11-06-fit-review/output/clearance-v1/README.md) retain source triangle witnesses and exact scope; contact counts are not automatic source-defect diagnoses. No arbitrary tyre/pivot clamp was applied to hide those reports.

## Lightning and additional source research

The [current Lightning comparison](../experiments/2026-11-06-cohort-acceptance/output/lightning-scale-final-v3.json) joins the exact source/prepared descriptor to attributed platform dimensions, with a year-free UI label. Five authored checks pass: wheelbase, length, ground height and both tracks. Visible mesh width is 2.226 m versus the brochure's 2.009 m; conventions and mirror contribution remain unknown, so this is neither a width pass nor proof that mirrors explain the difference. The native year/power declaration conflicts with the brochure; exact trim and source handling remain unverified. Seven manufacturer and two source-game dimension records are now indexed.

Retained [primary-source research](../experiments/2026-11-06-cohort-acceptance/output/dimension-research/dimension-proposals-v2.json) also establishes a Sport Trac platform comparison with roughly 10% excessive candidate length/wheelbase; no guessed fit or promotion was applied. Cobra standard/R identity is unresolved. The F150 brochure table covers Styleside variants and cannot certify the source-labelled Flareside. These limits remain actionable per-car research, not hidden scale defaults.

Further [MC3 primary-source research](../experiments/2026-11-06-mc3-attachments/output/dimension-research/README.md) found no applicable primary dimensions for the new Saleen/Esprit candidates. Viper coupe/GTS-R evidence rejects using the preliminary RT-10/SRT10 convertible table. Source geometry measurements remain recorded, canonical fields remain null and these new rows stay ineligible. No whole-model calibration was applied to hide mismatched proportions.

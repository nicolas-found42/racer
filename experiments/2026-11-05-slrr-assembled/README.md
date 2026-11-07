# Stock Furrano visible assembly — 2026-11-05

Question: can the canonical 2.31 Furrano be assembled beyond the chassis with original panels, glass, lights and wheels, retaining each source identity and attachment transform?

Canonical root: `../../../raw/slrr-231` from this experiment. Originals unchanged. Full member paths, bytes and SHA256 are retained in `output/furrano-static-v2.json` provenance. Target package `cars/racers/Furrano.rpk` SHA256 `63d7ec06f22b2176d476980e1fa66df823e9a6e8bac915474c9f292c622b89ec`.

## Procedure and evidence

All operations headless; free disk424GiB. Individual input cap16MiB, aggregate resolver cap32MiB, output cap32MiB, command budgets under300s. Actual distinct source bytes2,894,175 and glTF2,560,954 bytes. No asset copies outside local experiment output.

Behavioral discovery first used `jg` with explicit canonical Furrano root, max-requests8000/concurrency20, retained `output/assembly-jg.txt`. Its9000-byte excerpt cap truncated search context; focused original CFG/Java reads supplied actual assembly evidence. No conclusion relies on omitted excerpts.

The chassis CFG `_main_GT54.cfg` stockpart lines535..563 supply exterior/interior, doors and nested windows/lights; `Furrano_GT54.java` supplies actual Java stock rim0x316 and tyre0x3d5 rather than CFG's four generic wheels. Exhaust0x114 is explicit Java addPart. Script reads that Java source into provenance, but does not execute its arbitrary descriptor-conditioned stock method. Source chassis and Java are not identical stock declarations: this export uses CFG visible parts and explicit Java wheels/exhaust, not a claim that arbitrary native descriptor selects this exact configuration.

Each part's native CFG is recovered from RPK. Exact `attach` links identify parent resource+slot; `compatible` and matching parent `attach` resolve steering-wheel999. Source-parent matrix times parent-slot matrix times inverse child-slot matrix supplies placement. Original render pose applies before centimetre-to-metre mesh scale. Four wheels use source chassis wheel frames and slots101..104. No upstream user-measured wheel offsets adopted. Duplicate source slot IDs are marked ambiguous and rejected if used; repeated suspension slots do not affect these selected visible attachments.

External primary reference retrieval used Firecrawl against pinned `nedobylskiy/SLRR_rev` commit642945c69a38f9c632d3a6009ba18e1bbab1c7f6; original TypeScript retained as `output/reference-*.ts`, hashes in `output/verification.json`. `model-transform.ts` specifies0.01 mesh units, `transforms.ts` YXZ Euler(pitch,yaw,roll), `slot-frames.ts` steering/wheel slottype frames. These are reference implementation evidence, **not execution of supplied native game**. First incorrect owner URL returned404; correct pinned owner returned200. `reference-part-host.ts` fetch also404 and is explicitly unusable; other retained references contain source. Jev decision retained `output/assembly-judgment.json` supported source-backed static assembly with explicit limitations over origin concatenation or chassis-only stop.

## Result

`output/furrano-static-v2.gltf`:32 source mesh nodes,45,012 vertices,19,140 triangles, all selected visible parts resolved. SHA256 `64b977dab3ab894e523406b4e6af13ee51677af366bef326370a8baba4f98b7c`. Includes chassis, bumpers, hood/trunk, roof, glass/windows, both doors, mirrors, skirts, seats, headlights/taillights, steering, exhaust, four rims and four tyres. Earlier31-node output retained, superseded by v2 after source-compatible steering link resolution.13 primitive material issues remain explicit (null/absent/out-of-range maps); source materialindex5 is not remapped or fabricated.

Run from repo root:

```sh
python3 scripts/slrr_vehicle.py --root ../raw/slrr-231 --gltf /tmp/furrano-new.gltf --report /tmp/furrano-new.json
python3 tests/slrr_vehicle_checks.py
python3 tests/slrr_asset_checks.py
python3 tests/slrr_gltf_material_checks.py
```

All pass:5 matrix/pivot/wheel/nonfinite/duplicate/remapping checks plus existing SCX UV/topology/malformed/material tests. Actual exported glTF was separately checked for32nodes, all attribute/accessor indices and buffer ranges, no pending assembly links; see `output/verification.json`. REA controlled process test capture exit0 Evidence `ev_badf6cb9c8f07d2fb1aa6de166f0fc56a039895a6dc77374f4805a57260f86d5`; short-lived process sampling incomplete, no filesystem/network observation, so it only corroborates test command/result. No active native REA target changed.

## Remaining limitations / resume

This is a source-backed static **visible vehicle**, not full native stock simulation. Engine, battery, pedals and suspension internals have not been assembled. Supplied game installation/descriptor execution, deformable skin/bone behavior, rotating/steering wheel motion, paint/shader parity and physics are untested. Parent/child placement follows pinned reference conventions and actual source poses; still needs independent render review and comparison to native gameplay. Source UV stays raw, diffuse-only PBR factors/sampling authored; no claim of original appearance. Root owns runtime importer and gameplay verification; next action is headless render review of this32-node glTF, native-reference alignment review, then expand internal hardware source assembly only if needed. No code changes to runtime, shared parser, CMake or plan here.

Independent headless geometry review: `output/render-review.py` decodes final glTF buffers and32 node matrices into a Pillow painter projection; `output/furrano-static-review.png` has front/rear oblique, side and top panels with per-part diagnostic colors. Reviewed image: exterior forms a recognizable closed body with windshield/side glass, aligned doors/skirts/hood/bumpers/lights and4 wheel positions; no detached panels. Side view shows rear tyre clearance tightly intersects source wheel arch; no invented wheel offset applied. This painter lacks depth buffering, transparency, texture and native shader behavior, so overlap artifacts and hidden parts cannot establish final render quality or prove native alignment. Runtime GPU review remains root-owned.

## Latest root checkpoint

Root native review: first Furrano load failed asset_image_budget because repeated default-white/gray textures exceeded32MiB decoded. Shared runtime content-SHA dedup fixes this without raisingcaps; vehicle_validate and hiddennativefit-dedup load32groups/19140tris with9uniqueimages. Sidepixelsreviewed: coherentbodyand4wheels butbody/wheelarchrestfit questionable; playereligiblefalse retained. Firecrawl pinned suspension-3d.ts shows CFGspringrest used as hardpoint offset and later subtracted atrest; therefore blindly adding0.29m to wheel centers is not justified. output/suspension-reference-query.json retained. Need native restpose/suspension authority, not inventedvisualfit.

## Runtime candidate preparation — not promoted

NEW `scripts/prepare_slrr_vehicle.py` and `tests/slrr_preparation_checks.py` adapt the exact assembled v2 input, pinned reportSHA `f7ebdde3cc18b34a2559113397066832b8740d63d927df68df3d61d2436d940f` and chassisCFG SHA `b0074215c7de997983ec52d6cee5b6fadb8c4634e242e8d2280027292960a6a2`. No canonical reextraction. Output `output/furrano-prepared-v1/ba086fe0712a2c7549b8b5069c6c0bfb48fa9894ed0a19b890553239d7f9dbe6.{glb,vehicle,json}`, GLB2,713,412bytes. ExactdescriptorSHA `dd001e45d7836d27270fca475f642a9744d3a70faa47d1bad3f8615badb2a8fa`. All32groups/45,012vertices/19,140triangles retained, original32buffers and27PNG bytes preserved plus material/texture/sampler metadata. Missing diffuse bindings remain13issues; no substitutions. CFG explicitly labels FL/FR/RL/RR and pivots; wheel pairs retain their source group ownership, not bbox-selected triangles. ReflectZ for +Zfront/+Xright; localposition/normal/tangentZ and tangentW reflection, indexedwindingreverse, arbitrarysourceproperrotation matrix conjugation S M S. Existing0.01 meshscale untouched. Uniformrootlift.8143500308743705 yields alltires≥ground and visiblebodyminimum.38208196446812054/maximum1.3174371776334037. That unusually high bodygap is retained and **blocks player eligibility pending native visual/suspension-height review**. roleplayer-candidate/runtime_player_eligiblefalse inGLB+receipt. No rootcatalog/main/CMake changes.

```sh
python3 scripts/prepare_slrr_vehicle.py --source experiments/2026-11-05-slrr-assembled/output/furrano-static-v2.gltf --report experiments/2026-11-05-slrr-assembled/output/furrano-static-v2.json --cfg ../raw/slrr-231/cars/racers/Furrano_Data/scripts/_main_GT54.cfg --output /tmp/furrano-fresh
python3 tests/slrr_preparation_checks.py
python3 tests/slrr_preparation_checks.py --source experiments/2026-11-05-slrr-assembled/output/furrano-static-v2.gltf --prepared experiments/2026-11-05-slrr-assembled/output/furrano-prepared-v1
```

Eight fixtures pass including arbitraryrotation/sharedaccessors, originalPNG/material preservation, pins/pivot/CFGlabels/partialassembly failures, unsupportedmatrix/skin/pose/externalURI/indexbudget and freshprivatepublication. Independentstruct-based completeactualchecker verifies everyworldvertex equals originalreflection+lift, allbody/rim/tyrevertices fitdescriptor and allsourcebuffer/imagebytes retained (`output/furrano-prepared-independent-v1.json`). Actualradiuscommonaxles.34435003087437055m,widthleft.221095389/right.220851479; wheelbase2.71,tracks1.68/1.88. Units follow retainedprimaryreference SCXcm/CFGmetre conventions, not nativeexecution or manufacturerproof. No rideheight/wheel correction inferred from images. Newoutput<3MiB, selectedsource<3MiB and totaladditionalwellbelow128MiB; free-space20GiB guard; callercommand≤300s, no maximumperformance qualification. Privateexclusivefresh3files, not transactional/crashdurable; failuremayleavepartialoutput.

REA controlledindependentchecker Evidence `ev_57cc7eb9679aa5f527863c4a5ce612b85f1889a6a5a99ba6abb936ed276887ea`, exit0, retainedsource/prepared/descriptor/receipt hashes in `output/furrano-prepared-rea-v1.json`. Incomplete shortprocesssampling; filesystembefore/after notsyscalltrace; no nativegame/network observation. Jevgate `furrano-prepared-jev-gate-v1.json` escalatedpatchlowconfidence(.23safe-to-apply), bothclaimsverifiedauto(.99/.91). Independent source_vehicle_review inspectedsourcepins/CFGownership/matrixmath/pivots/cylinders and reran8fixtures/fullactualcheck: no concreteconverterdefect exactpinnedcandidate. Nativevisual/suspensionheight stillblocked; originalshader/damage/internalhardware/physics unverified. Next: preservecandidate and compare native restpose before any playerpromotion. User excludes Redline andGT1 models; this SLRR evidence does not authorize enabling them.

# Donor cars in normal gameplay

Current resume — 2026-11-06: seven player cars are now installed. The [fit review](../2026-11-06-fit-review/README.md) supersedes the four-car resume notes below: MCLA player Roadster v4, authored MC3 factory mounts and SLRR fixed pose are reviewed and published; Juiced 2 stock brakes use rolling discs and steering-only calipers. GT1/Redline are blocked at active listing/acquisition/publication, and MCLA ambient stays traffic-only. Final 45 CTest targets, seven native garage loops, 28 current scale views and 21 maximum-steer views pass within their recorded scope. The [observability delta](../2026-11-06-observability-delta/coverage.md) adds retrieved workflow identities and explicit coverage limits. Overall goal remains active; preserve historical records below and expand reviewed variants next.


Active user goal replaces the earlier broad system roadmap: import/modify car models from source games and the supplied carmodels repository, use them in normal Racer gameplay, and verify model/physics alignment. Eventually every car/game is desired; this investigation must build a repeatable catalog/import path and account for all discovered source families rather than treat a preview chassis as complete. User is AFK and authorized autonomous completion. All native checks remain hidden/no desktop focus.

Inputs: canonical games in ../raw and public https://github.com/nicolas-found42/carmodels. Firecrawl live root observation reports commit ce047799fc550cdf92e4f7b62d97ef5c603e53ad; verify exact pinned assets before use. Prior SLRR CFG/SCX/RPK exports are leads, not fully assembled cars. Preserve existing dirty/staged work, prior experiments and player saves.

Bounds: each batch<=300s; generated experiment output<=256MiB; initial selected model<=16MiB and32MiB combined; free>=20GiB. Input acquisitions need exact provenance/hashes and measured separate bounds. Current preflight424GiB free, prior all-milestones output147MiB, integration5.7MiB. No bulk disc duplication or deletion.

Requirements: (1) inventoried source catalog/provenance and explicit unsupported branches; (2) complete recognizable donor body/glass/wheels/materials in normal launch; (3) reproducible import/conversion with scale/axes/pivots/wheels/collision data; (4) selectable/modified models and truthful persisted identity; (5) wheels/pose/camera/reset/boundary/steering/reverse and benchmark alignment verified in code and real renderer captures, both sizes; (6) retained diagnostics/builds/source/commands/query outputs and updated README/plan; (7) all twelve Jev capabilities used for appropriate evidence/decision tasks, Firecrawl/REA used on actual external/artifact questions. No full original-game physics or shading parity claim without direct evidence.

Historical starting observation (superseded by current checkpoint): normal main.cpp still builds cubes; only explicit --preview-gltf replaces geometry. Physics hardcodes2.7m wheelbase and497.5m center bounds. Existing glTF lane loads static embedded geometry/UV/base color PNG but lacks animated wheel/pivot/vehicle metadata. Next: inspect supplied catalog, select evidence-backed complete donor models, implement the connected vehicle representation and replace default cubes.

External review: repository root Firecrawl markdown screened by Jev, review probabilities injection.44 andtail.60; inspected as ordinary GitHub listing/README/tool usage. No instruction to expose credentials or override agent rules followed. README/recovery claims remain unverified until exact assets/manifests are checked.

## Current checkpoint — imported player cars, scale and retained diagnostics

Normal gameplay now uses the real GT4 NSX; the managed library has four player
preparations: NSX, GT4 350Z, Ford1973 Mustang and ISO-extracted Juiced2 350Z.
GT1/Redline are excluded by user. MCLA ambient models are retained traffic-only;
they are not installed or offered for player selection. MCLA player350Z
`vp_nsn_350z_06` has now been hash-acquired (4,143,144bytes, SHA7f4818ad423f9db6802e70a65b6de4c4cb0e38dab4b335f98318a7d8360bd56a)
but is not adapted/promoted. Its76nodes/66meshes/47images and source wheel
approximation/omission metadata are retained in the MCLA experiment.

Runtime replaces rigid cubes with independently bound body/four wheel groups.
Measured source pivots and wheelbase feed renderer/turn curvature; signed travel
feeds wheel roll and reset, conservative full-steering envelope feeds oriented
world-boundary contact. Physics identity hashes actual mesh plus all descriptor
geometry, so changed geometry cannot compare with old results. Legacy profile1
records remain readable; imported records use profile2/modelrevision2. This
preserves authored8s acceleration/38.8737m braking; donor drivetrain/handling
parity is not claimed.

| Verification | Actual evidence | Result / limits |
|---|---|---|
| Regression suite | output/ctest-acceptance.log |39/39pass; imported hash/binding/containment/profile2/physics identity/turn curvature/reverse/reset and existing diagnostic/storage/domain checks. |
| 720p full garage→tune→test→compare→course loop | output/donor-loop-720/manifest.json,37PNG/screens/actions/native.log |exit0,181.91s; synthetic course, pause/reset/cancel/save failure/retry/reload. Old exactbuild089959b1… retained, not silently called current. |
| 1080p full loop | output/donor-loop-1080/manifest.json,37PNG/actions/native.log |exit0,182.16s; actual build SHA e84f5b11f6953036e4b455ca2ca066936ccb89e8401f1379a869830fd956b28c. Captures produce stalls; not a no-capture performance claim. |
| Model selection/failure/recovery/livery | output/selection-four-v1/manifest.json,13PNG/actions/native.log and reload/history |exit0; dirty Keep/Discard, broken Juiced2 mesh retainsFord, write-denied selection activeinmemory,RetrySave recovers,Juiced2 reload matchesexactSHA, applied stripe visible, actual8.000s result. |
| Native steering/reverse/reset | output/motion-{nsx,juiced2}-v1/manifest.json,7PNG/run/history |bothpass9checks; right/left physics/model alignment,reverse,reset,pause and sampledwheelpose. No physicalinput/human acceptance inferred. |
| Imported-car virtual gamepad loop | output/virtual-pad.log/history |liveSDLvirtualgamepad edit/apply/test/compare/persist/retry/cancel/focus/rearm/disconnect pass. Physicalcontroller unavailable. |
| Shared metric fixture | ../2026-11-05-city-scale/output/eligible-four-v1/manifest.json |16hiddennativeviews,allfourplayercars/allactualSHA+body/wheelcontainment pass; identical8mcamera,2.5×5.5mbay,1.75mfigure,1mticks,3mlanes. |
| No-capture 1080p Juiced2 drive | output/perf-juiced2.log/history |119.997FPS,13.009measuredseconds,9.66046mslongest,0/1561>16.67ms; boundedlocalMetal sample. |
| Installer lifecycle | output/install-four-player.json,install-four-resume.json,install-local-compatible.json;assets/local/carmodels/install-receipts |4-entrynativevalidatedcatalog90a07cc3…; immutablefiles/history, sharedlock,hashchecks,resume. Newlocalpublisher3fault/lifecycle tests and13acquisition-installer tests pass. Localproprietarypreparations required; bootstrap obtains2GT4defaults only. |

Independent source review repaired actual issues: Fordnodecap reservesgeneratedroot;
GT4 mirror preservesleft/right; MCLAfalseplayerrole corrected; MC3 upstream
export skipped7NULLexternalparts withoutwarning. ExactnativeDAVEname/hash joins
nowrestoreMC3hood/bumpers/skirts/lights. An experimentaluniformfactorywheelbase
calibration still leaves axletracks~12.5% belowGM; checker now gatestracks too,
soMC3remainsineligible. SLRR32-part candidate retains all geometry/images and
loadsaftersharedPNGdeduplication (9uniqueimages instead of27duplicates hitting
32MiB); GPUsideviewstillhas questionable restfit, so it remainsineligible.
Juiced2body/panels/interior/pivots and14native textures independently checked;
stockproceduralTYRE_PROFILEandTEST_CALLIPER/TEST_DISCcomponents remainunresolved.
No arbitrary missinggeometry, wheel offsets or nativephysics claims substituted.

### Observability additions and historical reconstruction

Coverage extends library/descriptor, meshvalidation, GPUupload, selectionstate,
persistence, installer/cache/catalog and sourceconversion boundaries. Startup
records librarySHA/count/fixedfailure; pairedassetloadoperations record actual
meshSHA/physicsidentity/bounds/materialcoverage; wheelgeometry atload and10Hz
wheelpose/motion recordsteering/signedtravel. Descriptor opens useO_NOFOLLOW,
nonblocking regularFD andboundedconsistentread. Duplicateimages usecontentSHA
sharing, retaining32MiB uniqueRGBA/128image caps. Telemetry remains bounded,
local and fail-open; receipts haveUUID/source/tool/hash lineage and noautomatic
retention pruning. No new service/deployment/credentials required.

Actual reconstruction: output/retrieved-asset-outcomes.json identifiesoperation13
failedasset_parse atmono11123.67ms afterFordoperation11 succeeded; following
operation14 loadsJuiced2 at12959.37ms. NativeUI/captures06/07showFordretained,
08/09showUNSAVEDselection,10showRetrySave success; reloadassetSHA matchesJuiced2.
This supports loaderrejection→oldcarretained→repair→newcaractive→savefailure→retry
→restartreload. The intentionalfixture supplies knowncause (badbytes/write-denied
isolateddir); a historicalsameerroralone wouldnotprovewhocorruptedthefile orwhy.
No sourcegamewasexecuted and telemetrycannotrecoverunretainedpastdata.

Copyable retrieval:

```sh
python3 scripts/diagnostics.py --root experiments/2026-11-05-car-models/output/selection-four-v1/history --event asset_load_end
python3 scripts/diagnostics.py --root experiments/2026-11-05-car-models/output/selection-four-v1/history --operation 13
python3 scripts/diagnostics.py --root experiments/2026-11-05-car-models/output/motion-juiced2-v1/history --event motion --event wheel_pose --limit 500
./build/vehicle_validate assets/local/vehicles/catalog.racer
python3 scripts/install_prepared_cars.py --id ford-racing-2/MACH1_SIXTY --id juiced-2/350Z
```

All12Jevcapabilities haveactualretainedresults indexed in
output/jev-capability-index.json. Lowconfidencecompactclaimverification was not
rerolled: root inspectedexactnativeactions/logs/captures and source/manifests.
Previousstrongreviewerscaughtconcretedefects; later review attempts stopped on
workspacecredits and are not approvals. Finalwhole-goalcompletion is **unproven**.

Resume: acquire/adapt actualMCLAplayervehicle withnativepart/wheelproof, finish
SLRRrestfit andMC3trackspace diagnosis, resolve Juiced2stocktyre/brake fidelity,
then expandreviewedsourcevariants and finish fullphysics/whole-goalacceptance.
Humanlap andphysicalcontroller remainunverified but do notprevent localwork.
Goal remainsactive. Oldresearchoutputs/inputs/staging/savespreserved; no Gitcommit.

Final broad integration Jev gate retained in output/integration-gate.json returned
**escalate** (no truncation; aggregate0.6314/safe0.31, broadtest-gap/blastradius
uncertainty). It is not approval and was not rerolled. Three bounded claims were
supported but two lowconfidence. Whole-goal completion and broaderindependent
review remain open. Existing directsource/nativechecks still stand narrowly;
next review should inspect retained actual per-file evidence and close concrete
gaps, including dedicated materialshader malformed/cutoff regression.

Exact currentfourcar library andSHAmanifest additionally preserved atoutput/car-checkpoint-build/models (7,533,073bytes). Genericbuildsnapshot hasnoissues andexecutablee84f5b11…; sourcecopyrelationshipremainsworking-tree-at-copy,notsilentcompileproof.

## Escalation review fixes closed

Strongindependentreviewer reproduced androotfixedtwo newlocalpublisher bugs:
inventoryduplicatescouldmaskmissingrequestedIDs; deadlinewasnotcheckedafter
validator. NowrejectduplicatesandselectexactIDs, propagatecooperativedeadline
throughvalidationandprepublication, boundsubprocessbyremainingtime;5tests pass
includingbothreproducers. Reviewerconfirmedbothfixesand13selectioncapture
hashes/rawasset/reloadevidence. This closesboundedfindings, notfullgoalapproval.
DedicatedpinnedMetalshader regression nowtestsactualcutoff0/.247/1, preserved
interface/trailer/NUL and malformedlength/interface/nonfinite inputs. Latest
output/ctest-forty.log shows40/40pass. NoJevoverallgatereroll.


## Current source-exclusion enforcement

Independent source_vehicle_review found and fixed two active-policy gaps: the lower-level importer still allowed direct excluded-family acquisition, and local prepared publication trusted player flags for ambient MCLA entries. `import_car_models.py` now owns shared excluded-family policy for game, ID and source-file namespace, filters active inventory, and rejects excluded batches before cache/network/storage work. `install_cars.py` shares that policy. `install_prepared_cars.py` rejects va_ player publication and requires the exact reviewed MCLA player ID/source SHA. Its repository inventory remains an explicit trusted review boundary for other provenance claims.

Offline commands `python3 tests/car_import_checks.py`, `python3 tests/car_install_checks.py`, `python3 tests/prepared_install_checks.py` pass 15/13/7 checks. Regression cases cover falsely eligible excluded/ambient rows, no publication or validator call on rejection, direct acquisition with each namespace field excluded, CLI active listing, historical catalog retention, and permitted raw traffic acquisition. Canonical source catalog and historical assets were not changed or reacquired. Exact pinned catalog SHA and active/historical counts are retained in `output/source-exclusion-review.json`; new diagnostic output is under 2KiB. Resume: parent independently review these narrow code changes; no source exclusion was lifted, no donor analysis or runtime launch performed.

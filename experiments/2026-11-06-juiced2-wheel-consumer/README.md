# Juiced2 wheel consumer investigation

Question: can retained source/runtime analysis establish stock rim scaling or procedural tyre-profile construction for held Juiced2 ISO assemblies, without guessed dimensions or arbitrary fits?

Previous goal turn was verified progress: shared bounded inventory capacity and four-model verification snapshots; current13players/52preparationrows unchanged. Full goal remains active. Juiced2 canonical ISO remains /Users/nicolas/Documents/github/reverse-engineering/games/raw/juiced-2/juiced-2.iso. Reuse cached native evidence/REAstate, do not duplicate originals.

Before production: measure current remainingproject allowance beforeanyoutput; initial reservationthisleaf256KiB total, eachcommand<=300s and20GiBminimumfree. No fullnative executable extraction/new Ghidra database or model preparation copies fit this reservation. Only small retained queries/source ranges/receipts; if required input is absent, verify actual blocker before next action. Existing heldGLBs each3.9–5.2MB exceed remaining~1.8MB project allowance for duplicatepublication; no suchcopy is authorized here. All work headless/noactivation, no emulatorinstall or desktopinput.

Plan: inspect current REAsession and retained executable/config indexing; resolve nativeconsumer entrypoint only from actualsourceaddresses/refs. Sourceconfigurationdeclarations are not formulas. Use smallREAranges and savedprojects; retain provider/build/hash and boundednegativefindings. A source-backed small adapterchange can be implemented/verified if its neededinputs are established withoutnewlargeoutputs. Do not claim originalgameexecution or promote heldcars from metadataalone.

Resume: find currentREAsession and any existingnativeJuiced2 executable/proofs, then traceTYRE_PROFILE/rim construction. KeepGT1/Redlineexcluded and MCLAambienttrafficonly.

Before furtherconsumer excerpts/verification: raise thisleafreservation to512KiB total (supersedes256KiB), within1,846,569B measuredprojectheadroom; command<=300s, sourceexcerpt<=32KiB each, rawcode/data ranges<=16KiBbatch. No largeproducer/newdatabase/modelcopies. Existingsourceidentityreviewused128861B, including retained strictfailedprobes. SourceXEX nowfreshlymatchedactualISO; nineexportedsectionsmatchdecodedmemorybut.rdata43Bdifferent/.relocunexported. Usepre-importdecodedmemoryforactualbytequeries, notordinaryPEloaderorexported.rdataasidentical.

Before implementation: build a bounded first-party native-wheel contract audit/kernel, with generatedsmallfixtures and actualISO/profile+decodedimage readback. It will encode proven rawnative profile anchor/sample-count and setter float-operation order, retaining unresolved argument semantics/shader deformation; it will NOT change existing renderer/physics/defaultvehicleconversion or publishmodels. New report+596Bprofile+source/test snapshots+logs/native windows within512KiB leaf. Tests memoryonly forimagepins/finite/rawschema; syntheticdiskfixtures<=32KiB. No fullmodel/PE/databasecopies. Final gate uses boundedactualproof notwholetranslations.

## Final result (checkpoint closed 2026-11-06)

Question answered, qualified: retained native analysis **does** establish the shared static wheel-sizing contract — the 596-byte `TYRE_PROFILE` anchor sampling (12-of-13 constructor scan, flag0), the setter's explicit float32/float64 rounding order and scale/extra formulas, the matrix/material consumers, and the `TyreCode` `%d/%dR%d` input bridge. It **does not** establish stock per-car wheel geometry: actual per-car record/upgrade selection, caller f4, the writable race-time multiplier, and continuous-curve/shader deformation remain unrecovered. The `--registers 225 .45 17` CLI path stays an explicitly labeled analyst demonstration, not a stock configuration.

Nothing changed in game C++, player eligibility, GLB geometry or physics. All 52 preparation rows / 13 players and the 13-entry catalog (`3da5f93b…`) are byte-unchanged; only four held Juiced 2 research rows gained a `native_wheel_contract` evidence field (`geometry_applied: false`). Exact-patch reconstruction from the immutable before-snapshot proves only those four fields differ.

Verified fresh at checkpoint close: 9/9 contract unit tests, 71/71 CTest targets, hub checker PASS. Final review ran once (`output/kernel-review-v2.json`): no actionable defect in the publication-owner and metadata-only delta; limits recorded, escalation not rerolled.

## Evidence

- Audit report: `output/contract-v2/report.json` (SHA `a0386a975791c5cbf3b046ea3e04cb94b131f6528e6776a93b53e0101c1a41a7`), retained 596-byte profile `output/contract-v2/profile.bin`, lifecycle sidecar.
- Source identity: current-ISO XEX `ae20f2467cc0535872b18517941ac4434f60408cb6d07bf47da799ce1564e574`; decoded memory image `ee51a8b7be39967bee04eddb3146116616500fb357d8fc2751fb1fa58eecddc0` (memory layout, not an ordinary PE; exported `.rdata` differs at 43 bytes, `.reloc` unexported — qualifications retained).
- Inventory delta: `output/inventory-evidence-update.json` (before `a75b0ce5…`, after `3fb258cf…`).
- Kernel reviews: `output/kernel-review.json` (pinned audit/kernel scope), `output/kernel-review-v2.json` (final publication-owner/metadata delta).
- Source coverage: `output/aggregate-source-coverage-v7.json` — 174 first-party files, 171 unchanged inherited.
- Test logs: `output/ctest-final-v2.log` (71/71), `output/kernel-tests-v2.log`.

## Storage accounting (measured at close)

- This experiment's `output/` tree: 484 KiB raw `du` (375,298 B measured at the reservation check), within the raised 512 KiB leaf reservation.
- Project standard allowance (hub checker, `st_size` sum over `experiments/*/output`): 2,133,700,152 B of 2,147,483,648 B → headroom **13,783,496 B**, checker PASS (as of checkpoint close 2026-11-06; later same-day continuation outputs grew the tree — final 2026-11-07T02:34Z re-run: 2,133,993,602 B used, 13,490,046 B headroom, PASS). Raw `du` of output trees is 2,114,336 KiB (block slack above `st_size`); the checker figure is authoritative.
- Nonstandard roots (not in checker allowance): `assets/local` 76,908 KiB, `build/` 29,684 KiB, default diagnostics store empty (0). Free space on the volume ≈ 417.9 GB, above the 20 GiB floor.

## Next action

Recover actual per-car argument/resource state (which stored car record and upgrade level select the TyreCode arguments, caller f4 source, mutable multiplier at race time), then continuous curve/shader construction. Only then independently render and drive any resulting geometry before eligibility. Storage headroom (~13.1 MiB checker) forbade duplicate GLB publication at this checkpoint (superseded 2026-11-07: the user doubled the limits and four Juiced 2 cars were published in place; see held-GLB publication).

## Retrieve

```sh
cd /Users/nicolas/Documents/github/reverse-engineering/games/racer
python3 -m json.tool experiments/2026-11-06-juiced2-wheel-consumer/output/contract-v2/report.json
python3 -m json.tool experiments/2026-11-06-juiced2-wheel-consumer/output/inventory-evidence-update.json
PYTHONDONTWRITEBYTECODE=1 python3 tests/juiced2_wheel_contract_checks.py
```

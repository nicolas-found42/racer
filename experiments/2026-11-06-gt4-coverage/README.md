# GT4 corpus metadata coverage audit

Current question: which of the 730 pinned GT4 catalog rows have supported metadata and actual validated preparation, and which structural/data extremes belong in a bounded representative cohort? Parent owns model acquisition/preparation/GPU and registry publication. This leaf reads retained catalog/exporter/native SpecDB evidence, preserves all canonical inputs, and produces metadata only.

Before execution: each command <=300s, this leaf <=128MiB additional output, selected native member <=16MiB and <=32MiB per extraction batch, free space >=20GiB. No full model corpus download, no native game execution or desktop focus, no shared REA active-target changes. Verified catalog SHA fcd6eb5badd4cc120da3daaae315e83b71fb2b9400062b371b73c9f42a442e6c. Historical evidence retained. Ordinary source discovery uses jg with explicit scripts root, maxrequests8000/concurrency20. Native/source dimensions remain distinct from real manufacturer specifications.

## Result and scope

All 730 pinned GT4 catalog codes join through native EU GenericCar, DefaultParts, CarVariation, Variation, Chassis and tire tables. All 730 match the adapter dispatch tuple; this audit prepares **zero** models and establishes **zero** native game/runtime validations. The root-owned eight-model preparation/render cohort is separate evidence. Names, paint variants and raw game fields are not manufacturer specifications or a proved playable roster.

`output/coverage-audit-v1.json` contains all 730 complete row chains, source dimensions/flags/tire bytes, native member offsets/hashes/roles, preview pins and an explicitly labelled X/Z placement hypothesis. Y placement is unknown here. Native WheelLayout is 0 for 728 records and 2 only for `benz0001` and `daih0017`; no native consumer proof establishes what 2 means. Standard NSX `acra0014` and Z `niss0004` both have value 0.

The exact name/code joins reproduce the historical-car conflict; this is not explained by a simple catalog name swap:

| Model code | Generic label | Chassis row | Raw WB | Raw tread F/R | Raw WheelLayout |
|---|---|---:|---:|---:|---:|
| benz0001 | patent_motor_wagen_886 | 2340 | 1450 | 1449 / 1449 | 2 |
| dmlr0001 | motor_carriage_886 | 2341 | 1300 | 50 / 1209 | 0 |
| daih0017 | midget_mp5_63 | 2409 | 1905 | 151 / 1271 | 2 |

The declared hypothesis `centre track = (raw tread - 5 * raw tire width byte) / 1000` reproduces known exporter centres: NSX 1.508/1.539 m, Z 1.534/1.534 m, Benz 1.399/1.399 m, Daimler 0/1.159 m, Midget '63 0.011/1.131 m. This does not prove native units, runtime wheel topology, MDLS frame conventions or factory dimensions. It identifies an exporter/adapter assumption requiring a separate native consumer or actual wheel-position proof. Do not repair the zero track by forcing four wheels or swapping names. CHASSIS width/dwidth and VARIATION four-float field semantics remain unresolved; their raw values are preserved.

The source index has 673 vehicles with the five standard roles; 43 additionally have open-model and 14 additionally have open-model plus open-wheel. Showroom previews do not validate race/open variants. The only duplicate display name is Ford GT '05 (`ford0006`, `ford0015`), which remains two source identities. The field-selected cohort is 11 previews totalling 15,332,400 bytes: benz0001, daih0017, dmlr0001, jay_0001, toyt0047, dodg0009, auni0001, tvr_0006, ford0007, peug0003, dodg0007. Selection reasons are retained per code (topology flag, raw dimension/mass extrema, preview size/triangle extrema and paint-row count); it is not an installation recommendation.

## Source and implementation authority

Pinned carmodels commit `ce047799fc550cdf92e4f7b62d97ef5c603e53ad`; native index SHA256 `d6483838ea99983fde8223588475aef1c74ca1b2b1ce66319a7611709a3381c3`. Index source is EU `SCES_517.19`, ISO 5,660,540,928 bytes, SHA256 `efcb2ac8428be5f4c67f3d5e97f941f4c267015ab92ea0cc1c624d75cb830ef5`, GT4_EU2560. This is **not** the retained canonical US ISO: its prior US2560 GenericCar table has 722 rows. No cross-build row-ID equivalence is assumed.

Nineteen metadata files total 1,562,592 bytes. `output/metadata-acquisition.json` SHA256 `6809009a63f69e6fe6c069c86e5fbee88f0a7944852800701adf3969b0f3b40c` retains the pinned URLs, Git blob identities, SHA256, original ISO ranges and packed/unpacked hashes. The new reader verifies this exact manifest and all table hashes. The extraction index reports source identities; this leaf did not independently re-read the EU ISO ranges. Native member data remain retained unchanged.

`scripts/gt4_metadata.py` is a bounded, independent stdlib reader using separately fetched/screened Nenkai/PDTools C# format/schema definitions at commit `2a9637d8c36100e4c211d73cd8140a9d690578d2`. Sources and complete screen responses are retained as `output/pdtools-*.cs.json` and `.reference`. No upstream C#/Python decoder is executed. Input cap 16MiB/file, decoded cap 16MiB/table and 32MiB/batch, row/string/index bounds, exact table-ID joins and duplicate/model identity rejection are enforced. Repeated Variation row IDs are preserved as paint rows.

The separately fetched carmodels `gt4_specdb.py` received a Jev **block** (injection .76; no exact passage identified). Its exact bytes and response remain quarantined in `output/gt4_specdb.py`, its blob receipt, and `output/specdb-source-screen.json`. It was never executed/imported; after the block it was not used as implementation/analysis authority. No reroll or partial rescreen occurred. Human review is still pending. The PDTools route is a distinct independent primary source, with complete separate screening records.

## Verification and reproduction

Run from the repository root; each command completes in under 2 seconds on the observed host:

```sh
python3 tests/gt4_metadata_checks.py
python3 scripts/audit_gt4_coverage.py --catalog experiments/2026-11-05-car-models/output/source-catalog.json --native-index experiments/2026-11-06-gt4-coverage/output/cars-index.json --metadata-folder experiments/2026-11-06-gt4-coverage/output/specdb-eu --metadata-manifest experiments/2026-11-06-gt4-coverage/output/metadata-acquisition.json --output /tmp/gt4-coverage-new.json
```

Output creation is exclusive; use a fresh output path. Eight offline checks pass: raw rows, template/literal/patch compression, long Huffman codes, malformed patch/template/row offsets, decoded amplification caps, exact pins/symlinks, strings, all 730 native joins, missing/duplicate model joins and cross-build mismatch rejection. `output/rea-metadata-tests.json` retains target-free REA controlled replay `ev_4d8353c3dfa663e2f31a179dedb0ae6931c65a76627d9ad28700f830b67bf367`, exit 0 and eight tests passed. Terminal content is complete; REA flags process sampling partial and no filesystem tracing. This validates the audit utility, not the donor game.

Retention: canonical input tables, index, source references/screens, decoded report, audit report and REA evidence retained; this leaf currently occupies about 11MiB. No source models or native active binding changed.

Resume: metadata audit is ready for independent review. Root owns the eight-model GLB/render cohort and any per-entry eligibility decisions. Next native question is the MDLS WheelPosRelated/placement consumer for benz0001, dmlr0001 and daih0017; no authoritative wheel frame was established here. Do not promote unusual topology based on generic adapter acceptance. The quarantined decoder remains blocked pending human review.

## Follow-up: Model T and Tank native draw evidence

Root pixel review found visibly incorrect Model T floating components, Tank Car wheel placement, and Benz topology. These remain source-specific adaptation holds, not permanent exclusions. Public pinned `dealership/public/gran-turismo-4` contains only index.json and previews; the advertised native ZIP paths are absent. [Git directory response](output/public-native-availability.json) establishes that limitation; do not retry guessed ZIP URLs.

Using the existing **US** volume index and its own offsets, [bounded extraction](output/extract_us_special_models.py) selected just two menu CAR4 members (1,136,584 decoded bytes total). Both are byte-identical to the exact EU sources named by the previews:

| Code | US ISO offset | Decoded bytes | SHA256 |
|---|---:|---:|---|
| ford0013 | 338829312 | 521736 | b9700e7725fa482fad6303c107bc8a16cda7caf4d76c0ea04fb894cbcefc06f3 |
| jay_0001 | 361437184 | 614848 | d488732215bff72abb9a78752fef1ea541f5b188909cb5b70daaab5aee49d895 |

[Receipt](output/native-us-selected.json) records packed hashes, exact lengths, qualified raw-DEFLATE EOF/no-tail checks and unchanged input file metadata. Native members retained in `output/native-us-selected/`. This selected-data identity does **not** equate EU/US executable addresses.

Separately screened geometry sources `gt4_glb.py` (pass injection .13) and `gt4_model.py` (pass .19) establish the current upstream preview contract. The exporter always adds four wheels from inferred SpecDB placement and supplies the same translations to callbacks11–14. It does not branch on raw WheelLayout. Other callback matrices and VM operations are ignored. TirePosRelated is explicitly unknown/unused. No quarantined SpecDB source was used. Geometry source Git blob `4176b05e7c1d9483551a5e68f92026bbdf90faf4` is checked before executing its manually reviewed, stdlib-only shape/VIF decoder for the selected native bytes; the retained `.reference` adds one formatting newline, which the verifier removes before the exact Git identity check.

[Own command tracer](output/trace_special_commands.py) inventories exact native commands, stack transforms, callback dependencies and draw offsets under LOD0/branch0. [Draw/vertex join](output/join_special_draw_vertices.py) compares indexed triangle multisets against actual pinned previews. [Full evidence](output/special-draw-vertex-joins.json):

- Model T: all 3,475 body triangles exactly reproduce the preview from native packets and exporter transforms. Floating upper shapes8/9 draw at5168/5176 under callback31@5133, following Translate(.7785000205,1.2611446381,-.1661704779) and RotateX(85.74313354)@5155. Their exported bounds reach Y2.373802. Shapes5–7 similarly depend on callback30@5019 and angle−88.15784454.
- Tank: all 3,744 preview body triangles have native geometry witnesses. Current screened exporter omission policy reproduces3,504; an extra240-triangle set exactly duplicates native shapes37/38/39 (kind1, kind2, kind0/depth-off). This is an observed legacy-preview/current-policy discrepancy, not a claim of complete current-code reproduction or permission to hide a part. Several narrow components depend on callbacks20/24/28–32. Callback11–14 geometry is placed using the same generic inferred wheel centres as the separately added wheel meshes.
- Neither selected body path contains opcode19, so its upstream omission is **not** demonstrated as the cause of these two defects. Both paths contain opcode89 VMCallback values36–39; native callbacks15–18 and20–32 are also present. PDTools primary callback definitions identify tire/wheel operations and note matrix-dependent callbacks20–30, but do not recover the required rest matrices.

The primary `Cmd_pglRotateX` definition says it follows glRotate, and a callback `RotateZ` recovered-code comment multiplies engine radians by57.29578 before invoking pglRotateZ. Upstream uses raw angle values directly in radian sin/cos. [Separate degree-aware replay](output/special-command-traces-degrees.json) therefore tests a concrete angle-contract discrepancy, while retaining unknown callbacks as unknown. It moves Model T parts toward callback-local origins and **does not** restore a complete valid car: the missing callback rest matrices remain necessary. No degree-only candidate is represented as fixed, and no arbitrary geometry repositioning, hiding or four-wheel coercion was applied.

Verification commands (under2s each): `python3 output/trace_special_commands.py`, `python3 output/trace_special_commands.py --degrees`, `python3 output/join_special_draw_vertices.py`, from this experiment directory. Source decoder imports no SpecDB module. Tracer/parser output is analysis evidence; no native game executed or active REA binding changed. The first independent join probe exposed Tank's240-triangle discrepancy; it is retained as an explicit result rather than weakened into an exact-replay claim.

Current resume: independent metadata and exact native draw joins are delivered. Root owns reviewed installation holds. Full repair still needs the actual CarModel matrix/wheel callback consumer or a separately justified source-frame adaptation with independent review. The retained old REA snapshot is metadata evidence; its prior generic MIPS-I lane had EE-instruction/function-discovery limits. No new broad/cold executable import was started merely to fill that gap. Existing GLBs, screenshots, native sources and quarantined helper remain unchanged.

# Canonical SLRR chassis coverage audit

Question: distinguish the single public Furrano preview from current canonical extracted game car/chassis definitions and the one source-backed static assembly. Canonical input ../raw/slrr-231; no bulk extraction/download/models/GPU. Read-only selected package/CFG/Java/class identity audit, ≤300s/command,≤16MiBnewoutput,16MiBperfile,32MiBselectedsource initial budget. Source names alone do not establish playable roster. Record exact RPK nativecar/script links and source hashes, missing/unparsed coverage explicitly.

Resume: audit top-level cars/racers RPK resource declarations, main CFG topology and corresponding source class inheritance; compare one assembled Furrano scope.

## Current evidence

`output/canonical-chassis-coverage.json` retains25top-level racerRPK hashes and70native `car` resource declarations, each linked to exactCFG, compiledclass andJava sourceSHA plusparentmodels→Chassis inheritance. All70_mainCFGfiles are linked; everyCFG contains one `chassis` command and four `wheel` frames. Counts derive resource/class/native links, not foldernames. Sourcebytes read3,756,006 (<32MiB), newinventory~184KiB; all25packagesparse, no unavailableclass/Java/CFGlinks.45Java sources contain literalbanned=1; allavailability/descriptor/nativeexecution remains unknown. Packagecounts are familycontainers, not25or70verifiedplayercars.

ExistinggenericCFGparser successfullyparses27/70;43reject nativehexresource IDswith `r` suffix (e.g.0x000000E3r). RawCFG paths/hashes/commandcounts are retained evenwhenparserfails. This is a concreteadaptergeneralization gap, notsourceabsence. No sourceparserchanged underthis read-onlyinventoryscope. Firstaudit assignedCFGidentityonlyafterparsing, incorrectlyreported43unlinkedpaths; correctedidentityretainedbeforeparse shows0unlinked. Rawstandalonecommandcountregex initiallymissedCRLF; corrected includesCR andconfirmsall70chassiscommands. These are inventorytool errors, notnativegamefailures.

## Furrano and public scope

`output/furrano-source-links.json` shows two distinctnativechassis: resource6 aliasFurrano_GT54 scriptFurrano_GT54.class/_main_GT54.cfg andresource343 aliasFurrano scriptFurrano_GTS.class/_main_GTS.cfg, bothpackageSHA63d7ec06f22b2176d476980e1fa66df823e9a6e8bac915474c9f292c622b89ec. GT54JavaSHA/nativeCFG/class/parenthashes are inthatreport. Existinglocal32-nodevisibleassembly SHA64b977dab3ab894e523406b4e6af13ee51677af366bef326370a8baba4f98b7c (`output/existing-assembly-scope.json`) usesGT54CFGparts plusJava-selectedwheels/exhaust. It doesnot executearbitrarydescriptor-dependentstockassembly. Engine/battery/pedals/suspensioninternals/nativeequilibrium are incomplete/unverified; GTS andother68declarations have no reviewedcompleteassembly inthisaudit.

The retainedpublicpreviewcatalog SHA fcd6eb5badd4cc120da3daaae315e83b71fb2b9400062b371b73c9f42a442e6c contains1435rows acrosssixfamilies andZERO SLRRrows (`output/public-catalog-scope.json`). Therefore a separate“onepublicFurranopreview” is not a rosterlimit or evidencedbythiscatalog; existence/count ofanyseparatepublicsurface remainsunknown inthisno-downloadtask. One reviewedlocalFurranoassembly and70canonicalsourcechassisdeclarations are distinctcoveragelevels.

Coverage: racerRPK/nativeCFG/classidentity inspected; stockdescriptor/Javabehavior source-linkedbutnotexecuted;43CFGtypedparses blockedformat;traffic/fake_racers/ROC savedinstances explicitlyexcludedfromplayerdefinitioncounts andnotinspectedbeyondpresence. Nativefullassembly/render/physics for69otherchassis uninspected; noallcarscompleteclaim.

Reproduce fromrepo:
```sh
python3 experiments/2026-11-06-slrr-coverage/output/audit_scope.py
python3 -c 'import json;d=json.load(open("experiments/2026-11-06-slrr-coverage/output/canonical-chassis-coverage.json"));print([(r["alias"],r["cfg"]["path"],r.get("cfg_error")) for r in d["chassis"]])'
```
Resume: extendtypedresource-IDsyntaxwithfocusedtests inaseparatelyauthorizedimplementation; chooseoneadditionalchassis exactsourceclass/stockdescriptor beforeassembling. Preservecanonicalsource, sourcehashes andcurrentFurranoassembly; no bulkdownload/export.

Authorized parser follow-up: retain old43failureaudit unchanged; inspect primary pinnedreference CFG parser and canonical resource/classlinks, then implement strict uint32resource-token parsing only for resource-bearing commands. Newauditv2 and pinnedFurrano exact-outputregression required; no newassemblies/publication.

## Implemented resource qualifier support

Pinned primaryreference `https://raw.githubusercontent.com/nedobylskiy/SLRR_rev/642945c69a38f9c632d3a6009ba18e1bbab1c7f6/src/formats/cfg.ts` retained `output/reference-cfg.ts` explicitly acceptshexadecimalresourceIDs withoptionalr/R thenparseuint32. Jevexternalcontentscreen pass,injection.02 (`reference-screen.json`). CanonicalCFGsource proof `resource-qualifier-source-proof.json` retains1020qualifiedoccurrences;976matchexactbinarylocalRPKresourceIDs/aliases,44external/unresolvednotclaimedresolved. ExistingJava usesqualifiedresourceconstants too. This supports lexicalnumericidentity, notoriginalnativeparserexecution.

Minimal `scripts/slrr_vehicle.py` resource_id helper acceptsunsignedplainhex/decimal orhexr/R uint32; onlyresourcepositions attach/compatible/stockpart/render/deformable changed. SlotIDs/slottype unchanged. `tests/slrr_resource_literal_checks.py`4tests rejectmalformed/negative/overflow/unexpectedqualifier/decimalr, verifyqualified/plainidentityacrossallresourcecommands. Existing5assemblychecks pass.

Actual sourcepinned `output/audit_scope_v2.py` verifiesold25RPKhashes+70CFGhashes beforeacceptingall70typedparses; results `canonical-chassis-coverage-v2.json`, `audit-summary-v2.json`. Historical`canonical-chassis-coverage.json` retains43parserfailures unchanged andoriginalauditscript nowrefusesoverwrite. ExactFurranoregression `output/furrano-parser-regression.json`: regeneratingassemble() fromcanonicalsource yieldsbyte-identical64b977dab3ab894e523406b4e6af13ee51677af366bef326370a8baba4f98b7c,32parts,2,894,175sourcebytes. No newmodelassemblies/catalog/publication/nativeexecution.

Currentrecheck:
```sh
python3 tests/slrr_resource_literal_checks.py
python3 tests/slrr_vehicle_checks.py
python3 experiments/2026-11-06-slrr-coverage/output/audit_scope_v2.py
```
Resume: independentminimalparserreview;70parses stillarenot70complete/playableassemblies. Priorremainingstockdescriptor/Java/engine/suspension/nativephysics limitations persist. Nextcarassembly mustseparatelyprovecompletepartownershipandstockselection.

## Independent resource-literal review

No actionable defect found in the bounded lexical change. Four resource-literal and five existing assembly checks pass; extra probes reject r-qualified slot types, attachment parent slots and render/wheel pose values. A separate direct binary RPK-record reader verifies all25 package hashes, all70 unchanged CFG hashes and typed parse results, every1020 qualified resource occurrence, and976 exact local uint32 ID/alias joins. The other44 remain external/unresolved. In-memory assemble() regeneration is byte-identical to retained Furrano64b977…b7c,32parts, with no original or model output rewritten. Evidence and reproducible checker retained output/independent-resource-review.json and independent_resource_review.py. Own first probes needed semicolon-comment tokenization and null unresolved-alias normalization; these were checker assumptions, not producer defects. No native/GPU/catalog actions. Resume: root owns CMake registration;70 typed parses still do not establish complete player assemblies or native parser execution.

Independentresourceparserreviewclosed: `output/independent-resource-review.json` verifiesownrawRPKreader25packages/70CFGs/1020qualifiedtokens/976exactID+aliasmatches/44unknown,4+5tests, exactFurranoGLTFregeneration. Extra numeric-fieldprobesrejectroutside resourcepositions. No actionableparserdefect; no produceredits/nativeGPU.

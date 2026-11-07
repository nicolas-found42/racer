# SLRR Furrano resource chain
Question: resolve actual supported RPAK512 entries into package-qualified mesh/texture source chains while retaining repeated texture order and null slots.
Target canonical ../raw/slrr-231/cars/racers/Furrano.rpk, companion shipped Furrano.rdb and _main_GTS.cfg. Each command<=300s, selectedmember<=16MiB, aggregateinput/extraction<=32MiB, output<=256MiB, free>=20GiB. Read-only, no nativeREA session or GUI mutation. Status: validate binary table against native bounds and shippedRDB text before emitting asset references.

## Result and retained evidence
Implemented `scripts/slrr_resources.py`, a bounded read-only parser/resolver for the observed RPAK512 text-RSD layout. This is an independently bounds-checked interpretation of shipped bytes, corroborated by the shipped text RDB, not a claim of complete native RPK semantics. The retained upstream SCX importer describes mesh material indices but supplies no RPK specification.

`output/rdb-corroboration.json` records exact hashes and equality of all 336 binary (ID, kind, alias) records with all 336 active shipped RDB records (one fully commented record excluded). Header: 16 bytes, ten 64-byte external-package records, four u32 table fields at 656, variable descriptors at 672..12221. Each descriptor has 23 fixed bytes followed by a NUL-terminated alias; its offset/length selects a bounded nonoverlapping text payload. All actual Furrano ranges pass. Duplicate IDs A10E, A02B, A21B and F7 occur in real input; native precedence remains unknown, so ambiguous resolution reports all candidates rather than selecting a winner.

`output/furrano-body.json` retains the actual source chain, descriptor and payload offsets/hashes, ordered references and all input hashes. Furrano.rpk SHA256 `63d7ec06f22b2176d476980e1fa66df823e9a6e8bac915474c9f292c622b89ec`. Body resource 0x46 resolves mesh 0x47 to `cars/racers/Furrano_Data/meshes/chassis.scx` (342900 bytes, SHA256 `e02939ea8dba386e91633806973f18a9aeb74df4fad73e639cf81260961b50d8`). Its five texture references, in original order, are:

1. External 0x00020025 → `cars.rpk:0x0025` → `cars/textures/default_white.png`.
2. Local 0xBBCC → `Furrano_clear.png`.
3. Explicit null ID 0.
4. Local 0x48 → `Furrano_frame.png`.
5. Local 0x4A → `Furrano_dasboard.png` (shipped spelling).

The declaring package's explicit external table determines package identity; IDs are never flattened globally. Repeated texture references and null slots survive resolution. `_main_GTS.cfg` separately references deformable 0x46, mesh 0x47 and default texture 0x00020025; the latter does not replace the deformable resource's five ordered material references.

## Reproduction and checks
From repository root:

```sh
python3 tests/slrr_resource_checks.py
python3 scripts/slrr_resources.py --root ../raw/slrr-231 --package cars/racers/Furrano.rpk --resource 0x46 --output /tmp/furrano-body-new.json
```

Actual resolver run succeeded: 838733 unique input bytes read, no inputs modified or copied. Fixture checks PASS (`output/checks.txt`): malformed headers/counts/truncation/ranges; package scope; exact repeated-reference order and null; ambiguous IDs; cycles; absent resources; traversal/absolute/drive/symlink containment. Per-file limit 16MiB, aggregate reads 32MiB, 64 packages, depth 16, 65536 descriptors/package, 4096 commands/payload and 4096 characters/line. Outputs contain source paths/hashes and descriptors, not asset copies. Evidence remains local ignored experiment output and committed-intent script/tests/record; no external upload or runtime execution.

## Resume / limitations
Ready for parent renderer integration using the retained exact source chain. This establishes asset association, not visual correctness or native material/shader behavior. The renderer must preserve material texture indices, null semantics and repeated references; generic RPK versions, binary RSD, shape/physics interpretation, duplicate-ID native precedence and unsupported source commands remain unresolved. Current parser refuses unsupported/corrupt layouts; it does not guess missing assets. No native REA session or desktop activity was used. Next action: parent loads these exact sources with existing SCX support and captures the resulting body/material rendering headlessly.

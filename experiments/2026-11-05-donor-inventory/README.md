# 2026-11-05-donor-inventory: establish interview evidence

- Status: initial inventory and design rounds completed; shared-understanding confirmation pending. Implementation has not started.
- Question: which source-game artifacts and development prerequisites are available, and what can bounded static inspection establish for the design interview?
- Targets: canonical inputs under `../raw/`; names alone do not verify edition, platform, or behavior. Full inventory and selected hashes will be recorded in `output/`.
- Existing identity: `../INPUTS.json` records MC3 Xbox, XDK 5849 retail (historical project identification), 4,840,554,496 bytes, SHA-256 `d58490dc8e1837e9f47716268b52ae1f1ac8578e5a5e42e061fa7f1c4b068b52`; revalidation pending.
- Tools: local filesystem/Python inspection and shared REA MCP; actual versions/provider and exact operations will be appended.
- Working directory: `/Users/nicolas/Documents/github/reverse-engineering/games/racer`.
- Limits before running: each initial probe at most 300 seconds; combined generated output at most 256 MiB (target under 10 MiB); memory target at most 2 GiB; no bulk extraction, runtime launch, acquisition, or input changes. Large-file hashing is bounded; incomplete coverage stays explicit.
- Storage preflight: `df -h .` reports 431 GiB free; `du -sk experiments ../raw` reports 8 KiB for experiment records and 39,338,336 KiB allocated for originals. Existing Racer generated output and saved analysis state are absent. Hub checker will measure managed lab roots before captures/exports.
- Output: `experiments/2026-11-05-donor-inventory/output/` (ignored). Canonical originals remain in place; all supporting evidence is retained.
- Commands before investigation: read hub/project instructions, README and setup experiment; `git status --short`; `git rev-parse --show-toplevel`; `git log -1 --oneline`; `ls -la ../raw`; preflight above. Git root is independent; no commits exist and all scaffold files were already untracked.

## Questions and evidence status

1. Source inventory, exact identities and duplicate/edition relationships: pending.
2. Installed host/build tools relevant to engine choice: pending.
3. REA static evidence for candidate contribution areas: pending; no gameplay behavior verified.
4. User decisions: first delivery scope, platform, C++ boundary and import policy asked in round one; no answers yet.

## Retention

Keep canonical inputs, this record, inventory manifests, REA evidence, and any saved analysis state. No deletion or replacement of existing files is planned.

## Next action

Confirm [PLAN.md](../../PLAN.md), then start a separate implementation experiment for the agreed SDL3/bgfx/Metal grid. The first inventory is complete within the boundaries below; the source games' runtime behavior is not verified.

## Executed probes and retained results

All paths below are under `output/` unless stated otherwise. Canonical sources were left unchanged. The final records below supersede the initial pending checklist.

- Filesystem/stat inventory: 35,528 files, 40,163,671,374 logical bytes; 0.530 s. `filesystem-inventory.json` records paths and sizes. These counts include compressed carriers and unpacked images; they are not unique-content totals.
- Full hashing of nine selected canonical files: four images, two .7z carriers and three SLRR main/backup executables; 14.31 s, bounded to 300 s. `selected-sha256.json` records full values and coverage. MC3 matches the historical manifest. No directory-content digest was inferred from selected hashes. Updated hub `games/INPUTS.json` with unregistered sources and unknown provenance/build fields; existing MC3 identity record preserved. Curated hash reference: [source-inputs.json](../../references/source-inputs.json).
- Read-only headers, archive/disc listings and host versions: `headers-and-archive-listings.json`, `disc-root-listings.json`, `text-metadata-and-tools.json`, `host-tools.json`. Exact argv/status/output retained. Each helper timeout at most 30 s. Host: macOS 27.0.1 arm64, Apple clang 21.0.0, CMake 4.4.4, ninja 1.13.2; installed raylib 6.2 and SDL3 3.4.18.
- Selected disc extraction: `probe-log.json` declares bounds of 300 s, 16 MiB/member, 32 MiB total. Five named files extracted using xdvdfs-cli 0.8.3 `info`/`copy-out` or bsdtar `-tvf`/`-xOf`; 19,974,837 bytes, 0.077 s. No bulk extraction. `disc-probes/` retains MC3 XBE, Juiced2/MCLA XEX, GT4 boot ELF and SYSTEM.CNF, with original/extract linkage and hashes in the log.
- SLRR manual HTML → text: Python HTMLParser, reading three named existing documents, preserving original hashes in `slrr-manual-text.json`. Documentation establishes intended UI/feature descriptions, not observed binary behavior.
- Local controller inventory: `ioreg -r -c IOHIDDevice -l`, 15 s timeout; retained only unique Product strings in `hid-products.json`, no serials/identifiers. No recognizable gamepad observed; actual controller verification remains outstanding.
- Library comparison: primary official docs retrieved via Firecrawl/developer search and selected official source/release metadata; evidence and exact retrieval descriptions in `stack-evaluation.md`. No dependency downloaded or installed in this investigation. Godot was subsequently explicitly excluded by the user; raylib was not selected. User selected SDL3 + bgfx after comparison.
- Donor manuals: publisher material on third-party mirrors; `donor-documentation.md` retains sections/pages, URLs, retrieval and edition/OCR limits. Firecrawl rate limits were handled with web reading. No manual scans or game media downloaded to the workspace.
- Shipped SLRR source: `jg files /Users/nicolas/Documents/github/reverse-engineering/games/raw/slrr-231/parts/scripts --list`, followed by one semantic search with `--max-requests 8000 --concurrency 20 --max-output-bytes 20000`, subprocess timeout 120 s. Actual query/argv in `slrr-jg-command.json`; finished in 4.64 s. `slrr-jg-result.txt` ends `End context.` but explicitly omits 105,004 bytes; discovery remains incomplete. Focused reads supply the cited facts, not unseen search output. `slrr-source-findings.md` records exact source paths/lines/hashes, fitment/tuning observations and native-method/build-correspondence unknowns.

## REA operations and evidence

Shared MCP was used directly; no registration changes or deep native session/database opened. REA runtime identified itself as **6.8.0**. Actual providers: safe artifact graph v1, PE import parser v1, PE/ELF export reader v1, analysis view v1, process capture v3.

| Operation | Exact scope and result | Evidence ID |
|---|---|---|
| `inspect_desktop_application` | slrr-221 canonical directory, summary, max_entries 30000, max_probe_bytes 33554432; 9,094 entries, 648 probed bytes; complete within scan | `ev_6bfe0fd3e279ad1f5ccd5e30be2b64aa33d4368f072709bdf7dc3aac34522964` |
| `inspect_desktop_application` | slrr-231, same bounds; partial at 20,737 entries due to 32 MiB metadata representation budget; no attempt to equate this with complete content coverage | `ev_d1d2aa1691bcb4d7d71959ad7055388526ba11ef6feaef672e156c0bf56dc353` |
| `inspect_pe_imports` | slrr-221/StreetLegal_Redline.exe, max_file_bytes 4194304, max_dlls 100, max_functions 4000; x86 PE32, 10 DLLs/194 functions | `ev_e85ae07d4105c6fd82a6d7d2fda53ee63003b9e9752f2ed8c03daec7392764db` |
| `inspect_pe_imports` | slrr-231/StreetLegal_Redline.exe, same bounds; x86 PE32, 12 DLLs/202 functions | `ev_7a1bbca51932b9245a466ee590d6b32154ed6990576a426829936a9a98f9b0d2` |
| `inspect_native_exports` | extracted gt4-SCUS_973.28, max_file_bytes 1048576, summary; MIPS32 little endian, no dynamic symbol table | `ev_37021a6de2143cc75eab9c88184ceaace1d8353f90816b49b7a4b224c9d33442` |
| `capture_process_scenario` | `/usr/bin/file` with the three selected XBE/XEX paths; timeout 10000 ms, idle 2000, settle 100, finalization 1000; output 32768 bytes, 4 process samples, 8 files/16384 bytes/depth1; exit 0, complete terminal output | `ev_fd9d1c2c832da18ab9fc858e1807e6ba9eab7d5504e51d7cb40351a1d0f9c728` |

The process capture observed the **file-classification utility**, not game execution. Its process sampling was incomplete and filesystem effects were unobserved; retained limitations remain in the canonical Evidence. The extract hashes in `probe-log.json` identify game files; the capture's executable digest identifies `/usr/bin/file`.

`get_evidence_bundle(detail=summary,limit=20)` was rejected because limit is only accepted for records/links. Corrected to summary without limit; 13 retained records, no missing direct links. `export_evidence_bundle(path=<this experiment>/output/rea-evidence.json)` succeeded: **17,231,730 bytes, 13 records, 4 unknowns**. Preserve this bundle. No opened native session required closing.

## Findings and limits

Four source discs and two SLRR variants were inventoried. Both .7z carriers list the names of the existing loose images, but payload equality is unverified. Exact source editions/builds remain qualified: MC3 XBE names DUB edition, while the historical manifest says Remix; MCLA Complete Edition appears in its filename and external manual, not independently verified local metadata. GT4 SYSTEM.CNF VER=2.00 is a configuration value, not a proved release version.

The initial engine/handling blocker was revalidated and resolved through interview decisions: native macOS C++/CMake, SDL3/bgfx/Metal, approachable grip handling, keyboard and gamepad. All first-playable product decisions are now in PLAN.md. Every donor family has an accepted contribution direction in [donor findings](../../findings/donor-contributions.md), supported by documentation/static source at the stated authority. No claim of verified runtime behavior, extracted physics, usable game assets or import compatibility follows.

All initial questions are answered within inventory/documentation scope; runtime/build-correspondence questions remain unresolved and are explicitly later investigations. No code, engine configuration, external publication, game launch, input deletion or tool installation occurred. Initial scaffold files were already untracked; no commits or pushes were performed.

## Retention and validation

Keep originals, selected extracts, all supporting JSON/text, the complete REA bundle, curated findings and source hashes. No generated evidence was classified disposable. Standard output was about 41 MiB before final text additions, below the 256 MiB experiment ceiling. No saved native database exists. Hub measurement and final documentation checks follow below.

- `git diff --check`: exit 0 (initial project files remain untracked, so this is not a full untracked-content check).
- Python JSON parsing and required-document presence/nonempty checks: PASS.
- Hub `python3 tools/check.py`: PASS; Racer/lab managed output **42,299,059 bytes**, free space **462,515,830,784 bytes**. Historical/nonstandard lab roots remain outside this check's coverage.
- No game compilation or gameplay test is applicable before implementation. Project remains a separate Git checkout.

## Handoff fulfilled

User confirmed PLAN.md ("Yes — implement this plan"). First playable is implemented and verified in [the implementation experiment](../2026-11-05-first-playable/README.md). Earlier pending-confirmation entries describe this investigation's original checkpoint.

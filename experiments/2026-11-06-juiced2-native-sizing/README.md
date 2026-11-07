# Juiced 2 native tyre sizing: static PPC trace of f4

Question: where does renderer 820F1DB0 get `f4` (`[[context+684]+192]` / `+176`), and does it justify the f4=1 assumption used for native sizing outputs?

Target: Oversteer retained decoded text section `decoded-sections/82070000-.text.bin` (read-only; hashes in output/inputs.sha256; decoded-image qualifications from the wheel-consumer experiment apply: exported .rdata differs by 43 bytes). Tooling: Homebrew LLVM 23.1.3 `llvm-mc --disassemble -triple=powerpc64 -mattr=+altivec` (ppc64 BE; no VMX128) plus raw-encoding scans in `ppc_scan.py`/`ppc_dis.py`. Limits: CPU-only, seconds, output < 1 MB, no source-game execution. Provider: llvm-mc, not REA (REA lacks PowerPC for this target).

Result (static, one build):
1. `stw rX,684(rY)` occurs at 8 sites (output/stw684.txt). The one belonging to the wheel/render context is `820f0c6c` in constructor `820f0a28` (entry thunk `820f0a18`): `mr r26,r4 ... stw r26,684(r31)`, so **context+684 = the constructor's second argument (an owner object)**, not NULL. The 821BC5xx NULL stores in the earlier note are other classes sharing offset 684.
2. The constructor is called at `8219b620` with `r4 = [r28+44]`; that field is set at `8219b5c8` from a 9672-byte (0x25C8) allocation constructed by `82109860`. The wheel constructor itself writes `stfs f0,9656(r26)`, inside that object, so the owner is the **car object**. A second caller is `82103ea4` (r4 = r28).
3. In the car constructor `82109860`, `stfs f31,176(r31)` (`821099f0`) and `stfs f31,192(r31)` (`821099f4`) store f31 = `lfs [0x8204cb10]` = **1.0f** (decoded .rdata). Copy-construction paths (`82109f1c/f44`, `8210a618/640`) copy +176/+192 from another car object.
The constructor default is 1.0, but this is NOT the only writer (see the 2026-11-07 REA-skill pass below), so it does not establish f4=1 for any specific car.

Limits / unresolved: no dynamic evidence; override sites for the car class not attributed; multiplier 0x824CBE70 writer still unlocated; the native radial/xscale factors do not reproduce the per-car native hub heights (e.g. Charger 0.3364 hub vs radial 0.9335 x 0.3185), so the native table cannot replace the authored hub-height/stock-width fit applied to the four cars; that fit remains an authored substitute.

Next action: attribute stores to car-object +176/+192 by tracing xrefs of `82109860`'s class vtable/callers (and the 0x824CBE70 multiplier) with ppc_scan.py; separately derive the template tyre's native radius to test the radial hypothesis. Only a match would justify replacing the authored fit.

## 2026-11-07 pass under the reverse-engineer-anything skill

Route: REA `open_binary` with `format: raw-binary` rejects `powerpc` (accepted: 6502, x86, x86_64, arm, arm64, m68k), so no REA provider can open this PPC image; analysis stayed on llvm-mc/raw-encoding scans of the same decoded text section (no REA session was opened, nothing to close). Scripts: `car_class_scan.py` (functions touching both +176/+192 and car-only offsets 9656..9668; output/car-class-176-192.txt). Function splitting by `mflr r12` prologue markers (10,985 candidates) is heuristic.

Observations (static, one build): exactly five functions in the car class store +176/+192:
- `82109860` constructor: 1.0f (rdata 0x8204CB10).
- `82109be8`, `8210a330`: copy constructors (copy +176/+192 from another car object).
- `8210d470` (reset path, stores at `8210d640/644`): constant `0.5f` (rdata 0x8201A8E4) under a branch conditioned on a field at [r11+20].
- `82194718` (called from `8218beb4` with this = car, r4 = record key, r5 flag; looks up a manager record via [[0x825778E8]+128]): copies four-float blocks, +164..+176 from source +228..+240 and +180..+192 from source +244..+256, so **f4 (+176 / +192) is the fourth float of each axle block of a looked-up per-car record**, i.e. data-driven.

Inference: f4 is per-car record data (with defaults 1.0 / 0.5 on other paths), so the f4=1 sizing table is an assumption, not a recovered stock value, and the four +228..+256 record fields still need a producer (likely the TyreCode parser) to turn "225/45R18"-style strings into the per-axle floats. That producer, the record lookup key, and the 0x824CBE70 multiplier writer are not yet traced. The radial-vs-hub-height mismatch from the first pass therefore remains untested rather than refuted.

Next action: trace stores to record offsets 228..256 in the TyreCode-parsing function (candidates share the 35 functions that store all of 228..256; start with ones near the string/parse helpers recorded in wheel-consumer/output/parser-sizing-leads.json) and the 82194718 record lookup key; only then recompute sizing with real per-axle f4 and compare against native hub heights.

## Review correction (2026-11-07)

`ppc_dis.py` previously spawned one `llvm-mc` process per instruction with an unbounded COUNT and no timeout. It now makes one call (30 s timeout, COUNT ≤ 4096), maps `llvm-mc` invalid-encoding warnings back to their word (printed as `?`), validates the start address against the text section, and reports a missing `llvm-mc` plainly (override with `LLVM_MC`). Output for `820f0a18` matches the retained `output/ctor-820f0a18.txt` listing. Test: `tests/juiced2_native_sizing_checks.py`.

## Second review corrections (2026-11-07)

`ppc_scan.py mult` previously listed any load/store with displacement `0xBE70` on any base register (5 hits, no `lis` pairing, no `addi`), so it could not reproduce the wheel-args claim of a "lis/addi whole-image scan". It now pairs `lis 0x824D` (and `lis 0x824C` + `ori 0xBE70`) with same-register uses within 40 words, stopping when the register is reloaded, and labels each hit load / store / address-taken: the retained decoded `.text` section gives **4 loads (0x820f5268, 0x8210cf1c, 0x82147dfc, 0x82294dec), 0 stores, 0 address-taken**. The negative result stands, with its limits: `.text` only, 40-word window, no data-flow beyond one register. `JUICED2_DECODED_SECTIONS` relocates the section directory; bad `ppc_dis.py`/`ppc_scan.py` arguments and unknown patterns exit non-zero with a usage line (an unknown pattern used to exit 0). Tests: `tests/juiced2_native_sizing_checks.py` (7).

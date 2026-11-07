# Confirmed donor directions and evidence

Date: 2026-11-05. User accepted the following contribution allocation in Q17. These are later design references, not implemented features or claims of recovered runtime behavior. Canonical identity/hashes: [source inputs](../references/source-inputs.json). Exact operations, limitations and retained evidence: [experiment](../experiments/2026-11-05-donor-inventory/README.md).

| Family | Accepted contribution | Supporting evidence | Remaining verification |
|---|---|---|---|
| SLRR, both supplied versions compared | Modular building, fitment, tuning with measurable effects | Supplied older manual, Garage/Menu Screens: install/remove parts and fine tuning. Newer shipped `Tyre.java:272–299` checks rim dimensions; inflation apply/cancel and wheel parameter propagation are visible. `Transmission.java:219–305` gates tuning and applies/cancels ratios. | Build/source correspondence, native compatibility/dyno methods, actual behavior and part effects. |
| GT4 | Per-car tuning presets and structured driving feedback/tests | Sony/SCEA manual, Race Settings: A/B/C per-car setups. Time Trial/Ghost/Analyzer: recorded driving comparisons; Circuit: practice/free-run. | Supplied disc build versus manual, implementation and runtime details. |
| MC3 | Garage/menu flow and checkpoint route creation | Rockstar Xbox DUB Edition manual, The Garage pp.24–25 and Race Editor pp.22–23. | Original DUB versus historical Remix label; runtime behavior and exact edition. |
| Juiced 2 | Layered livery editing and performance classes | THQ Xbox360 manual, Car Rating p.7; Decal Editor p.8 describes layered editing. | Exact build, scoring/rating implementation, livery format and compatibility. |
| MC LA | Map exploration, event discovery and street challenges | Rockstar Complete Edition manual, Getting Around pp.8–9 and Career Mode pp.10–11. | Complete Edition is not yet independently verified for the local image; implementation/runtime details. |

## Documentation sources

- [GT4 Sony/SCEA manual transcription, third-party mirror](https://manuals.plus/m/e4e3782f870e1d4c5b4e0fe877c47d59bdba3a7a1e5ec060e9629fdf8e778f98). Publisher provenance and section references are recorded in the retained research note; scan not visually verified.
- [MC3 Rockstar Xbox manual, Internet Archive OCR mirror](https://archive.org/stream/xboxmanual_Midnight_Club_3_Dub_Edition/Midnight_Club_3_Dub_Edition_djvu.txt). Covers original DUB Edition; OCR has limitations.
- [Juiced 2 THQ Xbox360 manual, Games Database mirror](https://www.gamesdatabase.org/Media/SYSTEM/Microsoft_Xbox_360/manual/Formated/Juiced_2_-_Hot_Import_Nights_-_2007_-_THQ.pdf). Printed page numbers; converted button glyphs are unreliable and unused.
- [MC LA Rockstar manual, videogamemanual mirror](https://www.videogamemanual.com/xbox360/Midnight%20Club-%20Los%20Angeles.pdf). The consulted manual explicitly names Complete Edition; this does not prove local edition correspondence.
- SLRR bundled manuals remain at `../../raw/slrr-221/SLR Manual_files/`; selected text and original SHA-256 values are in the experiment output. Shipped source paths, line citations and hashes are in `output/slrr-source-findings.md`.

## Evidence discipline

REA established static identities/import/export metadata and retained a controlled file-classification probe; no game was run. Filenames, manual instructions, source parameter paths and runtime observations have different evidential scope. Do not use these findings to claim physics accuracy, donor interoperability, redistribution permission, or an already working importer.

The first grid uses authored placeholder geometry and Racer handling targets. Each donor-inspired subsystem will need its own bounded investigation before later implementation. No direct asset/data import has been approved by this contribution allocation.

# Garage milestone: evidence to design

2026-11-05. Static shipped-source/documentation comparison for [PLAN.md](../PLAN.md). Investigation and retained outputs: [garage implementation experiment](../experiments/2026-11-05-garage-tests/README.md). No donor game was launched, no new binary scan was performed and no donor formulas or assets are imported.

## Revalidated source identity

Canonical SLRR-231 executable SHA-256 remains identified by the selected-input manifest as `f44fb88a4335c657e20701cdb84afb8d1d85f7c3aceb93d30113e6e6e44fefc2`. This pass rehashed the following source files, matching the earlier donor-inventory findings:

| Path under `../raw/slrr-231/parts/scripts/` | SHA-256 |
|---|---|
| `rgearpart/reciprocatingrgearpart/SRC/Tyre.java` | `7cea735bbed7b7135bfae4e99fa502bcaa57562edea0c4b1f30e33976872bb57` |
| `enginepart/slidingenginepart/reciprocatingenginepart/SRC/Transmission.java` | `bbf7cb991786251a732b914415e1e6401d070baf4fb559eddc47c4f9a454b60b` |

`output/donor-source-check.json` retains exact numbered excerpts and hashes. Tyre lines 336–359 load/save versioned inflation; 371–400 copy current inflation into old/new values, edit the new value, restore the old on cancel, apply the new on acceptance and force an update. Transmission lines 230–305 snapshot gear/final ratios and restore on cancel; acceptance includes sign conversion and an update. These are distinct source implementations: Racer uses a uniform isolated draft rather than copying the transmission menu's temporary mutations.

A case-insensitive exact-filename walk under canonical `../raw/slrr-221/` found no `Tyre.java` or `Transmission.java`. This is a bounded absence of those source filenames, not proof their behavior is missing or that packaged scripts contain no equivalent. Direct source-level correspondence with 231 is unavailable in this supplied loose tree.

The corresponding 221 bundled `SLR Manual_files/Garage_Menu_Screens.htm` rehashes to `27ef446dea6257e81d734938913d66bb77b3326896d728bc0d37318971036f87`, matching the retained HTML-to-text record. Its Garage items 2, 9, 11 and 13 describe test track access, car test records, part tuning including gear ratios/tire pressure, and engine/steering testing. Main Menu describes automatic career save on exit and car save/load. It does not establish the 231 draft/cancel implementation or identical mechanics. Exact manual content and identity are retained in `output/donor-comparison.json`.

## Evidence to authored behavior

| Evidence boundary | Observation | Racer design choice |
|---|---|---|
| SLRR-231 Tyre/Transmission source paths above | Tuning values have snapshot/cancel/accept paths; Tyre has versioned persistence. | Applied setup and editable draft are separate. Apply commits, Cancel discards; defaults remain draft changes until applied. |
| SLRR-221 bundled Garage manual | Tuning, driving/test access and car test records share the garage flow. | Garage → measured test → result → garage loop; deterministic automatic measurements plus a player course. |
| Retained GT4 publisher-manual transcription notes, “Race Settings” | Three per-car A/B/C setups are documented. | Three independent setup slots for Racer's single car. |
| Same GT4 notes, “Time Trial / Ghost / Analyzer” | Saved driving feedback and comparisons between matching course/start conditions are documented. | Results retain exact setup values and model/course revision. Automatic schedules are identical; player times are labeled as player runs. |
| Racer's existing authored simulation | It exposes acceleration, braking and steering convergence terms. | 0.8–1.2 multipliers and tests measure those terms honestly. No horsepower, pressure or drivetrain parameter is implied. |

GT4 citation: [Sony/SCEA NTSC U/C PS2 manual transcription, Manuals+ mirror](https://manuals.plus/m/e4e3782f870e1d4c5b4e0fe877c47d59bdba3a7a1e5ec060e9629fdf8e778f98), sections “Race Settings” and “Time Trial / Ghost / Analyzer”; [44-page USA manual scan lead](https://www.videogamemanual.com/PS2/Gran%20Turismo%204%20(USA).pdf). Reused section notes are retained in donor-inventory `output/donor-documentation.md`; that pass read converted/mirrored text and did not visually verify the scan. Button-glyph/OCR corruption and exact local edition correspondence remain limits. This pass's bounded 30-second curl refresh returned a connection-security page (16,401 bytes), with none of the cited section markers; retained as `output/donor-gt4.html`/`donor-gt4-text.txt`. It adds no fresh manual support. The table explicitly relies on the retained earlier section notes and does not claim a new transcription or runtime verification.

## Retained REA scope and unknowns

The earlier complete exported donor-inventory `output/rea-evidence.json` remains canonical. Record `ev_7a1bbca51932b9245a466ee590d6b32154ed6990576a426829936a9a98f9b0d2` is REA 6.8.0 PE import parser v1 identity/import evidence for the 231 executable, not authority for these Java paths or runtime tuning behavior. The planning experiment already found that record absent from the current server ledger but present in the export; this pass does not rescan to recreate it.

Unknown: exact shipped-source/executable correspondence, native torque/dyno and complete fitment effects, donor runtime apply/cancel behavior, and exact GT4 local-build/manual correspondence. Those questions are outside this milestone. No new native analysis session/database was opened. Preserve canonical source, saved REA export, prior manual notes and all new small evidence files; no deletions. Next action: validate Racer's authored setup/test loop against its acceptance checks.

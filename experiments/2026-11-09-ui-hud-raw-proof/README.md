# 2026-11-09 UI/HUD raw proof — every Racer element against the shipped game files

- Status: completed (element set and verification frozen in this leaf; 12 elements have no exact counterpart shipped and are marked)
- Target/build/platform: Racer, branch `feat/vehicle-physics`, HEAD `25533ae`, `src/` clean; native binary `build/racer` sha256 `6eb13e63d6f5045570a842b3a0bff4fda049851eefe2b0bb27a867167f1d1dc9` (mtime before the captures), macOS Metal, `--background --no-diagnostics --profile … --review-script … --screenshot …`
- Canonical inputs (read-only): `games/raw/mc3.iso`, `games/raw/gran-turidmo-4.iso`, `games/raw/juiced-2`, `games/raw/midnight-club-la`, `games/raw/slrr-221`, `games/raw/slrr-231` (hashes in `games/INPUTS.json`). Decoded assets come from the sibling leaf [2026-11-08-ui-source-extracts](../2026-11-08-ui-source-extracts/README.md); nothing in either raw tree is modified.
- Question: for every HUD and UI element Racer draws, which shipped asset in the six raw games is the same element class, and can each pairing be shown as a screenshot against the raw file with a verifiable provenance chain?
- Output (71 MiB, ignored): `output/captures` (24 native states), `output/raw-candidates.json` (1,775 shipped UI images), `output/judgments.json` (jev asset classification), `output/raw-picks.json` (36 elements → 119 copied assets with hashes), `output/sheets/*.png` (36 proof sheets), `output/element-judgments.json` (jev element likelihoods), `output/mc3-hud-constants.txt` (verbatim MC3 layout numbers), `output/scratch` (transient single-asset tests).

## What a proof sheet is

Each `output/sheets/E##-<name>.png` is one self-contained product:

| panel | content |
|---|---|
| left | Racer crop at native pixels, labelled with capture file, pixel box, logical canvas and the section of the interface it belongs to |
| right | 3–4 shipped assets (PNG render of the decoded raw file) with game, file name, pixel size, jev asset class and probability, and `flip-vertical` where the MC3 texture decodes bottom-up |
| header | the element's role and one line of Racer evidence (state, anchors, values) |
| footer | the exact raw members: `mc3:assets_x.dat/texture_x/…`, `gt4:race_display/…/display.gpb`, `slrr:slrr-231/…`, `mcla:/00000000/resources/ui/…::name.dds` |

The crop box and capture are recorded per element in `elements.json`; the picked assets, their sizes, classes, transforms and hashes are in `output/raw-picks.json`.

## Elements (36)

Sections: HUD/driving 11, UI/cards 5, HUD/event state 4, UI/chrome 4, UI/menus 4, UI/notices 2, HUD/menus 1, HUD/compact 1, UI/event board 1, UI/compact 1, UI/garage 1, HUD/palette 1. Every element has 3 or 4 raw counterparts (25×3, 11×4); 119 tiles total from mc3 43, slrr 44, gt4 26, mcla 6.

`prob` is the jev element likelihood described below; `gap` names what no shipped game actually provides.

| id | element | sheet | raw counterparts | jev | gap |
|---|---|---|---|---|---|
| E01 | speedometer dial | [E01](output/sheets/E01-speedometer-dial.png) | mc3:`hud_speed_1.tex`, gt4:`speed_240km.png`, slrr:`general__general_gauge.png` | 0.54 uncertain | shared round-dial + needle; no shipped tick-ring dial with numerals |
| E02 | gear indicator | [E02](output/sheets/E02-gear-indicator.png) | mc3:`hud_tac_2.tex`, gt4:`gear_base.png`, slrr:`SL2_Digital_Font_render.png` | 0.74 uncertain | counterparts are slot plates and a digital font; no gear-letter glyph |
| E03 | pedal input bars | [E03](output/sheets/E03-pedal-input-bars.png) | gt4:`pedals.png`, gt4:`pedal_bar.png`, mc3:`hud_turbo_nitrobars.tex`, slrr:`LongOSDGauge.png` | 0.91 likely | — |
| E04 | radar minimap | [E04](output/sheets/E04-radar-minimap.png) | mc3:`hud_map_sd.tex`, mc3:`hud_map_tokyo.tex`, mc3:`hud_map_atlanta.tex` | 0.92 likely | — |
| E05 | compass rim and cardinals | [E05](output/sheets/E05-compass-rim-and-cardinals.png) | mc3:`hud_map_damage.tex`, slrr:`debug_gauge_frame.png`, slrr:`general_gauge.png` | 0.62 uncertain | no shipped compass ring; nearest radial art is a damage pie and a gauge frame |
| E06 | range readout | [E06](output/sheets/E06-range-readout.png) | gt4:`mph.png`, gt4:`kmph.png`, mc3:`hud_navsys_default.tex` | 0.76 uncertain | unit wordmarks and a nav frame; Racer prints a text range readout |
| E07 | world waypoint marker | [E07](output/sheets/E07-world-waypoint-marker.png) | mc3:`icon_arrow.tex`, mcla:`icon_checkpoint.dds`, slrr:`arrow_right.png` | 0.93 likely | — |
| E08 | waypoint label chip | [E08](output/sheets/E08-waypoint-label-chip.png) | mc3:`prompt_background.tex`, slrr:`msgBox_green_small.png`, mc3:`whitechip.tex` | 0.74 uncertain | generic plates only; no labelled waypoint chip |
| E09 | off-screen edge arrow | [E09](output/sheets/E09-off-screen-edge-arrow.png) | mcla:`icon_arrow2.dds`, mc3:`ui_arrowright.tex`, slrr:`arrow_right.png` | 0.90 likely | — |
| E10 | HUD identity block | [E10](output/sheets/E10-hud-identity-block.png) | mc3:`logo_manufacturer.tex`, mc3:`navsys_title01_en.tex`, slrr:`streetlegal.png`, gt4:`GT4logo.png` | 0.94 likely | — |
| E11 | drive control hints | [E11](output/sheets/E11-drive-control-hints.png) | mc3:`prompt_a.tex`, mc3:`prompt_b.tex`, mc3:`prompt_background.tex`, slrr:`Ok.png` | 0.84 uncertain | individual prompt keys; no full button-row strip |
| E12 | announcement banner | [E12](output/sheets/E12-announcement-banner.png) | mc3:`msg_go.tex`, mc3:`hud_messageon_en.tex`, slrr:`title_win.png` | 0.95 likely | — |
| E13 | countdown ring | [E13](output/sheets/E13-countdown-ring.png) | slrr:`lap_time.png`, gt4:`timing_lamp.png`, mc3:`hud_pu_go.tex` | 0.87 likely | — |
| E14 | test timer plate | [E14](output/sheets/E14-test-timer-plate.png) | slrr:`holder_timer.png`, gt4:`GT4_meter_texture_laptime.png`, gt4:`panel_base.png` | 0.95 likely | — |
| E15 | gate counter | [E15](output/sheets/E15-gate-counter.png) | slrr:`pos_2_a.png`, gt4:`position_base.png`, gt4:`mark_1st.png` | 0.93 likely | — |
| E16 | test state chip | [E16](output/sheets/E16-test-state-chip.png) | mc3:`barround_center.tex`, slrr:`msgBox_green_small.png`, slrr:`denied.png` | 0.62 uncertain | no refused/inactive chip art shipped |
| E17 | compact HUD cluster | [E17](output/sheets/E17-compact-hud-cluster.png) | slrr:`LongOSDGauge.png`, mc3:`hud_speed_1.tex`, slrr:`general__general_gauge.png` | 0.73 uncertain | single gauge assets only; no composite minimal cluster |
| E18 | menu backdrop scrim | [E18](output/sheets/E18-menu-backdrop-scrim.png) | mc3:`background_top.tex`, mc3:`background_left.tex`, gt4:`opt_bg_4.png`, mcla:`pausebg_ps3.dds` | 0.93 likely | — |
| E19 | screen header | [E19](output/sheets/E19-screen-header.png) | slrr:`streetlegal.png`, slrr:`redline.png`, mc3:`navsys_title01_en.tex`, slrr:`center_line.png` | 0.78 uncertain | wordmarks and rules only; no header lockup |
| E20 | menu row plate | [E20](output/sheets/E20-menu-row-plate.png) | mc3:`orange_bar_center.tex`, slrr:`center_line.png`, mc3:`bar_center.tex` | 0.92 likely | — |
| E21 | menu row icon | [E21](output/sheets/E21-menu-row-icon.png) | mc3:`icon_star.tex`, slrr:`engine_icon.png`, mcla:`icon_timetrial.dds` | 0.85 likely | — |
| E22 | slider row | [E22](output/sheets/E22-slider-row.png) | slrr:`slider_stripe.png`, slrr:`slider_knob.png`, gt4:`base.png`, slrr:`switch_stripe.png` | 0.95 likely | — |
| E23 | field chevrons | [E23](output/sheets/E23-field-chevrons.png) | mc3:`ui_arrowleft.tex`, mc3:`ui_arrowright.tex`, slrr:`arrow_right.png`, mcla:`icon_arrow2.dds` | 0.92 likely | — |
| E24 | info card plate | [E24](output/sheets/E24-info-card-plate.png) | slrr:`large.png`, slrr:`tuning.png`, slrr:`wide.png`, gt4:`panel_base.png` | 0.96 likely | — |
| E25 | stat tiles | [E25](output/sheets/E25-stat-tiles.png) | gt4:`tab1_o.png`, gt4:`tab1.png`, slrr:`raceresult_top.png` | 0.86 likely | — |
| E26 | result hero | [E26](output/sheets/E26-result-hero.png) | slrr:`title_pos_1st.png`, gt4:`mark_1st.png`, mc3:`icon_trophy.tex` | 0.76 uncertain | 1st-place emblems only; no laurel hero plate |
| E27 | detail hint block | [E27](output/sheets/E27-detail-hint-block.png) | slrr:`tuning.png`, mc3:`prompt_background.tex`, gt4:`txtarea_1.png` | 0.77 uncertain | text areas and plates only; no hint block |
| E28 | key-value rows | [E28](output/sheets/E28-key-value-rows.png) | slrr:`raceinfo_splitter.png`, slrr:`splitter.png`, gt4:`panel_base.png` | 0.86 likely | — |
| E29 | warning block | [E29](output/sheets/E29-warning-block.png) | gt4:`sign_asm.png`, gt4:`caution.png`, slrr:`msgBox_red_long.png` | 0.86 likely | — |
| E30 | notice block | [E30](output/sheets/E30-notice-block.png) | slrr:`msgBox_yellow_long.png`, slrr:`msgBox_green_long.png`, gt4:`sign_asm.png` | 0.96 likely | — |
| E31 | event map | [E31](output/sheets/E31-event-map.png) | mc3:`hud_sd_autox_all.tex`, mc3:`hud_detroit_autox_all.tex`, mc3:`hud_map_atlanta.tex` | 0.91 likely | — |
| E32 | footer hints | [E32](output/sheets/E32-footer-hints.png) | mc3:`prompt_a.tex`, mc3:`prompt_b.tex`, mc3:`prompt_background.tex`, slrr:`Ok.png` | 0.91 likely | — |
| E33 | page counter | [E33](output/sheets/E33-page-counter.png) | slrr:`pos_1_a.png`, gt4:`position_base.png`, slrr:`pos_2_a.png` | 0.90 likely | — |
| E34 | compact menu | [E34](output/sheets/E34-compact-menu.png) | slrr:`medium.png`, slrr:`msgBox_green_small.png`, mc3:`bar_left.tex` | 0.93 likely | — |
| E35 | showroom stage | [E35](output/sheets/E35-showroom-stage.png) | gt4:`garage_bg.png`, gt4:`garage_in_bg.png`, slrr:`garage_top.png`, mcla:`sh_default.dds` | 0.95 likely | — |
| E36 | accent palette | [E36](output/sheets/E36-accent-palette.png) | mc3:`hud_arrowcolor.tex`, mc3:`hud_arrowcolor_classic.tex`, mc3:`hud_pu_nitro.tex`, mc3:`hud_pu_go.tex` | 0.67 uncertain | colour-grade textures, not a named palette |

## Extraction inventory behind the picks

`scripts/build_candidates.py` walks only the retained extraction tree and the extraction manifests, so every candidate keeps its raw member:

| game | shipped UI images | decode | source of the member identity |
|---|---|---|---|
| MC3 (Xbox) | 263 | `.tex` palette/DXT, rows bottom-up → flipped | `assets_x.dat` entry manifest |
| GT4 (PS2) | 494 | `.gpb` page → per-page PNG | `decode-report.json` + container sha per `.gpb` |
| SLRR (PC) | 414 | installed-tree PNG/TGA, flattened names | installed tree path + sha256 of the file |
| MCLA (Xbox 360) | 604 | tiled DXT/ARGB untiled → PNG | catalogue entry `…/resources/ui/<id>::name.dds` |

`rubric.json` defines the asset classes; `judgments.json` holds the jev classification (1,775/1,775 candidates covered, keyed `id|game:name`). Picks are hand-anchored first from the classifier's admissible classes, then filled by class rank, size and a ≤2-per-game cap.

## Verification (both run, both recorded)

1. **Provenance chain — `scripts/verify_picks.py` → PASS.** 36 elements, 119 tiles checked: every picked copy exists and its sha256 equals the recorded value; every extraction source still matches its recorded sha256; every MC3, GT4 and SLRR raw member re-hashes equal in its retained extraction tree or `games/raw/slrr-231|221` (113 tiles, MC3 via `assets_x.dat` member bytes, GT4 via the extracted `.gpb` pages, SLRR with 231 preference); every MC3 tile is flipped exactly once and no other tile is transformed; every member identity is present and no unreferenced copies linger in `output/raw-picks`. The 6 MCLA tiles carry `raw_member_note` instead of a hash because the catalogue records entry/name/format but the container itself is not in the extractor manifest.
2. **Element likelihood — jev (`jev_noul`, `typesafe/jev-1.14-20261014` via OpenRouter, batched, 36 propositions).** Each proposition states "Racer's E## crop and the listed raw assets are the same interface element class"; the context item carries the Racer evidence plus each counterpart's game, file name, size, jev asset class and a 16×8 ink/alpha thumbnail. Result: 24 likely (≥0.85), 12 uncertain, 0 unlikely, mean 0.848. `output/jev-request.json` and `output/element-judgments.json` are the exact request and response.

## Raw access and provider record (REA)

The extraction leaf's providers are recorded in [2026-11-08-ui-hud](../2026-11-08-ui-hud/README.md): REA MCP commit `71f680d` — MC3 via `capture_process_scenario` running `xdvdfs-cli 0.8.3` (evidence `ev_8bc84979…8ede44`), SLRR via the Ghidra 12.2 provider (`open_binary`, `search_strings`, `inspect_pe_imports`, `xrefs`, `procedure_pseudo_code`), MCLA/GT4/Juiced 2 via `inspect_byte_entropy` (`ev_ff403d0f…9685`, `ev_4f05969f…1836a`, `ev_93d9b579…c54e`) with project decoders for the image formats. This leaf re-checked the SLRR side directly: REA 12.2/Ghidra 12.2 opens `games/raw/slrr-231/StreetLegal_Redline.exe` as PE x86 with sha256 `f44fb88a4335c657e20701cdb84afb8d1d85f7c3aceb93d30113e6e6e44fefc2`, matching the recorded extraction hash; a regex search of its string inventory for the picked UI asset names returned no path literals (SLRR resolves textures from config), so the member-byte hashes above, not the executable strings, are the SLRR evidence. REA rejects the raw ISO/disc images as an unsupported binary format, so container-level access is what the extraction evidence records; the member bytes it produced are what `verify_picks.py` re-hashes.

## Limits and honest caveats

- jev here reads text and ASCII thumbnails, not images. Its scores under-read shape: the E01 dial pair (Racer sweep dial vs MC3's green gauge with 25–175 numerals) scores 0.54, while single-element calls are even less stable (E01 0.29, E16 0.10, E26 0.15 in a spot check), so the batched run is the reported one and the sheet, not the number, is the proof. The 12 uncertain elements are exactly the ones where no shipped game ships the same element: compass rim, gear lettering, waypoint chip, full prompt strip, refused-state chip, composite compact cluster, header lockup, laurel result hero, hint block, named accent palette. Racer's versions are its own design, so a counterpart can only be the nearest class.
- Art identity is not claimed: different games, different art direction. The claim is element class, layout role and, where available, exact numbers. MC3's shipped constants are quoted verbatim in `output/mc3-hud-constants.txt` — speedometer sweep −130…+119°, centre (52,58), needle 9×50 with rotation origin (118,38), tachometer −130.95…+103.51°, centre (39,45), plus damage-meter, arrow, map, splash, rank and nitro blocks.
- MC3 texture rows decode bottom-up; the flip is applied at copy time and printed on the sheet. Five text-bearing assets were checked by eye for orientation, and the sheets show the result.
- The classifier mislabels some art (E01's dial is classified `gauge_pin` 0.22); that is why the pick list is hand-anchored instead of classifier-driven, and why the classifier probability is printed, not hidden.
- MCLA container bytes are not re-hashed: the 6 MCLA tiles depend on the extraction's decode record. The other 113 tiles are re-hashed end to end.

## Captures

24 native states in `output/captures` (16 used by elements): 1280×720 drive/menus/garage/results, 1920×1080 extra states (`capture_extra.sh`: off-screen waypoint, countdown, magenta accent, invalid results, pending dialog), 640×480 compact HUD and compact menu. Each state keeps its `.review` script, `.profile.career` and `.log`. Binary sha256, branch and HEAD are recorded above; `src/` was clean, so the capture binary corresponds to `25533ae`.

## Retention

Keep everything in `output/` except `scratch/` (39 transient single-asset tests, deletable). Sources: `games/raw` untouched; the extraction leaf keeps the decoded PNGs this leaf references (moving or pruning either leaf breaks `verify_picks.py`). 71 MiB used; free space 400 GiB.

## Regeneration

```sh
# 1. inventory + jev asset classes (needs the extraction leaf)
python3 scripts/build_candidates.py ../2026-11-08-ui-source-extracts/output output/raw-candidates.json
# 2. captures (from the repo root; binary and flags as above)
scripts/capture_ui.sh experiments/2026-11-09-ui-hud-raw-proof/output/captures 1280 720
scripts/capture_extra.sh experiments/2026-11-09-ui-hud-raw-proof/output/captures
# 3. picks + proof sheets
python3 scripts/build_elements.py
# 4. verification
python3 scripts/verify_picks.py
python3 scripts/verify_elements.py   # writes output/jev-request.json; judge with jev_noul
```

`build_elements.py` is idempotent: it rewrites `raw-picks.json`, the picked copies and the sheets from `elements.json` + `raw-candidates.json` + `judgments.json`, leaving nothing to hand-edit. Adding an element means adding one `elements.json` entry (id, name, section, capture, crop, evidence, claim, kinds, prefer, limits) and re-running step 3–4.

## Next action

Use the sheets as the review surface for Racer's HUD work: the 12 gaps are the only places where a counterpart is missing, so any new HUD element should either reuse an existing element class or declare a new gap. When a Racer HUD change lands, re-capture and re-run step 3–4; a failing `verify_picks.py` means the extraction tree moved.

# 2026-11-08 UI source extracts (sibling of ui-hud)

- Status: completed
- Targets: the six canonical inputs under `games/raw/` (see [ui-hud](../2026-11-08-ui-hud/README.md) for tools, providers and limits)
- Question: which shipped UI/HUD resources of MCLA, MC3, GT4, Juiced 2 and SLRR can be decoded within budget, and what layout constants do they hold?
- Output (ignored, ~193 MiB): `output/{mcla-ui,mcla-ui-textures,mc3-ui,gt4-ui,juiced2-ui,slrr-ui}`; moved here from the ui-hud leaf after extraction to stay under 256 MiB. Paths cited inside the agents' notes still say `experiments/2026-11-08-ui-hud/output/...`; replace that prefix with this directory.

## Observations (from the agents' reports; each decode was checked by eye, not against a reference decoder)

- **MC3 (Xbox):** 188 UI `.tex` decode to PNG (palette/DXT, rows bottom-up); `hudmap.xbpf` 75 pages decode; `tune/hud/*` holds exact anchors, sweep angles (speedo -130..+119 deg, tach -131..+103 deg), colours and timings. Flash `.xbck` menus and font bitmaps not decoded.
- **Juiced 2 (Xbox 360):** 7,662 container records, 2,834 textures (Xbox 360 tiled DXT/ARGB, own untiler), 619 UI layout scripts with screen-fraction boxes, 4,039 string tables. Hash-to-name mapping not recovered.
- **GT4 (PS2):** 132 UI files from `GT4.VOL`, 494 PNGs from 25 `Tex1` bundles (HUD, tuning, garage, photo, licence); STRB layout banks and font bitmaps not decoded.
- **MCLA (Xbox 360):** 25 Scaleform movies (string tables only), 1,041 UI textures decoded, `tune/ui` and `tune/checkpoint` text files with colours and pulse rates; coordinates come from screenshots.
- **SLRR 2.2.1/2.3.1 (PC):** UI textures, per-car gauge atlases, Java OSD layout and `osd_*` cfg lines readable; exe imports only D3D9 (HUD is textured quads); `osd_gauge` handler decompiled (`%d %f %f %f`).
- Findings text for each game (element inventories, colours, top-10 ideas) was returned by the agents inline; the transferable results are summarised in the ui-hud README table.

## Retention

Everything kept; none of it is redistributable game content. Regenerate with the scripts in `../2026-11-08-ui-hud/scripts/` (`extract_gt4_ui.py`, `decode_gt4_gpb.py`, `j2_ui_extract.py`, `j2_tex.py`, `mcla-mining/`, MC3/SLRR scripts inside their output folders).

## Next action

None needed for this question; mine the MC3 `tune/hud` constants again if a HUD colour option or per-class dial scales are added.

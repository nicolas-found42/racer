# 2026-11-08 Juiced 2 / GT4 / MC3 effect-pipeline strings (REA pass)

**Question:** which post-processing, lighting and effect systems do the other raw games ship, as named in their executables, so Racer's gaps can be matched to real systems rather than guessed?

## Targets and method
- **Juiced 2: Hot Import Nights (Xbox 360):** `default.xex` from the canonical ISO (`2026-11-05-donor-inventory/output/disc-probes/juiced2-default.xex`, 5,349,376 bytes, SHA-256 `ae20f246...e574`). `decode_xex.py` follows Xenia's public `xex_module.cc` (retrieved read-only to `output/`; key bytes not logged): normal encryption + basic compression, image 6,356,992 bytes (SHA-256 `e65b11dc...2c56`), base 0x82000000, entry 0x823d7fd8, then an analyst-built big-endian PowerPC ELF carrier (`output/image.ppc.elf`, SHA-256 `31689233...2b83`; not an original ELF). REA 6.8.0 / Ghidra 12.2: `open_binary`, two `search_strings` regex passes, `close_binary`.
- **Gran Turismo 4 (PS2):** earlier analysis carrier `2026-11-05-gt4-mc3-data/output/CORE.analysis.elf` (SHA-256 `1243d126...0ab4`, MIPS little-endian, built from the inflated CORE.GT4 in the earlier phase). REA `open_binary`, `search_strings`, two `xrefs`, `close_binary`.
- **Midnight Club 3 (Xbox):** `mc3-default.xbe` (5,099,520 bytes, SHA-256 `0b3d81a0...51a3`). **REA rejected it: `open_binary` -> unsupported binary format.** A plain printable-string scan (not REA, no analysis) was used instead; it shows names only.
- No game was executed. Output is small (<7 MiB, mostly the decoded image and ELF), local and gitignored under `output/`.

## Observed: Juiced 2 (names in the executable, with addresses)
- **Auto exposure and tone mapping:** `Exposure_Lda`, `Exposure_LWhite`, `Exposure_FadeSpeed`, `Exposure_Gamma`, `Exposure_MinLuminance`, `Exposure_MaxLuminance`, `SceneManualExposure`, `ExposureBias/Enable/Limits`, `AverageLuminance`, `Auto Exposure` (0x82027b38-0x8202b71c). The names match Reinhard-style adaptation.
- **Bloom, grain, saturation:** `Bloom_Threshold/Offset/Scale/Amplitude`, `SceneMinBloom/MaxBloom`, `Film_Grain` (0x820288bc), `Saturation`, `LPCSaturation`.
- **Blur family:** `VelocityBlur`, `RadialBlur` with `blurScale/blurScaleMid/blurScaleOut`, `DepthOfField` with `depthOfFieldDistance/Range`, `ReplayDepthOfField(+Lerp)`, `HorizBlur/VertBlur`, `LightBlur`, `MotionBlur`, `NitrousFOV` (0x82030ebc: a nitro field-of-view kick).
- **Lights and flares:** `SunFlare/SunFlareSize`, `LIGHTFLARE_*` with `YREFLECT`/`DRYYREFLECT` size and alpha parameters (flare reflections on wet/dry road), `headlightflares`, `car_flare01`, `SkyLuminosity`, `EnvMapUp/DownFactor`, `g_envMapMul`, `envMapDirY`.
- **Tyres, smoke, sparks:** `smoke_tarmac`, `SKID_TARMAC`, `SKID_SNOW`, `metal_skid%d`, `chassis_sparks`, `small_sparks`, `TyreSkidMuScalar`, `MinimumForSkid`, `SkidRollOff`, `SkidMinDist`, wheel blur materials (`WHEEL_GENERIC_BLUR`, `toyo_tyre_BLUR`), `[NeonColour]` / `UI_CAR_NEON` (car underglow).
- **Not found:** the numeric defaults of these parameters. The names are `%f` format strings of a tuning dump; the 2026-11-05 typed script export contains `DepthOfField 1.0`, `TyreSkidMuScalar 1`, `[NeonColour] 255/5` entries but no bloom/exposure values. Their data source (per-track environment files) was not located.

## Observed: GT4 (CORE.GT4)
`DynamicEnvmapCamera` (0x6aa81a, a live environment-map camera), `shadowDarkness0-2`, `shadowBlur0-3`, `bottomShadow`, `shadowOpacity`, `dirtiness`, `FlareClass`, `SparkParticle`, `mBlurFace`, `rain_noiz`, `back_light_comp`, `CustumLightPosition`, `UserMotionLight`, `mCarModelPS2`. The xref of `shadowDarkness0` lands in a nearby script-property table (0x695648), not code with defaults; the `blurLevel` string at 0x6aa9a0 has no xref. No numeric values recovered.

## Observed: MC3 (printable strings only)
`TireSkidsV3`, `fx_smoke_particle`, `tune/vehicle/ambientTireSmoke`, `fx_headlight_cone_car`, `fx_hlight_glow`, `fx_glowcone`, `fx_glowstar`, `fxltglow_dry_weather`, `m_brakeLightGlowColor`, `m_tailLightGlowColorAmbient`, `glow_headlight%d`, `glow_taillight%d`, `roadreflectors`, `fx_reflector`, `mcAmbientWindow` with `m_windows_%d_pos/width/height/rot` and `tune/vehicle/ambientWindowGlass`, `tune/particlefog`, `m_fogNear/Far/Tint`, `m_litFog`, per-weather city strings (`..._rain`, `..._rain_nt`), `mcFbGlowParams`, `softGlowScale`, `m_blurRadius`.

## Inferred (not verified)
- All four titles run the same family of effects Racer has (bloom, flares, motion/radial blur, DoF, skid marks, tyre smoke, sparks, headlight glow). The gap to the references is therefore content and tuning, not missing effect categories, except for these named systems Racer lacks: **auto exposure**, **flare reflections on the road**, **headlight cone/volume sprite** (MC3 `fx_headlight_cone_car`), **road reflectors**, **per-window ambient glass glow** and **spark particles** (`chassis_sparks`).
- Juiced 2's `NitrousFOV` and its radial/velocity blur parameters support Racer's authored FOV kick and radial blur, not their values.

## Not done
Locating the numeric tune data for Juiced 2 / GT4 / MC3 (the MC3 and GT4 packages were not re-opened for their data files in this pass); decompiling the functions that consume these parameters; any REA on the PS3/Xbox 360 builds of GT4/MC3 (the supplied images are PS2/Xbox).

## Next
Search the Juiced 2 environment data (`tracks`, `scripts.jfs`) for the bloom/exposure keys by hex literal; add one of the named missing systems to Racer, starting with spark particles at the chassis and the headlight cone, and re-capture.

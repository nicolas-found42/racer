# Car and wheel standardization kit (examples of each game's cars and wheels)

- Question: how does each donor game's car, rim and tyre look in the files Racer actually loads, and what would a shared car/rim/tyre/material standard have to replace? Goal behind it: each car its own file, one lighting/material model for all games, rims and tyres split, any tyre on any rim resized to match.
- Targets (Racer-prepared GLBs in `assets/local/vehicles/`, SHA-256 = file stem, verified identical to the copies in the kit):
  - GT4 Acura NSX '04 `4c157f28…8e` · Ford Racing 2 Mustang 1973 `207871bc…6d` · MC3 Corvette Z06 `bf016ebb…3f` · MCLA 350Z Roadster `71a6d4ab…d6` · Juiced 2 350Z `77a9becc…fb` · SLRR Furrano GT54 `e2a0ef64…25`
- Tools: Blender 5.2.2 LTS (EEVEE, headless), Chrome 156.0.8078.81 (headless print-to-PDF), poppler 26.11.0 `pdftoppm` (page rasterising for review; installed via Homebrew on the user's instruction, which also upgraded jpeg-turbo and lz4), Python 3.15 + PIL 13. REA and Jev were not used (static glTF/JSON inspection only).
- Commands (from `games/racer`, scratch dir any writable path): see the README in the kit, "Reproduce"; scripts in `scripts/`: `analyze_glb.py`, `render_kit.py` + `render_all.sh`, `wheel_summary.py`, `build_kit_docs.py`.
- Limits: 6 Blender runs of about 25 s each, 60 renders at 1600×900 or 1200×900; total output 114 MB (limit 512 MiB per experiment); 376 GiB free at start.
- Output (not tracked; copyrighted game assets, gitignored): `assets/local/car-standardization-kit/` containing `README.md`, `car-standardization-deck.pdf` (33 slides, sha256 changes per rebuild), `models/`, `renders/`, `data/analysis.json`, `data/wheel_summary.json`, `tools/`.
- Result:
  - Rim and tyre are separate meshes in 5 of 6 cars; Ford Racing 2 is one fused mesh (split in the renders is a radius heuristic).
  - Tyre inner radius sits 53 mm (GT4) and 43 mm (Juiced 2) inside the rim outer radius; MC3 and MCLA meet exactly; SLRR within 3 mm.
  - GT4, MC3 and Ford tyres have no inboard sidewall (open shells); Juiced 2, MCLA and SLRR are closed.
  - Visible sidewall 49–116 mm; one uniform scale cannot retarget tyres (sidewall factors 0.42–2.35 across the five split cars).
  - Materials are one metallic/roughness pair per car with per-game metadata (`gt4_material`, MC3 `shader_category`, MCLA `sourceShader`); no metallic-roughness textures anywhere.
  - Only Juiced 2 has brake parts (rolling disc, steering-only caliper carrier) and descriptor format v2.
- Limitations: Blender importer + studio rig, not Racer's renderer; front-left wheel rendered only (all four are measured); rim 'diameter' and 'aspect' come from mesh radii, not recovered nominal sizes; the GT4 window colours and white SLRR body are properties of the data, the GT4 window cause was not investigated; Ford GLB has 124 nodes outside the scene that were not examined; redistribution rights of donor meshes not assessed.
- Checks: hub `python3 tools/check.py` PASS. Not run: Racer build and `ctest` (this experiment changed no project source; `src/main.cpp`, `src/tyre_contact.h` and `tests/tyre_contact_checks.cpp` show uncommitted edits that are not from this experiment).
- Next action: user picks units (mm/in), stock-wheel policy and the pilot car; then freeze the spec and a validator, and pilot the GT4 NSX (rim origin/axle normalisation, barrel authoring, first normalised tyre).

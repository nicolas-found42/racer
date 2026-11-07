# mc3-guidance — bounded feedback research

Question: which retained source/documentation facts support understandable tuning feedback and route guidance?

Targets: canonical ../raw inputs and retained donor-inventory extracts; exact hashes will be retained in output/probe.json. Platform/build correspondence and runtime behavior remain separate questions.

Bounds before execution: <=300 s per batch, <=256 MiB output per experiment, >=20 GiB free. Preflight observed 429 GiB free and 137064 KiB existing experiments. Reuse originals/extracts; no installation, bulk extraction, or game save writes.

Retention: preserve canonical inputs, saved REA export and all cited evidence. No cleanup.

Next action: rehash selected inputs and inspect cited source/manual notes; probe compatible runtimes without launching games.

## Executed batch and exact target hashes

Python 3 hashlib SHA-256 streamed 4 MiB blocks; paths explicitly listed in `output/probe.json`. Full batch completed in 3.93 s, no extraction. Runtime inventory used `shutil.which` for wine/wine64/pcsx2/xemu/qemu-system-i386 and immediate app-directory name checks. Hashes match retained source-inputs manifest and cited source hashes; selected hashes do not identify installation trees.

| Exact selected file | Bytes | SHA-256 |
|---|---:|---|
| `/Users/nicolas/Documents/github/reverse-engineering/games/raw/mc3.iso` | 4840554496 | `d58490dc8e1837e9f47716268b52ae1f1ac8578e5a5e42e061fa7f1c4b068b52` |
| `/Users/nicolas/Documents/github/reverse-engineering/games/racer/experiments/2026-11-05-donor-inventory/output/disc-probes/mc3-default.xbe` | 5099520 | `0b3d81a02834e57864a601d473d5296cc0a2463e4b837373d91030f751fa51a3` |

## Navigation and wayfinding observations

Reused `output/retained-documentation.md`, Rockstar Xbox **original DUB Edition** manual notes: Garage printed pp.24–25 and Race Editor pp.22–23. Notes are publisher intent from OCR, not visual scan verification or runtime observations. Retained XBE metadata identifies Midnight Club 3: DUB edition / TT-121; historical Remix label remains unresolved and no Remix-specific claim is made.

| Question | Evidence / observed scope | Unknown | Racer design choice / check |
|---|---|---|---|
| Garage actions | Garage pp.24–25 describes owned cars, buying/selling, tune/upgrades, separate appearance options | Back/confirm/cancel controls and persistence | Context controls and explicit draft/apply status; test transitions |
| Route sequence | Race Editor pp.22–23 describes laying checkpoints, testing races, radius/height, laps/time/weather | Live next-gate/offscreen/missed/wrong-way/finish indicators | Number active gate, distance and heading derived from current course data |
| Test route | Manual describes test racing | Actual local build runtime | Keep fixed Racer route; complete native loop and report human/synthetic separately |

Fresh runtime preflight: `/Applications/xemu.app` is installed, Info.plist reports **0.8.137**. `~/Library/Application Support/xemu/xemu/xemu.toml` only configures EEPROM under sys.files; bootrom/flash/HDD paths are absent. Directory contains configuration, shader_cache_list and 256-byte EEPROM only. `output/xemu-preflight.json` retains the bounded observation. Compatibility/required boot assets are not established, so no game launch or configuration change was attempted. This is more precise than claiming xemu is absent. No install/acquisition is authorized or needed for Racer fixes.

Next donor action: establish an existing configured bootable xemu instance and exact game build with separate save, then garage change/back/cancel and route straight/offscreen/miss/wrong-way/finish sequence within 300 s. Until then, checkpoint UI and save/reload outcomes remain unknown.

## Retention and resume

Retain all output, canonical originals, prior notes and saved `rea-evidence.json`; no original/extract duplicated or removed. New output is small text/JSON, below 256 MiB. No native analysis provider/database opened. Shared prior REA 6.8.0 identities remain prior static evidence, not fresh runtime evidence. Jev verification: `../2026-11-05-slrr-feedback/output/jev-verification.json`, OpenRouter typesafe/jev-1.14-20261014, 8790 input / 309 output tokens; five verified, none contradicted/unsupported, one review explicitly resolved by source reads. Next action: implement and verify authored Racer presentation, with donor runtime/edition limitations retained.

# gt4-comparisons — bounded feedback research

Question: which retained source/documentation facts support understandable tuning feedback and route guidance?

Targets: canonical ../raw inputs and retained donor-inventory extracts; exact hashes will be retained in output/probe.json. Platform/build correspondence and runtime behavior remain separate questions.

Bounds before execution: <=300 s per batch, <=256 MiB output per experiment, >=20 GiB free. Preflight observed 429 GiB free and 137064 KiB existing experiments. Reuse originals/extracts; no installation, bulk extraction, or game save writes.

Retention: preserve canonical inputs, saved REA export and all cited evidence. No cleanup.

Next action: rehash selected inputs and inspect cited source/manual notes; probe compatible runtimes without launching games.

## Executed batch and exact target hashes

Python 3 hashlib SHA-256 streamed 4 MiB blocks; paths explicitly listed in `output/probe.json`. Full batch completed in 3.93 s, no extraction. Runtime inventory used `shutil.which` for wine/wine64/pcsx2/xemu/qemu-system-i386 and immediate app-directory name checks. Hashes match retained source-inputs manifest and cited source hashes; selected hashes do not identify installation trees.

| Exact selected file | Bytes | SHA-256 |
|---|---:|---|
| `/Users/nicolas/Documents/github/reverse-engineering/games/raw/gran-turidmo-4.iso` | 5314478080 | `67b6c0075837f3ae1132d608acf2858bf13b2dd62d6eae83dff76df02e4e824f` |
| `/Users/nicolas/Documents/github/reverse-engineering/games/racer/experiments/2026-11-05-donor-inventory/output/disc-probes/gt4-SCUS_973.28` | 273020 | `f8f10823160e2b5cef5c7032628134632b291b1df87a9aee3c144794dd8019fa` |
| `/Users/nicolas/Documents/github/reverse-engineering/games/racer/experiments/2026-11-05-donor-inventory/output/disc-probes/gt4-SYSTEM.CNF` | 57 | `7bb2979e21efc32977f7a47fd28618c659994ee6e5a9272da5e258695b22f2c0` |

## Comparison fields and provenance

Reused publisher-documentation notes `output/retained-documentation.md`, “Gran Turismo 4 — PS2”; original note and scan lead remain under donor-inventory. No fresh scan was retrieved, so no new page/pixel verification is claimed. Relevant retained sections: Race Settings, Time Trial / Ghost / Analyzer, Circuit (printed p.24). Boot configuration directly read: `BOOT2 = cdrom0:\SCUS_973.28;1`, `VMODE = NTSC`, `VER = 2.00`. Sony/SCEA NTSC U/C manual notes and local serial/region are compatible leads, not exact edition/revision proof. VER alone is not a release identifier.

| Field | Retained publisher-intent observation | Racer design choice / verification |
|---|---|---|
| Setup identity | Three per-car A/B/C settings | Mark next active slot and show exact applied values |
| Comparable context | Analyzer compares best-lap recordings with matching course/start | Preserve exact car/model/test revisions and values |
| Reference | Saved best-lap ghost / two recordings | Name originating slot; matching values do not mean each slot was driven |
| Measurement | Best-lap recordings; sector graphs | Label seconds/metres and signed lower-is-better delta |
| Missing record | Not established in retained notes | Explicit no comparable record |
| Automatic 0–100 / 100–0 | Not established | Racer authored schedules, no GT4 attribution |
| Save/reload after tuning | Not observed | Verify in Racer separately |

No pcsx2 command was found on PATH or named app in the bounded top-level application scan. Compatible GT4 runtime is not established. No game launch, save change, extract, analysis database or REA session was created. Next action for donor runtime: supply/identify an already configured compatible runtime, confirm exact disc build/manual correspondence, then bounded A → B edit → reopen → practice → compare → reload.

## Retention and resume

Retain all output, canonical originals, prior notes and saved `rea-evidence.json`; no original/extract duplicated or removed. New output is small text/JSON, below 256 MiB. No native analysis provider/database opened. Shared prior REA 6.8.0 identities remain prior static evidence, not fresh runtime evidence. Jev verification: `../2026-11-05-slrr-feedback/output/jev-verification.json`, OpenRouter typesafe/jev-1.14-20261014, 8790 input / 309 output tokens; five verified, none contradicted/unsupported, one review explicitly resolved by source reads. Next action: implement and verify authored Racer presentation, with donor runtime/edition limitations retained.

# slrr-feedback — bounded feedback research

Question: which retained source/documentation facts support understandable tuning feedback and route guidance?

Targets: canonical ../raw inputs and retained donor-inventory extracts; exact hashes will be retained in output/probe.json. Platform/build correspondence and runtime behavior remain separate questions.

Bounds before execution: <=300 s per batch, <=256 MiB output per experiment, >=20 GiB free. Preflight observed 429 GiB free and 137064 KiB existing experiments. Reuse originals/extracts; no installation, bulk extraction, or game save writes.

Retention: preserve canonical inputs, saved REA export and all cited evidence. No cleanup.

Next action: rehash selected inputs and inspect cited source/manual notes; probe compatible runtimes without launching games.

## Executed batch and exact target hashes

Python 3 hashlib SHA-256 streamed 4 MiB blocks; paths explicitly listed in `output/probe.json`. Full batch completed in 3.93 s, no extraction. Runtime inventory used `shutil.which` for wine/wine64/pcsx2/xemu/qemu-system-i386 and immediate app-directory name checks. Hashes match retained source-inputs manifest and cited source hashes; selected hashes do not identify installation trees.

| Exact selected file | Bytes | SHA-256 |
|---|---:|---|
| `/Users/nicolas/Documents/github/reverse-engineering/games/raw/slrr-221/StreetLegal_Redline.exe` | 2408448 | `b284a7a53909d0b9ce59d59ddc11e14df40a7eb74d86fa76efb06305aadc2b03` |
| `/Users/nicolas/Documents/github/reverse-engineering/games/raw/slrr-231/StreetLegal_Redline.exe` | 2446848 | `f44fb88a4335c657e20701cdb84afb8d1d85f7c3aceb93d30113e6e6e44fefc2` |
| `/Users/nicolas/Documents/github/reverse-engineering/games/raw/slrr-231/parts/scripts/rgearpart/reciprocatingrgearpart/SRC/Tyre.java` | 12726 | `7cea735bbed7b7135bfae4e99fa502bcaa57562edea0c4b1f30e33976872bb57` |
| `/Users/nicolas/Documents/github/reverse-engineering/games/raw/slrr-231/parts/scripts/enginepart/slidingenginepart/reciprocatingenginepart/SRC/Transmission.java` | 8162 | `bbf7cb991786251a732b914415e1e6401d070baf4fb559eddc47c4f9a454b60b` |
| `/Users/nicolas/Documents/github/reverse-engineering/games/raw/slrr-221/SLR Manual_files/Garage_Menu_Screens.htm` | 21471 | `27ef446dea6257e81d734938913d66bb77b3326896d728bc0d37318971036f87` |

## Observations and two-version transition table

Exact static reads: `Tyre.java:336–400`, `Transmission.java:219–305` and focused follow-up `:308–340`. Retained line-numbered excerpts and manual text: `output/source-excerpts.txt`. Exact symbol/path discovery was already supplied in PLAN; no new unfamiliar discovery was needed and no new Jevgrep search was run. Prior discovery remains retained in donor-inventory `slrr-jg-command.json` / `slrr-jg-result.txt` with its explicit truncation notice.

| Operation | 221 bundled manual (publisher intent) | 231 source (static, executable correspondence unknown) | Runtime unknown |
|---|---|---|---|
| Enter tune | Garage item 11: click part, tune gear ratios/tyre pressure | Tyre snapshots old/new inflation, Transmission snapshots ratios | Exact UI/controls in each supplied executable |
| Edit | No detailed draft contract | Tyre changes new_inflation only; Transmission changes ratio/end_ratio fields temporarily (`:310–322`) | Visible feedback while changing |
| Cancel | Not specified | Tyre reapplies old inflation; Transmission restores old ratios/end_ratio | Reopen values in running game |
| Accept | Not specified | Tyre applies new inflation; both paths forceUpdate | Measurable driving effects |
| Test | Garage items 2/9/13 separate test track, records and engine/steering test | Not established by these files | Test and record UI |
| Save/reload | Main Menu says careers autosave on exit career/game; Save/Load Car are separate | Tyre save/load writes/reads inflation | Actual persisted/reloaded state in both builds |

No wine/wine64 was found on PATH; top-level /Applications and ~/Applications scan found no matching Wine/CrossOver application. This bounds the blocker; it does not prove no compatible runtime exists anywhere on disk. No donor was launched. Loose 221 equivalent source remains unknown beyond the prior exact-filename search; packaged equivalents were not unpacked.

Jev returned verified on all five research claims. Transmission claim was marked review (supports .83, confidence .74). Direct source inspection resolves its concrete content: :235–240 snapshots then negates ratios; :283–287 restores both ratio array and end_ratio; :310–322 assigns Slider values directly. This supports temporary mutation and cancellation only; no native or runtime behavior is asserted. The review is retained and not retried.

## Retention and resume

Retain all output, canonical originals, prior notes and saved `rea-evidence.json`; no original/extract duplicated or removed. New output is small text/JSON, below 256 MiB. No native analysis provider/database opened. Shared prior REA 6.8.0 identities remain prior static evidence, not fresh runtime evidence. Jev verification: `../2026-11-05-slrr-feedback/output/jev-verification.json`, OpenRouter typesafe/jev-1.14-20261014, 8790 input / 309 output tokens; five verified, none contradicted/unsupported, one review explicitly resolved by source reads. Next action: implement and verify authored Racer presentation, with donor runtime/edition limitations retained.

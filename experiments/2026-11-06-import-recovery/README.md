# Ten-car import recovery and restart

Question: does actual native car switching preserve the previous car on a broken selected mesh, recover after repair, expose a failed selection save, retry it, and reload the new exact geometry identity in a fresh process?

Preflight: hidden --background only, no desktop focus/input; output<=64MiB, command<=120s, native children<=70s/12s. Source assets/local/vehicles measured35MiB before copying; free>400GiB; project standard output~1.44GB<2GiB. Preserve original input/default profiles and all earlier evidence. Child profiles and corruption fixtures isolated inside output. No dependencies/network.

Input catalog currently10cars with Juiced2 rubber-only revision77a9becc6d20882a97417610a5a6a22120c33076c92d54ae7b84bec70eef81fb; previous versions retained. Exact current catalog/build SHA in generated manifest and native history. Binary chosen from expanded-acceptance/output/build-v1/runtime/racer; its source/runtime snapshot is separately retained, not an atomic compiler-input attestation.

Command: python3 scripts/verify_vehicle_selection.py experiments/2026-11-06-import-recovery/output --binary experiments/2026-11-06-expanded-acceptance/output/build-v1/runtime/racer

Next: retain actual result, inspect all13workflow captures+reload, retrieve asset/selection/save/load history and update resume. No human/physical controller or source-game parity claim.

## Verified result

Native script exit0;13workflow captures+reload independently pixel-reviewed. Exact selected new350Z77a9… reloads and selection sidecar matches. Run1793953542712396-67208 op24 pairs expected vehicle77a9… with asset_parse failure; op25 then loads exact repaired77a9… successfully. Screenshot06/07 show the previous MCLA car retained. Vehicle document hash8879f52f… fails save op26 attemporary_open errno13; op29 saves atomically; new run1793953576196045-68788 loads the same document and exact77a9… mesh. Livery red-stripe apply also survives restart;13result uses explicit review timing override, not a real8s measurement.

Actual retrieval artifacts: output/selection-query.jsonl, document-save-query.jsonl, reload-query.jsonl and manifest.json. Bad bytes are the retained driver fixture literal; canonical models/default profiles were untouched. The failure's generic asset_parse lacks actual failed input SHA/stage: this concrete remaining historical-diagnosis gap starts asset-failure-context work, rather than treating parser error as a supported root cause.

Retention: original/copy models, all captures, raw histories, native logs/driver retained. No source game, physical controller or human course acceptance; all windows hidden.

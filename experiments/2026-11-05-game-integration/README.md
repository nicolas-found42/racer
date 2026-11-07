# Connected prototype systems — integration verification

Question: do the new asset/parts/livery/class/career slices preserve the accepted foundation and leave enough retained evidence to reconstruct failures after exit/reload?

Target: native C++20 SDL3/bgfx/Metal Racer in the existing dirty independent checkout. Canonical donor inputs and normal player saves remain untouched. Every native run must use `--background`, a fresh isolated profile,<=300s process deadline, exact executable hash and private diagnostic store. Output<=256MiB for this investigation; free-space preflight remains above420GiB. Retain failures and analysis state, no staging/commits.

Implementation/evidence context: [all-family execution](../2026-11-05-all-milestones/README.md) and [current coverage/unknowns](../2026-11-05-all-milestones/coverage.md). Earlier feature and career captures belong to their exact interim hashes; this experiment verifies the subsequent integrated renderer/configuration and does not relabel old captures as new.

Status: active. `output/build*.log`, `ctest*.log` retain executed build/check results. Next: archive the exact tested build after the build-copy traversal fix, run native baseline controls, both-size feature loops, source material preview and explicit loader failure, retrieve histories and review every changed image. Keep human course report and physical hardware unverified until actually supplied.

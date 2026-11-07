# First-playable dependencies

All dependency source and license files are retained under ignored `.deps/`; bootstrap downloads pinned GitHub source archives. The procedural game geometry is authored Racer code. The position/color Metal shaders are the precompiled bgfx `01-cubes` example shaders from the pinned bgfx source, loaded directly from `.deps/bgfx/examples/runtime/shaders/metal`.

| Dependency | Pin | License retained |
|---|---|---|
| SDL3 | 3.4.18, installed Homebrew package | zlib, installed SDL3 distribution |
| bgfx.cmake | 1af3832b87ad0588c05f1f0bd7ee17a7b14d2315 | `.deps/bgfx.cmake/LICENSE` (CC0) |
| bgfx | b2513038f4b753ebeced40821c193978daa0492f | `.deps/bgfx/LICENSE` (BSD 2-clause) |
| bx | da13683750ff8df8f44a5a15f637b6ae9460a04b | `.deps/bx/LICENSE` (BSD 2-clause) |
| bimg | 64a34f7441af8f06e40ccab08d76bbf5e59e55b1 | `.deps/bimg/LICENSE` (BSD 2-clause) |
| cgltf | 85cd62382dfea638278962690cf515023f33ed00 | `third_party/cgltf/LICENSE` (MIT) |

The static glTF inspection loader vendors cgltf with exact header/license hashes in `third_party/cgltf/SOURCE.json`. Embedded PNG base-color maps use the already pinned bimg decoder, qualified with a four-color2×2 fixture. Livery/material rendering embeds the pinned bgfx debugdraw `fill_texture` Metal programs from their generated headers; the original cubes programs remain the untextured path. These additions do not establish complete glTF PBR, donor shader, skin or animation support.

Build: Apple clang 21.0.0, CMake 4.4.4, Ninja 1.13.2. These identify the verified machine, not a portability certification. CMake finds SDL3 3.4 or later; the verified version above is pinned as evidence. The source archives come from `https://codeload.github.com/bkaradzic/<name>/tar.gz/<revision>`; the wrapper was initially cloned at the listed HEAD. Retain upstream notices with any redistributed binaries, including the bgfx shaders. No distribution/package publication has been performed.

Native integration references: [SDL Metal view](https://wiki.libsdl.org/SDL3/SDL_Metal_CreateView), [SDL gamepad](https://wiki.libsdl.org/SDL3/CategoryGamepad), and the pinned bgfx headers/examples. The selected bgfx revision uses `Init.swapChain`/`Init.reset` and `reset(flags, &swapChain)`. Older `Init.resolution` examples do not match this revision.

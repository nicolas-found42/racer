#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .deps
python3 - <<'PY'
import pathlib,subprocess,urllib.request,tarfile,io
pins={'bgfx.cmake':'1af3832b87ad0588c05f1f0bd7ee17a7b14d2315','bgfx':'b2513038f4b753ebeced40821c193978daa0492f','bx':'da13683750ff8df8f44a5a15f637b6ae9460a04b','bimg':'64a34f7441af8f06e40ccab08d76bbf5e59e55b1'}
for name,rev in pins.items():
 dest=pathlib.Path('.deps')/name
 if dest.exists():continue
 print('Fetching',name,rev,flush=True)
 with urllib.request.urlopen(f'https://codeload.github.com/bkaradzic/{name}/tar.gz/{rev}',timeout=120) as r:data=r.read(180*1024*1024)
 if len(data)>=180*1024*1024:raise RuntimeError('Download budget exceeded')
 with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as t:
  if sum(m.size for m in t.getmembers())>800*1024*1024:raise RuntimeError('Extract budget exceeded')
  t.extractall('.deps',filter='data')
 pathlib.Path('.deps',name+'-'+rev).rename(dest)
PY
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH=/opt/homebrew
cmake --build build -j 6
python3 scripts/install_cars.py

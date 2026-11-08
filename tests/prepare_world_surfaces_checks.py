import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import prepare_world_surfaces as prep

with tempfile.TemporaryDirectory(prefix="racer-surfaces-") as folder:
    root = Path(folder)
    source = root / "source"
    source.mkdir()
    pins = {}
    # Sixteen tiles; the non-square sources must be resampled to 256x256.
    sizes = [(256, 256)] * 5 + [(512, 256)] + [(256, 256)] + [(512, 512)] + [(256, 256)] * 2 + \
        [(2048, 128)] + [(64, 256)] + [(256, 128)] + [(256, 256)] + [(512, 512)] + [(256, 256)]
    for i, size in enumerate(sizes):
        name = str(i) + ".dds"
        path = source / name
        Image.new("RGB", size, (40 + i * 10, 30, 20)).save(path, "PNG")
        pins[name] = (hashlib.sha256(path.read_bytes()).hexdigest(), size)
    output = root / "prepared"

    def run():
        with patch.object(prep, "PINS", pins), patch.object(sys, "argv", ["prepare", "--source", str(source), "--output", str(output)]), contextlib.redirect_stdout(io.StringIO()):
            prep.main()

    def rejected():
        try:
            run()
        except ValueError:
            return
        raise AssertionError("Conflicting input/output was accepted")

    run()
    atlas = output / "surfaces.rgba"
    manifest = output / "surfaces.json"
    original = atlas.read_bytes(), manifest.read_bytes()
    stamps = atlas.stat().st_mtime_ns, manifest.stat().st_mtime_ns
    run()
    assert stamps == (atlas.stat().st_mtime_ns, manifest.stat().st_mtime_ns), "identical outputs were rewritten"
    assert json.loads(original[1])["sha256"] == hashlib.sha256(original[0]).hexdigest()
    assert original[0][:8] == b"RCRSURF4" and len(original[0]) == 8 + 256 * 4096 * 4, "sixteen-tile RCRSURF4 payload"
    pixels = original[0][8:]
    for i in range(16):  # every tile is filled (resampled tiles keep their flat colour)
        assert pixels[(i * 256 + 128) * 256 * 4:(i * 256 + 128) * 256 * 4 + 3] == bytes((40 + i * 10, 30, 20)), "tile " + str(i)
    manifest.write_bytes(b"retained provenance")
    rejected()
    assert manifest.read_bytes() == b"retained provenance" and atlas.read_bytes() == original[0]
    manifest.unlink()
    atlas.write_bytes(b"retained atlas")
    rejected()
    assert not manifest.exists() and atlas.read_bytes() == b"retained atlas"
    atlas.unlink()
    atlas.symlink_to(source / "0.dds")
    rejected()
    assert atlas.is_symlink() and not manifest.exists()
    atlas.unlink()
    (source / "0.dds").write_bytes(b"changed source")
    rejected()
    assert not atlas.exists() and not manifest.exists()

print("PASS: pinned preparation, repeat-run preservation, manifest/atlas/link conflicts and source hash rejection")

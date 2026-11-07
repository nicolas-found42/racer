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
    for i in range(4):
        name = str(i) + ".dds"
        path = source / name
        Image.new("RGB", (256, 256), (40 + i * 30, 30, 20)).save(path, "PNG")
        pins[name] = hashlib.sha256(path.read_bytes()).hexdigest()
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

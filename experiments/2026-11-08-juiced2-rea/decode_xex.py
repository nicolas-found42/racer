#!/usr/bin/env python3
"""Decode the Juiced 2 default.xex (Xbox 360, retail) into its memory image and wrap it as a big-endian PPC ELF carrier
for REA/Ghidra. Layout, AES-CBC key schedule and 'basic' compression follow Xenia's public xex_module.cc (retrieved read-only
into output/); key bytes are never printed or written to a report. Limits: image < 32 MiB.
Usage: decode_xex.py SOURCE.xex OUT_DIR"""
import ctypes, hashlib, json, re, struct, sys
from pathlib import Path
src = Path(sys.argv[1]); out = Path(sys.argv[2]); d = src.read_bytes()
cpp = (out / "xenia-xex_module.cc").read_text()
body = re.search(r"xe_xex2_retail_key\[16\] = \{(.*?)\};", cpp, re.S).group(1)
key = bytes(int(x, 16) for x in re.findall(r"0x([0-9a-fA-F]+)", body)); assert len(key) == 16
lib = ctypes.CDLL("/usr/lib/system/libcommonCrypto.dylib"); fn = lib.CCCrypt; fn.restype = ctypes.c_int
fn.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
def decrypt(k, data):
    o = ctypes.create_string_buffer(len(data)); n = ctypes.c_size_t()
    assert fn(1, 0, 0, k, len(k), bytes(16), data, len(data), o, len(data), ctypes.byref(n)) == 0
    return o.raw[:n.value]
header = struct.unpack_from(">6I", d); assert d[:4] == b"XEX2"
security = header[4]; session = decrypt(key, d[security + 0x150:security + 0x160])
payload = decrypt(session, d[header[2]:])
opts = dict(struct.unpack_from(">2I", d, 24 + i * 8) for i in range(header[5]))
f = opts[0x3ff]; size, enc, comp = struct.unpack_from(">IHH", d, f)
report = {"source_sha256": hashlib.sha256(d).hexdigest(), "source_bytes": len(d), "encryption_type": enc, "compression_type": comp}
assert (enc, comp) == (1, 1), report  # normal encryption + basic compression only
blocks = [struct.unpack_from(">2I", d, f + 8 + i * 8) for i in range((size - 8) // 8)]
image = bytearray(); cursor = 0
for count, zero in blocks:
    image.extend(payload[cursor:cursor + count]); image.extend(bytes(zero)); cursor += count
assert cursor == len(payload) and image[:2] == b"MZ" and len(image) < 32 << 20
base, entry = opts[0x10201], opts[0x10100]
(out / "image.pe").write_bytes(image)
# ELF32 big-endian PowerPC executable: one PT_LOAD mapping the whole memory image at the image base (Xenia copies
# memory-image bytes directly; PE raw offsets must not be reused).
ehsize, phsize = 52, 32; filesz = len(image)
elf = bytearray(struct.pack(">16sHHIIIIIHHHHHH", b"\x7fELF\x01\x02\x01" + bytes(9), 2, 20, 1, entry, ehsize, 0, 0, ehsize, phsize, 1, 0, 0, 0))
elf += struct.pack(">8I", 1, 0x1000, base, base, filesz, filesz, 7, 0x1000)
elf = bytes(elf).ljust(0x1000, b"\0") + bytes(image)
(out / "image.ppc.elf").write_bytes(elf)
report.update({"image_bytes": len(image), "image_sha256": hashlib.sha256(image).hexdigest(), "elf_sha256": hashlib.sha256(elf).hexdigest(),
               "image_base": hex(base), "entry": hex(entry), "blocks": blocks,
               "method": "Xenia xex_module.cc layout; CommonCrypto AES-CBC; basic zero reinsertion; analyst-built ELF carrier, not an original ELF"})
(out / "xex-decoding.json").write_text(json.dumps(report, indent=1)); print(json.dumps({k: v for k, v in report.items() if k != "blocks"}))

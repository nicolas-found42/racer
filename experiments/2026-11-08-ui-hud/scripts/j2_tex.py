"""Juiced 2 (Xbox 360) UI texture + archive helpers. Analysis only; never runs game code.

Archive: <name>.jfshdr = BE u32 count + count * 6xBE u32 [hash, offset, packed, unpacked, 4, flag];
<name>.jfs = concatenated records (zlib if packed != unpacked, else stored). Verified in
2026-11-05-juiced2-data (scripts/cardecals) and re-verified here for every ui* record (0 failures).

Textures: 40-byte header (BE) [magic, width, height, 1,1,1,0,0,0,0xbf000000?...] + tiled payload.
magic 0x1A200152 = DXT1, 0x1A200153 = DXT2/3 (explicit alpha), 0x1A200154 = DXT4/5,
0x1A200171 = DXN (ATI2), 0x18280186 = 32-bit ARGB.  Payload is padded to 32x32 blocks and Xbox 360
tiled; the untile routine is the public Xenia/UModel GetTiledOffset2D, validated here by inspecting
the output images (ReverseBox's xbox360 untile is NOT qualified, so it is not used).
"""
import struct
import zlib

import numpy as np
from PIL import Image


def load_archive(base):
    h = open(base + '.jfshdr', 'rb').read()
    jfs = open(base + '.jfs', 'rb').read()
    n = struct.unpack('>I', h[:4])[0]
    assert len(h) == 4 + n * 24
    out = []
    for i in range(n):
        r = struct.unpack('>6I', h[4 + i * 24:28 + i * 24])
        p = jfs[r[1]:r[1] + r[2]]
        if r[2] == r[3]:
            data = p
        else:
            dec = zlib.decompressobj()
            data = dec.decompress(p)
            assert dec.eof and len(data) == r[3]
        out.append((i, r, data))
    return out


def tiled_offsets(w_blocks, h_blocks, log2bpp):
    """Block indices (UModel GetXbox360TiledOffset) for every block of a padded surface."""
    pitch = (w_blocks + 31) // 32 * 32
    ys, xs = np.mgrid[0:h_blocks, 0:w_blocks].astype(np.int64)
    bpp = log2bpp
    macro = ((xs >> 5) + (ys >> 5) * (pitch >> 5)) << (bpp + 7)
    micro = ((xs & 7) + ((ys & 6) << 2)) << bpp
    off = (macro + ((micro & ~15) << 1) + (micro & 15) + ((ys & 8) << (3 + bpp)) + ((ys & 1) << 4))
    res = (((off & ~511) << 3) + ((off & 448) << 2) + (off & 63) + ((ys & 16) << 7) +
           (((((ys & 8) >> 2) + (xs >> 3)) & 3) << 6))
    return res >> bpp  # in blocks


def untile(payload, w_blocks, h_blocks, block_bytes):
    log2 = {4: 2, 8: 3, 16: 4}[block_bytes]
    pw = (w_blocks + 31) // 32 * 32
    ph = (h_blocks + 31) // 32 * 32
    offs = tiled_offsets(w_blocks, h_blocks, log2) * block_bytes
    buf = np.frombuffer(payload, dtype=np.uint8)
    if len(buf) < pw * ph * block_bytes:
        buf = np.concatenate([buf, np.zeros(pw * ph * block_bytes - len(buf), np.uint8)])
    idx = (offs[..., None] + np.arange(block_bytes)[None, None, :])
    return buf[idx]  # (h_blocks, w_blocks, block_bytes)


def _rgb565(c):
    r = ((c >> 11) & 31) * 255 // 31
    g = ((c >> 5) & 63) * 255 // 63
    b = (c & 31) * 255 // 31
    return np.stack([r, g, b], -1).astype(np.int32)


def _dxt_color(blk, dxt1):
    c0 = blk[..., 0].astype(np.int32) | (blk[..., 1].astype(np.int32) << 8)
    c1 = blk[..., 2].astype(np.int32) | (blk[..., 3].astype(np.int32) << 8)
    p0, p1 = _rgb565(c0), _rgb565(c1)
    pal = np.zeros(blk.shape[:2] + (4, 4), np.int32)  # r,g,b,a
    pal[..., 3] = 255
    pal[..., 0, :3] = p0
    pal[..., 1, :3] = p1
    four = (c0 > c1) | (not dxt1)
    f = four[..., None]
    pal[..., 2, :3] = np.where(f, (2 * p0 + p1) // 3, (p0 + p1) // 2)
    pal[..., 3, :3] = np.where(f, (p0 + 2 * p1) // 3, 0)
    if dxt1:
        pal[..., 3, 3] = np.where(four, 255, 0)
    bits = (blk[..., 4].astype(np.uint32) | (blk[..., 5].astype(np.uint32) << 8) |
            (blk[..., 6].astype(np.uint32) << 16) | (blk[..., 7].astype(np.uint32) << 24))
    sel = np.stack([(bits >> (2 * i)) & 3 for i in range(16)], -1)  # (..., 16)
    px = np.take_along_axis(pal, sel[..., None].astype(np.int64).repeat(4, -1), axis=2)
    return px  # (bh,bw,16,4)


def _alpha_block(a8):
    a0 = a8[..., 0].astype(np.int32)
    a1 = a8[..., 1].astype(np.int32)
    pal = np.zeros(a8.shape[:2] + (8,), np.int32)
    pal[..., 0], pal[..., 1] = a0, a1
    gt = (a0 > a1)
    for i in range(1, 7):
        pal[..., i + 1] = np.where(gt, ((7 - i) * a0 + i * a1) // 7,
                                   np.where(i <= 4, ((5 - i) * a0 + i * a1) // 5, 0))
    pal[..., 7] = np.where(gt, pal[..., 7], 255)
    pal[..., 6] = np.where(gt, pal[..., 6], 0)
    bits = np.zeros(a8.shape[:2], np.uint64)
    for i in range(6):
        bits |= a8[..., 2 + i].astype(np.uint64) << np.uint64(8 * i)
    sel = np.stack([(bits >> np.uint64(3 * i)) & np.uint64(7) for i in range(16)], -1).astype(np.int64)
    return np.take_along_axis(pal, sel, axis=2)


def decode_texture(d):
    magic, w, h = struct.unpack('>III', d[:12])
    pay = d[40:]
    if magic == 0x18280186:
        bw, bh = w, h
        t = untile(pay, bw, bh, 4)  # (h,w,4) bytes A R G B
        img = np.stack([t[..., 1], t[..., 2], t[..., 3], t[..., 0]], -1)
        if img[..., 3].max() == 0:
            img[..., 3] = 255
        return Image.fromarray(img.astype(np.uint8), 'RGBA'), 'ARGB8888'
    f = magic & 0xff
    bb = {0x52: 8, 0x53: 16, 0x54: 16, 0x71: 16}[f]
    bw, bh = (w + 3) // 4, (h + 3) // 4
    # 8-in-16 endian swap, then untile blocks
    sw = np.frombuffer(pay, dtype=np.uint8)
    n = len(sw) // 2 * 2
    sw = sw[:n].reshape(-1, 2)[:, ::-1].reshape(-1)
    blk = untile(sw.tobytes(), bw, bh, bb)
    if f == 0x52:
        px = _dxt_color(blk, True)
        name = 'DXT1'
    elif f == 0x53:
        px = _dxt_color(blk[..., 8:], False)
        a = blk[..., :8].astype(np.int32)
        al = np.stack([((a[..., i // 2] >> (4 * (i % 2))) & 15) * 17 for i in range(16)], -1)
        px[..., 3] = al
        name = 'DXT3'
    elif f == 0x54:
        px = _dxt_color(blk[..., 8:], False)
        px[..., 3] = _alpha_block(blk[..., :8])
        name = 'DXT5'
    else:  # DXN: two 8-bit channels (x,y)
        x = _alpha_block(blk[..., :8])
        y = _alpha_block(blk[..., 8:])
        px = np.zeros(blk.shape[:2] + (16, 4), np.int32)
        px[..., 0], px[..., 1], px[..., 2], px[..., 3] = x, y, 128, 255
        name = 'DXN'
    # (bh,bw,16,4) -> (bh*4, bw*4, 4)
    img = px.reshape(bh, bw, 4, 4, 4).transpose(0, 2, 1, 3, 4).reshape(bh * 4, bw * 4, 4)
    return Image.fromarray(img[:h, :w].clip(0, 255).astype(np.uint8), 'RGBA'), name

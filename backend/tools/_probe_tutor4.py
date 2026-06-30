#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
rom = next((ROOT / "local_artifacts").glob("*.gba")).read_bytes()
BPS = 19

def has_tutor(species_id, tutor_idx, off, zero_based=False):
    sid = species_id - 1 if zero_based else species_id
    base = off + sid * BPS
    if base + BPS > len(rom):
        return None
    byte_idx = tutor_idx // 8
    bit_idx = tutor_idx % 8
    return bool(rom[base + byte_idx] & (1 << bit_idx))

candidates = [0x2b0300, 0x2b2a00, 0x2b2a80, 0x2b2b00, 0x2b2b40, 0x2b2ec0, 0x2b2e80, 0xa7eb40, 0xa7fb80]
lines = []
for off in candidates:
    for zb in (False, True):
        b1_fp = has_tutor(1, 0, off, zb)
        c4_fp = has_tutor(4, 0, off, zb)
        sid1 = 0 if zb else 1
        sid4 = 3 if zb else 4
        bits1 = sum(bin(rom[off + sid1 * BPS + i]).count("1") for i in range(BPS))
        bits4 = sum(bin(rom[off + sid4 * BPS + i]).count("1") for i in range(BPS))
        lines.append(f"off={hex(off)} zb={zb} bulba_fp={b1_fp} char_fp={c4_fp} bulba_bits={bits1} char_bits={bits4}")

(ROOT / "tools" / "_probe_tutor_out.txt").write_text("\n".join(lines), encoding="utf-8")

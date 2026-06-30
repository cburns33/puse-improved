#!/usr/bin/env python3
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
rom = next((ROOT / "local_artifacts").glob("*.gba")).read_bytes()
SPECIES_MAX = 1267
NUM_TUTORS = 146
BPS = (NUM_TUTORS + 7) // 8
TABLE_SIZE = (SPECIES_MAX + 1) * BPS

best = []
for off in range(0, len(rom) - TABLE_SIZE, 64):
    ok = True
    bit_counts = []
    for sid in range(1, min(40, SPECIES_MAX + 1)):
        base = off + sid * BPS
        chunk = rom[base:base + BPS]
        if len(chunk) < BPS:
            ok = False
            break
        if all(b == 0xFF for b in chunk):
            ok = False
            break
        if all(b == 0 for b in chunk):
            continue
        bits = sum(bin(b).count("1") for b in chunk)
        bit_counts.append(bits)
        if bits > 80:
            ok = False
            break
    if not ok or len(bit_counts) < 10:
        continue
    avg = sum(bit_counts) / len(bit_counts)
    if 2 <= avg <= 45:
        best.append((off, avg, len(bit_counts)))

best.sort(key=lambda x: (-x[2], x[1]))
lines = [f"BPS={BPS} TABLE_SIZE={TABLE_SIZE}", f"candidates={len(best)}"]
for off, avg, n in best[:20]:
    lines.append(f"off={hex(off)} avg_bits={avg:.1f} sampled={n}")
(ROOT / "tools" / "_probe_tutor_out.txt").write_text("\n".join(lines), encoding="utf-8")

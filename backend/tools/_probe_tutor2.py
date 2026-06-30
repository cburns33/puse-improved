#!/usr/bin/env python3
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
rom = next((ROOT / "local_artifacts").glob("*.gba")).read_bytes()
TUTOR_MOVES_OFF = 0x2AB0B0
NUM_TUTORS = 146  # TUTOR00 through TUTOR145
BYTES_PER_SPECIES = (NUM_TUTORS + 7) // 8  # 19

ptr = struct.pack("<I", 0x08000000 + TUTOR_MOVES_OFF)
hits = []
idx = 0
while True:
    pos = rom.find(ptr, idx)
    if pos < 0:
        break
    hits.append(pos)
    idx = pos + 1

lines = [f"ptr hits={len(hits)}", "first=" + ", ".join(hex(h) for h in hits[:10])]

# scan after tutor move list for plausible compatibility table
start = TUTOR_MOVES_OFF + NUM_TUTORS * 2
lines.append(f"scan start={hex(start)}")
for delta in range(0, 256, 4):
    off = start + delta
    # read species 1-3 compatibility bytes
    chunk = rom[off:off + BYTES_PER_SPECIES * 5]
    lines.append(f"delta={delta} off={hex(off)} head={list(chunk[:40])}")

(ROOT / "tools" / "_probe_tutor_out.txt").write_text("\n".join(lines), encoding="utf-8")

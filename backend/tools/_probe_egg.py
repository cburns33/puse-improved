#!/usr/bin/env python3
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
candidates = list((ROOT / "local_artifacts").glob("*.gba"))
if not candidates:
    raise SystemExit("no gba")
rom_path = candidates[0]
rom = rom_path.read_bytes()
out = ROOT / "tools" / "_probe_egg_out.txt"
lines = [f"rom bytes={len(rom)}", f"rom path len={len(str(rom_path))}"]

EGG_OFF = 20000
needle = struct.pack("<HHH", 1 + EGG_OFF, 130, 204)
pos = rom.find(needle)
lines.append(f"bulbasaur needle={hex(pos) if pos >= 0 else None}")

idx = 0
hits = []
while len(hits) < 8:
    pos = rom.find(bytes([0x21, 0x4E]), idx)
    if pos < 0:
        break
    hits.append(pos)
    idx = pos + 1
lines.append("hits=" + ", ".join(hex(h) for h in hits))
for h in hits[:5]:
    words = [struct.unpack_from("<H", rom, h + i * 2)[0] for i in range(12)]
    lines.append(f"{hex(h)} {words}")

out.write_text("\n".join(lines), encoding="utf-8")

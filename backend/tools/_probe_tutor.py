#!/usr/bin/env python3
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
rom = next((ROOT / "local_artifacts").glob("*.gba")).read_bytes()

moves = {}
for line in (ROOT / "data" / "moves.txt").read_text(encoding="utf-8").splitlines():
    if ":" not in line:
        continue
    left, right = line.split(":", 1)
    if left.strip().isdigit():
        moves[right.strip()] = int(left.strip())

# tutors.h order, exact names from moves.txt
tutor_move_names = [
    "Fire Punch", "Ice Punch", "ThunderPunch", "Snore", "Heal Bell",
    "Electroweb", "Low Kick", "Uproar", "Bind", "Helping Hand",
]
ids = [moves[n] for n in tutor_move_names]
needle = struct.pack("<" + "H" * len(ids), *ids)
pos = rom.find(needle)
lines = [f"tutor moves needle={hex(pos) if pos >= 0 else None}", f"ids={ids}"]
if pos >= 0:
    words = [struct.unpack_from("<H", rom, pos + i * 2)[0] for i in range(40)]
    lines.append(f"next40={words}")
(ROOT / "tools" / "_probe_tutor_out.txt").write_text("\n".join(lines), encoding="utf-8")

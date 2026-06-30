#!/usr/bin/env python3
"""Score tutor compatibility table candidates against DPE source lists."""
from __future__ import annotations

import re
import struct
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
rom = next((ROOT / "local_artifacts").glob("*.gba")).read_bytes()

# species token -> id from species_id.txt
species_token_to_id: dict[str, int] = {}
for line in (ROOT / "data" / "species_id.txt").read_text(encoding="utf-8").splitlines():
    parts = line.strip().split()
    if len(parts) >= 2 and parts[1].startswith("0x"):
        species_token_to_id[parts[0]] = int(parts[1], 16)

# tutor index -> set(species_id) from GitHub DPE Unbound branch
BASE = "https://raw.githubusercontent.com/Skeli789/Dynamic-Pokemon-Expansion/Unbound/src/tutor_compatibility/"
listing = urllib.request.urlopen(
    "https://api.github.com/repos/Skeli789/Dynamic-Pokemon-Expansion/contents/src/tutor_compatibility?ref=Unbound"
).read().decode("utf-8")
import json
files = json.loads(listing)
tutor_species: dict[int, set[int]] = {}
for entry in files:
    name = entry["name"]
    m = re.match(r"^(\d+)\s*-", name)
    if not m:
        continue
    tutor_idx = int(m.group(1)) - 1
    if tutor_idx < 0 or tutor_idx >= 146:
        continue
    text = urllib.request.urlopen(BASE + urllib.parse.quote(name)).read().decode("utf-8", errors="ignore")
    sids = set()
    for raw in text.splitlines():
        tok = raw.strip()
        if not tok or tok.startswith("Tutor"):
            continue
        sid = species_token_to_id.get(tok)
        if sid:
            sids.add(sid)
    tutor_species[tutor_idx] = sids

print(f"loaded tutors={len(tutor_species)}")

BPS = 19
NUM_SPECIES = max(species_token_to_id.values())

def read_table(off: int, zero_based: bool) -> dict[int, set[int]]:
    out: dict[int, set[int]] = {}
    for sid in range(1, NUM_SPECIES + 1):
        row = sid - 1 if zero_based else sid
        base = off + row * BPS
        tutors: set[int] = set()
        for t in range(146):
            if rom[base + t // 8] & (1 << (t % 8)):
                tutors.add(t)
        if tutors:
            out[sid] = tutors
    return out

def score(off: int, zero_based: bool) -> tuple[int, int]:
    table = read_table(off, zero_based)
    match = 0
    mismatch = 0
    for t, expected in tutor_species.items():
        for sid in range(1, min(200, NUM_SPECIES + 1)):
            has = t in table.get(sid, set())
            exp = sid in expected
            if has == exp:
                match += 1
            else:
                mismatch += 1
    return match, mismatch

import urllib.parse

best = []
for off in range(0x2b0000, 0x2b8000, 4):
    for zb in (False, True):
        m, mm = score(off, zb)
        if mm == 0 and m > 1000:
            best.append((off, zb, m, mm))

best.sort(key=lambda x: -x[2])
lines = [f"perfect hits={len(best)}"]
for row in best[:5]:
    lines.append(f"off={hex(row[0])} zb={row[1]} match={row[2]} mismatch={row[3]}")

# also score known candidate
for off, zb in [(0x2b2ec0, False), (0x2b2ec0, True)]:
    m, mm = score(off, zb)
    lines.append(f"check off={hex(off)} zb={zb} match={m} mismatch={mm}")

(ROOT / "tools" / "_probe_tutor_out.txt").write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines))

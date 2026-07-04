import struct
import sys
from collections import defaultdict

SECTION_SIZE = 0x1000
FOOTER_ID_OFF = 0xFF4
FOOTER_SAVEINDEX_OFF = 0xFFC
SECTOR_HEADER_SIZE = 4
SECTOR_PAYLOAD_SIZE = 0xFF0
POKEMON_STREAM_SECTORS = [5, 6, 7, 8, 9, 10, 11, 12]
PRESET_SECTOR_ID = 0
MON_SIZE_PC = 58
OFFSET_PRESET_START = 0xB0
PRESET_CAPACITY = 30
BOX_SLOT_COUNT = 30

FALLBACK_BOX_LAYOUTS = {
    20: [('absolute', 1, 21, 0x1EB0C)],
    21: [('absolute', 1, 30, 0x1F1E8)],
    22: [('absolute', 1, 30, 0x1F8B4)],
    23: [('section', 2, 1, 4, 0x0F18), ('section', 3, 5, 30, 0x0010)],
    24: [('section', 3, 1, 30, 0x05F4)],
}


def ru16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def ru32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def is_valid_mon(raw):
    if len(raw) < MON_SIZE_PC:
        return False
    pid = ru32(raw, 0)
    if pid == 0:
        return False
    species_id = ru16(raw, 0x1C)
    if species_id == 0 or species_id > 2500:
        return False
    exp = ru32(raw, 0x20)
    return 0 < exp <= 2_000_000


path = sys.argv[1]
with open(path, "rb") as f:
    buf = f.read()

n = len(buf) // SECTION_SIZE
sections = []
for i in range(n):
    off = i * SECTION_SIZE
    chunk = buf[off:off + SECTION_SIZE]
    if len(chunk) < SECTION_SIZE:
        break
    sect_id = ru16(chunk, FOOTER_ID_OFF)
    saveidx = ru32(chunk, FOOTER_SAVEINDEX_OFF)
    sections.append({"id": sect_id, "idx": saveidx, "off": off})

max_idx = max(s["idx"] for s in sections if s["id"] != 0xFFFF)
active = [s for s in sections if s["idx"] == max_idx]
by_id = {}
for s in active:
    by_id.setdefault(s["id"], []).append(s)


def section_offset(sec_id):
    m = by_id.get(sec_id)
    return m[0]["off"] if m else None


pc_buffer = bytearray()
for sid in POKEMON_STREAM_SECTORS:
    off = section_offset(sid)
    if off is None:
        continue
    pc_buffer += buf[off + SECTOR_HEADER_SIZE: off + SECTOR_HEADER_SIZE + SECTOR_PAYLOAD_SIZE]

pid_locations = defaultdict(list)
total = 0

total_slots = len(pc_buffer) // MON_SIZE_PC
for idx in range(total_slots):
    slot = (idx % BOX_SLOT_COUNT) + 1
    box_id = (idx // BOX_SLOT_COUNT) + 1
    raw = pc_buffer[idx * MON_SIZE_PC: idx * MON_SIZE_PC + MON_SIZE_PC]
    if is_valid_mon(raw):
        pid_locations[ru32(raw, 0)].append(("linear", box_id, slot))
        total += 1

preset_off = section_offset(PRESET_SECTOR_ID)
if preset_off is not None:
    base = preset_off + OFFSET_PRESET_START
    for slot in range(1, PRESET_CAPACITY + 1):
        raw = buf[base + (slot - 1) * MON_SIZE_PC: base + (slot - 1) * MON_SIZE_PC + MON_SIZE_PC]
        if is_valid_mon(raw):
            pid_locations[ru32(raw, 0)].append(("preset", 26, slot))
            total += 1

for box_id, layout in FALLBACK_BOX_LAYOUTS.items():
    for seg in layout:
        kind = seg[0]
        if kind == 'absolute':
            _, start_slot, end_slot, base_off = seg
            for slot in range(start_slot, end_slot + 1):
                abs_off = base_off + (slot - start_slot) * MON_SIZE_PC
                if abs_off + MON_SIZE_PC > len(buf):
                    continue
                raw = buf[abs_off:abs_off + MON_SIZE_PC]
                if is_valid_mon(raw):
                    pid_locations[ru32(raw, 0)].append(("fallback-abs", box_id, slot))
                    total += 1
        else:
            _, sec_id, start_slot, end_slot, rel_off = seg
            sec_off = section_offset(sec_id)
            if sec_off is None:
                continue
            for slot in range(start_slot, end_slot + 1):
                abs_off = sec_off + rel_off + (slot - start_slot) * MON_SIZE_PC
                if abs_off + MON_SIZE_PC > len(buf):
                    continue
                raw = buf[abs_off:abs_off + MON_SIZE_PC]
                if is_valid_mon(raw):
                    pid_locations[ru32(raw, 0)].append(("fallback-sec", box_id, slot))
                    total += 1

print(f"Total valid mons across ALL boxes (linear, preset, fallback 20-24): {total}")

dupes = {pid: locs for pid, locs in pid_locations.items() if len(locs) > 1}
if dupes:
    print(f"\n*** DUPLICATES: {len(dupes)} ***")
    for pid, locs in dupes.items():
        print(f"  PID=0x{pid:08X}: {locs}")
else:
    print("No duplicate PIDs found across ALL boxes.")

box_counts = defaultdict(int)
for pid, locs in pid_locations.items():
    for kind, b, s in locs:
        box_counts[b] += 1
print("\nBox occupancy:")
for b in sorted(box_counts):
    print(f"  Box {b}: {box_counts[b]} mons")

# Detail boxes 1 and 11
for target_box in (1, 11):
    print(f"\nBox {target_box} slots:")
    base = (target_box - 1) * 30
    for slot in range(1, 31):
        idx = base + (slot - 1)
        off = idx * MON_SIZE_PC
        if off + MON_SIZE_PC > len(pc_buffer):
            break
        raw = pc_buffer[off:off + MON_SIZE_PC]
        if is_valid_mon(raw):
            pid = ru32(raw, 0)
            species = ru16(raw, 0x1C)
            print(f"  slot {slot:2d}: PID=0x{pid:08X} species={species}")
        else:
            pid = ru32(raw, 0)
            species = ru16(raw, 0x1C)
            if pid or species:
                print(f"  slot {slot:2d}: INVALID (pid=0x{pid:08X} species={species})")

import struct
import sys
from pathlib import Path

SECTION_SIZE = 0x1000
FOOTER_ID_OFF = 0xFF4
FOOTER_SAVEINDEX_OFF = 0xFFC
SECTOR_HEADER_SIZE = 4
SECTOR_PAYLOAD_SIZE = 0xFF0
POKEMON_STREAM_SECTORS = [5, 6, 7, 8, 9, 10, 11, 12]
MON_SIZE_PC = 58


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
    sp = ru16(raw, 0x1C)
    if sp == 0 or sp > 2500:
        return False
    exp = ru32(raw, 0x20)
    return 0 < exp <= 2_000_000


def load_pc(path):
    buf = Path(path).read_bytes()
    sections = []
    for i in range(len(buf) // SECTION_SIZE):
        off = i * SECTION_SIZE
        sid = ru16(buf, off + FOOTER_ID_OFF)
        sidx = ru32(buf, off + FOOTER_SAVEINDEX_OFF)
        sections.append({"id": sid, "idx": sidx, "off": off})
    max_idx = max(s["idx"] for s in sections if s["id"] != 0xFFFF)
    by_id = {}
    for s in sections:
        if s["idx"] == max_idx:
            by_id.setdefault(s["id"], []).append(s)
    pc = bytearray()
    for sid in POKEMON_STREAM_SECTORS:
        off = by_id[sid][0]["off"]
        pc += buf[off + SECTOR_HEADER_SIZE: off + SECTOR_HEADER_SIZE + SECTOR_PAYLOAD_SIZE]
    return pc


def box_slots(pc, box):
    out = {}
    base = (box - 1) * 30
    for slot in range(1, 31):
        off = (base + slot - 1) * MON_SIZE_PC
        if off + MON_SIZE_PC > len(pc):
            break
        raw = pc[off: off + MON_SIZE_PC]
        if is_valid_mon(raw):
            out[slot] = (ru32(raw, 0), ru16(raw, 0x1C))
    return out


def main():
    artifacts = Path(__file__).resolve().parents[1] / "local_artifacts"
    orig = next(artifacts.glob("*corrupted*.sav"))
    new = next(p for p in artifacts.glob("*.sav") if "corrupted" not in p.name.lower())

    moved_slots = [2, 3, 6, 12, 13, 14, 15, 16, 17, 18, 19, 23]
    orig_pc = load_pc(orig)
    new_pc = load_pc(new)
    orig_box1 = box_slots(orig_pc, 1)
    orig_moved = {s: orig_box1[s] for s in moved_slots if s in orig_box1}
    moved_values = set(orig_moved.values())

    print("Comparing corrupted vs new repro save")
    print("\nMoved mons from original box 1:")
    for s, (pid, sp) in sorted(orig_moved.items()):
        print(f"  slot {s:2d}: PID=0x{pid:08X} species={sp}")

    print("\nSearch in new save (linear boxes 1-18):")
    found = 0
    for box in range(1, 19):
        slots = box_slots(new_pc, box)
        for slot, val in sorted(slots.items()):
            if val in moved_values:
                print(f"  FOUND box {box} slot {slot}: PID=0x{val[0]:08X} species={val[1]}")
                found += 1

    print(f"\nFound {found}/{len(orig_moved)} moved mons in linear buffer")

    missing = []
    for s, val in orig_moved.items():
        found_any = False
        for box in range(1, 19):
            if val in box_slots(new_pc, box).values():
                found_any = True
                break
        if not found_any:
            missing.append((s, val))
    if missing:
        print("\nMISSING mons (not in any linear box 1-18):")
        for s, (pid, sp) in missing:
            print(f"  was box1 slot {s}: PID=0x{pid:08X} species={sp}")


if __name__ == "__main__":
    main()

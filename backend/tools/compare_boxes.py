import struct
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


def box_detail(pc, box):
    print(f"\nBox {box}:")
    base = (box - 1) * 30
    count = 0
    for slot in range(1, 31):
        off = (base + slot - 1) * MON_SIZE_PC
        if off + MON_SIZE_PC > len(pc):
            break
        raw = pc[off: off + MON_SIZE_PC]
        if is_valid_mon(raw):
            count += 1
            print(f"  slot {slot:2d}: PID=0x{ru32(raw, 0):08X} species={ru16(raw, 0x1C)}")
    print(f"  ({count} mons)")


artifacts = Path(__file__).resolve().parents[1] / "local_artifacts"
orig = next(artifacts.glob("*corrupted*.sav"))
new = next(p for p in artifacts.glob("*.sav") if "corrupted" not in p.name.lower())

for label, path in [("BEFORE (corrupted baseline)", orig), ("AFTER (new repro)", new)]:
    print(f"=== {label} ===")
    pc = load_pc(path)
    for box in (1, 2, 10):
        box_detail(pc, box)

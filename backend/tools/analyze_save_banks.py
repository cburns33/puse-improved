import struct
import sys
from pathlib import Path

SECTION_SIZE = 0x1000
FOOTER_VALIDLEN_OFF = 0xFF0
FOOTER_ID_OFF = 0xFF4
FOOTER_CHK_OFF = 0xFF6
FOOTER_SIG_OFF = 0xFF8
FOOTER_SAVEINDEX_OFF = 0xFFC
EXPECTED_SIG = 0x01121999

UNBOUND_PRESET_MAGIC_LEN = 0xADC
UNBOUND_ITEM_FIXED_LEN = 0x450


def ru16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def ru32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def gba_checksum(buf, off, length):
    length = max(0, length)
    total = 0
    full = length - (length % 4)
    for i in range(0, full, 4):
        total = (total + ru32(buf, off + i)) & 0xFFFFFFFF
    if length % 4 != 0:
        tail = bytearray(4)
        for i in range(length % 4):
            tail[i] = buf[off + full + i]
        total = (total + struct.unpack_from("<I", tail, 0)[0]) & 0xFFFFFFFF
    return ((total >> 16) + (total & 0xFFFF)) & 0xFFFF


def analyze(path):
    buf = Path(path).read_bytes()
    n = len(buf) // SECTION_SIZE
    sections = []
    for i in range(n):
        off = i * SECTION_SIZE
        sections.append({
            "idx": i,
            "off": off,
            "id": ru16(buf, off + FOOTER_ID_OFF),
            "saveidx": ru32(buf, off + FOOTER_SAVEINDEX_OFF),
            "valid_len": ru32(buf, off + FOOTER_VALIDLEN_OFF),
            "sig": ru32(buf, off + FOOTER_SIG_OFF),
            "chk_stored": ru16(buf, off + FOOTER_CHK_OFF),
        })

    max_idx = max(s["saveidx"] for s in sections if s["id"] != 0xFFFF)
    print(f"\n=== {Path(path).name} (len={len(buf)}) ===")
    print(f"Active saveidx: {max_idx}")

    mismatches = []
    for s in sections:
        sid = s["id"]
        if sid == 0xFFFF:
            continue
        if s["saveidx"] != max_idx:
            continue
        if sid == 4:
            continue
        off = s["off"]
        if sid == 0:
            calc = gba_checksum(buf, off, UNBOUND_PRESET_MAGIC_LEN)
        elif sid == 13:
            calc = gba_checksum(buf, off, UNBOUND_ITEM_FIXED_LEN)
        else:
            calc = gba_checksum(buf, off, 0xFF4)
        ok = calc == s["chk_stored"]
        if not ok:
            mismatches.append((s["idx"], sid, s["chk_stored"], calc))
        print(f"  ACTIVE idx={s['idx']:2d} id={sid:3d} valid_len=0x{s['valid_len']:04X} "
              f"chk=0x{s['chk_stored']:04X} calc=0x{calc:04X} sig=0x{s['sig']:08X} {'OK' if ok else 'MISMATCH'}")

    if mismatches:
        print(f"\n*** {len(mismatches)} ACTIVE CHECKSUM MISMATCH(ES) ***")
    else:
        print("\nAll active checksums OK (excl id 4)")

    # Compare both banks for each section id 0-13
    print("\nPer-section-id bank comparison (inactive vs active):")
    for sid in range(14):
        rows = [s for s in sections if s["id"] == sid and s["saveidx"] > 0 and s["saveidx"] != 0xFFFFFFFF]
        if len(rows) < 2:
            continue
        rows.sort(key=lambda r: r["saveidx"])
        inactive, active = rows[0], rows[-1]
        if inactive["saveidx"] == active["saveidx"]:
            continue
        off_a, off_i = active["off"], inactive["off"]
        diff = sum(1 for a, b in zip(buf[off_i:off_i + 0xFF4], buf[off_a:off_a + 0xFF4]) if a != b)
        chk_i_ok = inactive["chk_stored"] == gba_checksum(buf, off_i, 0xFF4 if sid not in (0, 13) else (UNBOUND_PRESET_MAGIC_LEN if sid == 0 else UNBOUND_ITEM_FIXED_LEN))
        chk_a_ok = active["chk_stored"] == gba_checksum(buf, off_a, 0xFF4 if sid not in (0, 13) else (UNBOUND_PRESET_MAGIC_LEN if sid == 0 else UNBOUND_ITEM_FIXED_LEN))
        flag = ""
        if sid in (5, 6, 7, 8, 9, 10, 11, 12):
            flag = " [PC STREAM]"
        print(f"  id={sid:2d}: inactive idx={inactive['saveidx']} chk_ok={chk_i_ok} | "
              f"active idx={active['saveidx']} chk_ok={chk_a_ok} | payload diffs={diff}")


if __name__ == "__main__":
    paths = sys.argv[1:] if len(sys.argv) > 1 else []
    if not paths:
        artifacts = Path(__file__).resolve().parents[1] / "local_artifacts"
        paths = sorted(artifacts.glob("*.sav"), key=lambda p: ("corrupt" not in p.name.lower(), p.name))
    for p in paths:
        analyze(p)

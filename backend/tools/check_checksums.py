import struct
import sys

SECTION_SIZE = 0x1000
FOOTER_VALIDLEN_OFF = 0xFF0
FOOTER_ID_OFF = 0xFF4
FOOTER_CHK_OFF = 0xFF6
FOOTER_SAVEINDEX_OFF = 0xFFC

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
        tw = struct.unpack_from("<I", tail, 0)[0]
        total = (total + tw) & 0xFFFFFFFF
    return ((total >> 16) + (total & 0xFFFF)) & 0xFFFF


path = sys.argv[1]
with open(path, "rb") as f:
    buf = f.read()

n = len(buf) // SECTION_SIZE
mismatches = []
for i in range(n):
    off = i * SECTION_SIZE
    chunk = buf[off:off + SECTION_SIZE]
    if len(chunk) < SECTION_SIZE:
        break
    sect_id = ru16(chunk, FOOTER_ID_OFF)
    valid_len = ru32(chunk, FOOTER_VALIDLEN_OFF)
    chk_stored = ru16(chunk, FOOTER_CHK_OFF)
    saveidx = ru32(chunk, FOOTER_SAVEINDEX_OFF)

    if sect_id == 0:
        calc = gba_checksum(buf, off, UNBOUND_PRESET_MAGIC_LEN)
        algo = f"preset(0x{UNBOUND_PRESET_MAGIC_LEN:04X})"
    elif sect_id == 13:
        calc = gba_checksum(buf, off, UNBOUND_ITEM_FIXED_LEN)
        algo = f"bag(0x{UNBOUND_ITEM_FIXED_LEN:04X})"
    elif sect_id == 4:
        calc = None
        algo = "opaque-skip"
    else:
        calc = gba_checksum(buf, off, 0xFF4)
        algo = "standard(0xFF4)"

    status = "SKIP" if calc is None else ("OK" if calc == chk_stored else "MISMATCH")
    calc_str = "----" if calc is None else f"0x{calc:04X}"
    print(f"idx={i:2d} off=0x{off:06X} id={sect_id:3d} saveidx={saveidx:6d} algo={algo:20s} "
          f"chk_stored=0x{chk_stored:04X} chk_calc={calc_str} {status}")
    if status == "MISMATCH":
        mismatches.append((i, off, sect_id, saveidx, chk_stored, calc))

print()
if mismatches:
    print(f"*** {len(mismatches)} CHECKSUM MISMATCH(ES) ***")
    for row in mismatches:
        print(f"  idx={row[0]} off=0x{row[1]:06X} id={row[2]} saveidx={row[3]} stored=0x{row[4]:04X} calc=0x{row[5]:04X}")
else:
    print("All checksums OK (excluding opaque section 4).")

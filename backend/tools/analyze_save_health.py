import struct
from pathlib import Path

SECTION_SIZE = 0x1000
SIGNATURE_OFF = 0xFF8
EXPECTED_SIG = 0x01121999
FOOTER_ID_OFF = 0xFF4
FOOTER_SAVEINDEX_OFF = 0xFFC
FOOTER_VALIDLEN_OFF = 0xFF0
FOOTER_CHK_OFF = 0xFF6
SECTOR_HEADER_SIZE = 4
SECTOR_PAYLOAD_SIZE = 0xFF0
POKEMON_STREAM_SECTORS = [5, 6, 7, 8, 9, 10, 11, 12]
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
            "sig": ru32(buf, off + SIGNATURE_OFF),
            "chk": ru16(buf, off + FOOTER_CHK_OFF),
        })

    max_idx = max(s["saveidx"] for s in sections if s["id"] != 0xFFFF)
    print(f"\n=== {Path(path).name} ===")
    print(f"Active saveidx: {max_idx}")

    bad_sig = [s for s in sections if s["id"] != 0xFFFF and s["saveidx"] > 0 and s["sig"] != EXPECTED_SIG]
    if bad_sig:
        print(f"BAD signatures: {len(bad_sig)}")
        for s in bad_sig[:5]:
            print(f"  idx={s['idx']} id={s['id']} sig=0x{s['sig']:08X}")
    else:
        print("All non-empty section signatures OK")

    # Compare PC stream between active and inactive generations
    def pc_stream_for_saveidx(target_idx):
        by_id = {}
        for s in sections:
            if s["saveidx"] == target_idx and s["id"] in POKEMON_STREAM_SECTORS:
                by_id[s["id"]] = s
        if len(by_id) != len(POKEMON_STREAM_SECTORS):
            return None
        pc = bytearray()
        for sid in POKEMON_STREAM_SECTORS:
            off = by_id[sid]["off"]
            pc += buf[off + SECTOR_HEADER_SIZE: off + SECTOR_HEADER_SIZE + SECTOR_PAYLOAD_SIZE]
        return bytes(pc)

    inactive_idx = max(s["saveidx"] for s in sections if s["id"] != 0xFFFF and s["saveidx"] < max_idx)
    active_pc = pc_stream_for_saveidx(max_idx)
    inactive_pc = pc_stream_for_saveidx(inactive_idx)
    if active_pc and inactive_pc:
        diffs = sum(1 for a, b in zip(active_pc, inactive_pc) if a != b)
        print(f"PC stream bytes differing active({max_idx}) vs inactive({inactive_idx}): {diffs}/{len(active_pc)}")

    # Active-gen checksum summary for ids 0-13
    mism = []
    for s in sections:
        if s["saveidx"] != max_idx:
            continue
        sid = s["id"]
        if sid == 4:
            continue
        off = s["off"]
        if sid == 0:
            calc = gba_checksum(buf, off, UNBOUND_PRESET_MAGIC_LEN)
        elif sid == 13:
            calc = gba_checksum(buf, off, UNBOUND_ITEM_FIXED_LEN)
        else:
            calc = gba_checksum(buf, off, 0xFF4)
        if calc != s["chk"]:
            mism.append(s)
    print(f"Active-gen checksum mismatches (excl id4): {len(mism)}")


artifacts = Path(__file__).resolve().parents[1] / "local_artifacts"
for sav in sorted(artifacts.glob("*.sav")):
    analyze(sav)

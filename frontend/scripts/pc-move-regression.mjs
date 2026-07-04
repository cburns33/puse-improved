/**
 * PC batch-move regression: load save, move box-1 slots to box 10, commit, verify checksums + placement.
 *
 * Usage (from frontend/):
 *   node scripts/pc-move-regression.mjs [--save path/to/file.sav]
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

import { gbaChecksum } from '../src/core/checksum.js';
import { saveAll } from '../src/core/commit.js';
import {
    applyPcContextToSave,
    getActivePcSectors,
    loadPcContext,
    movePcMon,
    readPcMonRaw,
} from '../src/core/pc.js';
import { OFF_CHECKSUM, OFF_ID, OFF_SAVE_IDX, OFF_VALID_LEN, SECTION_SIZE } from '../src/core/sections.js';

const MON_SIZE_PC = 58;
const UNBOUND_PRESET_MAGIC_LEN = 0xADC;
const UNBOUND_ITEM_FIXED_LEN = 0x450;
const POKEMON_STREAM_SECTORS = [5, 6, 7, 8, 9, 10, 11, 12];
const SECTOR_HEADER_SIZE = 4;
const SECTOR_PAYLOAD_SIZE = 0xFF0;
const MAX_VALID_LEN = 0xFF4;

const MOVED_SLOTS = [2, 3, 6, 12, 19, 23];
const DEST_BOX = 10;

function parseArgs(argv) {
    const cwd = process.cwd();
    const saveIdx = argv.indexOf('--save');
    const defaultSave = path.resolve(cwd, '../backend/local_artifacts');
    return {
        save: saveIdx >= 0
            ? path.resolve(cwd, argv[saveIdx + 1])
            : null,
        artifactsDir: defaultSave,
    };
}

async function resolveSavePath(args) {
    if (args.save) {
        return args.save;
    }
    const entries = await fs.readdir(args.artifactsDir);
    const name = entries.find((n) => n.endsWith('.sav') && !n.toLowerCase().includes('corrupted'))
        || entries.find((n) => n.endsWith('.sav'));
    if (!name) {
        throw new Error(`No .sav found in ${args.artifactsDir}`);
    }
    return path.join(args.artifactsDir, name);
}

function ru16(buf, off) {
    return buf[off] | (buf[off + 1] << 8);
}

function ru32(buf, off) {
    return buf[off] | (buf[off + 1] << 8) | (buf[off + 2] << 16) | (buf[off + 3] << 24);
}

function isValidMon(raw) {
    if (!raw || raw.length < MON_SIZE_PC) return false;
    const pid = ru32(raw, 0);
    if (pid === 0) return false;
    const species = ru16(raw, 0x1c);
    if (species === 0 || species > 2500) return false;
    const exp = ru32(raw, 0x20);
    return exp > 0 && exp <= 2_000_000;
}

function extractPcBufferFromFile(buffer) {
    const sectors = getActivePcSectors(buffer);
    const maxIdx = Math.max(...sectors.map((s) => s.idx));
    const active = sectors.filter((s) => s.idx === maxIdx);
    const byId = new Map();
    active.forEach((s) => byId.set(s.id, s));
    const chunks = [];
    POKEMON_STREAM_SECTORS.forEach((id) => {
        const sec = byId.get(id);
        if (!sec) return;
        chunks.push(buffer.slice(sec.offset + SECTOR_HEADER_SIZE, sec.offset + SECTOR_HEADER_SIZE + SECTOR_PAYLOAD_SIZE));
    });
    const total = chunks.reduce((n, c) => n + c.length, 0);
    const pc = new Uint8Array(total);
    let cursor = 0;
    chunks.forEach((chunk) => {
        pc.set(chunk, cursor);
        cursor += chunk.length;
    });
    return pc;
}

function boxOccupants(pcBuffer, boxId) {
    const out = new Map();
    const base = (boxId - 1) * 30;
    for (let slot = 1; slot <= 30; slot += 1) {
        const off = (base + slot - 1) * MON_SIZE_PC;
        if (off + MON_SIZE_PC > pcBuffer.length) break;
        const raw = pcBuffer.slice(off, off + MON_SIZE_PC);
        if (isValidMon(raw)) {
            out.set(slot, ru32(raw, 0));
        }
    }
    return out;
}

function invalidPcStreamValidLens(buffer) {
    const bad = [];
    const total = Math.floor(buffer.length / SECTION_SIZE);
    let maxIdx = 0;
    for (let i = 0; i < total; i += 1) {
        const off = i * SECTION_SIZE;
        const sid = ru16(buffer, off + OFF_ID);
        const sidx = ru32(buffer, off + OFF_SAVE_IDX);
        if (sid !== 0xffff && sidx > maxIdx) maxIdx = sidx;
    }
    for (let i = 0; i < total; i += 1) {
        const off = i * SECTION_SIZE;
        const sid = ru16(buffer, off + OFF_ID);
        const sidx = ru32(buffer, off + OFF_SAVE_IDX);
        if (sidx !== maxIdx || !POKEMON_STREAM_SECTORS.includes(sid)) continue;
        const validLen = ru32(buffer, off + OFF_VALID_LEN) >>> 0;
        if (validLen > MAX_VALID_LEN) {
            bad.push({ idx: i, sid, validLen });
        }
    }
    return bad;
}

function checksumActiveSections(buffer) {
    const mismatches = [];
    const total = Math.floor(buffer.length / SECTION_SIZE);
    let maxIdx = 0;
    for (let i = 0; i < total; i += 1) {
        const off = i * SECTION_SIZE;
        const sid = ru16(buffer, off + OFF_ID);
        const sidx = ru32(buffer, off + OFF_SAVE_IDX);
        if (sid !== 0xffff && sidx > maxIdx) maxIdx = sidx;
    }

    for (let i = 0; i < total; i += 1) {
        const off = i * SECTION_SIZE;
        const sid = ru16(buffer, off + OFF_ID);
        const sidx = ru32(buffer, off + OFF_SAVE_IDX);
        if (sidx !== maxIdx) continue;
        if (sid === 4) continue;

        let calc;
        if (sid === 0) calc = gbaChecksum(buffer, off, UNBOUND_PRESET_MAGIC_LEN);
        else if (sid === 13) calc = gbaChecksum(buffer, off, UNBOUND_ITEM_FIXED_LEN);
        else calc = gbaChecksum(buffer, off, 0xff4);

        const stored = ru16(buffer, off + OFF_CHECKSUM);
        if (stored !== calc) {
            mismatches.push({ idx: i, off, sid, stored, calc });
        }
    }
    return mismatches;
}

function buffersEqual(a, b) {
    if (a.length !== b.length) return false;
    for (let i = 0; i < a.length; i += 1) {
        if (a[i] !== b[i]) return false;
    }
    return true;
}

async function main() {
    const args = parseArgs(process.argv.slice(2));
    const savePath = await resolveSavePath(args);
    const raw = await fs.readFile(savePath);
    let failures = 0;

    const fail = (msg) => {
        failures += 1;
        console.error(`FAIL: ${msg}`);
    };
    const pass = (msg) => console.log(`PASS: ${msg}`);

    // --- Test 1: round-trip without moves ---
    {
        const buf = new Uint8Array(raw);
        const ctx = loadPcContext(buf);
        const beforePc = ctx.pcBuffer.slice(0);
        applyPcContextToSave(buf, ctx);
        const badLens = invalidPcStreamValidLens(buf);
        if (badLens.length === 0) pass('round-trip PC stream valid_len OK');
        else fail(`round-trip invalid valid_len: ${JSON.stringify(badLens)}`);
        const mm = checksumActiveSections(buf);
        if (mm.length === 0) pass('round-trip active checksums OK');
        else fail(`round-trip checksum mismatches: ${mm.length}`);
        const ctx2 = loadPcContext(buf);
        if (buffersEqual(beforePc, ctx2.pcBuffer)) {
            pass('round-trip pcBuffer unchanged through load/save/reload');
        } else {
            let diff = 0;
            for (let i = 0; i < beforePc.length; i += 1) {
                if (beforePc[i] !== ctx2.pcBuffer[i]) diff += 1;
            }
            fail(`round-trip changed pcBuffer (${diff} byte diffs)`);
        }
    }

    // --- Test 2: repair corrupted valid_len on known-bad export ---
    {
        const artifacts = path.dirname(savePath);
        const entries = await fs.readdir(artifacts);
        const baselineName = entries.find((n) => n.endsWith('.sav') && n.toLowerCase().includes('corrupt'));
        if (!baselineName) {
            console.log('SKIP: no corrupted baseline save for repair test');
        } else {
            const baseline = new Uint8Array(await fs.readFile(path.join(artifacts, baselineName)));
            const beforeBad = invalidPcStreamValidLens(baseline);
            if (beforeBad.length === 0) {
                console.log('SKIP: corrupted baseline has no invalid valid_len to repair');
            } else {
                const ctx = loadPcContext(baseline);
                const out = new Uint8Array(baseline);
                saveAll(out, ctx);
                const afterBad = invalidPcStreamValidLens(out);
                if (afterBad.length === 0) {
                    pass(`repaired invalid valid_len (was ${JSON.stringify(beforeBad)})`);
                } else {
                    fail(`still invalid valid_len after saveAll: ${JSON.stringify(afterBad)}`);
                }
            }
        }
    }

    // --- Test 3: batch move when source slots exist ---
    {
        const buf = new Uint8Array(raw);
        const ctx = loadPcContext(buf);
        const movedPids = [];
        const attempted = [];
        for (const slot of MOVED_SLOTS) {
            try {
                readPcMonRaw(ctx, 1, slot);
                attempted.push(slot);
            } catch {
                continue;
            }
        }
        if (attempted.length === 0) {
            console.log('SKIP: no move test slots occupied in source save');
        } else {
            for (const slot of attempted) {
                const rawMon = readPcMonRaw(ctx, 1, slot);
                movedPids.push(ru32(rawMon, 0));
                movePcMon(ctx, { box: 1, slot }, { box: DEST_BOX });
            }
            const out = new Uint8Array(buf);
            saveAll(out, ctx);
            const badLens = invalidPcStreamValidLens(out);
            if (badLens.length === 0) pass('post-move PC stream valid_len fields OK');
            else fail(`post-move invalid valid_len: ${JSON.stringify(badLens)}`);
            const reloaded = loadPcContext(out);
            let foundIn10 = 0;
            movedPids.forEach((pid) => {
                if ([...boxOccupants(reloaded.pcBuffer, DEST_BOX).values()].includes(pid)) {
                    foundIn10 += 1;
                } else {
                    fail(`PID 0x${pid.toString(16)} missing from box ${DEST_BOX}`);
                }
            });
            if (foundIn10 === movedPids.length) {
                pass(`all ${movedPids.length} moved mons in box ${DEST_BOX}`);
            }
        }
    }

    if (failures > 0) {
        process.exitCode = 1;
        console.error(`\n${failures} failure(s)`);
    } else {
        console.log('\nAll checks passed');
    }
}

main().catch((err) => {
    console.error(err);
    process.exitCode = 1;
});

import fs from 'node:fs/promises';
import path from 'node:path';

import { loadPcContext, movePcMon, readPcMonRaw } from '../src/core/pc.js';

const MOVED_SLOTS = [4, 5, 7];
const DEST_BOX = 10;
const MON_SIZE_PC = 58;

function ru32(raw, off) {
    return raw[off] | (raw[off + 1] << 8) | (raw[off + 2] << 16) | (raw[off + 3] << 24);
}

function isValidMon(raw) {
    if (!raw || raw.length < MON_SIZE_PC) return false;
    const pid = ru32(raw, 0);
    if (pid === 0) return false;
    const species = raw[0x1c] | (raw[0x1d] << 8);
    if (species === 0 || species > 2500) return false;
    const exp = ru32(raw, 0x20);
    return exp > 0 && exp <= 2_000_000;
}

function boxPids(pcBuffer, box) {
    const out = [];
    const base = (box - 1) * 30;
    for (let slot = 1; slot <= 30; slot += 1) {
        const off = (base + slot - 1) * MON_SIZE_PC;
        if (off + MON_SIZE_PC > pcBuffer.length) break;
        const raw = pcBuffer.slice(off, off + MON_SIZE_PC);
        if (isValidMon(raw)) out.push({ slot, pid: ru32(raw, 0) });
    }
    return out;
}

async function main() {
    const artifacts = path.resolve('../backend/local_artifacts');
    const entries = await fs.readdir(artifacts);
    const name = entries.find((n) => n.endsWith('.sav'));
    const bytes = await fs.readFile(path.join(artifacts, name));
    const buf = new Uint8Array(bytes);

    const ctx = loadPcContext(buf);
    console.log(`pcBuffer length: ${ctx.pcBuffer.length}`);
    console.log(`box 10 before: ${boxPids(ctx.pcBuffer, 10).length} mons`);
    console.log(`box 2 before: ${boxPids(ctx.pcBuffer, 2).length} mons`);

    const movedPids = [];
    for (const slot of MOVED_SLOTS) {
        try {
            const raw = readPcMonRaw(ctx, 1, slot);
            movedPids.push(ru32(raw, 0));
            const placed = movePcMon(ctx, { box: 1, slot }, { box: DEST_BOX });
            console.log(`move box1:${slot} -> box${placed.box} slot${placed.slot}`);
        } catch (err) {
            console.error(`FAILED slot ${slot}: ${err.message}`);
        }
    }

    console.log(`\nbox 10 after: ${boxPids(ctx.pcBuffer, 10).length} mons`);
    boxPids(ctx.pcBuffer, 10).forEach(({ slot, pid }) => {
        const tag = movedPids.includes(pid) ? 'MOVED' : '';
        console.log(`  slot ${slot}: 0x${pid.toString(16)} ${tag}`);
    });
    console.log(`\nbox 2 after: ${boxPids(ctx.pcBuffer, 2).length} mons`);
    const in2 = movedPids.filter((pid) => boxPids(ctx.pcBuffer, 2).some((m) => m.pid === pid));
    console.log(`moved mons found in box 2: ${in2.length}`);
}

main().catch(console.error);

import fs from 'node:fs/promises';
import path from 'node:path';

import { saveAll } from '../src/core/commit.js';
import { loadPcContext, movePcMon, readPcMonRaw } from '../src/core/pc.js';

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

function findPid(pcBuffer, pid) {
    for (let box = 1; box <= 18; box += 1) {
        const base = (box - 1) * 30;
        for (let slot = 1; slot <= 30; slot += 1) {
            const off = (base + slot - 1) * MON_SIZE_PC;
            if (off + MON_SIZE_PC > pcBuffer.length) return null;
            const raw = pcBuffer.slice(off, off + MON_SIZE_PC);
            if (isValidMon(raw) && ru32(raw, 0) === pid) return { box, slot };
        }
    }
    return null;
}

async function main() {
    const artifacts = path.resolve('../backend/local_artifacts');
    const name = (await fs.readdir(artifacts)).find((n) => n.endsWith('.sav'));
    const buf = new Uint8Array(await fs.readFile(path.join(artifacts, name)));
    const ctx = loadPcContext(buf);

    const fromSlot = 8;
    const raw = readPcMonRaw(ctx, 1, fromSlot);
    const pid = ru32(raw, 0);
    console.log(`Moving box1:${fromSlot} pid=0x${pid.toString(16)} -> box10`);

    const placed = movePcMon(ctx, { box: 1, slot: fromSlot }, { box: 10 });
    console.log(`Placed at box ${placed.box} slot ${placed.slot}`);

    const inMem = findPid(ctx.pcBuffer, pid);
    console.log(`In-memory after move: box ${inMem?.box} slot ${inMem?.slot}`);

    const out = new Uint8Array(buf);
    saveAll(out, ctx);

    const reloaded = loadPcContext(out);
    const onDisk = findPid(reloaded.pcBuffer, pid);
    console.log(`After saveAll+reload: box ${onDisk?.box} slot ${onDisk?.slot}`);

    if (onDisk?.box === 10 && inMem?.box === 10) {
        console.log('PASS: mon survived save round-trip in box 10');
    } else {
        console.error('FAIL: placement lost or wrong after save');
        process.exitCode = 1;
    }
}

main().catch((err) => {
    console.error(err);
    process.exitCode = 1;
});

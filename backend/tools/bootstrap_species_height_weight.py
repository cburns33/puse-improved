#!/usr/bin/env python3
"""Build species_height_weight.json from a user-supplied height/weight CSV.

The CSV (backend/local_artifacts/species_height_weight_source.csv) has columns
"#,Name,Height (ft),Weight (lbs)". Only base species (no Mega/Alolan/Galarian/
Gigantamax/etc. forms) are matched, by exact name against pokemon.txt - form
variants are skipped rather than guessed at.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from core.data_loader import data_path, backend_root

SOURCE_CSV = backend_root() / "local_artifacts" / "species_height_weight_source.csv"


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def parse_height_to_inches(raw: str) -> int | None:
    match = re.match(r"(\d+)′(\d+)″", raw.strip())
    if not match:
        return None
    feet, inches = int(match.group(1)), int(match.group(2))
    return feet * 12 + inches


def load_pokemon_names() -> dict[int, str]:
    out: dict[int, str] = {}
    text = data_path("pokemon.txt").read_text(encoding="utf-8", errors="ignore")
    for line in text.splitlines():
        line = line.strip()
        if ":" not in line:
            continue
        left, right = line.split(":", 1)
        if left.strip().isdigit():
            out[int(left.strip())] = right.strip()
    return out


def load_base_species_csv(csv_path: Path) -> dict[str, dict]:
    """Only keep rows with a single-line name (i.e. no form label)."""
    out: dict[str, dict] = {}
    with csv_path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.reader(fh)
        next(reader)  # header
        for row in reader:
            if len(row) < 4:
                continue
            _, name_field, height_raw, weight_raw = row[:4]
            lines = [ln.strip() for ln in name_field.splitlines() if ln.strip()]
            if len(lines) != 1:
                continue
            height_in = parse_height_to_inches(height_raw)
            try:
                weight_lb = float(weight_raw)
            except ValueError:
                weight_lb = None
            if height_in is None or weight_lb is None:
                continue
            out[normalize(lines[0])] = {"height_in": height_in, "weight_lb": weight_lb}
    return out


def main() -> None:
    if not SOURCE_CSV.exists():
        raise SystemExit(f"Source CSV not found: {SOURCE_CSV}")

    base_species = load_base_species_csv(SOURCE_CSV)
    pokemon_names = load_pokemon_names()

    out: dict[str, dict] = {}
    unmatched: list[str] = []

    for sid, name in sorted(pokemon_names.items()):
        entry = base_species.get(normalize(name))
        if entry is None:
            unmatched.append(f"{sid}:{name}")
            continue
        out[str(sid)] = entry

    out_path = data_path("species_height_weight.json")
    out_path.write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")
    print(f"[OK] Wrote {len(out)} species height/weight entries -> {out_path}")
    if unmatched:
        print(f"[INFO] {len(unmatched)} species had no plain-name match (forms, fakemon, etc.); skipped")


if __name__ == "__main__":
    main()

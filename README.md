# PUSE - Pokémon Unbound Save Editor

> Live app: **[https://zannael.github.io/PUSE/](https://zannael.github.io/PUSE/)**

Web-based save editor for Pokémon Unbound (v2.1.1.1). Parsing, editing, checksum recalculation, and export can run entirely in the browser (**Local mode**, recommended) or through a local FastAPI server (**Backend mode**) with parity-focused behavior.

The project also includes **Nintendo Switch** and **experimental Nintendo 3DS** homebrew ports under `switch-homebrew/` and `3ds-homebrew/`.

## Features

### Save editing

| Area | What you can do |
|------|-----------------|
| **Party** | Edit all 6 slots: species, nickname, level, nature, item, ability slot, IVs/EVs, moves, PP/PP Ups, shiny, gender |
| **PC** | Browse boxes 1–24 and **Preset** (internal box 26); edit stored Pokémon; insert new Pokémon into writable empty slots; release (delete) stored Pokémon |
| **All** | Sortable, filterable table of every owned Pokémon; multiselect to copy/export Markdown or mass-release PC Pokémon |
| **Bag** | Quick pockets (main, balls, berries, TM case, key items), search fallback, explicit **SAVE BAG CHANGES** before write |
| **Resources** | Money (up to 999,999,999) and Battle Points (up to 65,535) |
| **Export** | Download checksum-safe `.sav` / `.srm` after edits |

PC support includes Unbound-specific fragmented box layouts (tail boxes) where the standard contiguous PC stream does not apply. Box 25 is hidden from navigation by design.

### Pokémon editor

Open any party or PC Pokémon for a full modal editor:

- **Stats** — IV/EV sliders, battle stat preview, Hidden Power type, growth-aware level editing
- **Moves** — per-slot PP/PP Up controls, **MAX PP**, Showdown set import (species/level/identity preserved)
- **Dex** — Unbound Dex learnsets, save-progress TM/HM hints, links to external Dex locations, manual **Seen** / **Caught** flags
- **Info** — species search (form-aware labels), nickname, shiny/gender with PID-aware warnings

For PC Pokémon, the editor also has a **Release** button that permanently clears the slot (with confirmation). Party Pokémon cannot be released from the editor, because the in-game party is a packed list that needs slot-shifting.

**Legit mode** (header toggle, persisted in browser) enforces a 510 EV cap and surfaces learnset/level-cap warnings when enabled. **Cap: Normal / Expert** selects which level-cap table is used for warnings and roster export (save difficulty is not auto-detected yet).

### All Pokémon table

The bottom-nav **All** tab lists every party and PC Pokémon in a single sortable, filterable table (dex #, level, nature, ability, all six IVs, IV total, and location). It is built for triage and bulk actions:

- **Sort** by any column (level, individual IVs, IV total, name, etc.) with click-to-sort headers.
- **Filter** with search and quick chips (Shiny, Hidden ability, 6 IV, **2+ perfect IVs**), or open **IV filters** to set minimum thresholds per stat with **Match all** (every stat) / **Match any** (at least one stat) modes plus a minimum IV total.
- **Select** individual rows or use **Select filtered** to select everything matching the current filters. Selection is shared with the roster export queue used elsewhere.
- **Act on the selection** in-table: **COPY SELECTION** / **EXPORT** as Markdown, or **DELETE** to mass-release the selected PC Pokémon (party Pokémon are skipped).

Clicking any row opens the standard editor modal.

### Team sharing (roster export)

Copy or download party + PC data as Markdown for team sharing, planning, or AI agent workflows. See [Roster export](#roster-export) below.

### Living Dex

The bottom-nav **Dex** tab reads caught/seen flags from your save and shows completion progress. See [Living Dex tab](#living-dex-tab) below.

### Recovery & utilities

- **RTC tools** — pair repair and quick-fix candidate generation for known RTC tampering scenarios (home page, before upload)
- **SRM / SAV converter** — convert between `.srm` and `.sav` before loading (home page)
- **Optional sprites** — Pokémon and item icons from pinned CDN manifests or local folders; placeholders when missing

## Runtime Modes

- **Local mode (`VITE_RUNTIME_MODE=local`)**: parsing, editing, checksum, and export run completely in the browser. Used by the GitHub Pages deployment.
- **Backend mode (`VITE_RUNTIME_MODE=backend`)**: uses a local FastAPI server at `VITE_API_BASE_URL` (default `http://localhost:8000`).

Both modes target the same behavior. When they differ, backend logic is treated as canonical during development.

## End-User UX (Website)

Start from the live app: **[https://zannael.github.io/PUSE/](https://zannael.github.io/PUSE/)**

Typical workflow:

1. **Load** a `.sav` or `.srm` file (convert first if needed).
2. **Edit** via Party, PC Box, All, Bag, or Living Dex tabs; tap a Pokémon for the full editor.
3. **Share or bulk-manage** (optional) — **COPY ROSTER**, **COPY SELECTION**, download Markdown exports, or use the **All** tab to filter, multiselect, and mass-release.
4. **Download** the updated save file (checksum-safe).

For RTC recovery, use the tools on the home page before uploading a broken save.

After upload, the header shows money/BP, legit mode, cap profile, roster copy/export actions, and save/download controls.

## Roster export

After loading a save, use the header actions **COPY PARTY**, **COPY ROSTER**, or **EXPORT ROSTER**. All three work in **Local** and **Backend** runtime modes.

| Action | Output |
|--------|--------|
| COPY PARTY | Clipboard Markdown for the current party only |
| COPY ROSTER | Clipboard Markdown for party + all occupied PC slots (boxes 1–25 and preset box 26) |
| **COPY SELECTION** | Clipboard Markdown for Pokémon you queued with the export toggle (party or PC) |
| EXPORT ROSTER | Downloads `<save-name>_roster.md` with the same content as COPY ROSTER |
| **EXPORT SELECTION** | Downloads `<save-name>_selection.md` for the queued Pokémon |

Use the **+** toggle on party cards or PC slots to build a session-only export queue. **Add box to export** on the PC screen queues every occupied slot in the current box, and the **All** tab can multiselect (including **Select filtered**) into the same queue. Selected PC Pokémon use the same detailed stat blocks as party members so agent comparisons get full IV/EV/move context. The queue clears when you load a new save file.

The **Cap: Normal / Expert** selector controls level-cap checks in the export. Expert caps come from the Unbound expert milestone table; the save difficulty flag is not auto-detected yet.

### Markdown sections

1. **Game Progress** — badges, normal/expert level caps, champion status, money/BP, key items (DexNav, Stat Scanner, Mega Ring), consumable counts
2. **Level Cap Check** — Pokémon above the selected cap profile (skipped on champion saves)
3. **Expert Speed Tiers** — party speed vs upcoming expert boss threats (skipped on champion saves)
4. **Party** — detailed blocks per mon: types, stats, IV/EV, moves, Hidden Power, egg-move flags, evolution hints
5. **PC** — compact one-line entries grouped by box (empty slots omitted)

Party entries include calculated battle stats, Hidden Power type, and evolution tags (for example `→ [FinalEvolution] (BST n)` on unevolved Pokémon).

### Dex tab (progress-aware)

The Pokémon editor **Dex** tab uses your loaded save to annotate learnsets:

- **Living Dex flags** — mark or clear Seen/Caught (with confirmation); Caught also sets Seen
- **Save progress banner** — badges, level cap profile, TM Case status, TM/HM count in bag
- **TM / HM moves** — moves whose TM item is not in your bag are marked `(TM not in bag)`; locked TM Case shows `(TM Case not unlocked)`
- **Move links** — each move opens the external [Unbound Dex](https://ydarissep.github.io/Unbound-Pokedex/) filtered to species that learn it
- **Tutor moves** — labeled as story-dependent (tutor unlock flags are not in save data yet)
- **Legit mode** — learnset validation when legit mode is on

Works in Local and Backend modes via `GET /game-progress` (backend) or in-browser parsing (local).

### Living Dex tab

The bottom-nav **Dex** tab reads caught/seen flags from the trainer save section (CFRU SaveBlock1 layout):

- **Completion summary** — seen and caught percentages for species IDs 1–999
- **Filterable list** — default filter shows species not yet caught; search by name or ID
- **Unbound Dex links** — open encounter/location data for each species
- **Manual flags** — mark or clear Seen/Caught with a confirmation prompt (also available on the editor Dex tab)

API: `GET /pokedex/summary`, `GET /pokedex/species/{id}`, `POST /pokedex/species/{id}/flags` (backend) or equivalent local core calls. Species above ID 999 are not stored in this bitfield.

## Technical Notes

- Frontend local mode and backend mode are designed to remain behaviorally aligned.
- API contracts are intentionally stable (`nature_id`, `item_id`, `ability_index`, etc.).
- Catalog data is ROM-truth synchronized across backend and frontend local runtime.
- Optional icon systems degrade safely with placeholders when mappings/assets are unavailable.

## Project Structure

- `frontend/` React + Vite UI
- `backend/` FastAPI API and save editing modules
- `backend/data/` static lookup tables (`items.txt`, `pokemon.txt`, `moves.txt`, `tms.txt`)

## Requirements

- Node.js 20+
- Python 3.10+

## Local Run

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Frontend default URL: `http://localhost:5173`

- For **frontend-only mode** (recommended), set in `frontend/.env`:
  - `VITE_RUNTIME_MODE=local`
- For **backend mode**, set in `frontend/.env`:
  - `VITE_RUNTIME_MODE=backend`
  - `VITE_API_BASE_URL=http://localhost:8000`

### Backend (only if using backend mode)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --host ${BACKEND_HOST:-0.0.0.0} --port ${BACKEND_PORT:-8000}
```

## Docker

```bash
docker compose up --build
```

## 3DS Homebrew (3DSX / CIA)
EXPERIMENTAL, USE AT YOUR OWN RISK!
Any help in developing it will be appreciated.

A Nintendo 3DS port of PUSE is available under `3ds-homebrew/`. Requires Docker — no host C++ toolchain needed.

### Prerequisites

- Docker Desktop (or Docker Engine on Linux)
- `3ds-homebrew/tools/Dockerfile` builds the full devkitARM + libstarlight environment automatically
- Place your save at `sdmc:/3ds/puse/Unbound.sav` before launching

### Build .3dsx (Homebrew Launcher)

```bash
# First build or after any source change
3ds-homebrew/scripts/build_docker.sh
```

Output: `3ds-homebrew/puse-3ds.3dsx`

Copy to `sdmc:/3ds/puse-3ds/puse-3ds.3dsx` and launch via Homebrew Launcher.

### Build .cia (FBI install — Home Menu title)

```bash
# Rebuild Docker image first (only needed once, or after Dockerfile changes)
docker build -t puse-3ds-dev -f 3ds-homebrew/tools/Dockerfile 3ds-homebrew/tools/

# Then build the .3dsx + .cia
3ds-homebrew/scripts/build_docker.sh
3ds-homebrew/scripts/build_cia.sh
```

Output: `3ds-homebrew/puse-3ds.cia`

Install via FBI from SD card. The CIA uses test/false keys and is compatible with Luma3DS.

### Controls

| Button | Action |
|--------|--------|
| A | Select / confirm |
| B | Back |
| L | PC boxes |
| R | Bag |
| Select | Money & BP |
| Y | Toggle legit mode (510 EV cap) |
| X | Save (backup created automatically) |
| Start | Exit |

### RTC Quick Fix

For saves broken by the RTC bug: go to **Select → Money screen → RTC Quick Fix**. Generates three candidate saves and applies your chosen profile directly to `Unbound.sav`. Restart PUSE after applying.

### Optional: Pokémon Icons

Place 48×48 PNG icons at `sdmc:/3ds/puse/icons/pokemon/{id:04d}.png`. Missing icons are silently skipped.

---

## Switch Homebrew (NRO)

A Nintendo Switch `.nro` port of PUSE is available under `switch-homebrew/`. Build requires Docker and devkitPro — no host C++ toolchain needed.

### Prerequisites

- Docker Desktop (or Docker Engine on Linux)
- The `switch-homebrew/tools/Dockerfile` provides the full devkitPro + Plutonium build environment automatically

### Build

```bash
# Full build: Docker image + compile + SD card bundle
switch-homebrew/scripts/build_docker.sh

# If backend/data changed, sync static data into ROMFS first
switch-homebrew/scripts/sync_romfs_data.sh
```

Output: `switch-homebrew/artifacts/sdmc/switch/puse/` ready to copy to an SD card.

### SD Card Setup

1. Copy `switch-homebrew/artifacts/sdmc/switch/puse/` to the root of your Switch SD card.
2. Place your save file at `sdmc:/switch/puse/Unbound.sav`.
3. Launch `hbmenu`, then open PUSE.

### Controls

| Button | Action |
|--------|--------|
| A | Select / confirm edit |
| B | Back / cancel |
| X | Save changes to SD card |
| + | Exit to hbmenu |

### Capabilities

- Browse and edit all 6 party Pokémon (species, nickname, level, nature, item, ability, IVs, EVs, moves + PP/PP-Up, shiny/gender)
- Browse all 18 PC boxes; edit any stored Pokémon (same fields as party, PP-Up editable)
- Read and write trainer money (up to 999,999,999)
- Save written in-place to `Unbound.sav` on SD card; toast confirmation on success

### Optional: Pokémon and Item Icons

Sprites are not required to run the NRO — the app boots and all editing works without them; menu items simply show no icon.

**Pokémon icons** — copy the `gFrontSprite*.png` sprite sheet into:
```
sdmc:/switch/puse/icons/pokemon/
```
Sources:
- [Skeli789/Dynamic-Pokemon-Expansion](https://github.com/Skeli789/Dynamic-Pokemon-Expansion/tree/master/graphics/frontspr) (original)
- [Shiny-Miner/Dynamic-Pokemon-Expansion-Gen-9](https://github.com/Shiny-Miner/Dynamic-Pokemon-Expansion-Gen-9/tree/master/graphics/frontspr) (Gen 9 extended)

**Item icons** — copy item PNG files into:
```
sdmc:/switch/puse/icons/items/
```
Source: [PokeAPI/sprites](https://github.com/PokeAPI/sprites) item icons or Leon's ROM Base item icon pack.

## Optional Pokemon Sprites

- Pokemon icon sprites are optional and not required to run the app.
- If missing, the backend logs a warning and returns a tiny fallback image, so UI keeps working.
- Source for icon assets:
  - Upstream (original): `https://github.com/Skeli789/Dynamic-Pokemon-Expansion/tree/master/graphics/frontspr`
  - Extended Gen 9 fork: `https://github.com/Shiny-Miner/Dynamic-Pokemon-Expansion-Gen-9/tree/master/graphics/frontspr`
- To enable sprites locally, clone/copy that folder into:
  - `backend/icons/pokemon/`

### Frontend icon delivery (GitHub Pages / local mode)

- In frontend local mode, icons are resolved without backend endpoints:
  - Pokemon icons: pinned commit from `Shiny-Miner/Dynamic-Pokemon-Expansion-Gen-9` (fork of `Skeli789/Dynamic-Pokemon-Expansion`)
  - Item icons: `PokeAPI/sprites`
- Manifests are generated and committed under:
  - `frontend/src/data/pokemon-icon-manifest.json`
  - `frontend/src/data/item-icon-manifest.json`
- To refresh mappings after changing pinned commits or source lists:
  - Run `npm run icons:manifest` inside `frontend/`
  - (Optional CI/local guard) run `npm run icons:check`
- Unmapped IDs gracefully fall back to local placeholders in `frontend/public/icons/`.

## Optional Item Icons

- Item icons are optional and not required to run the app.
- If missing, backend item-icon lookup simply returns no icon and UI keeps working.
- Item icon sources are:
  - `https://github.com/PokeAPI/sprites` (item icons)
  - Leon's ROM Base item icon pack
- Place them like this:
  - Copy the PokeAPI item icon folder contents into `backend/icons/items/Base Items/`
  - Copy Leon's ROM Base item icon folders/files into `backend/icons/items/`
- The backend resolver checks `Base Items/` first (including subfolders), then falls back to the other folders in `backend/icons/items/`.

## Environment Variables

### Backend (`backend/.env`)

- `BACKEND_HOST` default `0.0.0.0`
- `BACKEND_PORT` default `8000`
- `CORS_ORIGINS` comma-separated origins

### Frontend (`frontend/.env`)

- `VITE_API_BASE_URL` backend base URL
- `VITE_RUNTIME_MODE` runtime mode (`backend` or `local`)
- `VITE_BASE_PATH` Vite base path (`/` for local dev, `/<repo>/` for project Pages)

## Deployment (Maintainers)

- Frontend deploy is handled by `.github/workflows/deploy-pages.yml`.
- One-time setup: in GitHub, go to `Settings -> Pages -> Source` and choose **GitHub Actions**.
- On push to `main` (or manual run), the workflow builds `frontend/dist` in local mode, sets `VITE_BASE_PATH=/<repo>/`, and copies `index.html` to `404.html` for SPA fallback.
- Icons in local mode are served from pinned CDN commits via generated manifests, so no backend icon folders are required on GitHub Pages.

## Safety Notes

- Always work on copies of your `.sav` files (even if the code SHOULD never touch you original one).
- Keep personal `.sav`/ROM files under `backend/local_artifacts/` (ignored by git).
- Never share personal saves publicly in issue reports.
- This project is community-maintained and evolving.

## Disclaimer

This project is an unofficial fan-made utility. Use it only with legally obtained game files and your own save data.

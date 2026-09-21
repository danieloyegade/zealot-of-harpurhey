# Building Texture Pass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every in-world building that still ships flat placeholder colours a set of real PBR surface materials (base colour, ORM and normal maps), without touching geometry.

**Architecture:** This follows the precedent set by Vinyl Exchange and Nice Things: tiling PBR sets at metric scale, with colours measured from the reference photographs. It generalises that precedent into three shared pieces:

- **`commonSurfaces.py`** holds parameterised builders (brick, ashlar, painted metal, painted timber, timber, concrete, plaster, painted render, glazed tile). Each building's texture script is then only a measured palette plus a list of builder calls.
- **`texturedRuntimeExport.py`** post-processes the GLB that already ships. It stashes an untextured copy, imports it, swaps placeholder slots for textured materials, box-projects UVs per material slot, re-exports, and fails if any node name changes. No building's create script has to be re-implemented, and the geometry is exactly what ships today.
- **`config/building-textures.json`** is one contract that drives both the exporter and a `npm test` check (surfaces present, UV0 on textured primitives, no unaccounted placeholders, size budget).

**Tech Stack:** Blender 5.2.1 (bundled Python and numpy; system `python3` has neither numpy nor PIL), `vinylExchangeTextures.Surface` toolkit, `surfaceWeathering.build_pbr_material`, glTF 2 GLB, Three.js 0.185 `MeshStandardMaterial`, `node --test`.

**Spec:** No separate spec. The request was "a plan for textures for each building that has no textures yet". The audit it rests on is in the *Scope* section below.

## Global Constraints

- Map convention (unchanged from Vinyl Exchange): `<slug>-{basecolor,orm,normal}.png`, sRGB base colour, ORM = R occlusion / G roughness / B metallic, OpenGL (+Y) tangent-space normal, 1 Blender unit = 1 m.
- Colours are measured from `references/`, not invented. No pixels from a reference photograph may reach an output map (`docs/ASSET_RIGHTS.md`).
- Default map size is 1024². Use 2048² only when the review render shows mush at street distance, and never for more than two sets per building.
- Per-GLB budget for newly textured buildings: **5,000,000 bytes** (Nice Things' 9-set GLB is 1.5 MB). The exceptions are Real Camera (9.5 MB) and Coral (7 MB), whose untextured geometry is already 7.5 MB and 4.8 MB.
- Runtime material names: `MAT_<CODE>_Surface_<slug>`. Placeholder materials not listed in a building's `placeholders` must be listed in its `untexturedAllowed`.
- Glass, emissive/glow, lettering, logos, posters, signage and interior-furniture props stay as placeholders. Signage needs bespoke artwork (as Cass Art's signage pass does) and is out of scope here.
- Blender invocation: `/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python <script> -- <args>`.
- Cache-buster for every re-exported GLB: `?v=textured-YYYYMMDD` (the date of the change).
- Repo protocol (`AGENTS.md`): read `SYNC.md`, then run `git log --oneline -20` and `git status` before starting. Commit **and push** after each task. Append a `SYNC.md` entry at the end of the session.

## Scope

Audit of `public/assets/models/*.glb` as loaded by `src/world/createWorld.ts` on 2026-09-22 (embedded images per GLB):

| Building | GLB | Status | In this plan |
|---|---|---|---|
| Come Through Lab | `come_through_lab.glb`, `ctl_dropbox.glb`, `ctl_dropoff_props.glb` | 0 images | Task 5 |
| The Hive | `the_hive.glb` | 0 images | Task 6 |
| Gulliver's | `harperhey-gullivers.glb` | 0 images | Task 7 |
| Renee | `renee-blockout.glb` | 0 images | Task 8 |
| Real Camera | `real_camera.glb` | 0 images | Task 9 |
| Greek Gyros | `greek_gyros.glb` | 0 images | Task 10 |
| Village Books | `village-books-blockout.glb` | 0 images | Task 11 |
| Advanced Photo | `advanced-photo-blockout.glb` | 0 images | Task 12 |
| ABC Building | `abc_building.glb` | 0 images, **no UVs** | Task 13 |
| Dreams | `harperhey-dreams-greybox.glb` | 0 images | Task 14 |
| Coral | `harperhey-coral-shop.glb` | 0 images; brick and concrete replaced at runtime by world-prototype tiles | Task 15 |
| Nice Things | `nice-things-blockout.glb` | **in flight in another session** (`niceThingsTextures.py`, `exportNiceThings.py` uncommitted) | Excluded |
| Cass Art | `cass_art.glb` | **in flight in another session** (`cassArtTextures.py` uncommitted) | Excluded |
| MCR1, Spice Cabin, Vinyl Exchange | — | already textured | — |
| Florist (legacy) | `harperhey-florist.glb` | not loaded; superseded by Nice Things | Excluded |

## Decisions (confirmed by Daniel, 2026-09-22)

1. **Dreams:** texture the approved greybox. The older photographic `harperhey-dreams.glb` stays retired.
2. **Coral:** proceed with the two reference photos.
3. **Village Books and ABC:** left to Claude's judgement from the photographs:
   - **Village Books upper wall:** off-white painted render with dark window frames (`DSC06337.JPG`, `bbc76082…jpeg`), so `painted_render`. The shop floor is dark and hard, so `concrete`, not timber.
   - **ABC end block** (the west-end block carrying the Smolensky / Every Man signs): pale painted render under the "ABC" letters (`Screenshot 2026-09-11 at 14.43.55.png`), so `painted_render`. The blockout's brown "brick" placeholder was a guess, and the only brick in frame is the neighbouring building.
   - **ABC planters:** black powder-coated steel boxes (`IMG_8908.HEIC`), so `painted_metal`, not concrete.
4. **Signage, lettering and logos:** a later artwork pass.

## Precondition

The other session's Nice Things / Cass Art work touches `src/world/createWorld.ts` (uncommitted diff on 2026-09-22). Do not start Task 5 until `git status --short src/world/createWorld.ts` is empty or that work has been committed. Tasks 1–4 touch no shared files and can start immediately.

## File structure

| File | Responsibility |
|---|---|
| `config/building-textures.json` (create) | One entry per textured GLB: prefix, texture dir, placeholder→slug map, allowlist, expected surface count, byte budget |
| `tests/building-textures.test.mjs` (create) | Contract check of each listed GLB against its entry |
| `blender/scripts/commonSurfaces.py` (create) | Parameterised surface builders, palette loading, `run_texture_pass` |
| `blender/scripts/measurePatch.py` (create) | Median-colour sampling of a reference photo into a building's `palette.json` |
| `blender/scripts/texturedRuntimeExport.py` (create) | Stash, import, swap materials, per-slot metric UVs, export, inspect |
| `blender/scripts/exportTexturedBuilding.py` (create) | CLI: texture every GLB of one building from the contract |
| `blender/source/runtime-untextured/` (create) | Untextured copies of shipped GLBs, the exporter's input |
| `tests/blender/test_*.py` (create) | Blender-run tests for the three Python modules |
| `src/world/buildingMaterials.ts` (create) | `profileAuthoredMaps()`: shared texture filtering for authored PBR maps |
| `blender/scripts/<building>Textures.py` (create, one per building) | Palette keys + builder calls |
| `blender/source/textures/<building>/` (create) | `palette.json`, maps, `validation.json` |
| `renders/<building>-textures/` (create) | Review renders + `00-contact-sheet.png` |
| `src/world/createWorld.ts` (modify) | Per-building policy keeps maps; cache-busters |

---

### Task 1: Building texture contract and test

**Files:**
- Create: `config/building-textures.json`
- Create: `tests/building-textures.test.mjs`

**Interfaces:**
- Produces: the contract entry shape `{ building, glb, surfacePrefix, textureDir, placeholders, untexturedAllowed, expectedSurfaces, maxBytes, legacyExporter? }`, which Tasks 4–15 read and extend.

- [ ] **Step 1: Write the contract, seeded with Vinyl Exchange as the known-good case**

```json
{
  "buildings": [
    {
      "building": "vinyl-exchange",
      "glb": "assets/models/vinyl-exchange-blockout.glb",
      "legacyExporter": "blender/scripts/exportVinylExchangeBlockout.py",
      "surfacePrefix": "MAT_VE_Surface_",
      "textureDir": "blender/source/textures/vinyl-exchange",
      "placeholders": {},
      "untexturedAllowed": [
        "MAT_VE_Interior_PLACEHOLDER",
        "MAT_VE_DisplaySurface_PLACEHOLDER",
        "MAT_VE_Glass_PLACEHOLDER",
        "MAT_VE_Plaque_PLACEHOLDER"
      ],
      "expectedSurfaces": 10,
      "maxBytes": 16000000
    }
  ]
}
```

- [ ] **Step 2: Write the test**

```js
import assert from 'node:assert/strict';
import { readFile, stat } from 'node:fs/promises';
import { resolve } from 'node:path';
import test from 'node:test';

const root = resolve(new URL('..', import.meta.url).pathname);
const contract = JSON.parse(
  await readFile(resolve(root, 'config/building-textures.json'), 'utf8'),
);

async function readGlbJson(path) {
  const bytes = await readFile(path);
  assert.equal(bytes.toString('latin1', 0, 4), 'glTF', `${path} is not a GLB`);
  assert.equal(bytes.readUInt32LE(16), 0x4e4f534a, `${path} has no JSON chunk`);
  return JSON.parse(bytes.toString('utf8', 20, 20 + bytes.readUInt32LE(12)));
}

for (const entry of contract.buildings) {
  test(`${entry.glb} carries its authored surface materials`, async () => {
    const path = resolve(root, 'public', entry.glb);
    const gltf = await readGlbJson(path);
    const materials = gltf.materials ?? [];

    const surfaces = materials
      .map((material, index) => ({ material, index }))
      .filter(({ material }) => (material.name ?? '').startsWith(entry.surfacePrefix));
    assert.equal(surfaces.length, entry.expectedSurfaces, 'surface material count');
    for (const { material } of surfaces) {
      assert.ok(material.pbrMetallicRoughness?.baseColorTexture, `${material.name}: no base colour map`);
      assert.ok(material.pbrMetallicRoughness?.metallicRoughnessTexture, `${material.name}: no ORM map`);
      assert.ok(material.normalTexture, `${material.name}: no normal map`);
    }

    const surfaceIndices = new Set(surfaces.map(({ index }) => index));
    const unmapped = (gltf.meshes ?? [])
      .flatMap((mesh) => mesh.primitives)
      .filter((primitive) => surfaceIndices.has(primitive.material))
      .filter((primitive) => !('TEXCOORD_0' in primitive.attributes));
    assert.equal(unmapped.length, 0, 'textured primitives without TEXCOORD_0');

    const allowed = new Set(entry.untexturedAllowed);
    const unaccounted = materials
      .map((material) => material.name ?? '')
      .filter((name) => !name.startsWith(entry.surfacePrefix) && !allowed.has(name));
    assert.deepEqual(unaccounted, [], 'materials neither textured nor allowlisted');

    const { size } = await stat(path);
    assert.ok(size <= entry.maxBytes, `${size} bytes exceeds budget ${entry.maxBytes}`);
  });
}
```

- [ ] **Step 3: Run it and confirm it passes on the seed**

Run: `npm test`
Expected: PASS, including `assets/models/vinyl-exchange-blockout.glb carries its authored surface materials`.

- [ ] **Step 4: Prove the test can fail**

Temporarily set the seed's `"expectedSurfaces": 11`, run `npm test`, and confirm it FAILS with `surface material count`. Revert to `10`.

- [ ] **Step 5: Commit**

```bash
git add config/building-textures.json tests/building-textures.test.mjs
git commit -m "Add a contract test for textured building GLBs"
git push
```

---

### Task 2: Shared surface builders

**Files:**
- Create: `blender/scripts/commonSurfaces.py`
- Test: `tests/blender/test_common_surfaces.py`

**Interfaces:**
- Consumes: `vinylExchangeTextures.Surface`, `lin`, `write_surface`, `review_render`, `contact_sheet`, `seam_report`; `surfaceWeathering.F`, `smoothstep`.
- Produces (all builders return a `Surface`; colours are sRGB hex strings; `seed` is keyword-only and required):
  - `brick(slug, description, face, mortar, soot, *, seed, soot_amount=0.30, tile=1.80, px=1024, pitch=0.225, course=0.075, joint=0.010, face_spread=0.14)`
  - `ashlar(slug, description, stone, joint_colour, soot, *, seed, soot_amount=0.25, tile=2.40, px=1024, course=0.30, block=0.60, joint=0.008)`
  - `painted_metal(slug, description, paint, *, seed, rust="#5E3620", bare="#6B6C6E", rust_amount=0.55, chips=20, tile=0.50, px=1024, roughness=0.55, metallic=0.0)`
  - `painted_timber(slug, description, paint, *, seed, primer="#8A7A62", tile=0.60, px=1024, gloss=0.42, chips=14)`
  - `timber(slug, description, light, dark, *, seed, tile=(0.60, 1.20), px=(512, 1024), finish=0.55)`
  - `concrete(slug, description, colour, *, seed, stain="#4A4A46", stain_amount=0.25, tile=2.00, px=1024, roughness=0.88)`
  - `plaster(slug, description, colour, *, seed, tile=2.00, px=512, roughness=0.90)`
  - `painted_render(slug, description, colour, dirt, *, seed, dirt_amount=0.30, tile=2.40, px=1024, roughness=0.80)`
  - `glazed_tile(slug, description, glaze, grout, *, seed, tile_size=(0.152, 0.076), tile=0.912, px=1024, spread=0.10, craze=True)`
  - `load_palette(path, required) -> dict[str, str]` (key → albedo hex)
  - `run_texture_pass(asset, texture_dir, render_dir, palette_path, builders, argv) -> list[dict]`

- [ ] **Step 1: Write the failing test**

```python
"""Run:
    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python-exit-code 1 --python tests/blender/test_common_surfaces.py
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / "blender" / "scripts"))

from commonSurfaces import (  # noqa: E402
    ashlar, brick, concrete, glazed_tile, painted_metal, painted_render,
    painted_timber, plaster, timber,
)
from vinylExchangeTextures import seam_report  # noqa: E402


def cases():
    small = {"px": 128}
    return [
        (brick("t-brick", "t", "#8A4A3A", "#9A958C", "#3A3632", seed=1, **small), "#8A4A3A"),
        (ashlar("t-ashlar", "t", "#BBA48A", "#6C5B4F", "#3A332C", seed=2, **small), "#BBA48A"),
        (painted_metal("t-metal", "t", "#2A3F6A", seed=3, **small), "#2A3F6A"),
        (painted_timber("t-paint", "t", "#1E3A2A", seed=4, **small), "#1E3A2A"),
        (timber("t-timber", "t", "#B08A60", "#6A4A30", seed=5, px=(64, 128)), "#8E6C48"),
        (concrete("t-concrete", "t", "#8C8A84", seed=6, **small), "#8C8A84"),
        (plaster("t-plaster", "t", "#E8E0D2", seed=7, **small), "#E8E0D2"),
        (painted_render("t-render", "t", "#EDEBE4", "#5A5850", seed=8, **small), "#EDEBE4"),
        (glazed_tile("t-tile", "t", "#1F5A3A", "#CFC8B8", seed=9, **small), "#1F5A3A"),
    ]


def hex_rgb(value):
    value = value.lstrip("#")
    return np.array([int(value[i:i + 2], 16) for i in (0, 2, 4)], float)


def main():
    failures = []
    for surface, dominant in cases():
        base, orm, normal = surface.maps()
        for name, grid in (("base", base), ("orm", orm), ("normal", normal)):
            if not np.isfinite(grid).all() or grid.min() < 0 or grid.max() > 1:
                failures.append(f"{surface.slug}: {name} map out of range")
        for axis, step in seam_report(surface, {"basecolor": base, "orm": orm, "normal": normal}).items():
            if step["wrap"] > max(3.0, step["typical"] * 3.0):
                failures.append(f"{surface.slug}: seam on {axis} ({step})")
        mean = np.array(surface.record()["base_srgb_mean"], float)
        if np.abs(mean - hex_rgb(dominant)).max() > 40:
            failures.append(f"{surface.slug}: mean {mean} drifted from {dominant}")

    try:
        brick("t-bad", "t", "#8A4A3A", "#9A958C", "#3A3632", seed=1, tile=1.0, px=64)
        failures.append("brick accepted a tile that is not a whole number of bricks")
    except ValueError:
        pass

    if failures:
        raise AssertionError("\n".join(failures))
    print("commonSurfaces: all builders tile, stay in range and hold their palette")


main()
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python tests/blender/test_common_surfaces.py`
Expected: exit code 1 with `ModuleNotFoundError: No module named 'commonSurfaces'`.

- [ ] **Step 3: Write `blender/scripts/commonSurfaces.py`**

```python
"""Parameterised tiling surfaces shared by the building texture passes.

Vinyl Exchange and Nice Things each wrote their surfaces by hand.  The
buildings that follow share most of their materials -- clay brick, sandstone
ashlar, painted steel, painted joinery, concrete -- and differ mainly in
palette.  Each builder here takes the measured palette and returns a
`vinylExchangeTextures.Surface` in the same glTF convention (sRGB base colour,
ORM, OpenGL normal) at metric scale, so a building's texture script is a
palette plus a list of calls.

Every repeating feature (brick pitch, course height, tile module) must divide
the tile exactly, or the maps would not wrap; `_check_tiles` enforces that.
Weathering that depends on where a texel sits on the building belongs to a
later `surfaceWeathering` atlas bake, not here.
"""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.append(str(Path(__file__).resolve().parent))

from surfaceWeathering import F, smoothstep  # noqa: E402
from vinylExchangeTextures import Surface, lin  # noqa: E402


# ------------------------------------------------------------------ helpers

def _check_tiles(tile, *pitches):
    for pitch in pitches:
        count = tile / pitch
        if abs(count - round(count)) > 1e-6:
            raise ValueError(f"tile {tile} m is not a whole number of {pitch} m pitches")


def _check_even_courses(tile, course):
    if round(tile / course) % 2:
        raise ValueError(f"a {tile} m tile holds an odd number of {course} m courses; "
                         "a half-bond stagger would not wrap")


def _chips(s, count, seed, size=(0.0010, 0.0038)):
    field = np.zeros(s.shape, F)
    rng = np.random.default_rng(seed)
    for _ in range(count):
        s.stamp(field, rng.uniform(0, s.width), rng.uniform(0, s.height),
                rng.uniform(*size), value=rng.uniform(0.5, 1.0), core=0.7,
                elongate=rng.uniform(0.6, 1.8))
    return field


def _unit_centres(s, pitch, course):
    """Stretcher-bond unit centres per texel, and the per-row stagger."""
    row = np.floor(s.y / course)
    stagger = np.where(np.mod(row, 2) > 0.5, pitch * 0.5, 0.0).astype(F)
    centre_x = (np.floor((s.x + stagger) / pitch) + 0.5) * pitch - stagger
    centre_y = (row + 0.5) * course
    return centre_x, centre_y, stagger


def _joints(s, pitch, course, stagger, joint):
    half = joint * 0.5
    soft = min(0.0015, half * 0.5)
    return np.maximum(smoothstep(half, half - soft, s.repeat(s.y, course)),
                      smoothstep(half, half - soft, s.repeat(s.x + stagger, pitch)))


def _soot(s, seed, colour, amount):
    """Run-down soot: streak-led, concentrated in patches, never a ruled band."""
    streaks = s.noise((0.12, 1.2), seed, 3) ** 2
    patchy = smoothstep(0.3, 0.8, s.noise((0.6, 0.9), seed + 1, 2))
    dirt = np.clip(streaks * (0.4 + 0.9 * patchy), 0.0, 1.0)
    s.tint(dirt, colour, amount)
    s.roughen(dirt, 0.92, 0.4)


# ----------------------------------------------------------------- masonry

def brick(slug, description, face, mortar, soot, *, seed, soot_amount=0.30,
          tile=1.80, px=1024, pitch=0.225, course=0.075, joint=0.010, face_spread=0.14):
    """Stretcher-bond clay brick.  Pitches include the joint: 1.80 m = 8 x 24."""
    _check_tiles(tile, pitch, course)
    _check_even_courses(tile, course)
    s = Surface(slug, description, tile, tile, px, px)
    s.fill(lin(face), 0.84)

    centre_x, centre_y, stagger = _unit_centres(s, pitch, course)
    at_centre = (centre_x - s.x, centre_y - s.y)
    tone = s.noise((pitch, course), seed, warp=at_centre)
    s.base *= (1.0 - face_spread * 0.5 + face_spread * tone)[..., None]
    overburnt = smoothstep(0.82, 0.97, s.noise((pitch, course), seed + 1, warp=at_centre))
    s.shade(overburnt, 0.72)

    pits = smoothstep(0.78, 0.95, s.noise(0.006, seed + 2, 2))
    s.shade(pits, 0.80, 0.7)
    s.relief -= pits * 0.0006
    s.relief += (s.noise(0.03, seed + 3, 2) - 0.5) * 0.0005

    mask = _joints(s, pitch, course, stagger, joint)
    s.tint(mask, lin(mortar))
    s.roughen(mask, 0.95)
    s.relief -= mask * 0.004
    s.occlude(mask, 0.55)

    _soot(s, seed + 4, lin(soot), soot_amount)
    return s


def ashlar(slug, description, stone, joint_colour, soot, *, seed, soot_amount=0.25,
           tile=2.40, px=1024, course=0.30, block=0.60, joint=0.008):
    """Coursed sandstone ashlar: per-block tone, bedding planes, pores, fine joints."""
    _check_tiles(tile, course, block)
    _check_even_courses(tile, course)
    s = Surface(slug, description, tile, tile, px, px)
    s.fill(lin(stone), 0.86)

    centre_x, centre_y, stagger = _unit_centres(s, block, course)
    tone = s.noise((block, course), seed, warp=(centre_x - s.x, centre_y - s.y))
    s.base *= (0.93 + 0.14 * tone)[..., None]
    # Sedimentary bedding runs along each block.
    beds = s.noise((0.9, 0.012), seed + 1, 3)
    s.base *= (0.965 + 0.07 * beds)[..., None]
    s.relief += (beds - 0.5) * 0.0002

    pores = smoothstep(0.80, 0.95, s.noise(0.004, seed + 2, 2))
    s.shade(pores, 0.85, 0.7)
    s.relief -= pores * 0.0003
    s.relief += (s.noise(0.05, seed + 3, 2) - 0.5) * 0.0004

    mask = _joints(s, block, course, stagger, joint)
    s.tint(mask, lin(joint_colour), 0.8)
    s.roughen(mask, 0.92, 0.8)
    s.relief -= mask * 0.002
    s.occlude(mask, 0.5)

    _soot(s, seed + 4, lin(soot), soot_amount)
    return s


# -------------------------------------------------------------- paint films

def painted_metal(slug, description, paint, *, seed, rust="#5E3620", bare="#6B6C6E",
                  rust_amount=0.55, chips=20, tile=0.50, px=1024, roughness=0.55, metallic=0.0):
    """Painted or coated steel: rust bloom with its bleed, chips to bare metal, dust."""
    s = Surface(slug, description, tile, tile, px, px)
    s.fill(lin(paint), roughness, metallic)
    s.relief += (s.noise(0.010, seed, 2) - 0.5) * 0.00020
    s.base *= (0.94 + 0.12 * s.noise(0.16, seed + 1, 3))[..., None]

    bloom = smoothstep(0.66, 0.95, s.noise(0.055, seed + 2, 4))
    lifted = (np.zeros_like(s.x), np.full_like(s.y, 0.05))
    above = smoothstep(0.66, 0.95, s.noise(0.055, seed + 2, 4, warp=lifted))
    bleed = above * smoothstep(0.30, 0.80, s.noise((0.035, 0.30), seed + 3, 2))
    rusted = np.clip(bloom + 0.6 * bleed, 0, 1)
    s.tint(rusted, lin(rust), rust_amount)
    s.roughen(rusted, 0.92, 0.9 * min(1.0, rust_amount / 0.55))
    s.relief += bloom * 0.00022 * rust_amount

    chipped = _chips(s, chips, seed + 4) * (1.0 - bloom)
    s.tint(chipped, lin(bare), 0.7)
    s.metalise(chipped, 1.0, 0.6)
    s.roughen(chipped, 0.45, 0.8)
    s.relief -= chipped * 0.00018

    dust = smoothstep(0.5, 0.95, s.noise(0.05, seed + 5, 3))
    s.shade(dust, 1.06, 0.5)
    s.roughen(dust, 0.75, 0.5)
    return s


def painted_timber(slug, description, paint, *, seed, primer="#8A7A62", tile=0.60,
                   px=1024, gloss=0.42, chips=14):
    """Painted joinery: grain telegraphing through the film, brush marks, chipped arrises."""
    s = Surface(slug, description, tile, tile, px, px)
    s.fill(lin(paint), gloss)
    grain = s.noise((0.004, 0.30), seed, 3)
    s.relief += (grain - 0.5) * 0.00025
    s.base *= (0.97 + 0.06 * grain)[..., None]

    brush = s.noise((0.002, 0.08), seed + 1, 2)
    s.roughen(smoothstep(0.4, 0.9, brush), gloss + 0.12, 0.6)
    s.relief += (brush - 0.5) * 0.00008

    dull = smoothstep(0.45, 0.85, s.noise(0.25, seed + 2, 3))
    s.roughen(dull, min(gloss + 0.25, 0.95), 0.7)
    s.shade(dull, 0.94, 0.6)

    chipped = _chips(s, chips, seed + 3)
    s.tint(chipped, lin(primer), 0.8)
    s.roughen(chipped, 0.85, 0.8)
    s.relief -= chipped * 0.00015
    return s


def painted_render(slug, description, colour, dirt, *, seed, dirt_amount=0.30,
                   tile=2.40, px=1024, roughness=0.80):
    """Painted smooth render: float marks, fresher repair patches, run-down dirt."""
    s = Surface(slug, description, tile, tile, px, px)
    s.fill(lin(colour), roughness)
    s.base *= (0.95 + 0.10 * s.noise(0.8, seed, 3))[..., None]
    s.relief += (s.noise(0.003, seed + 1, 2) - 0.5) * 0.0003
    s.relief += (s.noise(0.12, seed + 2, 2) - 0.5) * 0.0006

    patches = smoothstep(0.72, 0.90, s.noise(0.5, seed + 3, 2))
    s.shade(patches, 1.05, 0.8)
    s.roughen(patches, max(roughness - 0.10, 0.3), 0.8)

    _soot(s, seed + 4, lin(dirt), dirt_amount)
    return s


# ------------------------------------------------------------------ others

def timber(slug, description, light, dark, *, seed, tile=(0.60, 1.20), px=(512, 1024),
           finish=0.55):
    """Sealed or oiled timber, grain running up the tile."""
    s = Surface(slug, description, tile[0], tile[1], px[0], px[1])
    s.fill(lin(light), finish)
    wobble = (0.02 * (s.noise(0.3, seed) - 0.5), np.zeros_like(s.y))
    figure = s.noise((0.012, 0.9), seed + 1, 3, warp=wobble)
    rings = (0.5 + 0.5 * np.sin(figure * 40.0)).astype(F)
    s.tint(rings, lin(dark), 0.55)
    s.relief += (rings - 0.5) * 0.00012

    pores = smoothstep(0.75, 0.95, s.noise((0.0015, 0.02), seed + 2, 2))
    s.shade(pores, 0.85, 0.6)
    s.relief -= pores * 0.0001
    return s


def concrete(slug, description, colour, *, seed, stain="#4A4A46", stain_amount=0.25,
             tile=2.00, px=1024, roughness=0.88):
    """Cast concrete: aggregate mottle, blowholes, water staining."""
    s = Surface(slug, description, tile, tile, px, px)
    s.fill(lin(colour), roughness)
    s.base *= (0.90 + 0.20 * s.noise(0.35, seed, 4))[..., None]
    fine = s.noise(0.01, seed + 1, 2)
    s.base *= (0.96 + 0.08 * fine)[..., None]
    s.relief += (fine - 0.5) * 0.0004

    blowholes = smoothstep(0.82, 0.96, s.noise(0.005, seed + 2))
    s.shade(blowholes, 0.6, 0.8)
    s.relief -= blowholes * 0.0008
    s.occlude(blowholes, 0.7)

    stains = smoothstep(0.55, 0.90, s.noise((0.2, 0.8), seed + 3, 3))
    s.tint(stains, lin(stain), stain_amount)
    s.roughen(stains, 0.95, 0.4)
    return s


def plaster(slug, description, colour, *, seed, tile=2.00, px=512, roughness=0.90):
    """Interior plaster/emulsion: soft trowel variation only."""
    s = Surface(slug, description, tile, tile, px, px)
    s.fill(lin(colour), roughness)
    s.base *= (0.96 + 0.08 * s.noise(0.4, seed, 3))[..., None]
    s.relief += (s.noise(0.02, seed + 1, 2) - 0.5) * 0.0002
    return s


def glazed_tile(slug, description, glaze, grout, *, seed, tile_size=(0.152, 0.076),
                tile=0.912, px=1024, spread=0.10, craze=True):
    """Glazed ceramic tile: per-tile tone, pillowed faces, recessed grout, crazing."""
    tile_w, tile_h = tile_size
    _check_tiles(tile, tile_w, tile_h)
    s = Surface(slug, description, tile, tile, px, px)
    s.fill(lin(glaze), 0.12)

    centre_x = (np.floor(s.x / tile_w) + 0.5) * tile_w
    centre_y = (np.floor(s.y / tile_h) + 0.5) * tile_h
    tone = s.noise(tile_size, seed, warp=(centre_x - s.x, centre_y - s.y))
    s.base *= (1.0 - spread * 0.5 + spread * tone)[..., None]

    # 0 at the grout line, 1 at the tile centre.
    inset = np.minimum(s.repeat(s.x, tile_w) / (tile_w * 0.5),
                       s.repeat(s.y, tile_h) / (tile_h * 0.5))
    s.relief += smoothstep(0.0, 0.25, inset) * 0.0015
    s.shade(1.0 - smoothstep(0.0, 0.2, inset), 1.10, 0.5)  # thin glaze on the roll
    s.roughen(smoothstep(0.5, 0.9, s.noise(0.02, seed + 1, 2)), 0.20, 0.5)

    lines = smoothstep(0.004, 0.002, np.minimum(s.repeat(s.x, tile_w), s.repeat(s.y, tile_h)))
    s.tint(lines, lin(grout))
    s.roughen(lines, 0.95)
    s.relief -= lines * 0.002
    s.occlude(lines, 0.6)

    if craze:
        cracks = s.ridges(0.03, seed + 2, width=0.03)
        s.shade(cracks, 0.85, 0.5)
    return s


# ------------------------------------------------------------ palette + run

def load_palette(path, required):
    """Albedo hex per key from a building's palette.json (see measurePatch.py)."""
    path = Path(path)
    data = json.loads(path.read_text()) if path.exists() else {}
    missing = [key for key in required if key not in data]
    if missing:
        raise SystemExit(f"{path} is missing measured keys: {', '.join(missing)}")
    return {key: entry["albedo"] for key, entry in data.items()}


def run_texture_pass(asset, texture_dir, render_dir, palette_path, builders, argv):
    """Write every surface, refuse any that does not tile, and record validation.json.

    `builders` is a sequence of no-argument callables returning a Surface.
    Pass `--no-render` in argv to skip the review renders.
    """
    from vinylExchangeTextures import contact_sheet, review_render, write_surface

    render = "--no-render" not in argv
    records, frames = [], []
    for build in builders:
        surface = build()
        record = write_surface(surface, texture_dir=texture_dir)
        seams = [f"{axis}: wrap {step['wrap']} vs typical {step['typical']}"
                 for axis, step in record["seam_levels"].items()
                 if step["wrap"] > max(3.0, step["typical"] * 3.0)]
        if seams:
            raise RuntimeError(f"{surface.slug} does not tile: " + "; ".join(seams))
        print(f"  {surface.slug:28s} {surface.w_px}x{surface.h_px}  "
              f"{record['mm_per_texel'][0]:.3f} mm/texel", flush=True)
        if render:
            frames.append(review_render(surface, texture_dir=texture_dir, render_dir=render_dir))
        records.append(record)
    if render:
        contact_sheet(frames, render_dir=render_dir)

    validation = {
        "asset": asset,
        "pass": "surface materials (commonSurfaces)",
        "convention": {
            "maps": "<slug>-{basecolor,orm,normal}.png",
            "orm": "R occlusion, G roughness, B metallic (glTF)",
            "normal": "OpenGL tangent space (+Y up)",
            "unit": "1 Blender unit = 1 m; coverage_m is what one tile spans",
        },
        "measured_reference_patches": json.loads(Path(palette_path).read_text()),
        "materials": records,
    }
    (Path(texture_dir) / "validation.json").write_text(json.dumps(validation, indent=2) + "\n")
    print(f"wrote {len(records)} materials to {texture_dir}", flush=True)
    return records
```

- [ ] **Step 4: Run the test and confirm it passes**

Run: `/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python tests/blender/test_common_surfaces.py`
Expected: exit 0 and `commonSurfaces: all builders tile, stay in range and hold their palette`. If a builder's mean drifts more than 40 levels, lower that builder's overlay amounts rather than widening the tolerance.

- [ ] **Step 5: Commit**

```bash
git add blender/scripts/commonSurfaces.py tests/blender/test_common_surfaces.py
git commit -m "Add shared parameterised surface builders for building texture passes"
git push
```

---

### Task 3: Reference palette measurement tool

**Files:**
- Create: `blender/scripts/measurePatch.py`
- Test: `tests/blender/test_measure_patch.py`

**Interfaces:**
- Produces: `patch_median(photo: Path, box: tuple[int,int,int,int]) -> np.ndarray` (sRGB 0–1), `record_sample(palette_path, key, photo, box, light) -> str` (returns the new albedo hex), and `palette.json` entries `{key: {"albedo": "#RRGGBB", "samples": [{"photo", "box", "light", "srgb"}]}}`, which `commonSurfaces.load_palette` reads.

- [ ] **Step 1: Write the failing test**

```python
"""Run:
    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python-exit-code 1 --python tests/blender/test_measure_patch.py
"""
import json
import sys
import tempfile
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / "blender" / "scripts"))

from measurePatch import patch_median, record_sample  # noqa: E402


def solid_png(path, top, bottom, size=(40, 20)):
    """Top half one colour, bottom half another, as an 8-bit PNG."""
    width, height = size
    image = bpy.data.images.new("t", width, height, alpha=True)
    grid = np.ones((height, width, 4), np.float32)
    grid[: height // 2, :, :3] = np.array(bottom) / 255.0   # Blender rows are bottom-up
    grid[height // 2:, :, :3] = np.array(top) / 255.0
    image.pixels.foreach_set(grid.ravel())
    image.filepath_raw = str(path)
    image.file_format = "PNG"
    image.save()


def main():
    work = Path(tempfile.mkdtemp())
    photo = work / "p.png"
    solid_png(photo, top=(128, 64, 32), bottom=(10, 20, 30))

    top = np.round(patch_median(photo, (0, 0, 40, 10)) * 255)
    assert top.tolist() == [128, 64, 32], top          # y counts from the top
    bottom = np.round(patch_median(photo, (0, 10, 40, 20)) * 255)
    assert bottom.tolist() == [10, 20, 30], bottom

    palette = work / "palette.json"
    assert record_sample(palette, "brick face", photo, (0, 0, 40, 10), "overcast") == "#804020"
    # A sunlit sample is scaled by 0.85, and the albedo is the mean of both samples:
    # (128+108.8)/2=118.4 -> 0x76, (64+54.4)/2=59.2 -> 0x3B, (32+27.2)/2=29.6 -> 0x1E.
    albedo = record_sample(palette, "brick face", photo, (0, 0, 40, 10), "sunlit")
    assert albedo == "#763B1E", albedo
    data = json.loads(palette.read_text())
    assert len(data["brick face"]["samples"]) == 2
    print("measurePatch: medians, orientation and albedo averaging are correct")


main()
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python tests/blender/test_measure_patch.py`
Expected: exit 1, `ModuleNotFoundError: No module named 'measurePatch'`.

- [ ] **Step 3: Write `blender/scripts/measurePatch.py`**

```python
"""Measure the median colour of a rectangle in a reference photograph.

The building texture passes anchor every albedo on a patch median sampled from
the photographs in `references/` (see MEASURED in vinylExchangeTextures.py).
This records those samples in the building's `palette.json` and derives the
authored albedo with one explicit de-lighting rule: a sunlit sample is scaled
by 0.85, a shaded one by 1.15, an overcast one is taken as-is, and the albedo
is the mean of all samples for that key.  Only the median colour is stored;
no pixels from the photograph reach any output.

Coordinates are pixels from the photograph's top-left, as an image viewer
shows them.  Blender cannot read HEIC or AVIF; convert those first with
`sips -s format jpeg <in> --out <scratch>.jpg`.  Blender ignores EXIF
rotation, so check the photo's orientation in the printed size.

Run:

    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python blender/scripts/measurePatch.py -- \
        <palette.json> "<key>" <photo> <x0> <y0> <x1> <y1> <sunlit|shaded|overcast>
"""

import json
import sys
from pathlib import Path

import bpy
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LIGHT_SCALE = {"overcast": 1.0, "sunlit": 0.85, "shaded": 1.15}


def to_hex(rgb):
    return "#" + "".join(f"{int(round(float(v) * 255)):02X}" for v in np.clip(rgb, 0, 1))


def from_hex(value):
    value = value.lstrip("#")
    return np.array([int(value[i:i + 2], 16) for i in (0, 2, 4)], float) / 255.0


def patch_median(photo, box):
    """Median sRGB (0-1) of box = (x0, y0, x1, y1), y from the top."""
    image = bpy.data.images.load(str(photo), check_existing=False)
    width, height = image.size
    x0, y0, x1, y1 = box
    if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
        raise SystemExit(f"box {box} lies outside {Path(photo).name} ({width}x{height})")
    pixels = np.empty(width * height * 4, np.float32)
    image.pixels.foreach_get(pixels)
    bpy.data.images.remove(image)
    grid = pixels.reshape(height, width, 4)[::-1]  # top row first
    return np.median(grid[y0:y1, x0:x1, :3].reshape(-1, 3), axis=0)


def record_sample(palette_path, key, photo, box, light):
    if light not in LIGHT_SCALE:
        raise SystemExit(f"light must be one of {', '.join(LIGHT_SCALE)}")
    palette_path, photo = Path(palette_path), Path(photo)
    data = json.loads(palette_path.read_text()) if palette_path.exists() else {}
    srgb = patch_median(photo, box)
    try:
        shown = str(photo.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        shown = photo.name
    entry = data.setdefault(key, {"samples": []})
    entry["samples"].append({"photo": shown, "box": list(box), "light": light,
                             "srgb": to_hex(srgb)})
    corrected = [np.clip(from_hex(s["srgb"]) * LIGHT_SCALE[s["light"]], 0, 1)
                 for s in entry["samples"]]
    entry["albedo"] = to_hex(np.mean(corrected, axis=0))
    palette_path.parent.mkdir(parents=True, exist_ok=True)
    palette_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    return entry["albedo"]


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(argv) != 8:
        raise SystemExit(__doc__)
    palette, key, photo = argv[0], argv[1], argv[2]
    box = tuple(int(v) for v in argv[3:7])
    albedo = record_sample(palette, key, photo, box, argv[7])
    print(f"{key}: albedo {albedo}", flush=True)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the test and confirm it passes**

Run: the Step 2 command. Expected: exit 0 and `measurePatch: medians, orientation and albedo averaging are correct`.

- [ ] **Step 5: Commit**

```bash
git add blender/scripts/measurePatch.py tests/blender/test_measure_patch.py
git commit -m "Add a reference-photo palette measurement tool"
git push
```

---

### Task 4: Runtime texture exporter

**Files:**
- Create: `blender/scripts/texturedRuntimeExport.py`
- Create: `blender/scripts/exportTexturedBuilding.py`
- Test: `tests/blender/test_textured_runtime_export.py`

**Interfaces:**
- Consumes: `surfaceWeathering.build_pbr_material`, `load_image`; `validation.json` written by `commonSurfaces.run_texture_pass`; `config/building-textures.json` from Task 1.
- Produces: `texture_glb(public_glb, *, prefix, texture_dir, placeholder_map, expected_surfaces, stash_dir=STASH_DIR) -> dict[str, int]`, `apply_surfaces(meshes, *, prefix, texture_dir, placeholder_map) -> dict[str, int]`, `inspect_glb(path, prefix, expected_surfaces, reference=None)`, `read_glb_json(path) -> dict`. CLI: `exportTexturedBuilding.py -- <building>`.

- [ ] **Step 1: Write the failing test**

```python
"""Run:
    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python-exit-code 1 --python tests/blender/test_textured_runtime_export.py
"""
import json
import sys
import tempfile
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / "blender" / "scripts"))

from commonSurfaces import plaster  # noqa: E402
from texturedRuntimeExport import read_glb_json, texture_glb  # noqa: E402
from vinylExchangeTextures import write_surface  # noqa: E402

PLACEHOLDERS = {"MAT_T_A_PLACEHOLDER": "t-a", "MAT_T_B_PLACEHOLDER": "t-b"}


def write_textures(directory):
    records = [write_surface(plaster(slug, "t", "#CCCCCC", seed=i, tile=tile, px=32),
                             texture_dir=directory)
               for i, (slug, tile) in enumerate((("t-a", 1.0), ("t-b", 0.5)))]
    (directory / "validation.json").write_text(json.dumps({"materials": records}))


def write_untextured_glb(path):
    bpy.ops.wm.read_homefile(use_empty=True)
    bpy.ops.mesh.primitive_cube_add(size=2.0)
    cube = bpy.context.active_object
    cube.name = "T_Cube"
    for name in (*PLACEHOLDERS, "MAT_T_Glass_PLACEHOLDER"):
        cube.data.materials.append(bpy.data.materials.new(name))
    for polygon in cube.data.polygons:
        polygon.material_index = polygon.index % 3
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=False)


def uv_span(obj, polygon):
    uv = obj.data.uv_layers[0].data
    us = [uv[i].uv[0] for i in polygon.loop_indices]
    vs = [uv[i].uv[1] for i in polygon.loop_indices]
    return max(max(us) - min(us), max(vs) - min(vs))


def run(public, textures, stash):
    return texture_glb(public, prefix="MAT_T_Surface_", texture_dir=textures,
                       placeholder_map=PLACEHOLDERS, expected_surfaces=2, stash_dir=stash)


def main():
    work = Path(tempfile.mkdtemp())
    textures, stash, public = work / "tex", work / "stash", work / "public" / "t.glb"
    textures.mkdir()
    public.parent.mkdir()
    write_textures(textures)
    write_untextured_glb(public)

    counts = run(public, textures, stash)
    assert counts == {"t-a": 1, "t-b": 1}, counts
    assert (stash / "t.glb").exists(), "untextured source was not stashed"

    cube = bpy.data.objects["T_Cube"]
    expected_span = {0: 2.0, 1: 4.0}          # 2 m face / 1.0 m tile, / 0.5 m tile
    for polygon in cube.data.polygons:
        want = expected_span.get(polygon.material_index)
        if want is not None:
            assert abs(uv_span(cube, polygon) - want) < 1e-4, (polygon.index, uv_span(cube, polygon))

    names = [m["name"] for m in read_glb_json(public)["materials"]]
    assert "MAT_T_Glass_PLACEHOLDER" in names and "MAT_T_Surface_t-a" in names, names

    # Idempotent: a second run reads the stash, not the textured output.
    assert run(public, textures, stash) == {"t-a": 1, "t-b": 1}

    # With the stash gone and the output already textured, it must refuse.
    (stash / "t.glb").unlink()
    try:
        run(public, textures, stash)
        raise AssertionError("re-texturing a textured GLB without a stash was allowed")
    except RuntimeError:
        pass
    print("texturedRuntimeExport: stash, per-slot UVs, export and guards are correct")


main()
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python tests/blender/test_textured_runtime_export.py`
Expected: exit 1, `ModuleNotFoundError: No module named 'texturedRuntimeExport'`.

- [ ] **Step 3: Write `blender/scripts/texturedRuntimeExport.py`**

```python
"""Runtime material pass for building GLBs, applied to the GLB that ships.

Vinyl Exchange and Nice Things each re-open their source .blend and re-select
their export set; every create script selects differently (runtime duplicate
collections, NON_EXPORT filters, per-asset collections).  This pass works on
the shipped GLB instead, so the geometry, node names and extras are exactly
what the game loads today:

1. If the public GLB has no `<prefix>` materials it is the fresh untextured
   export, and is copied to `blender/source/runtime-untextured/`.  Otherwise
   the stash must already exist (re-run the building's create script to
   refresh it after a geometry change).
2. The stash is imported into an empty scene; placeholder slots named in the
   contract are swapped for textured materials built from the maps and
   `validation.json` of the building's texture pass.
3. Faces are box-projected in metres per material slot, so one mesh may carry
   several surfaces at different tile sizes (the Vinyl Exchange exporter could
   not).
4. The result is exported over the public GLB and inspected: exact surface
   count, UV0 on every textured primitive, and unchanged node names.
"""

import json
import shutil
import struct
import sys
from pathlib import Path

import bpy
from mathutils import Vector

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STASH_DIR = PROJECT_ROOT / "blender" / "source" / "runtime-untextured"

sys.path.append(str(PROJECT_ROOT / "blender" / "scripts"))
from surfaceWeathering import build_pbr_material, load_image  # noqa: E402


def read_glb_json(path):
    with Path(path).open("rb") as handle:
        magic, version, _ = struct.unpack("<4sII", handle.read(12))
        if magic != b"glTF" or version != 2:
            raise RuntimeError(f"{path} is not a glTF 2 GLB")
        length, kind = struct.unpack("<II", handle.read(8))
        if kind != 0x4E4F534A:
            raise RuntimeError(f"{path} has no JSON chunk")
        return json.loads(handle.read(length))


def has_surfaces(path, prefix):
    return any(m.get("name", "").startswith(prefix)
               for m in read_glb_json(path).get("materials", []))


def load_surface_specs(texture_dir):
    data = json.loads((Path(texture_dir) / "validation.json").read_text())
    return {m["slug"]: {"coverage": tuple(m["coverage_m"]), "normal": m["normal_strength"]}
            for m in data["materials"]}


def runtime_material(prefix, slug, texture_dir, spec):
    name = f"{prefix}{slug}"
    material = bpy.data.materials.get(name)
    if material is not None:
        return material
    images = {kind: load_image(Path(texture_dir) / f"{slug}-{kind}.png",
                               non_color=kind != "basecolor")
              for kind in ("basecolor", "orm", "normal")}
    material = bpy.data.materials.new(name)
    build_pbr_material(material, images["basecolor"], images["orm"], images["normal"],
                       normal_strength=spec["normal"])
    return material


def metric_uv(point, normal, coverage):
    """World-metre box projection; world Z is up on vertical faces."""
    width, height = coverage
    if abs(normal.z) < 0.707:
        tangent = Vector((normal.y, -normal.x, 0.0)).normalized()
        return ((point.x * tangent.x + point.y * tangent.y) / width, point.z / height)
    return (point.x / width, point.y / height)


def add_metric_uvs_per_slot(obj, slot_coverage):
    """UV-map only the faces whose material slot has a surface; others keep theirs."""
    mesh = obj.data
    uv = mesh.uv_layers[0] if mesh.uv_layers else mesh.uv_layers.new(name="UVMap")
    normal_matrix = obj.matrix_world.to_3x3().inverted().transposed()
    for polygon in mesh.polygons:
        coverage = slot_coverage.get(polygon.material_index)
        if coverage is None:
            continue
        normal = (normal_matrix @ polygon.normal).normalized()
        for loop_index in polygon.loop_indices:
            point = obj.matrix_world @ mesh.vertices[mesh.loops[loop_index].vertex_index].co
            uv.data[loop_index].uv = metric_uv(point, normal, coverage)
    mesh.update()


def apply_surfaces(meshes, *, prefix, texture_dir, placeholder_map):
    specs = load_surface_specs(texture_dir)
    unknown = sorted(set(placeholder_map.values()) - specs.keys())
    if unknown:
        raise RuntimeError(f"No authored maps in {texture_dir} for: {', '.join(unknown)}")
    counts = {}
    for obj in meshes:
        if obj.data.users > 1:
            obj.data = obj.data.copy()  # UVs are world-space; instances need their own
        slot_coverage = {}
        for index, material in enumerate(obj.data.materials):
            slug = placeholder_map.get(material.name) if material else None
            if slug is None:
                continue
            obj.data.materials[index] = runtime_material(prefix, slug, texture_dir, specs[slug])
            slot_coverage[index] = specs[slug]["coverage"]
            counts[slug] = counts.get(slug, 0) + 1
        if slot_coverage:
            add_metric_uvs_per_slot(obj, slot_coverage)
    return counts


def inspect_glb(path, prefix, expected_surfaces, reference=None):
    data = read_glb_json(path)
    names = [m.get("name", "") for m in data.get("materials", [])]
    surfaces = {i for i, name in enumerate(names) if name.startswith(prefix)}
    no_uv = [p for mesh in data.get("meshes", []) for p in mesh["primitives"]
             if p.get("material") in surfaces and "TEXCOORD_0" not in p["attributes"]]
    if len(surfaces) != expected_surfaces or no_uv:
        raise RuntimeError(f"{Path(path).name}: {len(surfaces)} surfaces "
                           f"(expected {expected_surfaces}), {len(no_uv)} textured primitives without UV0")
    if reference is not None:
        before = sorted(n.get("name", "") for n in read_glb_json(reference).get("nodes", []))
        after = sorted(n.get("name", "") for n in data.get("nodes", []))
        if before != after:
            raise RuntimeError(f"{Path(path).name}: node names changed; lost "
                               f"{sorted(set(before) - set(after))[:10]}, gained "
                               f"{sorted(set(after) - set(before))[:10]}")
    print(f"{Path(path).name}: {len(surfaces)} surface materials, "
          f"{len(data.get('images', []))} maps, {Path(path).stat().st_size / 1e6:.2f} MB", flush=True)


def texture_glb(public_glb, *, prefix, texture_dir, placeholder_map, expected_surfaces,
                stash_dir=STASH_DIR):
    public_glb = Path(public_glb)
    stash = Path(stash_dir) / public_glb.name
    if not has_surfaces(public_glb, prefix):
        stash.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(public_glb, stash)
        print(f"Stashed untextured source {stash.name}", flush=True)
    elif not stash.exists():
        raise RuntimeError(f"{public_glb.name} is already textured and has no untextured "
                           f"stash in {stash_dir}; re-run its create script first")

    bpy.ops.wm.read_homefile(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(stash))
    objects = list(bpy.context.scene.objects)
    meshes = [obj for obj in objects if obj.type == "MESH"]
    counts = apply_surfaces(meshes, prefix=prefix, texture_dir=texture_dir,
                            placeholder_map=placeholder_map)

    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(public_glb), export_format="GLB",
                              use_selection=True, export_apply=True, export_yup=True,
                              export_cameras=False, export_lights=False, export_extras=True)
    inspect_glb(public_glb, prefix, expected_surfaces, reference=stash)
    return counts
```

- [ ] **Step 4: Write `blender/scripts/exportTexturedBuilding.py`**

```python
"""Texture every GLB of one building from config/building-textures.json.

Run after the building's texture pass (`<building>Textures.py`):

    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python-exit-code 1 --python blender/scripts/exportTexturedBuilding.py -- <building>
"""

import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

from texturedRuntimeExport import PROJECT_ROOT, texture_glb  # noqa: E402


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(argv) != 1:
        raise SystemExit("usage: exportTexturedBuilding.py -- <building>")
    contract = json.loads((PROJECT_ROOT / "config" / "building-textures.json").read_text())
    entries = [e for e in contract["buildings"] if e["building"] == argv[0]]
    if not entries:
        raise SystemExit(f"No building-textures.json entry for {argv[0]}")
    for entry in entries:
        if "legacyExporter" in entry:
            raise SystemExit(f"{entry['glb']} is exported by {entry['legacyExporter']}")
        counts = texture_glb(PROJECT_ROOT / "public" / entry["glb"],
                             prefix=entry["surfacePrefix"],
                             texture_dir=PROJECT_ROOT / entry["textureDir"],
                             placeholder_map=entry["placeholders"],
                             expected_surfaces=entry["expectedSurfaces"])
        print(f"{entry['glb']}: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())),
              flush=True)


main()
```

- [ ] **Step 5: Run the test and confirm it passes**

Run: the Step 1 command. Expected: exit 0 and `texturedRuntimeExport: stash, per-slot UVs, export and guards are correct`.

- [ ] **Step 6: Commit**

```bash
git add blender/scripts/texturedRuntimeExport.py blender/scripts/exportTexturedBuilding.py tests/blender/test_textured_runtime_export.py
git commit -m "Add a runtime texture exporter that works on the shipped building GLB"
git push
```

---

## Per-building tasks

Tasks 5–15 have the same shape. Each spells out its own values, so they can run in any order after Task 4, except that Task 5 creates `src/world/buildingMaterials.ts`, which later tasks import. For each building:

- **Measure.** Pick a flat, evenly lit rectangle for every palette key in the building's photos: view the photo, note pixel coordinates from the top-left, and run `measurePatch.py`. Take at least one sample per key, and two in different light where the photos allow.
- **Look.** Open `renders/<building>-textures/00-contact-sheet.png` next to the reference photos before exporting. If a surface reads wrong in hue or value, re-measure; do not hand-tune hex values.
- **In-game check.** Run `preview_start` with `name: "zealot-dev"`, walk to the building, and take a screenshot. Check that surfaces are textured, the tile scale reads right (roughly 13 brick courses per metre), glass is still transparent, and the console shows no `[World] Failed to load` for this GLB.

### Task 5: Come Through Lab (and the shared runtime helper)

**Files:**
- Create: `src/world/buildingMaterials.ts`
- Create: `blender/scripts/comeThroughLabTextures.py`
- Create: `blender/source/textures/come-through-lab/` (palette, maps, validation)
- Create: `blender/source/runtime-untextured/{come_through_lab,ctl_dropbox,ctl_dropoff_props}.glb`
- Create: `renders/come-through-lab-textures/`
- Modify: `config/building-textures.json`, `src/world/createWorld.ts` (`applyComeThroughLabModelPolicy`, the three `loadModel('assets/models/…?v=geometry-20260912')` calls)
- Modify (re-exported): `public/assets/models/come_through_lab.glb`, `ctl_dropbox.glb`, `ctl_dropoff_props.glb`

**Interfaces:**
- Produces: `profileAuthoredMaps(material: MeshStandardMaterial): void`, exported from `src/world/buildingMaterials.ts`, used by Tasks 6–15.

- [ ] **Step 1: Add the contract entries (failing)**

Append to `buildings` in `config/building-textures.json`:

```json
{
  "building": "come-through-lab",
  "glb": "assets/models/come_through_lab.glb",
  "surfacePrefix": "MAT_CTL_Surface_",
  "textureDir": "blender/source/textures/come-through-lab",
  "placeholders": {
    "MAT_CTL_Brick_PLACEHOLDER": "ctl-brick",
    "MAT_CTL_ArchBrick_PLACEHOLDER": "ctl-arch-brick",
    "MAT_CTL_Stone_PLACEHOLDER": "ctl-stone",
    "MAT_CTL_WindowFrame_PLACEHOLDER": "ctl-frame-paint",
    "MAT_CTL_Wood_PLACEHOLDER": "ctl-door-timber",
    "MAT_CTL_WoodDark_PLACEHOLDER": "ctl-door-timber-dark",
    "MAT_CTL_Metal_PLACEHOLDER": "ctl-metal-black",
    "MAT_CTL_DropBox_PLACEHOLDER": "ctl-dropbox-paint"
  },
  "untexturedAllowed": ["MAT_CTL_Glass_PLACEHOLDER", "MAT_CTL_Paper_PLACEHOLDER"],
  "expectedSurfaces": 7,
  "maxBytes": 5000000
},
{
  "building": "come-through-lab",
  "glb": "assets/models/ctl_dropbox.glb",
  "surfacePrefix": "MAT_CTL_Surface_",
  "textureDir": "blender/source/textures/come-through-lab",
  "placeholders": {
    "MAT_CTL_Metal_PLACEHOLDER": "ctl-metal-black",
    "MAT_CTL_DropBox_PLACEHOLDER": "ctl-dropbox-paint"
  },
  "untexturedAllowed": [],
  "expectedSurfaces": 2,
  "maxBytes": 5000000
},
{
  "building": "come-through-lab",
  "glb": "assets/models/ctl_dropoff_props.glb",
  "surfacePrefix": "MAT_CTL_Surface_",
  "textureDir": "blender/source/textures/come-through-lab",
  "placeholders": {
    "MAT_CTL_WindowFrame_PLACEHOLDER": "ctl-frame-paint",
    "MAT_CTL_Wood_PLACEHOLDER": "ctl-door-timber",
    "MAT_CTL_WoodDark_PLACEHOLDER": "ctl-door-timber-dark",
    "MAT_CTL_Metal_PLACEHOLDER": "ctl-metal-black"
  },
  "untexturedAllowed": ["MAT_CTL_Glass_PLACEHOLDER", "MAT_CTL_Paper_PLACEHOLDER"],
  "expectedSurfaces": 4,
  "maxBytes": 5000000
}
```

Run `npm test`. Expected: FAIL on all three CTL entries with `surface material count` (actual 0).

- [ ] **Step 2: Measure the palette**

Photos: `references/architecture/buildings/come-through-lab/` (`ct.jpg`, `hgfcx.jpg`, `kjh.jpg`, `unnamed.jpg`, the four `Screenshot 2026-09-11 …png`). For each key, run:

```bash
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python blender/scripts/measurePatch.py -- blender/source/textures/come-through-lab/palette.json "brick face" "references/architecture/buildings/come-through-lab/ct.jpg" 410 220 470 260 overcast
```

Keys (all required): `brick face`, `brick mortar`, `brick soot`, `arch brick face`, `stone`, `stone joint`, `frame paint`, `door timber light`, `door timber dark`, `dark timber light`, `dark timber dark`, `black metal`, `dropbox paint`. The coordinates above are illustrative. Pick real boxes for each key from the photo.

- [ ] **Step 3: Write `blender/scripts/comeThroughLabTextures.py`**

```python
"""Surface materials for Come Through Lab (84 Silk Street), its drop box and drop-off props.

Palette measured from references/architecture/buildings/come-through-lab/ into
palette.json (measurePatch.py).  Builders from commonSurfaces.py.

Run:

    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python-exit-code 1 --python blender/scripts/comeThroughLabTextures.py

Add `-- --no-render` to write the maps without the review renders.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

from commonSurfaces import (  # noqa: E402
    ashlar, brick, load_palette, painted_metal, painted_timber, run_texture_pass, timber,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEXTURE_DIR = PROJECT_ROOT / "blender" / "source" / "textures" / "come-through-lab"
RENDER_DIR = PROJECT_ROOT / "renders" / "come-through-lab-textures"
PALETTE_PATH = TEXTURE_DIR / "palette.json"
P = load_palette(PALETTE_PATH, (
    "brick face", "brick mortar", "brick soot", "arch brick face", "stone", "stone joint",
    "frame paint", "door timber light", "door timber dark", "dark timber light",
    "dark timber dark", "black metal", "dropbox paint",
))

BUILDERS = (
    lambda: brick("ctl-brick", "Historic frontage: red stretcher-bond brick, sooted",
                  P["brick face"], P["brick mortar"], P["brick soot"], seed=6101),
    lambda: brick("ctl-arch-brick", "Window and door arches: darker, heavier soot",
                  P["arch brick face"], P["brick mortar"], P["brick soot"],
                  seed=6111, soot_amount=0.45, tile=0.90),
    lambda: ashlar("ctl-stone", "Sills, surround and address plaque stone",
                   P["stone"], P["stone joint"], P["brick soot"], seed=6121, tile=1.20),
    lambda: painted_timber("ctl-frame-paint", "Sash and window frames",
                           P["frame paint"], seed=6131, tile=0.30, px=512),
    lambda: timber("ctl-door-timber", "Entrance door timber",
                   P["door timber light"], P["door timber dark"], seed=6141),
    lambda: timber("ctl-door-timber-dark", "Dark stained door timber",
                   P["dark timber light"], P["dark timber dark"], seed=6151),
    lambda: painted_metal("ctl-metal-black", "Grilles, fixtures and black ironmongery",
                          P["black metal"], seed=6161, px=512),
    lambda: painted_metal("ctl-dropbox-paint", "24-hour film drop box: painted steel",
                          P["dropbox paint"], seed=6171, rust_amount=0.35),
)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    run_texture_pass("come-through-lab", TEXTURE_DIR, RENDER_DIR, PALETTE_PATH, BUILDERS, argv)
```

- [ ] **Step 4: Run the texture pass and review**

Run: `/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python blender/scripts/comeThroughLabTextures.py`
Expected: 8 lines of `<slug> 1024x1024 …`, then `wrote 8 materials to …/come-through-lab`. Compare `renders/come-through-lab-textures/00-contact-sheet.png` with the photos.

- [ ] **Step 5: Export**

Run: `/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python blender/scripts/exportTexturedBuilding.py -- come-through-lab`
Expected: three `Stashed untextured source …` lines and three inspect lines (`come_through_lab.glb: 7 surface materials …`, `ctl_dropbox.glb: 2 …`, `ctl_dropoff_props.glb: 4 …`).

- [ ] **Step 6: Create the runtime helper**

`src/world/buildingMaterials.ts`:

```ts
import type { MeshStandardMaterial } from 'three';
import { applyTextureProfile } from '../rendering/visualStyle';

/**
 * Building GLBs textured by blender/scripts/exportTexturedBuilding.py carry
 * Blender-authored base colour, ORM and normal maps. Runtime keeps every map
 * and applies the shared photographic filtering profile to each of them.
 */
export function profileAuthoredMaps(material: MeshStandardMaterial): void {
  for (const texture of [
    material.map,
    material.roughnessMap,
    material.metalnessMap,
    material.aoMap,
    material.normalMap,
  ]) {
    if (texture) {
      applyTextureProfile(texture, 'PHOTO_ENVIRONMENT');
    }
  }
}
```

- [ ] **Step 7: Stop the policy stripping the maps; bump cache-busters**

In `src/world/createWorld.ts`:
- Add `import { profileAuthoredMaps } from './buildingMaterials';` beside the other `./` imports.
- In `function applyComeThroughLabModelPolicy`, replace `material.map = null;` with `profileAuthoredMaps(material);`.
- Replace `?v=geometry-20260912` with `?v=textured-YYYYMMDD` in the three `come_through_lab.glb` / `ctl_dropbox.glb` / `ctl_dropoff_props.glb` `loadModel` calls.

- [ ] **Step 8: Verify**

Run: `npm test && npm run build`
Expected: PASS, including the three CTL contract tests. Then do the in-game check (see the shared notes before Task 5). Also confirm the drop box still triggers its interaction prompt, since `CTL_DropBox_InteractAnchor` must survive and `inspect_glb` already asserts node names.

- [ ] **Step 9: Commit**

```bash
git add config/building-textures.json src/world/buildingMaterials.ts src/world/createWorld.ts blender/scripts/comeThroughLabTextures.py blender/source/textures/come-through-lab blender/source/runtime-untextured renders/come-through-lab-textures public/assets/models/come_through_lab.glb public/assets/models/ctl_dropbox.glb public/assets/models/ctl_dropoff_props.glb
git commit -m "Texture Come Through Lab, its drop box and drop-off props"
git push
```

### Task 6: The Hive

**Files:**
- Create: `blender/scripts/theHiveTextures.py`, `blender/source/textures/the-hive/`, `renders/the-hive-textures/`, `blender/source/runtime-untextured/the_hive.glb`
- Modify: `config/building-textures.json`, `src/world/createWorld.ts` (`applyTheHiveModelPolicy`, `the_hive.glb?v=geometry-20260911`), `public/assets/models/the_hive.glb`

**Interfaces:**
- Consumes: `profileAuthoredMaps` (Task 5), the builders (Task 2), and the exporter (Task 4).

- [ ] **Step 1: Contract entry (failing)**

```json
{
  "building": "the-hive",
  "glb": "assets/models/the_hive.glb",
  "surfacePrefix": "MAT_HIVE_Surface_",
  "textureDir": "blender/source/textures/the-hive",
  "placeholders": {
    "MAT_DarkBrick_PLACEHOLDER": "hive-brick-black",
    "MAT_PaleBrick_PLACEHOLDER": "hive-brick-pale",
    "MAT_Concrete_PLACEHOLDER": "hive-concrete",
    "MAT_DarkMetal_PLACEHOLDER": "hive-metal-dark",
    "MAT_WhiteWall_PLACEHOLDER": "hive-render-white",
    "MAT_InteriorTimber_PLACEHOLDER": "hive-timber-interior"
  },
  "untexturedAllowed": ["MAT_Glass_PLACEHOLDER", "MAT_MetalScreen_PLACEHOLDER", "MAT_Interior_PLACEHOLDER"],
  "expectedSurfaces": 6,
  "maxBytes": 5000000
}
```

Run `npm test`. Expected: FAIL for `the_hive.glb` with `surface material count`.

- [ ] **Step 2: Measure the palette**

Photos: `references/architecture/buildings/arts-council/` (`DSC06330.JPG`, `hive1.jpg`, `hive5.jpg`, `thehive.jpg`, `web_optimized_image.jpg`, `1-1-13.jpg.webp`). Palette file: `blender/source/textures/the-hive/palette.json`. Keys: `black brick face`, `black brick mortar`, `pale brick face`, `pale brick mortar`, `soot`, `concrete`, `dark metal`, `white wall`, `white wall dirt`, `timber light`, `timber dark`.

- [ ] **Step 3: Write `blender/scripts/theHiveTextures.py`**

```python
"""Surface materials for The Hive (Arts Council England).

Palette measured from references/architecture/buildings/arts-council/ into
palette.json (measurePatch.py).  Builders from commonSurfaces.py.

Run:

    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python-exit-code 1 --python blender/scripts/theHiveTextures.py
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

from commonSurfaces import (  # noqa: E402
    brick, concrete, load_palette, painted_metal, painted_render, run_texture_pass, timber,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEXTURE_DIR = PROJECT_ROOT / "blender" / "source" / "textures" / "the-hive"
RENDER_DIR = PROJECT_ROOT / "renders" / "the-hive-textures"
PALETTE_PATH = TEXTURE_DIR / "palette.json"
P = load_palette(PALETTE_PATH, (
    "black brick face", "black brick mortar", "pale brick face", "pale brick mortar", "soot",
    "concrete", "dark metal", "white wall", "white wall dirt", "timber light", "timber dark",
))

BUILDERS = (
    lambda: brick("hive-brick-black", "Black-brick lower floors",
                  P["black brick face"], P["black brick mortar"], P["soot"],
                  seed=6201, face_spread=0.08, soot_amount=0.15),
    lambda: brick("hive-brick-pale", "Upper pale-brick towers",
                  P["pale brick face"], P["pale brick mortar"], P["soot"], seed=6211),
    lambda: concrete("hive-concrete", "Structural concrete and soffits", P["concrete"], seed=6221),
    lambda: painted_metal("hive-metal-dark", "Dark metal frames and cladding trims",
                          P["dark metal"], seed=6231, rust_amount=0.2),
    lambda: painted_render("hive-render-white", "White wall planes",
                           P["white wall"], P["white wall dirt"], seed=6241),
    lambda: timber("hive-timber-interior", "Interior timber seen through the glazing",
                   P["timber light"], P["timber dark"], seed=6251),
)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    run_texture_pass("the-hive", TEXTURE_DIR, RENDER_DIR, PALETTE_PATH, BUILDERS, argv)
```

- [ ] **Step 4: Run the texture pass and review**

Run: `/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python blender/scripts/theHiveTextures.py`
Expected: `wrote 6 materials to …/the-hive`. Review the contact sheet against the photos.

- [ ] **Step 5: Export**

Run: `/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python blender/scripts/exportTexturedBuilding.py -- the-hive`
Expected: `the_hive.glb: 6 surface materials …`.

- [ ] **Step 6: Runtime policy and cache-buster**

In `applyTheHiveModelPolicy`, replace `material.map = null;` with `profileAuthoredMaps(material);`. Change `the_hive.glb?v=geometry-20260911` to `?v=textured-YYYYMMDD`.

- [ ] **Step 7: Verify.** Run `npm test && npm run build` (expected PASS), then the in-game check. The metal screen must still be semi-transparent.

- [ ] **Step 8: Commit**

```bash
git add config/building-textures.json src/world/createWorld.ts blender/scripts/theHiveTextures.py blender/source/textures/the-hive blender/source/runtime-untextured/the_hive.glb renders/the-hive-textures public/assets/models/the_hive.glb
git commit -m "Texture The Hive"
git push
```

### Task 7: Gulliver's

**Files:**
- Create: `blender/scripts/gulliversTextures.py`, `blender/source/textures/gullivers/`, `renders/gullivers-textures/`, `blender/source/runtime-untextured/harperhey-gullivers.glb`
- Modify: `config/building-textures.json`, `src/world/createWorld.ts` (`applyGulliversModelPolicy`, `harperhey-gullivers.glb?v=geometry-wip-20260911`), `public/assets/models/harperhey-gullivers.glb`

**Interfaces:**
- Consumes: `profileAuthoredMaps` (Task 5), the builders (Task 2), and the exporter (Task 4).

- [ ] **Step 1: Contract entry (failing)**

```json
{
  "building": "gullivers",
  "glb": "assets/models/harperhey-gullivers.glb",
  "surfacePrefix": "MAT_GUL_Surface_",
  "textureDir": "blender/source/textures/gullivers",
  "placeholders": {
    "Gullivers_Placeholder_Green_Tile": "gul-tile-green",
    "Gullivers_Placeholder_Cream_Tile_Inlay": "gul-tile-cream",
    "Gullivers_Placeholder_Dark_Tile_Plinth": "gul-tile-plinth",
    "Gullivers_Placeholder_Brick": "gul-brick",
    "Gullivers_Placeholder_Brick_Infill": "gul-brick",
    "Gullivers_Placeholder_Cream_Joinery": "gul-joinery-cream",
    "Gullivers_Placeholder_Green_Trim": "gul-paint-green-trim",
    "Gullivers_Placeholder_Dark_Green": "gul-paint-green-dark",
    "Gullivers_Placeholder_Door": "gul-door",
    "Gullivers_Placeholder_Door_Panels": "gul-door",
    "Gullivers_Placeholder_Black_Metal": "gul-metal-black"
  },
  "untexturedAllowed": [
    "Gullivers_Placeholder_Cornice_Shadow",
    "Gullivers_Placeholder_Interior",
    "Gullivers_Placeholder_Roof",
    "Gullivers_Placeholder_Dark_Glass",
    "Gullivers_Placeholder_Clerestory_Glass"
  ],
  "expectedSurfaces": 9,
  "maxBytes": 5000000
}
```

Run `npm test`. Expected: FAIL for `harperhey-gullivers.glb`.

- [ ] **Step 2: Measure the palette**

Photos: `references/architecture/buildings/gullivers/` (`DSC06338.JPG`, `DSC06339.JPG`, `gullivers-manchester.jpg`, `Gullivers-January-2025-2.jpg`, `gullivers-jun-2023-mcrfinest-2-scaled.jpg`). Palette: `blender/source/textures/gullivers/palette.json`. Keys: `green tile glaze`, `cream tile glaze`, `plinth tile glaze`, `tile grout`, `brick face`, `brick mortar`, `soot`, `cream joinery`, `green trim`, `dark green`, `door paint`, `black metal`.

- [ ] **Step 3: Write `blender/scripts/gulliversTextures.py`**

```python
"""Surface materials for Gulliver's: the green-tiled pub frontage.

Palette measured from references/architecture/buildings/gullivers/ into
palette.json (measurePatch.py).  Builders from commonSurfaces.py.

Run:

    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python-exit-code 1 --python blender/scripts/gulliversTextures.py
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

from commonSurfaces import (  # noqa: E402
    brick, glazed_tile, load_palette, painted_metal, painted_timber, run_texture_pass,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEXTURE_DIR = PROJECT_ROOT / "blender" / "source" / "textures" / "gullivers"
RENDER_DIR = PROJECT_ROOT / "renders" / "gullivers-textures"
PALETTE_PATH = TEXTURE_DIR / "palette.json"
P = load_palette(PALETTE_PATH, (
    "green tile glaze", "cream tile glaze", "plinth tile glaze", "tile grout", "brick face",
    "brick mortar", "soot", "cream joinery", "green trim", "dark green", "door paint", "black metal",
))

BUILDERS = (
    lambda: glazed_tile("gul-tile-green", "Green glazed faience, 6x3 in",
                        P["green tile glaze"], P["tile grout"], seed=6301),
    lambda: glazed_tile("gul-tile-cream", "Cream tile inlay bands, 6x6 in",
                        P["cream tile glaze"], P["tile grout"], seed=6311,
                        tile_size=(0.152, 0.152)),
    lambda: glazed_tile("gul-tile-plinth", "Dark tiled plinth, 9x6 in",
                        P["plinth tile glaze"], P["tile grout"], seed=6321,
                        tile_size=(0.228, 0.152)),
    lambda: brick("gul-brick", "Upper-storey and infill brick",
                  P["brick face"], P["brick mortar"], P["soot"], seed=6331),
    lambda: painted_timber("gul-joinery-cream", "Cream sash and fascia joinery",
                           P["cream joinery"], seed=6341),
    lambda: painted_timber("gul-paint-green-trim", "Green painted trim",
                           P["green trim"], seed=6351),
    lambda: painted_timber("gul-paint-green-dark", "Dark green painted panels",
                           P["dark green"], seed=6361),
    lambda: painted_timber("gul-door", "Pub doors and door panels",
                           P["door paint"], seed=6371, chips=24),
    lambda: painted_metal("gul-metal-black", "Black railings and brackets",
                          P["black metal"], seed=6381, px=512),
)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    run_texture_pass("gullivers", TEXTURE_DIR, RENDER_DIR, PALETTE_PATH, BUILDERS, argv)
```

- [ ] **Step 4: Run the texture pass and review**

Run: `/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python blender/scripts/gulliversTextures.py`
Expected: `wrote 9 materials to …/gullivers`. The green faience is the building's identity, so if it reads flat at 1024, raise `gul-tile-green` to `px=2048` and re-check the budget in Step 7.

- [ ] **Step 5: Export**

Run: `/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python blender/scripts/exportTexturedBuilding.py -- gullivers`
Expected: `harperhey-gullivers.glb: 9 surface materials …`. Gulliver's merges each component collection into one multi-material mesh, which the per-slot UVs handle.

- [ ] **Step 6: Runtime policy and cache-buster**

In `applyGulliversModelPolicy`, insert `profileAuthoredMaps(material);` as the first statement after the `instanceof MeshStandardMaterial` guard. Change `harperhey-gullivers.glb?v=geometry-wip-20260911` to `?v=textured-YYYYMMDD`.

- [ ] **Step 7: Verify.** Run `npm test && npm run build` (expected PASS), then the in-game check.

- [ ] **Step 8: Commit**

```bash
git add config/building-textures.json src/world/createWorld.ts blender/scripts/gulliversTextures.py blender/source/textures/gullivers blender/source/runtime-untextured/harperhey-gullivers.glb renders/gullivers-textures public/assets/models/harperhey-gullivers.glb
git commit -m "Texture Gulliver's"
git push
```

### Task 8: Renee

**Files:**
- Create: `blender/scripts/reneeTextures.py`, `blender/source/textures/renee/`, `renders/renee-textures/`, `blender/source/runtime-untextured/renee-blockout.glb`
- Modify: `config/building-textures.json`, `src/world/createWorld.ts` (`applyReneeBlockoutPolicy`, `renee-blockout.glb?v=geometry-wip-20260911`), `public/assets/models/renee-blockout.glb`

**Interfaces:**
- Consumes: `profileAuthoredMaps` (Task 5), the builders (Task 2), and the exporter (Task 4).

- [ ] **Step 1: Contract entry (failing)**

```json
{
  "building": "renee",
  "glb": "assets/models/renee-blockout.glb",
  "surfacePrefix": "MAT_REN_Surface_",
  "textureDir": "blender/source/textures/renee",
  "placeholders": {
    "MAT_REN_Brick_PLACEHOLDER": "ren-brick",
    "MAT_REN_BlackFacade_PLACEHOLDER": "ren-facade-black",
    "MAT_REN_Stone_PLACEHOLDER": "ren-stone",
    "MAT_REN_Concrete_PLACEHOLDER": "ren-concrete",
    "MAT_REN_Metal_PLACEHOLDER": "ren-metal",
    "MAT_REN_WindowFrame_PLACEHOLDER": "ren-frame-paint",
    "MAT_REN_Timber_PLACEHOLDER": "ren-timber",
    "MAT_REN_DarkWall_PLACEHOLDER": "ren-wall-dark"
  },
  "untexturedAllowed": ["MAT_REN_Upholstery_PLACEHOLDER", "MAT_REN_Glass_PLACEHOLDER"],
  "expectedSurfaces": 8,
  "maxBytes": 5000000
}
```

Run `npm test`. Expected: FAIL for `renee-blockout.glb`.

- [ ] **Step 2: Measure the palette**

Photos: `references/architecture/buildings/renae/` (`renae-NQ-1024x768.jpg`, `renae-3-1470x770.jpg`, `IMG_8039-1-scaled.jpg`, `Renae_2103222281.jpg`, `2028.photo.2.jpg`). Palette: `blender/source/textures/renee/palette.json`. Keys: `brick face`, `brick mortar`, `soot`, `black facade`, `facade dirt`, `stone`, `stone joint`, `concrete`, `metal`, `frame paint`, `timber light`, `timber dark`, `dark wall`.

- [ ] **Step 3: Write `blender/scripts/reneeTextures.py`**

```python
"""Surface materials for Renee.

Palette measured from references/architecture/buildings/renae/ into
palette.json (measurePatch.py).  Builders from commonSurfaces.py.  The brief
(02_Renee.txt) says brick is to be carried by PBR materials, not modelled.

Run:

    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python-exit-code 1 --python blender/scripts/reneeTextures.py
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

from commonSurfaces import (  # noqa: E402
    ashlar, brick, concrete, load_palette, painted_metal, painted_render, painted_timber,
    plaster, run_texture_pass, timber,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEXTURE_DIR = PROJECT_ROOT / "blender" / "source" / "textures" / "renee"
RENDER_DIR = PROJECT_ROOT / "renders" / "renee-textures"
PALETTE_PATH = TEXTURE_DIR / "palette.json"
P = load_palette(PALETTE_PATH, (
    "brick face", "brick mortar", "soot", "black facade", "facade dirt", "stone", "stone joint",
    "concrete", "metal", "frame paint", "timber light", "timber dark", "dark wall",
))

BUILDERS = (
    lambda: brick("ren-brick", "Brick frontage", P["brick face"], P["brick mortar"], P["soot"],
                  seed=6401),
    lambda: painted_render("ren-facade-black", "Black painted shopfront facade",
                           P["black facade"], P["facade dirt"], seed=6411, dirt_amount=0.15,
                           roughness=0.6),
    lambda: ashlar("ren-stone", "Stone dressings", P["stone"], P["stone joint"], P["soot"],
                   seed=6421, tile=1.20),
    lambda: concrete("ren-concrete", "Concrete threshold and base", P["concrete"], seed=6431),
    lambda: painted_metal("ren-metal", "Metalwork", P["metal"], seed=6441, px=512),
    lambda: painted_timber("ren-frame-paint", "Window frames", P["frame paint"], seed=6451,
                           tile=0.30, px=512),
    lambda: timber("ren-timber", "Acoustic timber slats", P["timber light"], P["timber dark"],
                   seed=6461),
    lambda: plaster("ren-wall-dark", "Dark interior walls", P["dark wall"], seed=6471),
)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    run_texture_pass("renee", TEXTURE_DIR, RENDER_DIR, PALETTE_PATH, BUILDERS, argv)
```

- [ ] **Step 4: Run the texture pass and review**

Run: `/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python blender/scripts/reneeTextures.py`
Expected: `wrote 8 materials to …/renee`.

- [ ] **Step 5: Export**

Run: `/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python blender/scripts/exportTexturedBuilding.py -- renee`
Expected: `renee-blockout.glb: 8 surface materials …`.

- [ ] **Step 6: Runtime policy and cache-buster**

In `applyReneeBlockoutPolicy`, insert `profileAuthoredMaps(material);` as the first statement after the `instanceof MeshStandardMaterial` guard. Change `renee-blockout.glb?v=geometry-wip-20260911` to `?v=textured-YYYYMMDD`.

- [ ] **Step 7: Verify.** Run `npm test && npm run build` (expected PASS), then the in-game check.

- [ ] **Step 8: Commit**

```bash
git add config/building-textures.json src/world/createWorld.ts blender/scripts/reneeTextures.py blender/source/textures/renee blender/source/runtime-untextured/renee-blockout.glb renders/renee-textures public/assets/models/renee-blockout.glb
git commit -m "Texture Renee"
git push
```

### Task 9: Real Camera

**Files:**
- Create: `blender/scripts/realCameraTextures.py`, `blender/source/textures/real-camera/`, `renders/real-camera-textures/`, `blender/source/runtime-untextured/real_camera.glb`
- Modify: `config/building-textures.json`, `src/world/createWorld.ts` (`applyRealCameraModelPolicy`, `real_camera.glb?v=geometry-20260912`), `public/assets/models/real_camera.glb`

**Interfaces:**
- Consumes: `profileAuthoredMaps` (Task 5), the builders (Task 2), and the exporter (Task 4).

- [ ] **Step 1: Contract entry (failing)**

```json
{
  "building": "real-camera",
  "glb": "assets/models/real_camera.glb",
  "surfacePrefix": "MAT_RC_Surface_",
  "textureDir": "blender/source/textures/real-camera",
  "placeholders": {
    "MAT_RC_LightSandstone": "rc-sandstone-light",
    "MAT_RC_DarkSandstone": "rc-sandstone-dark",
    "MAT_RC_RedSandstone": "rc-sandstone-red",
    "MAT_RC_PaintedWindowFrames": "rc-frame-paint",
    "MAT_RC_ShopTrimGreen": "rc-trim-green",
    "MAT_RC_Black": "rc-shopfront-black",
    "MAT_RC_Shutter": "rc-shutter",
    "MAT_RC_Metal": "rc-metal",
    "MAT_RC_DisplayWood": "rc-display-wood",
    "MAT_RC_CounterBase": "rc-display-wood",
    "MAT_RC_InteriorWalls": "rc-interior-wall"
  },
  "untexturedAllowed": [
    "MAT_RC_ShopGlass", "MAT_RC_WindowGlass", "MAT_RC_LensGlass", "MAT_RC_Fluorescent",
    "MAT_RC_SignWhite", "MAT_RC_PosterBlue", "MAT_RC_PosterYellow", "MAT_RC_ShelfRed",
    "MAT_RC_GreyCarpet", "MAT_RC_CeilingTiles", "MAT_RC_AwningRed"
  ],
  "expectedSurfaces": 10,
  "maxBytes": 9500000
}
```

(`maxBytes` is 9.5 MB because the untextured GLB is already 7.5 MB of geometry. The 5 MB budget covers maps, not an existing mesh.)

Run `npm test`. Expected: FAIL for `real_camera.glb`.

- [ ] **Step 2: Measure the palette**

Photos: `references/architecture/buildings/real-camera/EXT/` (list with `ls`). The brief `13_Real_Camera.txt` calls for sandstone pores, discoloration and moulded bands. Palette: `blender/source/textures/real-camera/palette.json`. Keys: `light sandstone`, `dark sandstone`, `red sandstone`, `stone joint`, `soot`, `frame paint`, `trim green`, `shopfront black`, `shutter paint`, `metal`, `display wood light`, `display wood dark`, `interior wall`.

- [ ] **Step 3: Write `blender/scripts/realCameraTextures.py`**

```python
"""Surface materials for Real Camera: sandstone piers, bands and the shopfront.

Palette measured from references/architecture/buildings/real-camera/EXT/ into
palette.json (measurePatch.py).  Builders from commonSurfaces.py.

Run:

    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python-exit-code 1 --python blender/scripts/realCameraTextures.py
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

from commonSurfaces import (  # noqa: E402
    ashlar, load_palette, painted_metal, painted_timber, plaster, run_texture_pass, timber,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEXTURE_DIR = PROJECT_ROOT / "blender" / "source" / "textures" / "real-camera"
RENDER_DIR = PROJECT_ROOT / "renders" / "real-camera-textures"
PALETTE_PATH = TEXTURE_DIR / "palette.json"
P = load_palette(PALETTE_PATH, (
    "light sandstone", "dark sandstone", "red sandstone", "stone joint", "soot", "frame paint",
    "trim green", "shopfront black", "shutter paint", "metal", "display wood light",
    "display wood dark", "interior wall",
))

BUILDERS = (
    lambda: ashlar("rc-sandstone-light", "Buff sandstone piers and upper facade",
                   P["light sandstone"], P["stone joint"], P["soot"], seed=6501, px=2048),
    lambda: ashlar("rc-sandstone-dark", "Sooted sandstone bands and reveals",
                   P["dark sandstone"], P["stone joint"], P["soot"], seed=6511,
                   soot_amount=0.45),
    lambda: ashlar("rc-sandstone-red", "Red sandstone dressings",
                   P["red sandstone"], P["stone joint"], P["soot"], seed=6521),
    lambda: painted_timber("rc-frame-paint", "Painted window frames", P["frame paint"],
                           seed=6531, tile=0.30, px=512),
    lambda: painted_timber("rc-trim-green", "Green shop trim", P["trim green"], seed=6541),
    lambda: painted_timber("rc-shopfront-black", "Black shopfront joinery",
                           P["shopfront black"], seed=6551),
    lambda: painted_metal("rc-shutter", "Roller shutter", P["shutter paint"], seed=6561,
                          rust_amount=0.3),
    lambda: painted_metal("rc-metal", "Metal fixings", P["metal"], seed=6571, px=512),
    lambda: timber("rc-display-wood", "Display and counter timber",
                   P["display wood light"], P["display wood dark"], seed=6581),
    lambda: plaster("rc-interior-wall", "Interior walls", P["interior wall"], seed=6591),
)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    run_texture_pass("real-camera", TEXTURE_DIR, RENDER_DIR, PALETTE_PATH, BUILDERS, argv)
```

- [ ] **Step 4: Run the texture pass and review**

Run: `/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python blender/scripts/realCameraTextures.py`
Expected: `wrote 10 materials to …/real-camera`.

- [ ] **Step 5: Export**

Run: `/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python blender/scripts/exportTexturedBuilding.py -- real-camera`
Expected: `real_camera.glb: 10 surface materials …`, at or under 9.5 MB.

- [ ] **Step 6: Runtime policy and cache-buster**

In `applyRealCameraModelPolicy`, insert `profileAuthoredMaps(material);` as the first statement after the `instanceof MeshStandardMaterial` guard. Change `real_camera.glb?v=geometry-20260912` to `?v=textured-YYYYMMDD`.

- [ ] **Step 7: Verify.** Run `npm test && npm run build` (expected PASS), then the in-game check. The fluorescent tubes must still glow.

- [ ] **Step 8: Commit**

```bash
git add config/building-textures.json src/world/createWorld.ts blender/scripts/realCameraTextures.py blender/source/textures/real-camera blender/source/runtime-untextured/real_camera.glb renders/real-camera-textures public/assets/models/real_camera.glb
git commit -m "Texture Real Camera"
git push
```

### Task 10: Greek Gyros

**Files:**
- Create: `blender/scripts/greekGyrosTextures.py`, `blender/source/textures/greek-gyros/`, `renders/greek-gyros-textures/`, `blender/source/runtime-untextured/greek_gyros.glb`
- Modify: `config/building-textures.json`, `src/world/createWorld.ts` (`applyGreekGyrosPolicy`, `greek_gyros.glb?v=geometry-pass-20260912`), `public/assets/models/greek_gyros.glb`

**Interfaces:**
- Consumes: `profileAuthoredMaps` (Task 5), the builders (Task 2), and the exporter (Task 4).

- [ ] **Step 1: Contract entry (failing)**

```json
{
  "building": "greek-gyros",
  "glb": "assets/models/greek_gyros.glb",
  "surfacePrefix": "MAT_GG_Surface_",
  "textureDir": "blender/source/textures/greek-gyros",
  "placeholders": {
    "MAT_GG_White_PLACEHOLDER": "gg-panel-white",
    "MAT_GG_Blue_PLACEHOLDER": "gg-panel-blue",
    "MAT_GG_DeepBlue_PLACEHOLDER": "gg-panel-deep-blue",
    "MAT_GG_DarkMetal_PLACEHOLDER": "gg-metal-dark",
    "MAT_GG_Metal_PLACEHOLDER": "gg-metal-steel"
  },
  "untexturedAllowed": ["MAT_GG_Glass_PLACEHOLDER", "MAT_GG_FixtureLens_PLACEHOLDER"],
  "expectedSurfaces": 5,
  "maxBytes": 5000000
}
```

Run `npm test`. Expected: FAIL for `greek_gyros.glb`.

- [ ] **Step 2: Measure the palette**

Photos: `references/architecture/infrastructure:objects/gyros/` (`gyross.jpeg`, `images.jpeg`, `IMG_8918.HEIC`; convert the HEIC with `sips` into the scratchpad first). Palette: `blender/source/textures/greek-gyros/palette.json`. Keys: `white panel`, `blue panel`, `deep blue panel`, `dark metal`, `steel`.

- [ ] **Step 3: Write `blender/scripts/greekGyrosTextures.py`**

```python
"""Surface materials for the Greek Gyros kiosk.

Palette measured from references/architecture/infrastructure:objects/gyros/ into
palette.json (measurePatch.py).  Builders from commonSurfaces.py.

Run:

    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python-exit-code 1 --python blender/scripts/greekGyrosTextures.py
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

from commonSurfaces import load_palette, painted_metal, run_texture_pass  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEXTURE_DIR = PROJECT_ROOT / "blender" / "source" / "textures" / "greek-gyros"
RENDER_DIR = PROJECT_ROOT / "renders" / "greek-gyros-textures"
PALETTE_PATH = TEXTURE_DIR / "palette.json"
P = load_palette(PALETTE_PATH, ("white panel", "blue panel", "deep blue panel", "dark metal", "steel"))

BUILDERS = (
    lambda: painted_metal("gg-panel-white", "White enamelled kiosk panels",
                          P["white panel"], seed=6601, rust_amount=0.2, roughness=0.4),
    lambda: painted_metal("gg-panel-blue", "Blue kiosk panels",
                          P["blue panel"], seed=6611, rust_amount=0.2, roughness=0.4),
    lambda: painted_metal("gg-panel-deep-blue", "Deep blue kiosk bands",
                          P["deep blue panel"], seed=6621, rust_amount=0.2, roughness=0.4),
    lambda: painted_metal("gg-metal-dark", "Dark metal frame and roof edge",
                          P["dark metal"], seed=6631, px=512),
    lambda: painted_metal("gg-metal-steel", "Stainless counter and fittings",
                          P["steel"], seed=6641, rust_amount=0.05, chips=0,
                          roughness=0.35, metallic=0.9, px=512),
)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    run_texture_pass("greek-gyros", TEXTURE_DIR, RENDER_DIR, PALETTE_PATH, BUILDERS, argv)
```

- [ ] **Step 4: Run the texture pass and review**

Run: `/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python blender/scripts/greekGyrosTextures.py`
Expected: `wrote 5 materials to …/greek-gyros`.

- [ ] **Step 5: Export**

Run: `/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python blender/scripts/exportTexturedBuilding.py -- greek-gyros`
Expected: `greek_gyros.glb: 5 surface materials …`.

- [ ] **Step 6: Runtime policy and cache-buster**

In `applyGreekGyrosPolicy`, replace `material.map = null;` with `profileAuthoredMaps(material);`. Change `greek_gyros.glb?v=geometry-pass-20260912` to `?v=textured-YYYYMMDD`.

- [ ] **Step 7: Verify.** Run `npm test && npm run build` (expected PASS), then the in-game check. The counter fixture lens must still glow.

- [ ] **Step 8: Commit**

```bash
git add config/building-textures.json src/world/createWorld.ts blender/scripts/greekGyrosTextures.py blender/source/textures/greek-gyros blender/source/runtime-untextured/greek_gyros.glb renders/greek-gyros-textures public/assets/models/greek_gyros.glb
git commit -m "Texture the Greek Gyros kiosk"
git push
```

### Task 11: Village Books

**Files:**
- Create: `blender/scripts/villageBooksTextures.py`, `blender/source/textures/village-books/`, `renders/village-books-textures/`, `blender/source/runtime-untextured/village-books-blockout.glb`
- Modify: `config/building-textures.json`, `src/world/createWorld.ts` (`applyVillageBooksBlockoutPolicy`, `village-books-blockout.glb?v=geometry-wip-20260912`), `public/assets/models/village-books-blockout.glb`

**Interfaces:**
- Consumes: `profileAuthoredMaps` (Task 5), the builders (Task 2), and the exporter (Task 4).

- [ ] **Step 1: Contract entry (failing)**

```json
{
  "building": "village-books",
  "glb": "assets/models/village-books-blockout.glb",
  "surfacePrefix": "MAT_VB_Surface_",
  "textureDir": "blender/source/textures/village-books",
  "placeholders": {
    "MAT_VB_DarkFacade_PLACEHOLDER": "vb-shopfront-black",
    "MAT_VB_WindowFrame_PLACEHOLDER": "vb-frame-black",
    "MAT_VB_UpperWall_PLACEHOLDER": "vb-upper-wall",
    "MAT_VB_InteriorWall_PLACEHOLDER": "vb-interior-wall",
    "MAT_VB_Floor_PLACEHOLDER": "vb-floor"
  },
  "untexturedAllowed": ["MAT_VB_Glass_PLACEHOLDER", "MAT_VB_131A_Glass_PLACEHOLDER"],
  "expectedSurfaces": 5,
  "maxBytes": 5000000
}
```

Run `npm test`. Expected: FAIL for `village-books-blockout.glb`.

- [ ] **Step 2: Measure the palette**

Photos: `references/architecture/buildings/village-books/` (`DSC06337.JPG`, `4efd27a2bb538cccb3dd78ac6e20b603-623x438.jpg`, `b3102f59670e76236c2a828b58ba9eac.jpeg`, `bbc76082711a5a2a9ec54f95efcfd91a.jpeg`). Palette: `blender/source/textures/village-books/palette.json`. Keys: `shopfront black`, `frame black`, `upper wall`, `upper wall dirt`, `interior wall`, `floor`. Sample `upper wall` from the band above the fascia in `DSC06337.JPG` (overcast) and `bbc76082…jpeg`. Sample `floor` from the shop floor seen through the open door.

- [ ] **Step 3: Write `blender/scripts/villageBooksTextures.py`**

```python
"""Surface materials for Village Books.

Palette measured from references/architecture/buildings/village-books/ into
palette.json (measurePatch.py).  Builders from commonSurfaces.py.  The brief
(10_Village_Books.txt) specifies black metal/aluminium shopfront frames.

Run:

    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python-exit-code 1 --python blender/scripts/villageBooksTextures.py
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

from commonSurfaces import (  # noqa: E402
    concrete, load_palette, painted_metal, painted_render, plaster, run_texture_pass,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEXTURE_DIR = PROJECT_ROOT / "blender" / "source" / "textures" / "village-books"
RENDER_DIR = PROJECT_ROOT / "renders" / "village-books-textures"
PALETTE_PATH = TEXTURE_DIR / "palette.json"
P = load_palette(PALETTE_PATH, (
    "shopfront black", "frame black", "upper wall", "upper wall dirt", "interior wall", "floor",
))

BUILDERS = (
    lambda: painted_metal("vb-shopfront-black", "Black powder-coated shopfront",
                          P["shopfront black"], seed=6701, rust_amount=0.1, roughness=0.45),
    lambda: painted_metal("vb-frame-black", "Black aluminium window frames",
                          P["frame black"], seed=6711, rust_amount=0.05, px=512),
    lambda: painted_render("vb-upper-wall", "Off-white painted render above the fascia",
                           P["upper wall"], P["upper wall dirt"], seed=6721),
    lambda: plaster("vb-interior-wall", "Shop interior walls", P["interior wall"], seed=6731),
    lambda: concrete("vb-floor", "Dark sealed shop floor", P["floor"], seed=6741,
                     roughness=0.6, stain_amount=0.1),
)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    run_texture_pass("village-books", TEXTURE_DIR, RENDER_DIR, PALETTE_PATH, BUILDERS, argv)
```

- [ ] **Step 4: Run the texture pass and review**

Run: `/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python blender/scripts/villageBooksTextures.py`
Expected: `wrote 5 materials to …/village-books`.

- [ ] **Step 5: Export**

Run: `/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python blender/scripts/exportTexturedBuilding.py -- village-books`
Expected: `village-books-blockout.glb: 5 surface materials …`.

- [ ] **Step 6: Runtime policy and cache-buster**

In `applyVillageBooksBlockoutPolicy`, replace `material.map = null;` with `profileAuthoredMaps(material);`, and change its leading comment from "still at its geometry-review hold. Preserve the authored placeholder palette" to "carries the authored PBR sets from villageBooksTextures.py". Change `village-books-blockout.glb?v=geometry-wip-20260912` to `?v=textured-YYYYMMDD`.

- [ ] **Step 7: Verify.** Run `npm test && npm run build` (expected PASS), then the in-game check.

- [ ] **Step 8: Commit**

```bash
git add config/building-textures.json src/world/createWorld.ts blender/scripts/villageBooksTextures.py blender/source/textures/village-books blender/source/runtime-untextured/village-books-blockout.glb renders/village-books-textures public/assets/models/village-books-blockout.glb
git commit -m "Texture Village Books"
git push
```

### Task 12: Advanced Photo

**Files:**
- Create: `blender/scripts/advancedPhotoTextures.py`, `blender/source/textures/advanced-photo/`, `renders/advanced-photo-textures/`, `blender/source/runtime-untextured/advanced-photo-blockout.glb`
- Modify: `config/building-textures.json`, `src/world/createWorld.ts` (`applyAdvancedPhotoBlockoutPolicy`, `advanced-photo-blockout.glb?v=geometry-wip-20260913`), `public/assets/models/advanced-photo-blockout.glb`

**Interfaces:**
- Consumes: `profileAuthoredMaps` (Task 5), the builders (Task 2), and the exporter (Task 4).

- [ ] **Step 1: Contract entry (failing)**

`MAT_AP_InteriorWall_PLACEHOLDER` stays untextured: the runtime policy gives it a deliberate interior glow keyed on that name.

```json
{
  "building": "advanced-photo",
  "glb": "assets/models/advanced-photo-blockout.glb",
  "surfacePrefix": "MAT_AP_Surface_",
  "textureDir": "blender/source/textures/advanced-photo",
  "placeholders": {
    "MAT_AP_BlackWood_PLACEHOLDER": "ap-shopfront-black",
    "MAT_AP_ArcadeWall_PLACEHOLDER": "ap-arcade-wall",
    "MAT_AP_ArcadeFloor_PLACEHOLDER": "ap-arcade-floor",
    "MAT_AP_Floor_PLACEHOLDER": "ap-floor",
    "MAT_AP_Counter_PLACEHOLDER": "ap-counter",
    "MAT_AP_Metal_PLACEHOLDER": "ap-metal"
  },
  "untexturedAllowed": ["MAT_AP_Glass_PLACEHOLDER", "MAT_AP_InteriorWall_PLACEHOLDER", "MAT_AP_ReviewRing"],
  "expectedSurfaces": 6,
  "maxBytes": 5000000
}
```

Run `npm test`. Expected: FAIL for `advanced-photo-blockout.glb`.

- [ ] **Step 2: Measure the palette**

Photos: `references/architecture/buildings/advanced-photo/` (`shop2.jpg`, `aes.jpeg`, `images.jpeg`, `imffdages.jpeg`, `7afbd084-…webp`; convert `0_I-work-in-town.jpg.avif` with `sips` if needed). Palette: `blender/source/textures/advanced-photo/palette.json`. Keys: `shopfront black`, `arcade wall`, `arcade dirt`, `arcade floor`, `shop floor`, `counter light`, `counter dark`, `metal`.

- [ ] **Step 3: Write `blender/scripts/advancedPhotoTextures.py`**

```python
"""Surface materials for Advanced Photo and its arcade.

Palette measured from references/architecture/buildings/advanced-photo/ into
palette.json (measurePatch.py).  Builders from commonSurfaces.py.  The brief
(03_Advanced_Photo.txt) centres the black painted shopfront system.

Run:

    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python-exit-code 1 --python blender/scripts/advancedPhotoTextures.py
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

from commonSurfaces import (  # noqa: E402
    concrete, load_palette, painted_metal, painted_render, painted_timber, run_texture_pass, timber,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEXTURE_DIR = PROJECT_ROOT / "blender" / "source" / "textures" / "advanced-photo"
RENDER_DIR = PROJECT_ROOT / "renders" / "advanced-photo-textures"
PALETTE_PATH = TEXTURE_DIR / "palette.json"
P = load_palette(PALETTE_PATH, (
    "shopfront black", "arcade wall", "arcade dirt", "arcade floor", "shop floor",
    "counter light", "counter dark", "metal",
))

BUILDERS = (
    lambda: painted_timber("ap-shopfront-black", "Black painted shopfront system",
                           P["shopfront black"], seed=6801, gloss=0.35),
    lambda: painted_render("ap-arcade-wall", "Arcade walls", P["arcade wall"], P["arcade dirt"],
                           seed=6811),
    lambda: concrete("ap-arcade-floor", "Arcade floor", P["arcade floor"], seed=6821,
                     roughness=0.7),
    lambda: concrete("ap-floor", "Shop floor", P["shop floor"], seed=6831, roughness=0.6,
                     stain_amount=0.1),
    lambda: timber("ap-counter", "Counter", P["counter light"], P["counter dark"], seed=6841),
    lambda: painted_metal("ap-metal", "Metal fixtures", P["metal"], seed=6851, px=512),
)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    run_texture_pass("advanced-photo", TEXTURE_DIR, RENDER_DIR, PALETTE_PATH, BUILDERS, argv)
```

- [ ] **Step 4: Run the texture pass and review**

Run: `/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python blender/scripts/advancedPhotoTextures.py`
Expected: `wrote 6 materials to …/advanced-photo`.

- [ ] **Step 5: Export**

Run: `/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python blender/scripts/exportTexturedBuilding.py -- advanced-photo`
Expected: `advanced-photo-blockout.glb: 6 surface materials …`.

- [ ] **Step 6: Runtime policy and cache-buster**

In `applyAdvancedPhotoBlockoutPolicy`, replace `material.map = null;` with `profileAuthoredMaps(material);`. Change `advanced-photo-blockout.glb?v=geometry-wip-20260913` to `?v=textured-YYYYMMDD`.

- [ ] **Step 7: Verify.** Run `npm test && npm run build` (expected PASS), then the in-game check. The interior should still show its warm glow.

- [ ] **Step 8: Commit**

```bash
git add config/building-textures.json src/world/createWorld.ts blender/scripts/advancedPhotoTextures.py blender/source/textures/advanced-photo blender/source/runtime-untextured/advanced-photo-blockout.glb renders/advanced-photo-textures public/assets/models/advanced-photo-blockout.glb
git commit -m "Texture Advanced Photo"
git push
```

### Task 13: ABC Building

**Files:**
- Create: `blender/scripts/abcBuildingTextures.py`, `blender/source/textures/abc-building/`, `renders/abc-building-textures/`, `blender/source/runtime-untextured/abc_building.glb`
- Modify: `config/building-textures.json`, `src/world/createWorld.ts` (`applyAbcBuildingModelPolicy`, `abc_building.glb?v=geometry-20260921`), `public/assets/models/abc_building.glb`

**Interfaces:**
- Consumes: `profileAuthoredMaps` (Task 5), the builders (Task 2), and the exporter (Task 4).

- [ ] **Step 1: Contract entry (failing)**

This GLB ships with **no UVs**, so the exporter creates `UVMap`. `MAT_ABC_Canopy_PLACEHOLDER` stays untextured because the policy lights it. `MAT_CLINTS_PLACEHOLDER` and `MAT_SIDE_STREET_PLACEHOLDER` are neighbouring blocks that get their own pass later.

```json
{
  "building": "abc-building",
  "glb": "assets/models/abc_building.glb",
  "surfacePrefix": "MAT_ABC_Surface_",
  "textureDir": "blender/source/textures/abc-building",
  "placeholders": {
    "MAT_ABC_WhiteFacade_PLACEHOLDER": "abc-facade-white",
    "MAT_ABC_Concrete_PLACEHOLDER": "abc-concrete",
    "MAT_ABC_DarkMetal_PLACEHOLDER": "abc-metal-dark",
    "MAT_ABC_EndBlock_PLACEHOLDER": "abc-endblock",
    "MAT_ABC_Planter_PLACEHOLDER": "abc-planter"
  },
  "untexturedAllowed": [
    "MAT_ABC_Glass_PLACEHOLDER", "MAT_ABC_InteriorDark_PLACEHOLDER", "MAT_ABC_Canopy_PLACEHOLDER",
    "MAT_CLINTS_PLACEHOLDER", "MAT_SIDE_STREET_PLACEHOLDER"
  ],
  "expectedSurfaces": 5,
  "maxBytes": 5000000
}
```

Run `npm test`. Expected: FAIL for `abc_building.glb`.

- [ ] **Step 2: Measure the palette**

Photos: `references/architecture/buildings/clints/EXT/` (the nine `Screenshot 2026-09-11 …png`, `images.jpeg`; convert `IMG_8908.HEIC` with `sips`). Palette: `blender/source/textures/abc-building/palette.json`. Keys: `white facade`, `facade dirt`, `concrete`, `dark metal`, `end block render`, `planter`. Sample `end block render` from the pale wall around the "ABC" letters in `Screenshot 2026-09-11 at 14.43.55.png`, and `planter` from the black planter boxes in `IMG_8908.HEIC`. That photo is lit at night, so mark the planter sample `shaded` and take a second daylight sample from `Screenshot 2026-09-11 at 14.42.03.png` if the planters are visible there.

- [ ] **Step 3: Write `blender/scripts/abcBuildingTextures.py`**

```python
"""Surface materials for the ABC Building.

Palette measured from references/architecture/buildings/clints/EXT/ into
palette.json (measurePatch.py).  Builders from commonSurfaces.py.  The brief
(12_ABC_Building_Clints_Side_Street.txt) describes a white facade over a
strong concrete/stone structural grid.

Run:

    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python-exit-code 1 --python blender/scripts/abcBuildingTextures.py
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

from commonSurfaces import (  # noqa: E402
    concrete, load_palette, painted_metal, painted_render, run_texture_pass,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEXTURE_DIR = PROJECT_ROOT / "blender" / "source" / "textures" / "abc-building"
RENDER_DIR = PROJECT_ROOT / "renders" / "abc-building-textures"
PALETTE_PATH = TEXTURE_DIR / "palette.json"
P = load_palette(PALETTE_PATH, (
    "white facade", "facade dirt", "concrete", "dark metal", "end block render", "planter",
))

BUILDERS = (
    lambda: painted_render("abc-facade-white", "White facade panels",
                           P["white facade"], P["facade dirt"], seed=6901, px=2048),
    lambda: concrete("abc-concrete", "Structural grid and columns", P["concrete"], seed=6911),
    lambda: painted_metal("abc-metal-dark", "Dark metal mullions and frames",
                          P["dark metal"], seed=6921, rust_amount=0.15),
    lambda: painted_render("abc-endblock", "West end block: pale render under the ABC letters",
                           P["end block render"], P["facade dirt"], seed=6931),
    lambda: painted_metal("abc-planter", "Black powder-coated steel planter boxes",
                          P["planter"], seed=6941, rust_amount=0.1, roughness=0.5, px=512),
)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    run_texture_pass("abc-building", TEXTURE_DIR, RENDER_DIR, PALETTE_PATH, BUILDERS, argv)
```

- [ ] **Step 4: Run the texture pass and review**

Run: `/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python blender/scripts/abcBuildingTextures.py`
Expected: `wrote 5 materials to …/abc-building`.

- [ ] **Step 5: Export**

Run: `/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python blender/scripts/exportTexturedBuilding.py -- abc-building`
Expected: `abc_building.glb: 5 surface materials …`. The ABC export carries glTF extras (`export_extras=True` in `createABCBuilding.py`), and the exporter preserves them.

- [ ] **Step 6: Runtime policy and cache-buster**

In `applyAbcBuildingModelPolicy`, insert `profileAuthoredMaps(material);` as the first statement after the `instanceof MeshStandardMaterial` guard. Change `abc_building.glb?v=geometry-20260921` to `?v=textured-YYYYMMDD`.

- [ ] **Step 7: Verify.** Run `npm test && npm run build` (expected PASS), then the in-game check. The canopy must still glow, and Bus Stop B must still sit at the west end of the frontage.

- [ ] **Step 8: Commit**

```bash
git add config/building-textures.json src/world/createWorld.ts blender/scripts/abcBuildingTextures.py blender/source/textures/abc-building blender/source/runtime-untextured/abc_building.glb renders/abc-building-textures public/assets/models/abc_building.glb
git commit -m "Texture the ABC Building"
git push
```

### Task 14: Dreams (greybox)

**Files:**
- Create: `blender/scripts/dreamsGreyboxTextures.py`, `blender/source/textures/dreams-greybox/`, `renders/dreams-greybox-textures/`, `blender/source/runtime-untextured/harperhey-dreams-greybox.glb`
- Modify: `config/building-textures.json`, `src/world/createWorld.ts` (`applyDreamsModelPolicy`, `harperhey-dreams-greybox.glb?v=geometry-approved-20260911`), `public/assets/models/harperhey-dreams-greybox.glb`

**Interfaces:**
- Consumes: `profileAuthoredMaps` (Task 5), the builders (Task 2), and the exporter (Task 4).

- [ ] **Step 1: Contract entry (failing)**

Daniel confirmed (Decision 1) that the approved greybox is the one to texture.

```json
{
  "building": "dreams",
  "glb": "assets/models/harperhey-dreams-greybox.glb",
  "surfacePrefix": "MAT_DRM_Surface_",
  "textureDir": "blender/source/textures/dreams-greybox",
  "placeholders": {
    "Dreams_Greybox_Brick": "drm-brick",
    "Dreams_Greybox_Concrete": "drm-concrete",
    "Dreams_Greybox_Wall": "drm-wall",
    "Dreams_Greybox_Cladding": "drm-cladding",
    "Dreams_Greybox_Cladding_Joint": "drm-cladding",
    "Dreams_Greybox_Roof": "drm-roof",
    "Dreams_Greybox_Roof_Trim": "drm-roof-trim",
    "Dreams_Greybox_Shutter": "drm-shutter",
    "Dreams_Greybox_Shutter_Frame": "drm-shutter",
    "Dreams_Greybox_Shutter_Corrugation": "drm-shutter",
    "Dreams_Greybox_Gutter": "drm-rail",
    "Dreams_Greybox_Rail": "drm-rail",
    "Dreams_Greybox_Signboard": "drm-signboard"
  },
  "untexturedAllowed": [
    "Dreams_Greybox_Alarm", "Dreams_Greybox_Recess", "Dreams_Greybox_Mortar",
    "Dreams_Greybox_Fixture", "Dreams_Greybox_Light_Tube", "Dreams_Greybox_Noticeboard",
    "Dreams_Greybox_Notice_Accent", "Dreams_Greybox_Lettering"
  ],
  "expectedSurfaces": 9,
  "maxBytes": 5000000
}
```

Run `npm test`. Expected: FAIL for `harperhey-dreams-greybox.glb`.

- [ ] **Step 2: Measure the palette**

Photos: `references/architecture/buildings/dreams/` (`Dreams.jpg`, `57.jpg`, `IMG_6391.PNG`–`IMG_6394.PNG`, `image.png`). Palette: `blender/source/textures/dreams-greybox/palette.json`. Keys: `brick face`, `brick mortar`, `soot`, `concrete`, `wall`, `wall dirt`, `cladding`, `roof`, `roof trim`, `shutter`, `rail`, `signboard`.

- [ ] **Step 3: Write `blender/scripts/dreamsGreyboxTextures.py`**

```python
"""Surface materials for the approved Dreams greybox.

Palette measured from references/architecture/buildings/dreams/ into
palette.json (measurePatch.py).  Builders from commonSurfaces.py.

Run:

    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python-exit-code 1 --python blender/scripts/dreamsGreyboxTextures.py
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

from commonSurfaces import (  # noqa: E402
    brick, concrete, load_palette, painted_metal, painted_render, run_texture_pass,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEXTURE_DIR = PROJECT_ROOT / "blender" / "source" / "textures" / "dreams-greybox"
RENDER_DIR = PROJECT_ROOT / "renders" / "dreams-greybox-textures"
PALETTE_PATH = TEXTURE_DIR / "palette.json"
P = load_palette(PALETTE_PATH, (
    "brick face", "brick mortar", "soot", "concrete", "wall", "wall dirt", "cladding",
    "roof", "roof trim", "shutter", "rail", "signboard",
))

BUILDERS = (
    lambda: brick("drm-brick", "Brick base and piers", P["brick face"], P["brick mortar"],
                  P["soot"], seed=7001),
    lambda: concrete("drm-concrete", "Ramp and plinth concrete", P["concrete"], seed=7011),
    lambda: painted_render("drm-wall", "Painted wall planes", P["wall"], P["wall dirt"],
                           seed=7021),
    lambda: painted_metal("drm-cladding", "Profiled metal cladding", P["cladding"],
                          seed=7031, rust_amount=0.4),
    lambda: painted_metal("drm-roof", "Weathered roof sheet", P["roof"], seed=7041,
                          rust_amount=0.8),
    lambda: painted_metal("drm-roof-trim", "Painted roof trim", P["roof trim"], seed=7051,
                          px=512),
    lambda: painted_metal("drm-shutter", "Roller shutters and frames", P["shutter"],
                          seed=7061, rust_amount=0.5),
    lambda: painted_metal("drm-rail", "Handrails and gutters", P["rail"], seed=7071, px=512),
    lambda: painted_metal("drm-signboard", "Signboard backing", P["signboard"], seed=7081,
                          rust_amount=0.2),
)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    run_texture_pass("dreams-greybox", TEXTURE_DIR, RENDER_DIR, PALETTE_PATH, BUILDERS, argv)
```

- [ ] **Step 4: Run the texture pass and review**

Run: `/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python blender/scripts/dreamsGreyboxTextures.py`
Expected: `wrote 9 materials to …/dreams-greybox`.

- [ ] **Step 5: Export**

Run: `/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python blender/scripts/exportTexturedBuilding.py -- dreams`
Expected: `harperhey-dreams-greybox.glb: 9 surface materials …`.

- [ ] **Step 6: Runtime policy and cache-buster**

In `applyDreamsModelPolicy`, insert `profileAuthoredMaps(material);` as the first statement after the `instanceof MeshStandardMaterial` guard (`applyPhotographicModelPolicy` only profiles `map`, `emissiveMap` and `alphaMap`). Change `harperhey-dreams-greybox.glb?v=geometry-approved-20260911` to `?v=textured-YYYYMMDD`.

- [ ] **Step 7: Verify.** Run `npm test && npm run build` (expected PASS), then the in-game check. The light tubes must still glow.

- [ ] **Step 8: Commit**

```bash
git add config/building-textures.json src/world/createWorld.ts blender/scripts/dreamsGreyboxTextures.py blender/source/textures/dreams-greybox blender/source/runtime-untextured/harperhey-dreams-greybox.glb renders/dreams-greybox-textures public/assets/models/harperhey-dreams-greybox.glb
git commit -m "Texture the Dreams greybox"
git push
```

### Task 15: Coral

**Files:**
- Create: `blender/scripts/coralTextures.py`, `blender/source/textures/coral/`, `renders/coral-textures/`, `blender/source/runtime-untextured/harperhey-coral-shop.glb`
- Modify: `config/building-textures.json`, `src/world/createWorld.ts` (`applyCoralModelPolicy`, `loadModel('assets/models/harperhey-coral-shop.glb')`), `public/assets/models/harperhey-coral-shop.glb`

**Interfaces:**
- Consumes: `profileAuthoredMaps` (Task 5), the builders (Task 2), and the exporter (Task 4).

- [ ] **Step 1: Contract entry (failing)**

Daniel confirmed (Decision 2) that two photos are enough. Coral's policy currently replaces every brick and concrete material with the world-prototype tiles. After this task, the authored surfaces replace those.

```json
{
  "building": "coral",
  "glb": "assets/models/harperhey-coral-shop.glb",
  "surfacePrefix": "MAT_COR_Surface_",
  "textureDir": "blender/source/textures/coral",
  "placeholders": {
    "Coral_Brick": "cor-brick",
    "Coral_Upper_Brick": "cor-brick",
    "Coral_Blue_Tile": "cor-tile-blue",
    "Coral_Concrete": "cor-concrete",
    "Coral_Dark_Concrete": "cor-concrete",
    "Coral_Stair_Material": "cor-concrete",
    "Coral_Dark_Wall": "cor-render-dark",
    "Coral_Repair_Patch": "cor-render-patch",
    "Coral_Dark_Metal": "cor-metal-dark",
    "Coral_Black_Metal": "cor-metal-dark",
    "Coral_Metal": "cor-metal-dark",
    "Coral_Navy_Trim": "cor-paint-navy",
    "Coral_Aluminium": "cor-aluminium",
    "Coral_Window_Frame": "cor-frame",
    "Coral_Weathered_Timber": "cor-timber"
  },
  "untexturedAllowed": [
    "Coral_Cream_Plastic", "Coral_Soot_Stain", "Coral_Printed_White", "Coral_Printed_Tan",
    "Coral_Printed_Light_Blue", "Coral_Store_Glass", "Coral_White_Print", "Coral_Paper",
    "Coral_Ink", "Coral_Black", "Coral_Printed_Blue", "Coral_Printed_Green", "Coral_Curtain",
    "Coral_Upper_Window_Dark", "Coral_Upper_Window_Lit", "Coral_Sign_Blue", "Coral_Fluorescent",
    "Coral_Interior_Poster", "Coral_Interior_Screen", "Coral_Interior_Blue",
    "Coral_Interior_Ceiling", "Coral_Counter_Blue", "Coral_Counter_Top", "Coral_Interior_Floor",
    "Coral_Terminal_Dark", "Coral_Terminal_Glow", "Coral_Brass", "Coral_Logo_Green",
    "Coral_Logo_Red", "Coral_Logo_Yellow", "Coral_Sign_Letters", "Coral_Railing_Mesh",
    "Coral_Lamp_Glow", "Coral_Window_Recess"
  ],
  "expectedSurfaces": 10,
  "maxBytes": 7000000
}
```

(`maxBytes` is 7 MB because the untextured GLB is already 4.8 MB of geometry.)

Run `npm test`. Expected: FAIL for `harperhey-coral-shop.glb`.

- [ ] **Step 2: Measure the palette**

Photos: `references/architecture/buildings/coral/` (`coral.jpg`, `coral2.png`). Palette: `blender/source/textures/coral/palette.json`. Keys: `brick face`, `brick mortar`, `soot`, `blue tile glaze`, `tile grout`, `concrete`, `dark wall`, `wall dirt`, `repair patch`, `dark metal`, `navy trim`, `aluminium`, `window frame`, `timber light`, `timber dark`.

- [ ] **Step 3: Write `blender/scripts/coralTextures.py`**

```python
"""Surface materials for the Coral bookmaker and the block above it.

Palette measured from references/architecture/buildings/coral/ into
palette.json (measurePatch.py).  Builders from commonSurfaces.py.  Signage,
prints, logos and interior dressing stay flat for a later artwork pass.

Run:

    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python-exit-code 1 --python blender/scripts/coralTextures.py
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

from commonSurfaces import (  # noqa: E402
    brick, concrete, glazed_tile, load_palette, painted_metal, painted_render, painted_timber,
    run_texture_pass, timber,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEXTURE_DIR = PROJECT_ROOT / "blender" / "source" / "textures" / "coral"
RENDER_DIR = PROJECT_ROOT / "renders" / "coral-textures"
PALETTE_PATH = TEXTURE_DIR / "palette.json"
P = load_palette(PALETTE_PATH, (
    "brick face", "brick mortar", "soot", "blue tile glaze", "tile grout", "concrete",
    "dark wall", "wall dirt", "repair patch", "dark metal", "navy trim", "aluminium",
    "window frame", "timber light", "timber dark",
))

BUILDERS = (
    lambda: brick("cor-brick", "Shop and upper-block brick", P["brick face"], P["brick mortar"],
                  P["soot"], seed=7101, soot_amount=0.4),
    lambda: glazed_tile("cor-tile-blue", "Blue stall-riser tiles", P["blue tile glaze"],
                        P["tile grout"], seed=7111, tile_size=(0.152, 0.152)),
    lambda: concrete("cor-concrete", "Stairs, sills and concrete", P["concrete"], seed=7121,
                     stain_amount=0.35),
    lambda: painted_render("cor-render-dark", "Dark painted wall", P["dark wall"],
                           P["wall dirt"], seed=7131),
    lambda: painted_render("cor-render-patch", "Render repair patches", P["repair patch"],
                           P["wall dirt"], seed=7141, dirt_amount=0.15),
    lambda: painted_metal("cor-metal-dark", "Dark and black metalwork", P["dark metal"],
                          seed=7151),
    lambda: painted_metal("cor-paint-navy", "Navy fascia trim", P["navy trim"], seed=7161,
                          rust_amount=0.25),
    lambda: painted_metal("cor-aluminium", "Shopfront aluminium", P["aluminium"], seed=7171,
                          rust_amount=0.05, chips=0, roughness=0.4, metallic=0.85, px=512),
    lambda: painted_timber("cor-frame", "Upper window frames", P["window frame"], seed=7181,
                           tile=0.30, px=512),
    lambda: timber("cor-timber", "Weathered timber", P["timber light"], P["timber dark"],
                   seed=7191, finish=0.8),
)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    run_texture_pass("coral", TEXTURE_DIR, RENDER_DIR, PALETTE_PATH, BUILDERS, argv)
```

- [ ] **Step 4: Run the texture pass and review**

Run: `/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python blender/scripts/coralTextures.py`
Expected: `wrote 10 materials to …/coral`.

- [ ] **Step 5: Export**

Run: `/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python blender/scripts/exportTexturedBuilding.py -- coral`
Expected: `harperhey-coral-shop.glb: 10 surface materials …`.

- [ ] **Step 6: Runtime policy and cache-buster**

In `applyCoralModelPolicy`, the `sourceMaterials.map((source) => { … })` callback replaces anything named `*brick` or `*concrete` with world-prototype materials. `MAT_COR_Surface_cor-brick` ends in `brick`, so it would be replaced too. Right after the `instanceof MeshStandardMaterial` guard, insert:

```ts
      if (source.map) {
        // Authored PBR set from coralTextures.py: keep it, skip the palette overrides.
        profileAuthoredMaps(source);
        return source;
      }
```

Then delete the now-unreachable `brick` and `concrete` branches and the `brick` / `concrete` world-material constants they return (declared at the top of `applyCoralModelPolicy`). Change `loadModel('assets/models/harperhey-coral-shop.glb')` to `loadModel('assets/models/harperhey-coral-shop.glb?v=textured-YYYYMMDD')`.

- [ ] **Step 7: Verify.** Run `npm test && npm run build` (expected PASS), then the in-game check. The fluorescent, lamp, sign and terminal glows must be unchanged.

- [ ] **Step 8: Commit**

```bash
git add config/building-textures.json src/world/createWorld.ts blender/scripts/coralTextures.py blender/source/textures/coral blender/source/runtime-untextured/harperhey-coral-shop.glb renders/coral-textures public/assets/models/harperhey-coral-shop.glb
git commit -m "Texture Coral with authored surfaces in place of the world-prototype tiles"
git push
```

---

### Task 16: Close-out

**Files:**
- Modify: `SYNC.md`

- [ ] **Step 1: Full check**

Run: `npm run check`
Expected: tests, asset validation, rights check and build all PASS.

- [ ] **Step 2: Re-run the three Blender tests**

Run each of `tests/blender/test_common_surfaces.py`, `test_measure_patch.py` and `test_textured_runtime_export.py` with the Blender command in Global Constraints. Expected: all exit 0.

- [ ] **Step 3: Add the Nice Things and Cass Art contract entries if their sessions have landed**

If `git log` shows the Nice Things / Cass Art texture work committed, add contract entries for `nice-things-blockout.glb` (prefix `MAT_NT_Surface_`, `legacyExporter: "blender/scripts/exportNiceThings.py"`) and for Cass Art in the form that session used. This brings every textured building under the same test. Read their GLB material names first; do not guess.

- [ ] **Step 4: Append the `SYNC.md` entry**

Record which buildings are now textured, any `maxBytes` raised and why, that decisions 1–4 were confirmed by Daniel on 2026-09-22, and that signage/lettering remains a separate artwork pass.

- [ ] **Step 5: Commit**

```bash
git add SYNC.md config/building-textures.json
git commit -m "Record the building texture pass in SYNC.md"
git push
```

# Art School T-shirt — black

Standalone wearable built from Daniel's black oversized T-shirt reference
(`references/characters/clothing/TSAU t-shirts/art_school_black.jpg`). It carries the
two-line upper-chest print in dark muted cobalt:

> I went to art school and  
> all I got was this lousy T-shirt.

The white colourway is a separate asset with its own builder
(`art-school-tshirt-white.md`); the two do not share construction.

## Deliverables

- Runtime GLB: `public/assets/models/characters/clothing/art_school_tshirt_black.glb`
- Editable source: `blender/source/characters/clothing/art_school_tshirt_black.blend`
- Builder: `blender/scripts/createArtSchoolTShirtBlack.py`
- Textures: `blender/source/textures/characters/clothing/art-school-tshirt-black/`
- Review renders and `validation.json`: `renders/art-school-tshirt-black/`

Regenerate from the repository root with Blender 5.2 (about four minutes, most of it cloth simulation):

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background \
  --python blender/scripts/createArtSchoolTShirtBlack.py
```

When only texture, material or render changes are being tried, append `-- --reuse-sim`
to reuse the cached simulation in the system temp directory.

## How it is built

The garment is made the way the real one is, not modelled as a surface:

1. **Pattern pieces measured from the flat lay.** The only assumption is scale: the
   side seams span 1061 px and are read as a 0.62 m chest, a size-L boxy blank.
   The builder's constants record the rest: 0.678 m body length, 0.158 m neck seam,
   dropped shoulder point 0.296 m out and 0.091 m down, 0.298 m armhole, 0.228 m sleeve,
   0.193 m flat cuff.
2. **Panels meshed** by constrained Delaunay triangulation, with matched vertex counts
   on every pair of edges that will be sewn. Front and back are separate pieces.
   Each sleeve is split along its top fold for placement, and that fold is welded.
3. **Placed on the fitting body without stretching.** Pattern distances are walked
   as arc lengths over a shoulder roll and round the body. Starting from stretched
   panels forces the neckline open.
4. **Cloth simulation with sewing springs.** The seams close in zero gravity, then the
   garment falls and settles. The cloth is stiff in plane (it keeps its cut size) and
   moderate in bending (broad folds). Self-collision is on.
5. **The rib band is modelled as a shrinking zone** on the neck edge (9%), as in a real
   crew neck. It holds the neckline on the shoulders. Below about 8% the yoke can lift
   over the neck.
6. **Seams welded**, surface relaxed, the few folded vertices at seam junctions
   flattened, and residual penetration of the body removed.
7. **Collar rib** swept along the settled neckline with parallel-transported frames,
   narrowed only at tight turns. The neck edge is snapped to the band's path so the
   two stay in register.
8. **2.6 mm cloth thickness** is added by solidify, with plain offset (see Gotchas). Hems
   and cuffs get a slightly thicker fold.

## Fitting body

A 1.78 m adult male in a 45° A-pose. Its proportions follow
`docs/assets/player-character.md`. The build log measures its cross-sections: neck
half-width 0.055 m, chest 0.163 × 0.108 m, waist 0.145 × 0.104 m. It is kept in
`FITTING_BODY_DO_NOT_EXPORT` in the `.blend` and never exported.

## UVs and textures

The UVs are the flat pattern itself, laid axis-aligned into a 2048² atlas. The front is
never mirrored. The weave, seams and stitching are generated in pattern space, so they
run continuously across island boundaries.

| Island | Density |
| --- | ---: |
| Print band (centre chest) | 3400 px/m (≈0.3 mm/texel) |
| Collar rib | 2000 px/m |
| Everything else | 1000 px/m |

- **Base colour:** very dark charcoal (sRGB ≈ 30) with fibre and low-frequency mottle.
  The ink is dark muted cobalt, sRGB ≈ (59, 78, 155). Its coverage is modulated by the
  weave, so it sits in the cloth.
- **Roughness:** about 0.9 with slow variation. The print is only 0.05 smoother.
- **Normal:** stochastic jersey fibre, collar rib wales, seam ridges, single topstitching
  at the armholes and below the collar, and a double-needle coverstitch at the hem and
  cuffs. Regular sine knits were dropped because they moiré against the texel grid.
- **Print:** rendered from type at 4× supersampling, then box-filtered into the island.
  The working render is kept as `…-print-working.png`. Line two is fitted to the
  photograph's 0.268 m ink width. Line one then measures 0.211 m against the reference's
  0.214 m, which suggests the reference is set in Snell Roundhand or something very close.
  Ink tops land 0.166 m and 0.194 m below the high point of the shoulder, as measured.
- The inside of the shirt uses the back panel's island, so the print does not show
  through the neck opening.

Material `MAT_ArtSchool_Black`: metallic 0, restrained specular (`KHR_materials_specular`),
and light sheen (`KHR_materials_sheen`) so black cloth keeps its form under night lighting.
In three.js this loads as `MeshPhysicalMaterial` with base colour, normal and roughness
maps.

## Validation

The build fails on any of the following: more than one mesh, a missing material or
texture slot, a triangle count outside 5,000–12,000, non-manifold geometry after
welding glTF attribute splits, a leaked body, camera or light, a seam still more
than 30 mm open before welding, or a neckline that has ridden up the neck. All renders
are made from the **reimported GLB**, not the source scene. It was also loaded in the
project's own three.js/Vite stack with no console errors: the print reads correctly
on the −Z (front) side.

| Check | Result |
| --- | ---: |
| Triangles | 8,496 |
| Mesh objects / materials / UV sets | 1 / 1 / 1 |
| Non-manifold edges (welded) | 0 |
| Cloth strain vs flat pattern | mean −0.5%, p95 5.6% |
| Seam gaps before welding | mean 1.0 mm, max 6.2 mm |
| Neckline length | 0.428 m (pattern 0.448 m, rib-gathered) |
| GLB size | 3.1 MB |

The full machine-readable report, including clearance to the body, is `validation.json`.

## Review set

`01-front`, `02-rear`, `03-three-quarter`, `04-three-quarter-rear`, `05-side`,
`06-chest-print-closeup`, `07-collar-closeup`, `08-hard-light-construction`,
`09-night-streetlight` (sodium key with LED spill, as in the player character's view M).

## Known limitations

- **The A-pose lifts the hem.** On the fitting body the hem hangs 0.506 m below the
  shoulder, not the 0.678 m it is cut to. Nothing is short or stretched: the sleeve rests
  on the raised arm and carries the underarm up 0.187 m. `validation.json` records this
  under `hang_on_fitting_body`. The player rig's rest pose has the arms nearly vertical,
  so binding this garment to that rig needs a refit in that pose (re-running the
  simulation with the arms down) rather than only skinning the A-pose mesh.
- **Typeface licence.** Snell Roundhand is a macOS system font. Its licence has not been
  checked for rasterising into a distributed game texture. The builder falls back to
  Great Vibes (OFL) and then Burgues Script. Daniel's own lettering or a licensed face
  would settle it.
- **One small fold** remains at the wearer's right shoulder-neck junction. It is visible
  only in the collar close-up.
- **Not skinned.** This is a rest-state garment. Weights and deformation testing come
  with the chosen armature.
- **Size:** three embedded 2K PNGs. A KTX2 runtime derivative would be worthwhile if this
  becomes a common wardrobe item.

## Gotchas found while building this (they apply project-wide)

- `mathutils.bvhtree.BVHTree.FromObject` builds in **object space**. A mesh joined from
  primitives keeps the first part's origin, so every nearest-point query silently misses
  unless the transform is applied first. The builder asserts an identity matrix.
- Solidify's **Even Thickness** divides the offset by the cosine of the fold angle, so a
  sharp crease in simulated cloth throws the inner shell tens of centimetres, which
  shows as blades. `thickness_clamp` does not prevent it; plain offset does.
- The sleeve cap runs underarm→peak while the armhole runs shoulder→underarm. Sewing
  them unflipped attaches the sleeve with a half twist. The builder reports the longest
  initial gap for every seam and refuses anything wider than 0.45 m.

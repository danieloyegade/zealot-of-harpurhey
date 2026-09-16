# Art School T-shirt — white

Standalone wearable asset based on Daniel's supplied white oversized T-shirt reference. The garment carries the exact two-line upper-chest print:

> I went to art school and  
> all I got was this lousy T-shirt.

Only the white colourway is included in this pass.

## Deliverables

- Runtime GLB: `public/assets/models/characters/clothing/art_school_tshirt_white.glb`
- Editable source: `blender/source/characters/clothing/art_school_tshirt_white.blend`
- Deterministic builder: `blender/scripts/createArtSchoolTShirtWhite.py`
- Runtime textures: `blender/source/textures/characters/clothing/art-school-tshirt-white/`
- Review renders and validation: `renders/art-school-tshirt-white/`

Regenerate from the repository root with Blender 5.2:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background \
  --python blender/scripts/createArtSchoolTShirtWhite.py
```

The builder uses the repository's CC0 cotton-jersey maps. For the working calligraphic print it selects, in order, local Great Vibes, Burgues Script, or macOS Snell Roundhand. Great Vibes was used for the delivered textures. The 4096 px working print is retained beside the final maps so the chosen lettering is reviewable without reopening Blender.

## Construction and fit

- Contemporary oversized heavyweight blank: broad body, dropped shoulder, wide short sleeves, straight hem, and clean crew neck.
- Built around a 1.8 m adult male A-pose fitting body. The body is retained in a `DO_NOT_EXPORT` review collection in the `.blend`; it is not present in the GLB.
- Garment thickness is approximately 2.8 mm. The neck rib band and restrained shoulder/sleeve seam relief are modelled as part of the final mesh.
- The shirt is a standalone rest-state garment, not skinned. It must be bound and deformation-tested against the chosen character armature before gameplay use.
- Blender orientation: character front is `+Y`; glTF export uses Y-up conversion.

## Material and textures

- One runtime material: `MAT_ArtSchool_White`.
- Warm off-white cotton base, high roughness, restrained specular response, and a very fine weave normal. It is intentionally not pure white and not glossy.
- The burgundy-red script is baked into the base-colour texture; no text geometry is exported.
- One runtime UV set, `UVMap`, produced as a packed non-overlapping bake layout with padding.
- Runtime maps are 2048 × 2048 PNG: base colour, tangent-space normal, and roughness.
- The source typography is rendered at 4096 × 4096 before baking down to the runtime set.

## Export contract and validation

The generated GLB reimports into a clean Blender scene with:

| Check | Result |
| --- | ---: |
| Object | `ARTSCHOOL_TSHIRT_WHITE` |
| Mesh objects | 1 |
| Materials | 1 |
| Triangles | 9,206 |
| Imported vertices | 10,515 |
| UV sets | 1 |
| Scale | 1, 1, 1 |
| Bounds | 1.4121 × 0.3341 × 0.8187 m |
| Non-manifold edges after welding glTF attribute splits | 0 |
| Fitting body, cameras, or lights in GLB | none |

The raw reimport contains expected vertex duplication along UV and normal seams. Validation welds coincident import splits before checking the underlying surface topology. The complete machine-readable report is `renders/art-school-tshirt-white/validation.json`.

## Review set

- `01-front.png`
- `02-back.png`
- `03-left-three-quarter.png`
- `04-right-three-quarter.png`
- `05-side.png`
- `06-chest-typography-closeup.png`
- `07-hard-light-construction.png`

The review mannequin is deliberately simplified and exists only to expose fit, clearance, silhouette, sleeve openings, and hem construction. Review the garment on the final player/NPC body before skinning; do not treat the mannequin as a character proposal.

## Runtime note

The current GLB embeds three 2K PNG maps and is about 6 MB. If this becomes a common NPC wardrobe item, create a KTX2-compressed runtime derivative while keeping the source GLB and textures as authored masters.

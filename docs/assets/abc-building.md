# ABC Building — Clints + Side Street

A metric, geometry-only reconstruction of the ABC Buildings on Quay Street,
inferred from the photographs and Street View captures in
`references/architecture/buildings/clints/EXT/` and the brief
`references/architecture/buildings/clints/12_ABC_Building_Clints_Side_Street.txt`.
Clints is the hero, enterable storefront; Side Street has a finished exterior
and a shallow shell. There are no textures, emissives, logos, stock, foliage,
or detailed interiors yet: materials are the `MAT_ABC_*_PLACEHOLDER` set.

## Deliverables

- Approval blockout: `blender/source/abc_building_blockout.blend`, renders in `renders/abc-building-blockout/`
- Blockout script (owns the layout numbers): `blender/scripts/createABCBuildingBlockout.py`
- Second geometry pass: `blender/scripts/createABCBuilding.py` (imports the blockout
  script as a module and swaps in refined builders)
- Editable source: `blender/source/abc_building.blend`
- Three.js runtime model: `public/assets/models/abc_building.glb` (~0.8 MB)
- Detail renders: `renders/abc-building/` (views A–K)

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --python blender/scripts/createABCBuilding.py
```

The detail script validates the scene, renders, exports the GLB, saves the
`.blend` and then reimports the GLB to check the door hierarchy and anchors.

## Frame of reference and layout

- 1 unit = 1 m, Z up. Origin is the ground-level corner of Quay Street and Lower Byrom Street.
- Quay Street elevation faces −Y and runs along −X. Lower Byrom Street elevation faces +X.
- Quay Street, east to west (left to right from the street): Every Man / Smolensky end block
  with the vertical ABC blade sign, ABC, THE DOME, TARTUFFE, CLINTS, ABC, ABC, then Side Street.
  Side Street is the last frontage and wraps round onto Lower Byrom Street.
- 7.5 m structural bays, 0.6 m columns; canopy 3.2 m deep with its underside at 3.55 m.
- Podium 9.6 m; tower 26.4 × 22 m, 14 floors of 3.35 m to 56.5 m, with a glazed core
  and the ABC letters at its east end. The east side wall is deliberately blank.

## Gameplay objects

- `CL_Entrance` → `CL_DoorFrame`, `CL_DoorFixedLeaf`, `CL_Door`. `CL_Door`'s origin is on its
  west-jamb hinge; positive Z rotation swings it out onto the pavement. Glass, handles,
  hinges, lock and closer are its children.
- Anchors (empties): `CL_EntranceTriggerAnchor`, `CL_InteriorSpawnAnchor`, `CL_ExitAnchor`,
  `CL_Neon_LeftAnchor`, `CL_Neon_RightAnchor`, `CL_LogoInteriorAnchor`, `CL_SignAnchor_Canopy`,
  `SS_EntranceAnchor`, `SS_LogoAnchor`, `SS_SignAnchor`, `ABC_TowerLogoAnchor`.
- `CL_InteriorShell_TEMP` (14.3 m deep) is meant to be replaced by `CL_Interior_FINAL`
  without touching the facade.
- Sign surfaces: one `ABC_SignSurface_<bay>` per tenant on the canopy band, plus end returns.

## Performance notes

- The tower grid is built from linked instances: `ABC_TowerBay_Module_Detail` on the first
  three floors of the street elevations, the lighter `ABC_TowerBay_Module` above and on the rear,
  and a shared `ABC_TowerWindow_Module` glass. The exported GLB has ~980 nodes but ~200 unique meshes.
- Placeholder lettering (`*_PLACEHOLDER`), review guides and helpers stay in the `.blend`
  and are excluded from the GLB.
- Planters (`ABC_Planter_Module`) are independent props, not fused to the building.

## In game

Loaded by `addAbcBuildingModel` in `src/world/createWorld.ts` at `ABC_BUILDING_CORNER` (19.65, -63.95) with no rotation. It faces south across the outer North Road, with Lower Byrom Street at X = 26.4 (see `docs/WORLD_LAYOUT.md`). The runtime policy `applyAbcBuildingModelPolicy`:
- makes the tower-window glass opaque (about one pane in nine lit sodium) so it merges into two draw calls;
- keeps the shopfront glass transparent;
- gives the canopy material a low warm emission.

`CL_Entrance` is detached during `mergeStaticModelMeshes` and re-added afterwards, so the door stays a separate, pivoting object. After merging, the building is 64 meshes, 46 of them transparent glass.

## Not yet done

Texture/normal-map pass, final emissive canopy panels and Clints neon, the detailed
Clints interior (and entering it), and LODs.

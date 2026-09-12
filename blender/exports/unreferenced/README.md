# Unreferenced GLB exports

These are exported runtime-format assets that **no code currently loads**. They
live here rather than in `public/assets/models/` because Vite copies everything
under `public/` verbatim into `dist/` — so while they sat there they were
downloaded as part of the build without ever being used.

They are kept rather than deleted: several are component exports or superseded
hero assets that are still useful reference, and all are reproducible from the
`.blend` masters and scripts under `blender/`.

| File | Why it is not referenced |
| --- | --- |
| `harperhey-dreams.glb` | Superseded — `createWorld.ts` loads `harperhey-dreams-greybox.glb`. |
| `harperhey-florist.glb` | Superseded — the florist location loads `nice-things-blockout.glb`. |
| `harperhey-coral-street-set.glb` | Composed set; Coral loads its parts individually. |
| `harperhey-coral-shopfront.glb` | Component of the composed Coral set. |
| `harperhey-coral-upper-block.glb` | Component of the composed Coral set. |
| `harperhey-coral-window-module.glb` | Component of the composed Coral set. |
| `preston-bus-shelter.glb` | Shelter-only export; the world loads `preston-busstop-reference.glb`. |
| `preston-shopping-trolley.glb` | Trolley-only export; included in the composed reference GLB. |
| `real-camera-blockout.glb` | Blockout stage, not yet wired into Three.js. |

## Moving one back into the build

When code starts loading one of these, `git mv` it back to
`public/assets/models/` (bus-shelter parts belong in the `bus-shelter/`
subdirectory) in the same commit as the code that references it. Keeping the
move and the reference together is what stops this directory refilling.

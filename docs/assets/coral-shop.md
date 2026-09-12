# Coral shop environment kit

The Coral kit is a modular, metric Blender recreation of the night-time shop in
`references/architecture/coral/coral2.png`. It is built from native geometry and
procedural materials, so the production assets have no external texture
dependencies.

## Source and preview

- Editable master: `blender/source/harperhey-coral-shop.blend`
- Rebuild script: `blender/scripts/createCoralShop.py`
- Review render: `renders/coral-shop/harperhey-coral-shop-preview.png`

Rebuild from the repository root with:

```sh
/Applications/Blender.app/Contents/MacOS/Blender \
  --background --factory-startup \
  --python blender/scripts/createCoralShop.py
```

## Runtime assets

All runtime files are self-contained GLB files in `public/assets/models/`.

| File | Purpose |
| --- | --- |
| `harperhey-coral-shop.glb` | Complete shopfront and upper residential block |
| `harperhey-coral-street-set.glb` | Preassembled building, pavement, road, bin, lamp and bollards |
| `harperhey-coral-shopfront.glb` | Ground-floor betting-shop façade |
| `harperhey-coral-upper-block.glb` | Upper floors, windows, deck, rails and service block |
| `harperhey-coral-window-module.glb` | Reusable upper-storey window bay |
| `harperhey-coral-bin.glb` | Teal public bin with domed lid, opening, wheels and graffiti |
| `harperhey-coral-streetlight.glb` | Black sodium-style streetlamp |
| `harperhey-coral-bollard.glb` | Black octagonal bollard with reflector band |

## Blender collections

- `Coral_Shopfront`
- `Coral_Upper_Block`
- `Coral_Window_Module`
- `Coral_Bin`
- `Coral_Streetlight`
- `Coral_Bollard`
- `Coral_Scene_Context`

The master uses metres with one Blender unit equal to one metre. The complete
scene contains 716 named objects and 11,254 source triangles. All details visible
in the single reference view were modelled: the glazed door and handle, divided
window bays, printed Coral privacy graphics and notices, fascia wordmark and
three-colour mark, blue tiled plinth, fluorescent strips, brick piers, side
stairs, three upper window bands with lit rooms, projecting concrete deck,
weathered timber/mesh railings, bin, streetlamp, bollards, pavement, curb, wet
road and double-yellow markings.

The second modelling pass also opens the shop into a real recessed room behind
the glazing. It includes a floor and ceiling, back wall, illuminated information
panels, counters, angled betting terminals, hanging signs and three rows of
ceiling fixtures. The upper building adds canopy hooks, a soot line, utility
pipework, repair panels, vents, denser metal posts and three slightly irregular
weathered timber rails.

## Game integration

`src/world/createWorld.ts` replaces the Coral loading block with the complete
shop GLB and places the matching bin, streetlight and two bollards on its
pavement. The imported Blender materials retain their signage, glass and
emission settings; exterior brick and concrete are remapped to the game's
soot-stained brick and cracked-concrete runtime textures. Two cool local lights
provide the shopfront spill visible on the wet street. The Coral plot is marked
finished in `src/world/worldLayout.ts` and uses segmented east-facing collision:
side and rear walls, front-wall sections around the door, and fixed counter
obstacles. The doorway and interior circulation are now accessible to the
player. The model is used at its authored frontage and vertical
scale (approximately 22.5 metres wide and 13.7 metres tall); only its depth is
extended to meet the existing west-terrace rear line. MCR1 uses the south-facing
plot immediately west of the Florist.

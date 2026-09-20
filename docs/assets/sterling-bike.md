# Sterling Bikes asset system

## Status

Geometry blockout, placed in game on 2026-09-13 at Daniel's request ("put the
sterling bikes in the game"). The blockout masters are exported as runtime
GLBs clearly named `-blockout`.

Second geometry pass on 2026-09-16 (Claude), rebuilt part by part against the
photographs after a review of the first blockout:

- **Dock:** replaced the tall charger-like cabinet with the real slim J-profile
  grey side post. It stands beside the front wheel on the rider's left (+Y),
  about 0.8 m tall, with a raked yellow bolted top lock plate and silver bar, a
  tall yellow "Bike Hire" panel with a teal band facing the wheel, a concave
  notch, and yellow-striped tread plates under the tyre on a thin rounded
  baseplate (IMG_8915).
- **Rear enclosure:** a smooth D-shaped clamshell (superellipse arc over a flat
  base at z 0.40) with a closing crown. The lower wheel and spokes stay exposed.
  Seat stays now run outboard and cross the teal panel, with reflective strips.
  The chainstays are flattened and sit below the dark band, which continues
  forward as the chain guard (IMG_8911/8912).
- **Frame:** one swept, flattened step-through tube that swells into the
  battery housing at the crank, with an access-panel seam, a head-tube gusset
  and a slimmer 48 mm seat tube (IMG_8913/8914/8916).
- **Basket:** a solid moulded tub with a rolled lip. Perforations are deferred
  to an alpha/normal map. It is frame-mounted (IMG_8916), with a dock lock
  tongue underneath and a white head-unit panel behind it.
- **Cockpit:** real raked steering axis, painted grey-lavender fork and crown,
  tall silver stem with collar and bolts, swept-back cruiser bar.
- **Wheels and running gear:** sidewall reflective stripes, dull rims, 28
  spokes per wheel, spoke-aligned reflectors, wide channel mudguards with
  wire stays, rear mudguard tail with a tall capsule rear lens (IMG_8917),
  black chainring guard, silver 5-arm spider, platform pedals, chain
  tensioner roller.
- **Palette:** lemon frame, aqua panels, silver-grey dock, golden-yellow dock
  panels.

Final materials, textures, decals (STERLING lettering, "electric", fleet
number, bee mark), dirt, working lights, LODs and the brief's final
`sterling_bike.glb`/`sterling_dock.glb` are still to come.

## Source

- Brief: `references/architecture/sterling-bikes/11_Sterling_Bikes.txt`
- Photographs: `IMG_8911.HEIC` through `IMG_8917.HEIC`
- Rebuild script: `blender/scripts/createSterlingBikeBlockout.py`
- Editable blockout: `blender/source/sterling-bike/sterling_bike_blockout.blend`
- Review renders: `renders/sterling-bike-blockout/A-...png` through `H-...png`

All seven photographs were cross-referenced. Dimensions are inferred from the
photographs rather than surveyed.

## Blockout dimensions and axes

- Blender units: metres
- Ground plane: `Z = 0`
- Bike travel/forward direction: local `+X`
- Axle height: `0.355 m`
- Wheel outside diameter: approximately `0.71 m`
- Wheelbase: `1.31 m`
- Overall bike length: approximately `1.9 m`
- Handlebar height: approximately `1.25 m` (grips)
- Steering axis: `0.30 rad` rake from vertical through `(0.49, 0, 0.93)`
- Rear enclosure: flat base at `z 0.40`, arc top about `0.82 m`
- Dock spacing in the reference station: `0.94 m`

The reusable bike origin is at ground level between the axles. The reusable
dock origin is at the centre of its baseplate at ground level.

## Functional contract

The following remain independently transformable:

- `SB_FrontWheel`: origin at the front axle; child of `SB_SteeringRoot`
- `SB_RearWheel`: origin at the rear axle
- `SB_SteeringRoot`: origin on the head-tube steering axis, rotated so its
  local Z is that raked axis (steer by rotating about local Z)
- `SB_CrankRoot`: origin at the crank spindle
- `SB_Pedal_Left` and `SB_Pedal_Right`: separate pedal roots
- `SB_Basket`: open-topped separate assembly, parented to the frame root (it
  does not steer), carrying `SB_DockLockTongue` and the front light
- `SB_FrontLightAnchor` and `SB_RearLightAnchor`: future light anchors
- `SB_DockAnchor`: bike-side snap transform at the bike root
- `SD_BikeDockAnchor`: dock-side snap transform
- `SD_InteractionAnchor`: future hire/return standing position

The dock-side anchor is `0.69 m` behind the dock origin so snapping the bike's
origin-level `SB_DockAnchor` onto it places the front axle in the wheel channel.
The three station bikes and docks are collection instances of the reusable
masters. View G hides only the middle bike instance, proving that its dock is
complete and independent.

## Review gate

Review the eight renders for (H is a close-up of the empty dock):

- shared-bike silhouette and real-world scale;
- flattened step-through battery/frame mass;
- rear enclosure size and its visible separation from the wheel;
- basket depth and open interior;
- cockpit height and upright riding posture;
- front-wheel engagement with the dock;
- station spacing, both occupied and with the middle bike removed.

Approval unlocks the second geometry pass described by the brief.

## Runtime blockout export

- Export script: `blender/scripts/exportSterlingBikeBlockout.py`. It opens the
  saved blockout `.blend` and never re-renders or saves it.
- Bike: `public/assets/models/sterling-bike/sterling-bike-blockout.glb`
  (~14.7k triangles, 153 source meshes; was ~8.3k before the second pass)
- Dock: `public/assets/models/sterling-bike/sterling-dock-blockout.glb`
  (~1.7k triangles)

```bash
/Applications/Blender.app/Contents/MacOS/Blender --background \
  blender/source/sterling-bike/sterling_bike_blockout.blend \
  --python blender/scripts/exportSterlingBikeBlockout.py
```

Only the two master collections are exported, never the reference station
instances, so the game controls occupancy. glTF is Y-up: bike forward stays
`+X`, and the dock anchor imports at `(-0.69, 0, 0)`.

The script renames the blockout's descriptive `pivot` custom property to
`pivot_note` during export. The three r185 GLTFLoader reads `userData.pivot` as
a GLTFExporter pivot container. A string there becomes a NaN `Object3D.pivot`,
and the wheels, steering, crank and basket vanish. Keep that key name out of
any future Sterling export.

At load, `src/world/createWorld.ts` merges each bike's static meshes by
material under their nearest articulated node (or the root). The nodes are
`SB_FrontWheel`, `SB_RearWheel`, `SB_SteeringRoot`, `SB_CrankRoot`, both pedals
and `SB_Basket`. The contract above still holds, at a few dozen draw calls per
bike rather than ~153. Station placement lives in `STERLING_BIKE_DOCKS`; see
`docs/WORLD_LAYOUT.md`.

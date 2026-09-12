# Player character — the Zealot

The hero playable character: a young Black British man in his mid-to-late
twenties, cornrowed, wearing an oversized near-black raw indigo denim jacket
and enormous indigo jeans, metallic silver Y2K football trainers, a black
patchwork-leather delivery bag, and historical steel greaves over his shins
and articulated gauntlets over his hands and forearms.

The point of the costume is the collision, not its resolution. He is not a
knight redesigned as a delivery rider; he is **a delivery rider upon whom the
visual language of knighthood has accumulated**, without explanation. Every
individual object should stay materially credible so that the contradiction
reveals itself gradually rather than announcing itself — the deadpan register
`docs/creative-constitution.md` §77 asks for, and the courier/knight
correspondence of §37 and §42–45.

References: `references/characters/player/` (hairstyle, denim jacket and
oversized-jeans fits, silver football trainers, black patchwork leather bag,
bronze greaves, articulated steel gauntlets). The hairstyle photograph is
grooming and presentation reference only — the face is **not** a likeness of
the person photographed.

## Stages

Two passes, in the project's usual promote pattern
(`createTheHiveBlockout.py` → `createTheHive.py`):

**1. Blockout** — silhouette, proportion, the garment/armour relationship, the
material hierarchy, the modular component split, review renders A–N. Keeps the
blockout's four pivot empties so it drops into the running game unchanged.

**2. Rig** — imports the blockout geometry and adds the production humanoid
armature: spine/neck/head, clavicles, arms, hands, two bones per finger plus
thumbs, legs and feet, a delivery-bag bone, and helper bones for the jacket
hem, sleeve hems, wide trouser hems and bag straps. Renders the walking and
bicycle-riding poses (views O–R).

**The rigged GLB is what the game loads.** `src/player/PlayerController.ts`
drives its skeleton directly.

Still outstanding after both:

- textures, normal maps and packed ORM
- the LOD0 / LOD1 / LOD2 chain
- authored animation clips (the walk cycle is procedural, see **In game**)

Neither pass overwrites `public/assets/models/player-character.glb`, the
earlier placeholder, which is now unused by the game but left in place.

## Deliverables

Blockout:

- Geometry source: `blender/source/player-character-blockout.blend`
- Script: `blender/scripts/createPlayerCharacterBlockout.py`
- GLB: `public/assets/models/player-character-blockout.glb`
- Renders: `renders/player-character-blockout/` (views A–N)

Rig:

- Rigged source: `blender/source/player-character-rigged.blend`
- Script: `blender/scripts/createPlayerCharacterRig.py`
- GLB: `public/assets/models/player-character-rigged.glb`
- Renders: `renders/player-character-rig/` (views O–R)

Regenerate from the project root with:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --python blender/scripts/createPlayerCharacterBlockout.py
```

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --python blender/scripts/createPlayerCharacterRig.py
```

The rig script rebuilds the blockout geometry internally, so running it alone
is enough to regenerate the rigged asset.

The existing `blender/scripts/createPlayerCharacter.py` builds a different,
earlier character (grey hoodie, washed denim, white trainers, ochre courier
bag) and still owns `public/assets/models/player-character.glb`, which is what
`src/player/PlayerController.ts` loads today. It is superseded by this brief
but has deliberately not been deleted or overwritten while this pass is under
review.

## Scale and orientation

1.78 m tall, slim-athletic. One Blender unit is one metre, Z is vertical, the
soles sit on Z = 0, and the character faces **+Y in Blender / -Z in glTF**,
which is the facing `ThirdPersonCamera` and `PlayerController` assume.

Key heights: ankle 0.085, knee 0.455, crotch 0.845, hip 0.965, waist 1.075,
shoulder 1.425, chin 1.545, crown 1.780.

Deliberately **not** heroic proportions — no enormous shoulders, no V-taper,
no superhero mass. The clothing silhouette carries the character; the body
underneath is ordinary.

## Engine contract

**Blockout GLB.** Four empties keep the names
`src/player/PlayerController.ts` looks up by string to drive the stride and
arm swing:

```
player-character-root
    player-left-arm-pivot     player-right-arm-pivot
    player-left-leg-pivot     player-right-leg-pivot
```

Everything that must swing with a limb is parented to the matching pivot —
jacket sleeve, gauntlet, jeans leg, greave, shoe. **Do not rename these.**

Parenting uses `matrix_parent_inverse` rather than assigning `matrix_world`
after setting `.parent`: the pivots are created moments before their children
and their evaluated `matrix_world` is still stale at that point, which
silently offsets every limb by the pivot's own height.

**Rigged GLB.** The armature supersedes that pivot scheme, and
`PlayerController` now drives bones instead of pivots. The rigged file offers
named attachment empties, bone-parented for gameplay use:

```
attach-hand-L   attach-hand-R   attach-bag   attach-head
```

## In game

`PlayerController` loads `player-character-rigged.glb` and animates it
procedurally — there are no authored clips in the GLB yet. It drives
`thigh_L/R`, `shin_L/R`, `upperarm_L/R`, `forearm_L/R` and the trouser and
jacket hem helpers.

The same rest-frame problem the Blender poses have applies here: a bone's local
euler axes depend on its rest orientation and roll, so the sign that swings a
thigh forward tips the spine backward. At load the controller resolves, once
per bone, the character's own +X axis expressed in that bone's rest-local
frame, then applies each frame's swing as a rotation about it. That makes the
walk cycle readable in plain "radians forward" terms.

Knees only bend one way, so the shin uses a rectified sine offset slightly
behind the stride rather than a mirror of the thigh.

If the GLB fails to load, the controller keeps its crude fallback figure and
logs a warning rather than leaving the player invisible.

## Budget

|  | draw calls | triangles | size |
| --- | --- | --- | --- |
| old placeholder | 77 | 9.6k | 0.31 MB |
| blockout GLB | 259 | 66.5k | 2.74 MB |
| **rigged GLB (in game)** | **33** | **66.4k** | **5.0 MB** |

The rigged GLB merges each costume component into one skinned mesh, so the
character costs 33 draw calls rather than 259 — fewer than the placeholder it
replaces. Triangles are up roughly 7x, which is what a hero character costs and
what the LOD chain is for.

Note the script's own console report counts triangles *before* the bevel
modifiers are applied, so it reads around 39k. The exporter bakes them; the
re-imported GLB is the honest number.

5 MB is the one number worth revisiting — it is mostly skin weights, now that
every vertex carries them. Draco or meshopt compression would cut it hard, but
that needs a decoder wired into `loadModel`.

## Rig

47 deform bones. Rigid parts (armour plates, shoes, hardware, head features,
bag panels) are bone-parented; anything that must deform — torso, jacket body
and sleeves, jeans seat and legs, limbs, neck — is skinned with vertex weights
generated from distance to the bone segments.

Two falloff profiles: a tight one for skin and a deliberately soft one for
garments, because jeans this wide have to move as heavy cloth rather than as a
second skin (brief §18). Influences below 4% of the strongest are discarded —
without that cutoff a distant bone drags the whole garment back toward the
rest pose whenever a limb swings.

Routing from mesh name to bone uses **side-aware** regexes. A plain prefix like
`PC_Greave_` is side-agnostic, and matching it against a per-side rule list
silently binds every right-leg plate to the left leg's bones — a mirror bug
that is invisible at rest and only appears once the rig is posed. The binder
raises on any unrouted mesh rather than skipping it.

## Component split

Modular so components can be swapped or removed later (outfit variation,
removing the bag, damage states):

```
ZOH_BODY  ZOH_HEAD  ZOH_HAIR_CORNROWS  ZOH_JACKET_DENIM  ZOH_JEANS_OVERSIZED
ZOH_GREAVES  ZOH_GAUNTLETS  ZOH_SHOES  ZOH_DELIVERY_BAG    (+ ZOH_REVIEW)
```

`ZOH_REVIEW` holds the ground plane, both lighting rigs and the review camera
and is excluded from the GLB export.

The saved `.blend` keeps all 259 meshes separate and editable. The merge into
one mesh per component happens **after** the `.blend` is saved and only affects
the exported GLB, so components stay independently swappable in the source
(brief §20) without costing draw calls at runtime.

## The garment / armour relationship

The hardest problem in the brief, and the thing most likely to go wrong: the
greaves have to coexist with jeans this wide without becoming armour tubes
worn outside the trousers.

The solution here is compression. Each jeans leg is lofted with a profile that
is enormous at the knee (0.34 m wide), **gathers sharply** where the upper
greave strap crosses it, stays compressed against the shin for the length of
the plate, escapes again below the lower strap, and then stacks and breaks
over the shoe. The greave is sized to the leg, not to the denim column, and
sits proud of the compressed cloth by roughly 8 mm. The gauntlet cuff does the
same thing to the denim sleeve at the wrist.

The jeans hem is also pulled backwards as well as upwards so the toe of the
silver trainer clears the denim — the brief wants the silver to flash beneath
the trouser hems as he walks, which cannot happen if the stack buries the shoe.

Both jeans legs are wide enough that they overlap across the centre line, as
trousers this wide really do. That is correct standing still and will need
attention at the rigging stage (helper bones on the hems, per brief §18).

## Material hierarchy

Placeholder PBR response only — no textures yet. The separations that matter:

| Group | Read |
| --- | --- |
| Skin | deep brown, soft, restrained subsurface, no waxy sheen |
| Hair | near-black, tight, controlled specular along the braids |
| Denim | raw indigo so dark it reads near-black under subdued light — **never bright blue** |
| Leather | black, alternating matte / semi / worn-gloss panels |
| Armour | aged steel, tarnished, oxidised, irregular |
| Shoes | manufactured metallic silver, smoother and brighter than the armour |

The armour and the shoes must never share a material. The armour is handmade,
historical and dulled; the shoes are manufactured, smooth and Y2K. That
contrast is most of what makes the costume legible.

## Cornrows

Nine braids swept along real paths across the cranium, converging slightly
toward the nape and ending in short braided tails. The braid interlock is
geometry — a pulsing radius with a lateral offset — not a normal map, because
the braids have to survive in the silhouette. Partings show a stubble-material
scalp cap rather than bare face skin.

## Review renders

`renders/player-character-blockout/`:

| | |
| --- | --- |
| A–D | front, rear, left profile, right profile |
| E, F | three-quarter front, three-quarter rear |
| G–L | cornrows, denim jacket, delivery bag, gauntlet, greave, silver shoe |
| M | night streetlight test (sodium key, LED spill, shopfront) |
| N | gameplay camera — 6.8 m at 0.31 rad, 50° FOV, 1.05 m look target, matching `src/camera/ThirdPersonCamera.ts` |

`renders/player-character-rig/`:

| | |
| --- | --- |
| O | walking pose |
| P | bicycle-riding pose |
| Q | walking, from the gameplay camera, at night |
| R | rig at rest, front — compare against blockout view A |

**F and N are the important ones.** They approximate what the player actually
looks at, and the character has to read from them as: cornrows + oversized
denim + black delivery bag + metal gauntlets/greaves + silver shoes.

## Open items

- Face. Built from primitive assembly like every other asset in this project,
  which caps how far it can go; it is restrained rather than detailed on
  purpose (brief §16 puts the budget in silhouette and material). If the face
  needs to carry close-ups, it wants a dedicated sculpt pass, not more
  primitives.
- Both jeans legs are wide enough to overlap across the centre line, as
  trousers this wide really do. Correct standing still; under a full stride
  the two columns interpenetrate. Wants either a collision-aware pass or
  tuned hem helper bones.
- Textures and LODs, as listed under Stages.
- No integration into `createWorld.ts` / `PlayerController.ts` yet. That swap
  needs the controller moved onto skeletal animation and should happen only
  once the geometry is approved.
- The studio review rig is exposed to show true material values, so the
  near-black indigo reads near-black. Views M, N and Q are the ones to judge
  the character by — they are the lighting it actually lives in.

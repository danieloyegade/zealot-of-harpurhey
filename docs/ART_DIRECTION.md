# Art Direction

> **Reconciliation note (2026-09-14):** "Core principles" and "Rendering restraint" below predate the current direction, "uncanny realism suspended between the photographic and the obviously constructed" (see `AGENTS.md`). In particular, "not modern photorealistic PBR" and "Dreamcast-era urban 3D" conflict with the PBR garment pipeline in "Fashion as a Core Art-Direction Pillar" and `TECHNICAL.md`. The sections from "Fashion as a Core Art-Direction Pillar" onward are current. The two older sections are still to be reconciled by Daniel.

## Core principles

- Project title: **Zealot of Harperhey**.
- This is a browser-based 3D artwork and game.
- The experience is desktop first and centred on third-person exploration.
- Its visual language is Dreamcast-era urban 3D: it is **not** generic cyberpunk and **not** modern photorealistic PBR.
- Daniel Oyegade's photography and filmmaking are primary influences.
- *The Spectres Are All Around Us* is a primary influence.
- Frames should be planimetric and carefully composed.
- The world is made from liminal urban spaces, pools of isolated streetlight at night, and deep darkness with photographic colour casts.
- Architecture is derived partly from photographs of Manchester, Harperhey, Preston, and elsewhere in North-West England.
- Geography is fictional rather than a literal reconstruction of Manchester.
- Photographic textures should be combined with deliberately simplified geometry.
- Subtitles use EB Garamond in yellow.
- The game HUD should be restrained.
- The world should sometimes look like a photograph or film frame.
- Social commentary, melancholy, humour, and surrealism should coexist.
- Avoid unnecessary visual polish that destroys the early-3D character.

## Rendering restraint

Art-direction changes must not be made merely because a more modern rendering technique is technically available. Rendering decisions should serve the photographic composition, atmosphere, and deliberately constrained early-3D character of the work. A technically newer effect is not inherently an artistic improvement.

## Fashion as a Core Art-Direction Pillar

Fashion is a primary component of Zealot of Harperhey's visual identity, not incidental character decoration.

The game's characters should feel styled and cast rather than procedurally dressed. Daniel's background as a fashion photographer should directly inform character design.

Every significant character and many background NPCs should have deliberately curated outfits. The population of Harperhey should feel like a photographed and styled cast.

References may include:

- Daniel's own clothing and T-shirts (see `creative-constitution.md` §35–36)
- Issey Miyake
- Ann Demeulemeester
- Klintz and other contemporary/Manchester fashion
- Fashion photography and editorial styling
- Art-school and Manchester creative subcultures

Where real designers are used as references, distinguish between aesthetic reference and reproduction of protected branding/designs for public release.

### Clothing quality target

Characters must **not** have Roblox/Minecraft-like blocky clothing.

Garments should be recognisable by:

- silhouette
- cut
- proportion
- fabric weight
- layering
- drape
- construction
- texture
- fit

The player should immediately be able to distinguish:

- jeans from trousers
- hoodie from jumper
- denim from wool/leather/nylon
- slim, straight, wide and oversized trousers
- fitted vs oversized jackets
- different garment lengths and layering

Silhouette is more important than excessive polygon density or logo detail.

Clothing does not initially require real-time cloth simulation. The preferred pipeline is:

```
fashion reference / photograph
→ garment modelling
→ Blender cloth simulation where useful
→ establish/bake convincing drape
→ retopology
→ skin to character skeleton
→ PBR materials
→ GLB
→ Three.js
```

Use real-time cloth only where it produces a meaningful improvement that justifies its performance cost. Technical detail is in `TECHNICAL.md` under "Character and garment pipeline".

## Daniel's Fashion Photography as Character Reference

Daniel's existing fashion photography should become a major source of character concept art.

Rather than generating generic NPCs, selected styled models from Daniel's photography can provide references for:

- silhouette
- layering
- garment proportion
- fabric behaviour
- styling
- colour relationships
- accessories
- poses
- lighting
- relationship between character and architecture

The photographed person does not necessarily need to be reproduced as that individual. The photograph can instead function as an authoritative styling/casting reference for an original game character.

Develop a **Zealot Lookbook** from approximately 20–30 strong existing fashion photographs. Each selected photograph can become the starting point for:

1. character/outfit concept
2. garment asset brief
3. Blender mockup
4. game-ready character
5. lighting/environment reference

This extends the existing asset-first workflow (`AGENTS.md`):

```
approved photographic reference/mockup
→ individual Blender/GLB assets
→ review
→ texture/material pass
→ integration
```

The goal is for Harperhey's population to look authored by a fashion photographer rather than generated by a conventional NPC system.

## Player Character Fashion

The protagonist remains a Black male with cornrows wearing:

- oversized denim jacket
- oversized jeans
- black leather delivery bag
- silver trainers
- greaves on shins/hands

The existing blocky character is a placeholder and should eventually be rebuilt to the higher fashion-character standard.

The protagonist should have a recognisable silhouette even when seen from behind or at distance. The delivery bag, oversized denim proportions and greaves are particularly important silhouette elements — the bag and greaves carry the courier/knight correspondence (`creative-constitution.md` §37, §42).

## Curated NPC Wardrobe System

Avoid unrestricted random outfit generation. Create curated looks. For example:

```
NPC 017
- elongated black coat
- grey knit
- wide black trousers
- square-toe shoes
- silver jewellery
- wired headphones
```

A limited collection of excellent garments can be recombined carefully across compatible body types while maintaining authored styling.

Potential base-character approach:

- several reusable body types
- shared compatible skeletons
- modular garment library
- curated outfit definitions
- hero-quality major characters
- lower-detail distant/background NPCs

## Photography Equipment in the World

Photography and filmmaking equipment should physically appear within Harperhey. Potential recurring objects:

- COB video lights
- Fresnel attachments
- light stands
- C-stands
- flags
- reflectors
- diffusion
- sandbags
- apple boxes
- tripods
- extension cables
- medium-format cameras

These objects are not merely environmental decoration. They extend the project's idea (`creative-constitution.md` §14–15):

**THE CITY IS A STAGE.
STREETLIGHTS ARE STAGE LIGHTS.
THE APPARATUS PRODUCING THE IMAGE CAN ENTER THE IMAGE.**

Certain apparently ordinary urban scenes can be explicitly illuminated by visible photography/video lights.

Example: a character stands or sits alone at night in an otherwise ordinary municipal environment. They are unusually beautifully illuminated. At the edge of the scene is a photographic light on a stand aimed directly at them. Nobody acknowledges why it is there.

This creates an uncanny boundary between:

- street
- photograph
- film set
- theatre
- game environment

It also connects directly to Daniel's real photographic practice.

## Photographic Tableaux

Some locations should operate as temporary photographic tableaux. Possible pattern:

```
ordinary exploration
→ player turns a corner
→ composition becomes unusually controlled
→ isolated subject
→ curated fashion
→ hard artificial light
→ visible photographic apparatus
→ little or no conventional gameplay explanation
```

These should be relatively rare so their appearance remains significant. They should connect to:

- *The Spectres Are All Around Us*
- *Figures Isolated Within Municipal Architecture*
- *Public Illumination Studies*
- the city-as-stage concept
- streetlights as stage lights
- planimetric composition
- nocturnal fashion photography

## Light as a Possible Interaction Mechanic

Long-term possibility: some photographic lights may be interactive. The player could rotate/reposition/activate a light and change how part of the environment becomes readable.

Potential uses:

- reveal artwork
- reveal a Spectre
- illuminate an NPC
- transform an ordinary location into a tableau
- expose text/signs/objects
- create photographic compositions

Conceptually: **light is not merely used to see the world. Light determines how the world can be read.**

This should remain compatible with the broader semiotic/deconstructive framework of *The Spectres Are All Around Us*. Performance constraints are in `TECHNICAL.md` under "Photographic lighting".

---

# Transport and Movement

## Harperhey ↔ The Promised Land Bus Route

Introduce a functioning bus system early while the map is still small.

Initial system:

- two buses
- two bus stops
- Harperhey
- The Promised Land
- buses travel continuously between them

**THE PROMISED LAND** should be treated as a genuine place-name within the mythology of the world rather than merely a joke. The contrast between an ordinary British municipal bus journey and the mythological/religious promise of "The Promised Land" is intentional.

The bus functions as:

- transportation
- moving observation chamber
- social environment
- worldbuilding device
- cinematic space

The player should eventually be able to board and remain physically on the bus during the journey rather than simply teleporting.

Potential bus experiences:

- looking through windows at night
- passing streetlights
- rain on glass
- overheard conversations
- advertisements
- Spectres artwork
- strange NPC encounters
- delivery riders visible outside
- destination/next-stop announcements
- views of parts of the city inaccessible on foot

The bus can allow the game to suggest a world considerably larger than the playable streets.

## Bus Technical Principle

Do **not** initially build sophisticated autonomous driving AI. Use predetermined routes/splines/road nodes.

Basic behaviour:

```
route
→ decelerate
→ stop
→ doors open
→ dwell
→ doors close
→ accelerate
→ continue route
```

Two buses can initially travel opposing directions along the same transport corridor.

Visual systems can include:

- rotating wheels
- suspension movement
- indicators
- brake lights
- headlights
- interior lights
- destination board
- doors
- engine/audio
- seated passengers

Traffic interaction can come later.

## Bicycle System

The bicycle should be the player's primary working transport and should connect directly to the gig-economy/delivery-rider identity.

Movement hierarchy:

- **Walking** — slow, observational, interiors, photography.
- **Bicycle** — primary active transport. Fast enough for deliveries. Can access alleys, paths and shortcuts.
- **Bus** — passive/public transportation. Longer journeys. Observation and encounters.
- **Horse** — potential later uncanny/mythological transport progression (`creative-constitution.md` §45).

Do not prioritise realistic cycling simulation. Prioritise responsive arcade-style handling:

- accelerate
- brake
- steer
- coast
- lean
- collision
- mount
- dismount
- optional small hop

Useful animation states:

- seated pedalling
- standing pedalling
- acceleration
- braking
- cornering
- idle
- mount
- dismount

The delivery bag remains part of the player's silhouette while cycling.

## Bikes as Designed Cultural Objects

Bicycles should receive the same art-direction attention as clothing.

Potential bicycle identities:

- track bike
- fixie
- vintage road bike
- old Raleigh-style bicycle
- cheap mountain bike
- delivery e-bike
- BMX
- expensive art-school/creative-scene bicycle

NPC bicycles can contribute to characterisation.

The overlap between fashion, photography, music, art-school culture, cycling, delivery work and Manchester should be consciously exploited.

## Fashion as Social Worldbuilding

Fashion may eventually affect NPC dialogue and social recognition without becoming a conventional RPG stat system.

Avoid mechanics such as "+4 Charisma". Prefer contextual acknowledgement:

- an NPC recognises a T-shirt
- an NPC recognises a designer/reference
- someone comments on impractical clothing
- someone photographs the player
- a fashion student asks about an item
- characters recognise particular local cultural signifiers

Clothing becomes part of the game's social language rather than numerical equipment.

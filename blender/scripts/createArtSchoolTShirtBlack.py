"""Build the black Art School T-shirt as a standalone game-ready wearable.

The supplied reference is an oversized heavyweight black fashion blank carrying
a small two-line chest print in muted cobalt script.  Rather than extruding a
silhouette, this script builds the garment the way the real one is made:

  flat pattern pieces measured from the reference flat-lay
    -> constrained-Delaunay panel meshes with matched seam vertices
    -> Blender cloth simulation with sewing springs around an A-pose fitting body
    -> seams welded, collar rib built on the settled neckline, cloth thickness
    -> pattern coordinates reused directly as the UV atlas (no mirroring)
    -> numpy texture generation in fabric space, chest print rendered from type
    -> GLB export, reimport verification and the review render set.

Because the UVs *are* the flat pattern, the print lands on the chest at exactly
the size and height it occupies in the reference photograph, and the weave,
seam and stitch detail stay continuous across island boundaries.

Run from the repository root:

    /Applications/Blender.app/Contents/MacOS/Blender --background \
        --python blender/scripts/createArtSchoolTShirtBlack.py

Developer flag (not needed for a clean regeneration):

    ... --python blender/scripts/createArtSchoolTShirtBlack.py -- --reuse-sim

which reuses the cached simulated garment in the system temp directory so the
texture, material and render stages can be iterated without re-simulating.

One Blender unit is one metre, Z is up, and the character faces +Y in Blender
(-Z after the glTF Y-up conversion), matching every other asset in this project.
The fitting body, studio, cameras and working typography are never exported.
"""

from __future__ import annotations

import json
import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import delaunay_2d_cdt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import surfaceWeathering as weathering  # shared numpy value-noise helpers

F = np.float32

ROOT = Path(__file__).resolve().parents[2]
SLUG = "art-school-tshirt-black"
BLEND_PATH = ROOT / "blender" / "source" / "characters" / "clothing" / "art_school_tshirt_black.blend"
GLB_PATH = ROOT / "public" / "assets" / "models" / "characters" / "clothing" / "art_school_tshirt_black.glb"
TEXTURE_DIR = ROOT / "blender" / "source" / "textures" / "characters" / "clothing" / SLUG
RENDER_DIR = ROOT / "renders" / SLUG
VALIDATION_PATH = RENDER_DIR / "validation.json"
SIM_CACHE = Path(tempfile.gettempdir()) / "zoh_art_school_tshirt_black_sim.blend"

BASECOLOR_PATH = TEXTURE_DIR / f"{SLUG}-basecolor.png"
ROUGHNESS_PATH = TEXTURE_DIR / f"{SLUG}-roughness.png"
NORMAL_PATH = TEXTURE_DIR / f"{SLUG}-normal.png"
PRINT_WORKING_PATH = TEXTURE_DIR / f"{SLUG}-print-working.png"

GARMENT_NAME = "ARTSCHOOL_TSHIRT_BLACK"
MATERIAL_NAME = "MAT_ArtSchool_Black"
BODY_NAME = "FIT_BODY"
TEXTURE_SIZE = 2048

FONT_CANDIDATES = (
    # Closest match to the reference lettering; see docs/assets for the licence note.
    Path("/System/Library/Fonts/Supplemental/SnellRoundhand.ttc"),
    Path.home() / "Library" / "Fonts" / "GreatVibes-Regular.ttf",
    Path.home() / "Library" / "Fonts" / "Burgues Script Regular.otf",
)

PRINT_LINES = ("I went to art school and", "all I got was this lousy T-shirt.")

# --------------------------------------------------------------- measurements
#
# Every garment number below is measured off references/characters/clothing/
# "TSAU t-shirts"/art_school_black.jpg, a flat lay.  The single assumed number is
# the chest width: the side seams span 1061 px and are read as 0.62 m, which is
# a size-L oversized boxy blank.  Everything else follows from that scale
# (0.000584 m/px) and is therefore proportionally faithful to the photograph.

NECK_HALF = 0.079            # half neck-seam width (255 px between shoulder points)
FRONT_NECK_DROP = 0.099      # centre-front neckline below the high point of shoulder
BACK_NECK_DROP = 0.018
SHOULDER_X = 0.296           # dropped shoulder point, from centre
SHOULDER_DROP = 0.091
BODY_HALF = 0.310            # half chest width
UNDERARM_Y = -0.389          # armhole depth of 0.298 m below the shoulder point
HEM_Y = -0.678               # body length, HPS to hem

CAP_W = 0.245                # sleeve cap half width (sews to the armhole)
CAP_H = 0.160
SLEEVE_LEN = 0.228
CUFF_HALF = 0.195            # flat cuff opening of 0.193 m

HPS_Z = 1.450                # high point of shoulder on the fitting body
ARM_ANGLE = math.radians(45.0)   # neutral A-pose
SHOULDER_JOINT = (0.190, 0.0, 1.400)
SLEEVE_START = 0.075         # sleeve cap peak, measured along the arm from the joint

PRINT_TOPS = (-0.166, -0.194)    # ink-top of each line below the HPS
PRINT_CENTRES = (0.0032, 0.0)    # ink-centre x of each line
PRINT_LINE2_WIDTH = 0.268        # ink width of the longer line
PRINT_RECT = (-0.165, -0.240, 0.165, -0.150)

FABRIC_SRGB = (0.118, 0.118, 0.124)   # very dark charcoal, deliberately not RGB black
INK_SRGB = (0.231, 0.306, 0.608)      # dark muted cobalt, not electric blue

# Front-panel island split: (bottom, top, half width of the high-density band).
PRINT_BAND = (-0.256, -0.148, 0.198)
ATLAS_PAD = 7                # texel gutter around every island


def srgb_to_linear(value):
    value = np.asarray(value, F)
    return np.where(value <= 0.04045, value / 12.92, ((value + 0.055) / 1.055) ** 2.4).astype(F)


FABRIC_LINEAR = srgb_to_linear(FABRIC_SRGB)
INK_LINEAR = srgb_to_linear(INK_SRGB)


def smoothstep(edge0, edge1, x):
    t = np.clip((np.asarray(x, F) - edge0) / (edge1 - edge0), 0.0, 1.0)
    return (t * t * (3.0 - 2.0 * t)).astype(F)


def log(message):
    print(f"[{SLUG}] {message}", flush=True)


def set_enum(struct, prop, preferred):
    """Assign an enum identifier only if this Blender build actually offers it."""
    items = [item.identifier for item in struct.bl_rna.properties[prop].enum_items]
    if preferred in items:
        setattr(struct, prop, preferred)
    return getattr(struct, prop)


# ------------------------------------------------------------------ scene util

def ensure_directories():
    for path in (BLEND_PATH.parent, GLB_PATH.parent, TEXTURE_DIR, RENDER_DIR):
        path.mkdir(parents=True, exist_ok=True)


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.render.image_settings.file_format = "PNG"


def collection(name):
    found = bpy.data.collections.get(name)
    if found is None:
        found = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(found)
    return found


def move_to_collection(obj, target):
    for owner in list(obj.users_collection):
        owner.objects.unlink(obj)
    target.objects.link(obj)


def simple_material(name, colour, roughness=0.8):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*colour, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = 0.0
    return mat


def activate(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


# --------------------------------------------------------------- fitting body

def _primitive_ellipsoid(centre, radii, segments=28, rings=14):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=centre)
    obj = bpy.context.object
    obj.scale = radii
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj


def _primitive_capsule(start, end, radius_start, radius_end, vertices=18):
    start_v, end_v = Vector(start), Vector(end)
    axis = end_v - start_v
    bpy.ops.mesh.primitive_cone_add(vertices=vertices, radius1=radius_start, radius2=radius_end,
                                    depth=axis.length, location=(start_v + end_v) * 0.5)
    obj = bpy.context.object
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = axis.to_track_quat("Z", "Y")
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    caps = [_primitive_ellipsoid(start, (radius_start,) * 3, 16, 8),
            _primitive_ellipsoid(end, (radius_end,) * 3, 16, 8)]
    return [obj, *caps]


def build_fitting_body():
    """A 1.78 m adult male fitting body in a neutral A-pose.

    Proportions follow docs/assets/player-character.md so the garment is fitted
    to the same body the game's character is built on: shoulder 1.425,
    waist 1.075, hip 0.965, crotch 0.845, crown 1.780.  It is a fitting aid and
    a review mannequin only, and is never exported.
    """
    target = collection("FITTING_BODY_DO_NOT_EXPORT")
    parts = []
    # The neck base has to stay a narrow column: if the trapezius mass reaches
    # neckline height, the collar is forced open around it and the whole
    # neckline stretches.
    parts.append(_primitive_ellipsoid((0, 0.0, 1.245), (0.170, 0.113, 0.170)))      # ribcage
    parts.append(_primitive_ellipsoid((0, -0.008, 1.345), (0.198, 0.100, 0.080)))   # shoulder girdle
    parts.append(_primitive_ellipsoid((0, -0.012, 1.392), (0.135, 0.078, 0.055)))   # trapezius
    parts.append(_primitive_ellipsoid((0, 0.004, 1.105), (0.150, 0.103, 0.150)))    # abdomen
    parts.append(_primitive_ellipsoid((0, -0.008, 0.958), (0.166, 0.113, 0.118)))   # pelvis
    parts.append(_primitive_ellipsoid((0, 0.012, 1.658), (0.079, 0.096, 0.113)))    # head
    parts += _primitive_capsule((0, 0.004, 1.400), (0, 0.012, 1.552), 0.058, 0.050)  # neck

    forward = math.cos(ARM_ANGLE)
    down = math.sin(ARM_ANGLE)
    for sign in (-1, 1):
        joint = Vector((sign * SHOULDER_JOINT[0], 0.0, SHOULDER_JOINT[2]))
        direction = Vector((sign * forward, 0.0, -down))
        elbow = joint + direction * 0.290
        wrist = elbow + direction * 0.262
        parts.append(_primitive_ellipsoid(joint + Vector((sign * 0.008, 0, -0.012)),
                                          (0.060, 0.058, 0.060)))   # deltoid
        parts += _primitive_capsule(joint, elbow, 0.049, 0.041)
        parts += _primitive_capsule(elbow, wrist, 0.040, 0.030)
        parts.append(_primitive_ellipsoid(wrist + direction * 0.085, (0.034, 0.052, 0.048)))
        parts += _primitive_capsule((sign * 0.098, 0, 0.900), (sign * 0.106, 0.006, 0.470), 0.082, 0.056)
        parts += _primitive_capsule((sign * 0.106, 0.006, 0.470), (sign * 0.108, 0.0, 0.085), 0.055, 0.038)
        parts.append(_primitive_ellipsoid((sign * 0.108, 0.058, 0.043), (0.045, 0.125, 0.043)))

    bpy.ops.object.select_all(action="DESELECT")
    for part in parts:
        part.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    body = bpy.context.object
    body.name = BODY_NAME
    body.data.name = "FIT_BODY_MESH"
    move_to_collection(body, target)
    # Join keeps the first part's origin, and BVHTree.FromObject builds in object
    # space, not world space - so without this the clearance queries below would
    # silently miss the body by the height of that origin.
    activate(body)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    # Voxel remesh unions the overlapping primitives into one closed surface, so
    # the cloth solver sees a single smooth body instead of intersecting shells.
    remesh = body.modifiers.new("body-union", "REMESH")
    set_enum(remesh, "mode", "VOXEL")
    remesh.voxel_size = 0.007
    remesh.adaptivity = 0.0
    activate(body)
    bpy.ops.object.modifier_apply(modifier=remesh.name)

    smooth = body.modifiers.new("body-smooth", "SMOOTH")
    smooth.factor = 0.6
    smooth.iterations = 6
    bpy.ops.object.modifier_apply(modifier=smooth.name)

    decimate = body.modifiers.new("body-decimate", "DECIMATE")
    decimate.ratio = 0.35
    bpy.ops.object.modifier_apply(modifier=decimate.name)

    for polygon in body.data.polygons:
        polygon.use_smooth = True
    body.data.materials.append(simple_material("MAT_FittingBody_Clay", (0.126, 0.118, 0.110), 0.78))
    body["purpose"] = "A-pose fitting body and review mannequin; never exported"
    log(f"fitting body: {len(body.data.polygons)} faces")
    measure_body(body)
    return body


def measure_body(body):
    """Report the body's own torso cross-sections; the garment fit depends on them.

    Measured by casting outwards from the body's centre line, because a plain
    bounding slab at chest height would measure the arms, not the chest.
    """
    tree = body_bvh(body)
    for label, z in (("neck base", 1.450), ("shoulder", 1.400), ("chest", 1.290),
                     ("waist", 1.075), ("hip", 0.965)):
        spans = {}
        for axis, direction in (("width", Vector((1, 0, 0))), ("depth", Vector((0, 1, 0)))):
            hit, _, _, distance = tree.ray_cast(Vector((0.0, 0.0, z)), direction)
            spans[axis] = distance if hit is not None else float("nan")
        log(f"  body {label} z={z}: half width {spans['width']:.3f} m, "
            f"half depth {spans['depth']:.3f} m")


# ------------------------------------------------------------ pattern geometry

def _polyline(points):
    return np.asarray(points, dtype=np.float64)


def _arc_lengths(points):
    deltas = np.linalg.norm(np.diff(points, axis=0), axis=1)
    return np.concatenate([[0.0], np.cumsum(deltas)])


def resample(points, count):
    """Even arc-length resampling, endpoints preserved."""
    lengths = _arc_lengths(points)
    targets = np.linspace(0.0, lengths[-1], count)
    out = np.empty((count, 2))
    for axis in (0, 1):
        out[:, axis] = np.interp(targets, lengths, points[:, axis])
    return out


def _curve(function, samples=240):
    t = np.linspace(0.0, 1.0, samples)
    return _polyline([function(value) for value in t])


def body_panel_segments(front):
    """Canonical pattern segments for the front or back body panel.

    Pattern coordinates are 'as seen from outside the garment': x to the
    viewer's right, y up, origin at the centre-front high point of shoulder.
    """
    drop = FRONT_NECK_DROP if front else BACK_NECK_DROP
    segments = {}
    # Neckline: elliptical quarter arcs meeting the shoulder seam vertically.
    segments["neck"] = _curve(lambda t: (
        NECK_HALF * math.sin(math.pi * (t - 0.5)),
        -drop * math.cos(math.pi * (t - 0.5)),
    ))
    for sign, tag in ((-1.0, "L"), (1.0, "R")):
        segments[f"shoulder_{tag}"] = _curve(lambda t, s=sign: (
            s * (NECK_HALF + (SHOULDER_X - NECK_HALF) * t),
            -SHOULDER_DROP * t - 0.004 * math.sin(math.pi * t),   # slight shoulder curve
        ), 60)
        segments[f"armhole_{tag}"] = _curve(lambda t, s=sign: (
            s * (SHOULDER_X + (BODY_HALF - SHOULDER_X) * t - 0.010 * math.sin(math.pi * t)),
            -SHOULDER_DROP + (UNDERARM_Y + SHOULDER_DROP) * t,
        ), 120)
        segments[f"side_{tag}"] = _curve(lambda t, s=sign: (
            s * BODY_HALF,
            UNDERARM_Y + (HEM_Y - UNDERARM_Y) * t,
        ), 120)
    segments["hem"] = _curve(lambda t: (-BODY_HALF + 2 * BODY_HALF * t, HEM_Y), 200)
    return segments


def sleeve_half_segments():
    """One half of the sleeve: top fold line, cuff, underarm seam, cap curve."""
    segments = {}
    segments["top"] = _curve(lambda t: (0.0, -SLEEVE_LEN * t), 80)
    segments["cuff"] = _curve(lambda t: (CUFF_HALF * t, -SLEEVE_LEN), 80)
    segments["underarm"] = _curve(lambda t: (
        CUFF_HALF + (CAP_W - CUFF_HALF) * t,
        -SLEEVE_LEN + (SLEEVE_LEN - CAP_H) * t,
    ), 60)
    # Cap runs underarm -> peak; shallow, as a dropped shoulder demands.
    segments["cap"] = _curve(lambda t: (
        CAP_W * (1.0 - t),
        -CAP_H * (1.0 - t) ** 1.6,
    ), 200)
    return segments


BODY_LOOP = (
    ("shoulder_L", False), ("armhole_L", False), ("side_L", False), ("hem", False),
    ("side_R", True), ("armhole_R", True), ("shoulder_R", True), ("neck", True),
)
SLEEVE_LOOP = (("top", False), ("cuff", False), ("underarm", False), ("cap", False))

SEGMENT_SPACING = {
    "neck": 0.013, "shoulder": 0.016, "armhole": 0.017, "side": 0.024, "hem": 0.021,
    "top": 0.016, "cuff": 0.013, "underarm": 0.015, "cap": 0.017,
}


def spacing_for(name):
    return SEGMENT_SPACING[name.split("_")[0]]


def point_in_polygon(points, polygon):
    """Vectorised even-odd test for many points against one closed polygon."""
    x, y = points[:, 0], points[:, 1]
    inside = np.zeros(len(points), dtype=bool)
    x0, y0 = polygon[:, 0], polygon[:, 1]
    x1, y1 = np.roll(x0, -1), np.roll(y0, -1)
    for ax, ay, bx, by in zip(x0, y0, x1, y1):
        if ay == by:
            continue
        crosses = ((ay > y) != (by > y))
        if not crosses.any():
            continue
        t = (y - ay) / (by - ay)
        inside ^= crosses & (x < ax + t * (bx - ax))
    return inside


def distance_to_polyline(points, polyline, want_along=False):
    """Minimum distance from each point to a polyline, optionally with arc length."""
    best = np.full(len(points), 1e9)
    along = np.zeros(len(points))
    lengths = _arc_lengths(polyline)
    for index in range(len(polyline) - 1):
        a = polyline[index]
        b = polyline[index + 1]
        ab = b - a
        denom = float(ab @ ab)
        if denom < 1e-14:
            continue
        t = np.clip(((points - a) @ ab) / denom, 0.0, 1.0)
        closest = a + t[:, None] * ab
        distance = np.linalg.norm(points - closest, axis=1)
        closer = distance < best
        best = np.where(closer, distance, best)
        if want_along:
            along = np.where(closer, lengths[index] + t * math.sqrt(denom), along)
    return (best, along) if want_along else best


def hex_interior(polygon, spacing_fn, boundary):
    """Interior sample points on a hex lattice with region-dependent spacing."""
    ymin, ymax = polygon[:, 1].min(), polygon[:, 1].max()
    xmin, xmax = polygon[:, 0].min(), polygon[:, 0].max()
    rows = []
    y = ymin
    row_index = 0
    while y <= ymax:
        step = spacing_fn(y)
        xs = np.arange(xmin, xmax + step, step)
        if row_index % 2:
            xs = xs + step * 0.5
        rows.append(np.stack([xs, np.full_like(xs, y)], axis=1))
        y += step * 0.866
        row_index += 1
    points = np.concatenate(rows, axis=0)
    inside = point_in_polygon(points, polygon)
    points = points[inside]
    clearance = distance_to_polyline(points, boundary)
    keep = clearance > np.array([spacing_fn(p[1]) for p in points]) * 0.62
    return points[keep]



def build_piece(segments, loop, spacing_fn, counts):
    """Mesh one flat pattern piece; returns 2-D verts, faces and seam indices.

    Seam index lists are always returned in each segment's canonical direction,
    so a pair of sewn segments can be zipped together vertex for vertex.
    """
    boundary = []
    traversal = {}
    for name, reverse in loop:
        points = resample(segments[name], counts[name])
        if reverse:
            points = points[::-1]
        indices = list(range(len(boundary), len(boundary) + len(points) - 1))
        boundary.extend(points[:-1])
        traversal[name] = indices
    order = [name for name, _ in loop]
    seam_slices = {}
    for position, (name, reverse) in enumerate(loop):
        following = order[(position + 1) % len(order)]
        full = traversal[name] + [traversal[following][0]]
        seam_slices[name] = full[::-1] if reverse else full

    boundary = np.asarray(boundary)
    closed = np.vstack([boundary, boundary[:1]])
    interior = hex_interior(boundary, spacing_fn, closed)
    coords = [Vector(p) for p in boundary] + [Vector(p) for p in interior]
    face = [list(range(len(boundary)))]
    result = delaunay_2d_cdt(coords, [], face, 1, 1e-6, True)
    if not result[2]:
        face = [list(reversed(face[0]))]
        result = delaunay_2d_cdt(coords, [], face, 1, 1e-6, True)
    verts_out, _, faces_out, orig_verts, _, _ = result
    if not faces_out:
        raise RuntimeError("constrained triangulation produced no faces")

    remap = {}
    for new_index, originals in enumerate(orig_verts):
        for original in originals:
            remap[original] = new_index
    verts = np.array([[v.x, v.y] for v in verts_out])
    faces = []
    for polygon in faces_out:
        for k in range(1, len(polygon) - 1):
            faces.append((polygon[0], polygon[k], polygon[k + 1]))
    seams = {name: [remap[i] for i in indices] for name, indices in seam_slices.items()}
    return verts, faces, seams

def seam_counts():
    """Matched vertex counts so every sewn pair of segments lines up 1:1."""
    body_front = body_panel_segments(True)
    body_back = body_panel_segments(False)
    sleeve = sleeve_half_segments()

    def count(points, name):
        length = _arc_lengths(points)[-1]
        return max(3, int(round(length / spacing_for(name))) + 1)

    counts = {"front": {}, "back": {}, "sleeve": {}}
    for name, points in body_front.items():
        counts["front"][name] = count(points, name)
    for name, points in body_back.items():
        counts["back"][name] = count(points, name)
    for name, points in sleeve.items():
        counts["sleeve"][name] = count(points, name)

    for tag, other in (("L", "R"), ("R", "L")):
        for base in ("shoulder", "armhole", "side"):
            pair = max(counts["front"][f"{base}_{tag}"], counts["back"][f"{base}_{other}"])
            counts["front"][f"{base}_{tag}"] = pair
            counts["back"][f"{base}_{other}"] = pair
    cap = max(counts["sleeve"]["cap"], counts["front"]["armhole_L"], counts["back"]["armhole_R"])
    counts["sleeve"]["cap"] = cap
    for tag in ("L", "R"):
        counts["front"][f"armhole_{tag}"] = cap
        counts["back"][f"armhole_{tag}"] = cap
    return body_front, body_back, sleeve, counts


# --------------------------------------------------- pattern -> initial 3-D fit

class TorsoWrap:
    """Lays a flat body panel onto the fitting body, preserving arc length.

    The pattern's vertical distance below the high point of shoulder is walked
    over a shoulder roll and then straight down the body, and its horizontal
    distance is walked around the cross-section at that height.  Because both
    are walked as arc lengths, the panel starts the simulation at very nearly
    the size it was cut, instead of being stretched into position - which is
    what previously forced the neckline open and let it ride up over the neck.
    """

    HALF_WIDTH = 0.250

    def __init__(self, front):
        self.front = front
        self.roll = 0.085 if front else 0.075          # how sharply it turns over the shoulder
        self.settled_depth = 0.115 if front else 0.112  # half depth once it hangs on the body

    def profile(self, s):
        """Centre-line depth and drop, s metres of fabric below the shoulder."""
        quarter = self.roll * math.pi / 2
        if s <= quarter:
            theta = s / self.roll
            return self.roll * math.sin(theta), self.roll * (1.0 - math.cos(theta))
        extra = s - quarter
        depth = self.roll + (self.settled_depth - self.roll) * float(smoothstep(0.0, 0.20, extra))
        return depth, self.roll + extra

    def __call__(self, px, py):
        depth, drop = self.profile(max(0.0, -py))
        a, b = self.HALF_WIDTH, max(depth, 1e-4)
        phi = np.linspace(0.0, math.pi / 2, 160)
        dx, dy = a * np.cos(phi), -b * np.sin(phi)
        step = np.sqrt(dx * dx + dy * dy)
        arc = np.concatenate([[0.0], np.cumsum((step[1:] + step[:-1]) * 0.5 * np.diff(phi))])
        target = abs(px)
        if target <= arc[-1]:
            angle = float(np.interp(target, arc, phi))
            x, y = a * math.sin(angle), b * math.cos(angle)
            overhang = 0.0
        else:
            # Past the side of the body the fabric carries on outwards over the
            # arm, and falls as it goes: a dropped shoulder rests on the arm
            # rather than bridging to it in mid air.
            overhang = target - arc[-1]
            x, y = a + overhang, 0.0
        side = 1.0 if px >= 0 else -1.0
        z = HPS_Z - drop - 0.62 * overhang
        if self.front:
            return Vector((-side * x, y, z))
        return Vector((side * x, -y, z))


def sleeve_frame(sigma):
    forward = math.cos(ARM_ANGLE)
    down = math.sin(ARM_ANGLE)
    direction = Vector((sigma * forward, 0.0, -down))
    up = Vector((sigma * down, 0.0, forward))
    joint = Vector((sigma * SHOULDER_JOINT[0], SHOULDER_JOINT[1], SHOULDER_JOINT[2]))
    return joint, direction, up


def sleeve_world(sigma, half, px, py):
    joint, direction, up = sleeve_frame(sigma)
    forward_axis = Vector((0.0, half, 0.0))
    t = -py
    if t <= CAP_H:
        width = CAP_W
    else:
        width = CAP_W + (CUFF_HALF - CAP_W) * (t - CAP_H) / (SLEEVE_LEN - CAP_H)
    radius = max(width / math.pi, 0.058)
    theta = math.pi * min(abs(px) / max(width, 1e-6), 1.0)
    axis = joint + direction * (SLEEVE_START + t) - up * 0.012
    return axis + (math.cos(theta) * up + math.sin(theta) * forward_axis) * radius


def build_pattern_garment(body):
    """Create the flat panels, place them around the body, add sewing springs."""
    front_segments, back_segments, sleeve_segments, counts = seam_counts()

    def body_spacing(y):
        return 0.021 + (0.031 - 0.021) * float(smoothstep(-0.26, -0.40, y))

    def sleeve_spacing(_y):
        return 0.020

    front_verts, front_faces, front_seams = build_piece(
        front_segments, BODY_LOOP, body_spacing, counts["front"])
    back_verts, back_faces, back_seams = build_piece(
        back_segments, BODY_LOOP, body_spacing, counts["back"])
    sleeve_verts, sleeve_faces, sleeve_seams = build_piece(
        sleeve_segments, SLEEVE_LOOP, sleeve_spacing, counts["sleeve"])

    front_wrap, back_wrap = TorsoWrap(True), TorsoWrap(False)
    pieces = []
    pieces.append(dict(name="front", verts=front_verts, faces=front_faces, seams=front_seams,
                       place=lambda p: front_wrap(p[0], p[1]), island="front"))
    pieces.append(dict(name="back", verts=back_verts, faces=back_faces, seams=back_seams,
                       place=lambda p: back_wrap(p[0], p[1]), island="back"))
    # piece order fixes the face attribute ids; the UV layout is applied later
    for sigma, side in ((1.0, "R"), (-1.0, "L")):
        for half, tag in ((1.0, "f"), (-1.0, "b")):
            pieces.append(dict(
                name=f"sleeve{side}_{tag}", verts=sleeve_verts, faces=sleeve_faces,
                seams=sleeve_seams, island=f"sleeve_{side}{tag}",
                place=lambda p, s=sigma, h=half: sleeve_world(s, h, p[0], p[1])))

    positions = []
    pattern = []
    faces = []
    face_piece = []
    offsets = {}
    piece_ids = {piece["island"]: index for index, piece in enumerate(pieces)}
    for piece in pieces:
        offset = len(positions)
        offsets[piece["name"]] = offset
        for coord in piece["verts"]:
            positions.append(piece["place"](coord))
            pattern.append((float(coord[0]), float(coord[1])))
        for triangle in piece["faces"]:
            faces.append(tuple(index + offset for index in triangle))
            face_piece.append(piece_ids[piece["island"]])

    # ------------------------------------------------------------ sewing edges
    sewing = set()

    spans = {}

    def sew(piece_a, seg_a, piece_b, seg_b, flip=False):
        """Pair two seam segments vertex for vertex, in matching directions."""
        indices_a = [i + offsets[piece_a] for i in
                     next(p for p in pieces if p["name"] == piece_a)["seams"][seg_a]]
        indices_b = [i + offsets[piece_b] for i in
                     next(p for p in pieces if p["name"] == piece_b)["seams"][seg_b]]
        if flip:
            indices_b = indices_b[::-1]
        if len(indices_a) != len(indices_b):
            raise RuntimeError(f"seam mismatch {piece_a}.{seg_a} ({len(indices_a)}) "
                               f"vs {piece_b}.{seg_b} ({len(indices_b)})")
        longest = 0.0
        for a, b in zip(indices_a, indices_b):
            if a != b:
                sewing.add((min(a, b), max(a, b)))
                longest = max(longest, (positions[a] - positions[b]).length)
        spans[f"{piece_a}.{seg_a}->{piece_b}.{seg_b}"] = longest

    for front_tag, back_tag, side in (("R", "L", "L"), ("L", "R", "R")):
        sew("front", f"shoulder_{front_tag}", "back", f"shoulder_{back_tag}")
        sew("front", f"side_{front_tag}", "back", f"side_{back_tag}")
        # the cap runs underarm -> peak, the armhole shoulder -> underarm, so one
        # of the two has to be flipped or the sleeve is sewn in with a half twist
        sew("front", f"armhole_{front_tag}", f"sleeve{side}_f", "cap", flip=True)
        sew("back", f"armhole_{back_tag}", f"sleeve{side}_b", "cap", flip=True)
    for side in ("L", "R"):
        sew(f"sleeve{side}_f", "top", f"sleeve{side}_b", "top")
        sew(f"sleeve{side}_f", "underarm", f"sleeve{side}_b", "underarm")

    # A seam that has to close a gap wider than the garment itself is a sign the
    # two segments were paired in opposite directions; catch that here, not in
    # the renders.
    worst = max(spans.items(), key=lambda item: item[1])
    for name, span in sorted(spans.items(), key=lambda item: -item[1]):
        log(f"  seam span {name}: {span:.3f} m")
    if worst[1] > 0.45:
        raise RuntimeError(f"seam {worst[0]} spans {worst[1]:.3f} m; "
                           "the segments are almost certainly paired backwards")

    mesh = bpy.data.meshes.new(f"{GARMENT_NAME}_MESH")
    mesh.from_pydata([tuple(p) for p in positions], sorted(sewing), faces)
    mesh.validate(verbose=False)
    mesh.update()

    garment = bpy.data.objects.new(GARMENT_NAME, mesh)
    collection("GARMENT").objects.link(garment)

    # Flat pattern coordinates travel with the mesh: they are the UV layout, the
    # texture's fabric space, and the reference the strain check measures against.
    attribute = mesh.attributes.new(name="pat", type="FLOAT2", domain="POINT")
    attribute.data.foreach_set("vector", np.asarray(pattern, dtype=np.float32).ravel())
    piece_attribute = mesh.attributes.new(name="piece", type="INT", domain="FACE")
    piece_attribute.data.foreach_set("value", np.asarray(face_piece, dtype=np.int32))
    garment["pieces"] = json.dumps([piece["island"] for piece in pieces])

    # A rib band is cut shorter than the neckline it is sewn to, and that is
    # what stops a crew neck gaping or riding up.  Modelling it as a shrinking
    # zone along the neck edge is both truer than pinning the ring in place and
    # stable: the neckline no longer depends on millimetres of body surface.
    neck_indices = []
    for piece_name in ("front", "back"):
        piece = next(p for p in pieces if p["name"] == piece_name)
        neck_indices += [index + offsets[piece_name] for index in piece["seams"]["neck"]]
    neck_indices = sorted(set(neck_indices))
    rib = garment.vertex_groups.new(name="neck_rib")
    rib.add(neck_indices, 1.0, "REPLACE")
    adjacency = {}
    for face in faces:
        for index in face:
            adjacency.setdefault(index, set()).update(face)
    second = {n for index in neck_indices for n in adjacency.get(index, ())} - set(neck_indices)
    rib.add(sorted(second), 0.45, "REPLACE")
    log(f"neck rib zone: {len(neck_indices)} edge + {len(second)} adjacent vertices")

    orient_faces_outward(garment, pieces, offsets)
    # No initial push out of the body here: the shoulder span deliberately
    # crosses the arms, and snapping it to the surface tears the panel.  The
    # solver resolves the initial interpenetration during the sewing phase,
    # and any residue is cleaned up after the simulation instead.
    log(f"pattern: {len(positions)} verts, {len(faces)} faces, {len(sewing)} sewing springs")
    return garment



def orient_faces_outward(garment, pieces, offsets):
    """Flip any face whose normal points at the body rather than away from it."""
    mesh = garment.data
    ranges = []
    for piece in pieces:
        start = offsets[piece["name"]]
        ranges.append((start, start + len(piece["verts"]), piece["name"]))

    def outward_at(index, position):
        for start, end, name in ranges:
            if start <= index < end:
                if name.startswith("sleeve"):
                    sigma = 1.0 if name.startswith("sleeveR") else -1.0
                    joint, direction, _ = sleeve_frame(sigma)
                    along = (position - joint).dot(direction)
                    return position - (joint + direction * along)
                return Vector((position.x, position.y, 0.0))
        return Vector((0.0, 0.0, 1.0))

    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.faces.ensure_lookup_table()
    flip = []
    for face in bm.faces:
        reference = outward_at(face.verts[0].index, face.calc_center_median())
        if reference.length > 1e-9 and face.normal.dot(reference.normalized()) < 0.0:
            flip.append(face)
    if flip:
        bmesh.ops.reverse_faces(bm, faces=flip)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    log(f"oriented {len(flip)} faces outward")

def body_bvh(body):
    """BVH of the fitting body.

    BVHTree.FromObject works in object space, so this is only valid because the
    body's transform is applied when it is built; assert that rather than trust it.
    """
    if body.matrix_world != Matrix.Identity(4):
        raise RuntimeError("the fitting body carries a transform; its BVH would be offset")
    return BVHTree.FromObject(body, bpy.context.evaluated_depsgraph_get())


def push_out_of_body(garment, body, clearance=0.010):
    tree = body_bvh(body)
    mesh = garment.data
    moved = 0
    for vertex in mesh.vertices:
        location, normal, _, distance = tree.find_nearest(vertex.co)
        if location is None:
            continue
        outward = (vertex.co - location)
        inside = outward.dot(normal) < 0.0
        if inside or distance < clearance:
            vertex.co = location + normal * clearance
            moved += 1
    mesh.update()
    if moved:
        log(f"pushed {moved} vertices clear of the fitting body")


# ------------------------------------------------------------------ simulation

def simulate(garment, body, frames=170):
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = frames

    body.modifiers.new("collision", "COLLISION")
    body.collision.thickness_outer = 0.006
    body.collision.thickness_inner = 0.020
    body.collision.cloth_friction = 14.0
    body.collision.damping = 0.35

    modifier = garment.modifiers.new("cloth", "CLOTH")
    settings = modifier.settings
    settings.quality = 12
    settings.mass = 0.30                      # heavyweight jersey
    settings.air_damping = 1.4
    set_enum(settings, "bending_model", "ANGULAR")
    # Stiff in plane, so the panels keep the dimensions they were cut to, and
    # only moderately stiff in bending, so the excess drapes in broad folds.
    settings.tension_stiffness = 85.0
    settings.compression_stiffness = 60.0
    settings.shear_stiffness = 50.0
    settings.bending_stiffness = 4.0
    settings.tension_damping = 8.0
    settings.compression_damping = 8.0
    settings.shear_damping = 8.0
    settings.bending_damping = 0.8
    settings.use_sewing_springs = True
    settings.sewing_force_max = 0.0

    collision = modifier.collision_settings
    collision.use_collision = True
    collision.distance_min = 0.005
    collision.collision_quality = 5
    # Without this the back panel passes through itself across the shoulders.
    collision.use_self_collision = True
    collision.self_distance_min = 0.0035

    cache = modifier.point_cache
    cache.frame_start = 1
    cache.frame_end = frames

    if "neck_rib" in garment.vertex_groups:
        settings.vertex_group_shrink = "neck_rib"
        settings.shrink_min = 0.0
        # 9% is not arbitrary: below about 8% the neck opening is loose enough that
        # the yoke can lift over the neck instead of settling on the shoulders.
        settings.shrink_max = 0.09

    # Seams close first in zero gravity, then the garment is allowed to fall and
    # settle on the shoulders; otherwise the panels drop before they are sewn.
    path = f'modifiers["{modifier.name}"].settings.effector_weights.gravity'
    settings.effector_weights.gravity = 0.0
    garment.keyframe_insert(path, frame=1)
    garment.keyframe_insert(path, frame=26)
    settings.effector_weights.gravity = 1.0
    garment.keyframe_insert(path, frame=48)

    log(f"simulating {frames} frames")
    for frame in range(1, frames + 1):
        scene.frame_set(frame)
        if frame % 20 == 0:
            log(f"  frame {frame}/{frames}")
    activate(garment)
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    garment.animation_data_clear()
    body.modifiers.clear()
    log("simulation applied")



def strain_report(garment):
    """How far the simulated cloth has stretched from the flat pattern.

    The panels were cut to measured dimensions, so anything beyond a few per
    cent means the solver is stretching the garment rather than draping it.
    """
    mesh = garment.data
    pattern = np.empty(len(mesh.vertices) * 2, dtype=np.float32)
    mesh.attributes["pat"].data.foreach_get("vector", pattern)
    pattern = pattern.reshape(-1, 2)
    face_edges = set()
    for polygon in mesh.polygons:
        for key in polygon.edge_keys:
            face_edges.add(tuple(sorted(key)))
    strains = []
    face_edges = sorted(face_edges)
    for a, b in face_edges:
        flat = float(np.linalg.norm(pattern[a] - pattern[b]))
        if flat < 1e-5:
            continue
        current = (mesh.vertices[a].co - mesh.vertices[b].co).length
        strains.append(current / flat - 1.0)
    strains = np.array(strains)
    report = dict(mean=round(float(strains.mean()), 4),
                  p95=round(float(np.quantile(strains, 0.95)), 4),
                  max=round(float(strains.max()), 4))
    log(f"cloth strain vs flat pattern: {report}")
    worst = np.argsort(strains)[-4:][::-1]
    keys = list(face_edges)
    for rank in worst:
        a, b = keys[rank]
        mid = (mesh.vertices[a].co + mesh.vertices[b].co) / 2
        log(f"  worst strain {strains[rank]:+.2f} at pattern {pattern[a].round(3)} "
            f"world ({mid.x:.2f}, {mid.y:.2f}, {mid.z:.2f})")
    return report


def seam_gap_report(garment, sewing_pairs):
    """Residual distance across each sewing spring, just before welding."""
    mesh = garment.data
    gaps = np.array([(mesh.vertices[a].co - mesh.vertices[b].co).length
                     for a, b in sewing_pairs])
    report = dict(mean=round(float(gaps.mean()), 4), max=round(float(gaps.max()), 4))
    log(f"seam gaps before welding: {report}")
    if report["max"] > 0.030:
        worst = int(np.argmax(gaps))
        a, b = sewing_pairs[worst]
        location = (mesh.vertices[a].co + mesh.vertices[b].co) / 2
        raise RuntimeError(f"a seam is still {report['max']:.3f} m open at "
                           f"({location.x:.2f}, {location.y:.2f}, {location.z:.2f}); "
                           "the sewing springs did not close it")
    return report


def weld_seams(garment):
    """Merge each sewn pair into one vertex and drop the sewing springs."""
    mesh = garment.data
    parent = list(range(len(mesh.vertices)))

    def find(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    face_edges = set()
    for polygon in mesh.polygons:
        for key in polygon.edge_keys:
            face_edges.add(tuple(sorted(key)))
    sewing_edges = [tuple(sorted(edge.vertices)) for edge in mesh.edges
                    if tuple(sorted(edge.vertices)) not in face_edges]
    for a, b in sewing_edges:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    groups = {}
    for index in range(len(mesh.vertices)):
        groups.setdefault(find(index), []).append(index)

    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    targetmap = {}
    for members in groups.values():
        if len(members) < 2:
            continue
        centre = Vector((0.0, 0.0, 0.0))
        for index in members:
            centre += bm.verts[index].co
        centre /= len(members)
        keeper = bm.verts[members[0]]
        keeper.co = centre
        for index in members[1:]:
            targetmap[bm.verts[index]] = keeper
    if targetmap:
        bmesh.ops.weld_verts(bm, targetmap=targetmap)
    stray = [edge for edge in bm.edges if not edge.link_faces]
    if stray:
        bmesh.ops.delete(bm, geom=stray, context="EDGES")
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    log(f"welded {len(sewing_edges)} seam springs -> {len(mesh.vertices)} verts")

def relax_surface(garment, iterations=2, factor=0.22):
    """Take the numerical fizz off the simulated surface, keeping the openings."""
    mesh = garment.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    interior = [v for v in bm.verts if not v.is_boundary]
    for _ in range(iterations):
        bmesh.ops.smooth_vert(bm, verts=interior, factor=factor,
                              use_axis_x=True, use_axis_y=True, use_axis_z=True)
    boundary = [v for v in bm.verts if v.is_boundary]
    for _ in range(2):
        bmesh.ops.smooth_vert(bm, verts=boundary, factor=0.25,
                              use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()


def hang_report(garment):
    """Where the hem actually falls, against the length the pattern was cut to."""
    coordinates = np.empty(len(garment.data.vertices) * 3, dtype=np.float32)
    garment.data.vertices.foreach_get("co", coordinates)
    coordinates = coordinates.reshape(-1, 3)
    hem = float(coordinates[:, 2].min())
    drop = HPS_Z - hem
    # In an A-pose the sleeve rests on a raised arm and lifts the top of the
    # side seam with it; record where the underarm actually ends up.
    pattern = np.empty(len(garment.data.vertices) * 2, dtype=np.float32)
    garment.data.attributes["pat"].data.foreach_get("vector", pattern)
    pattern = pattern.reshape(-1, 2)
    underarm = np.hypot(np.abs(pattern[:, 0]) - BODY_HALF, pattern[:, 1] - UNDERARM_Y) < 0.02
    underarm_z = float(coordinates[underarm, 2].mean()) if underarm.any() else float("nan")
    lift = underarm_z - (HPS_Z + UNDERARM_Y)
    log(f"hang: hem at z {hem:.3f}, {drop:.3f} m below the shoulder (pattern length "
        f"{-HEM_Y:.3f} m); underarm at z {underarm_z:.3f}, lifted {lift:.3f} m by the A-pose arm")
    return dict(hem_z=round(hem, 4), drop_m=round(drop, 4), pattern_length_m=-HEM_Y,
                underarm_z=round(underarm_z, 4), underarm_lift_m=round(lift, 4))


def neckline_report(garment):
    loops, positions, _ = boundary_loops(garment.data)
    neck = max(loops, key=lambda loop: np.mean([positions[i].z for i in loop]))
    zs = [positions[i].z for i in neck]
    span = (min(zs), max(zs))
    log(f"neckline: {len(neck)} verts, z {span[0]:.3f}..{span[1]:.3f}")
    if span[1] > HPS_Z + 0.045:
        raise RuntimeError(f"neckline rode up to z={span[1]:.3f}; it has hooked on the body")
    return span


def despike(garment, threshold=0.011, strength=0.6, passes=2):
    """Flatten the few vertices left standing proud of their neighbours.

    Where four seams converge - the corner of a shoulder seam and the neckline -
    welding can leave one vertex folded, which shows as a small hard shard once
    the cloth is given thickness.  The threshold is well above the curvature of
    an ordinary fold, so this pulls those few vertices back in without touching
    the drape, which is the simulation's to decide.
    """
    mesh = garment.data
    neighbours = {}
    for edge in mesh.edges:
        a, b = edge.vertices
        neighbours.setdefault(a, set()).add(b)
        neighbours.setdefault(b, set()).add(a)
    flattened = 0
    for _ in range(passes):
        moves = {}
        for vertex in mesh.vertices:
            linked = neighbours.get(vertex.index)
            if not linked or len(linked) < 3:
                continue
            average = Vector((0, 0, 0))
            for other in linked:
                average += mesh.vertices[other].co
            average /= len(linked)
            offset = vertex.co - average
            if offset.length > threshold:
                moves[vertex.index] = average + offset.normalized() * threshold
        for index, target in moves.items():
            mesh.vertices[index].co = mesh.vertices[index].co.lerp(target, strength)
        flattened += len(moves)
    mesh.update()
    log(f"despiked {flattened} vertices standing proud of their neighbours")


def finish_simulation(garment, body):
    mesh = garment.data
    face_edges = set()
    for polygon in mesh.polygons:
        for key in polygon.edge_keys:
            face_edges.add(tuple(sorted(key)))
    sewing_pairs = [tuple(sorted(edge.vertices)) for edge in mesh.edges
                    if tuple(sorted(edge.vertices)) not in face_edges]
    measurements = dict(strain=strain_report(garment),
                        seam_gaps=seam_gap_report(garment, sewing_pairs))
    garment["measurements"] = json.dumps(measurements)
    weld_seams(garment)
    relax_surface(garment)
    despike(garment)
    push_out_of_body(garment, body, clearance=0.004)
    garment.data.calc_loop_triangles()
    neckline_report(garment)
    garment["hang"] = json.dumps(hang_report(garment))


# ---------------------------------------------------------------- collar rib

def boundary_loops(mesh):
    bm = bmesh.new()
    bm.from_mesh(mesh)
    edges = [e for e in bm.edges if e.is_boundary]
    remaining = {e.index: e for e in edges}
    loops = []
    while remaining:
        _, edge = remaining.popitem()
        loop = [edge.verts[0].index, edge.verts[1].index]
        current = edge.verts[1]
        while True:
            following = None
            for candidate in current.link_edges:
                if candidate.index in remaining and candidate.is_boundary:
                    following = candidate
                    break
            if following is None:
                break
            del remaining[following.index]
            current = following.other_vert(current)
            if current.index == loop[0]:
                break
            loop.append(current.index)
        loops.append(loop)
    positions = {v.index: v.co.copy() for v in bm.verts}
    normals = {v.index: v.normal.copy() for v in bm.verts}
    bm.free()
    return loops, positions, normals


def resample_closed(points, count):
    closed = np.vstack([points, points[:1]])
    lengths = _arc_lengths(closed)
    targets = np.linspace(0.0, lengths[-1], count, endpoint=False)
    out = np.empty((count, 3))
    for axis in range(3):
        out[:, axis] = np.interp(targets, lengths, closed[:, axis])
    return out, lengths[-1]


def snap_neckline_to(garment, loop_indices, samples):
    """Pull the simulated neck edge onto the smoothed path the collar follows.

    The band is swept along a smoothed curve, so a few millimetres of simulated
    waviness in the edge itself would leave the raw edge poking through the rib.
    Moving the edge onto the same curve keeps the two exactly in register, and
    tidies the neckline at the same time.
    """
    mesh = garment.data
    closed = np.vstack([samples, samples[:1]])
    moved = 0.0
    deltas = {}
    for index in loop_indices:
        point = np.array(mesh.vertices[index].co)
        best, closest = 1e9, point
        for a, b in zip(closed[:-1], closed[1:]):
            segment = b - a
            denominator = float(segment @ segment)
            if denominator < 1e-12:
                continue
            t = float(np.clip(((point - a) @ segment) / denominator, 0.0, 1.0))
            candidate = a + t * segment
            distance = float(np.linalg.norm(point - candidate))
            if distance < best:
                best, closest = distance, candidate
        deltas[index] = Vector(closest - point)
        moved = max(moved, best)
    for index, delta in deltas.items():
        mesh.vertices[index].co = Vector(np.array(mesh.vertices[index].co) + delta)

    neighbours = {}
    for edge in mesh.edges:
        a, b = edge.vertices
        neighbours.setdefault(a, set()).add(b)
        neighbours.setdefault(b, set()).add(a)
    ring = {n for index in deltas for n in neighbours.get(index, ())} - set(deltas)
    ring |= {n for index in ring for n in neighbours.get(index, ())} - set(deltas)
    # feather the correction, then settle the ring behind the edge: a small fold
    # left there pokes out through the rib band
    for index in ring:
        nearby = [deltas[n] for n in neighbours[index] if n in deltas]
        if nearby:
            average = Vector((0, 0, 0))
            for delta in nearby:
                average += delta
            mesh.vertices[index].co = mesh.vertices[index].co + average / len(nearby) * 0.35
    for _ in range(4):
        for index in ring:
            average = Vector((0, 0, 0))
            for other in neighbours[index]:
                average += mesh.vertices[other].co
            average /= len(neighbours[index])
            mesh.vertices[index].co = mesh.vertices[index].co.lerp(average, 0.4)
    mesh.update()
    log(f"neckline snapped to the collar path (max {moved * 1000:.1f} mm)")


def build_collar(garment):
    """A substantial ribbed crew band following the settled neckline.

    The band is framed against the neck axis rather than against interpolated
    surface normals, which flip where the simulated edge is wavy, and the loop
    is smoothed with a Taubin pass so it does not shrink away from the neckline
    it is supposed to sit on.
    """
    mesh = garment.data
    loops, positions, _ = boundary_loops(mesh)
    if not loops:
        raise RuntimeError("no open boundary found for the collar")
    neck = max(loops, key=lambda loop: np.mean([positions[i].z for i in loop]))
    raw = np.array([[*positions[i]] for i in neck])

    samples, _ = resample_closed(raw, 56)
    for _ in range(6):   # Taubin: shrink, then push back out by the same measure
        for weight in (0.52, -0.54):
            neighbours = (np.roll(samples, 1, axis=0) + np.roll(samples, -1, axis=0)) * 0.5
            samples = samples + weight * (neighbours - samples)
    centre = samples.mean(axis=0)
    length = float(sum(np.linalg.norm(samples[(i + 1) % len(samples)] - samples[i])
                       for i in range(len(samples))))

    start_index = int(np.argmin(samples[:, 1]))   # seam and UV start at centre back
    samples = np.roll(samples, -start_index, axis=0)
    snap_neckline_to(garment, neck, samples)

    # Profile of the rib band, in (along the band, through its thickness) metres.
    # It starts just below the neckline edge so the raw edge is enclosed.
    # The mouth of the band is deliberately wider than the cloth is thick: it has
    # to swallow the neckline edge and the millimetre or two of simulated
    # waviness around it, or the shirt surface escapes through the rib.
    profile = [
        (-0.0090, 0.0034), (0.0030, 0.0020), (0.0120, 0.0016), (0.0175, 0.0007),
        (0.0190, -0.0018), (0.0175, -0.0042), (0.0030, -0.0048), (-0.0090, -0.0060),
    ]
    profile_lengths = _arc_lengths(_polyline(profile + profile[:1]))

    # A band this wide folds through itself where the neckline turns tighter
    # than the band is deep, which is what puts shards in the neck opening.
    # Narrow it slightly through the tightest turns instead.
    count = len(samples)
    span = max(a for a, _ in profile) - min(a for a, _ in profile)
    radii = []
    for index in range(count):
        a, b, c = samples[index - 1], samples[index], samples[(index + 1) % count]
        area = 0.5 * float(np.linalg.norm(np.cross(b - a, c - a)))
        if area < 1e-9:
            radii.append(1e3)
            continue
        sides = (np.linalg.norm(b - a), np.linalg.norm(c - b), np.linalg.norm(a - c))
        radii.append(float(sides[0] * sides[1] * sides[2] / (4.0 * area)))
    radii = np.array(radii)
    for _ in range(3):
        radii = (np.roll(radii, 1) + 2.0 * radii + np.roll(radii, -1)) / 4.0
    width_scale = np.clip(radii / (1.35 * span), 0.45, 1.0)
    for _ in range(4):
        width_scale = (np.roll(width_scale, 1) + 2.0 * width_scale
                       + np.roll(width_scale, -1)) / 4.0
    log(f"collar band narrowed to {width_scale.min():.2f} of its width at the tightest turn")

    verts, pattern, arcs = [], [], []
    arc = 0.0
    for index in range(count):
        arcs.append(arc)
        arc += float(np.linalg.norm(samples[(index + 1) % count] - samples[index]))

    # Frames are carried around the loop by parallel transport rather than being
    # rebuilt at every section.  Rebuilding them twists the band sharply where
    # the neckline kinks at the shoulder seams, which pinches the tube and
    # notches the rib; transporting them keeps the sweep smooth, and the closing
    # twist is spread evenly around the loop.
    tangents = [(Vector(samples[(i + 1) % count]) - Vector(samples[i - 1])).normalized()
                for i in range(count)]

    def ideal_band(index):
        point = Vector(samples[index])
        radial = Vector((point.x - centre[0], point.y - centre[1], 0.0))
        radial = radial.normalized() if radial.length > 1e-6 else Vector((0, 1, 0))
        direction = (-radial + Vector((0, 0, 0.55))).normalized()
        return (direction - tangents[index] * direction.dot(tangents[index])).normalized()

    bands = [ideal_band(0)]
    for index in range(1, count):
        carried = tangents[index - 1].rotation_difference(tangents[index]) @ bands[-1]
        carried = (carried - tangents[index] * carried.dot(tangents[index])).normalized()
        # a light pull towards the ideal keeps the band upright without reintroducing the twist
        blended = (carried * 0.82 + ideal_band(index) * 0.18)
        blended = (blended - tangents[index] * blended.dot(tangents[index])).normalized()
        bands.append(blended)

    closing = tangents[-1].rotation_difference(tangents[0]) @ bands[-1]
    closing = (closing - tangents[0] * closing.dot(tangents[0])).normalized()
    residual = math.atan2(closing.cross(bands[0]).dot(tangents[0]), closing.dot(bands[0]))
    for index in range(count):
        correction = -residual * index / count
        bands[index] = (bands[index] @ __import__("mathutils").Matrix.Rotation(
            correction, 3, tangents[index])).normalized()

    for index in range(count):
        point = Vector(samples[index])
        band = bands[index]
        thickness = tangents[index].cross(band).normalized()
        radial = Vector((point.x - centre[0], point.y - centre[1], 0.0))
        if radial.length > 1e-6 and thickness.dot(radial.normalized()) < 0:
            thickness = -thickness
        for position, (along, through) in enumerate(profile):
            verts.append(point + band * (along * float(width_scale[index]))
                         + thickness * through)
            pattern.append((arcs[index], float(profile_lengths[position])))

    rings = len(profile)
    faces = []
    for index in range(count):
        following = (index + 1) % count
        for position in range(rings):
            nxt = (position + 1) % rings
            faces.append((index * rings + position, index * rings + nxt,
                          following * rings + nxt, following * rings + position))

    collar_mesh = bpy.data.meshes.new("ARTSCHOOL_COLLAR_MESH")
    collar_mesh.from_pydata([tuple(v) for v in verts], [], faces)
    collar_mesh.validate(verbose=False)
    collar_mesh.update()
    collar = bpy.data.objects.new("ARTSCHOOL_Collar_Rib", collar_mesh)
    collection("GARMENT").objects.link(collar)

    attribute = collar_mesh.attributes.new(name="pat", type="FLOAT2", domain="POINT")
    attribute.data.foreach_set("vector", np.asarray(pattern, dtype=np.float32).ravel())

    bm = bmesh.new()
    bm.from_mesh(collar_mesh)
    bm.faces.ensure_lookup_table()
    flip = []
    for face in bm.faces:
        ring_index = face.verts[0].index // rings
        outward = face.calc_center_median() - Vector(samples[ring_index])
        if outward.length > 1e-9 and face.normal.dot(outward.normalized()) < 0:
            flip.append(face)
    if flip:
        bmesh.ops.reverse_faces(bm, faces=flip)
    bm.to_mesh(collar_mesh)
    bm.free()

    log(f"collar: {count} sections, band length {length:.3f} m")
    return collar, length, float(profile_lengths[-1])


# -------------------------------------------------------- thickness and joining

def solidify_garment(garment, thickness=0.0026):
    garment.vertex_groups.new(name="shell")
    garment.vertex_groups.new(name="rim")
    modifier = garment.modifiers.new("cloth-thickness", "SOLIDIFY")
    modifier.thickness = thickness
    modifier.offset = -1.0
    modifier.use_rim = True
    modifier.use_rim_only = False
    # Even thickness divides the offset by the cosine of the fold angle, so a
    # sharp crease in simulated cloth throws the inner shell metres away and
    # leaves blades across the garment.  The cloth is a uniform 2.6 mm, so the
    # plain offset is both correct here and stable.  (thickness_clamp does not
    # help: it limits by edge length, not by the offset angle.)
    modifier.use_even_offset = False
    modifier.use_quality_normals = True
    modifier.shell_vertex_group = "shell"
    modifier.rim_vertex_group = "rim"
    activate(garment)
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    log(f"solidified: {len(garment.data.polygons)} faces")


def join_collar(garment, collar):
    bpy.ops.object.select_all(action="DESELECT")
    collar.select_set(True)
    garment.select_set(True)
    bpy.context.view_layer.objects.active = garment
    bpy.ops.object.join()
    garment.data.name = f"{GARMENT_NAME}_MESH"


# ------------------------------------------------------------------- UV atlas

def island_definitions(collar_length, collar_profile):
    """Pattern-space rectangles for every UV island, with their texel densities.

    Only the band the print actually occupies is given high density: at 3400
    px/m the hairlines of the script survive a close-up, while the rest of the
    garment sits at 1000 px/m, which is ample for weave, seams and stitching.
    Island rectangles are generous, because a face that straddles two islands is
    resolved to one of them and still has to find its vertices inside that rect.
    """
    base = 1000.0
    chest = 3400.0
    islands = {
        "front_top": dict(rect=(-0.322, -0.190, 0.322, 0.012), density=base),
        "front_print": dict(rect=(-0.245, -0.292, 0.245, -0.115), density=chest),
        "front_print_L": dict(rect=(-0.322, -0.292, -0.155, -0.115), density=base),
        "front_print_R": dict(rect=(0.155, -0.292, 0.322, -0.115), density=base),
        "front_lower": dict(rect=(-0.322, -0.690, 0.322, -0.215), density=base),
        "back": dict(rect=(-0.322, -0.690, 0.322, 0.012), density=base),
    }
    for side in ("R", "L"):
        for tag in ("f", "b"):
            islands[f"sleeve_{side}{tag}"] = dict(
                rect=(-0.010, -0.240, 0.258, 0.012), density=base)
    islands["collar"] = dict(rect=(0.0, 0.0, collar_length, collar_profile),
                             density=min(2000.0, (TEXTURE_SIZE - 2 * ATLAS_PAD - 40) / collar_length))
    return islands


def pack_islands(islands):
    """Shelf-pack the islands into the atlas; raises if the layout will not fit."""
    boxes = []
    for name, island in islands.items():
        x0, y0, x1, y1 = island["rect"]
        width = int(math.ceil((x1 - x0) * island["density"])) + 2 * ATLAS_PAD
        height = int(math.ceil((y1 - y0) * island["density"])) + 2 * ATLAS_PAD
        boxes.append((height, width, name))
    boxes.sort(reverse=True)

    shelves = []   # (y, height, used_width)
    for height, width, name in boxes:
        placed = False
        for shelf in shelves:
            if shelf["height"] >= height and shelf["used"] + width <= TEXTURE_SIZE:
                islands[name]["origin"] = (shelf["used"], shelf["y"])
                shelf["used"] += width
                placed = True
                break
        if placed:
            continue
        y = sum(s["height"] for s in shelves)
        if y + height > TEXTURE_SIZE:
            raise RuntimeError(f"UV atlas overflow placing {name} ({width}x{height})")
        shelves.append(dict(y=y, height=height, used=width))
        islands[name]["origin"] = (0, y)
    for name, island in islands.items():
        x0, y0, _, _ = island["rect"]
        ox, oy = island["origin"]
        island["pixel_origin"] = (ox + ATLAS_PAD, oy + ATLAS_PAD)
        island["offset"] = (ox + ATLAS_PAD - x0 * island["density"],
                            oy + ATLAS_PAD - y0 * island["density"])
    return islands


def uv_for(island, pattern):
    scale = island["density"]
    ox, oy = island["offset"]
    return ((pattern[0] * scale + ox) / TEXTURE_SIZE,
            (pattern[1] * scale + oy) / TEXTURE_SIZE)



def island_key(piece_name, pattern_points):
    """Which atlas island a face belongs to, from its pattern piece and position."""
    if piece_name != "front":
        return piece_name
    centroid_x = float(np.mean([p[0] for p in pattern_points]))
    centroid_y = float(np.mean([p[1] for p in pattern_points]))
    if centroid_y > PRINT_BAND[1]:
        return "front_top"
    if centroid_y > PRINT_BAND[0]:
        if centroid_x < -PRINT_BAND[2]:
            return "front_print_L"
        if centroid_x > PRINT_BAND[2]:
            return "front_print_R"
        return "front_print"
    return "front_lower"


def assign_uvs(garment, islands, piece_names):
    """Lay the pattern coordinates straight into the atlas.

    The front panel is never mirrored.  The inner shell reuses the back panel's
    island so the print does not appear on the inside of the shirt.
    """
    mesh = garment.data
    pattern = np.empty(len(mesh.vertices) * 2, dtype=np.float32)
    mesh.attributes["pat"].data.foreach_get("vector", pattern)
    pattern = pattern.reshape(-1, 2)
    face_piece = np.zeros(len(mesh.polygons), dtype=np.int32)
    mesh.attributes["piece"].data.foreach_get("value", face_piece)

    shell_group = garment.vertex_groups["shell"].index
    shell = np.zeros(len(mesh.vertices), dtype=bool)
    for vertex in mesh.vertices:
        shell[vertex.index] = any(g.group == shell_group and g.weight > 0.5
                                  for g in vertex.groups)

    uv_layer = mesh.uv_layers.new(name="UVMap")
    for polygon in mesh.polygons:
        identifier = int(face_piece[polygon.index])
        if identifier < 0:
            key = "collar"
        else:
            key = island_key(piece_names[identifier],
                             [pattern[v] for v in polygon.vertices])
        if key.startswith("front") and all(shell[v] for v in polygon.vertices):
            key = "back"
        island = islands[key]
        for loop_index in polygon.loop_indices:
            vertex = mesh.loops[loop_index].vertex_index
            uv_layer.data[loop_index].uv = uv_for(island, pattern[vertex])
    log("UV atlas assigned")


def mark_collar_faces(garment, first_collar_vertex):
    """Tag the joined collar faces with their own island id."""
    mesh = garment.data
    values = np.zeros(len(mesh.polygons), dtype=np.int32)
    mesh.attributes["piece"].data.foreach_get("value", values)
    tagged = 0
    for polygon in mesh.polygons:
        if all(index >= first_collar_vertex for index in polygon.vertices):
            values[polygon.index] = -1
            tagged += 1
    mesh.attributes["piece"].data.foreach_set("value", values)
    log(f"tagged {tagged} collar faces")


def thicken_hems(garment, piece_names):
    """A folded hem is thicker than the body of the cloth; nudge the inner shell."""
    mesh = garment.data
    pattern = np.empty(len(mesh.vertices) * 2, dtype=np.float32)
    mesh.attributes["pat"].data.foreach_get("vector", pattern)
    pattern = pattern.reshape(-1, 2)
    face_piece = np.zeros(len(mesh.polygons), dtype=np.int32)
    mesh.attributes["piece"].data.foreach_get("value", face_piece)

    sleeve_vertex = np.zeros(len(mesh.vertices), dtype=bool)
    body_vertex = np.zeros(len(mesh.vertices), dtype=bool)
    for polygon in mesh.polygons:
        identifier = int(face_piece[polygon.index])
        if identifier < 0:
            continue
        key = piece_names[identifier]
        for index in polygon.vertices:
            if key.startswith("sleeve"):
                sleeve_vertex[index] = True
            elif key:
                body_vertex[index] = True

    shell_group = garment.vertex_groups["shell"].index
    moved = 0
    for vertex in mesh.vertices:
        if not any(g.group == shell_group and g.weight > 0.5 for g in vertex.groups):
            continue
        py = float(pattern[vertex.index][1])
        amount = 0.0
        if body_vertex[vertex.index]:
            amount = float(smoothstep(HEM_Y + 0.030, HEM_Y + 0.004, py)) * 0.0013
        elif sleeve_vertex[vertex.index]:
            amount = float(smoothstep(-SLEEVE_LEN + 0.026, -SLEEVE_LEN + 0.004, py)) * 0.0013
        if amount > 1e-5:
            vertex.co -= vertex.normal * amount
            moved += 1
    mesh.update()
    log(f"thickened {moved} hem vertices")

def pick_font():
    for path in FONT_CANDIDATES:
        if path.exists():
            return path
    raise FileNotFoundError("no copperplate/Spencerian script font found")


def _print_scene(name):
    scene = bpy.data.scenes.new(name)
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "FLAT"
    scene.display.shading.color_type = "SINGLE"
    scene.display.shading.single_color = (1.0, 1.0, 1.0)
    scene.display.render_aa = "32"
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.resolution_percentage = 100
    try:
        scene.view_settings.view_transform = "Standard"
    except TypeError:
        pass
    return scene


def _ortho_camera(scene, rect, resolution):
    x0, y0, x1, y1 = rect
    camera_data = bpy.data.cameras.new(f"{scene.name}_CAM")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = x1 - x0
    camera_data.sensor_fit = "HORIZONTAL"
    camera = bpy.data.objects.new(camera_data.name, camera_data)
    camera.location = ((x0 + x1) / 2, (y0 + y1) / 2, 1.0)
    scene.collection.objects.link(camera)
    scene.camera = camera
    scene.render.resolution_x, scene.render.resolution_y = resolution
    return camera


def _render_alpha(scene, path):
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True, scene=scene.name)
    image = bpy.data.images.load(str(path), check_existing=False)
    width, height = image.size
    buffer = np.empty(width * height * 4, dtype=np.float32)
    image.pixels.foreach_get(buffer)
    bpy.data.images.remove(image)
    return buffer.reshape(height, width, 4)[..., 3]


def _text_object(scene, body, font, size):
    curve = bpy.data.curves.new(f"PRINT_{body[:8]}", "FONT")
    curve.body = body
    curve.font = font
    curve.align_x = "CENTER"
    set_enum(curve, "align_y", "TOP_BASELINE")
    curve.size = size
    curve.resolution_u = 32
    obj = bpy.data.objects.new(curve.name, curve)
    scene.collection.objects.link(obj)
    return obj


def render_print_mask(island, scratch):
    """Render the two-line script into a mask aligned to the chest UV island.

    The reference lettering is matched by measuring the rendered ink of each
    line and scaling the type so line two is exactly as wide as it is in the
    photograph, then landing each line's ink top at its measured height.
    """
    font_path = pick_font()
    font = bpy.data.fonts.load(str(font_path))
    log(f"print typeface: {font_path.name}")

    measure_rect = (-0.6, -0.3, 0.6, 0.3)
    measure = _print_scene("PRINT_MEASURE")
    _ortho_camera(measure, measure_rect, (2400, 1200))
    probe_size = 0.04
    metrics = []
    for index, line in enumerate(PRINT_LINES):
        obj = _text_object(measure, line, font, probe_size)
        alpha = _render_alpha(measure, scratch / f"print_probe_{index}.png")
        rows, cols = np.nonzero(alpha > 0.5)
        if not len(rows):
            raise RuntimeError("the print render produced no ink")
        height, width = alpha.shape
        metres_per_px = (measure_rect[2] - measure_rect[0]) / width
        x_min = measure_rect[0] + cols.min() * metres_per_px
        x_max = measure_rect[0] + (cols.max() + 1) * metres_per_px
        y_max = measure_rect[1] + (rows.max() + 1) * metres_per_px   # image row 0 is the bottom
        metrics.append(dict(width=x_max - x_min, top=y_max, centre=(x_min + x_max) / 2))
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.scenes.remove(measure)

    scale = PRINT_LINE2_WIDTH / metrics[1]["width"]
    size = probe_size * scale
    natural_ratio = metrics[0]["width"] / metrics[1]["width"]

    x0, y0, x1, y1 = PRINT_RECT
    density = island["density"]
    pixels_x = int(round((x1 - x0) * density))
    pixels_y = int(round((y1 - y0) * density))
    supersample = 4
    final = _print_scene("PRINT_FINAL")
    _ortho_camera(final, PRINT_RECT, (pixels_x * supersample, pixels_y * supersample))
    for index, line in enumerate(PRINT_LINES):
        obj = _text_object(final, line, font, size)
        obj.location = (PRINT_CENTRES[index] - metrics[index]["centre"] * scale,
                        PRINT_TOPS[index] - metrics[index]["top"] * scale, 0.0)
    alpha = _render_alpha(final, PRINT_WORKING_PATH)
    bpy.data.scenes.remove(final)

    mask = alpha.reshape(pixels_y, supersample, pixels_x, supersample).mean(axis=(1, 3))
    log(f"print: line widths {metrics[0]['width'] * scale:.3f} / "
        f"{metrics[1]['width'] * scale:.3f} m (reference 0.214 / {PRINT_LINE2_WIDTH})")
    return mask.astype(F), dict(font=font_path.name, size=size,
                                line1_width=round(metrics[0]["width"] * scale, 4),
                                line2_width=round(metrics[1]["width"] * scale, 4),
                                natural_ratio=round(natural_ratio, 4))


# -------------------------------------------------------------------- textures


def island_pixel_grid(island):
    """Pixel-centre pattern coordinates for an island, including its gutter.

    The gutter is filled with real extrapolated fabric rather than background,
    so mip-mapping cannot pull empty atlas space into the garment.
    """
    x0, y0, x1, y1 = island["rect"]
    density = island["density"]
    ox, oy = island["origin"]
    width = int(math.ceil((x1 - x0) * density)) + 2 * ATLAS_PAD
    height = int(math.ceil((y1 - y0) * density)) + 2 * ATLAS_PAD
    pad = ATLAS_PAD / density
    xs = (x0 - pad) + (np.arange(width, dtype=F) + 0.5) / density
    ys = (y0 - pad) + (np.arange(height, dtype=F) + 0.5) / density
    grid_x, grid_y = np.meshgrid(xs, ys)
    return grid_x, grid_y, (ox, oy, width, height)

def seam_fields(name, grid_x, grid_y):
    """Distance-driven seam, stitch and hem relief for one garment island."""
    shape = grid_x.shape
    points = np.stack([grid_x.ravel(), grid_y.ravel()], axis=1).astype(np.float64)
    height = np.zeros(points.shape[0], dtype=F)
    stitch = np.zeros(points.shape[0], dtype=F)

    def dashes(along, period=0.0034, duty=0.62):
        phase = np.mod(along, period) / period
        return smoothstep(duty + 0.08, duty - 0.08, phase)

    def add_stitch_line(polyline, offset, period=0.0034):
        distance, along = distance_to_polyline(points, polyline, want_along=True)
        groove = np.exp(-(((distance - offset) / 0.0011) ** 2)) * dashes(along, period)
        return groove.astype(F)

    def add_seam(polyline, ridge=0.00030, ridge_centre=0.0045, groove=0.00026):
        distance = distance_to_polyline(points, polyline)
        relief = ridge * np.exp(-(((distance - ridge_centre) / 0.0038) ** 2))
        relief -= groove * np.exp(-((distance / 0.0016) ** 2))
        return relief.astype(F)

    front = body_panel_segments(True)
    back = body_panel_segments(False)
    sleeve = sleeve_half_segments()

    if name.startswith("front") or name == "back":
        segments = front if name.startswith("front") else back
        for tag in ("L", "R"):
            height += add_seam(segments[f"side_{tag}"])
            height += add_seam(segments[f"shoulder_{tag}"])
            height += add_seam(segments[f"armhole_{tag}"], ridge=0.00034, ridge_centre=0.0050)
            line = add_stitch_line(segments[f"armhole_{tag}"], 0.0065)
            stitch += line
            height -= line * 0.00016
        # neckline: the rib join is topstitched just below the band
        line = add_stitch_line(segments["neck"], 0.0095)
        stitch += line
        height -= line * 0.00018
        # body hem: folded band with a double-needle coverstitch
        hem_distance = distance_to_polyline(points, segments["hem"])
        height += 0.00040 * smoothstep(0.027, 0.020, hem_distance)
        for offset in (0.0205, 0.0245):
            line = add_stitch_line(segments["hem"], offset)
            stitch += line
            height -= line * 0.00020
    elif name.startswith("sleeve"):
        height += add_seam(sleeve["underarm"])
        height += add_seam(sleeve["cap"], ridge=0.00034, ridge_centre=0.0050)
        line = add_stitch_line(sleeve["cap"], 0.0065)
        stitch += line
        height -= line * 0.00016
        cuff_distance = distance_to_polyline(points, sleeve["cuff"])
        height += 0.00036 * smoothstep(0.022, 0.016, cuff_distance)
        for offset in (0.0155, 0.0190):
            line = add_stitch_line(sleeve["cuff"], offset)
            stitch += line
            height -= line * 0.00020
    return height.reshape(shape), np.clip(stitch, 0.0, 1.0).reshape(shape)


def fabric_fields(name, grid_x, grid_y, print_mask=None):
    """Base colour, roughness and height for one island, in fabric space."""
    shape = grid_x.shape
    flat = np.stack([grid_x.ravel(), grid_y.ravel()], axis=1)

    if name == "collar":
        # 1x1 rib: wales run across the band, so they vary along its length
        rib = 0.5 + 0.5 * np.sin(2 * math.pi * flat[:, 0] / 0.0042)
        fibre = weathering.fbm2(flat / np.array([0.0016, 0.0042], F), octaves=3, seed=23)
        height = (0.00019 * (rib - 0.5) + 0.00011 * (fibre - 0.5)).astype(F)
        albedo = np.tile(FABRIC_LINEAR * 0.94, (len(flat), 1))
        albedo *= (1.0 + 0.10 * (fibre - 0.5) + 0.07 * (rib - 0.5))[:, None]
        rough = 0.92 + 0.02 * (fibre - 0.5)
        return (albedo.reshape(*shape, 3).astype(F), rough.reshape(shape).astype(F),
                height.reshape(shape))

    # Heavyweight cotton jersey: fine wales along the panel, courses across it,
    # and a fibrous stochastic component so it never reads as a regular grid.
    # Jersey reads as fibrous, directional noise rather than a regular grid: a
    # true 1 mm wale would sit under one texel and alias into moire, so the
    # structure is carried stochastically and only hinted at periodically.
    fibre = weathering.fbm2(flat / np.array([0.0021, 0.0062], F), octaves=3, seed=7)
    grain = weathering.fbm2(flat / np.array([0.0068, 0.0052], F), octaves=2, seed=19)
    wale = 0.5 + 0.5 * np.sin(2 * math.pi * flat[:, 0] / 0.0072)
    mottle = weathering.fbm2(flat / 0.075, octaves=4, seed=41)

    knit_height = (0.00015 * (fibre - 0.5) + 0.00009 * (grain - 0.5)
                   + 0.00004 * (wale - 0.5)).astype(F)

    ink = np.zeros(len(flat), F)
    if print_mask is not None:
        ink = print_mask.ravel()

    albedo = np.tile(FABRIC_LINEAR, (len(flat), 1))
    albedo *= (1.0 + 0.15 * (fibre - 0.5) + 0.07 * (grain - 0.5)
               + 0.06 * (mottle - 0.5))[:, None]
    # the ink sits in the cloth: coverage is modulated by the weave itself
    coverage = np.clip(ink * (0.90 + 0.10 * fibre), 0.0, 1.0)
    albedo = albedo * (1.0 - coverage)[:, None] + INK_LINEAR * coverage[:, None]

    rough = 0.90 + 0.035 * (mottle - 0.5) * 2.0 - 0.05 * coverage
    # plastisol slightly smooths the fibre it sits on, and nothing more
    height = knit_height * (1.0 - 0.45 * coverage) + 0.000025 * coverage
    return (albedo.reshape(*shape, 3).astype(F), rough.reshape(shape).astype(F),
            height.reshape(shape))


def height_to_normal(height, metres_per_pixel):
    dy, dx = np.gradient(height.astype(np.float64), metres_per_pixel)
    normal = np.stack([-dx, -dy, np.ones_like(dx)], axis=-1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    return normal.astype(F)


def build_textures(islands, print_info_holder):
    base = np.zeros((TEXTURE_SIZE, TEXTURE_SIZE, 3), F)
    rough = np.full((TEXTURE_SIZE, TEXTURE_SIZE), 0.9, F)
    normal = np.zeros((TEXTURE_SIZE, TEXTURE_SIZE, 3), F)
    normal[..., 2] = 1.0

    scratch = Path(tempfile.gettempdir())
    print_mask_full, print_info = render_print_mask(islands["front_print"], scratch)
    print_info_holder.update(print_info)

    for name, island in islands.items():
        grid_x, grid_y, (ox, oy, width, height_px) = island_pixel_grid(island)
        mask = None
        if name == "front_print":
            mask = np.zeros_like(grid_x)
            x0, y0, x1, y1 = PRINT_RECT
            density = island["density"]
            rect_x0 = int(round((x0 - island["rect"][0]) * density)) + ATLAS_PAD
            rect_y0 = int(round((y0 - island["rect"][1]) * density)) + ATLAS_PAD
            sub = print_mask_full
            mask[rect_y0:rect_y0 + sub.shape[0], rect_x0:rect_x0 + sub.shape[1]] = sub
        albedo, roughness, relief = fabric_fields(name, grid_x, grid_y, mask)
        seam_height, stitch = (np.zeros_like(relief), np.zeros_like(relief))
        if name != "collar":
            seam_height, stitch = seam_fields(name, grid_x, grid_y)
        total_height = relief + seam_height
        albedo = albedo * (1.0 + 0.10 * stitch)[..., None]
        roughness = np.clip(roughness - 0.04 * stitch, 0.35, 1.0)
        island_normal = height_to_normal(total_height, 1.0 / island["density"])

        base[oy:oy + height_px, ox:ox + width] = albedo
        rough[oy:oy + height_px, ox:ox + width] = roughness
        normal[oy:oy + height_px, ox:ox + width] = island_normal
        log(f"  island {name}: {width}x{height_px} px at {island['density']:.0f} px/m")

    def write(path, data, colorspace, name):
        image = bpy.data.images.new(name, width=TEXTURE_SIZE, height=TEXTURE_SIZE,
                                    alpha=False, float_buffer=False,
                                    is_data=(colorspace != "sRGB"))
        image.colorspace_settings.name = colorspace
        pixels = np.ones((TEXTURE_SIZE, TEXTURE_SIZE, 4), F)
        pixels[..., :3] = data
        image.pixels.foreach_set(pixels.ravel())
        image.filepath_raw = str(path)
        image.file_format = "PNG"
        image.save()
        return image

    base_image = write(BASECOLOR_PATH, np.clip(base, 0.0, 1.0), "sRGB", f"{SLUG}-basecolor")
    rough_image = write(ROUGHNESS_PATH, np.repeat(np.clip(rough, 0, 1)[..., None], 3, axis=2),
                        "Non-Color", f"{SLUG}-roughness")
    normal_image = write(NORMAL_PATH, normal * 0.5 + 0.5, "Non-Color", f"{SLUG}-normal")
    log("textures written")
    return base_image, rough_image, normal_image


def build_runtime_material(base, rough, normal):
    mat = bpy.data.materials.new(MATERIAL_NAME)
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    output.location = (620, 0)
    bsdf = tree.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (260, 0)
    tree.links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["Specular IOR Level"].default_value = 0.32   # restrained cotton specular
    bsdf.inputs["Sheen Weight"].default_value = 0.14         # keeps black cloth readable at night
    bsdf.inputs["Sheen Roughness"].default_value = 0.45
    bsdf.inputs["Sheen Tint"].default_value = (0.30, 0.30, 0.34, 1.0)

    for image, socket, location, non_colour in (
        (base, "Base Color", (-360, 240), False),
        (rough, "Roughness", (-360, -20), True),
    ):
        node = tree.nodes.new("ShaderNodeTexImage")
        node.image = image
        node.location = location
        if non_colour:
            node.image.colorspace_settings.name = "Non-Color"
        tree.links.new(node.outputs["Color"], bsdf.inputs[socket])

    normal_node = tree.nodes.new("ShaderNodeTexImage")
    normal_node.image = normal
    normal_node.location = (-360, -280)
    normal_map = tree.nodes.new("ShaderNodeNormalMap")
    normal_map.location = (-60, -280)
    normal_map.inputs["Strength"].default_value = 1.0
    tree.links.new(normal_node.outputs["Color"], normal_map.inputs["Color"])
    tree.links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


# ---------------------------------------------------------------------- export

def finalise_mesh(garment, material):
    mesh = garment.data
    mesh.materials.clear()
    mesh.materials.append(material)
    for polygon in mesh.polygons:
        polygon.material_index = 0
        polygon.use_smooth = True
    activate(garment)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    triangulate = garment.modifiers.new("runtime-triangulation", "TRIANGULATE")
    triangulate.keep_custom_normals = True
    bpy.ops.object.modifier_apply(modifier=triangulate.name)
    for name in ("pat", "piece"):
        if name in mesh.attributes:
            mesh.attributes.remove(mesh.attributes[name])
    for group in list(garment.vertex_groups):
        garment.vertex_groups.remove(group)
    mesh.validate(verbose=False, clean_customdata=False)
    garment["asset"] = "Zealot of Harperhey — Art School T-shirt, black"
    garment["fit"] = "oversized heavyweight boxy blank, dropped shoulder"
    garment["rigging"] = "standalone rest-state garment; skin to a compatible humanoid armature"
    garment["front"] = "+Y in Blender / -Z after glTF Y-up conversion"


def count_triangles(obj):
    return sum(len(polygon.vertices) - 2 for polygon in obj.data.polygons)


def non_manifold_edges(obj, weld_import_splits=False):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    if weld_import_splits:
        bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-6)
    count = sum(1 for edge in bm.edges if not edge.is_manifold)
    bm.free()
    return count


def export_glb(garment):
    activate(garment)
    bpy.ops.export_scene.gltf(
        filepath=str(GLB_PATH),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=True,
        export_materials="EXPORT",
        export_image_format="AUTO",
        export_cameras=False,
        export_lights=False,
        export_extras=True,
        export_tangents=False,
    )
    log(f"exported {GLB_PATH.name} ({GLB_PATH.stat().st_size / 1e6:.2f} MB)")


def read_glb_json():
    data = GLB_PATH.read_bytes()
    length = int.from_bytes(data[12:16], "little")
    return json.loads(data[20:20 + length].decode("utf-8"))


# ------------------------------------------------------------------ validation

def object_bounds(obj):
    corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    mins = Vector((min(c.x for c in corners), min(c.y for c in corners), min(c.z for c in corners)))
    maxs = Vector((max(c.x for c in corners), max(c.y for c in corners), max(c.z for c in corners)))
    return mins, maxs


def clearance_report(garment, body):
    """How much room the garment leaves at the points the brief names."""
    tree = BVHTree.FromObject(garment, bpy.context.evaluated_depsgraph_get())
    probes = {
        "chest": (0.0, 0.118, 1.290),
        "shoulder_R": (0.185, 0.0, 1.430),
        "upper_arm_R": (0.300, 0.0, 1.300),
        "waist": (0.0, 0.104, 1.080),
        "hip": (0.0, 0.110, 0.965),
    }
    out = {}
    for name, point in probes.items():
        location, _, _, distance = tree.find_nearest(Vector(point))
        out[name] = round(float(distance), 4) if location is not None else None
    return out


# --------------------------------------------------------------- review renders

def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def build_review_studio():
    """A lookbook studio: black cloth needs separation, not more key light."""
    review = collection("REVIEW_DO_NOT_EXPORT")
    backdrop_material = simple_material("MAT_Studio_Backdrop", (0.112, 0.110, 0.109), 0.92)

    bpy.ops.mesh.primitive_plane_add(size=14.0, location=(0, 0, 0))
    ground = bpy.context.object
    ground.name = "REVIEW_Ground"
    ground.data.materials.append(backdrop_material)
    move_to_collection(ground, review)

    bpy.ops.mesh.primitive_plane_add(size=14.0, location=(0, -4.2, 3.0),
                                     rotation=(math.radians(90), 0, 0))
    wall = bpy.context.object
    wall.name = "REVIEW_Backdrop"
    wall.data.materials.append(backdrop_material)
    move_to_collection(wall, review)

    lights = []
    for name, location, energy, size, colour in (
        # A black garment is lit for separation, not for exposure: a soft key,
        # a weak fill and two rims that find the silhouette and the hem.
        ("REVIEW_Key", (-1.9, 2.6, 2.9), 190, 1.8, (1.0, 0.96, 0.92)),
        ("REVIEW_Fill", (2.3, 2.0, 1.9), 65, 2.6, (0.88, 0.93, 1.0)),
        ("REVIEW_RimL", (-2.4, -1.9, 2.4), 170, 1.0, (1.0, 0.93, 0.86)),
        ("REVIEW_RimR", (2.5, -1.8, 2.4), 155, 1.0, (0.92, 0.95, 1.0)),
        ("REVIEW_Top", (0.0, 0.5, 3.4), 95, 2.0, (1.0, 0.98, 0.95)),
    ):
        bpy.ops.object.light_add(type="AREA", location=location)
        light = bpy.context.object
        light.name = name
        light.data.energy = energy
        light.data.shape = "DISK"
        light.data.size = size
        light.data.color = colour
        look_at(light, (0, 0, 1.2))
        move_to_collection(light, review)
        lights.append(light)

    camera_data = bpy.data.cameras.new("REVIEW_Camera")
    camera_data.lens = 85
    camera = bpy.data.objects.new("REVIEW_Camera", camera_data)
    move_to_collection(camera, review)
    scene = bpy.context.scene
    scene.camera = camera

    scene.render.engine = "BLENDER_EEVEE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("ArtSchool_Studio_World")
    scene.world.use_nodes = True
    background = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    background.inputs["Color"].default_value = (0.045, 0.046, 0.050, 1.0)
    background.inputs["Strength"].default_value = 1.0
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    return camera, lights, review


def render_view(camera, filename, location, target, lens, resolution):
    scene = bpy.context.scene
    camera.location = location
    camera.data.lens = lens
    look_at(camera, target)
    scene.render.resolution_x, scene.render.resolution_y = resolution
    scene.render.filepath = str(RENDER_DIR / filename)
    bpy.ops.render.render(write_still=True)
    log(f"  rendered {filename}")


def render_review_set(camera, lights, review, print_point):
    portrait = (1000, 1250)
    views = (
        ("01-front.png", (0, 3.05, 1.18), (0, 0, 1.15), 85, portrait),
        ("02-rear.png", (0, -3.05, 1.18), (0, 0, 1.15), 85, portrait),
        ("03-three-quarter.png", (2.05, 2.30, 1.26), (0, 0, 1.16), 85, portrait),
        ("04-three-quarter-rear.png", (-2.05, -2.30, 1.26), (0, 0, 1.16), 85, portrait),
        ("05-side.png", (3.05, 0.06, 1.22), (0, 0, 1.17), 85, portrait),
    )
    for view in views:
        render_view(camera, *view)

    close_target = tuple(print_point)
    close_location = (close_target[0], close_target[1] + 0.78, close_target[2] + 0.05)
    render_view(camera, "06-chest-print-closeup.png", close_location, close_target, 85, (1500, 1000))
    render_view(camera, "07-collar-closeup.png", (0.0, 0.92, 1.66), (0, 0.02, 1.45), 105, (1400, 1000))

    # Hard directional light: the construction check the brief's fashion standard needs.
    for light in lights:
        light.hide_render = True
    bpy.ops.object.light_add(type="AREA", location=(-1.5, 1.7, 2.6))
    hard = bpy.context.object
    hard.name = "REVIEW_HardLight"
    hard.data.energy = 320
    hard.data.size = 0.16
    look_at(hard, (0.10, 0.05, 1.20))
    move_to_collection(hard, review)
    render_view(camera, "08-hard-light-construction.png", (1.95, 2.45, 1.35), (0, 0, 1.18), 85,
                (1100, 1250))
    hard.hide_render = True

    # Night check: the lighting this garment actually lives in.
    world_background = next(n for n in bpy.context.scene.world.node_tree.nodes
                            if n.type == "BACKGROUND")
    world_background.inputs["Color"].default_value = (0.004, 0.005, 0.009, 1.0)
    bpy.ops.object.light_add(type="AREA", location=(-1.1, 1.6, 3.2))
    sodium = bpy.context.object
    sodium.name = "REVIEW_Sodium"
    sodium.data.energy = 260
    sodium.data.size = 0.9
    sodium.data.color = (1.0, 0.60, 0.26)
    look_at(sodium, (0, 0, 1.15))
    move_to_collection(sodium, review)
    bpy.ops.object.light_add(type="AREA", location=(1.8, -1.2, 1.8))
    led = bpy.context.object
    led.name = "REVIEW_LED"
    led.data.energy = 55
    led.data.color = (0.72, 0.83, 1.0)
    led.data.size = 0.6
    look_at(led, (0, 0, 1.25))
    move_to_collection(led, review)
    render_view(camera, "09-night-streetlight.png", (0.95, 2.35, 1.30), (0, 0, 1.17), 85, portrait)


def validate_and_render(expected_triangles, print_uv, print_info, clearances,
                        measurements):
    """Reimport the exported GLB into an empty scene, verify it, and shoot it."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(GLB_PATH))
    objects = list(bpy.context.scene.objects)
    meshes = [obj for obj in objects if obj.type == "MESH"]
    if len(meshes) != 1:
        raise RuntimeError(f"expected one exported mesh, got {len(meshes)}")
    garment = meshes[0]
    if GARMENT_NAME not in garment.name:
        raise RuntimeError(f"unexpected exported object name: {garment.name}")
    materials = sorted({slot.material.name for slot in garment.material_slots if slot.material})
    if not any(MATERIAL_NAME in name for name in materials):
        raise RuntimeError(f"missing runtime material {MATERIAL_NAME}: {materials}")
    if any(obj.name.startswith("FIT_") for obj in objects):
        raise RuntimeError("the fitting body leaked into the export")
    if any(obj.type in {"CAMERA", "LIGHT"} for obj in objects):
        raise RuntimeError("cameras or lights leaked into the export")

    triangles = count_triangles(garment)
    if not 5000 <= triangles <= 12000:
        raise RuntimeError(f"triangle budget violated: {triangles}")
    if abs(triangles - expected_triangles) > 8:
        raise RuntimeError(f"triangle count changed on export: {expected_triangles} -> {triangles}")
    raw_boundary = non_manifold_edges(garment)
    welded = non_manifold_edges(garment, weld_import_splits=True)
    if welded != 0:
        raise RuntimeError(f"reimported garment has {welded} non-manifold edges")
    if len(garment.data.uv_layers) != 1:
        raise RuntimeError(f"expected exactly one UV set, got {len(garment.data.uv_layers)}")

    gltf = read_glb_json()
    images = [image.get("mimeType", "?") for image in gltf.get("images", [])]
    extensions = gltf.get("extensionsUsed", [])
    material_json = gltf["materials"][0]
    pbr = material_json.get("pbrMetallicRoughness", {})
    for required in ("baseColorTexture", "metallicRoughnessTexture"):
        if required not in pbr:
            raise RuntimeError(f"exported material is missing {required}")
    if "normalTexture" not in material_json:
        raise RuntimeError("exported material is missing normalTexture")

    mins, maxs = object_bounds(garment)
    # Locate the print on the reimported geometry through its UVs, so the
    # close-up frames the type wherever the simulated cloth actually put it.
    uv_data = garment.data.uv_layers[0].data
    print_point = Vector((0, 0, 0))
    best = 1e9
    for polygon in garment.data.polygons:
        uv = Vector((0.0, 0.0))
        for loop_index in polygon.loop_indices:
            uv += Vector(uv_data[loop_index].uv)
        uv /= polygon.loop_total
        delta = (uv - Vector(print_uv)).length
        if delta < best:
            best = delta
            print_point = garment.matrix_world @ polygon.center

    with bpy.data.libraries.load(str(BLEND_PATH), link=False) as (source, target):
        target.collections = [name for name in source.collections
                              if name.startswith("FITTING_BODY")]
    for coll in bpy.data.collections:
        if coll.name.startswith("FITTING_BODY") and coll.name not in \
                {c.name for c in bpy.context.scene.collection.children}:
            bpy.context.scene.collection.children.link(coll)

    camera, lights, review = build_review_studio()
    render_review_set(camera, lights, review, print_point)

    report = {
        "asset": "Art School T-shirt — black",
        "glb": str(GLB_PATH.relative_to(ROOT)),
        "object": garment.name,
        "mesh_objects": len(meshes),
        "materials": materials,
        "vertices": len(garment.data.vertices),
        "triangles": triangles,
        "triangle_budget": [5000, 12000],
        "uv_sets": [layer.name for layer in garment.data.uv_layers],
        "non_manifold_edges_after_welding_import_splits": welded,
        "raw_import_boundary_edges_from_uv_normal_splits": raw_boundary,
        "bounds_m": {
            "min": [round(v, 4) for v in mins],
            "max": [round(v, 4) for v in maxs],
            "dimensions": [round(v, 4) for v in (maxs - mins)],
        },
        "object_scale": [round(v, 6) for v in garment.scale],
        "gltf": {
            "images": images,
            "extensionsUsed": extensions,
            "materialName": material_json.get("name"),
            "doubleSided": material_json.get("doubleSided", False),
            "metallicFactor": pbr.get("metallicFactor", 1.0),
        },
        "glb_size_mb": round(GLB_PATH.stat().st_size / 1e6, 2),
        "print": print_info,
        "clearance_to_fitting_body_m": clearances,
        "cloth_strain_vs_flat_pattern": measurements.get("strain"),
        "seam_gaps_before_welding_m": measurements.get("seam_gaps"),
        "neckline_length_m": measurements.get("neckline_length"),
        "hang_on_fitting_body": measurements.get("hang"),
        "fitting_body_exported": False,
        "cameras_exported": False,
        "lights_exported": False,
        "status": "PASS",
    }
    VALIDATION_PATH.write_text(json.dumps(report, indent=2) + "\n")
    return report


# ------------------------------------------------------------------------ main

def main():
    arguments = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    reuse = "--reuse-sim" in arguments

    ensure_directories()
    if reuse and SIM_CACHE.exists():
        log(f"reusing cached simulation {SIM_CACHE}")
        bpy.ops.wm.open_mainfile(filepath=str(SIM_CACHE))
        garment = bpy.data.objects[GARMENT_NAME]
        body = bpy.data.objects[BODY_NAME]
    else:
        reset_scene()
        body = build_fitting_body()
        garment = build_pattern_garment(body)
        simulate(garment, body)
        finish_simulation(garment, body)
        bpy.ops.wm.save_as_mainfile(filepath=str(SIM_CACHE), compress=True)
        log(f"cached simulation to {SIM_CACHE}")

    piece_names = json.loads(garment["pieces"])
    clearances = clearance_report(garment, body)
    log(f"clearance: {clearances}")

    collar, collar_length, collar_profile = build_collar(garment)
    solidify_garment(garment)
    first_collar_vertex = len(garment.data.vertices)
    join_collar(garment, collar)
    mark_collar_faces(garment, first_collar_vertex)

    islands = pack_islands(island_definitions(collar_length, collar_profile))
    assign_uvs(garment, islands, piece_names)
    thicken_hems(garment, piece_names)

    print_info = {}
    base, rough, normal = build_textures(islands, print_info)
    material = build_runtime_material(base, rough, normal)
    finalise_mesh(garment, material)

    triangles = count_triangles(garment)
    log(f"garment: {len(garment.data.vertices)} verts, {triangles} triangles, "
        f"{non_manifold_edges(garment)} non-manifold edges")
    if not 5000 <= triangles <= 12000:
        raise RuntimeError(f"source garment triangle budget violated: {triangles}")

    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH), compress=True)
    export_glb(garment)

    print_uv = uv_for(islands["front_print"], (0.0, -0.190))
    measurements = json.loads(garment.get("measurements", "{}"))
    measurements["neckline_length"] = round(collar_length, 4)
    measurements["hang"] = json.loads(garment.get("hang", "{}"))
    report = validate_and_render(triangles, print_uv, print_info, clearances, measurements)
    print(json.dumps(report, indent=2))
    log(f"BLEND:   {BLEND_PATH}")
    log(f"GLB:     {GLB_PATH}")
    log(f"RENDERS: {RENDER_DIR}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:   # surface the failure clearly in --background runs
        print(f"[{SLUG}] ERROR: {exc}", file=sys.stderr, flush=True)
        raise

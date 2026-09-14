"""Physically motivated weathering toolkit for baked texture passes.

Texture-pass scripts bake world position, world normal, object id, ambient
occlusion and convexity into an asset's UV atlas.  Weathering is then described
in world terms -- rain runs down, road spray rises, hands touch a known height,
dirt settles in recesses, sun reaches exposed faces -- instead of laying one
tiling grunge texture over everything.

The numpy functions operate on flat arrays of valid texels.  Only the UV, bake,
image and material helpers at the bottom of the file touch bpy.
"""

from math import radians
from pathlib import Path

import numpy as np

F = np.float32
UP = np.array((0.0, 0.0, 1.0), F)


# --------------------------------------------------------------------- noise

def _hash(ix, iy, iz, seed):
    h = ix.astype(np.uint32) * np.uint32(0x8DA6B343)
    h ^= iy.astype(np.uint32) * np.uint32(0xD8163841)
    h ^= iz.astype(np.uint32) * np.uint32(0xCB1AB31F)
    h ^= np.uint32((seed * 0x9E3779B1 + 0x7F4A7C15) & 0xFFFFFFFF)
    h ^= h >> np.uint32(15)
    h *= np.uint32(0x2C1B3C6D)
    h ^= h >> np.uint32(12)
    h *= np.uint32(0x297A2D39)
    h ^= h >> np.uint32(15)
    return (h >> np.uint32(8)).astype(F) * F(1.0 / (1 << 24))


def _lerp(a, b, t):
    return a + (b - a) * t


def noise3(p, seed=0):
    """Smooth value noise in [0, 1] for (M, 3) points."""
    cell = np.floor(p)
    f = (p - cell).astype(F)
    cell = cell.astype(np.int64)
    u = f * f * (F(3) - F(2) * f)
    x0, y0, z0 = cell[:, 0], cell[:, 1], cell[:, 2]
    x1, y1, z1 = x0 + 1, y0 + 1, z0 + 1
    ux, uy, uz = u[:, 0], u[:, 1], u[:, 2]
    c00 = _lerp(_hash(x0, y0, z0, seed), _hash(x1, y0, z0, seed), ux)
    c10 = _lerp(_hash(x0, y1, z0, seed), _hash(x1, y1, z0, seed), ux)
    c01 = _lerp(_hash(x0, y0, z1, seed), _hash(x1, y0, z1, seed), ux)
    c11 = _lerp(_hash(x0, y1, z1, seed), _hash(x1, y1, z1, seed), ux)
    return _lerp(_lerp(c00, c10, uy), _lerp(c01, c11, uy), uz)


def noise2(q, seed=0):
    """Smooth value noise in [0, 1] for (M, 2) points."""
    cell = np.floor(q)
    f = (q - cell).astype(F)
    cell = cell.astype(np.int64)
    u = f * f * (F(3) - F(2) * f)
    x0, y0 = cell[:, 0], cell[:, 1]
    x1, y1 = x0 + 1, y0 + 1
    zero = np.zeros_like(x0)
    a = _lerp(_hash(x0, y0, zero, seed), _hash(x1, y0, zero, seed), u[:, 0])
    b = _lerp(_hash(x0, y1, zero, seed), _hash(x1, y1, zero, seed), u[:, 0])
    return _lerp(a, b, u[:, 1])


def fbm3(p, octaves=4, seed=0, lacunarity=2.03, gain=0.5):
    total = np.zeros(len(p), F)
    q = p.astype(F)
    amplitude, norm = 1.0, 0.0
    for octave in range(octaves):
        total += F(amplitude) * noise3(q, seed + octave * 17)
        norm += amplitude
        amplitude *= gain
        q = q * F(lacunarity) + F(0.37)
    return total / F(norm)


def fbm2(q, octaves=4, seed=0, lacunarity=2.03, gain=0.5):
    total = np.zeros(len(q), F)
    r = q.astype(F)
    amplitude, norm = 1.0, 0.0
    for octave in range(octaves):
        total += F(amplitude) * noise2(r, seed + octave * 17)
        norm += amplitude
        amplitude *= gain
        r = r * F(lacunarity) + F(0.37)
    return total / F(norm)


def smoothstep(edge0, edge1, x):
    t = np.clip((np.asarray(x, F) - edge0) / (edge1 - edge0), 0.0, 1.0).astype(F)
    return t * t * (F(3) - F(2) * t)


def srgb_encode(linear):
    linear = np.clip(linear, 0.0, 1.0)
    return np.where(linear <= 0.0031308, linear * 12.92, 1.055 * np.power(linear, 1 / 2.4) - 0.055).astype(F)


def srgb_decode(encoded):
    encoded = np.clip(encoded, 0.0, 1.0)
    return np.where(encoded <= 0.04045, encoded / 12.92, np.power((encoded + 0.055) / 1.055, 2.4)).astype(F)


def plane_axes(normal):
    """Surface axes for a world normal: u runs horizontally, v runs up the face."""
    n = np.asarray(normal, F)
    n = n / np.linalg.norm(n)
    u = np.cross(UP, n)
    if np.linalg.norm(u) < 0.2:
        u = np.array((0.0, 1.0, 0.0), F) - n * n[1]
    u = u / np.linalg.norm(u)
    return n, u.astype(F), np.cross(n, u).astype(F)


# ------------------------------------------------------------------- texels

class Texels:
    """Valid texels of one baked atlas, flattened for vectorised weathering."""

    def __init__(self, position, normal, extra, names):
        height, width = position.shape[:2]
        normal = normal * 2.0 - 1.0
        # Baked texels carry POSITION_OFFSET; cleared background decodes to -offset.
        valid = (position.min(axis=-1) > -0.5 * POSITION_OFFSET) & (np.linalg.norm(normal, axis=-1) > 0.5)
        self.shape = (height, width)
        self.index = np.flatnonzero(valid)
        self.M = len(self.index)
        self.P = position.reshape(-1, 3)[self.index].astype(F)
        n = normal.reshape(-1, 3)[self.index].astype(F)
        self.N = n / np.linalg.norm(n, axis=1, keepdims=True)
        ex = extra.reshape(-1, 4)[self.index]
        self.ids = np.rint(ex[:, 0]).astype(np.int32)
        self.ao = np.clip(ex[:, 1], 0, 1).astype(F)
        self.convex = np.clip(ex[:, 2], 0, 1).astype(F)
        self.names = names

        t = np.cross(np.broadcast_to(UP, self.N.shape), self.N)
        flat = np.linalg.norm(t, axis=1) < 0.2
        t[flat] = (0.0, 1.0, 0.0)
        t -= self.N * np.sum(t * self.N, axis=1, keepdims=True)
        t /= np.linalg.norm(t, axis=1, keepdims=True)
        self.T = t.astype(F)
        self.B = np.cross(self.N, self.T).astype(F)
        self.s = np.sum(self.P * self.T, axis=1)
        self.t = np.sum(self.P * self.B, axis=1)

        grid = position.reshape(height, width, 3)
        both = valid[:, 1:] & valid[:, :-1]
        steps = np.linalg.norm(grid[:, 1:] - grid[:, :-1], axis=-1)[both]
        self.texel_m = float(np.median(steps[steps > 1e-6])) if steps.size else 0.003

    def name_mask(self, *fragments):
        wanted = [i for i, name in self.names.items() if any(f in name for f in fragments)]
        return np.isin(self.ids, wanted)

    def per_name(self, table, default=0.0):
        """Map an object-name fragment -> value table onto texels."""
        values = np.full(self.M, default, F)
        for object_id, name in self.names.items():
            for fragment, value in table.items():
                if fragment in name:
                    values[self.ids == object_id] = value
        return values

    def panel_bounds(self):
        """Per-object extent in surface coordinates, broadcast to texels."""
        s0 = np.zeros(self.M, F)
        s1 = np.zeros(self.M, F)
        t0 = np.zeros(self.M, F)
        t1 = np.zeros(self.M, F)
        for object_id in np.unique(self.ids):
            sel = self.ids == object_id
            # Measure the panel on its dominant faces, not the thin edges of a slab.
            axis = int(np.argmax(np.abs(self.N[sel]).sum(axis=0)))
            front = sel & (np.abs(self.N[:, axis]) > 0.9)
            ref = front if front.any() else sel
            s0[sel], s1[sel] = self.s[ref].min(), self.s[ref].max()
            t0[sel], t1[sel] = self.t[ref].min(), self.t[ref].max()
        return s0, s1, t0, t1

    def grid(self, values, fill):
        """Scatter texel values back into an (H, W[, C]) image, bottom-up."""
        height, width = self.shape
        values = np.asarray(values, F)
        channels = values.shape[1:] if values.ndim > 1 else ()
        out = np.empty((height * width, *channels), F)
        out[:] = fill
        out[self.index] = values
        return out.reshape(height, width, *channels)

    def stamp(self, center, normal, radius, mask=None, depth=0.03):
        """Texels near a world-space stamp and their (u, v) plane coordinates."""
        c = np.asarray(center, F)
        n, u_axis, v_axis = plane_axes(normal)
        d = self.P - c
        near = (np.abs(d).max(axis=1) < radius) & (self.N @ n > 0.6)
        if mask is not None:
            near &= mask
        idx = np.flatnonzero(near)
        d = d[idx]
        off_plane = np.abs(d @ n) < depth
        idx = idx[off_plane]
        d = d[off_plane]
        return idx, d @ u_axis, d @ v_axis


class Layers:
    """Physical surface channels being authored for one atlas."""

    def __init__(self, tex, albedo, rough, metal=0.0, alpha=1.0):
        self.tex = tex
        self.albedo = np.tile(np.asarray(albedo, F), (tex.M, 1))
        self.rough = np.full(tex.M, rough, F)
        self.metal = np.full(tex.M, metal, F)
        self.alpha = np.full(tex.M, alpha, F)
        self.height = np.zeros(tex.M, F)
        self.wet = np.zeros(tex.M, F)

    def tint(self, color, amount, idx=slice(None)):
        amount = np.clip(np.asarray(amount, F), 0.0, 1.0)
        if amount.ndim:
            amount = amount[:, None]
        self.albedo[idx] = self.albedo[idx] * (1 - amount) + np.asarray(color, F) * amount

    def mix_rough(self, value, amount, idx=slice(None)):
        amount = np.clip(np.asarray(amount, F), 0.0, 1.0)
        self.rough[idx] = self.rough[idx] * (1 - amount) + F(value) * amount

    def finish(self):
        self.albedo = np.clip(self.albedo, 0.0, 1.0)
        self.rough = np.clip(self.rough, 0.02, 1.0)
        self.metal = np.clip(self.metal, 0.0, 1.0)
        self.alpha = np.clip(self.alpha, 0.0, 1.0)
        self.wet = np.clip(self.wet, 0.0, 1.0)
        return self


# ------------------------------------------------------------ surface marks

def streaks(tex, width, length, seed, sharpness=2.6):
    """Run-down streak field in [0, 1], aligned with each surface's down axis."""
    columns = fbm2(np.stack((tex.s / width, tex.t / length), axis=1), 2, seed)
    clusters = noise2(np.stack((tex.s / (width * 16), tex.t / (length * 0.4)), axis=1), seed + 5)
    return np.clip((columns - 0.5) * 2.4 + (clusters - 0.45) * 1.2, 0.0, 1.0) ** sharpness


def micro_scratches(tex, seed, directions=4, spacing=None, length=0.12):
    """Thin anisotropic scratch lines gathered in patches (wiping, keys, bags)."""
    spacing = spacing or tex.texel_m * 1.6
    rng = np.random.default_rng(seed)
    out = np.zeros(tex.M, F)
    for k in range(directions):
        angle = rng.uniform(0, np.pi)
        c, s = np.cos(angle), np.sin(angle)
        across = tex.s * c + tex.t * s
        along = -tex.s * s + tex.t * c
        line = noise2(np.stack((across / spacing, along / length), axis=1), seed + 11 * k)
        line = smoothstep(0.9, 0.985, line)
        patch = smoothstep(0.55, 0.78, noise2(np.stack((tex.s * 2.7, tex.t * 2.7), axis=1), seed + 50 + k))
        out = np.maximum(out, line * patch)
    return out


def fingerprint(u, v, size, seed):
    """Oily fingertip smudge; returns intensity in [0, 1]."""
    r = np.sqrt((u / (size * 0.72)) ** 2 + (v / size) ** 2)
    body = smoothstep(1.0, 0.45, r)
    mottle = noise2(np.stack((u, v), axis=1) / (size * 0.16), seed)
    ridges = 0.5 + 0.5 * np.sin(np.sqrt(u ** 2 + (v * 0.85) ** 2) / (size * 0.06) * 2 * np.pi)
    return body * (0.35 + 0.65 * mottle) * (0.75 + 0.25 * ridges)


def palm_print(u, v, scale, seed, drag=0.0):
    """Palm and four fingers, optionally dragged downward into a smear."""
    # Below the palm the print is pulled downward, as when a hand slides off glass.
    v_drag = v + drag * np.clip(-v, 0, None)
    parts = [((0.0, 0.0), (0.042, 0.050))]
    for i, x in enumerate((-0.030, -0.010, 0.011, 0.030)):
        parts.append(((x, 0.075 + (0.01 if i in (1, 2) else 0.0)), (0.009, 0.030)))
    parts.append(((-0.052, 0.012), (0.010, 0.026)))
    out = np.zeros(len(u), F)
    for (cx, cy), (rx, ry) in parts:
        r = np.sqrt(((u - cx * scale) / (rx * scale)) ** 2 + ((v_drag - cy * scale) / (ry * scale)) ** 2)
        # Soft falloff: skin oil smears outward, so no hard print outline.
        out = np.maximum(out, smoothstep(1.15, 0.0, r))
    mottle = noise2(np.stack((u, v), axis=1) / (0.006 * scale), seed)
    return out * (0.55 + 0.45 * mottle)


def segment_coverage(u, v, a, b, width, texel):
    """Antialiased coverage of a thin line segment of the given width."""
    a = np.asarray(a, F)
    b = np.asarray(b, F)
    ab = b - a
    t = np.clip(((u - a[0]) * ab[0] + (v - a[1]) * ab[1]) / max(float(ab @ ab), 1e-9), 0, 1)
    d = np.hypot(u - (a[0] + ab[0] * t), v - (a[1] + ab[1] * t))
    # Never narrower than the texel grid, or sub-texel lines break into dashes.
    soft = max(width * 0.5, texel * 0.8)
    return np.clip(1.0 - d / soft, 0.0, 1.0) * min(1.0, width / texel + 0.35)


def polyline_coverage(u, v, points, width, texel):
    out = np.zeros(len(u), F)
    for a, b in zip(points[:-1], points[1:]):
        out = np.maximum(out, segment_coverage(u, v, a, b, width, texel))
    return out


def sample_cell(image, cell, u, v):
    """Bilinear RGBA lookup of an atlas cell with (u, v) in [0, 1]."""
    x0, y0, w, h = cell
    x = np.clip(x0 + u * (w - 1), 0, image.shape[1] - 1.001)
    y = np.clip(y0 + v * (h - 1), 0, image.shape[0] - 1.001)
    xi = np.floor(x).astype(np.int64)
    yi = np.floor(y).astype(np.int64)
    fx = (x - xi)[:, None]
    fy = (y - yi)[:, None]
    c00 = image[yi, xi]
    c10 = image[yi, xi + 1]
    c01 = image[yi + 1, xi]
    c11 = image[yi + 1, xi + 1]
    return (c00 * (1 - fx) + c10 * fx) * (1 - fy) + (c01 * (1 - fx) + c11 * fx) * fy


def apply_decal(layers, library, key, center, normal, size, angle=0.0, mask=None, strength=1.0, depth=0.03):
    """Composite one urban decal from the library onto a surface, in world space."""
    tex = layers.tex
    image, meta = library
    entry = meta[key]
    width, height = size
    idx, u, v = tex.stamp(center, normal, max(width, height) * 0.75, mask, depth)
    if not len(idx):
        return 0
    c, s = np.cos(angle), np.sin(angle)
    du = (u * c + v * s) / width + 0.5
    dv = (-u * s + v * c) / height + 0.5
    inside = (du >= 0) & (du <= 1) & (dv >= 0) & (dv <= 1)
    idx, du, dv = idx[inside], du[inside], dv[inside]
    rgba = sample_cell(image, entry["cell"], du, dv)
    a = rgba[:, 3] * strength
    kind = entry["kind"]
    if kind == "scratch":
        layers.rough[idx] += 0.35 * a
        layers.height[idx] -= 0.00004 * a
        layers.alpha[idx] += 0.05 * a
        layers.tint((0.55, 0.55, 0.53), 0.25 * a, idx)
    else:
        layers.tint(srgb_decode(rgba[:, :3]), a, idx)
        layers.mix_rough(entry["roughness"], a, idx)
        layers.metal[idx] *= 1 - a
        layers.height[idx] += entry["thickness"] * a
        if kind in ("paper", "tape", "residue", "ink", "gum"):
            layers.alpha[idx] = np.maximum(layers.alpha[idx], a * entry.get("opacity", 1.0))
    return len(idx)


def height_to_normal(height, texel_m, strength=1.0):
    """Tangent-space (OpenGL/glTF) normal map from a bottom-up height grid in metres."""
    gx = (np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)) / (2 * texel_m)
    gy = (np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0)) / (2 * texel_m)
    n = np.dstack((-gx * strength, -gy * strength, np.ones_like(height)))
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return (n * 0.5 + 0.5).astype(F)


# ----------------------------------------------------------------- bpy glue

def save_rgba(path, rgba, name=None):
    """Save a bottom-up float RGBA grid as PNG and return the loaded image."""
    import bpy

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    height, width = rgba.shape[:2]
    if rgba.shape[2] == 3:
        rgba = np.dstack((rgba, np.ones((height, width), F)))
    image = bpy.data.images.new(name or path.stem, width, height, alpha=True)
    image.pixels.foreach_set(np.clip(rgba, 0, 1).astype(F).ravel())
    image.filepath_raw = str(path)
    image.file_format = "PNG"
    image.save()
    bpy.data.images.remove(image)
    return load_image(path)


def load_image(path, non_color=False):
    import bpy

    image = bpy.data.images.load(str(path), check_existing=False)
    if non_color:
        image.colorspace_settings.name = "Non-Color"
    return image


def image_pixels(image):
    width, height = image.size
    pixels = np.empty(width * height * 4, F)
    image.pixels.foreach_get(pixels)
    return pixels.reshape(height, width, 4)


def unwrap_atlas(objects, importance=None, margin=0.006):
    """Unique, density-consistent UVs for objects sharing one texture atlas."""
    import bpy

    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        if not obj.data.uv_layers:
            obj.data.uv_layers.new(name="UVMap")
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=radians(60), island_margin=0.0, scale_to_bounds=False)
    bpy.ops.uv.average_islands_scale()
    bpy.ops.object.mode_set(mode="OBJECT")
    for obj in objects:
        factor = 1.0
        for fragment, value in (importance or {}).items():
            if fragment in obj.name:
                factor = value
        if factor != 1.0:
            uv = obj.data.uv_layers.active.data
            coords = np.empty(len(uv) * 2, F)
            uv.foreach_get("uv", coords)
            uv.foreach_set("uv", coords * factor)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(margin=margin, rotate=True)
    bpy.ops.object.mode_set(mode="OBJECT")


POSITION_OFFSET = 10.0


def bake_buffers(objects, width, height, ao_distance=0.3, convex_distance=0.012, samples=6, margin=12):
    """Bake world position, world normal and (object id, AO, convexity) grids.

    Returns position (H, W, 3), normal encoded in [0, 1] (H, W, 3), extra
    (H, W, 4) and an id -> object name table.  Grids are bottom-up.
    """
    import bpy

    scene = bpy.context.scene
    previous_engine = scene.render.engine
    scene.render.engine = "CYCLES"
    # CPU on purpose: headless Metal baking stalls on macOS, and these bakes
    # are simple enough that CPU takes seconds.
    scene.cycles.device = "CPU"

    names = {}
    originals = {}
    bake_mat = bpy.data.materials.new("TEMP_BakeBuffers")
    bake_mat.use_nodes = True
    nt = bake_mat.node_tree
    nt.nodes.clear()
    geometry = nt.nodes.new("ShaderNodeNewGeometry")
    info = nt.nodes.new("ShaderNodeObjectInfo")
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    # Rays per texel = scene samples x node samples; keep it near a hundred.
    ao.samples = 12
    ao.inputs["Distance"].default_value = ao_distance
    convex = nt.nodes.new("ShaderNodeAmbientOcclusion")
    convex.inside = True
    convex.only_local = True
    convex.samples = 6
    convex.inputs["Distance"].default_value = convex_distance
    invert = nt.nodes.new("ShaderNodeMath")
    invert.operation = "SUBTRACT"
    invert.inputs[0].default_value = 1.0
    nt.links.new(convex.outputs["AO"], invert.inputs[1])
    pos_offset = nt.nodes.new("ShaderNodeVectorMath")
    pos_offset.operation = "ADD"
    pos_offset.inputs[1].default_value = (POSITION_OFFSET,) * 3
    nt.links.new(geometry.outputs["Position"], pos_offset.inputs[0])
    nrm_encode = nt.nodes.new("ShaderNodeVectorMath")
    nrm_encode.operation = "MULTIPLY_ADD"
    nrm_encode.inputs[1].default_value = (0.5, 0.5, 0.5)
    nrm_encode.inputs[2].default_value = (0.5, 0.5, 0.5)
    nt.links.new(geometry.outputs["Normal"], nrm_encode.inputs[0])
    combine = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(info.outputs["Object Index"], combine.inputs[0])
    nt.links.new(ao.outputs["AO"], combine.inputs[1])
    nt.links.new(invert.outputs[0], combine.inputs[2])
    emission = nt.nodes.new("ShaderNodeEmission")
    output = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(emission.outputs[0], output.inputs["Surface"])
    target = nt.nodes.new("ShaderNodeTexImage")
    nt.nodes.active = target

    bpy.ops.object.select_all(action="DESELECT")
    for index, obj in enumerate(objects, 1):
        obj.pass_index = index
        names[index] = obj.name
        originals[obj.name] = [slot.material for slot in obj.material_slots]
        for slot in obj.material_slots:
            slot.material = bake_mat
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]

    scene.cycles.samples = 1
    results = []
    for label, socket in (("position", pos_offset.outputs[0]), ("normal", nrm_encode.outputs[0]), ("extra", combine.outputs[0])):
        image = bpy.data.images.new(f"TEMP_bake_{label}", width, height, alpha=True, float_buffer=True)
        image.colorspace_settings.name = "Non-Color"
        target.image = image
        for link in list(emission.inputs["Color"].links):
            nt.links.remove(link)
        nt.links.new(socket, emission.inputs["Color"])
        scene.cycles.samples = samples if label == "extra" else 1
        bpy.ops.object.bake(type="EMIT", margin=margin, use_clear=True)
        results.append(image_pixels(image))
        bpy.data.images.remove(image)

    for obj in objects:
        for slot, material in zip(obj.material_slots, originals[obj.name]):
            slot.material = material
    bpy.data.materials.remove(bake_mat)
    scene.render.engine = previous_engine

    position = results[0][..., :3] - POSITION_OFFSET
    normal = results[1][..., :3]
    extra = results[2]
    return position, normal, extra, names


def gltf_output_group():
    """The node group the glTF exporter reads ambient occlusion from."""
    import bpy

    group = bpy.data.node_groups.get("glTF Material Output")
    if group is None:
        group = bpy.data.node_groups.new("glTF Material Output", "ShaderNodeTree")
        group.interface.new_socket("Occlusion", in_out="INPUT", socket_type="NodeSocketFloat")
    return group


def build_pbr_material(mat, base_image, orm_image=None, normal_image=None, *, blend_alpha=False,
                       emission_strength=0.0, normal_strength=1.0, roughness=0.5, metallic=0.0):
    """Rebuild a material as a glTF-exportable textured Principled BSDF."""
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    shader = nt.nodes.new("ShaderNodeBsdfPrincipled")
    shader.location = (300, 0)
    output = nt.nodes.new("ShaderNodeOutputMaterial")
    output.location = (650, 0)
    nt.links.new(shader.outputs[0], output.inputs["Surface"])

    base = nt.nodes.new("ShaderNodeTexImage")
    base.name = base.label = "Base Color"
    base.image = base_image
    base.location = (-500, 250)
    nt.links.new(base.outputs["Color"], shader.inputs["Base Color"])
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metallic
    if blend_alpha:
        nt.links.new(base.outputs["Alpha"], shader.inputs["Alpha"])
        mat.surface_render_method = "BLENDED"
        mat.use_transparency_overlap = False
    else:
        mat.surface_render_method = "DITHERED"
        base_image.alpha_mode = "CHANNEL_PACKED"

    if orm_image is not None:
        orm = nt.nodes.new("ShaderNodeTexImage")
        orm.name = orm.label = "ORM"
        orm.image = orm_image
        orm.location = (-500, -50)
        split = nt.nodes.new("ShaderNodeSeparateColor")
        split.name = "ORM Split"
        split.location = (-200, -50)
        nt.links.new(orm.outputs["Color"], split.inputs["Color"])
        nt.links.new(split.outputs["Green"], shader.inputs["Roughness"])
        nt.links.new(split.outputs["Blue"], shader.inputs["Metallic"])
        settings = nt.nodes.new("ShaderNodeGroup")
        settings.node_tree = gltf_output_group()
        settings.location = (300, -450)
        nt.links.new(split.outputs["Red"], settings.inputs["Occlusion"])

    if normal_image is not None:
        normal_tex = nt.nodes.new("ShaderNodeTexImage")
        normal_tex.name = normal_tex.label = "Normal"
        normal_tex.image = normal_image
        normal_tex.location = (-500, -350)
        normal_map = nt.nodes.new("ShaderNodeNormalMap")
        normal_map.inputs["Strength"].default_value = normal_strength
        normal_map.location = (-200, -350)
        nt.links.new(normal_tex.outputs["Color"], normal_map.inputs["Color"])
        nt.links.new(normal_map.outputs["Normal"], shader.inputs["Normal"])

    if emission_strength > 0:
        nt.links.new(base.outputs["Color"], shader.inputs["Emission Color"])
        shader.inputs["Emission Strength"].default_value = emission_strength
    return mat

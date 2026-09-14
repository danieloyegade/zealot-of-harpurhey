"""Print artwork and the reusable urban decal library for the bus-shelter pass.

Signage is laid out as flat vector artwork in a temporary Blender scene and
rendered through an orthographic camera, so type stays crisp and the pipeline
needs no image library beyond Blender.  Ageing -- fading, paper grain, creases,
dirt, lamp banding -- is applied afterwards in numpy.

Layouts reconstruct what is legible in references/architecture/bus-stop/
Hires2.jpg.  Fine print that is illegible in the photograph is represented as
print bars rather than invented copy.  The advert keeps the photographed
headline and palette but omits the manufacturer's trade marks.
"""

import json
from math import cos, pi, sin
from pathlib import Path

import bpy
import numpy as np

from surfaceWeathering import (
    F,
    fbm2,
    image_pixels,
    noise2,
    polyline_coverage,
    smoothstep,
    srgb_decode,
    srgb_encode,
)

FONT_DIR = Path("/System/Library/Fonts/Supplemental")
FONT_FILES = {
    "arial": "Arial.ttf",
    "arial_bold": "Arial Bold.ttf",
    "black": "Arial Black.ttf",
    "rounded": "Arial Rounded Bold.ttf",
    "georgia_bold": "Georgia Bold.ttf",
}

INK = (0.07, 0.07, 0.075)
WHITE = (0.97, 0.97, 0.95)


# --------------------------------------------------------------- print scene

class PrintCanvas:
    """Flat print layout in pixel units with a top-left origin."""

    def __init__(self, name, width, height):
        self.width, self.height = width, height
        self.scene = scene = bpy.data.scenes.new(f"PRINT_{name}")
        scene.render.engine = "BLENDER_EEVEE"
        scene.render.resolution_x = width
        scene.render.resolution_y = height
        scene.render.resolution_percentage = 100
        scene.render.film_transparent = True
        scene.render.image_settings.file_format = "PNG"
        scene.render.image_settings.color_mode = "RGBA"
        scene.view_settings.view_transform = "Standard"
        scene.view_settings.look = "None"
        scene.display_settings.display_device = "sRGB"
        scene.eevee.taa_render_samples = 16
        scene.world = bpy.data.worlds.new(f"PRINT_{name}_World")
        scene.world.color = (0, 0, 0)
        camera_data = bpy.data.cameras.new(f"PRINT_{name}_Camera")
        camera_data.type = "ORTHO"
        camera_data.ortho_scale = max(width, height)
        camera_data.clip_end = 200
        camera = bpy.data.objects.new(f"PRINT_{name}_Camera", camera_data)
        camera.location = (width / 2, height / 2, 100)
        scene.collection.objects.link(camera)
        scene.camera = camera
        self.data = [camera_data, scene.world]
        self.objects = [camera]
        self.materials = {}
        self.depth = 0.0

    def _material(self, color, alpha=1.0):
        key = (tuple(round(c, 4) for c in color), round(alpha, 3))
        if key not in self.materials:
            mat = bpy.data.materials.new(f"PRINT_ink_{len(self.materials)}")
            mat.use_nodes = True
            nt = mat.node_tree
            nt.nodes.clear()
            emission = nt.nodes.new("ShaderNodeEmission")
            emission.inputs["Color"].default_value = (*srgb_decode(np.array(color, F)), 1.0)
            output = nt.nodes.new("ShaderNodeOutputMaterial")
            if alpha < 1.0:
                clear = nt.nodes.new("ShaderNodeBsdfTransparent")
                mix = nt.nodes.new("ShaderNodeMixShader")
                mix.inputs["Fac"].default_value = alpha
                nt.links.new(clear.outputs[0], mix.inputs[1])
                nt.links.new(emission.outputs[0], mix.inputs[2])
                nt.links.new(mix.outputs[0], output.inputs["Surface"])
                mat.surface_render_method = "BLENDED"
            else:
                nt.links.new(emission.outputs[0], output.inputs["Surface"])
            self.materials[key] = mat
        return self.materials[key]

    def _link(self, obj, data, color, alpha):
        data.materials.append(self._material(color, alpha))
        self.depth += 0.02
        obj.location.z = self.depth
        self.scene.collection.objects.link(obj)
        self.objects.append(obj)
        self.data.append(data)
        return obj

    def shape(self, outlines, color, alpha=1.0):
        """Filled 2D shape from one or more closed outlines (later ones cut holes)."""
        curve = bpy.data.curves.new("PRINT_shape", "CURVE")
        curve.dimensions = "2D"
        curve.fill_mode = "BOTH"
        for outline in outlines:
            spline = curve.splines.new("POLY")
            spline.points.add(len(outline) - 1)
            for point, (x, y) in zip(spline.points, outline):
                point.co = (x, self.height - y, 0, 1)
            spline.use_cyclic_u = True
        return self._link(bpy.data.objects.new("PRINT_shape", curve), curve, color, alpha)

    def rect(self, x, y, w, h, color, alpha=1.0):
        return self.shape([[(x, y), (x + w, y), (x + w, y + h), (x, y + h)]], color, alpha)

    def poly(self, points, color, alpha=1.0):
        return self.shape([points], color, alpha)

    @staticmethod
    def _circle_points(cx, cy, r, segments=72):
        return [(cx + r * cos(2 * pi * i / segments), cy + r * sin(2 * pi * i / segments)) for i in range(segments)]

    def circle(self, cx, cy, r, color, alpha=1.0):
        return self.shape([self._circle_points(cx, cy, r)], color, alpha)

    def ring(self, cx, cy, outer, inner, color, alpha=1.0):
        return self.shape([self._circle_points(cx, cy, outer), self._circle_points(cx, cy, inner)[::-1]], color, alpha)

    def line(self, x0, y0, x1, y1, width, color, alpha=1.0):
        dx, dy = x1 - x0, y1 - y0
        length = max((dx * dx + dy * dy) ** 0.5, 1e-6)
        nx, ny = -dy / length * width / 2, dx / length * width / 2
        return self.poly([(x0 + nx, y0 + ny), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)], color, alpha)

    def text(self, body, x, baseline, size, color, font="arial", align="LEFT", scale_x=1.0):
        curve = bpy.data.curves.new("PRINT_text", "FONT")
        curve.body = body
        path = FONT_DIR / FONT_FILES[font]
        if path.exists():
            curve.font = bpy.data.fonts.load(str(path), check_existing=True)
        curve.size = size
        curve.align_x = align
        obj = bpy.data.objects.new("PRINT_text", curve)
        obj.location = (x, self.height - baseline, 0)
        obj.scale = (scale_x, 1, 1)
        return self._link(obj, curve, color, 1.0)

    def print_bars(self, x, y, width, lines, color, rng, bar=9, step=22, alpha=1.0):
        """Fine print too small to read in the photograph, set as ruled bars."""
        for i in range(lines):
            length = width * rng.uniform(0.45, 1.0) if i < lines - 1 else width * rng.uniform(0.25, 0.6)
            self.rect(x, y + i * step, length, bar, color, alpha)
        return y + lines * step

    def render(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True, scene=self.scene.name)
        image = bpy.data.images.load(str(path), check_existing=False)
        pixels = image_pixels(image).copy()
        bpy.data.images.remove(image)
        self.dispose()
        return pixels

    def dispose(self):
        for obj in self.objects:
            bpy.data.objects.remove(obj, do_unlink=True)
        for data in self.data:
            collection = bpy.data.curves if isinstance(data, bpy.types.Curve) else None
            if collection is not None and data.users == 0:
                collection.remove(data)
        for mat in self.materials.values():
            bpy.data.materials.remove(mat)
        bpy.data.scenes.remove(self.scene)


# ----------------------------------------------------------------- utilities

def pixel_grid(height, width):
    y, x = np.mgrid[0:height, 0:width].astype(F)
    return x + 0.5, y + 0.5


def over(base_rgb, layer_rgba):
    a = layer_rgba[..., 3:4]
    return base_rgb * (1 - a) + layer_rgba[..., :3] * a


def flat_noise(x, y, scale, seed, octaves=3):
    q = np.stack((x.ravel() / scale, y.ravel() / scale), axis=1)
    return fbm2(q, octaves, seed).reshape(x.shape)


def soften(image):
    """One-pixel optical softness so vector artwork reads as ink on paper."""
    neighbours = sum(np.roll(image, shift, axis) for shift in (-1, 1) for axis in (0, 1))
    return image * 0.5 + neighbours * 0.125


def desaturate(linear, amount):
    luma = linear @ np.array((0.2126, 0.7152, 0.0722), F)
    return linear * (1 - amount) + luma[..., None] * amount


def crease(x, y, a, b, width):
    """Signed ridge profile across a fold line from a to b (pixel units)."""
    ax, ay = a
    bx, by = b
    nx, ny = -(by - ay), bx - ax
    length = (nx * nx + ny * ny) ** 0.5
    d = ((x - ax) * nx + (y - ay) * ny) / length
    return np.exp(-(d / width) ** 2), np.tanh(d / (width * 0.6)) * np.exp(-(d / (width * 2.5)) ** 2)


# ------------------------------------------------------------------ artwork

def timetable_artwork(work_dir, seed=3):
    """Lancashire County Council 'When's the next bus?' timetable poster."""
    rng = np.random.default_rng(seed)
    W, H = 1100, 2024
    paper = (0.93, 0.925, 0.875)
    navy = (0.11, 0.14, 0.30)
    red = (0.86, 0.33, 0.22)
    c = PrintCanvas("timetable", W, H)
    c.rect(0, 0, W, H, paper)
    c.rect(0, 0, W, 150, (0.09, 0.14, 0.12))
    c.text("www.lancashire.gov.uk", 46, 94, 38, (0.82, 0.86, 0.83), "arial")

    c.rect(700, 20, 362, 220, (0.985, 0.985, 0.975))
    c.text("Lancashire", 716, 104, 66, navy, "arial_bold", scale_x=0.92)
    c.text("County", 778, 158, 38, navy, "arial")
    c.text("Council", 778, 204, 38, navy, "arial")
    c.ring(1004, 176, 42, 36, navy)
    c.circle(1004, 176, 29, navy)
    for i in range(8):
        angle = 2 * pi * i / 8
        c.circle(1004 + 17 * cos(angle), 176 + 17 * sin(angle), 6.5, WHITE)
    c.circle(1004, 176, 6, WHITE)

    c.text("When’s the", 58, 392, 118, INK, "rounded")
    c.text("next bus?", 168, 600, 212, INK, "rounded", scale_x=0.86)

    c.rect(40, 640, 520, 100, INK)
    c.text("Bus times", 88, 713, 64, WHITE, "arial_bold")
    c.rect(40, 740, 520, 800, (0.975, 0.975, 0.955))
    c.rect(58, 760, 484, 42, (0.52, 0.08, 0.12))
    c.print_bars(72, 773, 300, 1, WHITE, rng, bar=12)
    y = 826
    for _ in range(7):
        c.rect(58, y, 484, 17, INK)
        y += 32
        y = c.print_bars(64, y, 440, int(rng.integers(2, 5)), (0.33, 0.33, 0.34), rng, bar=8, step=21)
        y += 14

    c.rect(40, 1556, 520, 112, (0.79, 0.85, 0.24))
    c.rect(58, 1572, 42, 80, INK)
    c.rect(64, 1582, 30, 54, (0.72, 0.82, 0.86))
    c.print_bars(118, 1576, 420, 3, (0.12, 0.16, 0.08), rng, bar=11, step=25)

    c.rect(40, 1684, 520, 216, (0.12, 0.54, 0.30))
    for word, x, baseline, size in (("When’s", 64, 1752, 54), ("the", 96, 1800, 40), ("next", 136, 1846, 54), ("bus?", 160, 1890, 54)):
        c.text(word, x, baseline, size, (0.95, 0.97, 0.72), "rounded")
    c.poly([(330, 1900), (372, 1900), (430, 1790), (392, 1770)], (0.80, 0.14, 0.12))
    c.circle(418, 1772, 30, (0.90, 0.74, 0.60))
    c.poly([(420, 1700), (480, 1690), (500, 1800), (440, 1812)], INK)
    c.poly([(428, 1712), (474, 1704), (490, 1790), (444, 1799)], (0.62, 0.80, 0.86))

    c.rect(40, 1914, 520, 92, INK)
    c.rect(330, 1928, 196, 62, (0.985, 0.985, 0.975))
    c.print_bars(344, 1942, 160, 2, (0.75, 0.10, 0.12), rng, bar=10, step=22)
    c.print_bars(62, 1936, 230, 2, (0.8, 0.8, 0.8), rng, bar=8, step=24)

    c.rect(590, 640, 472, 1344, red)
    for cx in (670, 826, 982):
        c.rect(cx - 62, 690, 124, 176, INK)
    c.rect(620, 706, 100, 64, (0.93, 0.93, 0.9))
    c.rect(622, 694, 96, 8, (0.95, 0.6, 0.2))
    for x in (626, 700):
        c.circle(x + 7, 842, 9, WHITE)
    c.line(800, 690, 826, 660, 5, INK)
    c.line(852, 690, 826, 660, 5, INK)
    c.rect(780, 712, 92, 70, (0.93, 0.93, 0.9))
    c.rect(778, 820, 96, 12, (0.85, 0.85, 0.82))
    c.poly([(920, 866), (920, 740), (950, 690), (1014, 690), (1044, 740), (1044, 866)], INK)
    c.rect(940, 732, 84, 56, (0.93, 0.93, 0.9))
    for x in (944, 1012):
        c.circle(x + 4, 842, 9, WHITE)
    for i, line in enumerate(("Your one stop for", "information about", "public transport")):
        c.text(line, 826, 956 + i * 50, 40, WHITE, "arial_bold", align="CENTER")
    y = 1110
    for lines in (4, 3, 2, 4, 3):
        c.circle(622, y + 5, 5, WHITE)
        y = c.print_bars(640, y, 390, lines, (0.99, 0.94, 0.9), rng, bar=10, step=25)
        y += 26
    c.text("Please signal clearly", 826, 1748, 40, INK, "black", align="CENTER", scale_x=0.8)
    c.text("to stop the bus", 826, 1800, 40, INK, "black", align="CENTER", scale_x=0.8)
    hand = [(640, 1880), (820, 1880), (960, 1886), (962, 1904), (840, 1906), (966, 1912), (966, 1930), (842, 1932),
            (958, 1938), (956, 1954), (836, 1956), (930, 1962), (926, 1976), (720, 1978), (640, 1960)]
    c.poly(hand, (0.95, 0.88, 0.70))

    art = c.render(work_dir / "timetable-print.png")
    return art[..., :3], (W, H)


def no_smoking_artwork(work_dir):
    W, H = 440, 520
    red = (0.74, 0.11, 0.11)
    border = (0.24, 0.29, 0.27)
    c = PrintCanvas("nosmoking", W, H)
    c.rect(0, 0, W, H, (0.945, 0.95, 0.935))
    for x, y, w, h in ((18, 18, 404, 7), (18, 495, 404, 7), (18, 18, 7, 484), (415, 18, 7, 484)):
        c.rect(x, y, w, h, border)
    for cx, cy, r in ((262, 150, 17), (282, 128, 13), (246, 124, 11)):
        c.circle(cx, cy, r, (0.62, 0.64, 0.62))
    c.rect(118, 196, 184, 28, INK)
    c.rect(118, 196, 36, 28, (0.72, 0.52, 0.32))
    c.ring(220, 190, 132, 110, red)
    c.line(136, 108, 304, 272, 22, red)
    c.text("NO SMOKING", 220, 392, 60, red, "black", align="CENTER", scale_x=0.8)
    c.text("It is against the law to", 220, 438, 25, INK, "arial_bold", align="CENTER")
    c.text("smoke in this bus shelter", 220, 470, 25, INK, "arial_bold", align="CENTER")
    art = c.render(work_dir / "no-smoking-print.png")
    return art[..., :3], (W, H)


def stop_number_artwork(work_dir):
    """Stop number vinyl.  White marks live digits, red marks the ghost of a removed one."""
    W, H = 900, 256
    c = PrintCanvas("stopnumber", W, H)
    c.text("3309", 30, 196, 168, (1, 1, 1), "arial_bold")
    c.text("0", 392, 196, 168, (1, 0, 0), "arial_bold")
    c.text("0083", 494, 196, 168, (1, 1, 1), "arial_bold")
    art = c.render(work_dir / "stop-number-print.png")
    live = np.clip(art[..., 1] * art[..., 3], 0, 1)
    ghost = np.clip((art[..., 0] - art[..., 1]) * art[..., 3], 0, 1)
    return live, ghost, (W, H)


def advert_artwork(work_dir):
    W, H = 1024, 1432
    cream = (0.99, 0.96, 0.93)
    gold = (0.86, 0.66, 0.32)
    c = PrintCanvas("advert", W, H)
    for i, word in enumerate(("The richest", "creamiest", "chocolate")):
        c.text(word, 512, 330 + i * 150, 146, cream, "georgia_bold", align="CENTER", scale_x=0.8)
    for x0, length in ((372, 70), (452, 118), (580, 72)):
        c.rect(x0, 698, length, 10, cream, 0.55)
    center_x, center_y, half, angle = 512, 968, 158, -0.1
    corners = [(-half, -half), (half, -half), (half, half), (-half, half)]
    c.poly([(center_x + x * cos(angle) - y * sin(angle), center_y + x * sin(angle) + y * cos(angle)) for x, y in corners], (0.30, 0.08, 0.36))
    inner = [(x * 0.9, y * 0.9) for x, y in corners]
    c.shape([
        [(center_x + x * cos(angle) - y * sin(angle), center_y + x * sin(angle) + y * cos(angle)) for x, y in corners],
        [(center_x + x * cos(angle) - y * sin(angle), center_y + x * sin(angle) + y * cos(angle)) for x, y in inner][::-1],
    ], gold, 0.9)
    c.ring(468, 920, 84, 72, gold)
    c.ring(574, 1000, 62, 53, gold)
    c.poly([(548, 890), (616, 884), (606, 1052), (566, 1056)], (0.97, 0.93, 0.85))
    c.poly([(560, 1060), (660, 1030), (690, 1110), (590, 1140)], (0.36, 0.20, 0.10))
    for x0, length in ((430, 46), (486, 64), (560, 36)):
        c.rect(x0, 1238, length, 9, cream, 0.55)
    art = c.render(work_dir / "advert-print.png")
    return art, (W, H)


# ------------------------------------------------------------ ageing passes

def age_timetable(rgb, seed=5):
    H, W = rgb.shape[:2]
    x, y = pixel_grid(H, W)
    top = H - y
    lin = srgb_decode(rgb)
    paper = srgb_decode(np.array((0.93, 0.925, 0.875), F))
    lin = soften(lin)
    lin = desaturate(lin, 0.12) * 0.96 + paper * 0.04
    bleach = smoothstep(0.55 * H, 0.0, top) * 0.05
    lin = lin * (1 - bleach[..., None]) + paper * bleach[..., None]
    fibre = flat_noise(x, y, 3.0, seed, 2) - 0.5
    grain = noise2(np.stack((x.ravel(), y.ravel()), axis=1) * 0.9, seed + 1).reshape(H, W) - 0.5
    lin *= (1 + 0.05 * fibre + 0.08 * grain)[..., None]
    scuffs = smoothstep(0.93, 0.99, flat_noise(x * 0.08, y * 1.6, 4, seed + 6, 2)) * smoothstep(0.5, 0.7, flat_noise(x, y, 160, seed + 7, 2))
    lin = lin * (1 - 0.35 * scuffs[..., None]) + paper * (0.35 * scuffs)[..., None]
    fold_h, fold_h_shade = crease(x, y, (0, H * 0.52), (W, H * 0.505), 5.0)
    fold_v, fold_v_shade = crease(x, y, (W * 0.49, 0), (W * 0.5, H), 5.0)
    lin *= (1 + 0.05 * fold_h_shade + 0.04 * fold_v_shade - 0.03 * (fold_h + fold_v))[..., None]
    edge = np.minimum.reduce((x, W - x, y, top))
    edge_dirt = np.exp(-edge / 26.0) * (0.55 + 0.45 * flat_noise(x, y, 18, seed + 2))
    wick = smoothstep(90, 0, y) * (0.5 + 0.5 * flat_noise(x, y, 30, seed + 3))
    tide = np.exp(-((y - 70 - 25 * flat_noise(x, y, 120, seed + 4)) / 3.0) ** 2) * smoothstep(W * 0.35, W * 0.9, x)
    dirt_color = srgb_decode(np.array((0.42, 0.36, 0.27), F))
    amount = np.clip(0.4 * edge_dirt + 0.3 * wick + 0.35 * tide, 0, 1)[..., None]
    lin = lin * (1 - amount) + lin * dirt_color * amount * 1.4
    height = 0.00025 * fold_h + 0.0002 * fold_v + 0.00003 * fibre
    rough = 0.82 + 0.08 * edge_dirt
    return np.clip(lin, 0, 1), rough, height


def age_no_smoking(rgb, seed=9):
    H, W = rgb.shape[:2]
    x, y = pixel_grid(H, W)
    lin = srgb_decode(rgb)
    red = (lin[..., 0] > lin[..., 1] * 2.2)[..., None]
    lin = np.where(red, desaturate(lin, 0.2) * 0.85 + srgb_decode(np.array((0.9, 0.6, 0.58), F)) * 0.15, lin)
    edge = np.minimum.reduce((x, W - x, y, H - y))
    dirt = np.exp(-edge / 20.0) * (0.5 + 0.5 * flat_noise(x, y, 12, seed)) + smoothstep(120, 0, y) * 0.35
    lin *= (1 - 0.35 * np.clip(dirt, 0, 1))[..., None]
    height = np.zeros((H, W), F)
    rough = 0.42 + 0.25 * np.clip(dirt, 0, 1)
    for cx, cy in ((34, 34), (W - 34, 34), (34, H - 34), (W - 34, H - 34)):
        r = np.hypot(x - cx, y - cy)
        head = smoothstep(11, 8, r)
        lin = lin * (1 - head[..., None]) + srgb_decode(np.array((0.36, 0.36, 0.35), F)) * head[..., None]
        lin *= (1 - 0.5 * np.exp(-((r - 12) / 2.5) ** 2))[..., None]
        height += 0.0012 * np.sqrt(np.clip(1 - (r / 10) ** 2, 0, 1))
        rough = np.where(head > 0.5, 0.5, rough)
    rng = np.random.default_rng(seed)
    for _ in range(9):
        a = rng.uniform((60, 60), (W - 60, H - 60))
        b = a + rng.normal(0, 60, 2)
        cov = polyline_coverage(x.ravel(), y.ravel(), [a, b], 1.2, 1.0).reshape(H, W)
        lin += (0.12 * cov)[..., None]
        rough += 0.25 * cov
        height -= 0.00004 * cov
    return np.clip(lin, 0, 1), np.clip(rough, 0, 1), height


def age_stop_number(live, ghost, seed=13):
    H, W = live.shape
    x, y = pixel_grid(H, W)
    paint = srgb_decode(np.array((0.20, 0.235, 0.21), F))
    vinyl = srgb_decode(np.array((0.90, 0.88, 0.79), F))
    residue = srgb_decode(np.array((0.36, 0.38, 0.30), F))
    wear = flat_noise(x, y, 5, seed, 2)
    holes = smoothstep(0.24, 0.18, wear)
    torn = smoothstep(W * 0.84, W * 0.88, x + (H - y) * 0.9 - 120)
    live_cov = np.clip(live * (1 - holes) * (1 - torn), 0, 1)
    dirt = 0.78 + 0.22 * flat_noise(x, y, 24, seed + 1)
    streak = flat_noise(x * 2.0, y * 0.12, 6, seed + 2, 2)
    lin = paint[None, None] * (dirt * (1 - 0.12 * smoothstep(0.6, 0.85, streak)))[..., None]
    lin = lin * (1 - ghost[..., None] * 0.55) + residue * (ghost * 0.55)[..., None]
    lin = lin * (1 - live_cov[..., None]) + vinyl * (live_cov * dirt)[..., None]
    rough = 0.62 * (1 - live_cov) + 0.34 * live_cov + 0.1 * ghost
    height = 0.00012 * live_cov
    return np.clip(lin, 0, 1), rough, height


def age_advert(art, seed=17):
    H, W = art.shape[:2]
    x, y = pixel_grid(H, W)
    u, v = x / W, y / H
    radial = np.hypot((u - 0.5) * 1.3, (v - 0.55) * 0.9)
    centre = srgb_decode(np.array((0.95, 0.80, 0.92), F))
    rim = srgb_decode(np.array((0.62, 0.36, 0.63), F))
    t = smoothstep(0.05, 0.75, radial)[..., None]
    bg = centre * (1 - t) + rim * t
    sheen = np.sin(u * 9.0 + v * 4.0 + 3.0 * flat_noise(x, y, 180, seed)) * 0.05
    bg *= (1 + sheen)[..., None]
    lin = soften(bg * (1 - art[..., 3:4]) + srgb_decode(art[..., :3]) * art[..., 3:4])
    grain = noise2(np.stack((x.ravel(), y.ravel()), axis=1) * 0.8, seed + 2).reshape(H, W) - 0.5
    lin *= (1 + 0.05 * grain)[..., None]
    tubes = sum(np.exp(-((u - xt) / 0.08) ** 2) for xt in (0.2, 0.5, 0.8)) * 0.08
    corner = smoothstep(0.35, 0.75, np.hypot(u - 0.5, v - 0.5))
    lamp = 0.9 + tubes - 0.28 * corner
    lin *= lamp[..., None]
    rng = np.random.default_rng(seed)
    for _ in range(5):
        cx, cy = rng.uniform(80, W - 80), rng.uniform(14, 48)
        r = np.hypot((x - cx) / 7, (y - cy) / 4)
        body = smoothstep(1.0, 0.6, r)
        for leg in range(6):
            angle = rng.uniform(0, 2 * pi)
            a = (cx, cy)
            b = (cx + 14 * cos(angle), cy + 14 * sin(angle))
            body = np.maximum(body, polyline_coverage(x.ravel(), y.ravel(), [a, b], 1.4, 1.0).reshape(H, W) * 0.8)
        lin *= (1 - 0.85 * body)[..., None]
    dust = smoothstep(70, 0, y) * 0.25 * flat_noise(x, y, 14, seed + 1)
    lin *= (1 - dust)[..., None]
    return np.clip(lin, 0, 1)


def light_diffuser(size=512, seed=21):
    """Warm under-roof fixture diffuser (lower 75%) and dark metal rim (top band)."""
    x, y = pixel_grid(size, size)
    u, v = x / size, y / size
    warm = srgb_decode(np.array((1.0, 0.93, 0.78), F))
    yellow = srgb_decode(np.array((0.86, 0.72, 0.46), F))
    edge = np.minimum.reduce((u - 0.02, 0.98 - u, v - 0.02, 0.74 - v))
    yellowing = smoothstep(0.12, 0.0, edge)
    lin = warm * (1 - 0.35 * yellowing[..., None]) + yellow * (0.35 * yellowing)[..., None]
    lin *= (0.88 + 0.12 * flat_noise(x, y, 20, seed))[..., None]
    rng = np.random.default_rng(seed)
    specks = np.zeros((size, size), F)
    for _ in range(26):
        cx, cy = rng.uniform(0.05, 0.95) * size, rng.uniform(0.04, 0.2) * size
        specks = np.maximum(specks, smoothstep(1.0, 0.3, np.hypot((x - cx) / rng.uniform(2, 5), (y - cy) / rng.uniform(1.5, 3.5))))
    lin *= (1 - 0.8 * specks)[..., None]
    rim = v > 0.76
    lin[rim] = srgb_decode(np.array((0.09, 0.10, 0.095), F))
    rough = np.where(rim, 0.55, 0.35 + 0.3 * specks)
    return np.clip(lin, 0, 1), rough


# ------------------------------------------------------- urban decal library

def build_urban_decal_library(out_png, out_json, seed=31):
    """Reusable 1024 px RGBA atlas of small street ephemera.

    Cells are 256 px.  Each entry records its cell rectangle (bottom-up pixel
    coordinates), a material kind and physical hints so bake-time or runtime
    decal systems respond consistently.  Nothing here carries legible copy.
    """
    cell = 256
    atlas = np.zeros((1024, 1024, 4), F)
    meta = {}
    rng = np.random.default_rng(seed)
    x, y = pixel_grid(cell, cell)
    u, v = x / cell, y / cell

    def noise(scale, s, octaves=3):
        return flat_noise(x, y, scale, seed + s, octaves)

    def put(index, key, rgba, kind, roughness, thickness, opacity=1.0):
        col, row = index % 4, index // 4
        x0, y0 = col * cell, row * cell
        atlas[y0:y0 + cell, x0:x0 + cell] = rgba
        meta[key] = {"cell": [x0, y0, cell, cell], "kind": kind, "roughness": roughness,
                     "thickness": thickness, "opacity": opacity}

    def rgba(color, alpha):
        out = np.zeros((cell, cell, 4), F)
        out[..., :3] = color
        out[..., 3] = np.clip(alpha, 0, 1)
        return out

    # 0 torn paper remnant with adhesive where the paper has gone
    rect = np.maximum(np.abs(u - 0.5) - 0.34, np.abs(v - 0.5) - 0.26)
    torn = rect + 0.1 * (noise(40, 1) - 0.5) + 0.22 * smoothstep(0.35, 0.95, u + v * 0.6) * noise(22, 2)
    paper = smoothstep(0.012, -0.004, torn) * smoothstep(0.35, 0.55, noise(3, 3, 2) + smoothstep(0.0, -0.01, torn))
    adhesive = smoothstep(0.01, -0.01, rect) * 0.3
    color = np.where(paper[..., None] > 0.5, np.array((0.91, 0.9, 0.84), F), np.array((0.58, 0.56, 0.5), F))
    color = color * (0.85 + 0.15 * noise(10, 4))[..., None]
    put(0, "torn_paper", rgba(color, np.maximum(paper, adhesive)), "paper", 0.86, 0.00012)

    # 1 shipping-label fragment with barcode
    label = smoothstep(0.01, -0.01, np.maximum(np.abs(u - 0.5) - 0.36, np.abs(v - 0.52) - 0.24))
    label *= smoothstep(-0.02, 0.02, (0.78 - u) + (v - 0.3) * 0.9 + 0.05 * (noise(18, 5) - 0.5))
    bars = (np.sin(u * 190 + 6 * np.floor(u * 23)) > 0.2) & (v > 0.55) & (v < 0.7) & (u > 0.22) & (u < 0.74)
    lines = (np.abs(((v - 0.32) * 36) % 2 - 1) < 0.35) & (v > 0.3) & (v < 0.5) & (u > 0.2) & (u < 0.2 + 0.5 * noise(60, 6, 1))
    color = np.full((cell, cell, 3), (0.9, 0.89, 0.84), F)
    color[bars | lines] = (0.12, 0.12, 0.12)
    color *= (0.8 + 0.2 * noise(12, 7))[..., None]
    put(1, "shipping_label", rgba(color, label), "paper", 0.7, 0.00012)

    # 2 partially removed printed sticker
    disc = smoothstep(0.38, 0.36, np.hypot(u - 0.5, v - 0.5))
    kept = smoothstep(0.42, 0.5, noise(20, 8))
    backing = smoothstep(0.3, 0.4, noise(8, 9))
    color = np.where(kept[..., None] > 0.5, np.array((0.14, 0.48, 0.3), F), np.array((0.88, 0.87, 0.82), F))
    alpha = disc * np.maximum(kept, backing * 0.9 + 0.2)
    put(2, "removed_sticker", rgba(color, alpha), "paper", 0.78, 0.0001)

    # 3 adhesive residue rectangle with scrape marks and lint
    box = smoothstep(0.012, -0.012, np.maximum(np.abs(u - 0.5) - 0.38, np.abs(v - 0.5) - 0.22))
    scrape = 0.6 + 0.4 * np.abs(np.sin(v * 70 + 4 * noise(30, 10)))
    lint = smoothstep(0.93, 0.97, noise(1.6, 11, 1))
    alpha = box * (0.35 + 0.25 * noise(9, 12)) * scrape + box * lint * 0.6
    color = np.where(lint[..., None] > 0.3, np.array((0.2, 0.2, 0.2), F), np.array((0.62, 0.6, 0.53), F))
    put(3, "adhesive_residue", rgba(color, alpha), "residue", 0.72, 0.00004, 0.6)

    # 4 faded event sticker: colour blocks and bars, no copy
    body = smoothstep(0.01, -0.01, np.maximum(np.abs(u - 0.5) - 0.4, np.abs(v - 0.5) - 0.3))
    body *= smoothstep(-0.02, 0.02, (u - 0.18) + (0.8 - v) * 0.5 + 0.06 * noise(16, 13))
    color = np.where((v > 0.5)[..., None], np.array((0.85, 0.42, 0.66), F), np.array((0.42, 0.74, 0.82), F))
    bars = ((np.abs(((v - 0.25) * 22) % 2 - 1) < 0.4) & (u > 0.2) & (u < 0.75) & (v < 0.45)) | ((u > 0.2) & (u < 0.62) & (v > 0.58) & (v < 0.7))
    color[bars] = (0.96, 0.95, 0.92)
    color = color * 0.55 + 0.45 * np.array((0.93, 0.92, 0.88), F)
    color *= (0.85 + 0.15 * noise(7, 14))[..., None]
    put(4, "faded_event_sticker", rgba(color, body), "paper", 0.6, 0.0001)

    # 5 marker tag
    coverage = np.zeros(cell * cell, F)
    for _ in range(5):
        points = [rng.uniform(0.25, 0.75, 2) * cell]
        heading = rng.uniform(0, 2 * pi)
        for _ in range(int(rng.integers(10, 22))):
            heading += rng.normal(0, 0.7)
            step = np.array((cos(heading), sin(heading))) * 9
            points.append(np.clip(points[-1] + step, 0.12 * cell, 0.88 * cell))
        coverage = np.maximum(coverage, polyline_coverage(x.ravel(), y.ravel(), points, rng.uniform(4, 7), 1.0))
    coverage = coverage.reshape(cell, cell) * (0.75 + 0.25 * noise(4, 15))
    put(5, "marker_tag", rgba(np.array((0.05, 0.05, 0.07), F), coverage), "ink", 0.42, 0.00002)

    # 6 scratched initials (etched strokes -- a roughness/normal mask)
    coverage = np.zeros(cell * cell, F)
    strokes = [[(60, 70), (60, 190), (110, 190), (110, 130), (60, 130)],
               [(140, 70), (140, 190)], [(140, 130), (200, 70)], [(140, 130), (200, 190)],
               [(40, 40), (220, 52)]]
    for stroke in strokes:
        jitter = [np.array(p, F) + rng.normal(0, 2.5, 2) for p in stroke]
        coverage = np.maximum(coverage, polyline_coverage(x.ravel(), y.ravel(), jitter, 2.2, 1.0))
    put(6, "scratched_initials", rgba(np.array((1, 1, 1), F), coverage.reshape(cell, cell)), "scratch", 0.8, 0.0)

    # 7 tape residue strip
    strip = smoothstep(0.012, -0.012, np.abs(v - 0.5 - 0.03 * (u - 0.5)) - 0.1)
    ends = smoothstep(0.0, 0.03, u - 0.08 - 0.04 * noise(10, 16)) * smoothstep(0.0, 0.03, 0.92 - u - 0.04 * noise(10, 17))
    edge_dirt = np.exp(-((np.abs(v - 0.5 - 0.03 * (u - 0.5)) - 0.1) / 0.012) ** 2)
    alpha = strip * ends * (0.28 + 0.2 * noise(6, 18)) + edge_dirt * ends * 0.35
    color = np.where(edge_dirt[..., None] > 0.4, np.array((0.25, 0.22, 0.17), F), np.array((0.78, 0.7, 0.46), F))
    put(7, "tape_residue", rgba(color, alpha), "tape", 0.55, 0.00005, 0.7)

    # 8 round sticker remnant
    r = np.hypot(u - 0.5, v - 0.5)
    angle = np.arctan2(v - 0.5, u - 0.5)
    ring = smoothstep(0.37, 0.35, r) * smoothstep(0.28, 0.3, r) * (np.sin(angle * 3 + 1) > -0.3)
    alpha = ring * (0.7 + 0.3 * noise(8, 19)) + smoothstep(0.3, 0.28, r) * 0.18
    put(8, "round_sticker_remnant", rgba(np.array((0.9, 0.89, 0.85), F), alpha), "paper", 0.8, 0.0001)

    # 9 flattened chewing gum
    blob = smoothstep(0.3, 0.26, r + 0.05 * (noise(14, 20) - 0.5))
    color = np.array((0.2, 0.2, 0.19), F) * (0.8 + 0.4 * smoothstep(0.25, 0.0, r))[..., None]
    put(9, "chewing_gum", rgba(color, blob * 0.9), "gum", 0.6, 0.0006)

    out_png = Path(out_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    image = bpy.data.images.new("urban-decal-library", 1024, 1024, alpha=True)
    image.pixels.foreach_set(np.clip(atlas, 0, 1).ravel())
    image.filepath_raw = str(out_png)
    image.file_format = "PNG"
    image.save()
    bpy.data.images.remove(image)
    Path(out_json).write_text(json.dumps({"image": out_png.name, "cell_origin": "bottom-left", "entries": meta}, indent=2) + "\n")
    return atlas, meta


def encode(linear):
    return srgb_encode(linear)

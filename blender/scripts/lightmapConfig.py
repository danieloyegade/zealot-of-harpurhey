"""Pure-Python helpers for bakeLightmap.py (no bpy, so they can be unit tested).

Conversions between the game's world frame and a model's own Blender frame,
the game's sRGB hex colours to scene-linear, and the light-unit calibration.
"""

import json
from math import cos, pi, sin
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config" / "lightmap-bakes.json"

# Measured in Blender 5.2: a 1000 W Cycles point light lit a white diffuse
# plane 2 m below it to radiance L = 6.32 = I / (pi d^2), i.e. I = 79.6 in the
# game's candela terms, so I = P / (4 pi).
WATTS_PER_CANDELA = 4.0 * pi


def load_config(asset, path=CONFIG_PATH):
    config = json.loads(Path(path).read_text())
    if asset not in config["assets"]:
        raise SystemExit(f"No lightmap bake configured for '{asset}' in {path}")
    return config["assets"][asset]


def parse_hex(value):
    """'0xffa326' or 0xffa326 -> int."""
    return int(value, 16) if isinstance(value, str) else int(value)


def srgb_channel_to_linear(value):
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def hex_to_linear(value):
    """The linear-sRGB triple three.js's Color.set(0xRRGGBB) resolves to."""
    packed = parse_hex(value)
    return tuple(srgb_channel_to_linear(((packed >> shift) & 0xFF) / 255.0)
                 for shift in (16, 8, 0))


def candela_to_watts(candela):
    return candela * WATTS_PER_CANDELA


def emission_strength(candela, front_area):
    """Radiance of a Lambertian emitter of `front_area` m^2 seen head-on: I = Le * A."""
    return candela / front_area


def sky_strength(ambient_intensity):
    """Uniform-sky radiance factor matching a Three.js hemisphere light.

    Three applies albedo / pi to irradiance, so a white surface under an open
    hemisphere of colour c and intensity k shows k * c / pi.
    """
    return ambient_intensity / pi


def world_to_model(point, placement):
    """World (x, height, z) -> model Blender frame (x, y, z).

    The glTF importer maps Blender (x, y, z) to glTF (x, z, -y); three.js then
    rotates the model by `yaw` about Y and translates it to (x, 0, z).
    """
    wx, wy, wz = point
    dx = wx - placement["x"]
    dz = wz - placement["z"]
    yaw = placement["yaw"]
    gx = dx * cos(yaw) - dz * sin(yaw)
    gz = dx * sin(yaw) + dz * cos(yaw)
    return (gx, -gz, wy)


def model_to_world(point, placement):
    bx, by, bz = point
    gx, gz = bx, -by
    yaw = placement["yaw"]
    return (placement["x"] + gx * cos(yaw) + gz * sin(yaw),
            bz,
            placement["z"] - gx * sin(yaw) + gz * cos(yaw))


def world_rect_to_model_box(x_range, z_range, height, placement):
    """Axis-aligned world footprint -> (min, max) corners in the model frame."""
    corners = [world_to_model((x, 0.0, z), placement)
               for x in x_range for z in z_range]
    xs = [c[0] for c in corners]
    ys = [c[1] for c in corners]
    return (min(xs), min(ys), 0.0), (max(xs), max(ys), height)

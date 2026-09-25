"""Pure-Python checks for the lightmap bake's coordinate and colour helpers.

Run (no Blender needed):
    python3 tests/blender/test_lightmap_config.py
"""
import json
import sys
from math import pi
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / "blender" / "scripts"))

from lightmapConfig import (  # noqa: E402
    candela_to_watts, emission_strength, hex_to_linear, load_config, model_to_world,
    sky_strength, world_rect_to_model_box, world_to_model,
)

DREAMS = {"x": 1.5, "z": 39.0, "yaw": pi}


def close(a, b, tol=1e-6):
    assert all(abs(x - y) < tol for x, y in zip(a, b)), f"{a} != {b}"


def test_round_trip():
    for yaw in (0.0, pi / 2, pi, -pi / 2):
        placement = {"x": 3.0, "z": -7.0, "yaw": yaw}
        point = (4.2, 6.5, -1.1)
        close(model_to_world(world_to_model(point, placement), placement), point)


def test_dreams_faces_the_street():
    # Rotated by PI, the shopfront (model -Y) faces world -Z, toward the road.
    front = model_to_world((0.0, -4.25, 0.0), DREAMS)
    close(front, (1.5, 0.0, 34.75))
    close(world_to_model((1.5, 0.0, 34.75), DREAMS), (0.0, -4.25, 0.0))
    # World +X (east) is model -X for a building turned around.
    close(world_to_model((2.5, 0.0, 39.0), DREAMS), (-1.0, 0.0, 0.0))


def test_lamp_lands_in_front_of_the_shop():
    lamp = json.loads((ROOT / "config" / "lightmap-bakes.json").read_text())["assets"]["dreams"]["lights"]["lamps"][0]
    x, y, z = world_to_model(lamp["world"], DREAMS)
    assert y < -4.25, "the lamp must be on the street side of the shopfront"
    assert abs(z - 6.586) < 1e-9


def test_colours_match_three():
    close(hex_to_linear("0xffffff"), (1.0, 1.0, 1.0))
    close(hex_to_linear(0x000000), (0.0, 0.0, 0.0))
    r, g, b = hex_to_linear("0xffa326")
    assert r == 1.0 and 0.36 < g < 0.38 and b < 0.03  # sodium: nearly no blue


def test_units():
    assert abs(candela_to_watts(95) - 95 * 4 * pi) < 1e-9
    assert abs(emission_strength(9, 0.125) - 72.0) < 1e-9
    assert abs(sky_strength(0.72) - 0.72 / pi) < 1e-12


def test_stand_in_boxes():
    low, high = world_rect_to_model_box((-25.7, -7.5), (33.035, 44.965), 6.19, DREAMS)
    # Cass Art abuts Dreams' -X-world face, which is model +X: starts at x = 9.
    assert abs(low[0] - 9.0) < 1e-9 and high[0] > low[0] and high[2] == 6.19


def test_config_is_complete():
    cfg = load_config("dreams")
    assert cfg["contract"] == "dreams"
    assert cfg["building"]["size"] == 2048 and cfg["ground"]["size"] == [2048, 1024]
    assert len(cfg["lights"]["lamps"]) >= 1 and cfg["lights"]["tubes"]["candelaEach"] > 0


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for test in tests:
        test()
        print(f"ok  {test.__name__}")
    print(f"{len(tests)} passed")

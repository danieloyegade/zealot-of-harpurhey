#!/usr/bin/env python3
"""Build the Cass Art texture set from the approved photographic references.

The facade source is an ImageGen material study made from DSC06340.JPG,
DSC06343.JPG and CASS-Arts-623x438.jpg.  Everything else here is deterministic:
PBR companions, exact signage, and the photographed music-window composition.
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "blender" / "source" / "textures" / "cass-art"
SOURCE = OUT / "cass-facade-source.png"

ARIAL_BOLD = Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf")
ARIAL_BLACK = Path("/System/Library/Fonts/Supplemental/Arial Black.ttf")
DIN_BOLD = Path("/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf")
ORANGE = (240, 91, 35, 255)


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size=size)


def save_rgb(path: Path, array: np.ndarray) -> None:
    Image.fromarray(np.clip(array, 0, 255).astype(np.uint8), "RGB").save(
        path, optimize=True
    )


def fit_font(draw: ImageDraw.ImageDraw, text: str, path: Path, max_width: int,
             start: int) -> ImageFont.FreeTypeFont:
    size = start
    while size > 8:
        candidate = font(path, size)
        if draw.textbbox((0, 0), text, font=candidate)[2] <= max_width:
            return candidate
        size -= 2
    return font(path, 8)


def build_facade() -> None:
    source = Image.open(SOURCE).convert("RGB").resize((1024, 1024), Image.Resampling.LANCZOS)
    source = ImageEnhance.Color(source).enhance(0.48)
    source = ImageEnhance.Contrast(source).enhance(0.78)
    data = np.asarray(source, dtype=np.float32)
    # The photographs read darker and cooler than the neutral generated scan.
    data = data * np.array([0.72, 0.76, 0.79], dtype=np.float32)
    data = np.clip(data + np.array([1.0, 2.0, 3.0]), 0, 255)
    save_rgb(OUT / "cass-facade-albedo.png", data)

    grey = data.mean(axis=2) / 255.0
    blurred = np.asarray(
        Image.fromarray((grey * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2.2)),
        dtype=np.float32,
    ) / 255.0
    gx = np.roll(blurred, -1, axis=1) - np.roll(blurred, 1, axis=1)
    gy = np.roll(blurred, -1, axis=0) - np.roll(blurred, 1, axis=0)
    strength = 1.4
    normal = np.dstack((-gx * strength, -gy * strength, np.ones_like(grey)))
    normal /= np.linalg.norm(normal, axis=2, keepdims=True)
    save_rgb(OUT / "cass-facade-normal.png", (normal * 0.5 + 0.5) * 255)

    local = np.abs(grey - blurred)
    rough = 188 + local * 340 + (0.5 - grey) * 18
    save_rgb(OUT / "cass-facade-roughness.png", np.repeat(rough[:, :, None], 3, axis=2))


def build_floor() -> None:
    size = 1024
    rng = np.random.default_rng(1984)
    y, x = np.mgrid[0:size, 0:size]
    grain = (
        np.sin(x * 0.085 + np.sin(y * 0.017) * 1.7)
        + 0.45 * np.sin(x * 0.23 + y * 0.012)
        + rng.normal(0, 0.17, (size, size))
    )
    board = (x // 128) % 2
    seam = np.minimum(x % 128, 127 - (x % 128))
    base = np.empty((size, size, 3), dtype=np.float32)
    base[:] = (151, 133, 105)
    base += grain[:, :, None] * np.array([7.0, 5.0, 3.0])
    base += board[:, :, None] * np.array([5.0, 4.0, 2.0])
    base[seam < 2] *= 0.57
    save_rgb(OUT / "cass-floor-albedo.png", base)

    height = grain * 0.018 - (seam < 2) * 0.18
    gx = np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)
    gy = np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0)
    normal = np.dstack((-gx * 2.0, -gy * 2.0, np.ones_like(height)))
    normal /= np.linalg.norm(normal, axis=2, keepdims=True)
    save_rgb(OUT / "cass-floor-normal.png", (normal * 0.5 + 0.5) * 255)
    rough = 174 + rng.normal(0, 7, (size, size)) + (seam < 3) * 30
    save_rgb(OUT / "cass-floor-roughness.png", np.repeat(rough[:, :, None], 3, axis=2))


def build_slogan() -> None:
    image = Image.new("RGBA", (2048, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    # Legacy flat preview only: the runtime now uses traced raised geometry.
    text = "LETS FILL THIS TOWN WITH ARTISTS"
    face = fit_font(draw, text, Path("/System/Library/Fonts/Supplemental/Arial.ttf"), 1970, 150)
    box = draw.textbbox((0, 0), text, font=face)
    draw.text(((2048 - (box[2] - box[0])) / 2, 120), text, font=face,
              fill=ORANGE, anchor="lm", stroke_width=1, stroke_fill=(150, 45, 18, 255))
    image.save(OUT / "cass-slogan.png", optimize=True)


def logo_panel(width: int, height: int) -> Image.Image:
    image = Image.new("RGBA", (width, height), (242, 242, 236, 255))
    draw = ImageDraw.Draw(image)
    black = (24, 25, 23, 255)
    vertical = Image.new("RGBA", (height - 72, 180), (0, 0, 0, 0))
    vd = ImageDraw.Draw(vertical)
    vf = fit_font(vd, "CASS", ARIAL_BLACK, vertical.width - 12, 150)
    vd.text((vertical.width / 2, 84), "CASS", font=vf, fill=black, anchor="mm")
    vertical = vertical.rotate(90, expand=True, resample=Image.Resampling.BICUBIC)
    image.alpha_composite(vertical, (34, (height - vertical.height) // 2))

    left = int(width * 0.38)
    art_face = fit_font(draw, "ART", ARIAL_BLACK, width - left - 38, int(height * 0.36))
    draw.text((left, int(height * 0.12)), "ART", font=art_face, fill=black, anchor="la")
    draw.rectangle((left, int(height * 0.49), width - 42, int(height * 0.61)), fill=black)
    est_face = fit_font(draw, "EST.1984", ARIAL_BOLD, width - left - 38, int(height * 0.17))
    draw.text((left, int(height * 0.70)), "EST.1984", font=est_face, fill=black, anchor="la")
    return image


def build_signage() -> None:
    logo_panel(1024, 768).save(OUT / "cass-logo-sign.png", optimize=True)

    address = Image.new("RGBA", (512, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(address)
    face = fit_font(draw, "55–57", ARIAL_BOLD, 470, 170)
    draw.text((256, 128), "55–57", font=face, fill=ORANGE, anchor="mm")
    address.save(OUT / "cass-address.png", optimize=True)


def outlined(draw: ImageDraw.ImageDraw, xy, shape, fill, outline=(244, 239, 218, 255), width=10):
    if shape == "ellipse":
        draw.ellipse(xy, fill=fill, outline=outline, width=width)
    elif shape == "rectangle":
        draw.rounded_rectangle(xy, radius=20, fill=fill, outline=outline, width=width)


def build_window_display() -> None:
    image = Image.new("RGBA", (2048, 1024), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    cream = (245, 234, 207, 245)

    # Reference-specific music display: walkman, two tapes, looping cable,
    # record/8-ball and popcorn. Kept graphic so the shop interior remains seen.
    outlined(draw, (170, 300, 470, 790), "rectangle", (55, 174, 215, 238), width=14)
    draw.rectangle((245, 355, 405, 660), fill=(25, 87, 150, 245), outline=cream, width=10)
    draw.text((320, 710), "MUSIC", font=font(DIN_BOLD, 78), fill=cream, anchor="mm")

    def cassette(box, color, label):
        x0, y0, x1, y1 = box
        outlined(draw, box, "rectangle", color, width=13)
        draw.ellipse((x0 + 65, y0 + 65, x0 + 135, y0 + 135), outline=cream, width=10)
        draw.ellipse((x1 - 135, y0 + 65, x1 - 65, y0 + 135), outline=cream, width=10)
        draw.rectangle((x0 + 55, y1 - 115, x1 - 55, y1 - 55), outline=cream, width=9)
        draw.text(((x0 + x1) / 2, y0 + 35), label, font=font(DIN_BOLD, 42), fill=cream, anchor="mm")

    cassette((590, 220, 1020, 515), (224, 67, 43, 244), "SCHOOL’S OUT")
    cassette((810, 560, 1260, 855), (40, 181, 157, 244), "FOR SUMMER")
    draw.line((390, 330, 520, 175, 770, 170, 1130, 315, 1350, 250), fill=(210, 82, 198, 245), width=17)
    draw.line((445, 760, 570, 870, 790, 900, 1040, 850, 1370, 845), fill=(210, 82, 198, 245), width=17)
    draw.text((620, 710), "♪", font=font(ARIAL_BOLD, 135), fill=(218, 91, 201, 245), anchor="mm")
    draw.text((1345, 370), "♫", font=font(ARIAL_BOLD, 145), fill=(88, 175, 227, 245), anchor="mm")

    outlined(draw, (1320, 330, 1710, 720), "ellipse", (22, 23, 28, 246), width=15)
    outlined(draw, (1395, 400, 1635, 640), "ellipse", (242, 241, 231, 255), width=8)
    draw.text((1515, 520), "8", font=font(ARIAL_BLACK, 128), fill=(22, 23, 28, 255), anchor="mm")

    draw.polygon(((1720, 900), (1700, 525), (1960, 525), (1935, 900)),
                 fill=(224, 50, 45, 245), outline=cream)
    for x in range(1735, 1940, 58):
        draw.rectangle((x, 535, x + 28, 890), fill=(247, 239, 213, 245))
    draw.text((1830, 690), "POP!", font=font(ARIAL_BLACK, 70), fill=(224, 50, 45, 255),
              stroke_width=8, stroke_fill=cream, anchor="mm")
    for x, y, r in ((1740, 520, 55), (1810, 485, 68), (1880, 520, 58), (1940, 475, 48)):
        draw.ellipse((x - r, y - r, x + r, y + r), fill=cream, outline=(230, 136, 46, 255), width=8)

    label = Image.new("RGBA", (380, 285), (0, 0, 0, 0))
    label.alpha_composite(logo_panel(380, 285))
    image.alpha_composite(label, (34, 24))
    image.save(OUT / "cass-window-display.png", optimize=True)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    if not SOURCE.exists():
        raise FileNotFoundError(f"Missing approved facade source: {SOURCE}")
    build_facade()
    build_floor()
    build_signage()
    # Reference reconstructions are retained as authored PNG inputs; do not
    # overwrite them with the earlier schematic window/sign preview helpers.
    from traceCassArtLettering import main as trace_lettering
    trace_lettering()
    print(f"Built Cass Art texture set in {OUT}")


if __name__ == "__main__":
    main()

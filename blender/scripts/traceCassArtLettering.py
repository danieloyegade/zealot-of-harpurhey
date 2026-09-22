"""Measure the photographed orange letter outlines for Blender geometry.

This analyses the supplied photograph; it does not substitute a similar font.
Output is vector contours (including counters), in source-photo pixels.
Run with Python + Pillow + numpy before createCassArt.py.
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
PHOTO = ROOT / 'references/architecture/buildings/cass-art/DSC06343.JPG'
OUT = ROOT / 'blender/source/textures/cass-art/cass-lettering-contours.json'


def simplify(points, tolerance=0.9):
    points = np.asarray(points, dtype=float)
    if len(points) < 3:
        return points.tolist()
    delta = points[-1] - points[0]
    length = np.linalg.norm(delta)
    distances = (np.abs(delta[0] * (points[:, 1] - points[0, 1]) -
                        delta[1] * (points[:, 0] - points[0, 0])) / length
                 if length else np.linalg.norm(points - points[0], axis=1))
    split = int(np.argmax(distances))
    if distances[split] <= tolerance:
        return [points[0].tolist(), points[-1].tolist()]
    return simplify(points[:split + 1], tolerance)[:-1] + simplify(points[split:], tolerance)


def main():
    # The crop only selects the measured sign, not its cast shadow/backing rail.
    crop = (1270, 747, 4200, 905)
    rgb = np.asarray(Image.open(PHOTO).convert('RGB'))[crop[1]:crop[3], crop[0]:crop[2]].astype(float)
    r, g, b = rgb.transpose(2, 0, 1)
    mask = (r > 150) & (r > g * 1.25) & (g > b * 1.22) & (r - b > 65)
    # Trace oriented pixel boundaries. Opposite winding preserves letter holes.
    edges = {}
    for y, x in zip(*np.where(mask)):
        for a, z, exposed in (
            ((x,y),(x+1,y), y == 0 or not mask[y-1,x]),
            ((x+1,y),(x+1,y+1), x == mask.shape[1]-1 or not mask[y,x+1]),
            ((x+1,y+1),(x,y+1), y == mask.shape[0]-1 or not mask[y+1,x]),
            ((x,y+1),(x,y), x == 0 or not mask[y,x-1]),
        ):
            if exposed:
                edges.setdefault(a, []).append(z)
    contours = []
    while edges:
        start = next(iter(edges))
        point = start
        loop = [start]
        while True:
            targets = edges[point]
            nxt = targets.pop()
            if not targets:
                del edges[point]
            loop.append(nxt)
            point = nxt
            if point == start:
                break
        area = sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(loop,loop[1:])) / 2
        if abs(area) > 28:
            contours.append(simplify(loop))
    all_points = np.array([p for loop in contours for p in loop])
    data = {'source': str(PHOTO.relative_to(ROOT)), 'text': 'LETS FILL THIS TOWN WITH ARTISTS',
            'crop_px': crop, 'bounds_px': [*all_points.min(axis=0), *all_points.max(axis=0)],
            'contours': contours}
    OUT.write_text(json.dumps(data, indent=2) + '\n')
    print(f'Traced {len(contours)} contours, {len(all_points)} vertices to {OUT}')


if __name__ == '__main__':
    main()

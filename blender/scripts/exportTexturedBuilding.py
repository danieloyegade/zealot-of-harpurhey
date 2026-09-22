"""Texture every GLB of one building from config/building-textures.json.

Run after the building's texture pass (`<building>Textures.py`):

    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python-exit-code 1 --python blender/scripts/exportTexturedBuilding.py -- <building>
"""

import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

from texturedRuntimeExport import PROJECT_ROOT, texture_glb  # noqa: E402


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(argv) != 1:
        raise SystemExit("usage: exportTexturedBuilding.py -- <building>")
    contract = json.loads((PROJECT_ROOT / "config" / "building-textures.json").read_text())
    entries = [e for e in contract["buildings"] if e["building"] == argv[0]]
    if not entries:
        raise SystemExit(f"No building-textures.json entry for {argv[0]}")
    for entry in entries:
        if "legacyExporter" in entry:
            raise SystemExit(f"{entry['glb']} is exported by {entry['legacyExporter']}")
        counts = texture_glb(PROJECT_ROOT / "public" / entry["glb"],
                             prefix=entry["surfacePrefix"],
                             texture_dir=PROJECT_ROOT / entry["textureDir"],
                             placeholder_map=entry["placeholders"],
                             expected_surfaces=entry["expectedSurfaces"])
        print(f"{entry['glb']}: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())),
              flush=True)


main()

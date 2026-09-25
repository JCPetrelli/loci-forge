"""Download the image textures loci_start.blend uses from Poly Haven (CC0).

    python3 scripts/fetch_textures.py

The .blend expects textures/<asset>/diff.jpg, nor.jpg and rough.jpg:
Poly Haven's 2K JPGs of the Diffuse, OpenGL normal and Roughness maps. Each
file is checked against the MD5 that Poly Haven's API publishes; files that
are already there and match are skipped, so re-running is cheap.
"""
import hashlib
import json
import os
import sys
import urllib.request
from itertools import groupby

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(REPO, "textures")
API = "https://api.polyhaven.com/files/{}"
RESOLUTION = "2k"
MAPS = {"diff.jpg": "Diffuse", "nor.jpg": "nor_gl", "rough.jpg": "Rough"}  # file -> Poly Haven map
FULL = ("diff.jpg", "nor.jpg", "rough.jpg")
# Every textures/ path loci_start.blend references; keep in step with the .blend.
FILES = [f"{asset}/{name}" for asset in (
    "brown_leather", "chipped_concrete", "concrete_floor_damaged_01", "cracked_concrete_wall",
    "fabric_leather_01", "fabric_leather_02", "leather_white", "peeling_painted_wall",
    "rusty_metal_02", "wood_cabinet_worn_long",
) for name in FULL] + ["leather_red_02/nor.jpg", "leather_red_02/rough.jpg"]
HEADERS = {"User-Agent": "loci-forge texture fetcher"}  # Poly Haven asks for one


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=60) as res:
        return res.read()


def md5(data):
    return hashlib.md5(data).hexdigest()


def main():
    fetched = skipped = 0
    for asset, paths in groupby(sorted(FILES), key=lambda p: p.split("/")[0]):
        files = json.loads(get(API.format(asset)))  # one API call per asset
        os.makedirs(os.path.join(DEST, asset), exist_ok=True)
        for rel in paths:
            info = files[MAPS[os.path.basename(rel)]][RESOLUTION]["jpg"]
            path = os.path.join(DEST, rel)
            if os.path.exists(path):
                with open(path, "rb") as fh:
                    if md5(fh.read()) == info["md5"]:
                        skipped += 1
                        continue
            data = get(info["url"])
            if md5(data) != info["md5"]:
                sys.exit(f"checksum mismatch for {rel}; try again")
            with open(path, "wb") as fh:
                fh.write(data)
            fetched += 1
            print(f"  {rel}  {len(data) / 1e6:.1f} MB")
    print(f"done: {fetched} downloaded, {skipped} already up to date -> {DEST}")


if __name__ == "__main__":
    main()

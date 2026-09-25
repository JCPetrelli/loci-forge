"""Export the open palace for the web player. Never saves the .blend.

    blender -b loci_start.blend --python scripts/export_web.py -- --palace archive

Writes web/assets/<palace>/: palace.glb (baked atlases + glass),
mannequin.glb, palace.json (spawn point and walker settings) and, when
palaces/<palace>/loci.json exists, a copy of it (the player's loci hints).
A quick preview: --size 2048 --density 45 --samples 32 (about a minute).

Options (after --):
  --palace NAME     output folder name (default: the .blend's name)
  --size PX         atlas resolution (default 4096)
  --density PX_M    texels per metre; lower = fewer atlases (default 90)
  --samples N       Cycles samples per texel (default 96)
  --exposure EV     brightness added when saving atlases (default 0.7):
                    Cycles bakes come out darker than the EEVEE viewport
  --interior X0,Y0,Z0,X1,Y1,Z1
                    the room's inner box; faces outside it that face away
                    are dropped (never seen from inside, they waste atlas)
  --cpu             bake on the CPU

Per-palace values (interior, exposure) can instead live in the .blend as a
scene custom property `loci_export`, e.g. {"interior": [...], "exposure": 0.7};
the palace's build script sets it. Flags override it.
"""
import argparse
import json
import os
import shutil
import sys
import time

import bpy

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))

from loci_export import atlas, bake, collect, coords, gltf  # noqa: E402
from loci_walker.character import ROOT  # noqa: E402
from loci_walker.geometry import principled, socket  # noqa: E402
import loci_walker  # noqa: E402

# Walker settings the web player uses.
WEB_SETTINGS = ("walk_speed", "run_multiplier", "jump_speed", "gravity", "mouse_sensitivity",
                "eye_height", "third_person_distance", "third_person", "lens")
PALACE_DEFAULTS = {"interior": None, "exposure": 0.7}


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--palace", default=os.path.splitext(os.path.basename(bpy.data.filepath))[0])
    p.add_argument("--size", type=int, default=4096)
    p.add_argument("--density", type=float, default=90)
    p.add_argument("--samples", type=int, default=96)
    p.add_argument("--exposure", type=float)
    p.add_argument("--interior", type=lambda v: [float(x) for x in v.split(",")])
    p.add_argument("--cpu", action="store_true")
    return p.parse_args(argv)


def palace_settings(scene, args):
    """Flags override the scene's `loci_export` property, which overrides defaults."""
    stored = scene.get("loci_export") or {}
    settings = {}
    for key, default in PALACE_DEFAULTS.items():
        flag = getattr(args, key)
        settings[key] = flag if flag is not None else stored.get(key, default)
    if settings["interior"] is not None:
        settings["interior"] = [float(v) for v in settings["interior"]]
    return settings


def walker_settings(scene):
    """The scene's walker settings, as set in the Loci panel. Registering the
    add-on is the reliable way to read them: since Blender 5, bpy.props values
    are no longer reachable as plain custom properties (scene.get)."""
    if not hasattr(bpy.types.Scene, "loci_walker"):
        loci_walker.register()
    values = {key: getattr(scene.loci_walker, key) for key in WEB_SETTINGS}
    return {k: round(v, 5) if isinstance(v, float) else v for k, v in values.items()}  # drop float32 noise


def glass_look(mat):
    """Colour and opacity the web player draws this glass with."""
    bsdf = principled(mat)
    alpha = socket(bsdf, "Alpha").default_value if bsdf else 1.0
    return {"color": list(mat.diffuse_color[:3]), "opacity": alpha if alpha < 0.99 else 0.35}


def export_mannequin(out_dir):
    root = bpy.data.objects.get(ROOT)
    if root is None:
        return None
    parts = [root, *root.children_recursive]
    for obj in parts:
        obj.hide_render = False
        obj.hide_set(False)
        if obj is not root:
            obj.rotation_euler = (0, 0, 0)
    saved = root.matrix_world.copy()
    root.matrix_world.identity()
    gltf.export(parts, os.path.join(out_dir, "mannequin.glb"), export_materials='PLACEHOLDER')
    root.matrix_world = saved
    return {"location": list(saved.translation), "yaw": saved.to_euler().z}


def main():
    args = parse_args()
    scene = bpy.context.scene
    palace = palace_settings(scene, args)
    out_dir = os.path.join(REPO, "web", "assets", args.palace)
    work_dir = os.path.join(out_dir, "_atlases")  # the .glb embeds them; removed at the end
    os.makedirs(work_dir, exist_ok=True)
    t0 = time.time()

    keep, hide = collect.collect(scene)
    for obj in hide:
        obj.hide_render = True
    meshes = collect.realize(keep)
    if palace["interior"]:
        meshes = [o for o in meshes if collect.cull_exterior(o, palace["interior"])]
    solids, glasses = [], []
    for obj in meshes:
        solid, glass = collect.split_glass(obj)
        if solid:
            solids.append(solid)
        if glass:
            glasses.append(glass)
    areas = {o: collect.world_area(o) for o in solids}
    atlases = atlas.group(areas, args.size, args.density)
    print(f"[export] {len(solids)} objects, {sum(areas.values()):.0f} m², {len(glasses)} glass, "
          f"{len(atlases)} atlases of {args.size}px at {args.density:g} px/m")

    for obj in solids + glasses:
        coords.store(obj)
    coords.rewire(collect.materials_of(solids))
    for objs in atlases:
        atlas.unwrap(objs)
    print(f"[export] unwrapped in {time.time() - t0:.0f}s")

    # One object per atlas and collision flag: Cycles bakes object by object,
    # re-syncing the scene each time, so fewer objects bake far faster.
    joined = []
    for i, objs in enumerate(atlases):
        split = {label: [o for o in objs if bool(o.get("loci_nocollide")) == flag]
                 for flag, label in ((False, "solid"), (True, "decor"))}
        groups = [gltf.join(members, f"atlas{i}_{label}") for label, members in split.items() if members]
        joined.append(groups)

    bake.setup_cycles(scene, args.samples, use_gpu=not args.cpu)
    scene.view_settings.exposure += palace["exposure"]
    # Bake every atlas before swapping any material: an object already wearing
    # its baked image would light the later bakes a second time.
    baked = []
    for i, objs in enumerate(joined):
        t = time.time()
        image = bpy.data.images.new(f"atlas_{i}", args.size, args.size, float_buffer=True)
        bake.bake_atlas(objs, image)
        path = os.path.join(work_dir, f"atlas_{i}.jpg")
        bake.save_display(image, path, scene)
        bpy.data.images.remove(image)  # a 4096 px float image is ~270 MB
        baked.append(path)
        print(f"[export] atlas {i + 1}/{len(joined)} baked in {time.time() - t:.0f}s")
    exported = []
    for i, (objs, path) in enumerate(zip(joined, baked)):
        mat = gltf.baked_material(f"atlas_{i}", bpy.data.images.load(path))
        for obj in objs:
            gltf.assign_baked(obj, mat)
            exported.append(obj)

    by_material = {}
    for obj in glasses:
        name = next(s.material.name for s in obj.material_slots if collect.is_glass(s.material))
        by_material.setdefault(name, []).append(obj)
    for name, objs in by_material.items():
        glass = gltf.join(objs, f"glass_{name}")
        glass["loci_glass"] = glass_look(bpy.data.materials[name])
        exported.append(glass)

    gltf.export(exported, os.path.join(out_dir, "palace.glb"))
    spawn = export_mannequin(out_dir)

    info = {
        "palace": args.palace,
        "source": os.path.basename(bpy.data.filepath),
        "up": "z",
        "spawn": spawn,
        "walker": walker_settings(scene),
        "atlases": len(atlases),
        "exported": time.strftime("%Y-%m-%d %H:%M"),
    }
    with open(os.path.join(out_dir, "palace.json"), "w") as fh:
        json.dump(info, fh, indent=2)
    loci = os.path.join(REPO, "palaces", args.palace, "loci.json")
    if os.path.exists(loci):
        shutil.copy(loci, out_dir)
    shutil.rmtree(work_dir, ignore_errors=True)
    size_mb = sum(os.path.getsize(os.path.join(out_dir, f)) for f in os.listdir(out_dir)) / 1e6
    print(f"[export] done in {(time.time() - t0) / 60:.1f} min -> {out_dir} ({size_mb:.1f} MB)")


main()

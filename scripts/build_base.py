"""Builds loci_base.blend: a small sandbox to walk around in, the player, and
the embedded loader for the Loci Walker add-on.

    blender -b --factory-startup --python scripts/build_base.py

The sandbox has what a walker needs to be tested: open ground, a room with a
doorway, stairs up to a terrace, a ramp, and five numbered pedestals as sample
loci along a route.
"""
import math
import os
import sys

import bpy
from mathutils import Euler

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))

from loci_build import Batch  # noqa: E402
from loci_walker import character, geometry  # noqa: E402

OUTPUT = os.path.join(REPO, "loci_base.blend")
SANDBOX = "Loci_Sandbox"
SPAWN = (0.0, -9.0, 0.0)


def clear_scene():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj)
    for coll in list(bpy.data.collections):
        bpy.data.collections.remove(coll)


def build_sandbox(scene):
    coll = geometry.ensure_collection(scene, SANDBOX)
    ground = geometry.material("Loci_Ground", (0.32, 0.34, 0.33), 0.9)
    wall = geometry.material("Loci_Wall", (0.78, 0.76, 0.72), 0.8)
    stone = geometry.material("Loci_Stone", (0.55, 0.53, 0.5), 0.7)
    accent = geometry.material("Loci_Accent", (0.85, 0.35, 0.2), 0.4)

    b = Batch("Ground")
    b.box((0, 0, -0.1), (40, 40, 0.2), ground)
    b.build(coll)

    # Room, 8 x 8 x 3 m, doorway in the south wall
    cx, cy, w, h, t = 0.0, 6.0, 8.0, 3.0, 0.2
    door = 1.6
    side = (w - door) / 2
    b = Batch("Room")
    b.box((cx, cy + w / 2, h / 2), (w + t, t, h), wall)
    b.box((cx - w / 2, cy, h / 2), (t, w, h), wall)
    b.box((cx + w / 2, cy, h / 2), (t, w, h), wall)
    b.box((cx - door / 2 - side / 2, cy - w / 2, h / 2), (side, t, h), wall)
    b.box((cx + door / 2 + side / 2, cy - w / 2, h / 2), (side, t, h), wall)
    b.box((cx, cy - w / 2, 2.6), (door, t, 0.8), wall)
    b.box((cx, cy, h + t / 2), (w + t, w + t, t), wall)
    b.build(coll)

    # Stairs up to a terrace, and a ramp back down on the other side
    rise, run, n = 0.18, 0.32, 9
    sx, sy = 9.0, -4.0
    terrace_h = rise * n
    length, angle = 6.0, math.atan2(terrace_h, 6.0)
    b = Batch("Stairs_Terrace_Ramp")
    for i in range(n):
        top = rise * (i + 1)
        b.box((sx, sy + run * i + run / 2, top / 2), (2.4, run, top), stone)
    b.box((sx, sy + run * n + 2.5, terrace_h / 2), (5.0, 5.0, terrace_h), stone)
    b.box((sx, sy + run * n + 5.0 + length / 2 * math.cos(angle), terrace_h / 2 - 0.1),
          (2.4, length / math.cos(angle) + 0.1, 0.2), stone, rot=(-angle, 0, 0))
    b.build(coll)

    # Sample loci: five numbered pedestals along a route, one object each
    route = [(-6, -4), (-3, -1), (-2, 4), (2, 7), (9, 1.5)]
    for i, (x, y) in enumerate(route, start=1):
        z = terrace_h if i == 5 else 0.0
        b = Batch(f"Locus_{i}")
        b.box((x, y, z + 0.5), (0.6, 0.6, 1.0), stone)
        b.box((x, y, z + 1.2), (0.35, 0.35, 0.35), accent, rot=(0.6, 0.6, 0))
        b.build(coll)
        curve = bpy.data.curves.new(f"Locus_{i}_Label", 'FONT')
        curve.body = str(i)
        curve.align_x = 'CENTER'
        curve.size = 0.5
        label = bpy.data.objects.new(f"Locus_{i}_Label", curve)
        label.location = (x, y, z + 1.6)
        label.rotation_euler = (math.pi / 2, 0, 0)
        coll.objects.link(label)

    b = Batch("Pillars")
    for x, y in [(-8, 8), (-8, -8), (6, -8)]:
        b.cyl((x, y, 2.0), 0.35, 0.35, 4.0, stone, smooth=False)
    b.build(coll)


def build_lighting(scene):
    coll = geometry.ensure_collection(scene, "Loci_Lighting")
    sun = bpy.data.lights.new("Loci_Sun", 'SUN')
    sun.energy = 3.5
    sun.angle = math.radians(3)
    sun_obj = bpy.data.objects.new("Loci_Sun", sun)
    sun_obj.rotation_euler = (math.radians(50), 0, math.radians(35))
    coll.objects.link(sun_obj)

    world = scene.world or bpy.data.worlds.new("Loci_World")
    scene.world = world
    world.color = (0.55, 0.62, 0.72)
    if bpy.app.version < (5, 0, 0) and not world.use_nodes:
        world.use_nodes = True
    bg = next((n for n in world.node_tree.nodes if n.type == 'BACKGROUND'), None)
    if bg:
        bg.inputs[0].default_value = (0.55, 0.62, 0.72, 1.0)
        bg.inputs[1].default_value = 0.8


def embed_loader():
    path = os.path.join(REPO, "scripts", "loci_boot.py")
    text = bpy.data.texts.get("loci_boot.py") or bpy.data.texts.new("loci_boot.py")
    with open(path) as fh:
        text.from_string(fh.read())
    text.use_module = True


def frame_views():
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type != 'VIEW_3D':
                continue
            space = area.spaces.active
            space.shading.type = 'SOLID'
            space.shading.color_type = 'MATERIAL'
            space.shading.light = 'STUDIO'
            space.clip_end = 500
            rv3d = space.region_3d
            rv3d.view_perspective = 'PERSP'
            rv3d.view_location = (1.0, 0.0, 0.5)
            rv3d.view_distance = 30.0
            rv3d.view_rotation = Euler((math.radians(60), 0, math.radians(-30))).to_quaternion()


def main():
    clear_scene()
    scene = bpy.context.scene
    scene.name = "Loci"
    build_sandbox(scene)
    build_lighting(scene)
    root = character.ensure_player(bpy.context, location=SPAWN)
    scene.cursor.location = SPAWN
    for obj in scene.objects:
        obj.select_set(False)
    bpy.context.view_layer.objects.active = root
    embed_loader()
    frame_views()
    bpy.ops.wm.save_as_mainfile(filepath=OUTPUT, compress=True)
    print(f"Saved {OUTPUT}")


main()

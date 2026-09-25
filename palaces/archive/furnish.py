"""Furnishes the Archive palace in loci_start.blend.

The room is 18 x 15 m and 9 m high: x -9..9, y -9..6, entrance on the front
wall (y = -9), windows on the left wall, the tall bookcase on the back wall
under a hole in the roof. This script adds everything else, in stations
meant to be walked in order:

  1 entrance door and stopped clock    6 display cases in the hall
  2 armillary sphere on a round rug    7 staircase and gallery bookshelves
  3 reading table by the windows       8 telescope, globe and armchair on the gallery
  4 card catalogue                     9 upright piano
  5 paintings between the windows     10 arched door onward, end of the gallery

It is idempotent: everything lives in the Archive_Furnishing collection,
which is emptied and rebuilt on every run. Run it inside Blender, e.g.:

    exec(open(bpy.path.abspath("//palaces/archive/furnish.py")).read())
"""
import math
import random
import sys

import bpy
from mathutils import Euler, Vector

sys.path.insert(0, bpy.path.abspath("//scripts"))
from loci_build import Batch, emissive, fabric, plain, point_light, reset_collection  # noqa: E402
from loci_build.batch import frame  # noqa: E402
from loci_walker.geometry import principled, ramp_material, socket  # noqa: E402

COLLECTION = "Archive_Furnishing"
INTERIOR = (-9.0, -9.0, 0.0, 9.0, 6.0, 9.0)  # inner box of the room, for the web export
PI = math.pi
rng = random.Random(7)


def mat(name):
    return bpy.data.materials[name]


def ring(n, radius, phase=0.0):
    """(dx, dy) offsets of n points evenly spaced on a circle."""
    return [(math.cos(phase + i * 2 * PI / n) * radius, math.sin(phase + i * 2 * PI / n) * radius)
            for i in range(n)]


def without_dust(source, name):
    """Copy of a material with its flat-colour overlays switched off.

    The archive's wood mixes a dust colour onto upward faces and a damp
    colour below 1.8 m. Both suit the old bookcase but wash out furniture
    built at floor level, so every mix whose overlay (B) is a flat colour
    gets its factor unplugged and zeroed. The grain mixes, whose B is
    textured, are left alone.
    """
    copy = bpy.data.materials.get(name) or bpy.data.materials[source].copy()
    copy.name = name
    nt = copy.node_tree
    for node in nt.nodes:
        if node.type != 'MIX':
            continue
        factor = next(i for i in node.inputs if i.enabled and i.identifier.startswith("Factor"))
        overlay = next(i for i in node.inputs if i.enabled and i.identifier.startswith("B"))
        if factor.is_linked and not overlay.is_linked:
            for link in list(factor.links):
                nt.links.remove(link)
            factor.default_value = 0.0
    return copy


def clear_glass(name):
    glass = plain(name, (0.85, 0.92, 0.95), 0.04)
    socket(principled(glass), "Alpha").default_value = 0.1
    if hasattr(glass, "surface_render_method"):
        glass.surface_render_method = 'BLENDED'
    else:
        glass.blend_method = 'BLEND'
    return glass


# -- materials ---------------------------------------------------------------

# New furniture uses the archive's worn wood without its dust layer, which
# reads as white on the tops of everything built at floor level.
WOOD = without_dust("Archive_Ebony", "Furn_Wood")
WALL = mat("Archive_Wall")
STONE = mat("Archive_Column")
BRASS = mat("Archive_Gilt")
STEEL = mat("Archive_Steel")
PAPER = mat("Archive_Paper")
GLASS = clear_glass("Furn_CaseGlass")
LEATHER = mat("Archive_Oxblood")
RUBBLE = mat("Archive_Rubble")
BOOKS = [mat(f"BC_Book_{i}") for i in range(8)]
BLACK = plain("Furn_Black", (0.02, 0.02, 0.02), 0.45)
LACQUER = plain("Furn_PianoBlack", (0.012, 0.01, 0.009), 0.12)
KEY_WHITE = plain("Furn_KeyIvory", (0.9, 0.87, 0.78), 0.3)
MARBLE = plain("Furn_Marble", (0.88, 0.86, 0.82), 0.3)
GLOBE = plain("Furn_Globe", (0.09, 0.2, 0.26), 0.5)
BANKER_GREEN = emissive("Furn_BankerGreen", (0.1, 0.55, 0.22), 1.2, base=(0.04, 0.3, 0.1))
FLAME = emissive("Furn_Flame", (1.0, 0.55, 0.2), 25.0)
BULB = emissive("Furn_Bulb", (1.0, 0.8, 0.5), 12.0)
CRYSTAL = emissive("Furn_Crystal", (0.35, 0.8, 1.0), 2.5, base=(0.6, 0.9, 1.0))
RUG = fabric("Furn_RugRed", (0.03, 0.005, 0.007), (0.1, 0.018, 0.02), scale=25.0)
RUG_BORDER = fabric("Furn_RugBorder", (0.07, 0.05, 0.025), (0.2, 0.15, 0.07), scale=25.0)
LANTERN = emissive("Furn_Lantern", (1.0, 0.62, 0.3), 1.8, base=(0.9, 0.7, 0.45), roughness=0.3)
LAMP_SHADE = emissive("Furn_LampShade", (1.0, 0.7, 0.4), 1.5, base=(0.75, 0.62, 0.45), roughness=0.8)
GLOBE_MAP = ramp_material("Furn_GlobeMap", "ShaderNodeTexNoise", (0.04, 0.09, 0.09), (0.36, 0.25, 0.1),
                          roughness=0.55, Scale=4.0, Detail=4.0)
for element, position in zip(socket(principled(GLOBE_MAP), "Base Color").links[0].from_node.color_ramp.elements,
                             (0.5, 0.54)):
    element.position = position  # a hard edge: sea and land, not a blur
DOOR_GREEN = plain("Furn_DoorGreen", (0.03, 0.09, 0.06), 0.45)
DOOR_GLOW = emissive("Furn_DoorGlow", (1.0, 0.8, 0.5), 8.0)
IVY = plain("Furn_Ivy", (0.04, 0.14, 0.035), 0.55)
IVY_DARK = plain("Furn_IvyDark", (0.02, 0.08, 0.02), 0.5)
CANVAS = fabric("Furn_Canvas", (0.05, 0.04, 0.03), (0.32, 0.24, 0.13), scale=4.0, roughness=0.7)

WARM = (1.0, 0.72, 0.42)


# -- 0 structure ---------------------------------------------------------------

def structure(coll):
    b = Batch("Furn_FrontWall")
    b.box((-5.4, -9.25, 4.5), (8.2, 0.5, 9.0), WALL)
    b.box((5.4, -9.25, 4.5), (8.2, 0.5, 9.0), WALL)
    b.box((0, -9.25, 6.3), (2.6, 0.5, 5.4), WALL)
    b.build(coll)


# -- 1 entrance ----------------------------------------------------------------

def entrance(coll):
    b = Batch("Furn_Entrance")
    for sx in (-1, 1):
        b.box((sx * 1.43, -8.9, 1.9), (0.26, 0.24, 3.8), STONE)
        cx = sx * 0.65
        b.box((cx, -9.08, 1.8), (1.28, 0.08, 3.6), WOOD)
        b.box((cx, -9.02, 0.9), (0.95, 0.04, 1.2), WOOD)
        b.box((cx, -9.02, 2.55), (0.95, 0.04, 1.5), WOOD)
        b.torus((sx * 0.18, -8.98, 1.45), 0.07, 0.012, BRASS, rot=(PI / 2, 0, 0))
    b.box((0, -8.9, 3.95), (3.2, 0.28, 0.3), STONE)
    b.box((0, -8.86, 4.2), (0.35, 0.3, 0.3), STONE)  # keystone
    b.build(coll, bevel=0.01)

    # A stopped clock: 3:47
    c = Vector((0, -8.95, 5.9))
    b = Batch("Furn_Clock")
    b.cyl(c, 0.8, 0.8, 0.06, PAPER, rot=(PI / 2, 0, 0), segments=48)
    b.torus(c + Vector((0, 0.02, 0)), 0.82, 0.05, BRASS, rot=(PI / 2, 0, 0), segments=64)
    # The clock is read from inside the room, facing -Y, where +X is on the
    # viewer's left: clockwise from 12 therefore runs towards -X.
    def dial(angle):
        return Vector((-math.sin(angle), 0, math.cos(angle))), (0, -angle, 0)

    for h in range(12):
        long = h % 3 == 0
        d, rot = dial(h * PI / 6)
        b.box(c + d * 0.66 + Vector((0, 0.035, 0)), (0.05 if long else 0.025, 0.01, 0.13 if long else 0.07),
              BLACK, rot=rot)
    for angle, length, width, dy in (((3 + 47 / 60) * PI / 6, 0.4, 0.045, 0.045),
                                     (47 * PI / 30, 0.62, 0.025, 0.055)):
        d, rot = dial(angle)
        b.box(c + d * (length / 2 - 0.06) + Vector((0, dy, 0)), (width, 0.01, length), BLACK, rot=rot)
    b.cyl(c + Vector((0, 0.065, 0)), 0.04, 0.04, 0.02, BRASS, rot=(PI / 2, 0, 0))
    b.build(coll)

    b = Batch("Furn_Runner")
    b.box((0, -7.45, 0.003), (1.5, 3.0, 0.006), RUG_BORDER)
    b.box((0, -7.45, 0.006), (1.26, 2.76, 0.006), RUG)
    b.build(coll)


# -- 2 armillary sphere ------------------------------------------------------

def armillary(coll):
    cx, cy = 0.0, -3.9
    b = Batch("Furn_RoundRug")
    b.cyl((cx, cy, 0.004), 2.3, 2.3, 0.008, RUG_BORDER, segments=64, smooth=False)
    b.cyl((cx, cy, 0.008), 2.05, 2.05, 0.008, RUG, segments=64, smooth=False)
    b.cyl((cx, cy, 0.012), 0.9, 0.9, 0.008, RUG_BORDER, segments=48, smooth=False)
    b.build(coll)

    b = Batch("Furn_Armillary")
    b.cyl((cx, cy, 0.1), 0.6, 0.6, 0.2, STONE, segments=32)
    b.cyl((cx, cy, 0.6), 0.3, 0.2, 0.8, STONE, segments=32)
    b.cyl((cx, cy, 1.05), 0.25, 0.42, 0.1, STONE, segments=32)
    center = Vector((cx, cy, 1.95))
    b.torus(center, 0.92, 0.03, BRASS, segments=64)  # horizon ring
    for i in range(4):
        a = PI / 4 + i * PI / 2
        b.rod((cx + math.cos(a) * 0.3, cy + math.sin(a) * 0.3, 1.1),
              (cx + math.cos(a) * 0.92, cy + math.sin(a) * 0.92, 1.95), 0.018, BRASS)
    tilt = Euler((0.45, 0, 0.3)).to_matrix()
    rings = [((0, 0, 0), 0.8), ((PI / 2, 0, 0), 0.84), ((PI / 2, 0, PI / 2), 0.84),
             ((math.radians(23.4), 0, 0), 0.8)]
    for rot, radius in rings:
        b.torus(center, radius, 0.02, BRASS, rot=tilt @ Euler(rot).to_matrix(), segments=64, ring=8)
    for z in (-1, 1):  # tropics
        off = tilt @ Vector((0, 0, z * 0.8 * math.sin(math.radians(23.4))))
        b.torus(center + off, 0.8 * math.cos(math.radians(23.4)), 0.012, BRASS, rot=tilt, segments=48, ring=6)
    axis = tilt @ Vector((0, 0, 1))
    b.rod(center - axis * 1.0, center + axis * 1.0, 0.012, STEEL)
    b.sphere(center, (0.2, 0.2, 0.2), GLOBE, segments=24)
    b.build(coll)

    b = Batch("Furn_Benches")
    for sx in (-1, 1):
        f = frame((cx + sx * 3.0, cy, 0))
        b.box((0, 0, 0.44), (0.5, 1.7, 0.07), WOOD, frame=f)
        b.box((0, 0, 0.5), (0.44, 1.6, 0.06), LEATHER, frame=f)
        for lx in (-0.18, 0.18):
            for ly in (-0.7, 0.7):
                b.box((lx, ly, 0.2), (0.06, 0.06, 0.4), WOOD, frame=f)
        b.box((0, 0, 0.12), (0.04, 1.4, 0.05), WOOD, frame=f)
    b.build(coll, bevel=0.008)


# -- 3 reading table -----------------------------------------------------------

def chair(b, location, yaw):
    f = frame(location, yaw)
    b.box((0, 0, 0.46), (0.46, 0.46, 0.05), WOOD, frame=f)
    b.box((0, 0.01, 0.495), (0.4, 0.4, 0.03), LEATHER, frame=f)
    for lx in (-0.19, 0.19):
        for ly in (-0.19, 0.19):
            b.box((lx, ly, 0.22), (0.045, 0.045, 0.44), WOOD, frame=f)
        b.box((lx, -0.2, 0.75), (0.045, 0.045, 0.55), WOOD, frame=f)
    b.box((0, -0.2, 1.0), (0.44, 0.05, 0.07), WOOD, frame=f)
    b.box((0, -0.2, 0.78), (0.12, 0.03, 0.36), WOOD, frame=f)


def closed_book(b, center, size, yaw, cover, tilt=0.0):
    f = frame(center, yaw)
    w, d, t = size
    rot = (0, tilt, 0)
    b.box((0, 0, 0), (w, d, t), cover, rot=rot, frame=f)
    b.box((w * 0.03, 0, 0), (w * 0.96, d * 0.97, t * 0.8), PAPER, rot=rot, frame=f)


def open_book(b, center, yaw, cover):
    f = frame(center, yaw)
    for side in (-1, 1):
        b.box((side * 0.085, 0, 0.004), (0.17, 0.25, 0.006), cover, rot=(0, -side * 0.08, 0), frame=f)
        b.box((side * 0.08, 0, 0.016), (0.155, 0.235, 0.018), PAPER, rot=(0, -side * 0.1, 0), frame=f)


def banker_lamp(b, x, y, z, coll, name):
    b.cyl((x, y, z + 0.015), 0.085, 0.07, 0.03, BRASS)
    b.rod((x, y, z + 0.03), (x, y, z + 0.3), 0.01, BRASS)
    b.cyl((x, y, z + 0.33), 0.075, 0.075, 0.34, BANKER_GREEN, rot=(PI / 2, 0, 0), segments=24)
    b.rod((x + 0.05, y, z + 0.3), (x + 0.05, y, z + 0.18), 0.003, BRASS)
    point_light(coll, name, (x, y, z + 0.24), 60, WARM, radius=0.04)


def reading_area(coll):
    x0 = -7.3
    b = Batch("Furn_ReadingTable")
    b.box((x0, -2.5, 0.74), (1.2, 6.4, 0.06), WOOD)
    b.box((x0, -2.5, 0.66), (1.0, 6.2, 0.1), WOOD)
    for lx in (-0.5, 0.5):
        for ly in (-5.55, -2.5, 0.55):
            b.cyl((x0 + lx, ly, 0.355), 0.035, 0.05, 0.71, WOOD, segments=16)
    b.build(coll, bevel=0.01)

    b = Batch("Furn_Chairs")
    for i, y in enumerate((-4.8, -2.6, -0.4)):
        chair(b, (x0 - 1.0, y + rng.uniform(-0.1, 0.1), 0), -PI / 2 + rng.uniform(-0.1, 0.1))
        if i == 1:  # one chair pushed back and turned, as if someone just stood up
            chair(b, (x0 + 1.25, y + 0.3, 0), PI / 2 + 0.6)
        else:
            chair(b, (x0 + 1.0, y + rng.uniform(-0.1, 0.1), 0), PI / 2 + rng.uniform(-0.1, 0.1))
    b.build(coll, bevel=0.006)

    b = Batch("Furn_TableLamps")
    for i, y in enumerate((-4.6, -1.5, 0.2)):
        banker_lamp(b, x0, y, 0.77, coll, f"Furn_TableLamp_{i}")
    b.build(coll, nocollide=True)

    b = Batch("Furn_TableBooks")
    open_book(b, (x0 - 0.3, -3.5, 0.772), 0.2 - PI / 2, BOOKS[2])
    open_book(b, (x0 + 0.3, -0.9, 0.772), PI / 2 - 0.3, BOOKS[5])
    z = 0.77
    for i in range(5):
        t = rng.uniform(0.03, 0.06)
        closed_book(b, (x0 + 0.25, -5.1, z + t / 2), (0.19, 0.27, t), rng.uniform(-0.3, 0.3), BOOKS[i])
        z += t
    closed_book(b, (x0 - 0.25, -2.2, 0.79), (0.2, 0.28, 0.04), 1.2, BOOKS[6])
    for i in range(3):
        b.box((x0 + 0.1 + i * 0.05, -2.9 + i * 0.07, 0.772), (0.21, 0.29, 0.002), PAPER, rot=(0, 0, rng.uniform(-0.6, 0.6)))
    b.build(coll)


# -- 4 card catalogue -------------------------------------------------------

def card_catalogue(coll):
    back, depth = -9.0, 0.55
    front = back + depth
    y0, width, cols, rows = -8.85, 2.3, 6, 6
    cx = back + depth / 2
    b = Batch("Furn_CardCatalogue")
    b.box((cx, y0 + width / 2, 0.06), (depth - 0.04, width - 0.06, 0.12), WOOD)
    b.box((cx, y0 + width / 2, 0.81), (depth, width, 1.38), WOOD)
    b.box((cx + 0.02, y0 + width / 2, 1.52), (depth + 0.06, width + 0.06, 0.04), WOOD)
    cell_w, cell_h = (width - 0.1) / cols, 1.2 / rows
    pulled = {(1, 3), (4, 1), (2, 5), (5, 4)}
    for c in range(cols):
        for r in range(rows):
            y = y0 + 0.05 + cell_w * (c + 0.5)
            z = 0.2 + cell_h * (r + 0.5)
            out = 0.32 if (c, r) in pulled else 0.0
            fx = front + 0.02 + out
            b.box((fx, y, z), (0.04, cell_w - 0.02, cell_h - 0.02), WOOD)
            b.box((fx + 0.03, y, z - 0.03), (0.02, 0.08, 0.02), BRASS)
            b.box((fx + 0.022, y, z + 0.04), (0.005, 0.07, 0.035), PAPER)
            if out:
                b.box((fx - out / 2 - 0.01, y, z - 0.02), (out, cell_w - 0.04, cell_h - 0.06), WOOD)
                for k in range(8):
                    b.box((fx - 0.05 - k * 0.035, y, z + 0.02), (0.003, cell_w - 0.07, cell_h - 0.05), PAPER,
                          rot=(0, rng.uniform(-0.15, 0.15), 0))
    for k in range(12):  # index cards spilled on the floor
        b.box((front + rng.uniform(0.3, 1.4), -7.6 + rng.uniform(-0.9, 0.9), 0.002 + k * 0.0005),
              (0.13, 0.08, 0.001), PAPER, rot=(0, 0, rng.uniform(0, PI)))
    b.build(coll, bevel=0.004)

    # standing lamp beside the cabinet
    b = Batch("Furn_FloorLamp")
    x, y = -8.35, -6.1
    b.cyl((x, y, 0.02), 0.18, 0.16, 0.04, BRASS, segments=32)
    b.rod((x, y, 0.04), (x, y, 1.55), 0.014, BRASS)
    b.cyl((x, y, 1.6), 0.24, 0.15, 0.28, LAMP_SHADE, segments=32)
    b.build(coll)
    point_light(coll, "Furn_FloorLamp", (x, y, 1.4), 160, WARM, radius=0.1)


# -- 5 paintings -------------------------------------------------------------

def paintings(coll):
    b = Batch("Furn_Paintings")
    for y, w, h in ((-2.75, 1.2, 1.55), (1.75, 1.3, 1.1)):
        b.box((-8.97, y, 3.0), (0.06, w + 0.18, h + 0.18), BRASS)
        b.box((-8.93, y, 3.0), (0.03, w, h), CANVAS)
    b.build(coll, bevel=0.01)


# -- 6-8 gallery -------------------------------------------------------------

GALLERY_Z = 3.6
GALLERY_Y = (-2.3, 6.0)


def gallery(coll):
    y0, y1 = GALLERY_Y
    ym, length = (y0 + y1) / 2, y1 - y0
    b = Batch("Furn_Gallery")
    b.box((7.65, ym, GALLERY_Z - 0.125), (2.7, length, 0.25), WOOD)
    b.box((6.45, ym, GALLERY_Z - 0.35), (0.22, length, 0.2), WOOD)
    for y in (-2.15, 4.3):
        b.box((6.45, y, (GALLERY_Z - 0.25) / 2), (0.22, 0.22, GALLERY_Z - 0.25), WOOD)
    y = y0 + 0.5
    while y < y1:
        b.box((7.7, y, GALLERY_Z - 0.35), (2.5, 0.1, 0.18), WOOD)
        y += 1.2

    # railing along the open edge and the front edge beside the stairs
    top = GALLERY_Z + 1.0
    b.box((6.36, ym, top), (0.08, length, 0.06), WOOD)
    b.box((6.36, ym, GALLERY_Z + 0.12), (0.06, length, 0.05), WOOD)
    y = y0 + 0.05
    while y < y1:
        b.box((6.36, y, GALLERY_Z + 0.5), (0.035, 0.035, 0.9), WOOD)
        y += 0.2
    b.box((6.75, y0 + 0.04, top), (0.85, 0.08, 0.06), WOOD)
    for i in range(5):
        b.box((6.4 + i * 0.19, y0 + 0.04, GALLERY_Z + 0.5), (0.035, 0.035, 0.9), WOOD)

    # stairs up from the front, along the right wall
    steps, rise, run = 20, GALLERY_Z / 20, 0.28
    s0 = y0 - steps * run
    for i in range(steps):
        h = rise * (i + 1)
        b.box((8.05, s0 + run * (i + 0.5), h / 2), (1.7, run, h), WOOD)
    rail_start = 2
    for i in range(rail_start, steps, 2):
        yc = s0 + run * (i + 0.5)
        h = rise * (i + 1)
        b.box((7.23, yc, h + 0.47), (0.035, 0.035, 0.94), WOOD)
    b.rod((7.23, s0 + run * (rail_start + 0.5), rise * (rail_start + 1) + 0.95),
          (7.23, y0, GALLERY_Z + 1.0), 0.03, WOOD)
    b.build(coll, bevel=0.006)


def gallery_shelves(coll):
    z0 = GALLERY_Z
    b = Batch("Furn_GalleryShelves")
    books = Batch("Furn_GalleryBooks")
    for ya, yb in ((-1.6, 0.7), (0.9, 3.2)):  # the third bay is the onward door
        ym, w = (ya + yb) / 2, yb - ya
        b.box((8.99, ym, z0 + 1.35), (0.04, w, 2.7), WOOD)
        for side in (ya, yb):
            b.box((8.77, side, z0 + 1.35), (0.46, 0.05, 2.7), WOOD)
        for k in range(6):
            b.box((8.77, ym, z0 + 0.05 + k * 0.52), (0.46, w, 0.04), WOOD)
        for k in range(5):
            shelf_z = z0 + 0.07 + k * 0.52
            y = ya + 0.04
            while y < yb - 0.1:
                if rng.random() < 0.06:
                    y += rng.uniform(0.08, 0.2)  # gap
                    continue
                t = rng.uniform(0.03, 0.07)
                h = rng.uniform(0.24, 0.4)
                d = rng.uniform(0.2, 0.3)
                lean = rng.uniform(0.1, 0.25) if rng.random() < 0.05 else 0.0
                books.box((8.97 - d / 2, y + t / 2 + lean * h / 2, shelf_z + h / 2 * math.cos(lean)),
                          (d, t, h), rng.choice(BOOKS), rot=(-lean, 0, 0))
                y += t + lean * h + 0.002
    b.build(coll, bevel=0.005)
    books.build(coll)


def gallery_nook(coll):
    z = GALLERY_Z
    b = Batch("Furn_Armchair")
    f = frame((7.5, 5.2, z), PI + 0.35)
    b.box((0, 0, 0.3), (0.8, 0.75, 0.3), LEATHER, frame=f)
    b.box((0, 0.05, 0.5), (0.62, 0.62, 0.12), LEATHER, frame=f)
    b.box((0, -0.33, 0.75), (0.8, 0.18, 0.75), LEATHER, frame=f)
    for sx in (-1, 1):
        b.box((sx * 0.36, 0.02, 0.6), (0.14, 0.72, 0.28), LEATHER, frame=f)
        for sy in (-1, 1):
            b.box((sx * 0.33, sy * 0.3, 0.07), (0.06, 0.06, 0.14), WOOD, frame=f)
    b.build(coll, bevel=0.03)

    b = Batch("Furn_SideTable")
    b.cyl((6.8, 5.4, z + 0.6), 0.28, 0.28, 0.04, WOOD, segments=32)
    b.cyl((6.8, 5.4, z + 0.3), 0.04, 0.06, 0.58, WOOD, segments=16)
    b.cyl((6.8, 5.4, z + 0.02), 0.22, 0.22, 0.04, WOOD, segments=32)
    b.cyl((6.72, 5.33, z + 0.64), 0.06, 0.04, 0.04, BRASS)
    b.cyl((6.72, 5.33, z + 0.72), 0.018, 0.018, 0.14, KEY_WHITE, segments=12)
    b.sphere((6.72, 5.33, z + 0.81), (0.01, 0.01, 0.025), FLAME)
    closed_book(b, (6.88, 5.48, z + 0.645), (0.17, 0.24, 0.05), 0.4, BOOKS[3])
    b.build(coll)
    point_light(coll, "Furn_Candle", (6.72, 5.33, z + 0.86), 8, (1.0, 0.6, 0.3), radius=0.02)

    # a brass telescope on the railing, aimed at the hole in the roof
    b = Batch("Furn_Telescope")
    base = Vector((7.0, 0.3, z))
    head = base + Vector((0, 0, 1.2))
    for dx, dy in ring(3, 0.4, phase=0.3):
        b.rod(head, base + Vector((dx, dy, 0)), 0.015, WOOD)
    aim = (Vector((0.2, 2.35, 9.2)) - head).normalized()
    b.rod(head - aim * 0.45, head + aim * 0.75, 0.055, BRASS, segments=24)
    b.rod(head + aim * 0.75, head + aim * 0.85, 0.07, BRASS, segments=24)
    b.rod(head - aim * 0.6, head - aim * 0.45, 0.025, BLACK)
    b.build(coll)


def display_cases(coll):
    # A row in the open hall, north of the round rug. Not under the gallery:
    # a locus directly beneath another one (the telescope) gets confused with it.
    y = -1.1
    stands = (2.3, 3.4, 4.5)
    b = Batch("Furn_DisplayCases")
    for x in stands:
        b.box((x, y, 0.45), (0.72, 0.72, 0.9), WOOD)
        b.box((x, y, 0.93), (0.78, 0.78, 0.06), WOOD)
        b.box((x, y, 1.31), (0.66, 0.66, 0.7), GLASS)
        b.box((x, y, 1.68), (0.72, 0.72, 0.05), WOOD)
    b.build(coll, bevel=0.008)

    # hourglass
    x, z = stands[0], 0.96
    b = Batch("Furn_Hourglass")
    b.cyl((x, y, z + 0.015), 0.1, 0.1, 0.03, WOOD, segments=6, smooth=False)
    b.cyl((x, y, z + 0.44), 0.1, 0.1, 0.03, WOOD, segments=6, smooth=False)
    b.cyl((x, y, z + 0.13), 0.075, 0.01, 0.2, GLASS)
    b.cyl((x, y, z + 0.32), 0.01, 0.075, 0.2, GLASS)
    b.cyl((x, y, z + 0.06), 0.065, 0.005, 0.06, BRASS)
    for dx, dy in ring(3, 0.085):
        b.rod((x + dx, y + dy, z + 0.03), (x + dx, y + dy, z + 0.43), 0.008, WOOD)
    b.build(coll)

    # marble bust, looking towards the entrance
    x = stands[1]
    b = Batch("Furn_Bust")
    b.box((x, y, 1.0), (0.2, 0.2, 0.08), MARBLE)
    b.sphere((x, y, 1.13), (0.17, 0.1, 0.1), MARBLE)
    b.cyl((x, y, 1.24), 0.05, 0.045, 0.1, MARBLE)
    b.sphere((x, y, 1.36), (0.075, 0.09, 0.1), MARBLE)
    b.sphere((x, y - 0.085, 1.35), (0.015, 0.02, 0.03), MARBLE)
    b.build(coll)

    # glowing crystals on a rock
    x = stands[2]
    b = Batch("Furn_Crystals")
    b.sphere((x, y, 0.99), (0.12, 0.15, 0.06), RUBBLE)
    for i in range(6):
        a = rng.uniform(0, 2 * PI)
        tilt = rng.uniform(0.1, 0.5)
        length = rng.uniform(0.12, 0.3)
        root = Vector((x + math.cos(a) * 0.05, y + math.sin(a) * 0.05, 1.0))
        tip = root + Vector((math.cos(a) * math.sin(tilt), math.sin(a) * math.sin(tilt), math.cos(tilt))) * length
        rot = (tip - root).to_track_quat('Z', 'Y').to_matrix()
        b.cyl((root + tip) / 2, 0.03, 0.0, length, CRYSTAL, rot=rot, segments=6, smooth=False)
    b.build(coll)

    for i, x in enumerate(stands):
        point_light(coll, f"Furn_CaseLight_{i}", (x, y, 1.6), 6, (0.9, 0.95, 1.0), radius=0.03)
    point_light(coll, "Furn_CrystalGlow", (stands[2], y, 1.15), 4, (0.4, 0.8, 1.0), radius=0.05)


def gallery_globe(coll):
    """A large terrestrial globe on a floor stand, between the telescope and
    the armchair. No rings: it must not read as a second armillary sphere."""
    x, y, z = 7.9, 2.8, GALLERY_Z
    center = Vector((x, y, z + 1.0))
    b = Batch("Furn_Globe")
    b.cyl((x, y, z + 0.03), 0.34, 0.36, 0.06, WOOD, segments=32)
    for dx, dy in ring(3, 0.3, phase=0.4):
        b.rod((x + dx, y + dy, z + 0.05), (x + dx * 0.25, y + dy * 0.25, z + 0.5), 0.03, WOOD)
    b.cyl((x, y, z + 0.52), 0.07, 0.1, 0.08, WOOD, segments=16)
    b.rod((x, y, z + 0.55), center - Vector((0, 0, 0.42)), 0.035, WOOD)
    axis = Euler((0, math.radians(23.4), 0.6)).to_matrix() @ Vector((0, 0, 1))
    b.rod(center - axis * 0.5, center + axis * 0.5, 0.012, BRASS)
    b.sphere(center, (0.42, 0.42, 0.42), GLOBE_MAP, segments=40)
    b.build(coll, bevel=0.005)


ONWARD_DOOR_Y = 4.3


def onward_door(coll):
    """The way on to the next environment: an arched door in the right wall at
    the end of the gallery. Painted, narrow and round-topped, with light
    leaking under it, so it never reads as a second entrance door."""
    x, y, z = 9.0, ONWARD_DOOR_Y, GALLERY_Z
    half, spring = 0.55, 2.0  # half width; height where the arch starts
    b = Batch("Furn_OnwardDoor")
    # leaf: a box plus a disc on top makes the round head
    b.box((x - 0.05, y, z + spring / 2), (0.06, half * 2, spring), DOOR_GREEN)
    b.cyl((x - 0.05, y, z + spring), half, half, 0.06, DOOR_GREEN, rot=(0, PI / 2, 0), segments=32)
    for dz in (0.35, 1.0, 1.65):  # iron bands
        b.box((x - 0.085, y, z + dz), (0.012, half * 2 - 0.04, 0.05), BLACK)
    b.sphere((x - 0.1, y - 0.36, z + 1.0), (0.035, 0.035, 0.035), BRASS)
    b.box((x - 0.09, y - 0.36, z + 0.9), (0.01, 0.05, 0.08), BRASS)  # keyhole plate
    # stone jambs and a voussoir arch
    for side in (-1, 1):
        b.box((x - 0.08, y + side * (half + 0.1), z + spring / 2), (0.14, 0.2, spring), STONE)
    n = 9
    for i in range(n):
        a = PI * (i + 0.5) / n
        r = half + 0.1
        # local y runs along the arch, local z points out from its centre
        b.box((x - 0.08, y + math.cos(a) * r, z + spring + math.sin(a) * r), (0.14, PI * r / n * 1.02, 0.2),
              STONE, rot=(a - PI / 2, 0, 0))
    b.box((x - 0.08, y, z + 0.01), (0.2, half * 2 + 0.4, 0.02), STONE)  # threshold
    b.build(coll, bevel=0.006)

    b = Batch("Furn_DoorGlow")
    b.box((x - 0.08, y, z + 0.03), (0.02, half * 2 - 0.06, 0.012), DOOR_GLOW)
    b.build(coll, nocollide=True)
    point_light(coll, "Furn_DoorGlow", (x - 0.25, y, z + 0.08), 25, (1.0, 0.78, 0.5), radius=0.3)


def column_ivy(coll):
    """Ivy climbing the front-left column, so that one column of six is a locus
    that cannot be mistaken for the others."""
    x0, x1, y0, y1 = -5.8, -5.2, -6.3, -5.7
    b = Batch("Furn_Ivy")
    leaves = (IVY, IVY_DARK)
    # (face normal, fixed coordinate, range along the face)
    faces = (((1, 0), x1, (y0 + 0.05, y1 - 0.05)), ((0, -1), y0, (x0 + 0.05, x1 - 0.05)))
    for (nx, ny), fixed, (a0, a1) in faces:
        for _ in range(3):
            u, z = rng.uniform(a0, a1), 0.0
            top = rng.uniform(2.2, 3.6)
            prev = None
            while z < top:
                u = min(a1, max(a0, u + rng.uniform(-0.04, 0.04)))
                z += 0.06
                if nx:
                    p = Vector((fixed + 0.012, u, z))
                else:
                    p = Vector((u, fixed - 0.012, z))
                if prev is not None:
                    b.rod(prev, p, 0.006, WOOD, segments=5)
                prev = p
                for _ in range(2):
                    du, dz = rng.uniform(-0.07, 0.07), rng.uniform(-0.03, 0.03)
                    size = rng.uniform(0.035, 0.06)
                    lp = p + Vector((0, du, dz)) if nx else p + Vector((du, 0, dz))
                    lp += Vector((nx * 0.01, ny * 0.01, 0))
                    radii = (0.01, size, size * 0.85) if nx else (size, 0.01, size * 0.85)
                    spin = rng.uniform(-0.6, 0.6)
                    rot = (spin, 0, 0) if nx else (0, spin, 0)
                    b.sphere(lp, radii, rng.choice(leaves), rot=rot, segments=8)
    b.build(coll, nocollide=True)


# -- 9 piano -----------------------------------------------------------------

def piano(coll):
    cx, back = 4.4, -9.0
    w = 1.5
    b = Batch("Furn_Piano")
    b.box((cx, back + 0.22, 0.31), (w, 0.44, 0.62), LACQUER)
    b.box((cx, back + 0.28, 1.01), (w, 0.56, 0.58), LACQUER)
    b.box((cx, back + 0.29, 1.31), (w + 0.04, 0.6, 0.03), LACQUER)
    b.box((cx, back + 0.68, 0.66), (w, 0.24, 0.08), LACQUER)
    for sx in (-1, 1):
        b.box((cx + sx * (w / 2 - 0.035), back + 0.68, 0.76), (0.07, 0.26, 0.14), LACQUER)
        b.cyl((cx + sx * (w / 2 - 0.05), back + 0.75, 0.31), 0.03, 0.04, 0.62, LACQUER, segments=12)
        b.box((cx + sx * (w / 2 - 0.05), back + 0.72, 0.03), (0.08, 0.28, 0.06), LACQUER)
    keys_w = w - 0.16
    whites = 36
    kw = keys_w / whites
    x0 = cx - keys_w / 2
    for k in range(whites):
        b.box((x0 + kw * (k + 0.5), back + 0.72, 0.71), (kw - 0.002, 0.15, 0.02), KEY_WHITE)
        if k % 7 in (0, 1, 3, 4, 5) and k < whites - 1:
            b.box((x0 + kw * (k + 1), back + 0.69, 0.73), (kw * 0.55, 0.09, 0.03), LACQUER)
    b.box((cx, back + 0.6, 0.86), (keys_w, 0.02, 0.18), LACQUER, rot=(-0.25, 0, 0))
    b.box((cx, back + 0.6, 1.12), (0.62, 0.02, 0.24), LACQUER, rot=(-0.2, 0, 0))
    for sx in (-0.13, 0.13):
        b.box((cx + sx, back + 0.62, 1.13), (0.24, 0.004, 0.3), PAPER, rot=(-0.2, 0, sx * 0.4))
    for px in (-0.08, 0.08):
        b.box((cx + px, back + 0.5, 0.06), (0.04, 0.12, 0.015), BRASS)
    for sx in (-1, 1):
        base = Vector((cx + sx * 0.62, back + 0.58, 1.02))
        b.rod(base, base + Vector((sx * 0.05, 0.12, 0)), 0.008, BRASS)
        b.cyl(base + Vector((sx * 0.05, 0.12, 0.01)), 0.03, 0.02, 0.02, BRASS)
        b.cyl(base + Vector((sx * 0.05, 0.12, 0.08)), 0.012, 0.012, 0.12, KEY_WHITE, segments=12)
        tip = base + Vector((sx * 0.05, 0.12, 0.165))
        b.sphere(tip, (0.009, 0.009, 0.022), FLAME)
        point_light(coll, f"Furn_PianoCandle_{'LR'[sx > 0]}", tip + Vector((0, 0, 0.03)), 10,
                    (1.0, 0.58, 0.28), radius=0.02)
    b.build(coll, bevel=0.005)

    b = Batch("Furn_PianoStool")
    s = Vector((cx, back + 1.35, 0))
    b.cyl(s + Vector((0, 0, 0.5)), 0.2, 0.2, 0.06, LEATHER, segments=32)
    b.cyl(s + Vector((0, 0, 0.45)), 0.19, 0.19, 0.05, LACQUER, segments=32)
    for (tx, ty), (bx, by) in zip(ring(3, 0.12), ring(3, 0.2)):
        b.rod(s + Vector((tx, ty, 0.43)), s + Vector((bx, by, 0)), 0.02, LACQUER)
    b.build(coll)


# -- lighting ------------------------------------------------------------------

def pendant_lamps(coll):
    bottom = 4.6
    b = Batch("Furn_Pendants")
    for i, (x, y) in enumerate(((-2.6, -6.0), (2.6, -6.0), (-2.6, -1.5), (2.6, -1.5))):
        b.rod((x, y, 8.4), (x, y, bottom + 0.3), 0.008, BLACK)
        b.cyl((x, y, bottom + 0.15), 0.34, 0.07, 0.3, STEEL, segments=32)
        b.sphere((x, y, bottom - 0.02), (0.05, 0.05, 0.06), BULB)
        point_light(coll, f"Furn_Pendant_{i}", (x, y, bottom - 0.12), 140, WARM, radius=0.06)
    b.build(coll, nocollide=True)


def gallery_lights(coll):
    """Soft warm light for the stairs and the gallery: two sconces on the wall
    above the stairs and three lanterns standing on the gallery railing."""
    b = Batch("Furn_Sconces")
    for i, (y, z) in enumerate(((-6.6, 2.6), (-3.9, 4.1))):
        b.box((8.98, y, z), (0.04, 0.14, 0.26), BRASS)
        b.rod((8.97, y, z - 0.05), (8.72, y, z + 0.06), 0.012, BRASS)
        b.cyl((8.72, y, z + 0.14), 0.07, 0.11, 0.16, LAMP_SHADE, segments=24)
        point_light(coll, f"Furn_Sconce_{i}", (8.72, y, z + 0.08), 220, WARM, radius=0.12)
    b.build(coll, nocollide=True)

    b = Batch("Furn_Lanterns")
    top = GALLERY_Z + 1.03
    for i, y in enumerate((-1.2, 1.9, 4.9)):
        b.cyl((6.36, y, top + 0.015), 0.07, 0.07, 0.03, BRASS, segments=6, smooth=False)
        b.cyl((6.36, y, top + 0.13), 0.055, 0.055, 0.2, LANTERN, segments=6, smooth=False)
        b.cyl((6.36, y, top + 0.26), 0.075, 0.02, 0.07, BRASS, segments=6, smooth=False)
        b.torus((6.36, y, top + 0.31), 0.025, 0.006, BRASS, rot=(PI / 2, 0, 0), segments=16, ring=6)
        point_light(coll, f"Furn_Lantern_{i}", (6.36, y, top + 0.14), 120, (1.0, 0.64, 0.34), radius=0.08)
    b.build(coll, nocollide=True)

    # Broad, soft fills with no fixture: they lift the steps and the gallery
    # floor out of the dark without adding hard shadows.
    point_light(coll, "Furn_StairFill", (7.6, -5.0, 5.2), 420, WARM, radius=1.2)
    point_light(coll, "Furn_GalleryFill", (7.2, 1.0, 7.0), 520, WARM, radius=1.5)


def place_player():
    player = bpy.data.objects.get("Loci_Player")
    if player:
        player.location = (0, -6.3, 0)
        player.rotation_euler.z = 0.0


def main():
    scene = bpy.data.scenes["Archive"]
    scene["loci_export"] = {"interior": INTERIOR}
    coll = reset_collection(scene, COLLECTION)
    structure(coll)
    entrance(coll)
    armillary(coll)
    reading_area(coll)
    card_catalogue(coll)
    paintings(coll)
    gallery(coll)
    gallery_shelves(coll)
    gallery_nook(coll)
    gallery_globe(coll)
    onward_door(coll)
    column_ivy(coll)
    display_cases(coll)
    piano(coll)
    pendant_lamps(coll)
    gallery_lights(coll)
    place_player()
    return coll


main()

"""The player: a wooden artist's mannequin under a root empty at the feet.

The root faces +Y at zero rotation. Each body part is an object whose origin
is its joint, parented down the chain (pelvis > thigh > shin > foot, and so
on), so posing is just rotating parts around X. Every part carries
`loci_part` (its role) and `loci_nocollide` so the collision world ignores it.
"""
import math

import bpy

from . import geometry

COLLECTION = "Loci_Player"
ROOT = "Loci_Player"
VERSION = 3  # bump when the mannequin changes; older players are rebuilt

WOOD_LIGHT = (0.80, 0.60, 0.40)
WOOD_DARK = (0.55, 0.36, 0.20)
JOINT = (0.36, 0.22, 0.12)

HIP_HEIGHT = 0.93
PELVIS_TOP = 0.13
CHEST = 0.42
NECK = 0.08
THIGH, SHIN = 0.43, 0.43
UPPER_ARM, FOREARM = 0.28, 0.25


def _spec():
    """role: (parent role, joint location in the parent's space, mesh adders, material key)."""
    E, T = geometry.add_ellipsoid, geometry.add_taper
    spec = {
        "pelvis": (None, (0, 0, HIP_HEIGHT),
                   [E((0.15, 0.1, 0.1), (0, 0, 0.04))], "wood"),
        "chest": ("pelvis", (0, 0, PELVIS_TOP),
                  [E((0.07, 0.06, 0.06)), E((0.1, 0.075, 0.1), (0, 0, 0.1)),
                   E((0.165, 0.1, 0.16), (0, 0, CHEST - 0.16))], "wood"),
        "neck": ("chest", (0, 0, CHEST),
                 [E((0.045, 0.045, 0.045)), T(NECK, 0.04, 0.045, (0, 0, NECK))], "joint"),
        "head": ("neck", (0, 0, NECK),
                 [E((0.095, 0.11, 0.13), (0, 0.01, 0.11))], "wood"),
    }
    for side, x in (("l", -1), ("r", 1)):
        spec[f"thigh_{side}"] = ("pelvis", (0.09 * x, 0, -0.02),
                                 [E((0.07, 0.07, 0.07)), T(THIGH - 0.04, 0.075, 0.05, (0, 0, -0.03))], "wood")
        spec[f"shin_{side}"] = ("thigh_" + side, (0, 0, -THIGH),
                                [E((0.05, 0.05, 0.05)), T(SHIN - 0.04, 0.05, 0.035, (0, 0, -0.03))], "wood")
        spec[f"foot_{side}"] = ("shin_" + side, (0, 0, -SHIN),
                                [E((0.035, 0.035, 0.035)), E((0.045, 0.11, 0.035), (0, 0.06, -0.035))], "wood")
        spec[f"upper_arm_{side}"] = ("chest", (0.2 * x, 0, CHEST - 0.12),
                                     [E((0.05, 0.05, 0.05)), T(UPPER_ARM - 0.03, 0.045, 0.035, (0, 0, -0.02))], "wood")
        spec[f"forearm_{side}"] = ("upper_arm_" + side, (0, 0, -UPPER_ARM),
                                   [E((0.035, 0.035, 0.035)), T(FOREARM - 0.03, 0.035, 0.028, (0, 0, -0.02))], "wood")
        spec[f"hand_{side}"] = ("forearm_" + side, (0, 0, -FOREARM),
                                [E((0.028, 0.028, 0.028)), E((0.025, 0.045, 0.07), (0, 0.005, -0.07))], "wood")
    return spec


def ensure_player(context, location=None):
    """Return the player root, building (or upgrading) the mannequin as needed."""
    scene = context.scene
    coll = geometry.ensure_collection(scene, COLLECTION)
    root = bpy.data.objects.get(ROOT)
    if root is not None and root.get("loci_player_version") == VERSION:
        return root

    if root is None:
        root = bpy.data.objects.new(ROOT, None)
        root.empty_display_type = 'SINGLE_ARROW'
        root.empty_display_size = 0.5
        root.rotation_mode = 'XYZ'
        root.location = location if location is not None else scene.cursor.location
        coll.objects.link(root)
    else:
        geometry.remove_objects(root.children_recursive)
    root["loci_player_version"] = VERSION

    mats = {
        "wood": geometry.wood_material("Loci_Mannequin_Wood", WOOD_LIGHT, WOOD_DARK),
        "joint": geometry.wood_material("Loci_Mannequin_Joint", JOINT, WOOD_DARK, scale=12.0),
    }
    objects = {}
    for role, (parent, joint, adders, mat_key) in _spec().items():
        name = f"Loci_{role}"
        mesh = geometry.smooth_mesh(name, mats[mat_key], *adders)
        obj = geometry.add_object(name, mesh, coll, joint, parent=objects.get(parent, root))
        obj["loci_part"] = role
        obj["loci_nocollide"] = True
        objects[role] = obj
    animate(objects, 0.0, 0.0)
    return root


def parts(root):
    return {c["loci_part"]: c for c in root.children_recursive if "loci_part" in c}


def set_visible(parts_by_role, visible):
    for obj in parts_by_role.values():
        try:
            obj.hide_set(not visible)
        except RuntimeError:  # not in the active view layer
            pass


def pose(phase, amount, air=0.0, rise=0.0, land=0.0):
    """Joint rotations (role -> (x, y, z)) and pelvis height for one frame.

    Three layers, blended:
      walk   `phase` in radians, `amount` 0 = standing .. 1 = full stride
      air    0 on the ground .. 1 airborne; `rise` 1 going up .. 0 coming down
             (tucked knees and arms thrown up on the way up, legs reaching
             for the ground on the way down)
      land   0..1, a knee-bending crouch right after touching down

    Positive X rotation swings a hanging limb forward (+Y) but tips an upright
    part (chest, head) backward, so forward leans are negative. The web player's
    web/src/mannequin.js mirrors this function; keep the two in step.
    """
    s, c = math.sin(phase), math.cos(phase)
    a = amount * (1.0 - air)
    tuck = air * rise
    reach = air * (1.0 - rise)
    rot = {}
    for side, sign, offset in (("l", 1, 0.0), ("r", -1, math.pi)):
        sw = math.sin(phase + offset)
        lift = max(0.0, math.cos(phase + offset))  # swing phase: leg travelling forward
        stagger = 0.12 * sign * air                  # legs never quite symmetrical in the air
        rot[f"thigh_{side}"] = (0.5 * sw * a + 0.75 * tuck + 0.3 * reach + stagger + 0.55 * land, 0, 0)
        rot[f"shin_{side}"] = (-(0.1 + 0.9 * lift) * a - 1.25 * tuck - 0.35 * reach - 1.1 * land, 0, 0)
        rot[f"foot_{side}"] = ((0.25 * lift - 0.1 * sw) * a + 0.35 * tuck + 0.15 * reach + 0.5 * land, 0, 0)
        rot[f"upper_arm_{side}"] = (-0.45 * sw * a + 1.3 * tuck + 0.5 * reach + 0.25 * land,
                                    (0.1 + 0.3 * air + 0.15 * land) * sign, 0)
        rot[f"forearm_{side}"] = (0.15 + 0.35 * a * max(0.0, -sw) + 0.45 * tuck + 0.2 * reach, 0, 0)
        rot[f"hand_{side}"] = (0.0, 0.0, 0.0)
    rot["pelvis"] = (0.0, 0.04 * c * a, 0.12 * s * a)
    rot["chest"] = (-(0.06 * a + 0.2 * tuck - 0.08 * reach + 0.3 * land), 0, -0.2 * s * a)
    rot["neck"] = (0, 0, 0.08 * s * a)
    rot["head"] = (0.04 * a + 0.12 * tuck + 0.15 * land, 0, 0)  # keeps the gaze up as the chest leans
    pelvis_z = HIP_HEIGHT - 0.035 * a * abs(s) - 0.12 * land
    return rot, pelvis_z


def animate(parts_by_role, phase, amount, air=0.0, rise=0.0, land=0.0):
    """Apply `pose` to the mannequin (see `pose` for the arguments)."""
    rot, pelvis_z = pose(phase, amount, air, rise, land)
    for role, euler in rot.items():
        obj = parts_by_role.get(role)
        if obj:
            obj.rotation_euler = euler
    pelvis = parts_by_role.get("pelvis")
    if pelvis:
        pelvis.location.z = pelvis_z

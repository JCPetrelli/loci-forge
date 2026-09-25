"""Decide what goes into the export, and turn it into plain, single-user meshes."""
import bmesh
import bpy
import numpy as np

from loci_walker.character import COLLECTION as PLAYER_COLLECTION
from loci_walker.geometry import is_volume_only, principled

GEOMETRY_TYPES = {'MESH', 'CURVE', 'SURFACE', 'FONT', 'META'}


def select_only(objects):
    """Select exactly `objects`, the first one active (what most operators expect)."""
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]


def materials_of(objects):
    return {s.material for o in objects for s in o.material_slots
            if s.material and s.material.node_tree}


def is_glass(mat):
    """Transparent materials are exported unbaked and drawn see-through."""
    if mat is None or not mat.node_tree:
        return False
    if getattr(mat, "surface_render_method", "") == 'BLENDED' or getattr(mat, "blend_method", "") == 'BLEND':
        return True
    bsdf = principled(mat)
    if bsdf is None:
        return False
    transmission = next((s for s in bsdf.inputs if s.identifier == "Transmission Weight"), None)
    return transmission is not None and not transmission.is_linked and transmission.default_value > 0.5


def _in_player(obj):
    return any(c.name == PLAYER_COLLECTION for c in obj.users_collection)


def collect(scene):
    """Renderable, visible geometry; plus the objects to hide while baking."""
    keep, hide = [], []
    for obj in scene.objects:
        if obj.type not in GEOMETRY_TYPES:
            continue
        if _in_player(obj) or obj.particle_systems or is_volume_only(obj):
            hide.append(obj)
            continue
        if obj.hide_render or not obj.visible_get():
            continue
        keep.append(obj)
    return keep, hide


def realize(objects):
    """Replace every object's data with a single-user mesh, modifiers applied."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    result = []
    for obj in objects:
        mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph),
                                               preserve_all_data_layers=True, depsgraph=depsgraph)
        if not mesh.polygons:
            continue
        if obj.type == 'MESH':
            obj.modifiers.clear()
            obj.data = mesh
            target = obj
        else:  # curves, text: swap in a mesh object at the same place
            target = bpy.data.objects.new(obj.name + "_mesh", mesh)
            for coll in obj.users_collection:
                coll.objects.link(target)
            target.matrix_world = obj.matrix_world
            for key in obj.keys():
                target[key] = obj[key]
            obj.hide_render = True
        result.append(target)
    return result


def split_glass(obj):
    """Move glass faces into their own object. Returns (solid or None, glass or None)."""
    glass_slots = {i for i, s in enumerate(obj.material_slots) if is_glass(s.material)}
    if not glass_slots:
        return obj, None
    faces_glass = [p.material_index in glass_slots for p in obj.data.polygons]
    if all(faces_glass):
        return None, obj
    glass = obj.copy()
    glass.data = obj.data.copy()
    glass.name = obj.name + "_glass"
    for coll in obj.users_collection:
        coll.objects.link(glass)
    for target, drop_glass in ((obj, True), (glass, False)):
        bm = bmesh.new()
        bm.from_mesh(target.data)
        doomed = [f for f in bm.faces if (f.material_index in glass_slots) == drop_glass]
        bmesh.ops.delete(bm, geom=doomed, context='FACES')
        bm.to_mesh(target.data)
        bm.free()
    return obj, glass


def world_area(obj):
    s = obj.matrix_world.to_scale()
    factor = (abs(s.x * s.y * s.z)) ** (2 / 3)
    areas = np.empty(len(obj.data.polygons), dtype=np.float32)
    obj.data.polygons.foreach_get("area", areas)
    return float(areas.sum()) * factor


def cull_exterior(obj, bounds, margin=0.02):
    """Delete faces nobody inside the room can see: outside the interior box,
    and facing away from every corner of it (the outside of walls, the roof's
    top, the floor's underside). A face that any part of the room can see, such
    as the rim of a roof opening or a window jamb, stays."""
    lo = [b - margin for b in bounds[:3]]
    hi = [b + margin for b in bounds[3:]]
    corners = [(x, y, z) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
    mw = obj.matrix_world
    normal_matrix = mw.to_3x3().inverted_safe().transposed()
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    doomed = []
    for f in bm.faces:
        c = mw @ f.calc_center_median()
        if all(lo[i] <= c[i] <= hi[i] for i in range(3)):
            continue
        n = normal_matrix @ f.normal
        if all(sum(n[i] * (q[i] - c[i]) for i in range(3)) <= 0 for q in corners):
            doomed.append(f)
    if doomed:
        bmesh.ops.delete(bm, geom=doomed, context='FACES')
        bm.to_mesh(obj.data)
    bm.free()
    return len(obj.data.polygons) > 0

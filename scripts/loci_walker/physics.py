"""Collision world and character movement against the scene's meshes.

The world is baked once, when play starts, into a single BVH of every visible
mesh (instances included). Anything in the player collection, or carrying a
truthy `loci_nocollide` custom property, is left out.
"""
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from .character import COLLECTION
from .geometry import is_volume_only

UP = Vector((0.0, 0.0, 1.0))
DOWN = Vector((0.0, 0.0, -1.0))
GROUND_SNAP = 0.3  # how far down we stick to the ground while walking (stairs, slopes)


def _is_collider(obj):
    """Same rules as the web export (loci_export.collect): no player, no
    walk-through props, nothing hidden from render (boolean cutters), no haze."""
    if obj.type != 'MESH' or obj.get("loci_nocollide") or obj.hide_render:
        return False
    if is_volume_only(obj):
        return False
    return not any(c.name == COLLECTION for c in obj.users_collection)


def build_world(context):
    """Bake every visible mesh (instances included) into one static BVH.
    Triangles are read in bulk, so large scenes build quickly."""
    depsgraph = context.evaluated_depsgraph_get()
    vert_blocks, tri_blocks, offset = [], [], 0
    for inst in depsgraph.object_instances:
        obj = inst.object
        if not _is_collider(obj.original) or obj.original.particle_systems:
            continue
        if inst.is_instance and inst.particle_system is not None:
            continue  # dust, sparks... the exporter leaves particles out too
        if not inst.is_instance and not obj.original.visible_get():
            continue
        mesh = obj.to_mesh()
        if mesh is None:
            continue
        mesh.calc_loop_triangles()
        n_verts, n_tris = len(mesh.vertices), len(mesh.loop_triangles)
        if n_tris:
            co = np.empty(n_verts * 3, dtype=np.float32)
            mesh.vertices.foreach_get("co", co)
            co = co.reshape(-1, 3)
            mw = np.array(inst.matrix_world, dtype=np.float32)
            vert_blocks.append(co @ mw[:3, :3].T + mw[:3, 3])
            tris = np.empty(n_tris * 3, dtype=np.int32)
            mesh.loop_triangles.foreach_get("vertices", tris)
            tri_blocks.append(tris.reshape(-1, 3) + offset)
            offset += n_verts
        obj.to_mesh_clear()
    if not tri_blocks:
        return None
    verts = np.concatenate(vert_blocks).tolist()
    tris = np.concatenate(tri_blocks).tolist()
    return BVHTree.FromPolygons(verts, tris, all_triangles=True)


class Mover:
    """A capsule-ish body: spheres stacked above the step height, plus a ground ray."""

    def __init__(self, bvh, radius=0.3, height=1.75, step_height=0.35):
        self.bvh = bvh
        self.radius = radius
        self.height = height
        self.step_height = step_height
        top = height - radius
        h = step_height + radius
        self._samples = []
        while h < top:
            self._samples.append(h)
            h += radius
        self._samples.append(top)

    def move(self, pos, velocity, vz, dt, gravity, grounded):
        """Advance one tick. Returns (position, vertical speed, grounded)."""
        pos = pos.copy()
        delta = Vector((velocity.x, velocity.y, 0.0)) * dt
        steps = int(delta.length / (self.radius * 0.5)) + 1
        delta /= steps
        for _ in range(steps):
            pos += delta
            self._push_out(pos)

        vz -= gravity * dt
        if vz > 0.0 and self.ray(pos + Vector((0, 0, self.height - 0.05)), UP, vz * dt + 0.05) is not None:
            vz = 0.0
        pos.z += vz * dt

        fall = max(0.0, -vz * dt)
        origin = pos + Vector((0.0, 0.0, fall + self.step_height))
        hit = self.bvh.ray_cast(origin, DOWN, fall + self.step_height + GROUND_SNAP)[0]
        snap = GROUND_SNAP if grounded else 0.0
        if hit is not None and vz <= 0.0 and pos.z <= hit.z + snap:
            pos.z = hit.z
            return pos, 0.0, True
        return pos, vz, False

    def ray(self, origin, direction, distance):
        """Distance to the first hit along the ray, or None."""
        return self.bvh.ray_cast(origin, direction, distance)[3]

    def _push_out(self, pos):
        r = self.radius
        center = pos.copy()
        for _ in range(3):
            moved = False
            for h in self._samples:
                center.x, center.y, center.z = pos.x, pos.y, pos.z + h
                loc, normal, _index, dist = self.bvh.find_nearest(center, r)
                if loc is None or dist >= r:
                    continue
                away = center - loc
                if away.length < 1e-6:
                    away = normal.copy()
                away.normalize()
                correction = away * (r - dist + 1e-3)
                correction.z = 0.0
                if correction.length > 1e-6:
                    pos += correction
                    moved = True
            if not moved:
                return

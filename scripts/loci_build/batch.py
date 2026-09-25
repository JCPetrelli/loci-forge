"""Batch: accumulate many primitives, each with its own material, into one mesh.

One object per piece of furniture keeps the outliner readable and the scene
fast. Positions are world-space; `frame` (a 4x4 matrix) places a group of
primitives together, e.g. a chair built in its own local space.
"""
import math

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector


def _rotation(rot):
    if isinstance(rot, Matrix):
        return rot.to_4x4()
    return Euler(rot).to_matrix().to_4x4()


def frame(location, yaw=0.0):
    """Local frame at `location`, turned `yaw` radians around Z."""
    return Matrix.Translation(location) @ Matrix.Rotation(yaw, 4, 'Z')


class Batch:
    """Primitives merged into one mesh; each primitive's material gets a slot
    on first use."""

    def __init__(self, name):
        self.name = name
        self.materials = []
        self.bm = bmesh.new()

    def _matrix(self, center, rot, scale, frame):
        m = Matrix.Translation(center) @ _rotation(rot) @ Matrix.Diagonal((*scale, 1.0))
        return frame @ m if frame is not None else m

    def _assign(self, verts, mat, smooth):
        if mat not in self.materials:
            self.materials.append(mat)
        index = self.materials.index(mat)
        for face in {f for v in verts for f in v.link_faces}:
            face.material_index = index
            face.smooth = smooth

    def box(self, center, size, mat, rot=(0, 0, 0), frame=None):
        m = self._matrix(center, rot, size, frame)
        verts = bmesh.ops.create_cube(self.bm, size=1.0, matrix=m)["verts"]
        self._assign(verts, mat, False)

    def cyl(self, center, r_bottom, r_top, depth, mat, rot=(0, 0, 0), frame=None,
            segments=24, smooth=True):
        m = self._matrix(center, rot, (1, 1, 1), frame)
        verts = bmesh.ops.create_cone(self.bm, cap_ends=True, segments=segments,
                                      radius1=r_bottom, radius2=r_top, depth=depth, matrix=m)["verts"]
        self._assign(verts, mat, smooth)

    def sphere(self, center, radii, mat, rot=(0, 0, 0), frame=None, segments=20):
        m = self._matrix(center, rot, radii, frame)
        verts = bmesh.ops.create_uvsphere(self.bm, u_segments=segments, v_segments=segments // 2 + 2,
                                          radius=1.0, matrix=m)["verts"]
        self._assign(verts, mat, True)

    def torus(self, center, major, minor, mat, rot=(0, 0, 0), frame=None, segments=48, ring=10):
        """Torus lying in the local XY plane."""
        m = self._matrix(center, rot, (1, 1, 1), frame)
        verts = []
        for i in range(segments):
            a = 2 * math.pi * i / segments
            for j in range(ring):
                b = 2 * math.pi * j / ring
                r = major + minor * math.cos(b)
                verts.append(self.bm.verts.new(m @ Vector((r * math.cos(a), r * math.sin(a), minor * math.sin(b)))))
        for i in range(segments):
            for j in range(ring):
                n, k = (i + 1) % segments, (j + 1) % ring
                self.bm.faces.new((verts[i * ring + j], verts[n * ring + j],
                                   verts[n * ring + k], verts[i * ring + k]))
        self._assign(verts, mat, True)

    def rod(self, start, end, radius, mat, frame=None, segments=12):
        """Cylinder from `start` to `end`."""
        start, end = Vector(start), Vector(end)
        axis = end - start
        rot = axis.to_track_quat('Z', 'Y').to_matrix()
        self.cyl((start + end) / 2, radius, radius, axis.length, mat, rot=rot, frame=frame,
                 segments=segments)

    def build(self, collection, bevel=0.0, nocollide=False):
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces)
        mesh = bpy.data.meshes.new(self.name)
        self.bm.to_mesh(mesh)
        self.bm.free()
        for mat in self.materials:
            mesh.materials.append(mat)
        obj = bpy.data.objects.new(self.name, mesh)
        collection.objects.link(obj)
        if bevel:
            mod = obj.modifiers.new("Bevel", 'BEVEL')
            mod.width = bevel
            mod.segments = 2
            mod.limit_method = 'ANGLE'
        if nocollide:
            obj["loci_nocollide"] = True
        return obj

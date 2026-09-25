"""Mesh, material and collection helpers shared by the player, the palace
build scripts (loci_build) and the exporter (loci_export).

They live in the walker because it is the only package shipped on its own
(`just package`); everything else may import from here, not the reverse.
"""
import bmesh
import bpy
from mathutils import Matrix, Vector


# -- materials ---------------------------------------------------------------

def principled(mat):
    """The material's Principled BSDF node, or None."""
    if mat is None or not mat.node_tree:
        return None
    return next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)


def is_volume_only(obj):
    """Haze boxes and similar: a material with a volume but no surface."""
    for slot in obj.material_slots:
        mat = slot.material
        if not mat or not mat.node_tree:
            continue
        out = next((n for n in mat.node_tree.nodes if n.type == 'OUTPUT_MATERIAL'), None)
        if out and out.inputs["Volume"].is_linked and not out.inputs["Surface"].is_linked:
            return True
    return False


def socket(node, identifier):
    return next(s for s in node.inputs if s.identifier == identifier)


def material(name, color, roughness=0.5, metallic=0.0):
    """Get or create a Principled material; it also shows its colour in Solid view."""
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
        if bpy.app.version < (5, 0, 0):
            mat.use_nodes = True
    bsdf = principled(mat)
    socket(bsdf, "Base Color").default_value = (*color, 1.0)
    socket(bsdf, "Roughness").default_value = roughness
    socket(bsdf, "Metallic").default_value = metallic
    mat.diffuse_color = (*color, 1.0)
    return mat


def ramp_material(name, texture, dark, light, roughness=0.5, **texture_inputs):
    """Material whose base colour is `texture` (a ShaderNodeTex* type, driven
    by Object coordinates) mapped through a two-colour ramp. Re-running it
    updates the colours and texture inputs in place."""
    mat = material(name, light, roughness)
    nt = mat.node_tree
    base = socket(principled(mat), "Base Color")
    if not base.is_linked:
        coords = nt.nodes.new("ShaderNodeTexCoord")
        tex = nt.nodes.new(texture)
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        nt.links.new(coords.outputs["Object"], tex.inputs["Vector"])
        nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], base)
        coords.location, tex.location, ramp.location = (-900, 300), (-700, 300), (-450, 300)
    tex = base.links[0].from_node.inputs["Fac"].links[0].from_node
    ramp = base.links[0].from_node
    for key, value in texture_inputs.items():
        tex.inputs[key].default_value = value
    ramp.color_ramp.elements[0].color = (*dark, 1.0)
    ramp.color_ramp.elements[1].color = (*light, 1.0)
    return mat


def wood_material(name, light, dark, scale=6.0):
    """Wood grain: a distorted wave texture between two colours."""
    mat = ramp_material(name, "ShaderNodeTexWave", dark, light, roughness=0.45,
                        Scale=scale, Distortion=4.0, Detail=3.0)
    socket(principled(mat), "Base Color").links[0].from_node.color_ramp.elements[0].position = 0.2
    return mat


# -- meshes ------------------------------------------------------------------

def add_ellipsoid(radii, center=(0, 0, 0)):
    """bmesh adder: an ellipsoid with the given radii."""
    def add(bm):
        m = Matrix.Translation(center) @ Matrix.Diagonal((*radii, 1.0))
        bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=14, radius=1.0, matrix=m)
    return add


def add_taper(length, r_top, r_bottom, top=(0, 0, 0)):
    """bmesh adder: a tapered cylinder hanging `length` down from `top`."""
    def add(bm):
        m = Matrix.Translation(Vector(top) - Vector((0, 0, length / 2)))
        bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=r_bottom,
                              radius2=r_top, depth=length, matrix=m)
    return add


def smooth_mesh(name, mat, *adders):
    """Mesh made of several smooth-shaded primitives."""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    for add in adders:
        add(bm)
    for f in bm.faces:
        f.smooth = True
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(mat)
    return mesh


# -- objects and collections -------------------------------------------------

def add_object(name, mesh, collection, location=(0, 0, 0), parent=None):
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.parent = parent
    obj.location = location
    return obj


def remove_objects(objects):
    """Delete objects, and their mesh or light data once nothing else uses it."""
    for obj in list(objects):
        data = obj.data
        bpy.data.objects.remove(obj)
        if data is not None and data.users == 0:
            if isinstance(data, bpy.types.Mesh):
                bpy.data.meshes.remove(data)
            elif isinstance(data, bpy.types.Light):
                bpy.data.lights.remove(data)


def ensure_collection(scene, name):
    coll = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if coll.name not in scene.collection.children:
        scene.collection.children.link(coll)
    return coll

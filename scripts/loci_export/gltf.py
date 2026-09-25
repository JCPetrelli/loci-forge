"""Export materials, joining, and the glTF call."""
import bpy

from loci_walker.geometry import principled

from .atlas import UV_NAME, keep_only_bake_uv
from .collect import select_only


def baked_material(name, image):
    mat = bpy.data.materials.new(name)
    if bpy.app.version < (5, 0, 0):
        mat.use_nodes = True
    nt = mat.node_tree
    bsdf = principled(mat)
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = image
    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = UV_NAME
    nt.links.new(uv.outputs["UV"], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    return mat


def assign_baked(obj, material):
    """Every face uses the baked material; only the Bake UVs stay."""
    keep_only_bake_uv(obj)
    obj.data.materials.clear()
    obj.data.materials.append(material)
    obj.data.polygons.foreach_set("material_index", [0] * len(obj.data.polygons))
    for name in [a.name for a in obj.data.attributes if a.name.startswith("loci_")]:
        obj.data.attributes.remove(obj.data.attributes[name])


def join(objects, name):
    select_only(objects)
    if len(objects) > 1:
        bpy.ops.object.join()
    joined = bpy.context.view_layer.objects.active
    joined.name = name
    joined.data.name = name
    return joined


def export(objects, path, **overrides):
    """Export `objects` as GLB, passing only options this Blender knows."""
    select_only(objects)
    options = dict(
        filepath=path, export_format='GLB', use_selection=True, export_extras=True,
        export_apply=True, export_yup=True, export_lights=False, export_cameras=False,
        export_animations=False, export_image_format='JPEG', export_image_quality=88,
        export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6,
        export_draco_position_quantization=14, export_draco_normal_quantization=10,
        export_draco_texcoord_quantization=12,
    )
    options.update(overrides)
    known = bpy.ops.export_scene.gltf.get_rna_type().properties.keys()
    bpy.ops.export_scene.gltf(**{k: v for k, v in options.items() if k in known})

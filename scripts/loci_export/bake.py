"""Cycles lighting bake into atlas images."""
import bpy

from loci_walker.geometry import principled, socket

from .collect import materials_of, select_only

NODE_NAME = "LociBakeTarget"


def setup_cycles(scene, samples, use_gpu=True):
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'  # unless a GPU is found below
    if use_gpu:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for backend in ("METAL", "OPTIX", "CUDA", "HIP", "ONEAPI"):
            try:
                prefs.compute_device_type = backend
            except TypeError:
                continue
            prefs.get_devices()
            gpus = [d for d in prefs.devices if d.type != 'CPU']
            if gpus:
                for d in prefs.devices:
                    d.use = d.type != 'CPU'
                scene.cycles.device = 'GPU'
                print(f"[bake] GPU: {', '.join(d.name for d in gpus)}")
                break
    scene.cycles.samples = samples
    scene.cycles.use_adaptive_sampling = False
    scene.cycles.sample_clamp_indirect = 5.0
    bake = scene.render.bake
    bake.target = 'IMAGE_TEXTURES'
    bake.margin = 6
    bake.use_pass_direct = True
    bake.use_pass_indirect = True
    bake.use_pass_diffuse = True
    bake.use_pass_emit = True
    bake.use_pass_glossy = False  # view-dependent; it would look painted on
    bake.use_pass_transmission = False


def prepare_for_bake(materials):
    """Adjust materials (in the throwaway export session) so the bake matches
    what Blender shows:

    - Metals bake with their colour. The glossy pass is left out of the bake
      (reflections would look painted on), and a metal's colour lives entirely
      in its reflections, so brass and steel would otherwise bake black.
    - Tangent-space normal maps are unplugged. Without UVs they do nothing in
      the scene; the bake's own UV layout would switch them on, with tangents
      pointing a different way on every island.
    """
    for mat in materials:
        nt = mat.node_tree
        for node in nt.nodes:
            if node.type == 'NORMAL_MAP' and node.space == 'TANGENT':
                for link in list(node.outputs["Normal"].links):
                    nt.links.remove(link)
        bsdf = principled(mat)
        if bsdf is None:
            continue
        metallic = socket(bsdf, "Metallic")
        for link in list(metallic.links):
            nt.links.remove(link)
        metallic.default_value = 0.0


def bake_atlas(objects, image):
    """Bake COMBINED (diffuse lighting + emission) of `objects` into `image`."""
    materials = materials_of(objects)
    prepare_for_bake(materials)
    for mat in materials:
        nodes = mat.node_tree.nodes
        node = nodes.get(NODE_NAME) or nodes.new("ShaderNodeTexImage")
        node.name = NODE_NAME
        node.image = image
        for n in nodes:
            n.select = False
        node.select = True
        nodes.active = node
    select_only(objects)
    bpy.ops.object.bake(type='COMBINED', use_clear=True, margin=bpy.context.scene.render.bake.margin)


def save_display(image, path, scene, quality=88):
    """Save with the scene's view transform applied (AgX etc.), as a JPEG."""
    settings = scene.render.image_settings
    settings.file_format = 'JPEG'
    settings.quality = quality
    settings.color_mode = 'RGB'
    image.save_render(path, scene=scene)

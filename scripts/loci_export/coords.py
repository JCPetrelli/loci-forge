"""Keep procedural textures in place when objects are joined.

Most palace materials place their textures with Object coordinates, or with
Generated coordinates (the default for procedural textures). Both are
relative to each object, so joining objects would slide every texture. We
store both per vertex as attributes before joining, and rewire the materials
to read the attributes instead.
"""
import numpy as np

OBJECT_ATTR = "loci_object_co"
GENERATED_ATTR = "loci_generated_co"
RENDER_UV = "loci_render_uv"  # every object's render UV map, renamed alike before joining
PROCEDURAL = {'TEX_NOISE', 'TEX_WAVE', 'TEX_VORONOI', 'TEX_GRADIENT', 'TEX_MAGIC',
              'TEX_CHECKER', 'TEX_BRICK', 'TEX_WHITE_NOISE'}


def store(obj):
    mesh = obj.data
    co = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", co)
    lo = np.array(mesh.texspace_location - mesh.texspace_size, dtype=np.float32)
    span = np.maximum(2 * np.array(mesh.texspace_size, dtype=np.float32), 1e-6)
    generated = ((co.reshape(-1, 3) - lo) / span).ravel()
    for name, values in ((OBJECT_ATTR, co), (GENERATED_ATTR, generated)):
        attr = mesh.attributes.get(name) or mesh.attributes.new(name, 'FLOAT_VECTOR', 'POINT')
        attr.data.foreach_set("vector", values)
    # Image textures with no explicit UV read the render UV map. After a join
    # that is whatever the first object had, so give every object's the same
    # name and point those textures at it by name (see _rewire).
    render_uv = next((l for l in mesh.uv_layers if l.active_render), None)
    if render_uv is not None:
        render_uv.name = RENDER_UV


def _attribute_node(tree, name, near):
    node = tree.nodes.new("ShaderNodeAttribute")
    node.attribute_type = 'GEOMETRY'
    node.attribute_name = name
    node.location = (near.location.x - 200, near.location.y)
    return node


def _rewire(tree, done):
    if tree in done:
        return
    done.add(tree)
    for node in list(tree.nodes):
        if node.type == 'TEX_COORD':
            for output, attr in (("Object", OBJECT_ATTR), ("Generated", GENERATED_ATTR)):
                links = list(node.outputs[output].links)
                if links:
                    source = _attribute_node(tree, attr, node)
                    for link in links:  # linking an input replaces its old link
                        tree.links.new(source.outputs["Vector"], link.to_socket)
        elif node.type == 'TEX_IMAGE':
            vector = node.inputs.get("Vector")
            if vector is not None and not vector.is_linked:
                uv = tree.nodes.new("ShaderNodeUVMap")
                uv.uv_map = RENDER_UV
                uv.location = (node.location.x - 200, node.location.y)
                tree.links.new(uv.outputs["UV"], vector)
        elif node.type in PROCEDURAL:
            vector = node.inputs.get("Vector")
            if vector is not None and not vector.is_linked:
                source = _attribute_node(tree, GENERATED_ATTR, node)
                tree.links.new(source.outputs["Vector"], vector)
        elif node.type == 'GROUP' and node.node_tree:
            _rewire(node.node_tree, done)


def rewire(materials):
    done = set()
    for mat in materials:
        if mat and mat.node_tree:
            _rewire(mat.node_tree, done)

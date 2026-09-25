"""Procedural materials for props. All reuse an existing material by name."""
from loci_walker.geometry import material as plain
from loci_walker.geometry import principled, ramp_material, socket

__all__ = ["plain", "emissive", "fabric"]


def emissive(name, color, strength, base=None, roughness=0.4):
    mat = plain(name, base or color, roughness)
    bsdf = principled(mat)
    socket(bsdf, "Emission Color").default_value = (*color, 1.0)
    socket(bsdf, "Emission Strength").default_value = strength
    return mat


def fabric(name, dark, light, scale=60.0, roughness=0.95):
    """Mottled woven look: fine noise between two colours."""
    return ramp_material(name, "ShaderNodeTexNoise", dark, light, roughness,
                         Scale=scale, Detail=6.0)

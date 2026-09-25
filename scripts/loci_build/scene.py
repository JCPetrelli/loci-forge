"""Collections and lights."""
import bpy

from loci_walker.geometry import ensure_collection, remove_objects


def reset_collection(scene, name):
    """Empty (or create) a collection so a build script can re-run cleanly."""
    coll = ensure_collection(scene, name)
    remove_objects(coll.all_objects)
    return coll


def point_light(collection, name, location, energy, color=(1.0, 0.75, 0.48), radius=0.05):
    light = bpy.data.lights.new(name, 'POINT')
    light.energy = energy
    light.color = color
    light.shadow_soft_size = radius
    obj = bpy.data.objects.new(name, light)
    obj.location = location
    collection.objects.link(obj)
    return obj

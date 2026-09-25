"""Loci Walker: walk through a Blender scene like a game, in first or third person."""
import bpy
from bpy.props import PointerProperty

from . import controller, props, ui

bl_info = {
    "name": "Loci Walker",
    "author": "Jacopo Castellano",
    "version": (0, 1, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Loci",
    "description": "Walk through the scene like a game, in first or third person",
    "category": "3D View",
}

_classes = (
    props.LociWalkerSettings,
    controller.LOCI_OT_play,
    controller.LOCI_OT_place_player,
    ui.LOCI_PT_walker,
)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.loci_walker = PointerProperty(type=props.LociWalkerSettings)


def unregister():
    del bpy.types.Scene.loci_walker
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)

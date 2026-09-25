"""Group objects into texture atlases and give them a shared 'Bake' UV layout."""
import math

import bpy

from .collect import select_only

UV_NAME = "Bake"
PACKING = 0.55  # share of an atlas that islands actually cover


def group(areas, size, density):
    """Split objects into atlases so each holds about the same texel density
    (`density` pixels per metre). `areas` maps object -> world area.
    Biggest objects first, greedy fill."""
    budget = (size / density) ** 2 * PACKING
    atlases, current, used = [], [], 0.0
    for obj, area in sorted(areas.items(), key=lambda kv: kv[1], reverse=True):
        if current and used + area > budget:
            atlases.append(current)
            current, used = [], 0.0
        current.append(obj)
        used += area
    if current:
        atlases.append(current)
    return atlases


def unwrap(objects, margin=0.003):
    """Smart-project all objects together into one 0..1 UV space."""
    for obj in objects:
        layer = obj.data.uv_layers.get(UV_NAME) or obj.data.uv_layers.new(name=UV_NAME)
        obj.data.uv_layers.active = layer
    select_only(objects)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.reveal()
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=margin,
                             area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.average_islands_scale()
    bpy.ops.uv.pack_islands(margin=margin)
    bpy.ops.object.mode_set(mode='OBJECT')


def keep_only_bake_uv(obj):
    for layer in [l for l in obj.data.uv_layers if l.name != UV_NAME]:
        obj.data.uv_layers.remove(layer)

"""Drives the 3D viewport itself as the game camera, and puts it back afterwards.

Yaw 0 looks along +Y; positive pitch looks up.
"""
import math

from mathutils import Euler, Vector

FIRST_PERSON_DISTANCE = 0.01
# A perspective viewport shows twice the view plane of a camera with the same
# lens (Blender's CAMERA_PARAM_ZOOM_INIT_PERSP), so the walker's lens, which is
# a real camera focal length on a 36 mm sensor (as in the web player), is
# doubled before it is given to the viewport.
VIEWPORT_LENS_FACTOR = 2.0
CAMERA_MARGIN = 0.2


def rotation(yaw, pitch):
    return Euler((math.pi / 2 + pitch, 0.0, yaw)).to_quaternion()


def forward(yaw):
    return Vector((-math.sin(yaw), math.cos(yaw), 0.0))


def right(yaw):
    return Vector((math.cos(yaw), math.sin(yaw), 0.0))


def first_person(rv3d, eye, yaw, pitch):
    rot = rotation(yaw, pitch)
    rv3d.view_rotation = rot
    rv3d.view_distance = FIRST_PERSON_DISTANCE
    rv3d.view_location = eye - rot @ Vector((0.0, 0.0, FIRST_PERSON_DISTANCE))


def third_person(rv3d, pivot, yaw, pitch, distance, mover):
    """Orbit behind the pivot, pulling in when a wall is in the way."""
    rot = rotation(yaw, pitch)
    back = rot @ Vector((0.0, 0.0, 1.0))
    hit = mover.ray(pivot, back, distance + CAMERA_MARGIN)
    if hit is not None:
        distance = max(CAMERA_MARGIN, hit - CAMERA_MARGIN)
    rv3d.view_rotation = rot
    rv3d.view_distance = distance
    rv3d.view_location = pivot


class ViewportState:
    """Snapshot of everything play mode changes on a 3D view."""

    def __init__(self, space, rv3d):
        self.space, self.rv3d = space, rv3d
        self.location = rv3d.view_location.copy()
        self.rotation = rv3d.view_rotation.copy()
        self.distance = rv3d.view_distance
        self.perspective = rv3d.view_perspective
        self.lens = space.lens
        self.clip_start = space.clip_start
        self.overlays = space.overlay.show_overlays
        self.gizmos = space.show_gizmo

    def enter_play(self, settings):
        self.rv3d.view_perspective = 'PERSP'
        self.space.lens = settings.lens * VIEWPORT_LENS_FACTOR
        self.space.clip_start = 0.02
        if settings.hide_overlays:
            self.space.overlay.show_overlays = False
            self.space.show_gizmo = False

    def restore(self):
        self.rv3d.view_perspective = self.perspective
        self.rv3d.view_location = self.location
        self.rv3d.view_rotation = self.rotation
        self.rv3d.view_distance = self.distance
        self.space.lens = self.lens
        self.space.clip_start = self.clip_start
        self.space.overlay.show_overlays = self.overlays
        self.space.show_gizmo = self.gizmos

"""The play-mode modal operator: input, movement, character pose and camera."""
import math
import time

import bpy
from mathutils import Vector

from . import camera, character, physics

MOVE_KEYS = {
    'W': (0, 1), 'UP_ARROW': (0, 1),
    'S': (0, -1), 'DOWN_ARROW': (0, -1),
    'A': (-1, 0), 'LEFT_ARROW': (-1, 0),
    'D': (1, 0), 'RIGHT_ARROW': (1, 0),
}
RUN_KEYS = {'LEFT_SHIFT', 'RIGHT_SHIFT'}
HELP = "WASD move · Mouse look · Shift run · Space jump · V first/third person · Wheel zoom · Esc exit"
PITCH_LIMIT = math.radians(80)
FALL_LIMIT = 50.0  # metres below the start point before respawning


def _turn_towards(current, target, t):
    diff = (target - current + math.pi) % (2 * math.pi) - math.pi
    return current + diff * t


class LOCI_OT_play(bpy.types.Operator):
    bl_idname = "loci.play"
    bl_label = "Walk"
    bl_description = "Walk through the scene like a game. Esc to exit"

    @classmethod
    def poll(cls, context):
        return context.area is not None and context.area.type == 'VIEW_3D'

    def invoke(self, context, event):
        self.area = context.area
        self.window = context.window
        self.region = next(r for r in self.area.regions if r.type == 'WINDOW')
        self.space = self.area.spaces.active
        if self.space.region_quadviews:
            self.report({'ERROR'}, "Leave quad view first")
            return {'CANCELLED'}
        self.rv3d = self.space.region_3d
        self.settings = context.scene.loci_walker

        bvh = physics.build_world(context)
        if bvh is None:
            self.report({'ERROR'}, "Nothing to walk on: the scene has no visible meshes")
            return {'CANCELLED'}
        self.mover = physics.Mover(bvh, height=self.settings.eye_height + 0.13)

        self.root = character.ensure_player(context)
        self.parts = character.parts(self.root)
        self.spawn = self.root.location.copy()
        self.yaw = self.root.rotation_euler.z
        self.pitch = -0.15
        self.vz = 0.0
        self.grounded = False
        self.phase = 0.0
        self.stride = 0.0
        self.air = self.rise = self.land = 0.0
        self.keys = set()
        self.third = self.settings.third_person

        self.view = camera.ViewportState(self.space, self.rv3d)
        self.view.enter_play(self.settings)
        character.set_visible(self.parts, self.third)

        wm = context.window_manager
        self.timer = wm.event_timer_add(1 / 60, window=self.window)
        self.window.cursor_modal_set('NONE')
        self.window.cursor_warp(*self._center())
        self.mouse_ref = None
        self.last_state = None
        self.last = time.perf_counter()
        context.workspace.status_text_set(HELP)
        wm.modal_handler_add(self)
        self._update_view()
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        kind, value = event.type, event.value
        if kind == 'TIMER':
            self._tick()
        elif kind == 'MOUSEMOVE':
            self._look(event)
        elif kind == 'ESC' and value == 'PRESS':
            self._finish(context)
            return {'FINISHED'}
        elif kind == 'WINDOW_DEACTIVATE':
            self.keys.clear()
        elif kind == 'V' and value == 'PRESS' and not event.is_repeat:
            self.third = not self.third
            character.set_visible(self.parts, self.third)
        elif kind == 'SPACE' and value == 'PRESS' and self.grounded:
            self.vz = self.settings.jump_speed
            self.grounded = False
        elif kind in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
            factor = 0.9 if kind == 'WHEELUPMOUSE' else 1.1
            s = self.settings
            s.third_person_distance = min(12.0, max(0.5, s.third_person_distance * factor))
        elif kind in MOVE_KEYS or kind in RUN_KEYS:
            if value == 'PRESS':
                self.keys.add(kind)
            elif value == 'RELEASE':
                self.keys.discard(kind)
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        self._finish(context)

    # -- per-event work -------------------------------------------------

    def _center(self):
        return (self.region.x + self.region.width // 2,
                self.region.y + self.region.height // 2)

    def _look(self, event):
        # Deltas are measured from the last reported position, never from the
        # computed centre: on HiDPI screens cursor_warp lands a pixel off, and
        # measuring against the centre turns that into endless slow rotation.
        mx, my = event.mouse_x, event.mouse_y
        if self.mouse_ref is None:
            self.mouse_ref = (mx, my)
            return
        dx, dy = mx - self.mouse_ref[0], my - self.mouse_ref[1]
        self.mouse_ref = (mx, my)
        s = self.settings
        self.yaw -= dx * s.mouse_sensitivity
        self.pitch += (-dy if s.invert_mouse_y else dy) * s.mouse_sensitivity
        self.pitch = max(-PITCH_LIMIT, min(PITCH_LIMIT, self.pitch))

        cx, cy = self._center()
        if abs(mx - cx) > self.region.width // 4 or abs(my - cy) > self.region.height // 4:
            self.window.cursor_warp(cx, cy)
            self.mouse_ref = None  # the next event re-anchors after the jump

    def _tick(self):
        now = time.perf_counter()
        dt = min(now - self.last, 0.05)
        self.last = now
        s = self.settings

        ix = sum(MOVE_KEYS[k][0] for k in self.keys if k in MOVE_KEYS)
        iy = sum(MOVE_KEYS[k][1] for k in self.keys if k in MOVE_KEYS)
        wish = camera.right(self.yaw) * ix + camera.forward(self.yaw) * iy
        moving = wish.length > 1e-6
        if moving:
            wish.normalize()
        running = bool(self.keys & RUN_KEYS)
        speed = s.walk_speed * (s.run_multiplier if running else 1.0)

        was_grounded, fall_speed = self.grounded, -self.vz
        pos, self.vz, self.grounded = self.mover.move(
            self.root.location, wish * speed, self.vz, dt, s.gravity, self.grounded)
        if pos.z < self.spawn.z - FALL_LIMIT:
            pos, self.vz = self.spawn.copy(), 0.0

        facing = self.root.rotation_euler.z
        if not self.third:
            facing = self.yaw
        elif moving:
            facing = _turn_towards(facing, math.atan2(-wish.x, wish.y), min(1.0, dt * 12))

        walking = moving and self.grounded
        self.stride += ((1.0 if walking else 0.0) - self.stride) * min(1.0, dt * 10)
        if walking:
            self.phase += dt * speed * 3.2
        self.air += ((0.0 if self.grounded else 1.0) - self.air) * min(1.0, dt * 14)
        self.rise += ((1.0 if self.vz > 0 else 0.0) - self.rise) * min(1.0, dt * 8)
        if self.grounded and not was_grounded and fall_speed > 1.0:
            self.land = min(1.0, fall_speed / 6.0)  # harder landings crouch deeper
        self.land = max(0.0, self.land - dt * 4.0)

        state = (pos.to_tuple(4), round(facing, 4), self.yaw, self.pitch, round(self.stride, 4),
                 round(self.phase, 3), round(self.air, 3), round(self.land, 3),
                 self.third, s.third_person_distance)
        if state == self.last_state:
            return  # nothing moved: skip writing transforms and redrawing
        self.last_state = state

        self.root.location = pos
        self.root.rotation_euler.z = facing
        character.animate(self.parts, self.phase, self.stride * (1.3 if running else 1.0),
                          air=self.air, rise=self.rise, land=self.land)
        self._update_view()
        self.area.tag_redraw()

    def _update_view(self):
        s = self.settings
        loc = self.root.location
        if self.third:
            pivot = loc + Vector((0.0, 0.0, s.eye_height * 0.95)) + camera.right(self.yaw) * 0.35
            camera.third_person(self.rv3d, pivot, self.yaw, self.pitch, s.third_person_distance, self.mover)
        else:
            camera.first_person(self.rv3d, loc + Vector((0.0, 0.0, s.eye_height)), self.yaw, self.pitch)

    def _finish(self, context):
        context.window_manager.event_timer_remove(self.timer)
        self.window.cursor_modal_restore()
        self.view.restore()
        character.set_visible(self.parts, True)
        character.animate(self.parts, 0.0, 0.0)
        self.settings.third_person = self.third
        context.workspace.status_text_set(None)
        self.area.tag_redraw()


class LOCI_OT_place_player(bpy.types.Operator):
    bl_idname = "loci.place_player"
    bl_label = "Place Player at 3D Cursor"
    bl_description = "Move the player (creating it if needed) to the 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        root = character.ensure_player(context)
        root.location = context.scene.cursor.location
        return {'FINISHED'}

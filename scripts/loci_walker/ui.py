"""Sidebar panel: View3D > Sidebar (N) > Loci."""
import bpy


class LOCI_PT_walker(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Loci"
    bl_label = "Loci Walker"

    def draw(self, context):
        s = context.scene.loci_walker
        layout = self.layout

        col = layout.column(align=True)
        col.scale_y = 1.4
        col.operator("loci.play", icon='PLAY')
        layout.operator("loci.place_player", icon='PIVOT_CURSOR')

        box = layout.box()
        box.label(text="Movement")
        box.prop(s, "walk_speed")
        box.prop(s, "run_multiplier")
        box.prop(s, "jump_speed")
        box.prop(s, "gravity")

        box = layout.box()
        box.label(text="Camera")
        box.prop(s, "third_person")
        box.prop(s, "third_person_distance")
        box.prop(s, "eye_height")
        box.prop(s, "lens")
        box.prop(s, "mouse_sensitivity")
        box.prop(s, "invert_mouse_y")
        box.prop(s, "hide_overlays")

        col = layout.column(align=True)
        for line in ("WASD / arrows: move", "Mouse: look", "Shift: run   Space: jump",
                     "V: first / third person", "Wheel: camera distance", "Esc: exit"):
            col.label(text=line)

"""Per-scene walker settings, shown in the sidebar panel."""
import bpy
from bpy.props import BoolProperty, FloatProperty


class LociWalkerSettings(bpy.types.PropertyGroup):
    walk_speed: FloatProperty(name="Walk Speed", default=2.2, min=0.1, soft_max=10.0,
                              description="Metres per second")
    run_multiplier: FloatProperty(name="Run Multiplier", default=2.2, min=1.0, soft_max=5.0,
                                  description="Speed factor while Shift is held")
    jump_speed: FloatProperty(name="Jump Speed", default=4.2, min=0.0, soft_max=15.0)
    gravity: FloatProperty(name="Gravity", default=9.81, min=0.0, soft_max=30.0)
    mouse_sensitivity: FloatProperty(name="Mouse Sensitivity", default=0.0025,
                                     min=0.0002, max=0.02, precision=4)
    invert_mouse_y: BoolProperty(name="Invert Mouse Y", default=False)
    eye_height: FloatProperty(name="Eye Height", default=1.62, min=0.2, soft_max=3.0, unit='LENGTH')
    third_person_distance: FloatProperty(name="Camera Distance", default=3.0, min=0.5,
                                         soft_max=12.0, unit='LENGTH',
                                         description="Third-person distance (mouse wheel while walking)")
    third_person: BoolProperty(name="Third Person", default=True,
                               description="Start in third person (V toggles while walking)")
    lens: FloatProperty(name="Lens", default=18.0, min=8.0, max=120.0,
                        description="Focal length while walking, as a camera on a 36 mm "
                                    "sensor (18 mm is about 90 degrees across)")
    hide_overlays: BoolProperty(name="Hide Overlays", default=True,
                                description="Hide grid, gizmos and outlines while walking")

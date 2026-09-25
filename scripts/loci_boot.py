"""Embedded in the .blend as a registered text block: loads Loci Walker from the
repo's scripts/ folder whenever the file opens (needs "Allow Execution").

Running it again from the Text Editor reloads the add-on after you edit it.
"""
import os
import sys

import bpy

scripts_dir = os.path.join(bpy.path.abspath("//"), "scripts")
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)


def _from_repo(module):
    path = getattr(module, "__file__", None) or ""
    return os.path.dirname(os.path.dirname(os.path.abspath(path))) == os.path.abspath(scripts_dir)


loaded = sys.modules.get("loci_walker")
if hasattr(bpy.types, "LOCI_OT_play") and not (loaded and _from_repo(loaded)):
    pass  # installed as an add-on (`just package`): leave that copy running
else:
    if loaded is not None:  # re-running this text reloads the repo copy after edits
        try:
            loaded.unregister()
        except Exception:
            pass
        for name in [n for n in sys.modules if n == "loci_walker" or n.startswith("loci_walker.")]:
            del sys.modules[name]
    import loci_walker  # noqa: E402
    loci_walker.register()

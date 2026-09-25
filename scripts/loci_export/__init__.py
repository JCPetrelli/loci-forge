"""Turn a palace .blend into a self-contained web scene.

Pipeline (see scripts/export_web.py): collect renderable objects, convert
them to plain meshes, unwrap them into shared atlases, bake Cycles lighting
into those atlases, then join and export as glTF next to a small JSON file
the web player reads.
"""

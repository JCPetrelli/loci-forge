blender := env_var_or_default("BLENDER", "/Applications/Blender.app/Contents/MacOS/Blender")

# Open the base file with scripts allowed, so Loci Walker loads
run file="loci_base.blend":
    "{{blender}}" --enable-autoexec "{{file}}"

# Regenerate loci_base.blend from scripts/build_base.py
build:
    "{{blender}}" -b --factory-startup --python scripts/build_base.py

# Zip the add-on for Edit > Preferences > Add-ons > Install from Disk
package:
    rm -f loci_walker.zip && cd scripts && zip -rq ../loci_walker.zip loci_walker -x "*/__pycache__/*"

# Download the Poly Haven textures loci_start.blend uses into textures/
textures:
    python3 scripts/fetch_textures.py

# Bake and export a palace for the web player (see scripts/export_web.py for options)
export file="loci_start.blend" palace="archive" *args="":
    "{{blender}}" -b "{{file}}" --python scripts/export_web.py -- --palace {{palace}} {{args}}

# Serve the web player on http://localhost:8765/?palace=archive
run-web port="8765":
    python3 scripts/serve_web.py {{port}}

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

loci-forge builds memory palaces (method of loci) in Blender and plays them in the browser. Claude's job is the palace: well-spaced, distinct loci on a fixed route, and a tutorial that teaches the technique. Claude never generates the mnemonic images or assigns the user's notions to loci; making and placing images is the human part of the method. There are two runtimes: Python inside Blender (`scripts/`, `palaces/`) and a static three.js player (`web/`). There is no test suite, linter or build step.

## Commands

All recipes live in the `justfile`; Blender is found via `$BLENDER` (default `/Applications/Blender.app/...`).

```sh
just run [file]        # open loci_base.blend with autoexec, so Loci Walker loads
just build             # regenerate loci_base.blend from scripts/build_base.py (headless)
just package           # zip scripts/loci_walker as an installable add-on
just textures          # download the Poly Haven textures loci_start.blend needs (gitignored)
just export            # bake loci_start.blend into web/assets/archive/ (~6 min, Cycles GPU)
just export loci_start.blend archive --size 2048 --density 45 --samples 32   # ~1 min preview bake
just run-web           # serve web/ with no-cache headers on http://localhost:8765/?palace=archive
```

Rebuild the Archive's furniture inside a running Blender (e.g. through the Blender MCP server), then save the .blend before exporting — `just export` reads the file from disk:

```python
exec(open(bpy.path.abspath("//palaces/archive/furnish.py")).read())
bpy.ops.wm.save_mainfile()
```

## Architecture

**Package layering (Blender side).** `scripts/loci_walker/` is the only package shipped on its own (`just package`), so it owns the shared helpers in `geometry.py` (materials, sockets, collections). `loci_build/` (primitives for palace scripts) and `loci_export/` (web export) import from it; never the reverse. The .blend files load the walker from the repo through an embedded, registered text block (`scripts/loci_boot.py`), so `.blend` files must live in the repo root.

**A palace** is a `.blend` plus `palaces/<name>/`: an idempotent build script (`furnish.py` empties and refills one collection, `Archive_Furnishing`, and sets the scene custom property `loci_export` with per-palace export settings such as the interior box) and `loci.json`, the ordered loci in **Blender coordinates**. `loci_build.Batch` merges many primitives, each with its own material, into one object per piece of furniture.

**Object contract via custom properties**, used by the walker's collision, the exporter and the player alike: `loci_nocollide` (walk-through; exported into separate "decor" meshes), glass materials (split off and tagged `loci_glass` in glTF extras), and the player collection (never exported or collided).

**Export pipeline** (`scripts/export_web.py` driving `loci_export/`): collect visible renderables → realize to plain meshes → cull exterior faces outside the interior box → split glass → group objects into atlases by texel density → store Object/Generated coords per vertex (`coords.py`, so procedural textures don't slide when joined) → unwrap → join per atlas and collision flag → bake Cycles lighting for *all* atlases before swapping any material → Draco `palace.glb`. It also writes `mannequin.glb`, `palace.json` (spawn, walker settings, export time) and copies `palaces/<name>/loci.json`. It never saves the .blend. Walker settings are read by registering the add-on, because Blender 5 hides `bpy.props` values from `scene.get`.

**Web player** (`web/src/`, ES modules, three.js and three-mesh-bvh from a CDN import map): draws the baked atlases unlit, collides with a BVH of the same meshes, and ports the Blender walker's physics one to one (`physics.js`, `player.js`). Blender Z-up maps to three as `(x, y, z) -> (x, z, -y)`. `palace.json` is fetched with `no-cache` and its `exported` time versions the `.glb` URLs; don't drop that, or re-exports hide behind the browser cache. `window.loci` exposes `player`, `scene`, `camera`, `renderer` and `hints` for console testing (set the camera and call `renderer.render` to screenshot without pointer lock).

**Loci hints** (`web/src/loci.js`, key `L`): sprite badges from `loci.json`, drawn twice (depth-tested, plus a faint copy through walls). Every 5th locus gets a gold hand badge and every 10th a purple "Decimus" badge — a rule in code, not data, from the *Rhetorica ad Herennium*. Editing `loci.json` needs no re-bake: copy it to `web/assets/<palace>/` and reload.

## Designing loci

- Never make look-alike objects separate loci (the three display cases are one locus, the two paintings one). Each locus should be a different kind of thing, and no locus should stand directly above another across floors.
- The Archive route: entrance door (1), armillary sphere (2), then clockwise seen from above round the ground floor to the piano (10), up the stairs, along the gallery to the arched door onward (15), which will lead to the next environment.
- `research/` (gitignored, local only) holds a method-of-loci report and notes meant for the upcoming tutorial; read `research/reports/Method of loci technique.md` before designing tutorial features.

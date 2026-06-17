# TDU2 Blender Addon

Blender addon for importing TDU2 (Test Drive Unlimited 2) model files
(.3DG/.3DD, .2DM, .2DB).

**Status**: Work in progress — import works, export not yet functional.

## Features

- **Model Import** (.3DG/.3DD): geometry, normals, UVs, triangle indices
- **Material Import** (.2DM): diffuse/ambient/specular/emissive colors, texture layers
- **Texture Import** (.2DB): DXT1, DXT5, ARGB8 decompression to Blender images
- **Material Assignment**: automatic mapping of mesh groups to materials via
  group-name / texture-name matching
- **StringDemangler**: decodes mangled 8-byte TDU2 strings back to readable names
- **Half-float Support**: 16-bit half-precision floating-point vertex data

## Installation

1. Copy `io_scene_tdu2/` to your Blender addons path, e.g.:
   ```
   %APPDATA%\Blender Foundation\Blender\3.3\scripts\addons\
   ```
2. Enable in Blender: Edit > Preferences > Add-ons > "Import-Export: TDU2 Scene"

Requires Blender 3.3+ and Python 3.7+.

## Usage

1. Place `.3dg`, `.2dm`, and all `.2db` files in the same directory
2. File > Import > TDU2 Model (.3DG/.3DD)
3. Select the `.3dg` file — materials and textures are loaded automatically

## Current Limitations

### Textures
- Textures are imported and assigned to materials, but **may not appear**
  in Blender's **Solid** viewport mode
- Switch to **Material Preview** or **Rendered** viewport mode (`Z` key)
  to see textures
- The root cause is still under investigation

### Material Assignment
- Mesh groups are mapped to materials by a multi-strategy approach:
  1. **Texture filename suffix**: e.g. `370z_body_lr.2db` → group `BODY_LR`
  2. **Hash name match**: 8-byte material hash vs .3dg HASH entry
  3. **Keyword fallback**: semantic mappings (e.g. `MIRROR` → `Mirror`)
- Works for all 58 groups on the 370Z test model, but may need tuning
  for other vehicles

### Export
- The export operator class exists but `writer.py` has not been
  implemented — export will fail at runtime

### General
- No support for skinning/bones
- No support for multiple UV channels
- Material shader networks are not fully replicated in Blender nodes

## File Structure

```
io_scene_tdu2/
├── __init__.py       # Addon registration and metadata
├── operators.py      # Blender operators (import, export)
├── parser.py         # Binary parsers for .3dg, .2dm, .2db
├── types.py          # Data classes (MatFileData, TDU2Mesh, etc.)
└── dds.py            # DXT1/DXT5/ARGB8 decompression
```

## Technical Notes

- `prim.mat_id` in the .3dg file is **always 4** for all segments
  (confirmed by raw hex dump) — material assignment uses external
  name matching, not the PRIM segment's material index field
- `.2db` textures use raw 8-byte internal names (not ASCII strings)
  as cache keys — matching is done on raw bytes, not decoded strings
- The `StringDemangler` handles both plain ASCII names and the
  permuted-encoding mangled names used by TDU2

## License

MIT License

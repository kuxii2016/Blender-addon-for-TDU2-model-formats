# io_scene_tdu2
# Blender addon for importing/exporting TDU2 model formats (.3DG/.3DD, .2DM, .2DB)

__version__ = "1.0.0"
__author__ = "KuxiiSoft"
__doc__ = """Blender addon for TDU2 model formats"""

bl_info = {
    "name": "TDU2 Scene",
    "description": "Import/Export TDU2 model formats (.3DG/.3DD, .2DM, .2DB)",
    "author": "KuxiiSoft",
    "version": (1, 0, 0),
    "blender": (3, 3, 0),
    "location": "File > Import-Export",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "support": "COMMUNITY",
    "category": "Import-Export",
}

from .operators import register, unregister

from enum import IntEnum
from typing import List, Optional, Dict, Any
import struct


class TDU2ObjectType(IntEnum):
    GEOM = 0x4D4F4547  # MOEG
    PRIM = 0x4D495250  # MIRP
    DXVB = 0x42565844  # BXVD
    DXIB = 0x42495844  # BXID
    HASH = 0x48534148  # HSIH
    REAL = 0x4C414552  # LERE
    MTT = 0x2E54414D  # .MTA
    MATA = 0x4154414D  # MATA
    MTPA = 0x4150544D  # MTPA
    UVAA = 0x41415655  # UVAU


class TDU2TexFormat(IntEnum):
    DXT1 = 132
    DXT5 = 136
    ARGB8 = 144
    DXT1_OTHER = 196


class TDUMaterial:
    def __init__(self):
        self.name = ""
        self.diffuse = [0.7, 0.7, 0.7, 1.0]
        self.ambient = [0.2, 0.2, 0.2, 1.0]
        self.specular = [1.0, 1.0, 1.0, 1.0]
        self.emissive = [0.0, 0.0, 0.0, 0.0]
        self.diffuse_texture_bytes = None
        self.diffuse_texture_width = 0
        self.diffuse_texture_height = 0


class TDU2Mesh:
    def __init__(self):
        self.name = ""
        self.group_name = ""
        self.group_index = -1
        self.material_index = 0
        self.material_name = ""
        self.positions = []
        self.normals = []
        self.uvs = []
        self.triangles = []
        self.average_vertex_color = None


class TDU2Model:
    def __init__(self):
        self.file_version = 0
        self.some_flag = 0
        self.unk1 = 0
        self.size = 0
        self.segments = []
        self.materials = []
        self.meshes = []


class TDUTexture2DB:
    def __init__(self):
        self.file_version = 0
        self.unk1 = 0
        self.unk2 = 0
        self.size = 0
        self.id = b''
        self.id2 = b''
        self.unk3 = 0
        self.unk4 = 0
        self.some_size = 0
        self.some_other_size = 0
        self.name = b''
        self.width = 0
        self.height = 0
        self.param4 = 0
        self.param5 = 0
        self.unk5 = 0
        self.param7 = 0
        self.unk6 = 0
        self.unk7 = 0
        self.param6 = 0
        self.flags = 0
        self.unk9 = 0
        self.unk10 = 0
        self.unk11 = 0
        self.image_data = b''
    
    @property
    def Format(self):
        return self.param7
    
    @Format.setter
    def Format(self, value):
        self.param7 = value


class TDUMaterial2DM:
    def __init__(self):
        self.file_version = 0
        self.some_flag = 0
        self.unk1 = 0
        self.size = 0
        self.segments = []


class TextureLayerRef:
    def __init__(self):
        self.type_name = ""
        self.texture_name = b''


class MatFileData:
    def __init__(self):
        self.hash_name = b''
        self.name = ""
        self.ambient = [0.2, 0.2, 0.2, 1.0]
        self.diffuse = [0.7, 0.7, 0.7, 1.0]
        self.specular = [1.0, 1.0, 1.0, 1.0]
        self.emissive = [0.0, 0.0, 0.0, 0.0]
        self.texture_layers: List[TextureLayerRef] = []

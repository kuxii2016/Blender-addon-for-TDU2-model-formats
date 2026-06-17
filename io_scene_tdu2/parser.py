import struct
import math
from typing import List, Optional, Tuple
from .types import (
    TDU2Model, TDU2Mesh, TDUMaterial, TDU2ObjectType, TDU2TexFormat,
    TDUTexture2DB, TDUMaterial2DM, MatFileData, TextureLayerRef
)


def _read_u16(data: bytes, off: int) -> int:
    return struct.unpack('<H', data[off:off+2])[0]

def _read_u32(data: bytes, off: int) -> int:
    return struct.unpack('<I', data[off:off+4])[0]

def _read_u64(data: bytes, off: int) -> int:
    return struct.unpack('<Q', data[off:off+8])[0]

def _read_float(data: bytes, off: int) -> float:
    return struct.unpack('<f', data[off:off+4])[0]

def _read_s16(data: bytes, off: int) -> int:
    return struct.unpack('<h', data[off:off+2])[0]


def half_to_float(h: int) -> float:
    sign = (h >> 15) & 1
    exp = (h >> 10) & 0x1F
    mant = h & 0x3FF
    if exp == 0:
        if mant == 0:
            return 0.0
        val = mant / 1024.0
        return (1 if sign == 0 else -1) * val * math.pow(2, -14)
    if exp == 31:
        if mant == 0:
            return float('inf') if sign == 0 else float('-inf')
        return float('nan')
    norm = 1.0 + mant / 1024.0
    return (1 if sign == 0 else -1) * norm * math.pow(2, exp - 15)

def half16_vector(data: bytes, off: int) -> Tuple[float, float, float]:
    x = half_to_float(_read_u16(data, off))
    y = half_to_float(_read_u16(data, off + 2))
    z = half_to_float(_read_u16(data, off + 4))
    return (x, y, z)


class Segment3DG:
    def __init__(self, offset: int, buf: bytes, header_start: int):
        self.position = offset
        self.magic_type = _read_u32(buf, header_start)
        self.zero = _read_u32(buf, header_start + 4)
        self.seg_size = _read_u32(buf, header_start + 8)
        self.next_segment_ptr = _read_u32(buf, header_start + 12)
        end = self.next_segment_ptr if (self.next_segment_ptr > 0 and self.next_segment_ptr < self.seg_size) else self.seg_size
        data_len = max(0, int(end - 16))
        self.data = b''
        if data_len > 0 and header_start + 16 + data_len <= len(buf):
            self.data = buf[header_start + 16:header_start + 16 + data_len]
        self.children: List[Segment3DG] = []


class GenericSegment(Segment3DG):
    pass


class GEOMSegment(Segment3DG):
    pass


class PRIMSegment(Segment3DG):
    def __init__(self, offset: int, buf: bytes, header_start: int):
        super().__init__(offset, buf, header_start)
        self.offset_index = 0
        self.offset_vertex = 0
        self.offset_bone = 0
        self.offset_unk = 0
        self.unk2 = 0
        self.mat_id = 0
        self.unk3 = 0
        self.unk4 = 0
        self.n_verts = 0
        self.unk5 = 0
        self.unk6 = 0
        self.nb_indices = 0
        self.zero1 = 0
        self.zero2 = 0
        self.zero3 = 0
        self.bound_radius = 0
        self.bound_x = 0
        self.bound_y = 0
        self.bound_z = 0
        if len(self.data) >= 64:
            self.offset_index = _read_u32(self.data, 0)
            self.offset_vertex = _read_u32(self.data, 4)
            self.offset_bone = _read_u32(self.data, 8)
            self.offset_unk = _read_u32(self.data, 12)
            self.unk2 = _read_u16(self.data, 16)
            self.mat_id = _read_u16(self.data, 18)
            self.unk3 = _read_u32(self.data, 20)
            self.unk4 = _read_u32(self.data, 24)
            self.n_verts = _read_u32(self.data, 28)
            self.unk5 = _read_u32(self.data, 32)
            self.unk6 = _read_u32(self.data, 36)
            self.nb_indices = _read_u32(self.data, 40)
            self.zero1 = _read_u32(self.data, 44)
            self.zero2 = _read_u32(self.data, 48)
            self.zero3 = _read_u32(self.data, 52)
            self.bound_radius = _read_u16(self.data, 56)
            self.bound_x = _read_s16(self.data, 58)
            self.bound_y = _read_s16(self.data, 60)
            self.bound_z = _read_s16(self.data, 62)


class DXVertexBuffer(Segment3DG):
    def __init__(self, offset: int, buf: bytes, header_start: int):
        super().__init__(offset, buf, header_start)
        self.n_verts = 0
        self.positions_flag = 0
        self.normals_flag = 0
        self.color_flag = 0
        self.zero1 = 0
        self.uv = 0
        self.tangent = 0
        self.bi_normal = 0
        self.bone_indices = 0
        self.bone_weights = 0
        self.zero2 = 0
        self.zero3 = 0
        self.uv_loc = 0
        self.zero4 = 0
        self.parsed_positions: List[Tuple[float, float, float]] = []
        self.parsed_normals: List[Tuple[float, float, float]] = []
        self.parsed_uvs: List[List[Tuple[float, float]]] = []
        self.parsed_colors: List[Tuple[int, int, int, int]] = []

    def parse(self):
        if len(self.data) < 32:
            return
        self.n_verts = _read_u32(self.data, 0)
        self.positions_flag = _read_u16(self.data, 4)
        self.normals_flag = _read_u16(self.data, 6)
        self.color_flag = _read_u16(self.data, 8)
        self.zero1 = _read_u16(self.data, 10)
        self.uv = _read_u16(self.data, 12)
        self.tangent = _read_u16(self.data, 14)
        self.bi_normal = _read_u16(self.data, 16)
        self.bone_indices = _read_u16(self.data, 18)
        self.bone_weights = _read_u16(self.data, 20)
        self.zero2 = _read_u32(self.data, 22)
        self.zero3 = _read_u16(self.data, 26)
        self.uv_loc = _read_u16(self.data, 28)
        self.zero4 = _read_u16(self.data, 30)

        has_normals = (self.normals_flag & 0xFF) != 0
        has_color = (self.color_flag & 0xFF) != 0
        has_tangents = (self.tangent & 0xFF) != 0
        has_bi_normals = (self.bi_normal & 0xFF) != 0
        nb_uvs = self.uv & 0xFF
        uv_in_float_buffer = (self.uv_loc & 0xF000) != 0
        uv_in_main_buffer = (self.uv_loc & 0xF00) != 0

        float_stride = 3
        if uv_in_float_buffer:
            float_stride += nb_uvs * 2
        if (self.bone_indices & 0xFF) != 0:
            float_stride += 1
        if (self.bone_weights & 0xFF00) != 0:
            float_stride += ((self.bone_weights & 0xF00) >> 8) - 1

        main_stride = 0
        if has_normals:
            main_stride += 8
        if has_color:
            main_stride += 4
        if uv_in_main_buffer:
            main_stride += 8 * nb_uvs
        if has_tangents:
            main_stride += 8
        if has_bi_normals:
            main_stride += 8

        float_only_end = 32 + self.n_verts * float_stride * 4
        if main_stride > 0 and float_only_end + self.n_verts * main_stride > len(self.data):
            main_stride = 0

        total_stride = float_stride * 4 + main_stride
        if total_stride > 0:
            max_verts = (len(self.data) - 32) // total_stride
            if self.n_verts > max_verts:
                self.n_verts = max_verts

        self.parsed_positions.clear()
        self.parsed_normals.clear()
        self.parsed_uvs.clear()
        self.parsed_colors.clear()

        for i in range(self.n_verts):
            float_off = 32 + i * float_stride * 4
            if float_off + 12 <= len(self.data):
                px = _read_float(self.data, float_off)
                py = _read_float(self.data, float_off + 4)
                pz = _read_float(self.data, float_off + 8)
            else:
                px = py = pz = 0.0
            pos = (px, py, pz)

            uvs: List[Tuple[float, float]] = []
            if uv_in_float_buffer:
                for u in range(nb_uvs):
                    uv_off = float_off + 12 + u * 8
                    if uv_off + 8 <= len(self.data):
                        uu = _read_float(self.data, uv_off)
                        vv = _read_float(self.data, uv_off + 4)
                        uvs.append((uu, vv))
                    else:
                        uvs.append((0.0, 0.0))

            main_off = 32 + self.n_verts * float_stride * 4 + i * main_stride
            m_off = 0
            nx = ny = nz = 0.0
            if has_normals:
                if main_off + m_off + 6 <= len(self.data):
                    nx, ny, nz = half16_vector(self.data, main_off + m_off)
                m_off += 8
            normal = (nx, ny, nz)

            cr = cg = cb = ca = 0
            if has_color:
                if main_off + m_off + 4 <= len(self.data):
                    cr = self.data[main_off + m_off]
                    cg = self.data[main_off + m_off + 1]
                    cb = self.data[main_off + m_off + 2]
                    ca = self.data[main_off + m_off + 3]
                m_off += 4

            if uv_in_main_buffer:
                uvs.clear()
                for u in range(nb_uvs):
                    uv_off = main_off + m_off + u * 8
                    if uv_off + 8 <= len(self.data):
                        uu = _read_float(self.data, uv_off)
                        vv = _read_float(self.data, uv_off + 4)
                        uvs.append((uu, vv))
                    else:
                        uvs.append((0.0, 0.0))
                m_off += 8 * nb_uvs

            self.parsed_positions.append(pos)
            self.parsed_normals.append(normal)
            self.parsed_uvs.append(uvs)
            self.parsed_colors.append((cr, cg, cb, ca))

    def get_positions(self) -> List[Tuple[float, float, float]]:
        return self.parsed_positions

    def get_normals(self) -> List[Tuple[float, float, float]]:
        return self.parsed_normals

    def get_uvs(self, layer: int = 0) -> List[Tuple[float, float]]:
        result = []
        for uvs in self.parsed_uvs:
            if layer < len(uvs):
                result.append(uvs[layer])
            else:
                result.append((0.0, 0.0))
        return result


class DXIndexBuffer(Segment3DG):
    def __init__(self, offset: int, buf: bytes, header_start: int):
        super().__init__(offset, buf, header_start)
        self.nb_indices = 0
        self.n_type = 0
        self.padding = 0
        self.indices: List[int] = []

    def parse(self):
        if len(self.data) < 16:
            return
        self.nb_indices = _read_u32(self.data, 0)
        self.n_type = _read_u32(self.data, 4)
        self.padding = _read_u64(self.data, 8)
        max_indices = min(self.nb_indices, (len(self.data) - 16) // 2)
        self.indices = []
        for i in range(max_indices):
            self.indices.append(_read_u16(self.data, 16 + i * 2))

    def to_triangles(self) -> List[int]:
        faces = []
        nb = min(len(self.indices), self.nb_indices)
        for j in range(nb - 2):
            if j % 2 != 0:
                i1 = self.indices[j]
                i2 = self.indices[j + 2]
                i3 = self.indices[j + 1]
            else:
                i1 = self.indices[j]
                i2 = self.indices[j + 1]
                i3 = self.indices[j + 2]
            if i1 != i2 and i2 != i3 and i1 != i3:
                faces.append(i1)
                faces.append(i2)
                faces.append(i3)
        return faces


class HashSegment(Segment3DG):
    def __init__(self, offset: int, buf: bytes, header_start: int):
        super().__init__(offset, buf, header_start)
        self.entries: List[Tuple[bytes, int, int]] = []

    def parse(self):
        self.entries.clear()
        count = len(self.data) // 16
        for i in range(count):
            base_off = i * 16
            name = self.data[base_off:base_off + 8]
            off = _read_u32(self.data, base_off + 8)
            zero = _read_u32(self.data, base_off + 12)
            self.entries.append((name, off, zero))


class StringDemangler:
    _map: dict = {}

    @classmethod
    def _add_mapping(cls, name: str):
        key = cls._mangle(name)
        if key not in cls._map:
            cls._map[key] = name

    @staticmethod
    def _mangle(name: str) -> bytes:
        b = bytearray(8)
        bname = name.encode('ascii', errors='replace')
        for i, c in enumerate(bname):
            b[i % 8] = (b[i % 8] + c) & 0xFF
        return bytes(b)

    @staticmethod
    def _normalize_padding(name: bytes) -> bytes:
        b = bytearray(name)
        for i in range(len(b) - 1, -1, -1):
            if b[i] == 0x20:
                b[i] = 0
            else:
                break
        return bytes(b)

    @classmethod
    def demangle(cls, name: bytes) -> str:
        if all(b == 0x20 for b in name) or all(b == 0x3F for b in name):
            return ""
        if any(b == 0 for b in name):
            return name.rstrip(b'\x00').decode('ascii', errors='replace')
        if len(name) < 8:
            return name.decode('ascii', errors='replace')
        normalized = cls._normalize_padding(name)
        if normalized in cls._map:
            return cls._map[normalized]
        return "UNK_" + name.hex().upper()

    @classmethod
    def demangle_and_unknown(cls, name: bytes) -> str:
        return cls.demangle(name)


for _name in [
    "DIRTCOLOR", "DIRTCOLOR0", "DIRTCOLOR1", "DIRTCOLOR2", "DIRTCOLOR3", "DIRTCOLOR4",
    "ENVCOEFF", "FLAKEABNS", "GLOSSCLR", "GLOSSFCT", "GLOSSLIGHT", "HEATCOLOR",
    "LAYRCLR", "LAYRCLR1", "LAYRCLR2", "LAYRCLR3", "LAYRCLR4",
    "MATERIAL", "MATPARAM", "NOSCALE", "RAMPCLR1", "RAMPCLR2", "RAMPCLR3",
    "RAMPFLAKE", "RLINNCLR1", "RLINNCLR2", "SEATCOLOR", "SPECBLINN", "SPECCOEF",
    "SPECPARM", "TEXLIGHT", "DIRTSCRATCH", "REFLECTION", "REFLECTIVE", "CARBON",
    "CUBEMAP", "CUBEMAPB", "DIRT_SCRATCH", "IMPACT_MAPS", "FIO_DAMAGE", "FIO_DAMAGE_2",
    "FIO_FLAKES", "FIO_FLAKESCOOL_NORMAL_BIG",
    "LEATHER1", "LEATHER2", "LEATHER3", "MOKET2",
    "TS_LEATHER1", "TS_LEATHER2", "TS_LEATHER3", "TS_MOKET1", "TS_MOKET2",
    "USER_TEX", "WS_PLATE",
    "SRT10_Ext_Gris_01", "SRT10_Ext_Blanc_01", "SRT10_Ext_Bleu_01",
    "SRT10_Ext_Gris_02", "SRT10_Ext_Jaune_01", "SRT10_Ext_Jaune_02",
    "SRT10_Ext_Rouge_02", "SRT10_Ext_Vert_01", "SRT10_Ext_Vert_02",
    "SRT10_Int_Beige_01", "SRT10_Int_Beige_02", "SRT10_Int_Gris_01", "SRT10_Int_Gris_02",
    "SRT10_Int_Rouge_01", "SRT10_Int_Rouge_02",
    "308_GTS_Ext_Beige_01", "308_GTS_Ext_Jaune_01", "308_GTS_Ext_Bleu_01",
    "308_GTS_Ext_Bleu_02", "308_GTS_Ext_Bleu_03", "308_GTS_Ext_Blanc_01",
    "308_GTS_Ext_Gris_01", "308_GTS_Ext_Gris_02", "308_GTS_Ext_Rouge_01",
    "308_GTS_Ext_Rouge_02", "308_GTS_Ext_Marron_01", "308_GTS_Ext_Noir_01",
    "308_GTS_Ext_Vert_01", "308_GTS_Ext_Vert_02",
    "308_GTS_Int_Beige_01", "308_GTS_Int_Noir_01",
    "D_SHADOW", "D_SBOX", "EXHAUST_L", "EXHAUST_R", "EXHAUST_HL", "EXHAUST_HR",
    "EXH_FX_01", "EXH_FX_02", "EXH_FX_03",
    "BUMP_F_LR", "BUMP_R_LR", "BUMP_F_MR", "BUMP_R_MR", "BUMP_F_HR", "BUMP_R_HR",
    "DOOR_L_A_1", "DOOR_L_A_2", "DOOR_L_A_3",
    "DOOR_R_A_1", "DOOR_R_A_2", "DOOR_R_A_3",
    "DOOR_L_B_1", "DOOR_L_B_2", "DOOR_L_B_3",
    "DOOR_R_B_1", "DOOR_R_B_2", "DOOR_R_B_3",
    "DOOR_L_COL", "DOOR_R_COL",
    "BACK_LR_L", "BACK_LR_R", "BACK_HR_L", "BACK_HR_R",
    "HAND_LR_L", "HAND_LR_R", "HAND_HR_L", "HAND_HR_R",
    "FOOT_LR_L", "FOOT_LR_R", "FOOT_HR_L", "FOOT_HR_R",
    "SEAT_L_LR", "SEAT_R_LR", "SEAT_L_HR", "SEAT_R_HR",
    "HARDTOP_MR", "HARDTOP_LR", "GLASS_TOP", "GLASS_LEFT", "GLASS_RIGHT",
    "HANDLE_RL", "HANDLE_RR", "HANDLE_FL", "HANDLE_FR",
    "HANDLE_DOOR_L", "HANDLE_DOOR_R",
    "LGT_RF_GLASS", "LGT_RR_GLASS", "LGT_FL_MR", "LGT_FR_MR", "LGT_RL_MR", "LGT_RR_MR",
    "FA_B_RL_C", "FA_B_RR_C", "FA_L_FL_C", "FA_L_FR_C",
    "FA_L_FL1_C", "FA_L_FR1_C", "FA_R_RL_C", "FA_R_RR_C",
    "FA_S_RL_C", "FA_S_RR_C", "FA_S_RL1_C", "FA_S_RR1_C",
    "FA_W_FL_C", "FA_W_FR_C", "FA_W_RL_C", "FA_W_RR_C",
    "DVRSEAT_LR", "DVRSEAT_HR", "PSGSEAT_LR", "PSGSEAT_HR",
    "PSGFOOT_LR_L", "PSGFOOT_LR_R", "PSGFOOT_HR_L", "PSGFOOT_HR_R",
    "D_INT_HR_L", "D_INT_HR_R",
    "STIRRUP_FL", "STIRRUP_FR", "STIRRUP_RL", "STIRRUP_RR",
    "D_REVERSING", "D_BREAKING", "D_HEADLIGHT",
    "D_WHEEL_FL", "D_WHEEL_FR", "D_WHEEL_RL", "D_WHEEL_RR",
    "D_TIRE_FL", "D_TIRE_FR", "D_TIRE_RL", "D_TIRE_RR",
    "REVERSING", "BREAKING", "HEADLIGHT", "SCENE01"
]:
    StringDemangler._add_mapping(_name)


MAGIC_3DG = 0x4744332E
MAGIC_3DD = 0x4444332E
MAGIC_GEOM = 0x4D4F4547
MAGIC_PRIM = 0x4D495250
MAGIC_DXVB = 0x42565844
MAGIC_DXIB = 0x42495844
MAGIC_HASH = 0x48534148
MAGIC_REAL = 0x4C414552
MAGIC_MTT = 0x2E54414D


class TDU2ModelParser:
    @staticmethod
    def parse(filepath: str) -> TDU2Model:
        with open(filepath, 'rb') as f:
            buf = f.read()

        if len(buf) < 16:
            raise ValueError("File too small to be a valid TDU2 model")

        file_version = _read_u16(buf, 0)
        some_flag = _read_u16(buf, 2)
        unk1 = _read_u32(buf, 4)
        sz = _read_u32(buf, 8)
        magic = _read_u32(buf, 12)

        if magic != MAGIC_3DG and magic != MAGIC_3DD:
            raise ValueError(f"Invalid file magic: 0x{magic:X}")
        if len(buf) < sz:
            raise ValueError(f"File truncated: expected {sz} bytes, got {len(buf)}")

        model = TDU2Model()
        model.file_version = file_version
        model.some_flag = some_flag
        model.unk1 = unk1
        model.size = sz
        model.segments = []

        segment_stack: List[Tuple[List[Segment3DG], int]] = []
        current_list = model.segments

        offset = 16
        while offset < sz:
            if offset + 16 > sz:
                break
            magic_type = _read_u32(buf, offset)
            seg_size = _read_u32(buf, offset + 8)
            next_ptr = _read_u32(buf, offset + 12)

            if seg_size == 0 or offset + seg_size > sz:
                break

            seg: Segment3DG
            if magic_type == MAGIC_GEOM:
                seg = GEOMSegment(offset, buf, offset)
            elif magic_type == MAGIC_PRIM:
                seg = PRIMSegment(offset, buf, offset)
            elif magic_type == MAGIC_DXVB:
                seg = DXVertexBuffer(offset, buf, offset)
            elif magic_type == MAGIC_DXIB:
                seg = DXIndexBuffer(offset, buf, offset)
            elif magic_type == MAGIC_HASH:
                seg = HashSegment(offset, buf, offset)
            else:
                seg = GenericSegment(offset, buf, offset)

            current_list.append(seg)

            if next_ptr != 0 and next_ptr < seg_size:
                segment_stack.append((current_list, offset + seg_size))
                current_list = seg.children
                offset += next_ptr
            else:
                offset += seg_size
                while segment_stack and offset >= segment_stack[-1][1]:
                    current_list, reset_off = segment_stack.pop()
                    offset = reset_off

        model.meshes = TDU2ModelParser._extract_meshes(model, buf)
        return model

    @staticmethod
    def _extract_meshes(model: TDU2Model, buf: bytes) -> List[TDU2Mesh]:
        dxvbs: List[DXVertexBuffer] = []
        dxibs: List[DXIndexBuffer] = []
        prims: List[Tuple[PRIMSegment, int]] = []

        geom_index = 0

        def collect(seg_list: List[Segment3DG], parent_geom: int = -1):
            nonlocal geom_index
            for seg in seg_list:
                if isinstance(seg, GEOMSegment):
                    idx = geom_index
                    geom_index += 1
                    collect(seg.children, idx)
                elif isinstance(seg, PRIMSegment):
                    prims.append((seg, parent_geom if parent_geom >= 0 else -1))
                    if seg.children:
                        collect(seg.children, parent_geom)
                elif isinstance(seg, DXIndexBuffer):
                    seg.parse()
                    dxibs.append(seg)
                elif isinstance(seg, DXVertexBuffer):
                    seg.parse()
                    dxvbs.append(seg)
                elif seg.children:
                    collect(seg.children, parent_geom)

        collect(model.segments)

        hash_geom_names: List[str] = []

        def collect_hash_names(seg_list: List[Segment3DG]):
            for seg in seg_list:
                if isinstance(seg, HashSegment):
                    seg.parse()
                    for name_bytes, _, _ in seg.entries:
                        name = StringDemangler.demangle_and_unknown(name_bytes)
                        hash_geom_names.append(name)
                if seg.children:
                    collect_hash_names(seg.children)

        collect_hash_names(model.segments)

        materials: List[TDUMaterial] = []

        def collect_real_data(seg_list: List[Segment3DG]):
            for seg in seg_list:
                if isinstance(seg, GenericSegment) and seg.magic_type == MAGIC_REAL:
                    data_len = len(seg.data)
                    if data_len >= 16:
                        count = data_len // 16
                        for i in range(count):
                            off = i * 16
                            r = _read_float(seg.data, off)
                            g = _read_float(seg.data, off + 4)
                            b = _read_float(seg.data, off + 8)
                            a = _read_float(seg.data, off + 12)
                            mat = TDUMaterial()
                            mat.diffuse = [r, g, b, a]
                            mat.ambient = [r * 0.3, g * 0.3, b * 0.3, a]
                            mat.specular = [1.0, 1.0, 1.0, 1.0]
                            mat.emissive = [0.0, 0.0, 0.0, 0.0]
                            materials.append(mat)
                if seg.children:
                    collect_real_data(seg.children)

        collect_real_data(model.segments)
        model.materials = materials

        def get_group_name(gi: int) -> str:
            if 0 <= gi < len(hash_geom_names) and hash_geom_names[gi]:
                return hash_geom_names[gi]
            return f"Group_{gi}"

        result: List[TDU2Mesh] = []
        for prim, gi in prims:
            vb = None
            for v in dxvbs:
                if v.position == prim.offset_vertex:
                    vb = v
                    break
            if vb is None:
                continue

            pos = vb.get_positions()
            norms = vb.get_normals()
            uvs = vb.get_uvs(0)
            tris: List[int] = []

            ib = None
            for i in dxibs:
                if i.position == prim.offset_index:
                    ib = i
                    break

            if ib is not None:
                tris = ib.to_triangles()
            else:
                side = int(math.isqrt(len(pos)))
                if side * side == len(pos) and len(pos) >= 4:
                    actual_cols = side * 3
                    actual_rows = side
                    expanded_count = actual_rows * actual_cols

                    expanded_pos = [(0.0, 0.0, 0.0)] * expanded_count
                    for i in range(len(pos)):
                        row = i // side
                        col_base = (i % side) * 3
                        px, py, pz = pos[i]
                        expanded_pos[row * actual_cols + col_base] = (col_base * 7680.0 / (actual_cols - 1), px, row * 7680.0 / (actual_rows - 1))
                        expanded_pos[row * actual_cols + col_base + 1] = ((col_base + 1) * 7680.0 / (actual_cols - 1), py, row * 7680.0 / (actual_rows - 1))
                        expanded_pos[row * actual_cols + col_base + 2] = ((col_base + 2) * 7680.0 / (actual_cols - 1), pz, row * 7680.0 / (actual_rows - 1))
                    pos = expanded_pos

                    face_list = []
                    for r in range(actual_rows - 1):
                        for c in range(actual_cols - 1):
                            tl = r * actual_cols + c
                            tr = r * actual_cols + c + 1
                            bl = (r + 1) * actual_cols + c
                            br = (r + 1) * actual_cols + c + 1
                            face_list.append(tl)
                            face_list.append(bl)
                            face_list.append(tr)
                            face_list.append(tr)
                            face_list.append(bl)
                            face_list.append(br)
                    tris = face_list

                    norms = [(0.0, 0.0, 0.0)] * expanded_count
                    uvs = [(0.0, 0.0)] * expanded_count
                    for ti in range(0, len(tris), 3):
                        i0, i1, i2 = tris[ti], tris[ti + 1], tris[ti + 2]
                        e1 = (pos[i1][0] - pos[i0][0], pos[i1][1] - pos[i0][1], pos[i1][2] - pos[i0][2])
                        e2 = (pos[i2][0] - pos[i0][0], pos[i2][1] - pos[i0][1], pos[i2][2] - pos[i0][2])
                        fnx = e1[1] * e2[2] - e1[2] * e2[1]
                        fny = e1[2] * e2[0] - e1[0] * e2[2]
                        fnz = e1[0] * e2[1] - e1[1] * e2[0]
                        flen = math.sqrt(fnx*fnx + fny*fny + fnz*fnz)
                        if flen > 0:
                            fnx /= flen
                            fny /= flen
                            fnz /= flen
                        n0, n1, n2 = norms[i0], norms[i1], norms[i2]
                        norms[i0] = (n0[0] + fnx, n0[1] + fny, n0[2] + fnz)
                        norms[i1] = (n1[0] + fnx, n1[1] + fny, n1[2] + fnz)
                        norms[i2] = (n2[0] + fnx, n2[1] + fny, n2[2] + fnz)
                    for i in range(len(norms)):
                        nx, ny, nz = norms[i]
                        nl = math.sqrt(nx*nx + ny*ny + nz*nz)
                        if nl > 0:
                            norms[i] = (nx/nl, ny/nl, nz/nl)

                    min_x = min(p[0] for p in pos)
                    max_x = max(p[0] for p in pos)
                    min_z = min(p[2] for p in pos)
                    max_z = max(p[2] for p in pos)
                    rx = max_x - min_x
                    rz = max_z - min_z
                    for i in range(len(pos)):
                        uvs[i] = ((pos[i][0] - min_x) / rx if rx > 0 else 0,
                                   (pos[i][2] - min_z) / rz if rz > 0 else 0)
                else:
                    continue

            pos_flat = []
            norm_flat = []
            uv_flat = []
            for i in range(len(pos)):
                pos_flat.extend(pos[i])
            for i in range(len(norms)):
                norm_flat.extend(norms[i])
            for i in range(len(uvs)):
                uv_flat.extend(uvs[i])

            group_name = get_group_name(gi)
            mat_name = f"Mat_{prim.mat_id}" if prim.mat_id < len(materials) else ""

            avg_color = None
            if vb.parsed_colors:
                sr = sg = sb = sa = 0
                for cr, cg, cb, ca in vb.parsed_colors:
                    sr += cr / 255.0
                    sg += cg / 255.0
                    sb += cb / 255.0
                    sa += ca / 255.0
                cnt = len(vb.parsed_colors)
                avg_color = [sr / cnt, sg / cnt, sb / cnt, sa / cnt]

            mesh = TDU2Mesh()
            mesh.name = f"{group_name}_{len(result)}"
            mesh.group_name = group_name
            mesh.group_index = gi
            mesh.material_index = prim.mat_id
            mesh.material_name = mat_name
            mesh.positions = pos_flat
            mesh.normals = norm_flat
            mesh.uvs = uv_flat
            mesh.triangles = tris
            mesh.average_vertex_color = avg_color
            result.append(mesh)

        return result


class TDUSegment:
    def __init__(self, position: int, magic_type: int, zero: int,
                 size: int, next_segment_ptr: int, data: bytes):
        self.position = position
        self.magic_type = magic_type
        self.zero = zero
        self.size = size
        self.next_segment_ptr = next_segment_ptr
        self.data = data
        self.children = []


class TDU2TextureParser:
    @staticmethod
    def parse(filepath: str) -> TDUTexture2DB:
        with open(filepath, 'rb') as f:
            data = f.read()

        texture = TDUTexture2DB()
        TDU2TextureParser._parse_texture(data, texture)
        return texture

    @staticmethod
    def _parse_texture(data: bytes, texture: TDUTexture2DB):
        if len(data) < 80:
            raise ValueError("File too small to be a valid TDU2 texture")

        texture.file_version = _read_u16(data, 0)
        texture.unk1 = _read_u16(data, 2)
        texture.unk2 = _read_u32(data, 4)
        texture.size = _read_u32(data, 8)
        texture.id = data[12:16]
        texture.id2 = data[16:20]
        texture.unk3 = _read_u16(data, 20)
        texture.unk4 = _read_u16(data, 22)
        texture.some_size = _read_u32(data, 24)
        texture.some_other_size = _read_u32(data, 28)

        name_bytes = data[32:40]
        texture.name = name_bytes

        texture.width = _read_u16(data, 40)
        texture.height = _read_u16(data, 42)
        texture.param4 = _read_u16(data, 44)
        texture.param5 = data[46]
        texture.unk5 = data[47]
        texture.param7 = _read_u32(data, 48)
        texture.unk6 = _read_u32(data, 52)
        texture.unk7 = _read_u32(data, 56)
        texture.param6 = _read_u32(data, 60)
        texture.flags = _read_u32(data, 64)
        texture.unk9 = _read_u32(data, 68)
        texture.unk10 = _read_u32(data, 72)
        texture.unk11 = _read_u32(data, 76)

        image_len = texture.size - 80
        if image_len > 0 and len(data) >= 80 + image_len:
            texture.image_data = data[80:80 + image_len]

    @staticmethod
    def parse_from_bytes(data: bytes) -> TDUTexture2DB:
        texture = TDUTexture2DB()
        TDU2TextureParser._parse_texture(data, texture)
        return texture


class TDU2MaterialParser:
    @staticmethod
    def parse(filepath: str) -> TDUMaterial2DM:
        with open(filepath, 'rb') as f:
            data = f.read()

        material2d = TDUMaterial2DM()
        TDU2MaterialParser._parse_header(data, material2d)
        TDU2MaterialParser._parse_segments(data, material2d)
        return material2d

    @staticmethod
    def _parse_header(data: bytes, material2d: TDUMaterial2DM):
        if len(data) < 16:
            raise ValueError("File too small to be a valid TDU2 material")

        material2d.file_version = _read_u16(data, 0)
        material2d.some_flag = _read_u16(data, 2)
        material2d.unk1 = _read_u32(data, 4)
        material2d.size = _read_u32(data, 8)

        magic = _read_u32(data, 12)
        if magic != 0x4D44322E:
            raise ValueError(f"Invalid file magic: 0x{magic:X}")

    @staticmethod
    def _parse_segments(data: bytes, material2d: TDUMaterial2DM):
        offset = 16
        while offset < len(data) and offset < material2d.size:
            if offset + 16 > len(data):
                break
            magic = _read_u32(data, offset)
            zero = _read_u32(data, offset + 4)
            seg_size = _read_u32(data, offset + 8)
            next_ptr = _read_u32(data, offset + 12)

            if seg_size == 0 or offset + seg_size > len(data):
                break
            seg_data = data[offset + 16:offset + seg_size]

            model_segment = TDUModelSegment(
                position=offset,
                magic_type=magic,
                zero=zero,
                size=seg_size,
                next_segment_ptr=next_ptr,
                data=seg_data
            )
            material2d.segments.append(model_segment)
            offset += seg_size

    @staticmethod
    def parse_to_materials(filepath: str) -> List[MatFileData]:
        with open(filepath, 'rb') as f:
            buf = f.read()

        if len(buf) < 16:
            raise ValueError("File too small")

        sz = _read_u32(buf, 8)
        magic = _read_u32(buf, 12)
        if magic != 0x4D44322E:
            raise ValueError(f"Invalid .2DM magic: 0x{magic:X}")

        class _SegNode:
            def __init__(self, off, magic_type, size, next_ptr):
                self.off = off
                self.magic_type = magic_type
                self.size = size
                self.next_ptr = next_ptr
                end = next_ptr if (next_ptr > 0 and next_ptr < size) else size
                data_len = max(0, end - 16)
                self.data = b''
                if data_len > 0 and off + 16 + data_len <= len(buf):
                    self.data = buf[off + 16:off + 16 + data_len]
                self.children = []

        stack = []
        current_list: list = []
        root_list = current_list
        offset = 16
        while offset < sz:
            if offset + 16 > sz:
                break
            mt = _read_u32(buf, offset)
            size = _read_u32(buf, offset + 8)
            nptr = _read_u32(buf, offset + 12)
            if size == 0 or offset + size > sz:
                break
            node = _SegNode(offset, mt, size, nptr)
            current_list.append(node)

            if mt == 0x4154414D:
                stack.append((current_list, offset + size))
                current_list = node.children
                offset += nptr
            else:
                offset += size
                while stack and offset >= stack[-1][1]:
                    current_list, _ = stack.pop()

        def find_all_mat(nodes):
            results = []
            for n in nodes:
                if n.magic_type == 0x2E54414D or n.magic_type == 0x004D544D:
                    results.append(n)
                results.extend(find_all_mat(n.children))
            return results

        mat_nodes = find_all_mat(root_list)

        result = []
        for node in mat_nodes:
            d = node.data
            if len(d) < 256:
                continue
            m = MatFileData()
            m.hash_name = d[0:8]
            m.name = d[16:48].decode('ascii', errors='replace').rstrip('\x00')
            m.ambient = [_read_float(d, 176), _read_float(d, 180), _read_float(d, 184), _read_float(d, 188)]
            m.diffuse = [_read_float(d, 192), _read_float(d, 196), _read_float(d, 200), _read_float(d, 204)]
            m.specular = [_read_float(d, 208), _read_float(d, 212), _read_float(d, 216), _read_float(d, 220)]
            m.emissive = [_read_float(d, 224), _read_float(d, 228), _read_float(d, 232), _read_float(d, 236)]
            nb_layers = _read_u16(d, 252) if len(d) >= 254 else 0
            for li in range(min(nb_layers, 16)):
                lo = 256 + li * 32
                if lo + 32 > len(d):
                    break
                tlr = TextureLayerRef()
                raw = d[lo:lo+8]
                try:
                    tlr.type_name = raw.decode('ascii').rstrip('\x00')
                except UnicodeDecodeError:
                    tlr.type_name = StringDemangler.demangle_and_unknown(raw)
                tlr.texture_name = d[lo+8:lo+16]
                m.texture_layers.append(tlr)
            result.append(m)

        return result


class TDUModelSegment:
    def __init__(self, position: int, magic_type: int, zero: int,
                 size: int, next_segment_ptr: int, data: bytes):
        self.position = position
        self.magic_type = magic_type
        self.zero = zero
        self.size = size
        self.next_segment_ptr = next_segment_ptr
        self.data = data
        self.child_segments = []


class BinaryWriter:
    def __init__(self, stream):
        self.stream = stream

    def write(self, data):
        if isinstance(data, bytes):
            self.stream.write(data)
        elif isinstance(data, bytearray):
            self.stream.write(data)
        else:
            self.stream.write(struct.pack('<H', data) if isinstance(data, int) and data < 65536 else
                            struct.pack('<I', data) if isinstance(data, int) and data < 4294967296 else
                            data)


class TDU2ModelWriter:
    @staticmethod
    def write(filepath: str, model: TDU2Model):
        with open(filepath, 'wb') as f:
            writer = BinaryWriter(f)
            TDU2ModelWriter._write_header(writer, model)
            TDU2ModelWriter._write_segments(writer, model)
            TDU2ModelWriter._write_materials(writer, model)

    @staticmethod
    def _write_header(writer: BinaryWriter, model: TDU2Model):
        writer.write(struct.pack('<H', model.file_version))
        writer.write(struct.pack('<H', model.some_flag))
        writer.write(struct.pack('<I', model.unk1))
        writer.write(struct.pack('<I', model.size))
        writer.write(struct.pack('<I', 0x4744332E))

    @staticmethod
    def _write_segments(writer: BinaryWriter, model: TDU2Model):
        pass

    @staticmethod
    def _write_materials(writer: BinaryWriter, model: TDU2Model):
        pass

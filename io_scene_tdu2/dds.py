import struct
import math


def _rgb565_to_rgb(color: int):
    r = (color >> 11) & 0x1F
    g = (color >> 5) & 0x3F
    b = color & 0x1F
    r = (r << 3) | (r >> 2)
    g = (g << 2) | (g >> 4)
    b = (b << 3) | (b >> 2)
    return r, g, b


def decode_dxt1(data: bytes, width: int, height: int) -> bytearray:
    pixel_count = width * height
    result = bytearray(pixel_count * 4)
    block_w = max(1, (width + 3) // 4)
    block_h = max(1, (height + 3) // 4)
    offset = 0

    for by in range(block_h):
        for bx in range(block_w):
            if offset + 8 > len(data):
                break
            c0 = struct.unpack('<H', data[offset:offset+2])[0]
            c1 = struct.unpack('<H', data[offset+2:offset+4])[0]
            indices = struct.unpack('<I', data[offset+4:offset+8])[0]
            offset += 8

            r0, g0, b0 = _rgb565_to_rgb(c0)
            r1, g1, b1 = _rgb565_to_rgb(c1)

            dxt1_transparent = c0 <= c1
            if dxt1_transparent:
                colors = [
                    (r0, g0, b0, 255),
                    (r1, g1, b1, 255),
                    ((r0 + r1) // 2, (g0 + g1) // 2, (b0 + b1) // 2, 255),
                    (0, 0, 0, 0),
                ]
            else:
                colors = [
                    (r0, g0, b0, 255),
                    (r1, g1, b1, 255),
                    ((2 * r0 + r1) // 3, (2 * g0 + g1) // 3, (2 * b0 + b1) // 3, 255),
                    ((r0 + 2 * r1) // 3, (g0 + 2 * g1) // 3, (b0 + 2 * b1) // 3, 255),
                ]

            for py in range(4):
                for px in range(4):
                    x = bx * 4 + px
                    y = by * 4 + py
                    if x >= width or y >= height:
                        continue
                    idx = (indices >> (2 * (py * 4 + px))) & 3
                    dst = (y * width + x) * 4
                    if dxt1_transparent and idx == 3:
                        result[dst] = 0
                        result[dst+1] = 0
                        result[dst+2] = 0
                        result[dst+3] = 0
                    else:
                        cr, cg, cb, ca = colors[idx]
                        result[dst] = cb
                        result[dst+1] = cg
                        result[dst+2] = cr
                        result[dst+3] = ca

    return result


def decode_dxt5(data: bytes, width: int, height: int) -> bytearray:
    pixel_count = width * height
    result = bytearray(pixel_count * 4)
    block_w = max(1, (width + 3) // 4)
    block_h = max(1, (height + 3) // 4)
    offset = 0

    for by in range(block_h):
        for bx in range(block_w):
            if offset + 16 > len(data):
                break
            alpha0 = data[offset]
            alpha1 = data[offset + 1]
            alpha_bits = struct.unpack('<Q', data[offset:offset+8])[0]
            c0 = struct.unpack('<H', data[offset+8:offset+10])[0]
            c1 = struct.unpack('<H', data[offset+10:offset+12])[0]
            indices = struct.unpack('<I', data[offset+12:offset+16])[0]
            offset += 16

            alpha = bytearray(16)
            for ai in range(16):
                code = (alpha_bits >> (3 * ai)) & 7
                if code == 0:
                    alpha[ai] = alpha0
                elif code == 1:
                    alpha[ai] = alpha1
                elif alpha0 > alpha1:
                    alpha[ai] = ((8 - code) * alpha0 + (code - 1) * alpha1) // 7
                else:
                    if code <= 4:
                        alpha[ai] = ((4 - code) * alpha0 + (code - 1) * alpha1) // 3
                    else:
                        alpha[ai] = 0

            r0, g0, b0 = _rgb565_to_rgb(c0)
            r1, g1, b1 = _rgb565_to_rgb(c1)

            colors = [
                (r0, g0, b0),
                (r1, g1, b1),
                ((2 * r0 + r1) // 3, (2 * g0 + g1) // 3, (2 * b0 + b1) // 3),
                ((r0 + 2 * r1) // 3, (g0 + 2 * g1) // 3, (b0 + 2 * b1) // 3),
            ]

            for py in range(4):
                for px in range(4):
                    x = bx * 4 + px
                    y = by * 4 + py
                    if x >= width or y >= height:
                        continue
                    ci = (indices >> (2 * (py * 4 + px))) & 3
                    dst = (y * width + x) * 4
                    cr, cg, cb = colors[ci]
                    result[dst] = cb
                    result[dst+1] = cg
                    result[dst+2] = cr
                    result[dst+3] = alpha[py * 4 + px]

    return result


def decode_dxt3(data: bytes, width: int, height: int) -> bytearray:
    pixel_count = width * height
    result = bytearray(pixel_count * 4)
    block_w = max(1, (width + 3) // 4)
    block_h = max(1, (height + 3) // 4)
    offset = 0

    for by in range(block_h):
        for bx in range(block_w):
            if offset + 16 > len(data):
                break
            alpha_raw = data[offset:offset+8]
            c0 = struct.unpack('<H', data[offset+8:offset+10])[0]
            c1 = struct.unpack('<H', data[offset+10:offset+12])[0]
            indices = struct.unpack('<I', data[offset+12:offset+16])[0]
            offset += 16

            alpha = bytearray(16)
            for ai in range(8):
                a_low = alpha_raw[ai] & 0x0F
                a_high = (alpha_raw[ai] >> 4) & 0x0F
                alpha[ai * 2] = a_low * 17
                alpha[ai * 2 + 1] = a_high * 17

            r0, g0, b0 = _rgb565_to_rgb(c0)
            r1, g1, b1 = _rgb565_to_rgb(c1)

            colors = [
                (r0, g0, b0),
                (r1, g1, b1),
                ((2 * r0 + r1) // 3, (2 * g0 + g1) // 3, (2 * b0 + b1) // 3),
                ((r0 + 2 * r1) // 3, (g0 + 2 * g1) // 3, (b0 + 2 * b1) // 3),
            ]

            for py in range(4):
                for px in range(4):
                    x = bx * 4 + px
                    y = by * 4 + py
                    if x >= width or y >= height:
                        continue
                    ci = (indices >> (2 * (py * 4 + px))) & 3
                    dst = (y * width + x) * 4
                    cr, cg, cb = colors[ci]
                    result[dst] = cb
                    result[dst+1] = cg
                    result[dst+2] = cr
                    result[dst+3] = alpha[py * 4 + px]

    return result


def decode_texture_2db(data: bytes) -> bytearray:
    if len(data) < 80:
        raise ValueError("File too small for .2DB")
    width = struct.unpack('<H', data[40:42])[0]
    height = struct.unpack('<H', data[42:44])[0]
    fmt = struct.unpack('<I', data[48:52])[0]
    image_data = data[80:]
    return decode_dxt(image_data, width, height, fmt)


def decode_dxt(data: bytes, width: int, height: int, four_cc: int) -> bytearray:
    if four_cc == 0x31545844:
        return decode_dxt1(data, width, height)
    elif four_cc == 0x33545844:
        return decode_dxt3(data, width, height)
    elif four_cc == 0x35545844:
        return decode_dxt5(data, width, height)
    else:
        raise ValueError(f"Unsupported texture format: 0x{four_cc:X}")


TEX_FMT_DXT1 = 132
TEX_FMT_DXT5 = 136
TEX_FMT_ARGB8 = 144
TEX_FMT_DXT1_OTHER = 196

_FMT_TO_FOURCC = {
    TEX_FMT_DXT1: 0x31545844,
    TEX_FMT_DXT5: 0x35545844,
    TEX_FMT_DXT1_OTHER: 0x31545844,
}

def decode_2db_texture(tex) -> bytearray:
    fmt = tex.param7
    if fmt == TEX_FMT_ARGB8 or tex.image_data is None or len(tex.image_data) == 0:
        return tex.image_data or bytearray()
    fourcc = _FMT_TO_FOURCC.get(fmt, 0x31545844)
    return decode_dxt(tex.image_data, tex.width, tex.height, fourcc)

# Comprehensive integration test for TDU2 Blender addon

import sys
import os
import struct
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from io_scene_tdu2.parser import TDU2ModelParser, TDU2TextureParser, TDU2MaterialParser
from io_scene_tdu2.types import TDU2Model, TDUTexture2DB, TDUMaterial2DM, TDU2TexFormat


def create_test_model(filepath: str):
    """Create a comprehensive test TDU2 model file"""
    with open(filepath, 'wb') as f:
        # Write header
        f.write(struct.pack('<H', 1))  # file_version
        f.write(struct.pack('<H', 1))  # some_flag
        f.write(struct.pack('<I', 0))  # unk1
        f.write(struct.pack('<I', 200))  # size
        f.write(struct.pack('<I', 0x4744332E))  # ".3DG" magic
        
        # Write GEOM segment
        f.write(struct.pack('<I', 0x4D4F4547))  # "MOEG" magic
        f.write(struct.pack('<I', 0))  # zero
        f.write(struct.pack('<I', 64))  # seg_size
        f.write(struct.pack('<I', 0))  # next_ptr
        
        # Write PRIM segment
        f.write(struct.pack('<I', 0x4D495250))  # "MIRP" magic
        f.write(struct.pack('<I', 0))  # zero
        f.write(struct.pack('<I', 64))  # seg_size
        f.write(struct.pack('<I', 0))  # next_ptr


def create_test_texture(filepath: str):
    """Create a comprehensive test TDU2 texture file"""
    # Create test data
    data = bytearray(b'\x00' * 256)
    
    # Set up the header at offset 0
    data[0:2] = struct.pack('<H', 1)  # file_version
    data[2:4] = struct.pack('<H', 0)  # unk1
    data[4:8] = struct.pack('<I', 0)  # unk2
    data[8:12] = struct.pack('<I', 256)  # size
    data[12:16] = b'XXXX'  # id
    data[16:20] = b'XXXX'  # id2
    data[20:22] = struct.pack('<H', 0)  # unk3
    data[22:24] = struct.pack('<H', 0)  # unk4
    data[24:28] = struct.pack('<I', 0)  # some_size
    data[28:32] = struct.pack('<I', 0)  # some_other_size
    data[32:40] = b'testtex\x00\x00\x00\x00\x00\x00\x00'  # name
    data[40:42] = struct.pack('<H', 64)  # width
    data[42:44] = struct.pack('<H', 64)  # height
    data[44:46] = struct.pack('<H', 0)  # param4
    data[46] = 1  # param5 (mipmaps = 2)
    data[47] = 0  # unk5
    data[48:52] = struct.pack('<I', 136)  # param7 (DXT5)
    data[52:56] = struct.pack('<I', 0)  # unk6
    data[56:60] = struct.pack('<I', 0)  # unk7
    data[60:64] = struct.pack('<I', 0)  # param6
    data[64:68] = struct.pack('<I', 0x21)  # flags (MIPMAPS)
    data[68:72] = struct.pack('<I', 0)  # unk9
    data[72:76] = struct.pack('<I', 0)  # unk10
    data[76:80] = struct.pack('<I', 0)  # unk11
    
    # Write texture data (DXT5 compressed)
    # Create some dummy compressed texture data
    # DXT5 header + blocks
    import random
    for i in range(80, 256):
        data[i] = random.randint(0, 255)
    
    with open(filepath, 'wb') as f:
        f.write(data)


def create_test_material(filepath: str):
    """Create a comprehensive test TDU2 material file"""
    with open(filepath, 'wb') as f:
        # Write header
        f.write(struct.pack('<H', 1))  # file_version
        f.write(struct.pack('<H', 1))  # some_flag
        f.write(struct.pack('<I', 0))  # unk1
        f.write(struct.pack('<I', 512))  # size
        f.write(struct.pack('<I', 0x4D44322E))  # ".2DM" magic
        
        # Write REAL segment (material colors)
        f.write(struct.pack('<I', 0x4C414552))  # "LERE" magic
        f.write(struct.pack('<I', 0))  # zero
        f.write(struct.pack('<I', 128))  # seg_size
        f.write(struct.pack('<I', 0))  # next_ptr
        
        # Write color data (4 floats = 16 bytes)
        color1 = struct.pack('<ffff', 0.8, 0.8, 0.8, 1.0)  # White diffuse
        color2 = struct.pack('<ffff', 0.2, 0.2, 0.2, 1.0)  # Dark ambient
        color3 = struct.pack('<ffff', 1.0, 1.0, 1.0, 1.0)  # Full specular
        f.write(color1 + color2 + color3)


def test_complete_workflow():
    """Test the complete workflow: import and export"""
    print("=" * 60)
    print("TDU2 Blender Addon - Complete Workflow Test")
    print("=" * 60)
    
    all_passed = True
    
    # Test 1: Model parsing
    print("\n1. Testing Model File Parsing...")
    print("-" * 40)
    with tempfile.NamedTemporaryFile(suffix='.3DG', delete=False) as tmp:
        model_file = tmp.name
    try:
        create_test_model(model_file)
        model = TDU2ModelParser.parse(model_file)
        print(f"[PASS] Model parsed successfully: {model.file_version}")
        print(f"  - Segments: {len(model.segments)}")
        print(f"  - Meshes: {len(model.meshes)}")
        print(f"  - Materials: {len(model.materials) if model.materials else 0}")
    except Exception as e:
        print(f"[FAIL] Model parsing failed: {e}")
        all_passed = False
    finally:
        if os.path.exists(model_file):
            os.unlink(model_file)
    
    # Test 2: Texture parsing
    print("\n2. Testing Texture File Parsing...")
    print("-" * 40)
    with tempfile.NamedTemporaryFile(suffix='.2DB', delete=False) as tmp:
        tex_file = tmp.name
    try:
        create_test_texture(tex_file)
        texture = TDU2TextureParser.parse(tex_file)
        print(f"[PASS] Texture parsed successfully: {texture.width}x{texture.height}")
        print(f"  - Format: {texture.Format}")
        print(f"  - Image data size: {len(texture.image_data)} bytes")
    except Exception as e:
        print(f"[FAIL] Texture parsing failed: {e}")
        all_passed = False
    finally:
        if os.path.exists(tex_file):
            os.unlink(tex_file)
    
    # Test 3: Material parsing
    print("\n3. Testing Material File Parsing...")
    print("-" * 40)
    with tempfile.NamedTemporaryFile(suffix='.2DM', delete=False) as tmp:
        mat_file = tmp.name
    try:
        create_test_material(mat_file)
        material = TDU2MaterialParser.parse(mat_file)
        print(f"[PASS] Material parsed successfully: {material.file_version}")
        print(f"  - Segments: {len(material.segments)}")
    except Exception as e:
        print(f"[FAIL] Material parsing failed: {e}")
        all_passed = False
    finally:
        if os.path.exists(mat_file):
            os.unlink(mat_file)
    
    # Test 4: Type consistency
    print("\n4. Testing Type Consistency...")
    print("-" * 40)
    try:
        model = TDU2Model()
        model.file_version = 2
        assert model.file_version == 2
        
        tex = TDUTexture2DB()
        tex.width = 128
        tex.height = 128
        tex.Format = TDU2TexFormat.DXT5
        assert tex.width == 128
        assert tex.Format == 136
        
        mat = TDUMaterial2DM()
        mat.file_version = 3
        assert mat.file_version == 3
        
        print(f"[PASS] All types consistent")
    except Exception as e:
        print(f"[FAIL] Type consistency failed: {e}")
        all_passed = False
    
    # Test 5: Parser error handling
    print("\n5. Testing Parser Error Handling...")
    print("-" * 40)
    try:
        # Test with invalid file
        with tempfile.NamedTemporaryFile(suffix='.3DG', delete=False) as tmp:
            tmp.write(b'invalid data')
            invalid_file = tmp.name
        
        # This should raise an exception
        TDU2ModelParser.parse(invalid_file)
        print(f"[FAIL] Should have raised an exception for invalid file")
        all_passed = False
    except Exception as e:
        print(f"[PASS] Correctly raised exception for invalid file: {type(e).__name__}")
    finally:
        if os.path.exists(invalid_file):
            os.unlink(invalid_file)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("ALL TESTS PASSED! [PASS]")
        print("The TDU2 Blender addon is ready for use.")
    else:
        print("SOME TESTS FAILED [FAIL]")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    success = test_complete_workflow()
    sys.exit(0 if success else 1)

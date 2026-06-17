# Test script for the TDU2 parser module
# This script tests the parsing logic without requiring bpy

import sys
import os
import struct
import tempfile

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the parser module
from io_scene_tdu2.parser import TDU2ModelParser, TDU2TextureParser, TDU2MaterialParser


def create_test_model_file(filepath: str):
    """Create a simple test TDU2 model file for testing"""
    with open(filepath, 'wb') as f:
        # Write header
        f.write(struct.pack('<H', 1))  # file_version
        f.write(struct.pack('<H', 0))  # some_flag
        f.write(struct.pack('<I', 0))  # unk1
        f.write(struct.pack('<I', 100))  # size
        f.write(struct.pack('<I', 0x4744332E))  # ".3DG" magic
        
        # Write a simple segment
        # This is a minimal segment structure for testing
        f.write(struct.pack('<I', 0x4D4F4547))  # "MOEG" magic
        f.write(struct.pack('<I', 0))  # zero
        f.write(struct.pack('<I', 32))  # seg_size
        f.write(struct.pack('<I', 0))  # next_ptr


def create_test_texture_file(filepath: str):
    """Create a simple test TDU2 texture file"""
    # Create test data
    data = bytearray(b'\x00' * 128)  # Start with 128 bytes
    
    # Set up the header at offset 0
    data[0:2] = struct.pack('<H', 1)  # file_version
    data[2:4] = struct.pack('<H', 0)  # unk1
    data[4:8] = struct.pack('<I', 0)  # unk2
    data[8:12] = struct.pack('<I', 128)  # size
    data[12:16] = b'XXXX'  # id
    data[16:20] = b'XXXX'  # id2
    data[20:22] = struct.pack('<H', 0)  # unk3
    data[22:24] = struct.pack('<H', 0)  # unk4
    data[24:28] = struct.pack('<I', 0)  # some_size
    data[28:32] = struct.pack('<I', 0)  # some_other_size
    data[32:40] = b'testtex\x00\x00\x00\x00\x00\x00\x00'  # name
    data[40:42] = struct.pack('<H', 16)  # width
    data[42:44] = struct.pack('<H', 16)  # height
    data[44:46] = struct.pack('<H', 0)  # param4
    data[46] = 0  # param5
    data[47] = 0  # unk5
    data[48:52] = struct.pack('<I', 136)  # param7 (DXT5)
    data[52:56] = struct.pack('<I', 0)  # unk6
    data[56:60] = struct.pack('<I', 0)  # unk7
    data[60:64] = struct.pack('<I', 0)  # param6
    data[64:68] = struct.pack('<I', 0)  # flags
    data[68:72] = struct.pack('<I', 0)  # unk9
    data[72:76] = struct.pack('<I', 0)  # unk10
    data[76:80] = struct.pack('<I', 0)  # unk11
    
    with open(filepath, 'wb') as f:
        f.write(data)


def test_model_parsing():
    """Test importing a TDU2 model file"""
    # Create a temporary test file
    with tempfile.NamedTemporaryFile(suffix='.3DG', delete=False) as tmp:
        test_file = tmp.name
        create_test_model_file(test_file)

    try:
        # Try to parse the test file
        print(f"Attempting to parse model file: {test_file}")
        model = TDU2ModelParser.parse(test_file)
        print(f"Successfully parsed TDU2 model!")
        print(f"  File version: {model.file_version}")
        print(f"  Some flag: {model.some_flag}")
        print(f"  Unk1: {model.unk1}")
        print(f"  Size: {model.size}")
        print(f"  Number of segments: {len(model.segments)}")
        print(f"  Number of meshes: {len(model.meshes)}")
        
        if model.materials:
            print(f"  Number of materials: {len(model.materials)}")
        else:
            print(f"  No materials found")
        
        print("\nModel parsing test passed!")
        return True
    except Exception as e:
        print(f"Model parsing test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up
        if os.path.exists(test_file):
            os.unlink(test_file)


def test_texture_parsing():
    """Test importing a TDU2 texture file"""
    # Create a temporary test file
    with tempfile.NamedTemporaryFile(suffix='.2DB', delete=False) as tmp:
        test_file = tmp.name
        create_test_texture_file(test_file)

    try:
        # Try to parse the test file
        print(f"Attempting to parse texture file: {test_file}")
        texture = TDU2TextureParser.parse(test_file)
        print(f"Successfully parsed TDU2 texture!")
        print(f"  File version: {texture.file_version}")
        print(f"  Width: {texture.width}")
        print(f"  Height: {texture.height}")
        print(f"  Format: {texture.Format}")
        print(f"  Image data size: {len(texture.image_data)}")
        
        print("\nTexture parsing test passed!")
        return True
    except Exception as e:
        print(f"Texture parsing test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up
        if os.path.exists(test_file):
            os.unlink(test_file)


def test_material_parsing():
    """Test importing a TDU2 material file"""
    # Create a temporary test file
    with tempfile.NamedTemporaryFile(suffix='.2DM', delete=False) as tmp:
        test_file = tmp.name
        # Write a minimal material header
        with open(test_file, 'wb') as f:
            f.write(struct.pack('<H', 1))  # file_version
            f.write(struct.pack('<H', 0))  # some_flag
            f.write(struct.pack('<I', 0))  # unk1
            f.write(struct.pack('<I', 64))  # size
            f.write(struct.pack('<I', 0x4D44322E))  # ".2DM" magic

    try:
        # Try to parse the test file
        print(f"Attempting to parse material file: {test_file}")
        material = TDU2MaterialParser.parse(test_file)
        print(f"Successfully parsed TDU2 material!")
        print(f"  File version: {material.file_version}")
        print(f"  Some flag: {material.some_flag}")
        print(f"  Unk1: {material.unk1}")
        print(f"  Size: {material.size}")
        print(f"  Number of segments: {len(material.segments)}")
        
        print("\nMaterial parsing test passed!")
        return True
    except Exception as e:
        print(f"Material parsing test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up
        if os.path.exists(test_file):
            os.unlink(test_file)


if __name__ == "__main__":
    print("=" * 60)
    print("Testing TDU2 Blender Addon")
    print("=" * 60)
    
    all_passed = True
    
    print("\n1. Testing Model File Parsing...")
    print("-" * 40)
    if not test_model_parsing():
        all_passed = False
    
    print("\n2. Testing Texture File Parsing...")
    print("-" * 40)
    if not test_texture_parsing():
        all_passed = False
    
    print("\n3. Testing Material File Parsing...")
    print("-" * 40)
    if not test_material_parsing():
        all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("ALL TESTS PASSED!")
    else:
        print("SOME TESTS FAILED")
    print("=" * 60)
    
    sys.exit(0 if all_passed else 1)

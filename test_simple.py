# Simple test script that doesn't require bpy
# Run this to verify the parsing logic works without Blender

import sys
import os
import struct
import tempfile

# Import from the parser module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from io_scene_tdu2.parser import TDU2ModelParser


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


def test_import():
    """Test importing a TDU2 model file"""
    # Create a temporary test file
    with tempfile.NamedTemporaryFile(suffix='.3DG', delete=False) as tmp:
        test_file = tmp.name
        create_test_model_file(test_file)

    try:
        # Try to parse the test file
        print(f"Attempting to parse: {test_file}")
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
        
        print("\nTest passed!")
        return True
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up
        if os.path.exists(test_file):
            os.unlink(test_file)


if __name__ == "__main__":
    success = test_import()
    sys.exit(0 if success else 1)
